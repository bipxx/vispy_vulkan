"""Render-state fixtures whose pixels depend on actual pipeline descriptors."""

import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu

POSITIONS = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
VERTEX = """
attribute vec2 a_position;
uniform float u_depth;
void main() { gl_Position=vec4(a_position,u_depth,1.0); }
"""
FRAGMENT = "uniform vec4 u_color; void main() { gl_FragColor=u_color; }"


@pytest.fixture
def scene():
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    try:
        with canvas:
            program = gloo.Program(VERTEX, FRAGMENT)
            program["a_position"] = gloo.VertexBuffer(POSITIONS)
            program["u_depth"] = 0.0
            gloo.set_viewport(0, 0, 8, 8)
            gloo.set_clear_color((0, 0, 0, 1))
            gloo.clear(color=True, depth=True, stencil=True)
            yield program
    finally:
        canvas.close()


def test_separate_rgb_and_alpha_blend_factors(scene):
    gloo.clear(color=(1, 0, 0, 64 / 255), depth=False, stencil=False)
    gloo.set_state(blend=True, depth_test=False)
    gloo.set_blend_func("src_alpha", "one_minus_src_alpha", "zero", "one")
    scene["u_color"] = (0, 0, 1, 0.5)
    scene.draw("triangles")
    image = gloo.read_pixels()
    assert np.all(np.abs(image[..., 0].astype(int) - 128) <= 1)
    assert np.all(np.abs(image[..., 2].astype(int) - 128) <= 1)
    assert np.all(image[..., 1] == 0)
    assert np.all(image[..., 3] == 64)


@pytest.mark.parametrize("write_depth,expected", [(True, [255, 0, 0, 255]), (False, [0, 0, 255, 255])])
def test_depth_test_and_write_mask(scene, write_depth, expected):
    gloo.set_state(depth_test=True, blend=False)
    gloo.set_depth_func("less")
    gloo.set_depth_mask(write_depth)
    scene["u_depth"] = -0.5
    scene["u_color"] = (1, 0, 0, 1)
    scene.draw("triangles")
    scene["u_depth"] = 0.5
    scene["u_color"] = (0, 0, 1, 1)
    scene.draw("triangles")
    assert np.all(gloo.read_pixels() == expected)


def test_color_write_mask_preserves_disabled_channels(scene):
    gloo.clear(color=(0, 0, 1, 1), depth=False, stencil=False)
    gloo.set_color_mask(True, False, True, False)
    scene["u_color"] = (1, 1, 0, 0)
    scene.draw("triangles")
    assert np.all(gloo.read_pixels() == [255, 0, 0, 255])


def test_scissor_limits_draw_coverage(scene):
    gloo.set_scissor(0, 0, 4, 8)
    gloo.set_state(scissor_test=True)
    scene["u_color"] = (0, 1, 0, 1)
    scene.draw("triangles")
    image = gloo.read_pixels()
    assert np.all(image[:, :4] == [0, 255, 0, 255])
    assert np.all(image[:, 4:] == [0, 0, 0, 255])


@pytest.mark.parametrize("front_face,expected", [("ccw", [0, 255, 0, 255]), ("cw", [0, 0, 0, 255])])
def test_front_face_and_backface_culling(scene, front_face, expected):
    gloo.set_state(cull_face=True)
    gloo.set_cull_face("back")
    gloo.set_front_face(front_face)
    scene["u_color"] = (0, 1, 0, 1)
    scene.draw("triangles")
    assert np.all(gloo.read_pixels() == expected)


def test_stencil_replace_then_equal_selects_marked_pixels(scene):
    gloo.set_state(stencil_test=True, scissor_test=True)
    gloo.set_scissor(0, 0, 4, 8)
    gloo.set_stencil_func("always", ref=1, mask=0xff)
    gloo.set_stencil_mask(0xff)
    gloo.set_stencil_op("keep", "keep", "replace")
    gloo.set_color_mask(False, False, False, False)
    scene["u_color"] = (1, 0, 0, 1)
    scene.draw("triangles")
    gloo.set_state(scissor_test=False)
    gloo.set_color_mask(True, True, True, True)
    gloo.set_stencil_func("equal", ref=1, mask=0xff)
    gloo.set_stencil_op("keep", "keep", "keep")
    scene["u_color"] = (0, 1, 0, 1)
    scene.draw("triangles")
    image = gloo.read_pixels()
    assert np.all(image[:, :4] == [0, 255, 0, 255])
    assert np.all(image[:, 4:] == [0, 0, 0, 255])


def test_constant_alpha_blend_factor_uses_alpha_for_rgb(scene):
    gloo.set_state(blend=True)
    gloo.set_blend_color((0.1, 0.2, 0.3, 0.5))
    gloo.set_blend_func("constant_alpha", "zero", "one", "zero")
    scene["u_color"] = (1, 1, 1, 1)
    scene.draw("triangles")
    image = gloo.read_pixels()
    assert np.all(np.abs(image[..., :3].astype(int) - 128) <= 1)
    assert np.all(image[..., 3] == 255)
