# SPDX-License-Identifier: AGPL-3.0-only
"""Cursor-anchored zoom has independently expected world and pixel coordinates."""
import sys

import numpy as np
import pytest

from vispy import scene
from test_tkinter_panzoom_coordinates import application, assert_landmarks, assert_rect, wait

pytestmark = pytest.mark.gpu


def test_panzoom_wheel_direction_cursor_anchor_and_reverse(application):
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.bgcolor = '#101010'
        view.camera = scene.cameras.PanZoomCamera(rect=(-2, -1.5, 4, 3), aspect=None)
        # One normalized wheel unit halves/doubles the visible world dimensions.
        view.camera.zoom_factor = 2**(1/30)-1
        scene.visuals.Markers(pos=np.array([[0, 0], [-1, .5]], dtype=np.float32),
                              size=14, face_color=np.array([[1, 0, 0, 1], [0, 1, 0, 1]],
                                                          dtype=np.float32),
                              parent=view.scene)
        view.camera.rect = (-2, -1.5, 4, 3)
        canvas.update()
        wait(application, lambda: canvas._backend._photo is not None and
             canvas.native.winfo_viewable())
        assert tuple(view.size) == (240, 180)
        assert_landmarks(application, canvas, (240, 180), (120, 90), (60, 60))
        assert canvas.visual_at((90, 60)) is not None
        events = []
        canvas.events.mouse_wheel.connect(lambda event: events.append(
            (tuple(event.pos), tuple(event.delta))))
        raw_delta = 1 if sys.platform == 'darwin' else 120
        canvas.native.event_generate('<MouseWheel>', x=90, y=60, delta=raw_delta)
        assert events[-1] == ((90, 60), (0, 1))
        # Pixel(90,60) initially represents world(-.5,.5). Halving distances
        # about that point gives this literal rect; zooming about its center
        # would give(-1,-.75,2,1.5) and must fail.
        assert_rect(view.camera, (-1.25, -.5, 2, 1.5))
        assert_landmarks(application, canvas, (240, 180), (150, 120), (30, 60))
        canvas.native.event_generate('<MouseWheel>', x=90, y=60, delta=-raw_delta)
        assert events[-1] == ((90, 60), (0, -1))
        assert_rect(view.camera, (-2, -1.5, 4, 3))
        assert_landmarks(application, canvas, (240, 180), (120, 90), (60, 60))
    finally:
        canvas.close()
