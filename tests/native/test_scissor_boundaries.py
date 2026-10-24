# SPDX-License-Identifier: AGPL-3.0-only
"""Exact pixel ownership for scissor boundaries, independent of any GUI toolkit."""
import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('samples', [0, 4])
@pytest.mark.parametrize('size', [(257, 129), (301, 177)])
@pytest.mark.parametrize('upper_right', [False, True])
def test_native_scissor_clear_has_no_partial_boundary_samples(samples, size, upper_right):
    width, height = size
    left, bottom = width // 2, height // 2
    canvas = app.Canvas(app='dawn_headless', size=size, config={'samples': samples})
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, width, height)
        gloo.set_state(scissor_test=False)
        gloo.clear(color=(0, 0, 1, 1))
        rectangle = (left, bottom, width - left, height - bottom) if upper_right else (0, 0, left, bottom)
        gloo.set_scissor(*rectangle)
        gloo.set_state(scissor_test=True)
        gloo.clear(color=(1, 0, 0, 1))
        actual = gloo.read_pixels((0, 0, width, height), alpha=True)
        expected = np.empty((height, width, 4), dtype=np.uint8)
        expected[:] = [0, 0, 255, 255]
        if upper_right:
            expected[:height - bottom, left:] = [255, 0, 0, 255]
        else:
            expected[height - bottom:, :left] = [255, 0, 0, 255]
        np.testing.assert_array_equal(actual, expected)
    finally:
        canvas.close()
