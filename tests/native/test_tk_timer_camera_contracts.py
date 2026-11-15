# -*- coding: utf-8 -*-
"""Raster-present Tkinter timer, event, and camera contract tests for LIF-07.

Scope boundary:
- Covers the supported raster-present `Application('tkinter')` backend (`_dawn_tk`
  `PhotoImage` upload path, `_dawn.benchmark_surface_info(...)['attached'] is False`).
- Native Tk WSI swapchain admission (`LIF-07-NATIVE-ADMISSION`) remains strictly
  separate and out of scope here.
"""

import gc
import sys
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu

TEN_GAUGES = (
    'pending_tickets',
    'queued_frames',
    'live_buffer_bytes',
    'live_cpu_buffer_bytes',
    'live_texture_bytes',
    'canvas_texture_bytes',
    'transient_buffer_bytes',
    'line_resource_pool_busy_slots',
    'line_resource_pool_bytes',
    'host_import_pinned_bytes',
)


def _wait_tk(application, _dawn, predicate, timeout=5.0, desc='Tk/Dawn condition'):
    deadline = time.monotonic() + timeout
    while True:
        application.process_events()
        _dawn.process_events()
        if predicate():
            return
        assert time.monotonic() < deadline, f'timed out waiting for {desc}'
        time.sleep(0.004)


def _drain_idle(application, _dawn, timeout=5.0):
    _wait_tk(
        application,
        _dawn,
        lambda: not any(_dawn.probe()[k] for k in ('pending_tickets', 'queued_frames')),
        timeout=timeout,
        desc='Dawn idle retirement',
    )


def _ten_gauges(_dawn):
    probe = _dawn.probe()
    return {name: int(probe[name]) for name in TEN_GAUGES}


@pytest.fixture
def tk_app():
    tk = pytest.importorskip('tkinter')
    from vispy import _dawn, app
    import vispy.app._default_app as default_app_mod

    initial_root = getattr(tk, '_default_root', None)
    prev_default_app = default_app_mod.default_app
    application = app.Application('tkinter')
    default_app_mod.default_app = application
    yield application
    root = application._backend._root
    try:
        application.quit()
    finally:
        default_app_mod.default_app = prev_default_app
        if root is not None and root is not initial_root:
            try:
                alive = bool(root.winfo_exists())
            except tk.TclError:
                alive = False
            if alive:
                root.update_idletasks()
                root.destroy()
        gc.collect()
        _dawn.process_events()


