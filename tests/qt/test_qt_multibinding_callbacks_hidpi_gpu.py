# -*- coding: utf-8 -*-
"""Multi-binding Qt (PyQt5, PyQt6, PySide6) GPU lifecycle, input & fractional HiDPI tests.

Scope boundaries (W3-2: LIF-02, LIF-03, LIF-04, LIF-06, single-display LIF-08):
- Executed in isolated per-binding subprocesses (`VISPY_TEST_QT_BINDING` in
  `{'pyqt5', 'pyqt6', 'pyside6'}`) with zero competing Qt binding modules loaded
  in `sys.modules`.
- Input events are toolkit-synthesized (`event.native.spontaneous() is False`);
  physical HID devices are not claimed (`physical_hid_claimed = False`).
- `LIF-08` covers programmatic single-display fractional HiDPI (`QT_SCALE_FACTOR=1.5`,
  `pixel_scale == 1.5`); physical multi-monitor window drag transitions are not
  claimed (`physical_multimonitor_claimed = False`).
"""

from __future__ import annotations

import gc
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu

BINDING_TO_PKG = {
    'pyqt5': 'PyQt5',
    'pyqt6': 'PyQt6',
    'pyside6': 'PySide6',
}
ALL_QT_PACKAGES = ('PyQt4', 'PyQt5', 'PyQt6', 'PySide', 'PySide2', 'PySide6')

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


def _selected_binding() -> str:
    raw = (
        os.environ.get('VISPY_TEST_QT_BINDING')
        or os.environ.get('QT_API')
        or 'pyqt6'
    ).strip().lower()
    if raw not in BINDING_TO_PKG:
        raise RuntimeError(f'Unsupported VISPY_TEST_QT_BINDING={raw!r}; expected one of { sorted(BINDING_TO_PKG) }')
    return raw


def _competing_qt_modules(expected_pkg: str) -> list[str]:
    found = []
    for mod_name in sorted(sys.modules):
        for pkg in ALL_QT_PACKAGES:
            if pkg != expected_pkg and (mod_name == pkg or mod_name.startswith(pkg + '.')):
                found.append(mod_name)
    return found


def _assert_binding_isolation(binding: str) -> str:
    expected_pkg = BINDING_TO_PKG[binding]
    competing = _competing_qt_modules(expected_pkg)
    assert not competing, f'Competing Qt modules loaded in {binding} process: {competing}'
    return expected_pkg


def _activate_binding():
    binding = _selected_binding()
    expected_pkg = _assert_binding_isolation(binding)
    from vispy import _dawn, app

    application = app.use_app(binding)
    assert application.backend_name.lower() == binding
    QtCore = importlib.import_module(f'{expected_pkg}.QtCore')
    QtGui = importlib.import_module(f'{expected_pkg}.QtGui')
    QtWidgets = importlib.import_module(f'{expected_pkg}.QtWidgets')
    QtTest = importlib.import_module(f'{expected_pkg}.QtTest')
    assert f'{expected_pkg}.QtCore' in sys.modules
    _assert_binding_isolation(binding)
    qapp = application.native
    assert QtWidgets.QApplication.instance() is qapp
    return binding, expected_pkg, application, _dawn, QtCore, QtGui, QtWidgets, QtTest


def _qevent_type(QtCore, name: str):
    t_ns = getattr(QtCore.QEvent, 'Type', None)
    if t_ns is not None and hasattr(t_ns, name):
        return getattr(t_ns, name)
    return getattr(QtCore.QEvent, name)


def _qt_enum(QtCore, scope: str, name: str):
    qt = QtCore.Qt
    scoped = getattr(qt, scope, None)
    if scoped is not None and hasattr(scoped, name):
        return getattr(scoped, name)
    return getattr(qt, name)


def _pump_until(application, _dawn, predicate, timeout: float = 5.0, desc: str = 'Qt/Dawn condition') -> None:
    deadline = time.monotonic() + timeout
    while True:
        application.process_events()
        _dawn.process_events()
        if predicate():
            return
        assert time.monotonic() < deadline, f'Timed out waiting for {desc}'
        time.sleep(0.002)


def _drain_idle(application, _dawn, timeout: float = 5.0) -> None:
    _pump_until(
        application,
        _dawn,
        lambda: not any(
            _dawn.probe()[k] for k in ('pending_tickets', 'queued_frames', 'line_resource_pool_busy_slots')
        ),
        timeout=timeout,
        desc='Dawn idle retirement',
    )


def _make_mouse_event(QtCore, QtGui, widget, ev_type_name: str, x: float, y: float, button, buttons, modifiers):
    ev_type = _qevent_type(QtCore, ev_type_name)
    local_pt = QtCore.QPointF(float(x), float(y))
    global_pt = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(int(round(x)), int(round(y)))))
    return QtGui.QMouseEvent(ev_type, local_pt, global_pt, button, buttons, modifiers)


def _make_wheel_event(QtCore, QtGui, widget, x: float, y: float, dx: int, dy: int, buttons, modifiers):
    local_pt = QtCore.QPointF(float(x), float(y))
    global_pt = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(int(round(x)), int(round(y)))))
    no_phase = _qt_enum(QtCore, 'ScrollPhase', 'NoScrollPhase')
    return QtGui.QWheelEvent(
        local_pt,
        global_pt,
        QtCore.QPoint(0, 0),
        QtCore.QPoint(int(dx), int(dy)),
        buttons,
        modifiers,
        no_phase,
        False,
    )


def _read_canvas_rgba(canvas, gloo) -> np.ndarray:
    canvas.set_current()
    return gloo.read_pixels(alpha=True)


def _quiesce_teardown(application, _dawn, QtCore) -> dict[str, int]:
    deferred_delete = _qevent_type(QtCore, 'DeferredDelete')
    QtCore.QCoreApplication.sendPostedEvents(None, deferred_delete)
    application.process_events()
    gc.collect()
    QtCore.QCoreApplication.sendPostedEvents(None, deferred_delete)
    application.process_events()
    _drain_idle(application, _dawn)
    probe = _dawn.probe()
    gauges = {k: int(probe[k]) for k in TEN_GAUGES}
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges
    return gauges


