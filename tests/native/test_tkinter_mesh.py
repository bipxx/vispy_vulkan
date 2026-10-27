# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise the actual mesh example with literal projected landmark pixels."""
from pathlib import Path
import runpy

import numpy as np
import pytest

from test_tkinter_panzoom_coordinates import application, motion, wait
from test_tkinter_image_overlay import assert_points

pytestmark = pytest.mark.gpu


def test_mesh_example_updates_and_quarter_yaw(application):
    example = Path(__file__).resolve().parents[2] / 'examples/tk_mesh.py'
    factory = runpy.run_path(str(example), run_name='vispy_mesh_example')
    canvas, view, red, green = factory['create_scene'](application)
    try:
        wait(application, lambda: canvas._backend._photo is not None and
             canvas.native.winfo_viewable())
        # Height2 yields90pixels/world: x=120+90X, y=90-90Z.
        assert_points(application, canvas, (240, 180), [
            (60, 60, [255, 0, 0, 255]), (150, 120, [0, 255, 0, 255]),
            (60, 120, [0, 0, 0, 255])])
        vertices, faces = factory['cube_data']((-2/3, -1/3, -1/3))
        red.set_data(vertices=vertices, faces=faces, color='magenta')
        assert_points(application, canvas, (240, 180), [
            (60, 60, [0, 0, 0, 255]), (60, 120, [255, 0, 255, 255]),
            (150, 120, [0, 255, 0, 255])])
        # Restore position using the same visual, then rotate both meshes.
        vertices, faces = factory['cube_data']((-2/3, -1/3, 1/3))
        red.set_data(vertices=vertices, faces=faces, color='red')
        assert canvas.visual_at((30, 90)) is not None
        widget = canvas.native
        widget.event_generate('<ButtonPress-1>', x=30, y=90)
        motion(widget, 210, 90)
        widget.event_generate('<ButtonRelease-1>', x=210, y=90, state=0x100)
        np.testing.assert_allclose(view.camera.azimuth, -90, rtol=0, atol=1e-6)
        # Screen-right is now -Y, so the two X positions swap.
        assert_points(application, canvas, (240, 180), [
            (150, 60, [255, 0, 0, 255]), (60, 120, [0, 255, 0, 255]),
            (60, 60, [0, 0, 0, 255]), (150, 120, [0, 0, 0, 255])])
    finally:
        canvas.close()
