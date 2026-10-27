# SPDX-License-Identifier: AGPL-3.0-only
"""Literal image/overlay pixels through updates, recovery, resize and Tk panning."""
from pathlib import Path
import runpy

import numpy as np
import pytest

from test_tkinter_panzoom_coordinates import application, assert_rect, motion, wait

pytestmark = pytest.mark.gpu


def assert_points(application, canvas, size, points):
    previous = canvas._backend._photo
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not previous)
    assert tuple(canvas.size) == tuple(canvas.physical_size) == size
    pixels = canvas.render(alpha=True)
    assert pixels.shape == (size[1], size[0], 4) and pixels.dtype == np.uint8
    for x, y, rgba in points:
        np.testing.assert_array_equal(pixels[y-1:y+2, x-1:x+2],
                                      np.broadcast_to(rgba, (3, 3, 4)))
        assert canvas._backend._photo.get(x, y) == tuple(rgba[:3])


def test_image_overlay_updates_recovery_resize_and_pan(application):
    example = Path(__file__).resolve().parents[2] / 'examples/tk_image_overlay.py'
    create_scene = runpy.run_path(str(example), run_name='vispy_image_overlay_example')['create_scene']
    canvas, view, image, line = create_scene(application)
    try:
        wait(application, lambda: canvas._backend._photo is not None and canvas.native.winfo_viewable())
        assert tuple(view.size) == (240, 180)
        assert_rect(view.camera, (0, 0, 4, 3))
        assert_points(application, canvas, (240, 180), [
            (30, 30, [255, 0, 0, 255]), (180, 30, [0, 255, 0, 255]),
            (30, 150, [0, 0, 255, 255]), (180, 150, [255, 255, 0, 255]),
            (90, 105, [255, 255, 255, 255])])

        # Update the same visuals; both changed and vacated pixels are checked.
        data = np.array([[[0, 255, 255, 255], [0, 255, 0, 255]],
                         [[0, 0, 255, 255], [255, 255, 0, 255]]], dtype=np.uint8)
        image.set_data(data)
        line.set_data(pos=np.array([[.5, 2.25], [3.5, 2.25]], dtype=np.float32), color='magenta')
        mutated = [(30, 30, [0, 255, 255, 255]), (180, 30, [0, 255, 0, 255]),
                   (30, 150, [0, 0, 255, 255]), (180, 150, [255, 255, 0, 255]),
                   (90, 105, [0, 0, 255, 255]), (90, 135, [255, 0, 255, 255])]
        assert_points(application, canvas, (240, 180), mutated)

        with pytest.raises(TypeError, match='Complex data types not supported'):
            image.set_data(np.zeros((2, 2), dtype=np.complex64))
        assert_points(application, canvas, (240, 180), mutated)
        data[0, 0] = (255, 128, 0, 255)
        image.set_data(data)
        assert_points(application, canvas, (240, 180), [
            (30, 30, [255, 128, 0, 255]), (90, 135, [255, 0, 255, 255])])

        canvas.size = (360, 240)
        wait(application, lambda: tuple(view.size) == (360, 240))
        assert_rect(view.camera, (0, 0, 4, 3))
        assert_points(application, canvas, (360, 240), [
            (45, 40, [255, 128, 0, 255]), (270, 40, [0, 255, 0, 255]),
            (45, 200, [0, 0, 255, 255]), (270, 200, [255, 255, 0, 255]),
            (135, 180, [255, 0, 255, 255])])

        # At 90px/world X and 80px/world Y, right36/down24 shifts rect by(-.4,-.3).
        widget = canvas.native
        assert canvas.visual_at((20, 20)) is not None
        widget.event_generate('<ButtonPress-1>', x=20, y=20)
        motion(widget, 56, 44)
        widget.event_generate('<ButtonRelease-1>', x=56, y=44, state=0x100)
        assert_rect(view.camera, (-.4, -.3, 4, 3))
        assert_points(application, canvas, (360, 240), [
            (81, 64, [255, 128, 0, 255]), (306, 64, [0, 255, 0, 255]),
            (81, 224, [0, 0, 255, 255]), (306, 224, [255, 255, 0, 255]),
            (135, 180, [0, 0, 255, 255]), (171, 204, [255, 0, 255, 255])])
    finally:
        canvas.close()
