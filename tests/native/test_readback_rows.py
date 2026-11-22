"""B19: color reads of 8-bit RGBA storage copy rows directly; every stored byte must come back unchanged."""
import numpy as np
import pytest

from vispy import _dawn, app, gloo
from vispy.gloo.dawn_parser import read_pixels_dawn

pytestmark = pytest.mark.gpu


def test_slow_readback_times_out_and_same_canvas_recovers():
    with app.Canvas(app="dawn_headless", size=(4, 3), show=False):
        viewport = (0, 0, 4, 3)
        gloo.clear(color=(1, 0, 0, 1))
        np.testing.assert_array_equal(
            gloo.read_pixels(viewport), np.full((3, 4, 4), (255, 0, 0, 255), dtype=np.uint8)
        )
        generation = _dawn.probe()["device_generation"]

        gloo.clear(color=(0, 1, 0, 1))
        _dawn.diagnostic_timeout_next_readback()
        with pytest.raises(RuntimeError, match="Dawn callback wait timed out"):
            gloo.read_pixels(viewport)

        np.testing.assert_array_equal(
            gloo.read_pixels(viewport), np.full((3, 4, 4), (0, 255, 0, 255), dtype=np.uint8)
        )
        assert _dawn.probe()["device_generation"] == generation


def test_color_reads_return_every_stored_byte_with_and_without_alpha():
    # Each channel of each row holds all 256 byte values, offset differently, so a swizzle, a row-order or an
    # alpha-drop error changes the result.
    width, height = 256, 4
    columns = np.arange(width)
    data = np.empty((height, width, 4), np.uint8)
    for row in range(height):
        for channel in range(4):
            data[row, :, channel] = (columns + 67 * channel + 31 * row) % 256
    canvas = app.Canvas(app="dawn_headless", size=(width, height), show=False)
    with canvas:
        fbo = gloo.FrameBuffer(color=gloo.Texture2D(data))
        with fbo:
            viewport = (0, 0, width, height)
            rgba = gloo.read_pixels(viewport=viewport)
            rgb = gloo.read_pixels(viewport=viewport, alpha=False)
            floats = gloo.read_pixels(viewport=viewport, out_type="float")
            uncopied = read_pixels_dawn(viewport, True, "color", copy=False)
    canvas.close()
    expected = data[::-1]  # read_pixels puts the framebuffer's top row first
    print("first row", rgba[0, :4].tolist(), "owndata", rgba.flags.owndata, uncopied.flags.owndata)
    assert rgba.dtype == np.uint8 and rgba.shape == (height, width, 4)
    assert np.array_equal(rgba, expected)
    assert np.array_equal(rgb, expected[..., :3])
    assert np.array_equal(uncopied, expected)
    # The float read keeps the per-texel conversion; both agree on every byte.
    assert floats.dtype == np.float32
    assert np.array_equal(floats, expected.astype(np.float32) / np.float32(255))
    # gloo.read_pixels returns its own copy; the Qt readback path takes the native array as is.
    assert rgba.flags.owndata and not uncopied.flags.owndata
