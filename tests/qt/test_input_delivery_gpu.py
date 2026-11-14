# SPDX-License-Identifier: AGPL-3.0-only
"""Finite Qt-generated input delivery; not physical HID or focus routing."""
import gc
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
CASES = ('key_press_letter', 'key_release_letter', 'key_press_left',
         'key_release_left', 'wheel_vertical', 'wheel_horizontal',
         'mouse_press', 'mouse_release')


@pytest.mark.parametrize('case', CASES)
def test_qt_input_payload_rendering_acceptance_and_target_isolation(case):
    from PyQt6 import QtCore, QtGui
    from vispy import _dawn, app, gloo, keys

    application = app.use_app('pyqt6')
    canvases = []
    colors = [[1., 0., 0., 1.], [1., 0., 0., 1.]]
    draws = [0, 0]
    received, peer_events = [], []
    callback_errors = []
    handled = [True]
    event_name = ('key_press' if case.startswith('key_press') else
                  'key_release' if case.startswith('key_release') else
                  'mouse_wheel' if case.startswith('wheel') else case)
    qt = QtCore.Qt
    modifiers = qt.KeyboardModifier.ShiftModifier | qt.KeyboardModifier.ControlModifier

    def paint(index):
        def draw(event):
            draws[index] += 1
            gloo.set_viewport(0, 0, *canvases[index].physical_size)
            gloo.clear(color=colors[index], depth=False)
        return draw

    def pump_until(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            _dawn.process_events()
            assert time.monotonic() < deadline, 'Qt input redraw timed out'
            time.sleep(.001)

    def pixels(index, rgba):
        canvas = canvases[index]
        _dawn.finish(canvas.native._dawn_canvas_id)
        actual = _dawn.read_pixels(canvas.native._dawn_canvas_id, 0, 0, 2, 2, True)
        np.testing.assert_array_equal(actual, np.full((2, 2, 4), rgba, np.uint8))

    def deliver():
        widget = canvases[0].native
        event_type = QtCore.QEvent.Type
        pos = QtCore.QPointF(9, 7)
        global_pos = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(9, 7)))
        if case.startswith('key'):
            kind = event_type.KeyPress if event_name == 'key_press' else event_type.KeyRelease
            left = case.endswith('left')
            native = QtGui.QKeyEvent(kind, qt.Key.Key_Left if left else qt.Key.Key_A,
                                    modifiers, '' if left else 'A')
        elif case.startswith('wheel'):
            delta = QtCore.QPoint(0, 120) if case.endswith('vertical') else QtCore.QPoint(-240, 0)
            native = QtGui.QWheelEvent(pos, global_pos, QtCore.QPoint(), delta,
                                       qt.MouseButton.NoButton, modifiers,
                                       qt.ScrollPhase.NoScrollPhase, False)
        else:
            press = case == 'mouse_press'
            kind = event_type.MouseButtonPress if press else event_type.MouseButtonRelease
            native = QtGui.QMouseEvent(kind, pos, global_pos, qt.MouseButton.LeftButton,
                                       qt.MouseButton.LeftButton if press else qt.MouseButton.NoButton,
                                       modifiers)
        # The real QWidget dispatches the Qt event. No direct VisPy emitter call.
        QtCore.QCoreApplication.sendEvent(widget, native)
        assert not callback_errors, callback_errors
        return native.isAccepted()

    def check_event(event):
        assert event.type == event_name
        assert not event.native.spontaneous()
        assert event.modifiers == (keys.SHIFT, keys.CONTROL)
        if case.startswith('key'):
            assert event.key == (keys.LEFT if case.endswith('left') else keys.Key('A'))
            assert event.text == ('' if case.endswith('left') else 'A')
        else:
            np.testing.assert_array_equal(event.pos, (9, 7))
            if case.startswith('wheel'):
                np.testing.assert_array_equal(
                    event.delta, (0., 1.) if case.endswith('vertical') else (-2., 0.))
                assert event.buttons == []
            else:
                assert event.button == 1
                assert event.buttons == ([1] if case == 'mouse_press' else [])
        received.append(event.type)
        event.handled = handled[0]
        colors[0] = [0., 1., 0., 1.] if handled[0] else [0., 0., 1., 1.]
        canvases[0].update()

    def receive(event):
        # Report fixture assertions after sendEvent, outside Qt's virtual call.
        # A Python exception escaping that boundary can abort the whole process.
        try:
            check_event(event)
        except Exception as error:
            callback_errors.append(repr(error))

    try:
        for index in range(2):
            canvas = app.Canvas(app='pyqt6', size=(32, 24), show=False, vsync=False)
            canvases.append(canvas)
            canvas.events.draw.ignore_callback_errors = False
            canvas.events.draw.connect(paint(index))
            canvas.show()
        emitter = getattr(canvases[0].events, event_name)
        emitter.ignore_callback_errors = False
        emitter.connect(receive)
        getattr(canvases[1].events, event_name).connect(lambda event: peer_events.append(event.type))
        pump_until(lambda: all(draws))
        pixels(0, [255, 0, 0, 255])
        pixels(1, [255, 0, 0, 255])

        before = draws[0]
        assert deliver()
        pump_until(lambda: draws[0] > before)
        assert received == [event_name] and peer_events == []
        pixels(0, [0, 255, 0, 255])
        pixels(1, [255, 0, 0, 255])

        handled[0] = False
        before = draws[0]
        assert not deliver()
        pump_until(lambda: draws[0] > before)
        assert received == [event_name] * 2 and peer_events == []
        pixels(0, [0, 0, 255, 255])

        emitter.disconnect(receive)
        assert not deliver()
        application.process_events()
        assert received == [event_name] * 2 and peer_events == []
        pixels(0, [0, 0, 255, 255])

        emitter.connect(receive)
        handled[0] = True
        before = draws[0]
        assert deliver()
        pump_until(lambda: draws[0] > before)
        assert received == [event_name] * 3 and peer_events == []
        pixels(0, [0, 255, 0, 255])
        pixels(1, [255, 0, 0, 255])
    finally:
        for canvas in canvases:
            canvas.close()
        application.process_events()
        gc.collect()
        _dawn.process_events()