def test_qt_binding_callback_exception_hook_and_parent_key_guard(monkeypatch):
    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    binding, _pkg, application, _dawn, QtCore, QtGui, QtWidgets, _QtTest = _activate_binding()
    from vispy import app, gloo, keys, scene

    qapp = application.native
    qapp.setQuitOnLastWindowClosed(False)
    prev_hook = sys.excepthook

    parent_forwarded = []

    class _ForwardingParent(QtWidgets.QWidget):
        def keyPressEvent(self, ev):
            parent_forwarded.append('key_press')
            if child_widget_ref[0] is not None and canvas_ref[0] is not None:
                child_widget_ref[0]._keyEvent(canvas_ref[0].events.key_press, ev)

    key_press_type = _qevent_type(QtCore, 'KeyPress')
    filter_counts = {'parent': 0, 'child': 0}

    class _KeyReplayFilter(QtCore.QObject):
        def __init__(self, tag: str):
            super().__init__()
            self._tag = tag

        def eventFilter(self, _obj, ev):
            if ev.type() == key_press_type:
                filter_counts[self._tag] += 1
            return False

    parent_host = _ForwardingParent()
    parent_host.resize(160, 120)
    parent_layout = QtWidgets.QVBoxLayout(parent_host)
    parent_layout.setContentsMargins(0, 0, 0, 0)

    canvas = scene.SceneCanvas(
        app=binding, parent=parent_host, size=(120, 90), show=False, vsync=False, bgcolor=(0.05, 0.05, 0.05, 1.0)
    )
    view = canvas.central_widget.add_view()
    view.camera = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, 120.0, 90.0))
    rect_vis = scene.visuals.Rectangle(
        center=(60.0, 45.0), width=80.0, height=60.0, color=(1.0, 0.0, 0.0, 1.0), parent=view.scene
    )
    parent_layout.addWidget(canvas.native)
    child_widget_ref = [canvas.native]
    canvas_ref = [canvas]

    parent_filter = _KeyReplayFilter('parent')
    child_filter = _KeyReplayFilter('child')
    parent_host.installEventFilter(parent_filter)
    canvas.native.installEventFilter(child_filter)

    draws = [0]

    @canvas.events.draw.connect
    def _track_draw(_ev):
        draws[0] += 1

    probe_canvas = None
    orig_release = canvas.native._vispy_mouse_release
    try:
        parent_host.show()
        canvas.show()
        _pump_until(application, _dawn, lambda: draws[0] >= 1 and canvas.native._dawn_shown, desc='initial LIF-06 draw')
        _drain_idle(application, _dawn)

        px0 = _read_canvas_rgba(canvas, gloo)
        np.testing.assert_allclose(px0[px0.shape[0] // 2, px0.shape[1] // 2], [255, 0, 0, 255], atol=2)

        left_btn = _qt_enum(QtCore, 'MouseButton', 'LeftButton')
        no_btn = _qt_enum(QtCore, 'MouseButton', 'NoButton')
        no_mod = _qt_enum(QtCore, 'KeyboardModifier', 'NoModifier')

        # 1a) Exception inside canvas.events.mouse_press with default emitter containment
        #     AND with ignore_callback_errors=False + host sys.excepthook inside live Qt loop.
        contained_boom = RuntimeError('contained mouse_press callback failure')
        boom_calls = []

        def _fail_mouse_press(ev):
            assert not ev.native.spontaneous()
            boom_calls.append(tuple(ev.pos))
            raise contained_boom

        # Default VisPy emitter containment (ignore_callback_errors=True)
        canvas.events.mouse_press.ignore_callback_errors = True
        canvas.events.mouse_press.connect(_fail_mouse_press)
        ev_press_default = _make_mouse_event(
            QtCore, QtGui, canvas.native, 'MouseButtonPress', 30, 24, left_btn, left_btn, no_mod
        )
        QtCore.QCoreApplication.sendEvent(canvas.native, ev_press_default)
        application.process_events()
        assert boom_calls == [(30, 24)]
        assert not canvas.native._dawn_callback_failed

        # Host excepthook containment across real Qt exec loop with ignore_callback_errors=False
        hook_records = []

        def _host_excepthook(etype, value, tb):
            hook_records.append((etype, value, tb is not None))

        sys.excepthook = _host_excepthook
        canvas.events.mouse_press.ignore_callback_errors = False
        kept_events = []

        def _deliver_in_loop():
            ev = _make_mouse_event(
                QtCore, QtGui, canvas.native, 'MouseButtonPress', 44, 32, left_btn, left_btn, no_mod
            )
            kept_events.append(ev)
            QtCore.QCoreApplication.sendEvent(canvas.native, ev)

        QtCore.QTimer.singleShot(0, _deliver_in_loop)
        QtCore.QTimer.singleShot(12, lambda: qapp.exit(0))
        exec_fn = getattr(qapp, 'exec', None) or qapp.exec_
        assert exec_fn() == 0
        assert len(hook_records) == 1
        assert hook_records[0][0] is RuntimeError and hook_records[0][1] is contained_boom and hook_records[0][2]
        assert not canvas.native._dawn_callback_failed
        assert getattr(qapp, '_vispy_dawn_callback_error', None) is None

        canvas.events.mouse_press.disconnect(_fail_mouse_press)
        canvas.events.mouse_press.ignore_callback_errors = True
        sys.excepthook = prev_hook

        # Subsequent mouse press + GPU scene draw recovery on the same canvas
        subsequent_presses = []

        def _good_mouse_press(ev):
            subsequent_presses.append(tuple(ev.pos))
            ev.handled = True
            rect_vis.color = (0.0, 1.0, 0.0, 1.0)
            canvas.update()

        canvas.events.mouse_press.connect(_good_mouse_press)
        draws_before = draws[0]
        ev_good = _make_mouse_event(
            QtCore, QtGui, canvas.native, 'MouseButtonPress', 52, 40, left_btn, left_btn, no_mod
        )
        QtCore.QCoreApplication.sendEvent(canvas.native, ev_good)
        assert ev_good.isAccepted() is True
        _pump_until(application, _dawn, lambda: draws[0] > draws_before, desc='post-error green draw')
        _drain_idle(application, _dawn)
        assert subsequent_presses == [(52, 40)]
        px_green = _read_canvas_rgba(canvas, gloo)
        np.testing.assert_allclose(px_green[px_green.shape[0] // 2, px_green.shape[1] // 2], [0, 255, 0, 255], atol=2)

        # 2) Custom _vispy_mouse_release hook & raising hook behavior verified.
        custom_release_log = []

        def _custom_vispy_mouse_release(**kwargs):
            custom_release_log.append((tuple(kwargs['pos']), int(kwargs['button'])))
            res = orig_release(**kwargs)
            res.handled = True
            return res

        canvas.native._vispy_mouse_release = _custom_vispy_mouse_release
        ev_rel = _make_mouse_event(
            QtCore, QtGui, canvas.native, 'MouseButtonRelease', 52, 40, left_btn, no_btn, no_mod
        )
        QtCore.QCoreApplication.sendEvent(canvas.native, ev_rel)
        assert ev_rel.isAccepted() is True
        assert custom_release_log == [((52, 40), 1)]
        canvas.native._vispy_mouse_release = orig_release

        # Custom _vispy_mouse_release raising under a working host hook (canvas survives)
        rel_hook_err = RuntimeError('custom _vispy_mouse_release host-hook error')
        rel_hook_seen = []
        sys.excepthook = lambda et, val, _tb: rel_hook_seen.append((et, val))
        canvas.native._vispy_mouse_release = lambda **_kw: (_ for _ in ()).throw(rel_hook_err)
        ev_rel_fail1 = _make_mouse_event(
            QtCore, QtGui, canvas.native, 'MouseButtonRelease', 55, 41, left_btn, no_btn, no_mod
        )
        QtCore.QCoreApplication.sendEvent(canvas.native, ev_rel_fail1)
        assert rel_hook_seen == [(RuntimeError, rel_hook_err)]
        assert not canvas.native._dawn_callback_failed
        canvas.native._vispy_mouse_release = orig_release
        sys.excepthook = prev_hook

        # Raising sys.excepthook when _vispy_mouse_release raises on a disposable canvas:
        # broken hook is caught inside Qt virtual, original error surfaces from process_events(),
        # and primary canvas remains healthy and renders new color.
        probe_draws = [0]
        probe_canvas = app.Canvas(app=binding, size=(48, 36), show=False, vsync=False)

        @probe_canvas.connect
        def on_draw(_ev):
            gloo.set_viewport(0, 0, *probe_canvas.physical_size)
            gloo.clear(color=(0.2, 0.2, 0.8, 1.0))
            probe_draws[0] += 1

        probe_canvas.show()
        _pump_until(application, _dawn, lambda: probe_draws[0] >= 1, desc='probe_canvas initial draw')
        _drain_idle(application, _dawn)

        orig_probe_err = RuntimeError('probe _vispy_mouse_release failure')
        broken_hook_seen = []

        def _raising_excepthook(_et, val, _tb):
            broken_hook_seen.append(val)
            raise RuntimeError('broken excepthook boom')

        sys.excepthook = _raising_excepthook
        probe_canvas.native._vispy_mouse_release = lambda **_kw: (_ for _ in ()).throw(orig_probe_err)
        ev_probe_rel = _make_mouse_event(
            QtCore, QtGui, probe_canvas.native, 'MouseButtonRelease', 10, 10, left_btn, no_btn, no_mod
        )
        QtCore.QCoreApplication.sendEvent(probe_canvas.native, ev_probe_rel)
        assert broken_hook_seen == [orig_probe_err]
        assert probe_canvas.native._dawn_callback_failed is True
        assert ev_probe_rel.isAccepted() is False

        with pytest.raises(RuntimeError) as exc_info:
            application.process_events()
        assert exc_info.value is orig_probe_err
        sys.excepthook = prev_hook
        probe_canvas.close()
        probe_canvas = None

        draws_before_cyan = draws[0]
        rect_vis.color = (0.0, 0.75, 1.0, 1.0)
        canvas.update()
        _pump_until(application, _dawn, lambda: draws[0] > draws_before_cyan, desc='primary canvas cyan draw')
        _drain_idle(application, _dawn)
        px_cyan = _read_canvas_rgba(canvas, gloo)
        np.testing.assert_allclose(px_cyan[px_cyan.shape[0] // 2, px_cyan.shape[1] // 2], [0, 191, 255, 255], atol=2)

        # 3) Parent QWidget event filter confirms handled key events do not infinitely replay.
        key_events_received = []

        @canvas.events.key_press.connect
        def _on_key(ev):
            assert not ev.native.spontaneous()
            key_events_received.append((ev.key, ev.text))
            ev.handled = True

        filter_counts['parent'] = 0
        filter_counts['child'] = 0
        parent_forwarded.clear()

        key_a = _qt_enum(QtCore, 'Key', 'Key_A')
        qkey_a = QtGui.QKeyEvent(key_press_type, key_a, no_mod, 'a')
        QtCore.QCoreApplication.sendEvent(canvas.native, qkey_a)
        application.process_events()
        assert qkey_a.isAccepted() is True
        assert key_events_received == [(keys.Key('A'), 'a')]
        assert filter_counts['child'] == 1
        assert filter_counts['parent'] == 0
        assert parent_forwarded == []

        # Also send directly to forwarding parent and confirm exactly one delivery (zero replay loop).
        key_b = _qt_enum(QtCore, 'Key', 'Key_B')
        qkey_b = QtGui.QKeyEvent(key_press_type, key_b, no_mod, 'b')
        QtCore.QCoreApplication.sendEvent(parent_host, qkey_b)
        application.process_events()
        assert qkey_b.isAccepted() is True
        assert key_events_received == [(keys.Key('A'), 'a'), (keys.Key('B'), 'b')]
        assert filter_counts['parent'] == 1
        assert parent_forwarded == ['key_press']

        _assert_binding_isolation(binding)
    finally:
        sys.excepthook = prev_hook
        setattr(qapp, '_vispy_dawn_callback_error', None)
        canvas.native._vispy_mouse_release = orig_release
        canvas.native.removeEventFilter(child_filter)
        parent_host.removeEventFilter(parent_filter)
        child_widget_ref[0] = None
        canvas_ref[0] = None
        if probe_canvas is not None and not probe_canvas._closed:
            probe_canvas.close()
        if not canvas._closed:
            canvas.close()
        parent_host.close()
        parent_host.deleteLater()
        _quiesce_teardown(application, _dawn, QtCore)


def test_qt_binding_multicanvas_and_lineedit_focus_routing(monkeypatch):
    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    binding, _pkg, application, _dawn, QtCore, QtGui, QtWidgets, QtTest = _activate_binding()
    from vispy import gloo, keys, scene

    qapp = application.native
    host = QtWidgets.QWidget()
    host.setObjectName('multicanvas_focus_host')
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(4, 4, 4, 4)

    sc_a = scene.SceneCanvas(
        app=binding, parent=host, size=(120, 80), show=False, vsync=False, bgcolor=(0.1, 0.0, 0.0, 1.0)
    )
    view_a = sc_a.central_widget.add_view()
    view_a.camera = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, 120.0, 80.0))
    rect_a = scene.visuals.Rectangle(
        center=(60.0, 40.0), width=90.0, height=60.0, color=(1.0, 0.0, 0.0, 1.0), parent=view_a.scene
    )

    sc_b = scene.SceneCanvas(
        app=binding, parent=host, size=(120, 80), show=False, vsync=False, bgcolor=(0.0, 0.0, 0.1, 1.0)
    )
    view_b = sc_b.central_widget.add_view()
    view_b.camera = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, 120.0, 80.0))
    rect_b = scene.visuals.Rectangle(
        center=(60.0, 40.0), width=90.0, height=60.0, color=(0.0, 0.0, 1.0, 1.0), parent=view_b.scene
    )

    line_edit = QtWidgets.QLineEdit(host)
    line_edit.setObjectName('focus_line_edit')

    sc_a.native.setMinimumSize(120, 80)
    sc_b.native.setMinimumSize(120, 80)
    layout.addWidget(sc_a.native)
    layout.addWidget(sc_b.native)
    layout.addWidget(line_edit)

    draws = {'A': 0, 'B': 0}
    key_log: list[tuple[str, object, str]] = []

    @sc_a.events.draw.connect
    def _draw_a(_ev):
        draws['A'] += 1

    @sc_b.events.draw.connect
    def _draw_b(_ev):
        draws['B'] += 1

    a_palette = [(0.0, 1.0, 0.0, 1.0), (1.0, 0.5, 0.0, 1.0)]
    b_palette = [(1.0, 1.0, 0.0, 1.0)]
    a_presses = [0]
    b_presses = [0]

    @sc_a.events.key_press.connect
    def _key_a(ev):
        key_log.append(('A', ev.key, ev.text))
        ev.handled = True
        rect_a.color = a_palette[min(a_presses[0], len(a_palette) - 1)]
        a_presses[0] += 1
        sc_a.update()

    @sc_b.events.key_press.connect
    def _key_b(ev):
        key_log.append(('B', ev.key, ev.text))
        ev.handled = True
        rect_b.color = b_palette[min(b_presses[0], len(b_palette) - 1)]
        b_presses[0] += 1
        sc_b.update()

    def _center_rgba(sc) -> np.ndarray:
        px = _read_canvas_rgba(sc, gloo)
        return px[px.shape[0] // 2, px.shape[1] // 2]

    def _send_key_to_focused_host(qt_key, text: str) -> None:
        qapp.setActiveWindow(host)
        application.process_events()
        target = qapp.focusWidget() or host.focusWidget()
        assert target is not None
        win = host.windowHandle()
        no_mod = _qt_enum(QtCore, 'KeyboardModifier', 'NoModifier')
        if win is not None and hasattr(QtTest.QTest, 'keyClick'):
            before_log = len(key_log)
            before_txt = line_edit.text()
            QtTest.QTest.keyClick(win, qt_key, no_mod)
            application.process_events()
            if len(key_log) > before_log or line_edit.text() != before_txt:
                return
        # Fallback through host.focusWidget() if bare X11/QTest window dispatch ignored inactive top-level
        kp = QtGui.QKeyEvent(_qevent_type(QtCore, 'KeyPress'), qt_key, no_mod, text)
        kr = QtGui.QKeyEvent(_qevent_type(QtCore, 'KeyRelease'), qt_key, no_mod, text)
        QtCore.QCoreApplication.sendEvent(target, kp)
        QtCore.QCoreApplication.sendEvent(target, kr)
        application.process_events()

    try:
        host.resize(220, 240)
        host.show()
        sc_a.show()
        sc_b.show()
        host.activateWindow()
        qapp.setActiveWindow(host)
        _pump_until(
            application,
            _dawn,
            lambda: host.windowHandle() is not None and draws['A'] >= 1 and draws['B'] >= 1,
            desc='initial A & B SceneCanvas draw',
        )
        _drain_idle(application, _dawn)

        # Initial distinct colors: A=red, B=blue
        np.testing.assert_allclose(_center_rgba(sc_a), [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(_center_rgba(sc_b), [0, 0, 255, 255], atol=2)

        focus_reason = _qt_enum(QtCore, 'FocusReason', 'OtherFocusReason')

        # Step 1: Focus Canvas A -> 'k' routes ONLY to Canvas A (A turns green, B stays blue, LineEdit empty)
        sc_a.native.setFocus(focus_reason)
        qapp.setActiveWindow(host)
        _pump_until(application, _dawn, lambda: host.focusWidget() is sc_a.native, desc='focus sc_a')
        prev_a = draws['A']
        _send_key_to_focused_host(_qt_enum(QtCore, 'Key', 'Key_K'), 'k')
        _pump_until(application, _dawn, lambda: draws['A'] > prev_a, desc='sc_a green draw')
        _drain_idle(application, _dawn)
        assert key_log == [('A', keys.Key('K'), 'k')]
        assert line_edit.text() == ''
        np.testing.assert_allclose(_center_rgba(sc_a), [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(_center_rgba(sc_b), [0, 0, 255, 255], atol=2)

        # Step 2: Focus QLineEdit -> 'q', 't' route ONLY to QLineEdit (neither canvas receives keys)
        line_edit.setFocus(focus_reason)
        qapp.setActiveWindow(host)
        _pump_until(application, _dawn, lambda: host.focusWidget() is line_edit, desc='focus line_edit')
        _send_key_to_focused_host(_qt_enum(QtCore, 'Key', 'Key_Q'), 'q')
        _send_key_to_focused_host(_qt_enum(QtCore, 'Key', 'Key_T'), 't')
        assert line_edit.text() == 'qt'
        assert len(key_log) == 1
        np.testing.assert_allclose(_center_rgba(sc_a), [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(_center_rgba(sc_b), [0, 0, 255, 255], atol=2)

        # Step 3: Focus Canvas B -> 'm' routes ONLY to Canvas B (B turns yellow, A stays green, LineEdit stays 'qt')
        sc_b.native.setFocus(focus_reason)
        qapp.setActiveWindow(host)
        _pump_until(application, _dawn, lambda: host.focusWidget() is sc_b.native, desc='focus sc_b')
        prev_b = draws['B']
        _send_key_to_focused_host(_qt_enum(QtCore, 'Key', 'Key_M'), 'm')
        _pump_until(application, _dawn, lambda: draws['B'] > prev_b, desc='sc_b yellow draw')
        _drain_idle(application, _dawn)
        assert key_log == [('A', keys.Key('K'), 'k'), ('B', keys.Key('M'), 'm')]
        assert line_edit.text() == 'qt'
        np.testing.assert_allclose(_center_rgba(sc_a), [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(_center_rgba(sc_b), [255, 255, 0, 255], atol=2)

        # Step 4: Return focus to Canvas A -> 'z' routes ONLY to Canvas A (A turns orange, B stays yellow)
        sc_a.native.setFocus(focus_reason)
        qapp.setActiveWindow(host)
        _pump_until(application, _dawn, lambda: host.focusWidget() is sc_a.native, desc='refocus sc_a')
        prev_a2 = draws['A']
        _send_key_to_focused_host(_qt_enum(QtCore, 'Key', 'Key_Z'), 'z')
        _pump_until(application, _dawn, lambda: draws['A'] > prev_a2, desc='sc_a orange draw')
        _drain_idle(application, _dawn)
        assert key_log == [
            ('A', keys.Key('K'), 'k'),
            ('B', keys.Key('M'), 'm'),
            ('A', keys.Key('Z'), 'z'),
        ]
        assert line_edit.text() == 'qt'
        np.testing.assert_allclose(_center_rgba(sc_a), [255, 128, 0, 255], atol=2)
        np.testing.assert_allclose(_center_rgba(sc_b), [255, 255, 0, 255], atol=2)

        _assert_binding_isolation(binding)
    finally:
        for sc in (sc_a, sc_b):
            if not sc._closed:
                sc.close()
        host.close()
        host.deleteLater()
        _quiesce_teardown(application, _dawn, QtCore)


def test_qt_binding_parent_deletelater_reparent_and_zerosize_recovery(monkeypatch):
    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    binding, _pkg, application, _dawn, QtCore, QtGui, QtWidgets, _QtTest = _activate_binding()
    from vispy import gloo, scene

    destroyed_tags: list[str] = []

    doomed_parent = QtWidgets.QWidget()
    doomed_parent.resize(150, 110)
    doomed_layout = QtWidgets.QVBoxLayout(doomed_parent)
    doomed_layout.setContentsMargins(0, 0, 0, 0)

    frame_a = QtWidgets.QFrame()
    frame_a.resize(180, 140)
    frame_b = QtWidgets.QFrame()
    frame_b.resize(180, 140)

    def _mark_destroyed(tag: str):
        def _slot(*_args):
            destroyed_tags.append(tag)
        return _slot

    on_doomed_parent_dead = _mark_destroyed('doomed_parent')
    on_sibling_dead = _mark_destroyed('sibling_sc')
    on_frame_a_dead = _mark_destroyed('frame_a')
    on_frame_b_dead = _mark_destroyed('frame_b')

    doomed_parent.destroyed.connect(on_doomed_parent_dead)
    frame_a.destroyed.connect(on_frame_a_dead)
    frame_b.destroyed.connect(on_frame_b_dead)

    sibling_sc = scene.SceneCanvas(
        app=binding, parent=doomed_parent, size=(120, 90), show=False, vsync=False, bgcolor=(0.1, 0.0, 0.0, 1.0)
    )
    sibling_sc.native.destroyed.connect(on_sibling_dead)
    sib_view = sibling_sc.central_widget.add_view()
    sib_view.camera = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, 120.0, 90.0))
    scene.visuals.Rectangle(
        center=(60.0, 45.0), width=70.0, height=50.0, color=(1.0, 0.0, 0.25, 1.0), parent=sib_view.scene
    )
    doomed_layout.addWidget(sibling_sc.native)

    peer_sc = scene.SceneCanvas(
        app=binding,
        parent=frame_a,
        size=(160, 120),
        show=False,
        vsync=False,
        shared=sibling_sc,
        bgcolor=(0.05, 0.05, 0.1, 1.0),
    )
    assert peer_sc.context.shared is sibling_sc.context.shared
    peer_sc.native.setGeometry(0, 0, 160, 120)
    peer_view = peer_sc.central_widget.add_view()
    peer_view.camera = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, 160.0, 120.0))
    peer_rect = scene.visuals.Rectangle(
        center=(80.0, 60.0), width=90.0, height=60.0, color=(0.0, 0.8, 1.0, 1.0), parent=peer_view.scene
    )

    draws = {'sib': 0, 'peer': 0}

    @sibling_sc.events.draw.connect
    def _on_sib_draw(_ev):
        draws['sib'] += 1

    @peer_sc.events.draw.connect
    def _on_peer_draw(_ev):
        draws['peer'] += 1

    winid_type = _qevent_type(QtCore, 'WinIdChange')
    parent_change_type = _qevent_type(QtCore, 'ParentChange')
    reparent_events = []

    class _ReparentFilter(QtCore.QObject):
        def eventFilter(self, _obj, ev):
            if ev.type() in (winid_type, parent_change_type):
                reparent_events.append(ev.type())
            return False

    rep_filter = _ReparentFilter()
    peer_sc.native.installEventFilter(rep_filter)
    deferred_delete = _qevent_type(QtCore, 'DeferredDelete')

    try:
        doomed_parent.show()
        sibling_sc.show()
        frame_a.show()
        peer_sc.show()
        _pump_until(
            application,
            _dawn,
            lambda: draws['sib'] >= 1 and draws['peer'] >= 1,
            desc='initial sibling & peer draw',
        )
        _drain_idle(application, _dawn)

        px_init = _read_canvas_rgba(peer_sc, gloo)
        np.testing.assert_allclose(px_init[px_init.shape[0] // 2, px_init.shape[1] // 2], [0, 204, 255, 255], atol=3)

        # 1) LIF-04: Destroy sibling's parent QWidget via deleteLater() + processEvents(); shared peer survives.
        sibling_sc.update()
        peer_sc.update()
        doomed_parent.close()
        doomed_parent.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, deferred_delete)
        application.process_events()
        _pump_until(
            application,
            _dawn,
            lambda: 'doomed_parent' in destroyed_tags and 'sibling_sc' in destroyed_tags,
            desc='doomed_parent deleteLater destruction',
        )
        _drain_idle(application, _dawn)
        assert sibling_sc._closed is True
        assert peer_sc._closed is False

        prev_peer = draws['peer']
        peer_rect.color = (0.2, 1.0, 0.2, 1.0)
        peer_sc.update()
        _pump_until(application, _dawn, lambda: draws['peer'] > prev_peer, desc='peer render after sibling death')
        _drain_idle(application, _dawn)
        px_after_delete = _read_canvas_rgba(peer_sc, gloo)
        np.testing.assert_allclose(
            px_after_delete[px_after_delete.shape[0] // 2, px_after_delete.shape[1] // 2],
            [51, 255, 51, 255],
            atol=3,
        )

        # 2) LIF-02: setParent() (WinIdChange) reparenting across two QFrame hosts preserves valid rendering.
        _ = int(peer_sc.native.winId())
        frame_b.show()
        _ = int(frame_b.winId())
        winid_before = reparent_events.count(winid_type)

        peer_sc.native.setParent(frame_b)
        peer_sc.native.setGeometry(0, 0, 160, 120)
        peer_sc.native.show()
        frame_a.close()
        frame_a.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, deferred_delete)
        _pump_until(application, _dawn, lambda: 'frame_a' in destroyed_tags, desc='frame_a destruction')

        prev_peer = draws['peer']
        peer_rect.color = (1.0, 0.6, 0.0, 1.0)
        peer_sc.update()
        _pump_until(application, _dawn, lambda: draws['peer'] > prev_peer, desc='peer render in frame_b')
        _drain_idle(application, _dawn)

        assert reparent_events.count(parent_change_type) >= 1
        assert reparent_events.count(winid_type) > winid_before
        px_reparented = _read_canvas_rgba(peer_sc, gloo)
        np.testing.assert_allclose(
            px_reparented[px_reparented.shape[0] // 2, px_reparented.shape[1] // 2],
            [255, 153, 0, 255],
            atol=3,
        )

        # 3) LIF-03: Collapse to (0, 0) / minimized submits cleanly without error & recovers upon restore to (160, 120).
        cid = int(peer_sc.native._dawn_canvas_id)
        peer_sc.native.setFixedSize(0, 0)
        application.process_events()
        _drain_idle(application, _dawn)
        assert peer_sc.size == (0, 0)
        with pytest.raises(RuntimeError, match='empty canvas target'):
            _dawn.framebuffer_config(cid)

        probe_zero_before = _dawn.probe()
        draws_zero_before = draws['peer']
        for _ in range(4):
            peer_sc.update()
            QtCore.QCoreApplication.sendEvent(peer_sc.native, QtGui.QPaintEvent(QtCore.QRect(0, 0, 0, 0)))
            application.process_events()
            _dawn.process_events()
        probe_zero_after = _dawn.probe()
        assert draws['peer'] == draws_zero_before
        assert probe_zero_after['dawn_queue_submits'] == probe_zero_before['dawn_queue_submits']

        # Exercise minimized WindowStateChange suppression as well
        peer_sc.native.setMinimumSize(0, 0)
        peer_sc.native.setMaximumSize(16777215, 16777215)
        peer_sc.native.resize(160, 120)
        application.process_events()
        frame_b.showMinimized()
        application.process_events()
        forced_min = False
        orig_is_min = peer_sc.native.isMinimized
        def _window_state_change_event(old_state):
            try:
                return QtGui.QWindowStateChangeEvent(old_state)
            except TypeError:
                return QtCore.QEvent(_qevent_type(QtCore, 'WindowStateChange'))

        if not peer_sc.native.isMinimized():
            forced_min = True
            monkeypatch.setattr(peer_sc.native, 'isMinimized', lambda: True)
            QtCore.QCoreApplication.sendEvent(
                peer_sc.native,
                _window_state_change_event(_qt_enum(QtCore, 'WindowState', 'WindowNoState')),
            )
            application.process_events()

        _drain_idle(application, _dawn)
        with pytest.raises(RuntimeError, match='empty canvas target'):
            _dawn.framebuffer_config(cid)
        submits_min_before = _dawn.probe()['dawn_queue_submits']
        peer_sc.update()
        QtCore.QCoreApplication.sendEvent(peer_sc.native, QtGui.QPaintEvent(peer_sc.native.rect()))
        application.process_events()
        _dawn.process_events()
        assert _dawn.probe()['dawn_queue_submits'] == submits_min_before

        # Restore from minimized and (0, 0) back to (160, 120) and verify valid non-trivial scene render
        if forced_min:
            monkeypatch.setattr(peer_sc.native, 'isMinimized', orig_is_min)
            QtCore.QCoreApplication.sendEvent(
                peer_sc.native,
                _window_state_change_event(_qt_enum(QtCore, 'WindowState', 'WindowMinimized')),
            )
        frame_b.showNormal()
        peer_sc.native.resize(160, 120)
        peer_rect.color = (0.8, 0.2, 1.0, 1.0)
        prev_restore_draws = draws['peer']
        peer_sc.update()
        _pump_until(
            application,
            _dawn,
            lambda: draws['peer'] > prev_restore_draws and peer_sc.size == (160, 120),
            desc='restore to (160, 120) render',
        )
        _drain_idle(application, _dawn)

        assert peer_sc.size == (160, 120)
        assert _dawn.framebuffer_config(cid)['width'] >= 160
        px_restored = _read_canvas_rgba(peer_sc, gloo)
        h_px, w_px = px_restored.shape[:2]
        assert (w_px, h_px) == peer_sc.physical_size
        # Foreground rectangle at center vs dark scene background near outer edge
        np.testing.assert_allclose(px_restored[h_px // 2, w_px // 2], [204, 51, 255, 255], atol=3)
        np.testing.assert_allclose(px_restored[4, 4], [13, 13, 26, 255], atol=3)

        _assert_binding_isolation(binding)
    finally:
        peer_sc.native.removeEventFilter(rep_filter)
        for sc in (peer_sc, sibling_sc):
            if not sc._closed:
                sc.close()
        for host_tag, w in (
            ('doomed_parent', doomed_parent),
            ('frame_a', frame_a),
            ('frame_b', frame_b),
        ):
            if host_tag not in destroyed_tags:
                w.close()
                w.deleteLater()
        _quiesce_teardown(application, _dawn, QtCore)


_HIDPI_CHILD_SCRIPT = r"""
import gc
import importlib
import importlib.abc
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

BINDING_TO_PKG = {'pyqt5': 'PyQt5', 'pyqt6': 'PyQt6', 'pyside6': 'PySide6'}
ALL_QT_PACKAGES = ('PyQt4', 'PyQt5', 'PyQt6', 'PySide', 'PySide2', 'PySide6')
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

expected_pkg = BINDING_TO_PKG[BINDING]


class _BlockCompetingQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        top = fullname.split('.', 1)[0]
        if top in ALL_QT_PACKAGES and top != expected_pkg:
            raise ModuleNotFoundError(f'Blocked competing Qt package {fullname!r} in {BINDING} child')
        return None


sys.meta_path.insert(0, _BlockCompetingQt())

import vispy
assert str(Path(vispy.__file__).resolve()) == EXPECTED_VISPY

QtCore = importlib.import_module(f'{expected_pkg}.QtCore')
QtGui = importlib.import_module(f'{expected_pkg}.QtGui')
QtWidgets = importlib.import_module(f'{expected_pkg}.QtWidgets')

# Configure PassThrough fractional HiDPI rounding policy before QApplication creation.
policy_enum = getattr(QtCore.Qt, 'HighDpiScaleFactorRoundingPolicy', None)
if policy_enum is not None and hasattr(QtGui.QGuiApplication, 'setHighDpiScaleFactorRoundingPolicy'):
    QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(policy_enum.PassThrough)

from vispy import _dawn, app, gloo, scene

application = app.use_app(BINDING)
assert application.backend_name.lower() == BINDING

competing = [
    m for m in sorted(sys.modules)
    for p in ALL_QT_PACKAGES
    if p != expected_pkg and (m == p or m.startswith(p + '.'))
]
assert not competing, f'Competing Qt modules in 1.5x child: {competing}'


def _qevent_type(name):
    t_ns = getattr(QtCore.QEvent, 'Type', None)
    if t_ns is not None and hasattr(t_ns, name):
        return getattr(t_ns, name)
    return getattr(QtCore.QEvent, name)


def _qt_enum(scope, name):
    qt = QtCore.Qt
    scoped = getattr(qt, scope, None)
    if scoped is not None and hasattr(scoped, name):
        return getattr(scoped, name)
    return getattr(qt, name)


def _pump_until(pred, timeout=5.0, desc='1.5x HiDPI condition'):
    deadline = time.monotonic() + timeout
    while True:
        application.process_events()
        _dawn.process_events()
        if pred():
            return
        assert time.monotonic() < deadline, f'Timed out waiting for {desc}'
        time.sleep(0.002)


logical_w, logical_h = 160, 120
sc = scene.SceneCanvas(
    app=BINDING, size=(logical_w, logical_h), show=False, vsync=False, bgcolor=(0.0, 0.0, 0.0, 1.0)
)
view = sc.central_widget.add_view()
cam = scene.cameras.PanZoomCamera(rect=(0.0, 0.0, float(logical_w), float(logical_h)))
view.camera = cam

# Fill all 4 quadrants of logical (0..160, 0..120) so any quarter/fractional viewport clip is caught:
# Bottom-left world (0..80, 0..60) -> Red; Bottom-right (80..160, 0..60) -> Green;
# Top-left world (0..80, 60..120) -> Blue; Top-right (80..160, 60..120) -> Yellow.
scene.visuals.Rectangle(center=(40.0, 30.0), width=80.0, height=60.0, color=(1.0, 0.0, 0.0, 1.0), parent=view.scene)
scene.visuals.Rectangle(center=(120.0, 30.0), width=80.0, height=60.0, color=(0.0, 1.0, 0.0, 1.0), parent=view.scene)
scene.visuals.Rectangle(center=(40.0, 90.0), width=80.0, height=60.0, color=(0.0, 0.0, 1.0, 1.0), parent=view.scene)
scene.visuals.Rectangle(center=(120.0, 90.0), width=80.0, height=60.0, color=(1.0, 1.0, 0.0, 1.0), parent=view.scene)

draws = [0]
mouse_coords = []
wheel_coords = []


@sc.events.draw.connect
def _on_draw(_ev):
    draws[0] += 1


@sc.events.mouse_press.connect
def _on_press(ev):
    assert not ev.native.spontaneous()
    mouse_coords.append(('press', tuple(ev.pos)))


@sc.events.mouse_move.connect
def _on_move(ev):
    assert not ev.native.spontaneous()
    mouse_coords.append(('move', tuple(ev.pos)))


@sc.events.mouse_release.connect
def _on_release(ev):
    assert not ev.native.spontaneous()
    mouse_coords.append(('release', tuple(ev.pos)))


@sc.events.mouse_wheel.connect
def _on_wheel(ev):
    assert not ev.native.spontaneous()
    wheel_coords.append((tuple(ev.pos), tuple(ev.delta)))


try:
    sc.show()
    _pump_until(lambda: draws[0] >= 1 and sc.native._dawn_shown, desc='initial 1.5x SceneCanvas paint')
    sc.update()
    _pump_until(lambda: draws[0] >= 2 or not any(_dawn.probe()[k] for k in ('pending_tickets', 'queued_frames')))
    _pump_until(
        lambda: not any(_dawn.probe()[k] for k in ('pending_tickets', 'queued_frames', 'line_resource_pool_busy_slots')),
        desc='1.5x Dawn idle',
    )

    actual_scale = float(sc.pixel_scale)
    assert abs(actual_scale - 1.5) < 1e-3, f'Expected pixel_scale ~ 1.5, got {actual_scale} (size={sc.size}, physical={sc.physical_size})'
    assert sc.size == (logical_w, logical_h), sc.size
    expected_phys = (int(round(logical_w * 1.5)), int(round(logical_h * 1.5)))
    assert sc.physical_size == expected_phys, (sc.physical_size, expected_phys)

    sc.set_current()
    px = gloo.read_pixels(alpha=True)
    assert px.shape[:2] == sc.physical_size[::-1] == (180, 240), px.shape

    # Full-quadrant + outer-corner color verification across all 240x180 physical pixels (no quarter-screen clip):
    # Top-left [rows 0..90, cols 0..120] -> Blue [0, 0, 255, 255]
    for r, c in ((12, 16), (45, 60), (75, 100)):
        np.testing.assert_allclose(px[r, c], [0, 0, 255, 255], atol=2)
    # Top-right [rows 0..90, cols 120..240] -> Yellow [255, 255, 0, 255]
    for r, c in ((12, 224), (45, 180), (75, 140)):
        np.testing.assert_allclose(px[r, c], [255, 255, 0, 255], atol=2)
    # Bottom-left [rows 90..180, cols 0..120] -> Red [255, 0, 0, 255]
    for r, c in ((168, 16), (135, 60), (105, 100)):
        np.testing.assert_allclose(px[r, c], [255, 0, 0, 255], atol=2)
    # Bottom-right [rows 90..180, cols 120..240] -> Green [0, 255, 0, 255]
    for r, c in ((168, 224), (135, 180), (105, 140)):
        np.testing.assert_allclose(px[r, c], [0, 255, 0, 255], atol=2)

    # Mouse & wheel coordinates match logical canvas.size (160, 120), NOT physical (240, 180).
    w = sc.native
    left_btn = _qt_enum('MouseButton', 'LeftButton')
    no_btn = _qt_enum('MouseButton', 'NoButton')
    no_mod = _qt_enum('KeyboardModifier', 'NoModifier')
    no_phase = _qt_enum('ScrollPhase', 'NoScrollPhase')

    pt_press = QtCore.QPointF(20.0, 15.0)
    gpt_press = QtCore.QPointF(w.mapToGlobal(QtCore.QPoint(20, 15)))
    pt_end = QtCore.QPointF(140.0, 105.0)
    gpt_end = QtCore.QPointF(w.mapToGlobal(QtCore.QPoint(140, 105)))

    QtCore.QCoreApplication.sendEvent(
        w, QtGui.QMouseEvent(_qevent_type('MouseButtonPress'), pt_press, gpt_press, left_btn, left_btn, no_mod)
    )
    w._last_time = 0.0
    QtCore.QCoreApplication.sendEvent(
        w, QtGui.QMouseEvent(_qevent_type('MouseMove'), pt_end, gpt_end, no_btn, left_btn, no_mod)
    )
    QtCore.QCoreApplication.sendEvent(
        w, QtGui.QMouseEvent(_qevent_type('MouseButtonRelease'), pt_end, gpt_end, left_btn, no_btn, no_mod)
    )
    assert ('press', (20, 15)) in mouse_coords, mouse_coords
    assert ('move', (140, 105)) in mouse_coords, mouse_coords
    assert ('release', (140, 105)) in mouse_coords, mouse_coords
    assert all(0 <= pos[0] < sc.size[0] and 0 <= pos[1] < sc.size[1] for _, pos in mouse_coords), mouse_coords

    # Reset camera rect and verify wheel event logical pos + cursor-anchored PanZoom zoom at 1.5x DPR
    cam.rect = (0.0, 0.0, float(logical_w), float(logical_h))
    anchor = (120, 90)
    world_before = (
        cam.rect.left + (anchor[0] / float(logical_w)) * cam.rect.width,
        cam.rect.bottom + ((float(logical_h) - anchor[1]) / float(logical_h)) * cam.rect.height,
    )
    QtCore.QCoreApplication.sendEvent(
        w,
        QtGui.QWheelEvent(
            QtCore.QPointF(*anchor),
            QtCore.QPointF(w.mapToGlobal(QtCore.QPoint(*anchor))),
            QtCore.QPoint(0, 0),
            QtCore.QPoint(0, 240),
            no_btn,
            no_mod,
            no_phase,
            False,
        ),
    )
    application.process_events()
    assert wheel_coords[-1][0] == anchor
    np.testing.assert_allclose(wheel_coords[-1][1], (0.0, 2.0))
    assert cam.rect.width < float(logical_w) and cam.rect.height < float(logical_h)
    world_after = (
        cam.rect.left + (anchor[0] / float(logical_w)) * cam.rect.width,
        cam.rect.bottom + ((float(logical_h) - anchor[1]) / float(logical_h)) * cam.rect.height,
    )
    np.testing.assert_allclose(world_after, world_before, atol=1.5)
finally:
    if not sc._closed:
        sc.close()
    QtCore.QCoreApplication.sendPostedEvents(None, _qevent_type('DeferredDelete'))
    application.process_events()
    gc.collect()
    _dawn.process_events()
    _dawn.shutdown()

probe = _dawn.probe()
gauges = {k: int(probe[k]) for k in TEN_GAUGES}
assert not any(gauges.values()), gauges
competing_end = [
    m for m in sorted(sys.modules)
    for p in ALL_QT_PACKAGES
    if p != expected_pkg and (m == p or m.startswith(p + '.'))
]
assert not competing_end, competing_end
print(
    'HIDPI_1_5X_PROOF '
    + json.dumps(
        {
            'binding': BINDING,
            'pixel_scale': actual_scale,
            'logical_size': list(sc.size) if not sc._closed else [logical_w, logical_h],
            'physical_size': list(expected_phys),
            'readback_shape': list(px.shape),
            'shutdown_gauges': gauges,
        }
    ),
    flush=True,
)
"""


def test_qt_binding_programmatic_fractional_hidpi_scale():
    binding = _selected_binding()
    _assert_binding_isolation(binding)
    import vispy

    expected_vispy = str(Path(vispy.__file__).resolve())
    clean_path = [p for p in sys.path if p != '']
    setup = (
        f'import sys\n'
        f'sys.path[:] = {clean_path!r}\n'
        f'BINDING = {binding!r}\n'
        f'EXPECTED_VISPY = {expected_vispy!r}\n'
    )

    child_env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith(('QT_SCREEN_SCALE_FACTORS', 'QT_ENABLE_HIGHDPI_SCALING', 'QT_DEVICE_PIXEL_RATIO'))
    }
    child_env.update(
        PYTHONDONTWRITEBYTECODE='1',
        VISPY_TEST_QT_BINDING=binding,
        QT_API=binding,
        VISPY_QT_PRESENTATION='readback',
        QT_SCALE_FACTOR='1.5',
        QT_AUTO_SCREEN_SCALE_FACTOR='0',
        QT_SCALE_FACTOR_ROUNDING_POLICY='PassThrough',
    )

    res = subprocess.run(
        [sys.executable, '-I', '-S', '-B', '-X', 'faulthandler', '-c', setup + _HIDPI_CHILD_SCRIPT],
        cwd=Path(__file__).resolve().parents[2],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=90,
    )
    assert res.returncode == 0, f'1.5x HiDPI child failed ({binding}, exit={res.returncode}):\n{res.stdout}'
    marker_lines = [ln for ln in res.stdout.splitlines() if ln.startswith('HIDPI_1_5X_PROOF ')]
    assert len(marker_lines) == 1, res.stdout
    payload = json.loads(marker_lines[0][len('HIDPI_1_5X_PROOF ') :])
    assert payload['binding'] == binding
    assert payload['pixel_scale'] == pytest.approx(1.5)
    assert payload['logical_size'] == [160, 120]
    assert payload['physical_size'] == [240, 180]
    assert payload['readback_shape'] == [180, 240, 4]
    assert not any(payload['shutdown_gauges'].values()), payload['shutdown_gauges']
