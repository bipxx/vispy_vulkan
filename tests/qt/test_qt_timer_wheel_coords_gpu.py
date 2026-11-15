# -*- coding: utf-8 -*-
"""Qt GPU timer and toolkit-synthesized input/camera tests for LIF-06.

Scope boundary:
- Events are delivered via `QCoreApplication.sendEvent` to real Qt `QWidget`
  instances (`event.native.spontaneous() is False`).
- Physical HID devices, OS window-manager focus stealing, and multi-monitor
  fractional DPI moves (`LIF-08`) are explicitly out of scope here.
"""

import gc
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


def _qt_modules():
    PyQt6 = pytest.importorskip('PyQt6')
    from PyQt6 import QtCore, QtGui, QtWidgets
    return PyQt6, QtCore, QtGui, QtWidgets


def _pump_until(application, _dawn, predicate, timeout=5.0, desc='Qt timer/input condition'):
    deadline = time.monotonic() + timeout
    while True:
        application.process_events()
        _dawn.process_events()
        if predicate():
            return
        assert time.monotonic() < deadline, f'timed out waiting for {desc}'
        time.sleep(0.002)


def _drain_idle(application, _dawn, timeout=5.0):
    _pump_until(
        application,
        _dawn,
        lambda: not any(_dawn.probe()[k] for k in ('pending_tickets', 'queued_frames')),
        timeout=timeout,
        desc='Dawn idle retirement',
    )


def _ten_gauges(_dawn):
    probe = _dawn.probe()
    return {name: int(probe[name]) for name in TEN_GAUGES}


def test_lif06_qt_timer_single_shot_repeating_stop_restart_and_gpu_redraw(monkeypatch):
    _, QtCore, _, _ = _qt_modules()
    from vispy import _dawn, app, gloo

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')

    palette = [
        (1.0, 0.0, 0.0, 1.0),
        (0.0, 1.0, 0.0, 1.0),
        (1.0, 0.0, 1.0, 1.0),
        (0.0, 0.0, 1.0, 1.0),
    ]
    active_color = list(palette[0])
    draws = []

    canvas = app.Canvas(app='pyqt6', size=(48, 36), show=False, vsync=False)

    @canvas.connect
    def on_draw(event):
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color=active_color)
        draws.append(tuple(active_color))

    single_ticks = []
    single_timer = app.Timer(
        interval=0.005,
        connect=lambda ev: single_ticks.append((ev.iteration, ev.count)),
        iterations=1,
        start=False,
        app=application,
    )

    repeat_ticks = []

    def _on_repeat(ev):
        idx = min(ev.iteration + 1, len(palette) - 1)
        active_color[:] = palette[idx]
        repeat_ticks.append((ev.iteration, ev.count))
        canvas.update()

    repeat_timer = app.Timer(
        interval=0.005,
        connect=_on_repeat,
        iterations=3,
        start=False,
        app=application,
    )

    try:
        canvas.show()
        _pump_until(application, _dawn, lambda: len(draws) >= 1, desc='initial timer canvas paint')
        _drain_idle(application, _dawn)

        # 1) Single-shot QTimer route stops automatically after 1 iteration.
        single_timer.start()
        assert single_timer.running is True
        _pump_until(application, _dawn, lambda: not single_timer.running, desc='single-shot QTimer stop')
        assert single_ticks == [(0, 0)]
        assert single_timer.iter_count == 1
        assert single_timer.native.isActive() is False

        # 2) Finite repeating QTimer drives live Canvas color transitions and auto-stops at 3 ticks.
        draws_before = len(draws)
        repeat_timer.start()
        _pump_until(
            application,
            _dawn,
            lambda: not repeat_timer.running and len(draws) >= draws_before + 1,
            desc='3-iteration QTimer completion',
        )
        # Ensure final scheduled repaint completes.
        prev_draws = len(draws)
        canvas.update()
        _pump_until(application, _dawn, lambda: len(draws) > prev_draws, desc='post-repeat repaint')
        _drain_idle(application, _dawn)

        assert repeat_ticks == [(0, 0), (1, 1), (2, 2)]
        assert repeat_timer.native.isActive() is False
        canvas.set_current()
        px_blue = gloo.read_pixels(alpha=True)
        np.testing.assert_allclose(px_blue[18, 24], [0, 0, 255, 255], atol=1)

        # 3) Infinite start -> explicit stop -> verify quiescence -> restart with updated interval/iterations.
        restart_ticks = []

        def _on_restart(ev):
            restart_ticks.append(ev.iteration)
            if ev.iteration == 1:
                active_color[:] = [1.0, 1.0, 0.0, 1.0]
                canvas.update()

        restart_timer = app.Timer(interval=0.008, connect=_on_restart, iterations=-1, start=True, app=application)
        try:
            _pump_until(application, _dawn, lambda: len(restart_ticks) >= 2, desc='infinite timer 2 ticks')
            restart_timer.stop()
            assert restart_timer.running is False
            assert restart_timer.native.isActive() is False
            frozen_count = len(restart_ticks)
            t_end = time.monotonic() + 0.03
            while time.monotonic() < t_end:
                application.process_events()
                time.sleep(0.002)
            assert len(restart_ticks) == frozen_count

            restart_ticks.clear()
            restart_timer.start(interval=0.004, iterations=2)
            _pump_until(application, _dawn, lambda: not restart_timer.running, desc='restarted 2-tick timer')
            prev_d = len(draws)
            canvas.update()
            _pump_until(application, _dawn, lambda: len(draws) > prev_d, desc='restarted final paint')
            _drain_idle(application, _dawn)
            assert restart_ticks == [0, 1]
            canvas.set_current()
            px_yellow = gloo.read_pixels(alpha=True)
            np.testing.assert_allclose(px_yellow[18, 24], [255, 255, 0, 255], atol=1)
        finally:
            restart_timer.stop()
    finally:
        single_timer.stop()
        repeat_timer.stop()
        if not canvas._closed:
            canvas.close()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges


def test_lif06_qt_synthesized_wheel_modifiers_logical_hidpi_coords_and_panzoom(monkeypatch):
    _, QtCore, QtGui, _ = _qt_modules()
    from vispy import _dawn, app, keys, scene

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')
    qt = QtCore.Qt

    sc = scene.SceneCanvas(app='pyqt6', size=(160, 120), show=False, vsync=False, bgcolor='black')
    view = sc.central_widget.add_view()
    cam = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, 160.0, 120.0))
    view.camera = cam
    rect_vis = scene.visuals.Rectangle(
        center=(80.0, 60.0), width=40.0, height=30.0, color=(0.0, 1.0, 0.25, 1.0), parent=view.scene
    )
    assert rect_vis is not None

    wheel_log = []
    key_log = []
    accept_flag = [True]

    @sc.events.mouse_wheel.connect
    def _record_wheel(ev):
        assert not ev.native.spontaneous(), 'physical HID is out of scope; expected synthesized QEvent'
        wheel_log.append((tuple(ev.pos), tuple(ev.delta), tuple(ev.modifiers)))
        ev.handled = accept_flag[0]

    @sc.events.key_press.connect
    def _record_key(ev):
        assert not ev.native.spontaneous()
        key_log.append((ev.key, ev.text, tuple(ev.modifiers)))
        ev.handled = accept_flag[0]

    try:
        sc.show()
        _pump_until(application, _dawn, lambda: sc.native._dawn_shown, desc='SceneCanvas shown')
        sc.update()
        application.process_events()
        _drain_idle(application, _dawn)

        widget = sc.native

        # 1) Modifier combinations + wheel delta axes + accepted/ignored propagation.
        mod_combo = (
            qt.KeyboardModifier.ShiftModifier
            | qt.KeyboardModifier.ControlModifier
            | qt.KeyboardModifier.AltModifier
        )
        local_pt = QtCore.QPointF(40.0, 30.0)
        global_pt = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(40, 30)))

        accept_flag[0] = True
        ev_diag = QtGui.QWheelEvent(
            local_pt,
            global_pt,
            QtCore.QPoint(),
            QtCore.QPoint(120, -240),
            qt.MouseButton.NoButton,
            mod_combo,
            qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QtCore.QCoreApplication.sendEvent(widget, ev_diag)
        assert ev_diag.isAccepted() is True
        assert wheel_log[-1][0] == (40, 30)
        np.testing.assert_allclose(wheel_log[-1][1], (1.0, -2.0))
        assert set(wheel_log[-1][2]) == {keys.SHIFT, keys.CONTROL, keys.ALT}

        # Key press with Meta/Control modifier and unhandled propagation check.
        accept_flag[0] = False
        key_ev = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            qt.Key.Key_K,
            qt.KeyboardModifier.MetaModifier | qt.KeyboardModifier.ShiftModifier,
            'K',
        )
        QtCore.QCoreApplication.sendEvent(widget, key_ev)
        assert key_ev.isAccepted() is False
        assert key_log[-1][0] == keys.Key('K')
        assert set(key_log[-1][2]) == {keys.META, keys.SHIFT}

        # 2) Cursor-anchored PanZoomCamera wheel zoom under logical vs simulated 2x HiDPI scale.
        cam.rect = (0.0, 0.0, 160.0, 120.0)
        anchor_px = (40, 30)
        # Map anchor logical pixel to world coords before zoom: (x=40, y_bottom_up = 120 - 30 = 90).
        anchor_world_before = (
            cam.rect.left + (anchor_px[0] / 160.0) * cam.rect.width,
            cam.rect.bottom + ((120.0 - anchor_px[1]) / 120.0) * cam.rect.height,
        )

        # Simulate 2x logical-to-physical scale override and verify logical event.pos remains (40, 30)
        # while physical framebuffer doubles to (320, 240).
        widget._dawn_ratio_override = 2.0
        widget.resizeGL(widget.width(), widget.height())
        application.process_events()
        _drain_idle(application, _dawn)
        assert sc.size == (160, 120)
        assert sc.physical_size == (320, 240)
        assert sc.pixel_scale == pytest.approx(2.0)

        accept_flag[0] = True
        wheel_zoom = QtGui.QWheelEvent(
            QtCore.QPointF(*anchor_px),
            QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(*anchor_px))),
            QtCore.QPoint(),
            QtCore.QPoint(0, 240),
            qt.MouseButton.NoButton,
            qt.KeyboardModifier.NoModifier,
            qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QtCore.QCoreApplication.sendEvent(widget, wheel_zoom)
        application.process_events()
        _drain_idle(application, _dawn)

        assert wheel_log[-1][0] == anchor_px
        assert cam.rect.width < 160.0 and cam.rect.height < 120.0
        anchor_world_after = (
            cam.rect.left + (anchor_px[0] / 160.0) * cam.rect.width,
            cam.rect.bottom + ((120.0 - anchor_px[1]) / 120.0) * cam.rect.height,
        )
        np.testing.assert_allclose(anchor_world_after, anchor_world_before, atol=1.5)

        img = sc.render(alpha=True)
        assert img.shape == (240, 320, 4)
        assert int(img[..., 1].max()) > 200
    finally:
        if not sc._closed:
            sc.close()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges


def test_lif06_qt_turntable_camera_drag_and_wheel_zoom_route(monkeypatch):
    _, QtCore, QtGui, _ = _qt_modules()
    from vispy import _dawn, app, scene

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')
    qt = QtCore.Qt

    sc = scene.SceneCanvas(app='pyqt6', size=(120, 96), show=False, vsync=False, bgcolor='black')
    view = sc.central_widget.add_view()
    cam = scene.cameras.TurntableCamera(fov=45.0, azimuth=25.0, elevation=20.0, distance=4.0, scale_factor=2.5)
    view.camera = cam
    box = scene.visuals.Box(
        width=1.0, height=0.8, depth=1.2, color=(0.9, 0.2, 0.1, 1.0), edge_color='white', parent=view.scene
    )
    assert box is not None

    try:
        sc.show()
        _pump_until(application, _dawn, lambda: sc.native._dawn_shown, desc='Turntable SceneCanvas shown')
        sc.update()
        application.process_events()
        _drain_idle(application, _dawn)

        img_before = sc.render(alpha=True)
        az_before, el_before, sf_before = cam.azimuth, cam.elevation, cam.scale_factor

        widget = sc.native
        p_start = QtCore.QPointF(30.0, 30.0)
        p_end = QtCore.QPointF(85.0, 65.0)
        g_start = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(30, 30)))
        g_end = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(85, 65)))

        QtCore.QCoreApplication.sendEvent(
            widget,
            QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonPress,
                p_start,
                g_start,
                qt.MouseButton.LeftButton,
                qt.MouseButton.LeftButton,
                qt.KeyboardModifier.NoModifier,
            ),
        )
        # Clear BaseCanvasBackend._vispy_mouse_move 10 ms throttle deterministically.
        widget._last_time = 0.0
        QtCore.QCoreApplication.sendEvent(
            widget,
            QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                p_end,
                g_end,
                qt.MouseButton.NoButton,
                qt.MouseButton.LeftButton,
                qt.KeyboardModifier.NoModifier,
            ),
        )
        QtCore.QCoreApplication.sendEvent(
            widget,
            QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonRelease,
                p_end,
                g_end,
                qt.MouseButton.LeftButton,
                qt.MouseButton.NoButton,
                qt.KeyboardModifier.NoModifier,
            ),
        )
        assert cam.azimuth != pytest.approx(az_before) or cam.elevation != pytest.approx(el_before)

        QtCore.QCoreApplication.sendEvent(
            widget,
            QtGui.QWheelEvent(
                p_end,
                g_end,
                QtCore.QPoint(),
                QtCore.QPoint(0, 240),
                qt.MouseButton.NoButton,
                qt.KeyboardModifier.NoModifier,
                qt.ScrollPhase.NoScrollPhase,
                False,
            ),
        )
        assert cam.scale_factor < sf_before

        application.process_events()
        _drain_idle(application, _dawn)
        img_after = sc.render(alpha=True)
        assert not np.array_equal(img_before, img_after)
    finally:
        if not sc._closed:
            sc.close()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges
