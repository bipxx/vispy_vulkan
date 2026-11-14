# SPDX-License-Identifier: AGPL-3.0-only
"""Real Qt input dispatch must report callback errors outside C++ virtuals.

Each child uses an ordinary QWidget with the production input virtuals and
VisPy emitters. No Dawn canvas, GPU, surface or rendered output is acquired.
"""

import os
from pathlib import Path
import subprocess
import sys

import pytest


EVENTS = ('mouse_press', 'mouse_release', 'mouse_double_click', 'mouse_move',
          'mouse_wheel', 'key_press', 'key_release')

CHILD = r'''
from types import SimpleNamespace
import sys
from vispy.app.backends import _pyqt6
from vispy.app.canvas import MouseEvent, KeyEvent
from vispy.util.event import EmitterGroup

QT = _pyqt6._qt
application = QT.QApplication.instance() or QT.QApplication(['input-error-test'])
application.setQuitOnLastWindowClosed(False)
backend = QT.ApplicationBackend()
original = RuntimeError('deliberate input callback failure: ' + KIND)
failures, stopped, recovered = [], [], []
hook_calls, host_recovered, forwarded = [], [], []
previous_hook = sys.excepthook

class EventSource:
    pass

class Widget(QT.CanvasBackendDesktop):
    def __init__(self):
        # Bypass only native canvas allocation. Keep the actual virtual handlers,
        # common mouse bookkeeping, event emitters and application error path.
        self._initialized = False
        self._vispy_canvas = None
        QT.QWidget.__init__(self)
        self._dawn_canvas_id = 7
        self._dawn_closed = self._dawn_callback_failed = False
        self._dawn_paint_deferred = True
        self._dawn_poll_timer = SimpleNamespace(stop=lambda: stopped.append(True))
        self._last_time = 0
        self._double_click_supported = True
        self._vispy_mouse_data = dict(press_event=None, last_event=None,
                                     last_mouse_press=None)
        self._vispy_canvas = EventSource()
        self._vispy_canvas.events = EmitterGroup(
            source=self._vispy_canvas,
            **{name: KeyEvent if name.startswith('key') else MouseEvent
               for name in ('mouse_press', 'mouse_release', 'mouse_double_click',
                            'mouse_move', 'mouse_wheel', 'key_press', 'key_release')})

def event():
    core, gui, qt = QT.QtCore, QT.QtGui, QT.QtCore.Qt
    kinds = core.QEvent.Type
    if KIND.startswith('key'):
        t = kinds.KeyPress if KIND == 'key_press' else kinds.KeyRelease
        return gui.QKeyEvent(t, qt.Key.Key_A, qt.KeyboardModifier.NoModifier, 'a')
    pos = core.QPointF(12, 9)
    if KIND == 'mouse_wheel':
        return gui.QWheelEvent(pos, pos, core.QPoint(), core.QPoint(0, 120),
                              qt.MouseButton.NoButton, qt.KeyboardModifier.NoModifier,
                              qt.ScrollPhase.NoScrollPhase, False)
    t = dict(mouse_press=kinds.MouseButtonPress, mouse_release=kinds.MouseButtonRelease,
             mouse_double_click=kinds.MouseButtonDblClick, mouse_move=kinds.MouseMove)[KIND]
    return gui.QMouseEvent(t, pos, pos,
                          qt.MouseButton.NoButton if KIND == 'mouse_move' else qt.MouseButton.LeftButton,
                          qt.MouseButton.LeftButton, qt.KeyboardModifier.NoModifier)

widget = Widget()
widget.setMouseTracking(True)
emitter = widget._vispy_canvas.events[KIND]
emitter.ignore_callback_errors = IGNORE

def fail(ev):
    failures.append(ev.type)
    raise original

emitter.connect(fail)
def host_hook(error_type, error, traceback):
    hook_calls.append((error_type, error, traceback))
    if HOOK == 'broken':
        raise RuntimeError('host exception hook failure')

if HOOK != 'default':
    sys.excepthook = host_hook
parent = None
if FORWARD != 'none':
    class Parent(QT.QWidget):
        # napari's parent widgets forward keys through this private entry.
        def keyPressEvent(self, ev):
            forwarded.append('key_press')
            widget._keyEvent(widget._vispy_canvas.events.key_press, ev)
        def keyReleaseEvent(self, ev):
            forwarded.append('key_release')
            widget._keyEvent(widget._vispy_canvas.events.key_release, ev)
    parent = Parent()
    widget.setParent(parent)
native_events = []
def deliver():
    ev = event()
    native_events.append(ev)  # Preserve objects held by the mouse event chain.
    QT.QtCore.QCoreApplication.sendEvent(parent if FORWARD == 'parent' else widget, ev)

try:
    if HOOK == 'host':
        def later_delivery():
            try:
                emitter.disconnect(fail)
                def receive(event):
                    host_recovered.append(event.type)
                    event.handled = True
                emitter.connect(receive)
                widget._last_time = 0
                good = event()
                native_events.append(good)
                QT.QtCore.QCoreApplication.sendEvent(
                    parent if FORWARD == 'parent' else widget, good)
                emitter.disconnect(receive)
            finally:
                application.exit(0)
        # Exercise a host's own Qt loop, without VisPy's process_events/run.
        QT.QtCore.QTimer.singleShot(0, deliver)
        QT.QtCore.QTimer.singleShot(5, later_delivery)
        result = application.exec()
        assert result == 0, f'host loop exited early with {result}'
        assert host_recovered == [KIND]
        assert len(hook_calls) == 1 and hook_calls[0][0] is RuntimeError, (
            failures, forwarded, len(hook_calls))
        assert hook_calls[0][1] is original and hook_calls[0][2] is original.__traceback__
        assert not widget._dawn_callback_failed and not stopped
        assert getattr(application, '_vispy_dawn_callback_error', None) is None
        assert native_events[0].isAccepted() and native_events[1].isAccepted()
        assert forwarded == ([KIND, KIND] if FORWARD == 'parent' else [])
        peer = widget
    elif IGNORE:
        deliver()
        assert not widget._dawn_callback_failed and not stopped
        assert getattr(application, '_vispy_dawn_callback_error', None) is None
        emitter.disconnect(fail)
        peer = widget
    else:
        if ENTRY == 'run':
            QT.QtCore.QTimer.singleShot(0, deliver)
        else:
            deliver()
        seen = None
        try:
            if ENTRY == 'run':
                backend._vispy_run()
            else:
                backend._vispy_process_events()
        except RuntimeError as error:
            seen = error
        assert seen is original, repr(seen)
        assert widget._dawn_callback_failed and not widget._dawn_paint_deferred
        assert stopped == [True]
        assert native_events[0].isAccepted() is (FORWARD == 'canvas')
        assert forwarded == ([KIND] if FORWARD != 'none' else [])
        # It is reported once, and the failed canvas cannot run more callbacks.
        QT._raise_dawn_callback_error(application)
        widget._last_time = 0
        deliver()
        assert failures == [KIND]
        QT._raise_dawn_callback_error(application)
        assert forwarded == ([KIND, KIND] if FORWARD != 'none' else [])
        if HOOK == 'broken':
            assert len(hook_calls) == 1 and hook_calls[0][1] is original
        peer = Widget()
        peer.setMouseTracking(True)

    def succeed(ev):
        recovered.append(ev.type)
        ev.handled = True

    peer._vispy_canvas.events[KIND].connect(succeed)
    peer._last_time = 0
    good = event()
    native_events.append(good)
    QT.QtCore.QCoreApplication.sendEvent(peer, good)
    assert recovered == [KIND] and good.isAccepted()
    assert not peer._dawn_callback_failed
    assert failures == [KIND]
    print('input callback proof', KIND, ENTRY, 'ignore' if IGNORE else HOOK, flush=True)
finally:
    sys.excepthook = previous_hook
    for item in {widget, locals().get('peer', widget), parent} - {None}:
        item._vispy_canvas = None
        item._dawn_closed = True
        item.deleteLater()
    QT.QtCore.QCoreApplication.sendPostedEvents(None, QT.QtCore.QEvent.Type.DeferredDelete)
'''