def test_lif07_tk_raster_timer_single_shot_repeating_restart_and_photo_redraw(tk_app):
    from vispy import _dawn, app, gloo

    palette = [
        (1.0, 0.0, 0.0, 1.0),
        (0.0, 1.0, 0.0, 1.0),
        (1.0, 0.0, 1.0, 1.0),
        (0.0, 0.0, 1.0, 1.0),
    ]
    current_color = list(palette[0])

    canvas = app.Canvas(app=tk_app, size=(64, 48), show=True, config={'samples': 0})

    @canvas.connect
    def on_draw(event):
        w, h = canvas.physical_size
        gloo.set_viewport(0, 0, w, h)
        gloo.clear(color=current_color)

    single_ticks = []
    single_timer = app.Timer(
        interval=0.005,
        connect=lambda ev: single_ticks.append((ev.iteration, ev.count)),
        iterations=1,
        start=False,
        app=tk_app,
    )

    repeat_ticks = []

    def _on_repeat(ev):
        idx = min(ev.iteration + 1, len(palette) - 1)
        current_color[:] = palette[idx]
        repeat_ticks.append((ev.iteration, ev.count))
        canvas.update()

    repeat_timer = app.Timer(
        interval=0.005,
        connect=_on_repeat,
        iterations=3,
        start=False,
        app=tk_app,
    )

    try:
        _wait_tk(
            tk_app,
            _dawn,
            lambda: canvas._backend._photo is not None and canvas.native.winfo_viewable(),
            desc='initial Tk raster presentation',
        )
        cid = int(canvas._backend._dawn_canvas_id)
        assert _dawn.benchmark_surface_info(cid)['attached'] is False
        assert canvas._backend._photo.get(32, 24) == (255, 0, 0)

        # 1) Single-shot Tcl `after` timer stops cleanly and clears `_job`.
        single_timer.start()
        _wait_tk(tk_app, _dawn, lambda: not single_timer.running, desc='Tk single-shot timer stop')
        assert single_ticks == [(0, 0)]
        assert single_timer._backend._job is None

        # 2) Repeating 3-tick timer updates Canvas uniform color and raster PhotoImage pixels.
        repeat_timer.start()
        _wait_tk(tk_app, _dawn, lambda: not repeat_timer.running, desc='Tk 3-tick timer completion')
        prev_photo = canvas._backend._photo
        canvas.update()
        _wait_tk(tk_app, _dawn, lambda: canvas._backend._photo is not prev_photo, desc='Tk blue photo refresh')
        _drain_idle(tk_app, _dawn)
        assert repeat_ticks == [(0, 0), (1, 1), (2, 2)]
        assert repeat_timer._backend._job is None
        assert canvas._backend._photo.get(32, 24) == (0, 0, 255)

        # 3) Stop-then-restart increments generation guard so cancelled Tcl jobs cannot misfire.
        gen_ticks = []

        def _on_gen(ev):
            gen_ticks.append(ev.iteration)
            if ev.iteration == 1:
                current_color[:] = [0.0, 1.0, 1.0, 1.0]
                canvas.update()

        gen_timer = app.Timer(interval=0.008, connect=_on_gen, iterations=-1, start=True, app=tk_app)
        try:
            gen_start = gen_timer._backend._generation
            _wait_tk(tk_app, _dawn, lambda: len(gen_ticks) >= 2, desc='Tk infinite timer 2 ticks')
            gen_timer.stop()
            assert gen_timer.running is False
            assert gen_timer._backend._job is None
            assert gen_timer._backend._generation > gen_start
            stopped_len = len(gen_ticks)
            t_hold = time.monotonic() + 0.03
            while time.monotonic() < t_hold:
                tk_app.process_events()
                time.sleep(0.003)
            assert len(gen_ticks) == stopped_len

            gen_ticks.clear()
            gen_timer.start(interval=0.005, iterations=2)
            _wait_tk(tk_app, _dawn, lambda: not gen_timer.running, desc='Tk restarted 2-tick timer')
            prev_photo = canvas._backend._photo
            canvas.update()
            _wait_tk(tk_app, _dawn, lambda: canvas._backend._photo is not prev_photo, desc='Tk cyan photo refresh')
            _drain_idle(tk_app, _dawn)
            assert gen_ticks == [0, 1]
            assert canvas._backend._photo.get(32, 24) == (0, 255, 255)
        finally:
            gen_timer.stop()

        # 4) Callback exception stops timer immediately and surfaces cleanly through process_events().
        def _boom_cb(ev):
            raise RuntimeError('tk-timer-intentional-fault')

        # VisPy EmitterGroup logs callback errors unless ignore_callback_errors is disabled on timeout.
        fault_timer = app.Timer(interval=0.003, start=False, app=tk_app)
        fault_timer.events.timeout.ignore_callback_errors = False
        fault_timer.connect(_boom_cb)
        fault_timer.start()
        with pytest.raises(RuntimeError, match='tk-timer-intentional-fault'):
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                tk_app.process_events()
                time.sleep(0.003)
        assert fault_timer.running is False
        assert fault_timer._backend._job is None
    finally:
        single_timer.stop()
        repeat_timer.stop()
        if not canvas._closed:
            canvas.close()
        tk_app.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges


