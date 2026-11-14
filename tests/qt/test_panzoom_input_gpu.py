# SPDX-License-Identifier: AGPL-3.0-only
"""Qt-generated PanZoom gestures with literal Cartesian landmark oracles."""
from contextlib import contextmanager
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (240, 180)
INITIAL = (-2., -1.5, 4., 3.)


@contextmanager
def opened_scene():
    from vispy import _dawn, app, scene
    application = app.use_app('pyqt6')
    canvas = scene.SceneCanvas(app='pyqt6', size=SIZE, dpi=96, show=False,
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.bgcolor = '#101010'
        view.camera = scene.cameras.PanZoomCamera(rect=INITIAL, aspect=None)
        scene.visuals.Markers(
            pos=np.array([[0., 0.], [-1., .5]], np.float32), size=14,
            face_color=np.array([[1., 0., 0., 1.], [0., 1., 0., 1.]], np.float32),
            parent=view.scene)
        canvas.show()
        deadline = time.monotonic() + 5
        while tuple(view.size) != SIZE or not canvas.native.isVisible():
            application.process_events()
            assert time.monotonic() < deadline, 'Qt view layout timed out'
            time.sleep(.001)
        application.process_events()
        view.camera.rect = INITIAL
        yield application, canvas, view.camera
    finally:
        canvas.close()
        application.process_events()
        _dawn.process_events()


def assert_rect(camera, expected):
    np.testing.assert_allclose(camera.rect.pos + camera.rect.size, expected,
                               rtol=0, atol=1e-6)


def assert_landmarks(application, canvas, red, green):
    application.process_events()
    assert tuple(canvas.size) == SIZE
    # An explicit-size SceneCanvas render is the oracle. This does not assert
    # native display pixels, optical presentation or fractional-DPI behavior.
    image = canvas.render(size=SIZE, alpha=True)
    assert image.shape == (180, 240, 4)
    for (x, y), rgba in ((red, [255, 0, 0, 255]), (green, [0, 255, 0, 255])):
        np.testing.assert_array_equal(image[y-1:y+2, x-1:x+2],
                                      np.broadcast_to(rgba, (3, 3, 4)))
    return image


def mouse_event(widget, kind, position, pressed):
    from PyQt6 import QtCore, QtGui
    qt = QtCore.Qt
    pos = QtCore.QPointF(*position)
    global_pos = QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(*position)))
    button = qt.MouseButton.NoButton if kind == 'move' else qt.MouseButton.LeftButton
    event_type = {'press': QtCore.QEvent.Type.MouseButtonPress,
                  'move': QtCore.QEvent.Type.MouseMove,
                  'release': QtCore.QEvent.Type.MouseButtonRelease}[kind]
    event = QtGui.QMouseEvent(event_type, pos, global_pos, button,
                              qt.MouseButton.LeftButton if pressed else qt.MouseButton.NoButton,
                              qt.KeyboardModifier.NoModifier)
    if kind == 'move':
        # Allow the common backend's documented 10ms motion coalescing window.
        time.sleep(.015)
    QtCore.QCoreApplication.sendEvent(widget, event)
    return event


def test_qt_delivered_pan_moves_literal_landmarks_release_stops_and_new_drag_recovers():
    with opened_scene() as (application, canvas, camera):
        before = assert_landmarks(application, canvas, (120, 90), (60, 60))
        assert_rect(camera, INITIAL)
        events = []  # Retain Qt event objects used by VisPy's press/last chain.
        delivered_moves = []
        canvas.events.mouse_move.connect(
            lambda event: delivered_moves.append(tuple(event.pos)))
        events.append(mouse_event(canvas.native, 'press', (30, 30), True))
        events.append(mouse_event(canvas.native, 'move', (78, 66), True))
        events.append(mouse_event(canvas.native, 'release', (78, 66), False))
        assert_rect(camera, (-2.8, -.9, 4., 3.))
        assert_landmarks(application, canvas, (168, 126), (108, 96))
        # A move carrying a stale button bit must not continue a released drag.
        before_moves = len(delivered_moves)
        events.append(mouse_event(canvas.native, 'move', (150, 100), True))
        assert len(delivered_moves) == before_moves + 1
        assert delivered_moves[-1] == (150, 100)
        assert_rect(camera, (-2.8, -.9, 4., 3.))
        events.append(mouse_event(canvas.native, 'press', (90, 60), True))
        events.append(mouse_event(canvas.native, 'move', (114, 78), True))
        events.append(mouse_event(canvas.native, 'release', (114, 78), False))
        assert_rect(camera, (-3.2, -.6, 4., 3.))
        assert_landmarks(application, canvas, (192, 144), (132, 114))
        camera.rect = INITIAL
        np.testing.assert_array_equal(
            assert_landmarks(application, canvas, (120, 90), (60, 60)), before)


def test_qt_delivered_wheel_is_cursor_anchored_and_reverse_restores_literal_landmarks():
    from PyQt6 import QtCore, QtGui
    with opened_scene() as (application, canvas, camera):
        before = assert_landmarks(application, canvas, (120, 90), (60, 60))
        # One normalized notch halves/doubles the visible world dimensions.
        camera.zoom_factor = 2**(1/30)-1
        events = []
        for delta, rect, red, green in (
                (120, (-1.25, -.5, 2., 1.5), (150, 120), (30, 60)),
                (-120, INITIAL, (120, 90), (60, 60))):
            pos = QtCore.QPointF(90, 60)
            global_pos = QtCore.QPointF(canvas.native.mapToGlobal(QtCore.QPoint(90, 60)))
            event = QtGui.QWheelEvent(pos, global_pos, QtCore.QPoint(), QtCore.QPoint(0, delta),
                                      QtCore.Qt.MouseButton.NoButton,
                                      QtCore.Qt.KeyboardModifier.NoModifier,
                                      QtCore.Qt.ScrollPhase.NoScrollPhase, False)
            events.append(event)
            QtCore.QCoreApplication.sendEvent(canvas.native, event)
            # Cursor(90,60) represents world(-.5,.5), not the view's center.
            assert_rect(camera, rect)
            image = assert_landmarks(application, canvas, red, green)
        np.testing.assert_array_equal(image, before)