def run_child(kind, entry, ignore, hook='default', forwarding='none'):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    setup = (f'KIND = {kind!r}\nENTRY = {entry!r}\nIGNORE = {ignore!r}\nHOOK = {hook!r}\n'
             f'FORWARD = {forwarding!r}\n')
    result = subprocess.run(
        [sys.executable, '-B', '-X', 'faulthandler', '-c', setup + CHILD],
        cwd=Path(__file__).resolve().parents[2], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace', timeout=30,
    )
    assert result.returncode == 0, f'child exit {result.returncode}\n{result.stdout}'
    assert f'input callback proof {kind} {entry}' in result.stdout, result.stdout
    if not ignore and hook != 'host':
        assert 'Dawn Qt ' in result.stdout and 'deliberate input callback failure' in result.stdout


@pytest.mark.parametrize('entry', ('process_events', 'run'))
@pytest.mark.parametrize('kind', EVENTS)
def test_input_error_survives_qt_virtual_and_reaches_python_boundary(kind, entry):
    run_child(kind, entry, False)


@pytest.mark.parametrize('kind', EVENTS)
def test_ignored_callback_error_preserves_live_widget_and_later_delivery(kind):
    run_child(kind, 'process_events', True)


@pytest.mark.parametrize('kind', EVENTS)
def test_host_exception_hook_preserves_native_event_loop_and_same_widget(kind):
    run_child(kind, 'native_loop', False, 'host')


@pytest.mark.parametrize('kind', EVENTS)
def test_raising_host_hook_falls_back_to_original_deferred_error(kind):
    run_child(kind, 'process_events', False, 'broken')


@pytest.mark.parametrize('kind', ('key_press', 'key_release'))
@pytest.mark.parametrize('forwarding', ('canvas', 'parent'))
@pytest.mark.parametrize('hook', ('default', 'host', 'broken'))
def test_forwarding_parent_reports_each_error_once_without_replay(kind, forwarding, hook):
    entry = 'native_loop' if hook == 'host' else 'process_events'
    run_child(kind, entry, False, hook, forwarding)
