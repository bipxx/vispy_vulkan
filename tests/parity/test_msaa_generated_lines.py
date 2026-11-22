"""Check the full resolved image against the standard Vulkan sample grid."""

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu

WIDTH, HEIGHT = 32, 24
# The runtime renders into GL window row order and flips rows on readback.
SAMPLES = np.array([(6, 2), (14, 6), (2, 10), (10, 14)]) / 16


@contextmanager
def line_canvas():
    from vispy import _dawn, app, gloo

    canvas = app.Canvas(app="dawn_headless", size=(WIDTH, HEIGHT),
                        config={"samples": 4}, show=False)
    canvas.set_current()
    try:
        assert gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES) == 4
        gloo.set_viewport(0, 0, WIDTH, HEIGHT)
        gloo.set_state(blend=False)
        program = gloo.Program(
            "attribute vec3 a_pos; void main() { gl_Position = vec4(a_pos, 1.0); }",
            "uniform float u_alpha; void main() { gl_FragColor = vec4(1.0, 1.0, 1.0, u_alpha); }",
        )
        program["u_alpha"] = 1.0
        yield canvas, gloo, program
    finally:
        canvas.close()
        _dawn.process_events()


def set_endpoints(program, endpoints):
    from vispy import gloo

    clip = np.array(endpoints, dtype=np.float32)
    clip[:, :2] = clip[:, :2] / [WIDTH / 2, HEIGHT / 2] - 1
    program["a_pos"] = gloo.VertexBuffer(clip)


@pytest.fixture(scope="module")
def standard_sample_grid():
    """Check the grid independently using the native triangle rasterizer."""
    vertices = []
    for x, (sx, sy) in enumerate(SAMPLES):
        left, right = x + sx - 1 / 16, x + sx + 1 / 16
        bottom, top = sy - 1 / 16, sy + 1 / 16
        vertices.extend([(left, bottom, 0), (right, bottom, 0), (left, top, 0),
                         (left, top, 0), (right, bottom, 0), (right, top, 0)])
    # A control pixel verifies that the resolve and readback work.
    vertices.extend([(4, 0, 0), (5, 0, 0), (4, 1, 0),
                     (4, 1, 0), (5, 0, 0), (5, 1, 0)])
    with line_canvas() as (_, gloo, program):
        set_endpoints(program, vertices)
        gloo.clear(color=(0, 0, 0, 1))
        program.draw("triangles")
        probe = gloo.read_pixels((0, 0, 5, 1), alpha=False)[0, :, 0]
        assert probe[4] == 255
        if not np.all(probe[:4] == 64):
            pytest.skip(f"native triangles do not resolve the Vulkan standard 4x sample grid: {probe[:4]}")


def expected_image(endpoints, width, depth_test=False, smooth=False):
    """Resolve independently computed per-sample coverage and output alpha."""
    y, x = np.mgrid[:HEIGHT, :WIDTH]
    pixel = np.stack((x, y), axis=-1)[..., None, :] + SAMPLES
    a, b = np.asarray(endpoints)
    delta = b[:2] - a[:2]
    if not np.any(delta):
        return np.zeros((HEIGHT, WIDTH), dtype=np.uint8), 255
    relative = pixel - a[:2]
    length = np.linalg.norm(delta)
    along = relative @ (delta / length)
    across = relative @ (np.array([-delta[1], delta[0]]) / length)
    if smooth:
        side = np.clip(width / 2 + 0.5 - np.abs(across), 0, min(1, width))
        cap = np.clip(np.minimum(along, length - along) + 0.64, 0, min(1, length + 0.28))
        alpha = side * cap
        inside = alpha > 1 / 32
    else:
        inside = (along > 0) & (along < length) & (np.abs(across) < width / 2)
    if depth_test:
        # Clear depth is 0.5, so GL clip-space z/w must be negative.
        inside &= a[2] + (b[2] - a[2]) * (along / length) < 0
    rgb = np.rint(255 * inside.mean(axis=-1))[::-1].astype(np.uint8)
    if smooth:
        alpha = np.rint(255 * np.where(inside, alpha, 1).mean(axis=-1))[::-1].astype(np.uint8)
    else:
        alpha = 255
    return rgb, alpha


