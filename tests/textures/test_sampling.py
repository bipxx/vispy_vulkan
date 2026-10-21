"""Pixel checks for allocation-preserving uploads and scientific samples."""

import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu

VERTEX = """
attribute vec2 a_position;
attribute vec2 a_texcoord;
varying vec2 v_texcoord;
void main() { v_texcoord=a_texcoord; gl_Position=vec4(a_position,0,1); }
"""
POSITIONS = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
COORDINATES = np.array([[0, 0], [2, 0], [0, 2]], np.float32)


def _sample(texture_factory, expression="texture2D(u_texture,v_texcoord)", dimensions=2):
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    try:
        with canvas:
            texture = texture_factory()
            program = gloo.Program(
                VERTEX,
                f"uniform sampler{dimensions}D u_texture; varying vec2 v_texcoord; void main() {{ gl_FragColor={expression}; }}",
            )
            program["a_position"] = gloo.VertexBuffer(POSITIONS)
            program["a_texcoord"] = gloo.VertexBuffer(COORDINATES)
            program["u_texture"] = texture
            gloo.set_viewport(0, 0, 8, 8)
            program.draw("triangles")
            return gloo.read_pixels()
    finally:
        canvas.close()


def test_partial_upload_keeps_allocation_and_untouched_texels():
    def texture_factory():
        pixels = np.zeros((8, 8, 4), np.uint8)
        pixels[..., 0] = pixels[..., 3] = 255
        texture = gloo.Texture2D(pixels, interpolation="nearest")
        patch = np.zeros((2, 2, 4), np.uint8)
        patch[..., 2] = patch[..., 3] = 255
        texture.set_data(patch, offset=(0, 0))
        return texture

    image = _sample(texture_factory)
    # Numpy upload y=0 is the lower texture edge; VisPy capture flips rows.
    expected = np.zeros((8, 8, 4), np.uint8)
    expected[..., 0] = expected[..., 3] = 255
    expected[-2:, :2] = [0, 0, 255, 255]
    np.testing.assert_array_equal(image, expected)


def test_r32f_sample_retains_scientific_range():
    image = _sample(
        lambda: gloo.Texture2D(np.full((2, 2, 1), 15, np.float32), internalformat="r32f"),
        "vec4(vec3((texture2D(u_texture,v_texcoord).r - 10.0) / 10.0),1.0)",
    )
    assert np.all(np.abs(image[..., :3].astype(int) - 128) <= 1)
    assert np.all(image[..., 3] == 255)


def test_float_nan_reaches_shader():
    image = _sample(
        lambda: gloo.Texture2D(np.full((2, 2, 1), np.nan, np.float32), internalformat="r32f"),
        "(isnan(texture2D(u_texture,v_texcoord).r) ? vec4(0,1,0,1) : vec4(1,0,0,1))",
    )
    assert np.all(image == [0, 255, 0, 255])


def test_3d_float_sample_preserves_range_and_dimension():
    image = _sample(
        lambda: gloo.Texture3D(np.full((2, 2, 2, 1), 15, np.float32), internalformat="r32f"),
        "vec4(vec3((texture3D(u_texture,vec3(v_texcoord,0.5)).r - 10.0) / 10.0),1.0)",
        dimensions=3,
    )
    assert np.all(np.abs(image[..., :3].astype(int) - 128) <= 1)
    assert np.all(image[..., 3] == 255)


@pytest.mark.parametrize("format_,pixels,expected", [
    ("luminance", [128], [128, 128, 128, 255]),
    ("alpha", [128], [0, 0, 0, 128]),
    ("luminance_alpha", [40, 200], [40, 40, 40, 200]),
    ("red", [128], [128, 0, 0, 255]),
    ("rg", [40, 200], [40, 200, 0, 255]),
    ("rgb", [10, 20, 30], [10, 20, 30, 255]),
])
def test_source_channel_semantics(format_, pixels, expected):
    image = _sample(lambda: gloo.Texture2D(np.array([[pixels]], np.uint8), format=format_))
    assert np.all(image == expected)


def test_linear_filter_interpolates_adjacent_texels():
    image = _sample(
        lambda: gloo.Texture2D(np.array([[[255, 0, 0, 255], [0, 0, 255, 255]]], np.uint8), interpolation="linear"),
        "texture2D(u_texture,vec2(0.5))",
    )
    assert np.all(np.abs(image[..., 0].astype(int) - 128) <= 1)
    assert np.all(np.abs(image[..., 2].astype(int) - 128) <= 1)
    assert np.all(image[..., 1] == 0)


@pytest.mark.parametrize("wrapping,expected", [
    ("repeat", [255, 0, 0, 255]),
    ("clamp_to_edge", [0, 0, 255, 255]),
    ("mirrored_repeat", [0, 0, 255, 255]),
])
def test_sampler_wrapping(wrapping, expected):
    image = _sample(
        lambda: gloo.Texture2D(np.array([[[255, 0, 0, 255], [0, 0, 255, 255]]], np.uint8), wrapping=wrapping),
        "texture2D(u_texture,vec2(1.25,0.5))",
    )
    assert np.all(image == expected)
