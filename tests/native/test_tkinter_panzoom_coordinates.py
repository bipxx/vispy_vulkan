# SPDX-License-Identifier: AGPL-3.0-only
"""Expected world/pixel coordinates through real Tk PanZoom input."""
import time

import numpy as np
import pytest

from vispy import scene
from test_tkinter_backend import application, wait

pytestmark = pytest.mark.gpu


def assert_rect(camera, expected):
    np.testing.assert_allclose(camera.rect.pos + camera.rect.size, expected,
                               rtol=0, atol=1e-6)


def assert_landmarks(application, canvas, size, red, green):
    previous = canvas._backend._photo
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not previous)
    assert tuple(canvas.size) == tuple(canvas.physical_size) == size
    image = canvas.render(alpha=True)
    assert image.shape == (size[1], size[0], 4)
    for (x, y), rgba in ((red, [255, 0, 0, 255]), (green, [0, 255, 0, 255])):
        np.testing.assert_array_equal(image[y-1:y+2, x-1:x+2],
                                      np.broadcast_to(rgba, (3, 3, 4)))
        assert canvas._backend._photo.get(x, y) == tuple(rgba[:3])


def motion(widget, x, y, state=0x100):
    # The common backend coalesces motion inside 10ms, independently of Tk.
    time.sleep(.012)
    widget.event_generate('<Motion>', x=x, y=y, state=state)


def test_panzoom_expected_coordinates_resize_and_cancelled_gestures(application):
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.bgcolor = '#101010'
        view.camera = scene.cameras.PanZoomCamera(rect=(-2, -1.5, 4, 3), aspect=None)
        scene.visuals.Markers(pos=np.array([[0, 0], [-1, .5]], dtype=np.float32),
                              size=14, face_color=np.array([[1, 0, 0, 1], [0, 1, 0, 1]],
                                                          dtype=np.float32),
                              parent=view.scene)
        view.camera.rect = (-2, -1.5, 4, 3)
        canvas.update()
        wait(application, lambda: canvas._backend._photo is not None and
             canvas.native.winfo_viewable())
        assert tuple(view.size) == (240, 180)
        assert_rect(view.camera, (-2, -1.5, 4, 3))
        # Fixed Cartesian landmarks, top-left image origin, no candidate-derived
        # projection or comparison with another candidate transform.
        assert_landmarks(application, canvas, (240, 180), (120, 90), (60, 60))
        assert canvas.visual_at((30, 30)) is not None
        seen = []
        for name in ('mouse_press', 'mouse_move', 'mouse_release'):
            getattr(canvas.events, name).connect(lambda event: seen.append(
                (event.type, tuple(event.pos), tuple(event.buttons))))
        widget = canvas.native
        widget.event_generate('<ButtonPress-1>', x=30, y=30)
        assert seen[-1] == ('mouse_press', (30, 30), (1,))
        motion(widget, 78, 66)
        assert seen[-1] == ('mouse_move', (78, 66), (1,))
        widget.event_generate('<ButtonRelease-1>', x=78, y=66, state=0x100)
        assert seen[-1] == ('mouse_release', (78, 66), ())
        # Drag right48/down36 in240x180 moves the world rect left.8/up.6.
        assert_rect(view.camera, (-2.8, -.9, 4, 3))
        assert_landmarks(application, canvas, (240, 180), (168, 126), (108, 96))
        motion(widget, 150, 100, state=0x100)
        assert seen[-1][2] == ()
        assert_rect(view.camera, (-2.8, -.9, 4, 3))

        # Resizing changes pixel scale while preserving the same world rect.
        canvas.size = (360, 240)
        wait(application, lambda: tuple(view.size) == (360, 240))
        assert_rect(view.camera, (-2.8, -.9, 4, 3))
        assert_landmarks(application, canvas, (360, 240), (252, 168), (162, 128))
        widget.event_generate('<ButtonPress-1>', x=90, y=60)
        motion(widget, 126, 84)
        # At360x240, right36/down24 moves the world rect left.4/up.3.
        assert_rect(view.camera, (-3.2, -.6, 4, 3))
        widget.event_generate('<FocusOut>')
        assert seen[-1][0] == 'mouse_release' and seen[-1][2] == ()
        motion(widget, 162, 108, state=0x100)
        assert seen[-1][2] == ()
        assert_rect(view.camera, (-3.2, -.6, 4, 3))
        assert_landmarks(application, canvas, (360, 240), (288, 192), (198, 152))

        # A new gesture recovers after cancellation. Outside release also ends it.
        widget.event_generate('<ButtonPress-1>', x=150, y=70)
        motion(widget, 126, 58)
        widget.event_generate('<ButtonRelease-1>', x=-5, y=-5, state=0x100)
        assert seen[-1] == ('mouse_release', (-5, -5), ())
        assert_rect(view.camera, (-44/15, -.75, 4, 3))
        assert_landmarks(application, canvas, (360, 240), (264, 180), (174, 140))
        motion(widget, 170, 110, state=0x100)
        assert seen[-1][2] == ()
        assert_rect(view.camera, (-44/15, -.75, 4, 3))
    finally:
        canvas.close()
