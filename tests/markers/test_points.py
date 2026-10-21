"""Analytic GL point fixtures exercise batched native quad lowering."""

import numpy as np
import pytest

from vispy import _dawn, app, gloo
from vispy.visuals.markers import MarkersVisual

pytestmark = pytest.mark.gpu

VERTEX = """
attribute vec2 a_position;
attribute float a_size;
void main() { gl_Position=vec4(a_position,0.0,1.0); gl_PointSize=a_size; }
"""


def _render(positions, sizes, fragment, vertex=VERTEX):
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    try:
        with canvas:
            gloo.set_viewport(0, 0, 8, 8)
            gloo.set_clear_color((0, 0, 0, 1))
            gloo.clear(color=True, depth=True, stencil=True)
            program = gloo.Program(vertex, fragment)
            program["a_position"] = gloo.VertexBuffer(np.asarray(positions, np.float32))
            program["a_size"] = gloo.VertexBuffer(np.asarray(sizes, np.float32).reshape(-1, 1))
            program.draw("points")
            return gloo.read_pixels()
    finally:
        canvas.close()


def test_point_size_is_window_pixels():
    image = _render([[0, 0]], [4], "void main(){ gl_FragColor=vec4(0,1,0,1); }")
    expected = np.zeros((8, 8, 4), np.uint8)
    expected[..., 3] = 255
    expected[2:6, 2:6] = [0, 255, 0, 255]
    np.testing.assert_array_equal(image, expected)


def test_point_coordinate_origin_and_pixel_centers():
    image = _render([[0, 0]], [4], "void main(){ gl_FragColor=vec4(gl_PointCoord,0,1); }")
    values = np.array([32, 96, 159, 223], np.uint8)
    np.testing.assert_array_equal(image[2:6, 2:6, 0], np.broadcast_to(values, (4, 4)))
    np.testing.assert_array_equal(image[2:6, 2:6, 1], np.broadcast_to(values[:, None], (4, 4)))


def test_point_size_is_fixed_with_perspective_w():
    image = _render(
        [[0, 0]], [4], "void main(){ gl_FragColor=vec4(0,1,0,1); }",
        VERTEX.replace("1.0)", "2.0)"),
    )
    assert np.count_nonzero(image[..., 1] == 255) == 16


def test_point_center_outside_clip_volume_is_discarded():
    image = _render([[1.25, 0]], [8], "void main(){ gl_FragColor=vec4(0,1,0,1); }")
    assert np.all(image == [0, 0, 0, 255])


def test_points_use_per_point_attributes_in_one_draw():
    image = _render([[-0.5, 0], [0.5, 0]], [2, 4], "void main(){ gl_FragColor=vec4(0,1,0,1); }")
    expected = np.zeros((8, 8, 4), np.uint8)
    expected[..., 3] = 255
    expected[3:5, 1:3] = [0, 255, 0, 255]
    expected[2:6, 4:8] = [0, 255, 0, 255]
    np.testing.assert_array_equal(image, expected)


@pytest.mark.parametrize("size", [0.0, np.nan, np.inf])
def test_nonrenderable_point_sizes_do_not_cover_pixels(size):
    image = _render([[0, 0]], [size], "void main(){ gl_FragColor=vec4(0,1,0,1); }")
    assert np.all(image == [0, 0, 0, 255])


@pytest.mark.parametrize("method", ["points", "instanced"])
@pytest.mark.parametrize("spherical", [False, True])
def test_unmodified_marker_composer_builds_actual_admitted_pipeline(method, spherical):
    marker = MarkersVisual(method=method, spherical=spherical)
    marker.set_data(np.array([[0, 0]], np.float32), size=10, symbol="disc")
    marker._prepare_transforms(marker)
    marker._prepare_draw(marker)
    marker.view_program.build_if_needed()
    vertex, fragment = [shader.code for shader in marker.view_program.shaders]
    result = _dawn.compile_variant(
        vertex, fragment, has_depth=spherical, point_sprites=(method == "points"),
    )
    assert result["ok"], result["error"]
    assert result["pipeline"]