def assert_resolve(gloo, expected):
    image = gloo.read_pixels((0, 0, WIDTH, HEIGHT), alpha=True)
    rgb, alpha = expected
    rgb = np.broadcast_to(rgb[..., None], (HEIGHT, WIDTH, 3))
    np.testing.assert_allclose(image[..., :3], rgb, rtol=0, atol=1)
    if np.isscalar(alpha):
        np.testing.assert_array_equal(image[..., 3], alpha)
    else:
        np.testing.assert_allclose(image[..., 3], alpha, rtol=0, atol=1)


@pytest.mark.parametrize(
    "endpoints,width,smooth",
    [
        ([(5.27, 10.23, 0), (25.76, 10.23, 0)], 3.42, False),
        ([(25.81, 17.28, 0), (5.63, 4.19, 0)], 2.66, False),
        ([(5.63, 4.19, 0), (25.81, 17.28, 0)], 2.66, True),
        ([(15.24, 4.29, 0), (15.24, 19.77, 0)], 0.40, True),
    ],
)
def test_generated_line_resolves_rectangle_samples(standard_sample_grid, endpoints, width, smooth):
    with line_canvas() as (_, gloo, program):
        gloo.set_line_width(width)
        set_endpoints(program, endpoints)
        for enabled in (False, True, False) if smooth else (False,):
            gloo.set_state(line_smooth=enabled)
            gloo.clear(color=(0, 0, 0, 1))
            program.draw("lines")
            rgb, alpha = expected_image(endpoints, width, smooth=enabled)
            assert np.any((rgb > 0) & (rgb < 255))
            if enabled:
                assert np.any((alpha > 0) & (alpha < 255))
            assert_resolve(gloo, (rgb, alpha))


def test_generated_line_alpha_to_coverage():
    # The integer bounds fully cover every sample of the interior pixels.
    with line_canvas() as (_, gloo, program):
        program["u_alpha"] = 0.5
        gloo.set_line_width(4)
        set_endpoints(program, [(5, 10, 0), (25, 10, 0)])
        interior = np.zeros((HEIGHT, WIDTH), dtype=bool)
        interior[HEIGHT - 12:HEIGHT - 8, 5:25] = True
        for enabled in (False, True, False):
            gloo.set_state(line_smooth=False, sample_alpha_to_coverage=enabled)
            gloo.clear(color=(0, 0, 0, 1))
            program.draw("lines")
            image = gloo.read_pixels((0, 0, WIDTH, HEIGHT), alpha=True)
            background = image[~interior]
            foreground = image[interior]
            np.testing.assert_array_equal(background, np.broadcast_to([0, 0, 0, 255], background.shape))
            if enabled:
                # The mask and its spatial distribution are implementation-dependent.
                # Resolved RGB measures sample survival independently of output alpha.
                rgb = foreground[:, 0].astype(int)
                samples = np.rint(rgb * 4 / 255)
                assert np.any((samples > 0) & (samples < 4))
                expected = np.column_stack([samples * 255 / 4] * 3 + [255 - samples * 127 / 4])
                np.testing.assert_allclose(foreground, expected, rtol=0, atol=1)
            else:
                expected = np.broadcast_to([255, 255, 255, 128], foreground.shape)
                np.testing.assert_allclose(foreground, expected, rtol=0, atol=1)


def test_generated_line_depth_and_degenerate_recovery(standard_sample_grid):
    endpoints = [(5.27, 10.23, -0.46), (25.76, 10.23, 0.54)]
    width = 3.42
    with line_canvas() as (_, gloo, program):
        gloo.set_state(depth_test=True)
        gloo.set_depth_func("less")
        gloo.set_line_width(width)
        gloo.set_clear_depth(0.5)
        for segment in (endpoints, [endpoints[0]] * 2, endpoints):
            set_endpoints(program, segment)
            gloo.clear(color=(0, 0, 0, 1), depth=True)
            program.draw("lines")
            assert_resolve(gloo, expected_image(segment, width, depth_test=True))
