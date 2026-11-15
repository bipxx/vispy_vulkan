# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in native Tk WSI presentation camera, multi-widget Frame embed, and timer GPU tests.

Scope boundary:
- Exercises experimental opt-in `backend_kwargs={'presentation': 'native'}` embedded inside
  a multi-widget `tkinter.Frame` (`Label`, `Button`, `SceneCanvas`) on Windows Win32 and
  Linux/WSL X11 WSI surfaces without `PhotoImage` raster uploads.
- Verifies `PanZoomCamera` and `TurntableCamera` zoom/pan/orbit with `Line` and `Markers`
  visuals, explicit `canvas.render()` and `gloo.read_pixels()` pixel checks across camera
  mutations, `app.Timer` execution inside the native Tk event loop, default raster isolation
  (`app.Canvas(app='tkinter')` keeps `attached is False`), and clean teardown.
- Raster remains the default Tk presentation mode; mandatory matrix admission remains false.
"""
from __future__ import annotations

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


def _pump(application, _dawn, predicate, timeout=8.0, desc='Tk native condition'):
    deadline = time.monotonic() + timeout
    while True:
        application.process_events()
        _dawn.process_events()
        if predicate():
            return
        assert time.monotonic() < deadline, f'Timed out waiting for {desc}'
        time.sleep(0.005)


def _drain_idle(application, _dawn, timeout=6.0):
    _pump(
        application,
        _dawn,
        lambda: not any(_dawn.probe()[k] for k in ('pending_tickets', 'queued_frames')),
        timeout=timeout,
        desc='Dawn idle retirement',
    )


def _make_native_scene_canvas(**kwargs):
    """Construct a SceneCanvas forwarding `backend_kwargs` via `create_native=False`.

    Upstream `vispy.scene.SceneCanvas.__init__` does not accept `backend_kwargs` directly,
    while its `vispy.app.Canvas` base stores `self._backend_kwargs` before `create_native()`.
    """
    from vispy import scene

    backend_kwargs = kwargs.pop('backend_kwargs', None)
    create_native = kwargs.pop('create_native', True)
    canvas = scene.SceneCanvas(create_native=False, **kwargs)
    if backend_kwargs is not None:
        canvas._backend_kwargs.update(**backend_kwargs)
    if create_native:
        canvas.create_native()
        if not canvas._backend.__class__.__module__.endswith('jupyter_rfb'):
            canvas.set_current()
    return canvas


def _count_dominant(img, channel, min_val=150, max_other=90):
    rgb = img[..., :3].astype(np.int32)
    others = [i for i in range(3) if i != channel]
    mask = (rgb[..., channel] >= min_val) & (rgb[..., others[0]] <= max_other) & (rgb[..., others[1]] <= max_other)
    return mask


def _centroid_rc(mask):
    ys, xs = np.nonzero(mask)
    assert len(xs) > 0, 'Expected non-empty pixel mask for visual landmark'
    return float(ys.mean()), float(xs.mean())


def _tk_exists(tk, widget):
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def test_tk_native_embedded_frame_panzoom_line_markers_and_button_reset(monkeypatch):
    tk = pytest.importorskip('tkinter')
    from vispy import _dawn, gloo, scene
    from vispy.app.backends import _dawn_tk
    import vispy.app._default_app as default_app_mod

    # Upstream SceneCanvas.__init__ does not take backend_kwargs directly; verify clean TypeError
    # before creating any Tk root, then use the create_native=False forwarding helper.
    with pytest.raises(TypeError, match='backend_kwargs'):
        scene.SceneCanvas(create_native=False, backend_kwargs={'presentation': 'native'})

    def _forbid_photo(*args, **kwargs):
        raise AssertionError('Native Tk presentation must never allocate a tk.PhotoImage')

    monkeypatch.setattr(_dawn_tk.tk, 'PhotoImage', _forbid_photo)

    prev_default_app = default_app_mod.default_app
    host_root = tk.Tk()
    host_root.geometry('260x240+30+30')
    frame = tk.Frame(host_root, width=220, height=210)
    frame.pack(fill='both', expand=True)

    status_label = tk.Label(frame, text='Native Vulkan Frame Host')
    status_label.pack(side='top', fill='x')

    button_clicks = []
    canvas = None
    cam = None

    def _on_reset_button():
        button_clicks.append(1)
        if cam is not None and canvas is not None:
            cam.rect = (-2.0, -1.5, 4.0, 3.0)
            status_label.configure(text=f'Reset #{len(button_clicks)}')
            canvas.update()

    reset_button = tk.Button(frame, text='Reset Camera', command=_on_reset_button)
    reset_button.pack(side='top')
    host_root.update_idletasks()

    canvas = _make_native_scene_canvas(
        app='tkinter',
        parent=frame,
        size=(180, 132),
        backend_kwargs={'presentation': 'native'},
        show=True,
        bgcolor='black',
        config={'samples': 0},
    )
    tk_app = canvas.app
    default_app_mod.default_app = tk_app

    frame_counter = [0]

    @canvas.events.draw.connect
    def _track_frame(event):
        if canvas._backend._dawn_canvas_id:
            frame_counter[0] += 1
            _dawn.benchmark_begin_frame(canvas._backend._dawn_canvas_id, frame_counter[0])

    try:
        canvas.native.pack(side='top')
        host_root.deiconify()
        host_root.update_idletasks()

        cid = int(canvas._backend._dawn_canvas_id)
        assert cid != 0
        _pump(
            tk_app,
            _dawn,
            lambda: bool(_dawn.benchmark_surface_info(cid)['attached'])
            and canvas.native.winfo_viewable()
            and canvas.physical_size == (180, 132),
            desc='embedded native Tk SceneCanvas surface attachment',
        )

        assert tk_app._backend._owns_root is False
        assert tk_app._backend._root is host_root
        assert isinstance(canvas.native, _dawn_tk._NativeFrame)
        assert canvas.native.master is frame
        assert status_label.winfo_exists() and reset_button.winfo_exists()
        assert _dawn.benchmark_surface_info(cid)['attached'] is True
        assert getattr(canvas._backend, '_photo', None) is None

        view = canvas.central_widget.add_view()
        view.bgcolor = '#000000'
        cam = scene.cameras.PanZoomCamera(rect=(-2.0, -1.5, 4.0, 3.0), aspect=None)
        cam.zoom_factor = 2 ** (1.0 / 30.0) - 1.0
        view.camera = cam

        line = scene.visuals.Line(
            pos=np.array([[-1.6, -1.0], [1.6, -1.0]], dtype=np.float32),
            color=(0.0, 0.0, 1.0, 1.0),
            width=4.0,
            parent=view.scene,
        )
        markers = scene.visuals.Markers(
            pos=np.array([[0.0, 0.0], [-1.0, 0.5]], dtype=np.float32),
            size=16.0,
            edge_width=0.0,
            face_color=np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]], dtype=np.float32),
            parent=view.scene,
        )
        assert line is not None and markers is not None
        cam.rect = (-2.0, -1.5, 4.0, 3.0)

        # Pump native WSI draw + presentation and verify swapchain completion + zero PhotoImage.
        before_frames = frame_counter[0]
        canvas.update()
        _pump(
            tk_app,
            _dawn,
            lambda: frame_counter[0] > before_frames
            and any(r['presented'] for r in _dawn.benchmark_completions(cid)),
            desc='native WSI present completion for initial PanZoom scene',
        )
        _drain_idle(tk_app, _dawn)
        assert getattr(canvas._backend, '_photo', None) is None

        # Verify both explicit canvas.render() (FBO read_pixels) and canvas gloo.read_pixels().
        img0 = canvas.render(alpha=True)
        canvas.set_current()
        fb0 = gloo.read_pixels((0, 0, *canvas.physical_size), alpha=True)
        assert img0.shape == (132, 180, 4)
        assert fb0.shape[2] == 4 and int(np.count_nonzero(fb0[..., :3] > 80)) > 30

        red0 = _count_dominant(img0, 0)
        green0 = _count_dominant(img0, 1)
        blue0 = _count_dominant(img0, 2)
        assert int(red0.sum()) >= 20
        assert int(green0.sum()) >= 20
        assert int(blue0.sum()) >= 40
        r_row0, r_col0 = _centroid_rc(red0)
        assert abs(r_col0 - 90.0) < 6.0 and abs(r_row0 - 66.0) < 6.0

        # 1) MouseWheel zoom anchored off-center + left-button drag pan on native widget.
        raw_delta = 1 if sys.platform == 'darwin' else 120
        canvas.native.event_generate('<MouseWheel>', x=45, y=44, delta=raw_delta)
        rect_zoomed = tuple(cam.rect.pos) + tuple(cam.rect.size)
        assert rect_zoomed[2] < 3.5 and rect_zoomed[3] < 2.7

        img_zoom = canvas.render(alpha=True)
        assert not np.array_equal(img0, img_zoom)
        assert int(_count_dominant(img_zoom, 0).sum()) >= 20

        canvas.native.event_generate('<ButtonPress-1>', x=90, y=66)
        time.sleep(0.015)
        canvas.native.event_generate('<Motion>', x=126, y=84, state=0x0100)
        canvas.native.event_generate('<ButtonRelease-1>', x=126, y=84, state=0x0100)
        rect_panned = tuple(cam.rect.pos) + tuple(cam.rect.size)
        assert rect_panned[:2] != pytest.approx(rect_zoomed[:2])

        img_pan = canvas.render(alpha=True)
        assert not np.array_equal(img_zoom, img_pan)
        r_row_pan, r_col_pan = _centroid_rc(_count_dominant(img_pan, 0))
        assert abs(r_col_pan - r_col0) > 8.0 or abs(r_row_pan - r_row0) > 6.0

        # 2) Sibling Tk Button in same host Frame resets PanZoomCamera and updates native scene.
        before_reset_frames = frame_counter[0]
        reset_button.invoke()
        assert len(button_clicks) == 1
        assert status_label.cget('text') == 'Reset #1'
        _pump(
            tk_app,
            _dawn,
            lambda: frame_counter[0] > before_reset_frames,
            desc='native redraw after sibling Tk Button camera reset',
        )
        _drain_idle(tk_app, _dawn)
        img_reset = canvas.render(alpha=True)
        r_row_rst, r_col_rst = _centroid_rc(_count_dominant(img_reset, 0))
        assert abs(r_col_rst - r_col0) < 2.0 and abs(r_row_rst - r_row0) < 2.0
        assert _dawn.benchmark_surface_info(cid)['attached'] is True
        assert getattr(canvas._backend, '_photo', None) is None
    finally:
        default_app_mod.default_app = prev_default_app
        if canvas is not None and not canvas._closed:
            canvas.close()
        assert canvas._backend._dawn_canvas_id == 0
        tk_app.quit()
        assert _tk_exists(tk, host_root) is True
        host_root.update_idletasks()
        host_root.destroy()
        assert _tk_exists(tk, host_root) is False
        gc.collect()
        _dawn.process_events()

    probe = _dawn.probe()
    for gauge in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert int(probe[gauge]) == 0, {k: int(probe[k]) for k in TEN_GAUGES}


def test_tk_native_embedded_turntable_camera_orbit_zoom_line_markers_render(monkeypatch):
    tk = pytest.importorskip('tkinter')
    from vispy import _dawn, gloo, scene
    from vispy.app.backends import _dawn_tk
    import vispy.app._default_app as default_app_mod

    def _forbid_photo(*args, **kwargs):
        raise AssertionError('Native Tk Turntable test must never allocate a tk.PhotoImage')

    monkeypatch.setattr(_dawn_tk.tk, 'PhotoImage', _forbid_photo)

    prev_default_app = default_app_mod.default_app
    host_root = tk.Tk()
    host_root.geometry('260x260+40+40')
    frame = tk.Frame(host_root, width=230, height=230)
    frame.pack(fill='both', expand=True)
    tk.Label(frame, text='Turntable 3D Native').pack(side='top')
    orbit_clicks = []
    canvas = None
    cam = None

    def _orbit_step():
        orbit_clicks.append(1)
        if cam is not None and canvas is not None:
            cam.azimuth = cam.azimuth + 55.0
            cam.elevation = cam.elevation + 20.0
            canvas.update()

    orbit_btn = tk.Button(frame, text='Orbit +55', command=_orbit_step)
    orbit_btn.pack(side='top')
    host_root.update_idletasks()

    canvas = _make_native_scene_canvas(
        app='tkinter',
        parent=frame,
        size=(180, 132),
        backend_kwargs={'presentation': 'native'},
        show=True,
        bgcolor='black',
        config={'samples': 0},
    )
    tk_app = canvas.app
    default_app_mod.default_app = tk_app

    draw_seq = [0]

    @canvas.events.draw.connect
    def _on_draw_begin(event):
        if canvas._backend._dawn_canvas_id:
            draw_seq[0] += 1
            _dawn.benchmark_begin_frame(canvas._backend._dawn_canvas_id, draw_seq[0])

    try:
        canvas.native.pack(side='top')
        host_root.deiconify()
        host_root.update_idletasks()

        cid = int(canvas._backend._dawn_canvas_id)
        _pump(
            tk_app,
            _dawn,
            lambda: bool(_dawn.benchmark_surface_info(cid)['attached'])
            and canvas.native.winfo_viewable()
            and canvas.physical_size == (180, 132),
            desc='embedded native Turntable surface attachment',
        )
        assert _dawn.benchmark_surface_info(cid)['attached'] is True
        assert getattr(canvas._backend, '_photo', None) is None

        view = canvas.central_widget.add_view()
        view.bgcolor = '#000000'
        cam = scene.cameras.TurntableCamera(
            fov=45.0, azimuth=20.0, elevation=18.0, distance=4.2, scale_factor=2.8
        )
        view.camera = cam

        line3d = scene.visuals.Line(
            pos=np.array(
                [[-1.1, 0.0, 0.0], [1.1, 0.0, 0.0], [0.0, 1.1, 0.4], [0.0, -0.9, -0.5]],
                dtype=np.float32,
            ),
            color=(0.0, 0.0, 1.0, 1.0),
            width=3.0,
            parent=view.scene,
        )
        markers3d = scene.visuals.Markers(
            pos=np.array([[-0.9, 0.0, 0.2], [0.9, 0.2, -0.3]], dtype=np.float32),
            size=18.0,
            edge_width=0.0,
            face_color=np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]], dtype=np.float32),
            parent=view.scene,
        )
        assert line3d is not None and markers3d is not None

        seq0 = draw_seq[0]
        canvas.update()
        _pump(
            tk_app,
            _dawn,
            lambda: draw_seq[0] > seq0 and any(r['presented'] for r in _dawn.benchmark_completions(cid)),
            desc='initial 3D Turntable native presentation',
        )
        _drain_idle(tk_app, _dawn)

        frame0 = canvas.render(alpha=True)
        canvas.set_current()
        native_fb0 = gloo.read_pixels((0, 0, *canvas.physical_size), alpha=True)
        assert frame0.shape == (132, 180, 4)
        assert int(np.count_nonzero(frame0[..., :3] > 80)) > 40
        assert int(np.count_nonzero(native_fb0[..., :3] > 80)) > 30
        red_c0 = _centroid_rc(_count_dominant(frame0, 0))
        green_c0 = _centroid_rc(_count_dominant(frame0, 1))

        # Mouse drag orbit + sibling Button orbit + MouseWheel zoom.
        az0, el0, sf0 = cam.azimuth, cam.elevation, cam.scale_factor
        canvas.native.event_generate('<ButtonPress-1>', x=40, y=45)
        time.sleep(0.015)
        canvas.native.event_generate('<Motion>', x=115, y=85, state=0x0100)
        canvas.native.event_generate('<ButtonRelease-1>', x=115, y=85, state=0x0100)
        assert cam.azimuth != pytest.approx(az0) or cam.elevation != pytest.approx(el0)

        orbit_btn.invoke()
        assert len(orbit_clicks) == 1
        frame_orbit = canvas.render(alpha=True)
        assert not np.array_equal(frame0, frame_orbit)
        red_c1 = _centroid_rc(_count_dominant(frame_orbit, 0))
        green_c1 = _centroid_rc(_count_dominant(frame_orbit, 1))
        assert (abs(red_c1[0] - red_c0[0]) + abs(red_c1[1] - red_c0[1])) > 4.0
        assert (abs(green_c1[0] - green_c0[0]) + abs(green_c1[1] - green_c0[1])) > 4.0

        raw_delta = 1 if sys.platform == 'darwin' else 120
        canvas.native.event_generate('<MouseWheel>', x=90, y=66, delta=raw_delta)
        assert cam.scale_factor < sf0
        frame_zoom = canvas.render(alpha=True)
        assert not np.array_equal(frame_orbit, frame_zoom)
        assert int(np.count_nonzero(frame_zoom[..., :3] > 80)) > 40

        # Embedded native widget resize updates swapchain/canvas size cleanly without PhotoImage.
        canvas.size = (200, 144)
        canvas.update()
        _pump(
            tk_app,
            _dawn,
            lambda: canvas.physical_size == (200, 144),
            desc='embedded native Turntable resize (200, 144)',
        )
        _drain_idle(tk_app, _dawn)
        frame_resized = canvas.render(alpha=True)
        assert frame_resized.shape == (144, 200, 4)
        assert int(np.count_nonzero(frame_resized[..., :3] > 80)) > 40
        assert getattr(canvas._backend, '_photo', None) is None
    finally:
        default_app_mod.default_app = prev_default_app
        if canvas is not None and not canvas._closed:
            canvas.close()
        assert canvas._backend._dawn_canvas_id == 0
        tk_app.quit()
        if _tk_exists(tk, host_root):
            host_root.update_idletasks()
            host_root.destroy()
        assert _tk_exists(tk, host_root) is False
        gc.collect()
        _dawn.process_events()

    probe = _dawn.probe()
    for gauge in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert int(probe[gauge]) == 0, {k: int(probe[k]) for k in TEN_GAUGES}


def test_tk_native_timer_loop_and_raster_default_isolation():
    tk = pytest.importorskip('tkinter')
    from vispy import _dawn, app, gloo, scene
    import vispy.app._default_app as default_app_mod

    prev_default_app = default_app_mod.default_app
    host_root = tk.Tk()
    host_root.geometry('250x220+50+50')
    frame = tk.Frame(host_root, width=210, height=190)
    frame.pack(fill='both', expand=True)
    header = tk.Label(frame, text='Timer Loop Idle')
    header.pack(side='top')
    stop_btn = tk.Button(frame, text='Exit Loop', command=host_root.quit)
    stop_btn.pack(side='top')
    host_root.update_idletasks()

    native_canvas = _make_native_scene_canvas(
        app='tkinter',
        parent=frame,
        size=(160, 120),
        backend_kwargs={'presentation': 'native'},
        show=True,
        bgcolor='black',
        config={'samples': 0},
    )
    tk_app = native_canvas.app
    default_app_mod.default_app = tk_app

    raster_canvas = None
    loop_timer = None
    watchdog_job = None
    try:
        native_canvas.native.pack(side='top', fill='both', expand=True)
        host_root.deiconify()
        host_root.update_idletasks()

        native_cid = int(native_canvas._backend._dawn_canvas_id)
        _pump(
            tk_app,
            _dawn,
            lambda: bool(_dawn.benchmark_surface_info(native_cid)['attached'])
            and native_canvas.native.winfo_viewable(),
            desc='native SceneCanvas attach before Timer loop',
        )
        assert _dawn.benchmark_surface_info(native_cid)['attached'] is True
        assert getattr(native_canvas._backend, '_photo', None) is None

        view = native_canvas.central_widget.add_view()
        view.bgcolor = '#000000'
        cam = scene.cameras.PanZoomCamera(rect=(-2.0, -1.5, 4.0, 3.0), aspect=None)
        view.camera = cam
        scene.visuals.Line(
            pos=np.array([[-1.5, 0.0], [1.5, 0.0]], dtype=np.float32),
            color=(0.0, 0.0, 1.0, 1.0),
            width=3.0,
            parent=view.scene,
        )
        marker = scene.visuals.Markers(
            pos=np.array([[-1.0, 0.0]], dtype=np.float32),
            size=16.0,
            edge_width=0.0,
            face_color=np.array([[1.0, 0.0, 0.0, 1.0]], dtype=np.float32),
            parent=view.scene,
        )
        before_loop_img = native_canvas.render(alpha=True)
        _, col_before = _centroid_rc(_count_dominant(before_loop_img, 0))

        # Run a real VisPy app.Timer inside native tk_app.run() mainloop.
        ticks = []

        def _on_tick(ev):
            ticks.append((ev.iteration, ev.count))
            x_pos = -1.0 + 0.9 * (ev.iteration + 1)
            marker.set_data(
                pos=np.array([[x_pos, 0.0]], dtype=np.float32),
                size=16.0,
                edge_width=0.0,
                face_color=np.array([[1.0, 0.0, 0.0, 1.0]], dtype=np.float32),
            )
            header.configure(text=f'Tick {ev.iteration}')
            native_canvas.update()
            if len(ticks) >= 3:
                host_root.after(15, stop_btn.invoke)

        loop_timer = app.Timer(interval=0.01, connect=_on_tick, iterations=3, start=True, app=tk_app)
        watchdog_job = host_root.after(6000, host_root.quit)
        tk_app.run()
        if watchdog_job is not None:
            try:
                host_root.after_cancel(watchdog_job)
            except tk.TclError:
                pass
            watchdog_job = None

        assert ticks == [(0, 0), (1, 1), (2, 2)]
        assert loop_timer.running is False
        assert header.cget('text') == 'Tick 2'
        _drain_idle(tk_app, _dawn)

        after_loop_img = native_canvas.render(alpha=True)
        _, col_after = _centroid_rc(_count_dominant(after_loop_img, 0))
        assert col_after - col_before > 35.0
        assert _dawn.benchmark_surface_info(native_cid)['attached'] is True
        assert getattr(native_canvas._backend, '_photo', None) is None

        # Default raster isolation check: app.Canvas(app='tkinter') stays raster (`attached is False`).
        raster_canvas = app.Canvas(app='tkinter', size=(96, 64), show=True, config={'samples': 0})

        @raster_canvas.events.draw.connect
        def _draw_raster(event):
            gloo.set_viewport(0, 0, *raster_canvas.physical_size)
            gloo.clear(color=(0.0, 1.0, 0.0, 1.0))

        raster_cid = int(raster_canvas._backend._dawn_canvas_id)
        assert _dawn.benchmark_surface_info(raster_cid)['attached'] is False
        _pump(
            raster_canvas.app,
            _dawn,
            lambda: raster_canvas._backend._photo is not None,
            desc='default raster Canvas PhotoImage presentation',
        )
        assert _dawn.benchmark_surface_info(raster_cid)['attached'] is False
        assert raster_canvas._backend._photo.get(48, 32) == (0, 255, 0)
        # Meanwhile native_canvas remains native-attached with zero PhotoImage!
        assert _dawn.benchmark_surface_info(native_cid)['attached'] is True
        assert getattr(native_canvas._backend, '_photo', None) is None
    finally:
        default_app_mod.default_app = prev_default_app
        if loop_timer is not None:
            loop_timer.stop()
        if raster_canvas is not None and not raster_canvas._closed:
            raster_canvas.close()
            raster_canvas.app.quit()
        if native_canvas is not None and not native_canvas._closed:
            native_canvas.close()
        assert native_canvas._backend._dawn_canvas_id == 0
        tk_app.quit()
        if _tk_exists(tk, host_root):
            host_root.update_idletasks()
            host_root.destroy()
        assert _tk_exists(tk, host_root) is False
        gc.collect()
        _dawn.process_events()

    probe = _dawn.probe()
    for gauge in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert int(probe[gauge]) == 0, {k: int(probe[k]) for k in TEN_GAUGES}
