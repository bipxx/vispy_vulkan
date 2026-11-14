# SPDX-License-Identifier: AGPL-3.0-only
"""Source-only Qt application focus routing, without native canvas allocation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


CHILD = r'''
import hashlib, json, sys, time, types
from pathlib import Path
native_attempts = []
class ForbiddenNative(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        native_attempts.append(name)
        raise RuntimeError('Focus CPU fixture cannot call native: ' + name)
sys.modules['vispy._dawn'] = ForbiddenNative('vispy._dawn')
from vispy.app.backends import _pyqt6
from vispy.app.canvas import KeyEvent
from vispy.util.event import EmitterGroup
from vispy import keys
from PyQt6 import sip
QT = _pyqt6._qt
assert Path(QT.__file__).resolve() == Path(EXPECTED_QT).resolve()
assert hashlib.sha256(Path(QT.__file__).read_bytes()).hexdigest() == EXPECTED_QT_SHA
application = QT.QApplication.instance() or QT.QApplication(['focus-routing-cpu'])
application.setQuitOnLastWindowClosed(False)
received, focus_observations = [], []

class Source:
    pass

class Widget(QT.CanvasBackendDesktop):
    def __init__(self, name, parent):
        # Keep production key handlers and real QWidget focus. Bypass only
        # native initialization, rendering and their show-time configuration.
        self._initialized = False
        self._vispy_canvas = None
        QT.QWidget.__init__(self, parent)
        self.setObjectName(name)
        self.setMinimumSize(80, 40)
        self.setFocusPolicy(QT.QtCore.Qt.FocusPolicy.WheelFocus)
        self._dawn_closed = self._dawn_callback_failed = False
        self._dawn_shown = False
        self._vispy_canvas = Source()
        self._vispy_canvas.events = EmitterGroup(
            source=self._vispy_canvas, key_press=KeyEvent, key_release=KeyEvent)
        for event_name in ('key_press', 'key_release'):
            emitter = self._vispy_canvas.events[event_name]
            emitter.ignore_callback_errors = False
            def receive(event, name=name):
                # Validate snapshots outside the Qt virtual call.
                received.append((name, event.type, event.key, event.text,
                                 event.modifiers))
                event.handled = True
            emitter.connect(receive)

    def showEvent(self, event):
        QT.QWidget.showEvent(self, event)

    def paintEvent(self, event):
        pass

def until(predicate):
    deadline = time.monotonic() + 3
    while not predicate():
        application.processEvents()
        assert time.monotonic() < deadline, 'Qt application focus timed out'
        time.sleep(.001)

host = QT.QWidget()
layout = QT.QtWidgets.QVBoxLayout(host)
widgets = [Widget(name, host) for name in ('canvas_a', 'canvas_b')]
entry = QT.QtWidgets.QLineEdit(host)
entry.setObjectName('host_entry')
for widget in widgets:
    layout.addWidget(widget)
layout.addWidget(entry)
host.resize(220, 180)
owned_widgets = {'host': host, 'canvas_a': widgets[0],
                 'canvas_b': widgets[1], 'host_entry': entry}
destroyed = []
for name, widget in owned_widgets.items():
    widget.destroyed.connect(lambda obj=None, name=name: destroyed.append(name))
try:
    host.show()
    host.activateWindow()
    application.processEvents()
    until(lambda: host.windowHandle() is not None)
    window = host.windowHandle()
    sequence = ([widgets[0], widgets[1], widgets[0]] if FLOW == 'canvases'
                else [widgets[0], entry, widgets[0]])
    for target in sequence:
        target.setFocus(QT.QtCore.Qt.FocusReason.OtherFocusReason)
        until(lambda: application.focusWidget() is target)
        focus_observations.append(target.objectName())
        before = len(received)
        # The injection receiver is invariant. Qt resolves the focused child.
        QT.QtTest.QTest.keyClick(window, QT.QtCore.Qt.Key.Key_K,
                                QT.QtCore.Qt.KeyboardModifier.NoModifier)
        application.processEvents()
        if target is entry:
            assert entry.text() == 'k'
            assert len(received) == before, received
        else:
            assert len(received) == before + 2, received
            events = received[-2:]
            assert [e[0] for e in events] == [target.objectName()] * 2
            assert [e[1] for e in events] == ['key_press', 'key_release']
            assert all(e[2] == keys.Key('K') and e[3] == 'k' and e[4] == ()
                       for e in events), events
    assert entry.text() == ('' if FLOW == 'canvases' else 'k')
    assert not any(w._dawn_callback_failed for w in widgets)
    assert getattr(application, '_vispy_dawn_callback_error', None) is None
finally:
    for widget in widgets:
        widget._vispy_canvas = None
        widget._dawn_closed = True
    host.close()
    host.deleteLater()
    QT.QtCore.QCoreApplication.sendPostedEvents(
        None, QT.QtCore.QEvent.Type.DeferredDelete)
    application.processEvents()
assert not native_attempts, native_attempts
assert getattr(application, '_vispy_dawn_callback_error', None) is None
deleted_wrappers = {name: bool(sip.isdeleted(widget))
                    for name, widget in owned_widgets.items()}
teardown_drained = (all(deleted_wrappers.values()) and
                    sorted(destroyed) == sorted(owned_widgets))
assert teardown_drained, ('Qt focus teardown did not destroy all owned widgets',
                          destroyed, deleted_wrappers)
print('focus routing proof', json.dumps(dict(
    flow=FLOW, focus=focus_observations,
    events=[dict(target=e[0], type=e[1], key=str(e[2]), text=e[3])
            for e in received],
    qt_source_sha256=EXPECTED_QT_SHA, native_calls=native_attempts,
    destroyed_objects=sorted(destroyed), deleted_wrappers=deleted_wrappers,
    teardown_drained=teardown_drained)))
'''


@pytest.mark.parametrize('flow', ('canvases', 'host_entry'))
def test_host_qwindow_routes_keys_by_application_focus_and_recovers(flow):
    source = Path(__file__).resolve().parents[2]
    qt = source / 'src/vispy/app/backends/_qt.py'
    qt_sha = hashlib.sha256(qt.read_bytes()).hexdigest()
    setup = (f'FLOW = {flow!r}\nEXPECTED_QT = {str(qt)!r}\n'
             f'EXPECTED_QT_SHA = {qt_sha!r}\n')
    result = subprocess.run(
        [sys.executable, '-B', '-X', 'faulthandler', '-c', setup + CHILD],
        cwd=source,
        env=dict(os.environ, QT_QPA_PLATFORM='offscreen',
                 PYTHONDONTWRITEBYTECODE='1'),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace', timeout=30,
    )
    assert result.returncode == 0, f'child exit {result.returncode}\n{result.stdout}'
    proofs = [json.loads(line.removeprefix('focus routing proof '))
              for line in result.stdout.splitlines()
              if line.startswith('focus routing proof ')]
    assert len(proofs) == 1
    proof = proofs[0]
    assert proof['flow'] == flow and proof['qt_source_sha256'] == qt_sha
    assert proof['native_calls'] == [] and proof['teardown_drained']
    assert proof['destroyed_objects'] == ['canvas_a', 'canvas_b', 'host', 'host_entry']
    assert set(proof['deleted_wrappers']) == set(proof['destroyed_objects'])
    assert all(proof['deleted_wrappers'].values())
    assert proof['focus'] == (['canvas_a', 'canvas_b', 'canvas_a']
                              if flow == 'canvases' else
                              ['canvas_a', 'host_entry', 'canvas_a'])
    assert len(proof['events']) == (6 if flow == 'canvases' else 4)
    print('focus routing proof', json.dumps(proof))