def test_lif07_tk_embedded_frame_panzoom_wheel_drag_and_focus_out_cancel():
    tk = pytest.importorskip('tkinter')
    from vispy import _dawn, app, scene
    import vispy.app._default_app as default_app_mod

    prev_default_app = default_app_mod.default_app
    host_root = tk.Tk()
    host_root.geometry('220x170+20+20')
    host_frame = tk.Frame(host_root, width=180, height=135)
    host_frame.pack(fill='both', expand=True)
    host_root.update_idletasks()

    embedded_app = app.Application('tkinter')
    default_app_mod.default_app = embedded_app
    sc = scene.SceneCanvas(
        app=embedded_app,
        parent=host_frame,
        size=(160, 120),
        show=True,
        bgcolor='black',
        config={'samples': 0},
    )
    sc.native.pack()
    host_root.deiconify()
    host_root.update()
    try:
        assert embedded_app._backend._owns_root is False
        assert embedded_app._backend._root is host_root

        view = sc.central_widget.add_view()
        view.bgcolor = '#000000'
        cam = scene.cameras.PanZoomCamera(rect=(-2.0, -1.5, 4.0, 3.0), aspect=None)
        cam.zoom_factor = 2 ** (1.0 / 30.0) - 1.0
        view.camera = cam
        markers = scene.visuals.Markers(
            pos=np.array([[0.0, 0.0], [-1.0, 0.5]], dtype=np.float32),
            size=14,
            face_color=np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]], dtype=np.float32),
            parent=view.scene,
        )
        assert markers is not None
        cam.rect = (-2.0, -1.5, 4.0, 3.0)
        prev_photo = sc._backend._photo
        sc.update()
        _wait_tk(
            embedded_app,
            _dawn,
            lambda: (
                sc._backend._photo is not None
                and sc._backend._photo is not prev_photo
                and sc.native.winfo_viewable()
            ),
            desc='embedded Tk SceneCanvas viewable',
        )
        _drain_idle(embedded_app, _dawn)
        assert sc._backend._photo.get(80, 60) == (255, 0, 0)

        # Cursor-anchored <MouseWheel> zoom at pixel (40, 40) -> world (-1.0, +0.5).
        wheel_events = []
        sc.events.mouse_wheel.connect(lambda ev: wheel_events.append((tuple(ev.pos), tuple(ev.delta))))
        raw_delta = 1 if sys.platform == 'darwin' else 120
        sc.native.event_generate('<MouseWheel>', x=40, y=40, delta=raw_delta)
        assert wheel_events[-1] == ((40, 40), (0.0, 1.0))
        np.testing.assert_allclose(
            cam.rect.pos + cam.rect.size,
            (-1.5, -0.5, 2.0, 1.5),
            rtol=0,
            atol=1e-5,
        )

        # Mid-drag <FocusOut> must release active button state and stop further drag motion panning.
        sc.native.event_generate('<ButtonPress-1>', x=60, y=60)
        time.sleep(0.014)
        sc.native.event_generate('<Motion>', x=90, y=75, state=0x0100)
        rect_after_drag = tuple(cam.rect.pos) + tuple(cam.rect.size)
        assert rect_after_drag != (-1.5, -0.5, 2.0, 1.5)

        sc.native.event_generate('<FocusOut>')
        assert sc._backend._pressed_buttons == set()
        time.sleep(0.014)
        sc.native.event_generate('<Motion>', x=120, y=95, state=0x0100)
        np.testing.assert_allclose(
            cam.rect.pos + cam.rect.size,
            rect_after_drag,
            rtol=0,
            atol=1e-6,
        )
    finally:
        default_app_mod.default_app = prev_default_app
        if not sc._closed:
            sc.close()
        embedded_app.quit()
        # Host root must survive Application.quit() when _owns_root is False, then host destroys it.
        assert bool(host_root.winfo_exists()) is True
        host_root.update_idletasks()
        host_root.destroy()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges


def test_lif07_tk_turntable_camera_orbit_zoom_and_resize_raster_present(tk_app):
    from vispy import _dawn, scene

    sc = scene.SceneCanvas(
        app=tk_app, size=(120, 96), show=True, bgcolor='black', config={'samples': 0}
    )
    view = sc.central_widget.add_view()
    cam = scene.cameras.TurntableCamera(
        fov=45.0, azimuth=30.0, elevation=25.0, distance=4.0, scale_factor=2.4
    )
    view.camera = cam
    box = scene.visuals.Box(
        width=1.0,
        height=0.9,
        depth=1.1,
        color=(0.1, 0.8, 0.9, 1.0),
        edge_color='white',
        parent=view.scene,
    )
    assert box is not None

    try:
        sc.update()
        _wait_tk(
            tk_app,
            _dawn,
            lambda: sc._backend._photo is not None and sc.native.winfo_viewable(),
            desc='Tk Turntable SceneCanvas viewable',
        )
        _drain_idle(tk_app, _dawn)
        cid = int(sc._backend._dawn_canvas_id)
        assert _dawn.benchmark_surface_info(cid)['attached'] is False

        az0, el0, sf0 = cam.azimuth, cam.elevation, cam.scale_factor
        photo0 = sc._backend._photo
        assert (photo0.width(), photo0.height()) == (120, 96)

        # Left-button drag orbits TurntableCamera.
        sc.native.event_generate('<ButtonPress-1>', x=30, y=30)
        time.sleep(0.014)
        sc.native.event_generate('<Motion>', x=80, y=65, state=0x0100)
        sc.native.event_generate('<ButtonRelease-1>', x=80, y=65, state=0x0100)
        assert cam.azimuth != pytest.approx(az0) or cam.elevation != pytest.approx(el0)

        # Wheel zooms TurntableCamera.
        raw_delta = 1 if sys.platform == 'darwin' else 120
        sc.native.event_generate('<MouseWheel>', x=60, y=48, delta=raw_delta)
        assert cam.scale_factor < sf0

        # Resize updates raster PhotoImage dimensions and presents non-black rendered 3D scene.
        sc.size = (160, 120)
        sc.update()
        _wait_tk(
            tk_app,
            _dawn,
            lambda: sc._backend._photo is not None
            and (sc._backend._photo.width(), sc._backend._photo.height()) == (160, 120),
            desc='Tk resized PhotoImage (160, 120)',
        )
        _drain_idle(tk_app, _dawn)

        center_rgb = sc._backend._photo.get(80, 60)
        assert sum(center_rgb) > 30, f'expected rendered Box at center of PhotoImage, got {center_rgb}'
        rendered = sc.render(alpha=True)
        assert rendered.shape == (120, 160, 4)
    finally:
        if not sc._closed:
            sc.close()
        tk_app.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges
