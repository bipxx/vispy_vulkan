# SPDX-License-Identifier: AGPL-3.0-only
"""Input callback failure must preserve a real peer's rendered recovery."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
import vispy


CHILD = r'''
from pathlib import Path
import gc, hashlib, json, sys, time
import numpy as np
import vispy
assert str(Path(vispy.__file__).resolve()) == EXPECTED_VISPY
from vispy import _dawn, app, gloo
from PyQt6 import QtCore, QtGui, QtWidgets
application = app.use_app('pyqt6')
canvases, draws = [], [0, 0]
colors = [[1., 0., 0., 1.], [0., 0., 1., 1.]]
original = RuntimeError('input callback recovery: ' + KIND)
received, events = [], []
hook_calls = []
previous_hook = sys.excepthook

def paint(index):
    def draw(event):
        draws[index] += 1
        gloo.set_clear_color(colors[index])
        gloo.clear()
    return draw

def pump_until(predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        application.process_events()
        assert time.monotonic() < deadline, 'draw recovery timed out'
        time.sleep(.002)

def pixels(index, rgba):
    native = canvases[index].native
    _dawn.finish(native._dawn_canvas_id)
    image = _dawn.read_pixels(native._dawn_canvas_id, 0, 0, 2, 2, True)
    np.testing.assert_array_equal(image, np.full((2, 2, 4), rgba, np.uint8))

def deliver():
    qt = QtCore.Qt
    widget = canvases[0].native
    point = QtCore.QPointF(8, 6)
    global_point = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(8, 6)))
    if KIND == 'key_press':
        event = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, qt.Key.Key_A,
                               qt.KeyboardModifier.NoModifier, 'a')
    elif KIND == 'mouse_press':
        event = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonPress,
                                 point, global_point, qt.MouseButton.LeftButton,
                                 qt.MouseButton.LeftButton, qt.KeyboardModifier.NoModifier)
    else:
        event = QtGui.QWheelEvent(point, global_point, QtCore.QPoint(), QtCore.QPoint(0, 120),
                                 qt.MouseButton.NoButton, qt.KeyboardModifier.NoModifier,
                                 QtCore.Qt.ScrollPhase.NoScrollPhase, False)
    events.append(event)
    QtCore.QCoreApplication.sendEvent(widget, event)

def fail(event):
    received.append(event.type)
    raise original

try:
    for index in range(2):
        canvas = app.Canvas(app='pyqt6', size=(32, 24), show=False, vsync=False)
        canvases.append(canvas)
        canvas.events.draw.ignore_callback_errors = False
        canvas.events.draw.connect(paint(index))
        canvas.show()
    pump_until(lambda: all(draws))
    pixels(0, [255, 0, 0, 255])
    pixels(1, [0, 0, 255, 255])
    emitter = getattr(canvases[0].events, KIND)
    emitter.ignore_callback_errors = False
    emitter.connect(fail)
    if POLICY == 'host':
        def host_hook(error_type, error, traceback):
            hook_calls.append((error_type, error, traceback))
        sys.excepthook = host_hook
        native_application = QtWidgets.QApplication.instance()
        QtCore.QTimer.singleShot(0, deliver)
        # QApplication.quit() sends Quit and closes top-level windows. End
        # this fixture's loop without closing the canvases whose recovery we
        # still need to measure (Qt6.11 qapplication.cpp, QEvent::Quit).
        QtCore.QTimer.singleShot(5, lambda: native_application.exit(0))
        assert native_application.exec() == 0
        assert all(not canvas._closed and not canvas.native._dawn_closed
                   and canvas.native.isVisible() for canvas in canvases)
        assert len(hook_calls) == 1 and hook_calls[0][0] is RuntimeError
        assert hook_calls[0][1] is original and hook_calls[0][2] is original.__traceback__
        assert not canvases[0].native._dawn_callback_failed
        assert getattr(native_application, '_vispy_dawn_callback_error', None) is None
        sys.excepthook = previous_hook
        before = draws[0]
        colors[0] = [0., 1., 0., 1.]
        canvases[0].update()
        pump_until(lambda: draws[0] > before)
        pixels(0, [0, 255, 0, 255])
        pixels(1, [0, 0, 255, 255])
    else:
        if ENTRY == 'run':
            QtCore.QTimer.singleShot(0, deliver)
        else:
            deliver()
        seen = None
        try:
            if ENTRY == 'run':
                application.run()
            else:
                application.process_events()
        except RuntimeError as error:
            seen = error
        assert seen is original, repr(seen)
        assert canvases[0].native._dawn_callback_failed
        before = draws[0]
        canvases[0].update()
    assert received == [KIND]
    assert events[0].isAccepted() is (POLICY == 'host')
    assert not canvases[1].native._dawn_callback_failed
    previous_peer_draws = draws[1]
    colors[1] = [0., 1., 0., 1.]
    canvases[1].update()
    pump_until(lambda: draws[1] > previous_peer_draws)
    if POLICY == 'default':
        assert draws[0] == before
    pixels(1, [0, 255, 0, 255])
    canvases[0].close()
    previous_peer_draws = draws[1]
    colors[1] = [0., 0., 1., 1.]
    canvases[1].update()
    pump_until(lambda: draws[1] > previous_peer_draws)
    pixels(1, [0, 0, 255, 255])
finally:
    sys.excepthook = previous_hook
    for canvas in canvases:
        canvas.close()
    application.process_events()
    gc.collect()
    _dawn.process_events()
    _dawn.shutdown()
gauges = _dawn.probe()
names = ('pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
         'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
         'line_resource_pool_busy_slots', 'line_resource_pool_bytes', 'host_import_pinned_bytes')
zeros = {name: gauges[name] for name in names}
assert not any(zeros.values()), zeros
print('input recovery proof', json.dumps(dict(kind=KIND, entry=ENTRY, policy=POLICY,
      same_canvas_recovery=(POLICY == 'host'), peer='green-then-blue',
      shutdown_gauges=zeros, native_path=_dawn.__file__,
      native_sha256=hashlib.sha256(Path(_dawn.__file__).read_bytes()).hexdigest())), flush=True)
'''


def run_gpu_child(kind, entry, policy):
    setup = (f'import sys\nsys.path[:0] = {sys.path!r}\n'
             f'EXPECTED_VISPY = {str(Path(vispy.__file__).resolve())!r}\n'
             f'KIND = {kind!r}\nENTRY = {entry!r}\nPOLICY = {policy!r}\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join(sys.path), VISPY_QT_PRESENTATION='readback')
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-B', '-X', 'faulthandler', '-c', setup + CHILD],
        cwd=Path(__file__).resolve().parents[2], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace', timeout=60,
    )
    assert result.returncode == 0, f'child exit {result.returncode}\n{result.stdout}'
    assert 'input recovery proof' in result.stdout, result.stdout
    if policy == 'default':
        assert 'Dawn Qt ' in result.stdout and 'input callback recovery:' in result.stdout
    print(result.stdout)


@pytest.mark.gpu
@pytest.mark.parametrize('entry', ('process_events', 'run'))
@pytest.mark.parametrize('kind', ('key_press', 'mouse_press', 'mouse_wheel'))
def test_input_callback_failure_preserves_rendered_peer_and_resource_retirement(kind, entry):
    run_gpu_child(kind, entry, 'default')


@pytest.mark.gpu
@pytest.mark.parametrize('kind', ('key_press', 'mouse_press', 'mouse_wheel'))
def test_host_exception_hook_preserves_same_canvas_rendering_and_peer(kind):
    run_gpu_child(kind, 'native_loop', 'host')
