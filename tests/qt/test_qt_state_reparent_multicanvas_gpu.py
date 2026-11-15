# -*- coding: utf-8 -*-
"""Qt GPU lifecycle tests for LIF-01, LIF-02, LIF-03, and LIF-04.

Scope boundary:
- LIF-01 covers deterministic simulated device loss (`_dawn.lose_device()`),
  injected submission-stage faults (`_dawn.diagnostic_submission_controls`),
  and explicit WSI surface detach/reattach (`_dawn.clear_surface` + `_dawn_surface`);
  uncontrolled hardware TDR/driver reset storms are outside synthetic scope.
- Cross-platform Qt assertions use `VISPY_QT_PRESENTATION=readback` so both
  Windows hardware Vulkan and headless-repair WSL Lavapipe (`9c5`, which omits
  `VK_KHR_xlib_surface`) run identical assertions, while Win32 hardware Vulkan
  additionally exercises native Win32 swapchain reattachment and `read_presented`.
"""

import gc
import os
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

VERT_SRC = """
attribute vec2 a_position;
varying vec2 v_uv;
void main() {
    v_uv = a_position * 0.5 + 0.5;
    gl_Position = vec4(a_position, 0.0, 1.0);
}
"""

FRAG_COLOR_SRC = """
uniform vec4 u_color;
void main() {
    gl_FragColor = u_color;
}
"""

FRAG_TEX_SRC = """
uniform sampler2D u_tex;
uniform vec4 u_tint;
varying vec2 v_uv;
void main() {
    gl_FragColor = texture2D(u_tex, v_uv) * u_tint;
}
"""


def _qt_modules():
    PyQt6 = pytest.importorskip('PyQt6')
    from PyQt6 import QtCore, QtGui, QtWidgets, sip
    return PyQt6, QtCore, QtGui, QtWidgets, sip


def _pump_until(application, _dawn, predicate, timeout=5.0, desc='Qt/Dawn condition'):
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
        lambda: not any(
            _dawn.probe()[k] for k in ('pending_tickets', 'queued_frames')
        ),
        timeout=timeout,
        desc='Dawn idle retirement',
    )


def _grab_qwidget_rgba(widget, QtGui):
    qimg = widget.grab().toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.bits()
    ptr.setsize(qimg.sizeInBytes())
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, qimg.bytesPerLine()))
    return arr[:, : w * 4].reshape((h, w, 4)).copy()


def _ten_gauges(_dawn):
    probe = _dawn.probe()
    return {name: int(probe[name]) for name in TEN_GAUGES}


