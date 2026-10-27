# SPDX-License-Identifier: AGPL-3.0-only
"""Actual volume example output through data and rendering-method changes."""
from pathlib import Path
import runpy

import numpy as np
import pytest

from test_tkinter_panzoom_coordinates import application, wait
from test_tkinter_image_overlay import assert_points

pytestmark = pytest.mark.gpu


def test_volume_example_updates_methods_and_invalid_data(application):
    example = Path(__file__).resolve().parents[2] / 'examples/tk_volume.py'
    factory = runpy.run_path(str(example), run_name='vispy_volume_example')
    canvas, view, volume = factory['create_scene'](application)
    try:
        wait(application, lambda: canvas._backend._photo is not None and
             canvas.native.winfo_viewable())
        # Height40 gives4.5pixels/world. Block centers(X,Z)=(8.5,22.5),
        # (22.5,8.5) project to(88.5,58.5),(151.5,121.5), respectively.
        # The integer sample centers and their3x3patches are inside the blocks.
        white, black = [255, 255, 255, 255], [0, 0, 0, 255]
        assert_points(application, canvas, (240, 180), [
            (89, 59, white), (152, 122, white), (152, 59, black),
            (120, 90, black), (20, 20, black)])
        data = factory['volume_data']()
        data[20:26, 12:20, 6:12] = 0
        data[20:26, 12:20, 20:26] = 1
        volume.set_data(data, clim=(0, 1))
        updated = [(89, 59, black), (152, 122, white), (152, 59, white),
                   (120, 90, black), (20, 20, black)]
        assert_points(application, canvas, (240, 180), updated)

        # Every ray through a block also meets zero-valued voxels along Y.
        volume.method = 'minip'
        assert_points(application, canvas, (240, 180), [
            (89, 59, black), (152, 122, black), (152, 59, black)])
        volume.method = 'mip'
        assert_points(application, canvas, (240, 180), updated)

        with pytest.raises(ValueError, match='Volume render method should be'):
            volume.method = 'not-a-volume-method'
        assert volume.method == 'mip'
        with pytest.raises(ValueError, match='Volume visual needs a 3D array'):
            volume.set_data(np.ones((32, 32), dtype=np.float32))
        assert_points(application, canvas, (240, 180), updated)
        # A valid update after both rejected calls uses the same visual.
        volume.set_data(factory['volume_data'](), clim=(0, 1))
        assert_points(application, canvas, (240, 180), [
            (89, 59, white), (152, 122, white), (152, 59, black)])
    finally:
        canvas.close()
