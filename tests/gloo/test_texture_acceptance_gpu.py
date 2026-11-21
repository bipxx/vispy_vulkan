# SPDX-License-Identifier: AGPL-3.0-only
"""Public gloo texture and drawing contracts on headless Dawn."""

import numpy as np
import pytest

from vispy import _dawn, app, gloo
from vispy.gloo.util import draw_texture


pytestmark = pytest.mark.gpu

VERTEX = """
attribute vec2 position;
varying vec2 uv;
void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    uv = position * vec2(0.5, -0.5) + 0.5;
}
"""
POSITIONS = np.array([[-1., -1.], [3., -1.], [-1., 3.]], dtype=np.float32)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
BLUE = (0, 0, 255, 255)
YELLOW = (255, 255, 0, 255)
CYAN = (0, 255, 255, 255)
MAGENTA = (255, 0, 255, 255)
BLACK = (0, 0, 0, 255)


@pytest.fixture
def target():
    canvas = app.Canvas(app='dawn_headless', size=(8, 6), show=False,
                        config={'samples': 0})
    try:
        canvas.set_current()
        gloo.set_state(blend=False, depth_test=False, stencil_test=False,
                       scissor_test=False, cull_face=False)
        gloo.set_viewport(0, 0, 8, 6)
        gloo.clear(color=(0, 0, 0, 1))
        yield canvas
    finally:
        canvas.close()
        _dawn.process_events()


def sample_program(texture, fragment):
    program = gloo.Program(VERTEX, fragment)
    program['position'] = POSITIONS
    program['image'] = texture
    return program


def draw_strip(program, expected):
    gloo.clear(color=(1, 1, 1, 1))
    program.draw('triangles')
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 5, 1), alpha=True),
                                  np.array([expected], dtype=np.uint8))


@pytest.fixture
def strip(request, target):
    texture = gloo.Texture1D(np.array([RED, GREEN, BLUE], dtype=np.uint8),
                             interpolation='nearest', wrapping=request.param)
    # Five pixel centers sample -1/6, 1/6, 1/2, 5/6 and 7/6.
    program = sample_program(texture, """
        uniform sampler1D image;
        varying vec2 uv;
        void main() { gl_FragColor = texture1D(image, uv.x * (5.0 / 3.0) - 1.0 / 3.0); }
    """)
    gloo.set_viewport(0, 0, 5, 1)
    return texture, program


@pytest.mark.parametrize('strip,expected', [
    ('clamp_to_edge', [RED, RED, GREEN, BLUE, BLUE]),
    ('repeat', [BLUE, RED, GREEN, BLUE, RED]),
], indirect=['strip'])
def test_texture1d_texel_order_and_wrapping(strip, expected):
    _, program = strip
    draw_strip(program, expected)


@pytest.mark.parametrize('strip', ['clamp_to_edge'], indirect=True)
def test_texture1d_rejects_subupload_and_patches_same_object(strip):
    texture, program = strip
    original = [RED, RED, GREEN, BLUE, BLUE]
    draw_strip(program, original)
    patch = np.array([YELLOW], dtype=np.uint8)
    with pytest.raises(ValueError, match='Data is too large'):
        texture.set_data(patch, offset=(3,))
    draw_strip(program, original)
    texture.set_data(patch, offset=(1,))
    draw_strip(program, [RED, RED, YELLOW, BLUE, BLUE])


def upload_region(atlas, expected, colors):
    region = atlas.get_free_region(2, 2)
    assert region is not None
    x, y, width, height = region
    assert (width, height) == (2, 2)
    assert 0 <= x <= atlas.width - width
    assert 0 <= y <= atlas.height - height
    pixels = expected[y:y + height, x:x + width]
    np.testing.assert_array_equal(pixels, np.broadcast_to(BLACK, (2, 2, 4)))
    pixels[:] = colors
    atlas.set_data(pixels[..., :3].copy(), offset=(y, x))


@pytest.fixture
def atlas_scene(target):
    atlas = gloo.TextureAtlas((4, 8), dtype=np.uint8)
    expected = np.empty((4, 8, 4), dtype=np.uint8)
    expected[:] = BLACK
    upload_region(atlas, expected, [[RED, GREEN], [BLUE, YELLOW]])
    upload_region(atlas, expected, [[CYAN, BLUE], [YELLOW, MAGENTA]])
    program = sample_program(atlas, """
        uniform sampler2D image;
        varying vec2 uv;
        void main() { gl_FragColor = texture2D(image, uv); }
    """)
    gloo.set_viewport(0, 0, 8, 4)
    return atlas, program, expected


def draw_atlas(program, expected):
    gloo.clear(color=(1, 1, 1, 1))
    program.draw('triangles')
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 4), alpha=True), expected)


def test_texture_atlas_upload_and_sampling(atlas_scene):
    _, program, expected = atlas_scene
    draw_atlas(program, expected)


def test_texture_atlas_refusal_preserves_regions_and_space(atlas_scene):
    atlas, program, expected = atlas_scene
    draw_atlas(program, expected)
    assert atlas.get_free_region(atlas.width + 1, 2) is None
    draw_atlas(program, expected)
    upload_region(atlas, expected, [[MAGENTA, CYAN], [GREEN, RED]])
    draw_atlas(program, expected)


@pytest.fixture
def offset_viewport(target):
    # Viewport origin is bottom-left, while readback row zero is at the top.
    gloo.set_viewport(1, 1, 4, 2)
    texture = gloo.Texture2D(np.array([[RED, GREEN], [BLUE, YELLOW]], dtype=np.uint8),
                             interpolation='nearest')
    expected = np.empty((6, 8, 4), dtype=np.uint8)
    expected[:] = BLACK
    expected[3, 1:5] = [RED, RED, GREEN, GREEN]
    expected[4, 1:5] = [BLUE, BLUE, YELLOW, YELLOW]
    return texture, expected


def test_draw_texture_orientation_and_offset_viewport(offset_viewport):
    texture, expected = offset_viewport
    draw_texture(texture)
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True), expected)


def test_draw_texture_bad_input_preserves_target_and_allows_redraw(offset_viewport):
    texture, expected = offset_viewport
    with pytest.raises(ValueError, match='Too few dimensions for texture'):
        draw_texture(np.array([255, 0, 0, 255], dtype=np.uint8))
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True),
                                  np.broadcast_to(BLACK, expected.shape))
    draw_texture(texture)
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True), expected)


def test_deleted_globject_buffer_draw_fails_and_peer_can_draw(target):
    program = gloo.Program(VERTEX, 'void main() { gl_FragColor = vec4(0, 1, 0, 1); }')
    retired = gloo.VertexBuffer(POSITIONS)
    peer = gloo.VertexBuffer(POSITIONS)
    program['position'] = retired
    expected = np.broadcast_to(GREEN, (6, 8, 4))
    program.draw('triangles')
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True), expected)

    # Upload the peer before retirement so recovery tests an existing owner.
    program['position'] = peer
    program.draw('triangles')
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True), expected)
    program['position'] = retired
    retired.delete()
    retired.delete()
    # A new batch observes retirement after the batch carrying DELETE.
    target.context.flush_commands()
    with pytest.raises(RuntimeError, match='ATTRIBUTE position: missing buffer'):
        program.draw('triangles')
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True), expected)

    gloo.clear(color=(0, 0, 0, 1))
    program['position'] = peer
    program.draw('triangles')
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 6), alpha=True), expected)