def test_lif01_simulated_device_loss_and_submission_fault_recovery_boundary(monkeypatch):
    _, QtCore, QtGui, QtWidgets, sip = _qt_modules()
    from vispy import _dawn, app, gloo

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')
    qapp = application.native
    assert QtWidgets.QApplication.instance() is qapp

    full_tri = np.array([[-1.0, -1.0], [3.0, -1.0], [-1.0, 3.0]], dtype=np.float32)
    color = [1.0, 0.0, 0.0, 1.0]
    draws = []

    canvas = app.Canvas(
        app='pyqt6', size=(64, 48), decorate=False, show=False, vsync=False, config={'samples': 0}
    )
    program = gloo.Program(VERT_SRC, FRAG_COLOR_SRC)
    vbo = gloo.VertexBuffer(full_tri)
    program['a_position'] = vbo

    @canvas.connect
    def on_draw(event):
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        program['u_color'] = color
        program.draw('triangles')
        draws.append(tuple(color))

    try:
        canvas.show()
        _pump_until(application, _dawn, lambda: len(draws) >= 1, desc='initial LIF-01 paint')
        _drain_idle(application, _dawn)

        canvas.set_current()
        px_initial = gloo.read_pixels(alpha=True)
        assert px_initial.shape == (48, 64, 4)
        np.testing.assert_allclose(px_initial[24, 32], [255, 0, 0, 255], atol=1)
        grab_initial = _grab_qwidget_rgba(canvas.native, QtGui)
        np.testing.assert_allclose(grab_initial[24, 32], [255, 0, 0, 255], atol=2)

        # 1) Deterministic submission-stage fault injection and clean recovery.
        _dawn.diagnostic_submission_controls(False, 'before-submit')
        try:
            canvas.set_current()
            gloo.clear(color=(0.2, 0.4, 0.6, 1.0))
            with pytest.raises(RuntimeError):
                canvas.context.finish()
        finally:
            _dawn.diagnostic_submission_controls(False, '')

        # 2) Simulated device loss rebuilds live VBO + shader pipeline cleanly on next frame.
        info_before = _dawn.device_info()
        probe_before = _dawn.probe()
        _dawn.lose_device()
        info_after = _dawn.device_info()
        probe_after = _dawn.probe()
        assert info_after['ok'] is True
        assert int(info_after['loss_count']) == int(info_before['loss_count']) + 1
        assert int(probe_after['device_generation']) > int(probe_before['device_generation'])

        color[:] = [0.0, 1.0, 0.0, 1.0]
        before_draws = len(draws)
        canvas.update()
        _pump_until(application, _dawn, lambda: len(draws) > before_draws, desc='post-loss LIF-01 paint')
        _drain_idle(application, _dawn)

        canvas.set_current()
        px_recovered = gloo.read_pixels(alpha=True)
        np.testing.assert_allclose(px_recovered[24, 32], [0, 255, 0, 255], atol=1)
        grab_recovered = _grab_qwidget_rgba(canvas.native, QtGui)
        np.testing.assert_allclose(grab_recovered[24, 32], [0, 255, 0, 255], atol=2)
        assert int(_dawn.probe()['device_generation']) == int(probe_after['device_generation'])
    finally:
        program.delete()
        vbo.delete()
        if not canvas._closed:
            canvas.context.flush_commands()
            canvas.close()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    # 3) Hardware Win32 WSI swapchain detach/loss/reattach boundary when supported.
    dev_info = _dawn.device_info()
    if sys.platform == 'win32' and not bool(dev_info.get('software')):
        monkeypatch.setenv('VISPY_QT_PRESENTATION', 'native')
        wsi_draws = []
        wsi_color = [0.0, 0.0, 1.0, 1.0]
        wsi_canvas = app.Canvas(
            app='pyqt6', size=(48, 32), decorate=False, show=False, vsync=False, config={'samples': 0}
        )
        cid = int(wsi_canvas.native._dawn_canvas_id)

        @wsi_canvas.connect
        def on_draw(event):
            gloo.set_viewport(0, 0, *wsi_canvas.physical_size)
            gloo.clear(color=wsi_color)
            wsi_draws.append(tuple(wsi_color))

        try:
            wsi_canvas.show()
            _pump_until(application, _dawn, lambda: len(wsi_draws) >= 1, desc='initial Win32 WSI paint')
            _drain_idle(application, _dawn)
            assert _dawn.benchmark_surface_info(cid)['attached'] is True
            w, h = wsi_canvas.physical_size
            presented_blue = np.asarray(_dawn.read_presented(cid, 0, 0, w, h)).copy()
            # BGRA layout from read_presented: blue=(255, 0, 0, 255)
            np.testing.assert_allclose(presented_blue[h // 2, w // 2], [255, 0, 0, 255], atol=2)

            # Detach surface + lose device must invalidate stale presented capture.
            _dawn.clear_surface(cid)
            assert _dawn.benchmark_surface_info(cid)['attached'] is False
            with pytest.raises(RuntimeError):
                _dawn.read_presented(cid, 0, 0, w, h)

            _dawn.lose_device()
            wsi_canvas.native._dawn_surface()
            wsi_canvas.native._configure_dawn_drawable(wsi_canvas.native.width(), wsi_canvas.native.height())
            assert _dawn.benchmark_surface_info(cid)['attached'] is True

            wsi_color[:] = [1.0, 1.0, 0.0, 1.0]
            prev = len(wsi_draws)
            wsi_canvas.update()
            _pump_until(application, _dawn, lambda: len(wsi_draws) > prev, desc='recovered Win32 WSI paint')
            _drain_idle(application, _dawn)
            presented_yellow = np.asarray(_dawn.read_presented(cid, 0, 0, w, h)).copy()
            # BGRA for yellow=(0, 255, 255, 255)
            np.testing.assert_allclose(presented_yellow[h // 2, w // 2], [0, 255, 255, 255], atol=2)
        finally:
            if not wsi_canvas._closed:
                wsi_canvas.close()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            application.process_events()
            gc.collect()
            _dawn.process_events()
    else:
        assert sys.platform != 'win32' or bool(dev_info.get('software')) is True

    gauges = _ten_gauges(_dawn)
    assert not any(gauges.values()), gauges


def test_lif02_reparenting_winid_change_and_shared_program_survival(monkeypatch):
    _, QtCore, QtGui, QtWidgets, sip = _qt_modules()
    from vispy import _dawn, app, gloo

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')

    hosts = [QtWidgets.QWidget() for _ in range(3)]
    layouts = [QtWidgets.QVBoxLayout(h) for h in hosts]
    destroyed_hosts = []
    for idx, (host, layout) in enumerate(zip(hosts, layouts)):
        host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        host.destroyed.connect(lambda _obj=None, idx=idx: destroyed_hosts.append(idx))
        host.resize(96 + idx * 16, 72 + idx * 12)
        layout.setContentsMargins(0, 0, 0, 0)

    sibling_host = QtWidgets.QWidget()
    sibling_layout = QtWidgets.QVBoxLayout(sibling_host)
    sibling_layout.setContentsMargins(0, 0, 0, 0)
    sibling_host.resize(80, 60)

    canvas = app.Canvas(app='pyqt6', parent=hosts[0], size=(64, 48), show=False, vsync=False)
    sibling = app.Canvas(app='pyqt6', parent=sibling_host, size=(64, 48), show=False, vsync=False, shared=canvas)
    layouts[0].addWidget(canvas.native)
    sibling_layout.addWidget(sibling.native)

    quad = np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    shared_vbo = gloo.VertexBuffer(quad)
    tex_data = np.full((4, 4, 4), [255, 0, 0, 255], dtype=np.uint8)
    shared_tex = gloo.Texture2D(tex_data)

    prog_main = gloo.Program(VERT_SRC, FRAG_TEX_SRC)
    prog_main['a_position'] = shared_vbo
    prog_main['u_tex'] = shared_tex
    prog_main['u_tint'] = (1.0, 1.0, 1.0, 1.0)

    prog_sib = gloo.Program(VERT_SRC, FRAG_TEX_SRC)
    prog_sib['a_position'] = shared_vbo
    prog_sib['u_tex'] = shared_tex
    prog_sib['u_tint'] = (1.0, 1.0, 1.0, 1.0)

    draws_main, draws_sib, observed_events = [], [], []

    class _Filter(QtCore.QObject):
        def eventFilter(self, receiver, event):
            if event.type() in (QtCore.QEvent.Type.WinIdChange, QtCore.QEvent.Type.ParentChange):
                observed_events.append(event.type())
            return False

    ev_filter = _Filter()
    canvas.native.installEventFilter(ev_filter)

    @canvas.connect
    def on_draw(event):
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog_main.draw('triangle_strip')
        draws_main.append(1)

    @sibling.connect
    def on_draw(event):
        gloo.set_viewport(0, 0, *sibling.physical_size)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog_sib.draw('triangle_strip')
        draws_sib.append(1)

    try:
        hosts[0].show()
        sibling_host.show()
        _pump_until(application, _dawn, lambda: len(draws_main) >= 1 and len(draws_sib) >= 1, desc='initial reparent draw')
        _drain_idle(application, _dawn)

        # Force native window ID creation on the child widget so reparenting across top-level hosts triggers WinIdChange.
        winid_before = observed_events.count(QtCore.QEvent.Type.WinIdChange)
        _ = int(canvas.native.winId())

        stage_colors = [
            ([0, 255, 0, 255], 1),
            ([0, 128, 255, 255], 2),
        ]
        for rgba, next_idx in stage_colors:
            hosts[next_idx].show()
            layouts[next_idx - 1].removeWidget(canvas.native)
            layouts[next_idx].addWidget(canvas.native)
            canvas.native.show()
            hosts[next_idx - 1].close()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            _pump_until(application, _dawn, lambda idx=next_idx - 1: idx in destroyed_hosts, desc='old host deletion')

            shared_tex.set_data(np.full((4, 4, 4), rgba, dtype=np.uint8))
            m_prev, s_prev = len(draws_main), len(draws_sib)
            canvas.update()
            sibling.update()
            _pump_until(
                application,
                _dawn,
                lambda: len(draws_main) > m_prev and len(draws_sib) > s_prev,
                desc=f'reparent stage {next_idx} draw',
            )
            _drain_idle(application, _dawn)

            canvas.set_current()
            px_m = gloo.read_pixels(alpha=True)
            np.testing.assert_allclose(px_m[px_m.shape[0] // 2, px_m.shape[1] // 2], rgba, atol=2)

            sibling.set_current()
            px_s = gloo.read_pixels(alpha=True)
            np.testing.assert_allclose(px_s[px_s.shape[0] // 2, px_s.shape[1] // 2], rgba, atol=2)

        assert observed_events.count(QtCore.QEvent.Type.ParentChange) >= 2
        assert observed_events.count(QtCore.QEvent.Type.WinIdChange) > winid_before
        assert destroyed_hosts == [0, 1]
    finally:
        canvas.native.removeEventFilter(ev_filter)
        prog_main.delete()
        prog_sib.delete()
        shared_vbo.delete()
        shared_tex.delete()
        if not sibling._closed:
            sibling.context.flush_commands()
            sibling.close()
        if not canvas._closed:
            canvas.context.flush_commands()
            canvas.close()
        if not sip.isdeleted(sibling_host):
            sibling_host.close()
            sibling_host.deleteLater()
        for host in hosts:
            if not sip.isdeleted(host):
                host.close()
                host.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    assert not any(gauges.values()), gauges


def test_lif03_minimized_and_zero_size_zero_submit_suppression_and_recovery(monkeypatch):
    _, QtCore, QtGui, QtWidgets, sip = _qt_modules()
    from vispy import _dawn, app, gloo

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')

    host = QtWidgets.QWidget()
    host.resize(120, 90)
    canvas = app.Canvas(app='pyqt6', parent=host, size=(80, 60), show=False, vsync=False)
    widget = canvas.native
    widget.setGeometry(0, 0, 80, 60)
    cid = int(widget._dawn_canvas_id)

    color = [1.0, 0.25, 0.0, 1.0]
    draws = []

    @canvas.connect
    def on_draw(event):
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color=color)
        draws.append(tuple(canvas.physical_size))

    try:
        host.show()
        widget.show()
        _pump_until(application, _dawn, lambda: len(draws) >= 1, desc='initial LIF-03 paint')
        _drain_idle(application, _dawn)

        cfg0 = _dawn.framebuffer_config(cid)
        assert cfg0['width'] > 0 and cfg0['height'] > 0

        # Part A: Explicit 0x0 resize collapses Dawn target to empty (0x0) and issues 0 submits/presents.
        widget.setFixedSize(0, 0)
        application.process_events()
        _drain_idle(application, _dawn)
        assert widget.width() == 0 and widget.height() == 0
        with pytest.raises(RuntimeError, match='empty canvas target'):
            _dawn.framebuffer_config(cid)

        probe_before_zero = _dawn.probe()
        draws_before_zero = len(draws)
        for _ in range(5):
            canvas.update()
            QtCore.QCoreApplication.sendEvent(widget, QtGui.QPaintEvent(QtCore.QRect(0, 0, 0, 0)))
            application.process_events()
            _dawn.process_events()
        probe_after_zero = _dawn.probe()
        assert len(draws) == draws_before_zero
        assert probe_after_zero['dawn_queue_submits'] == probe_before_zero['dawn_queue_submits']
        assert probe_after_zero['application_presents'] == probe_before_zero['application_presents']
        assert probe_after_zero['pending_tickets'] == 0
        assert probe_after_zero['queued_frames'] == 0

        # Restore non-zero geometry and verify exact rendered pixels recover.
        color[:] = [0.0, 0.75, 0.25, 1.0]
        widget.setMinimumSize(0, 0)
        widget.setMaximumSize(16777215, 16777215)
        widget.resize(96, 64)
        widget.update()
        _pump_until(
            application,
            _dawn,
            lambda: len(draws) > draws_before_zero,
            desc='recovery from 0x0 resize',
        )
        _drain_idle(application, _dawn)
        assert _dawn.framebuffer_config(cid)['width'] >= 96
        canvas.set_current()
        px_restored = gloo.read_pixels(alpha=True)
        assert px_restored.shape[0] >= 64 and px_restored.shape[1] >= 96
        np.testing.assert_allclose(px_restored[32, 48], [0, 191, 64, 255], atol=2)

        # Part B: Minimized window state suspends drawable to empty (0x0) and suppresses submits until restored.
        top_canvas = app.Canvas(app='pyqt6', size=(72, 54), show=False, vsync=False)
        top_widget = top_canvas.native
        top_cid = int(top_widget._dawn_canvas_id)
        top_draws = []
        top_color = [0.5, 0.0, 1.0, 1.0]

        @top_canvas.connect
        def on_draw(event):
            gloo.set_viewport(0, 0, *top_canvas.physical_size)
            gloo.clear(color=top_color)
            top_draws.append(1)

        try:
            top_canvas.show()
            _pump_until(application, _dawn, lambda: len(top_draws) >= 1, desc='initial top-level LIF-03 paint')
            _drain_idle(application, _dawn)

            top_widget.showMinimized()
            application.process_events()
            # Bare Xvfb has no window manager to set _NET_WM_STATE_HIDDEN; ensure WindowStateChange path runs deterministically.
            forced_minimized = False
            orig_is_minimized = top_widget.isMinimized
            if not top_widget.isMinimized():
                forced_minimized = True
                monkeypatch.setattr(top_widget, 'isMinimized', lambda: True)
                QtCore.QCoreApplication.sendEvent(
                    top_widget,
                    QtGui.QWindowStateChangeEvent(QtCore.Qt.WindowState.WindowNoState),
                )
                application.process_events()

            _drain_idle(application, _dawn)
            with pytest.raises(RuntimeError, match='empty canvas target'):
                _dawn.framebuffer_config(top_cid)

            p_min_before = _dawn.probe()
            d_min_before = len(top_draws)
            for _ in range(4):
                top_canvas.update()
                QtCore.QCoreApplication.sendEvent(top_widget, QtGui.QPaintEvent(top_widget.rect()))
                application.process_events()
                _dawn.process_events()
            p_min_after = _dawn.probe()
            assert len(top_draws) == d_min_before
            assert p_min_after['dawn_queue_submits'] == p_min_before['dawn_queue_submits']
            assert p_min_after['application_presents'] == p_min_before['application_presents']

            top_color[:] = [1.0, 0.5, 0.0, 1.0]
            if forced_minimized:
                monkeypatch.setattr(top_widget, 'isMinimized', orig_is_minimized)
                QtCore.QCoreApplication.sendEvent(
                    top_widget,
                    QtGui.QWindowStateChangeEvent(QtCore.Qt.WindowState.WindowMinimized),
                )
            else:
                top_widget.showNormal()
            top_canvas.update()
            _pump_until(
                application,
                _dawn,
                lambda: len(top_draws) > d_min_before,
                desc='restore from minimized state',
            )
            _drain_idle(application, _dawn)
            assert _dawn.framebuffer_config(top_cid)['width'] > 0
            top_canvas.set_current()
            px_top = gloo.read_pixels(alpha=True)
            np.testing.assert_allclose(px_top[px_top.shape[0] // 2, px_top.shape[1] // 2], [255, 128, 0, 255], atol=2)
        finally:
            if not top_canvas._closed:
                top_canvas.close()
    finally:
        if not canvas._closed:
            canvas.close()
        if not sip.isdeleted(host):
            host.close()
            host.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    assert not any(gauges.values()), gauges


def test_lif04_multicanvas_parent_destruction_while_shared_siblings_keep_rendering(monkeypatch):
    _, QtCore, QtGui, QtWidgets, sip = _qt_modules()
    from vispy import _dawn, app, gloo

    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')

    doomed_host = QtWidgets.QWidget()
    doomed_host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
    doomed_layout = QtWidgets.QHBoxLayout(doomed_host)
    doomed_layout.setContentsMargins(0, 0, 0, 0)
    doomed_host.resize(140, 60)

    survivor_host = QtWidgets.QWidget()
    survivor_host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
    survivor_layout = QtWidgets.QHBoxLayout(survivor_host)
    survivor_layout.setContentsMargins(0, 0, 0, 0)
    survivor_host.resize(140, 60)

    survivor_a = app.Canvas(app='pyqt6', parent=survivor_host, size=(64, 48), show=False, vsync=False)
    survivor_b = app.Canvas(
        app='pyqt6', parent=survivor_host, size=(64, 48), show=False, vsync=False, shared=survivor_a
    )
    doomed_a = app.Canvas(
        app='pyqt6', parent=doomed_host, size=(64, 48), show=False, vsync=False, shared=survivor_a
    )
    doomed_b = app.Canvas(
        app='pyqt6', parent=doomed_host, size=(64, 48), show=False, vsync=False, shared=survivor_a
    )

    survivor_layout.addWidget(survivor_a.native)
    survivor_layout.addWidget(survivor_b.native)
    doomed_layout.addWidget(doomed_a.native)
    doomed_layout.addWidget(doomed_b.native)

    destroyed_names = []
    doomed_host.destroyed.connect(lambda _o=None: destroyed_names.append('doomed_host'))
    doomed_a.native.destroyed.connect(lambda _o=None: destroyed_names.append('doomed_a'))
    doomed_b.native.destroyed.connect(lambda _o=None: destroyed_names.append('doomed_b'))

    quad = np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    shared_vbo = gloo.VertexBuffer(quad)
    shared_tex = gloo.Texture2D(np.full((4, 4, 4), [255, 255, 255, 255], dtype=np.uint8))

    programs = {}
    tints = {
        'sa': [1.0, 0.0, 0.0, 1.0],
        'sb': [0.0, 1.0, 0.0, 1.0],
        'da': [0.0, 0.0, 1.0, 1.0],
        'db': [1.0, 1.0, 0.0, 1.0],
    }
    draw_counts = {'sa': 0, 'sb': 0, 'da': 0, 'db': 0}

    def _bind_canvas(key, c):
        prog = gloo.Program(VERT_SRC, FRAG_TEX_SRC)
        prog['a_position'] = shared_vbo
        prog['u_tex'] = shared_tex
        programs[key] = prog

        @c.connect
        def on_draw(event, key=key, c=c, prog=prog):
            if key not in programs:
                return
            gloo.set_viewport(0, 0, *c.physical_size)
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            prog['u_tint'] = tints[key]
            prog.draw('triangle_strip')
            draw_counts[key] += 1

    _bind_canvas('sa', survivor_a)
    _bind_canvas('sb', survivor_b)
    _bind_canvas('da', doomed_a)
    _bind_canvas('db', doomed_b)

    try:
        survivor_host.show()
        doomed_host.show()
        _pump_until(
            application,
            _dawn,
            lambda: all(v >= 1 for v in draw_counts.values()),
            desc='initial 4-canvas draw',
        )
        _drain_idle(application, _dawn)
        bytes_four_canvases = int(_dawn.probe()['canvas_texture_bytes'])
        assert bytes_four_canvases > 0

        # Queue updates on both doomed and surviving siblings, then destroy doomed_host immediately.
        doomed_a.update()
        doomed_b.update()
        survivor_a.update()
        survivor_b.update()
        programs.pop('da').delete()
        programs.pop('db').delete()
        doomed_host.close()
        doomed_host.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        _pump_until(
            application,
            _dawn,
            lambda: {'doomed_host', 'doomed_a', 'doomed_b'}.issubset(destroyed_names),
            desc='doomed parent & child destruction',
        )
        _drain_idle(application, _dawn)

        assert doomed_a._closed is True
        assert doomed_b._closed is True
        assert survivor_a._closed is False
        assert survivor_b._closed is False
        bytes_two_canvases = int(_dawn.probe()['canvas_texture_bytes'])
        assert 0 < bytes_two_canvases < bytes_four_canvases

        # Mutate shared GPU resources and prove surviving sibling canvases keep rendering accurately.
        shared_tex.set_data(np.full((4, 4, 4), [128, 255, 255, 255], dtype=np.uint8))
        tints['sa'] = [1.0, 0.5, 0.0, 1.0]
        tints['sb'] = [0.0, 1.0, 0.5, 1.0]
        prev_sa, prev_sb = draw_counts['sa'], draw_counts['sb']
        survivor_a.update()
        survivor_b.update()
        _pump_until(
            application,
            _dawn,
            lambda: draw_counts['sa'] > prev_sa and draw_counts['sb'] > prev_sb,
            desc='post-destruction survivor sibling draw',
        )
        _drain_idle(application, _dawn)

        survivor_a.set_current()
        px_sa = gloo.read_pixels(alpha=True)
        # [128, 255, 255, 255] * [1.0, 0.5, 0.0, 1.0] -> [128, 128, 0, 255]
        np.testing.assert_allclose(px_sa[px_sa.shape[0] // 2, px_sa.shape[1] // 2], [128, 128, 0, 255], atol=2)

        survivor_b.set_current()
        px_sb = gloo.read_pixels(alpha=True)
        # [128, 255, 255, 255] * [0.0, 1.0, 0.5, 1.0] -> [0, 255, 128, 255]
        np.testing.assert_allclose(px_sb[px_sb.shape[0] // 2, px_sb.shape[1] // 2], [0, 255, 128, 255], atol=2)
    finally:
        for k, prog in list(programs.items()):
            programs.pop(k, None)
            prog.delete()
        shared_vbo.delete()
        shared_tex.delete()
        for c in (survivor_b, survivor_a, doomed_a, doomed_b):
            if not c._closed:
                c.context.flush_commands()
                c.close()
        for h in (doomed_host, survivor_host):
            if not sip.isdeleted(h):
                h.close()
                h.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    assert not any(gauges.values()), gauges
