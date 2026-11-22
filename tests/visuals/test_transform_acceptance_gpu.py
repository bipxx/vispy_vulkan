# SPDX-License-Identifier: AGPL-3.0-only
"""Analytic coordinate and rendered landmark checks for public transforms."""
from types import SimpleNamespace

import numpy as np
import pytest

from vispy import app, gloo
from vispy.geometry import Rect
from vispy.visuals.shaders import ModularProgram
from vispy.visuals.transforms import (
    BaseTransform, LogTransform, MatrixTransform, NullTransform,
    PanZoomTransform, PolarTransform, STTransform, TransformCache,
    TransformSystem, arg_to_array, arg_to_vec4, as_vec4, create_transform,
)


def test_arg_to_array_ragged_retry():
    class Receiver:
        @arg_to_array
        def receive(self, coords, scale, *, offset):
            return coords, coords * scale + offset

    receiver = Receiver()
    coords, result = receiver.receive([[1, 2], [3, 4]], 2, offset=1)
    assert isinstance(coords, np.ndarray) and coords.dtype == np.dtype(int)
    np.testing.assert_array_equal(result, [[3, 5], [7, 9]])
    with pytest.raises(ValueError, match='inhomogeneous'):
        receiver.receive([[1], [2, 3]], 2, offset=1)
    coords, result = receiver.receive(np.array([5], np.int16), 2, offset=-1)
    assert coords.dtype == np.int16
    np.testing.assert_array_equal(result, [9])


def test_arg_to_vec4_protocol_and_rejected_inputs():
    class Receiver:
        @arg_to_vec4
        def move(self, coords):
            assert coords.ndim == 2 and coords.shape[-1] == 4
            return coords + [2, 3, 0, 0]

    receiver = Receiver()
    np.testing.assert_array_equal(receiver.move((1, 2)), [3, 5, 0, 1])
    np.testing.assert_array_equal(receiver.move([[1, 2, 3], [4, 5, 6]]),
                                  [[3, 5, 3, 1], [6, 8, 6, 1]])
    assert receiver.move(Rect(1, 2, 4, 6)) == Rect(3, 5, 4, 6)
    for invalid in (object(), [1, 2, 3, 4, 5]):
        with pytest.raises(TypeError, match='convert'):
            receiver.move(invalid)
    np.testing.assert_array_equal(receiver.move([1, 2, 3, 4]), [3, 5, 3, 4])


def test_as_vec4_defaults_shape_dtype_and_retry():
    np.testing.assert_array_equal(as_vec4(2), [[2, 0, 0, 1]])
    np.testing.assert_array_equal(as_vec4([2, 3]), [[2, 3, 0, 1]])
    batch = np.array([[[2, 3], [4, 5]]], dtype=np.int16)
    promoted = as_vec4(batch, default=(1, 1, 7, 9))
    assert promoted.shape == (1, 2, 4) and promoted.dtype == np.int16
    np.testing.assert_array_equal(promoted, [[[2, 3, 7, 9], [4, 5, 7, 9]]])
    with pytest.raises(TypeError, match='cannot be converted to vec4'):
        as_vec4(np.ones((2, 5)))
    np.testing.assert_array_equal(as_vec4([5, 6, 7, 8]), [[5, 6, 7, 8]])


def test_create_transform_dispatch_and_unknown_name():
    with pytest.raises(KeyError, match='missing-transform'):
        create_transform('missing-transform')
    identity = create_transform('null')
    scale = create_transform('st', (2, 3), translate=(4, 5))
    matrix = create_transform('matrix', np.diag([2, 3, 1, 1]))
    assert type(identity) is NullTransform
    assert type(scale) is STTransform
    assert type(matrix) is MatrixTransform
    for transform, expected in ((identity, [1, 2, 0, 1]),
                                (scale, [6, 11, 0, 1]),
                                (matrix, [2, 6, 0, 1])):
        np.testing.assert_array_equal(transform.map([1, 2]), expected)


def test_transform_cache_order_refresh_and_eviction():
    cache = TransformCache(max_age=1)
    scale, move = STTransform(scale=(2, 3)), STTransform(translate=(4, 5))
    forward = cache.get([move, scale])
    reverse = cache.get([scale, move])
    assert cache.get([move, scale]) is forward and reverse is not forward
    np.testing.assert_array_equal(forward.map([1, 2]), [6, 11, 0, 1])
    np.testing.assert_array_equal(reverse.map([1, 2]), [10, 21, 0, 1])
    for _ in range(3):
        cache.roll()
        assert cache.get([move, scale]) is forward
    recreated = cache.get([scale, move])
    assert recreated is not reverse
    np.testing.assert_array_equal(recreated.map([1, 2]), [10, 21, 0, 1])


@pytest.fixture
def draw_transform():
    from vispy import _dawn

    canvas = app.Canvas(app='dawn_headless', size=(32, 32), show=False,
                        config={'samples': 0})
    canvas.set_current()
    programs = []

    def make(transform, *, sample=False):
        expression = ('vec4($transform(u_point).xy * vec2(0.1, 0.05) + 0.4, 0.0, 1.0)'
                      if sample else 'vec4(1.0, 0.0, 0.0, 1.0)')
        vertex = ('vec4(a_position, 0.0, 1.0)' if sample else
                  '$transform(vec4(a_position, 0.0, 1.0))')
        program = ModularProgram(
            'attribute vec2 a_position; void main() { gl_Position = ' + vertex + '; }',
            'uniform vec4 u_point; void main() { gl_FragColor = ' + expression + '; }',
        )
        programs.append(program)
        stage = program.frag if sample else program.vert
        stage['transform'] = transform
        program['a_position'] = np.array(
            [[-1, -1], [3, -1], [-1, 3]] if sample else
            [[0, 0], [0.25, 0], [0, 0.25]], np.float32)

        def render(point=None):
            if point is not None:
                program['u_point'] = point
            gloo.set_viewport(0, 0, 32, 32)
            gloo.set_state(blend=False, depth_test=False)
            gloo.clear(color=(0, 0, 0, 1))
            program.draw('triangles')
            return gloo.read_pixels((0, 0, 32, 32), alpha=True)

        return render

    try:
        yield make, canvas
    finally:
        for program in programs:
            program.delete()
        try:
            gloo.flush()
        finally:
            canvas.close()
            _dawn.process_events()


@pytest.mark.gpu
def test_base_transform_subclass_change_and_inverse(draw_transform):
    class Shift(BaseTransform):
        glsl_map = 'vec4 shift(vec4 p) { return p + vec4($delta, 0.0, 0.0, 0.0); }'
        glsl_imap = 'vec4 unshift(vec4 p) { return p - vec4($delta, 0.0, 0.0, 0.0); }'

        def __init__(self):
            super().__init__()
            self.set_delta(0.5)

        def set_delta(self, delta):
            self.delta = delta
            self.shader_map()['delta'] = delta
            self.shader_imap()['delta'] = delta
            self.update()

        @arg_to_vec4
        def map(self, coords):
            return coords + [self.delta, 0, 0, 0]

        @arg_to_vec4
        def imap(self, coords):
            return coords - [self.delta, 0, 0, 0]

    make, _ = draw_transform
    shift = Shift()
    composed = STTransform(scale=(2, 1)) * shift
    np.testing.assert_array_equal(composed.map([1, 2]), [3, 2, 0, 1])
    np.testing.assert_array_equal(shift.inverse.map([1, 2]), [0.5, 2, 0, 1])
    render = make(shift.inverse.shader_map())
    np.testing.assert_array_equal(render()[14, 9], [255, 0, 0, 255])
    changed = []

    def on_change(event):
        changed.append(event)

    shift.changed.connect(on_change)
    with pytest.raises(NotImplementedError):
        BaseTransform.map(shift, [1, 2])
    shift.set_delta(-0.5)
    assert len(changed) == 1
    image = render()
    np.testing.assert_array_equal(image[14, 25], [255, 0, 0, 255])
    np.testing.assert_array_equal(image[14, 9], [0, 0, 0, 255])


def _assert_mapped_pixel(render, point, expected):
    pixel = render(point)[16, 16]
    np.testing.assert_allclose(pixel, [*expected, 0, 255], atol=1)


@pytest.mark.gpu
def test_log_inverse_base_mutation_and_domain_recovery(draw_transform):
    make, _ = draw_transform
    transform = LogTransform((2, 10))
    render = make(transform.shader_imap(), sample=True)
    _assert_mapped_pixel(render, (2, 1, 0, 1), [204, 230])
    np.testing.assert_allclose(transform.imap([2., 1., 3., 1.]), [4, 10, 3, 1])
    np.testing.assert_allclose(transform.map([8, 100, 3, 1]), [3, 2, 3, 1])
    with np.errstate(invalid='ignore', divide='ignore'):
        assert np.isnan(transform.map([-1., 10.])[0])
        assert np.isneginf(transform.map([0., 10.])[0])
    transform.base = (3, 2)
    np.testing.assert_allclose(transform.imap([1., 2.]), [3, 4])
    transform.shader_imap()  # Refresh the uniform on the existing shader function.
    _assert_mapped_pixel(render, (1, 2, 0, 1), [179, 153])


@pytest.mark.gpu
def test_polar_inverse_quadrants_and_shape_retry(draw_transform):
    make, _ = draw_transform
    transform = PolarTransform()
    render = make(transform.shader_imap(), sample=True)
    for point, theta, red in (((2, 0), 0, 102), ((0, 2), np.pi / 2, 142),
                              ((-2, -2), -3 * np.pi / 4, 42)):
        radius = 2 if 0 in point else np.sqrt(8)
        _assert_mapped_pixel(render, (*point, 0, 1), [red, round(102 + 12.75 * radius)])
        np.testing.assert_allclose(transform.imap(np.array(point, float)), [theta, radius])
    with pytest.raises(IndexError):
        transform.imap([1.])
    np.testing.assert_allclose(transform.imap([0., -2.]), [-np.pi / 2, 2])
    _assert_mapped_pixel(render, (0, -2, 0, 1), [62, 128])


@pytest.mark.gpu
def test_matrix_mutation_singular_and_recovery(draw_transform):
    make, _ = draw_transform
    transform = MatrixTransform()
    render = make(transform.shader_map())
    np.testing.assert_array_equal(render()[14, 17], [255, 0, 0, 255])
    transform.translate((0.5, 0, 0))
    image = render()
    np.testing.assert_array_equal(image[14, 25], [255, 0, 0, 255])
    np.testing.assert_array_equal(image[14, 17], [0, 0, 0, 255])
    matrix = transform.matrix.copy()
    with pytest.raises(np.linalg.LinAlgError, match='Singular'):
        transform.scale((0, 1, 1))
    np.testing.assert_array_equal(transform.matrix, matrix)
    np.testing.assert_allclose(transform.map([1, 2]), [1.5, 2, 0, 1])
    np.testing.assert_allclose(transform.imap([1, 2]), [0.5, 2, 0, 1])
    np.testing.assert_array_equal(render(), image)
    transform.reset()
    np.testing.assert_allclose(transform.imap([1, 2]), [1, 2, 0, 1])
    np.testing.assert_array_equal(render()[14, 17], [255, 0, 0, 255])


@pytest.mark.gpu
def test_panzoom_events_and_interrupted_drag(draw_transform):
    make, canvas = draw_transform
    transform = PanZoomTransform(canvas, aspect=1)
    np.testing.assert_allclose(transform.scale, [1, 1, 1, 1])
    resize_sizes = []

    @canvas.events.resize.connect
    def record_resize(event):
        resize_sizes.append(event.size)

    canvas.size = (64, 32)
    if not resize_sizes:  # Older headless backends resize without emitting.
        canvas.events.resize(size=(64, 32), physical_size=(64, 32))
    assert resize_sizes == [(64, 32)]
    np.testing.assert_allclose(transform.scale, [1, 2, 1, 1])
    render = make(transform.shader_map())
    np.testing.assert_array_equal(render()[13, 17], [255, 0, 0, 255])
    canvas.events.mouse_wheel(pos=(32, 16), delta=(0, -10))
    np.testing.assert_allclose(transform.scale, [1, 2 * np.exp(0.1), 1, 1])

    def drag(start, end):
        press = canvas.events.mouse_press(pos=start, button=1)
        canvas.events.mouse_move(pos=end, press_event=press, last_event=press)
        canvas.events.mouse_release(pos=end, button=1, press_event=press)

    drag((0, 0), (16, 0))
    np.testing.assert_allclose(transform.translate, [0.5, 0, 0, 0])
    canvas.events.mouse_move(pos=(40, 0))
    np.testing.assert_allclose(transform.map([0, 0]), [0.5, 0, 0, 1])
    drag((40, 0), (8, 0))
    np.testing.assert_allclose(transform.map([0, 0]), [-0.5, 0, 0, 1])
    image = render()
    np.testing.assert_array_equal(image[13, 9], [255, 0, 0, 255])
    np.testing.assert_array_equal(image[13, 17], [0, 0, 0, 255])


@pytest.mark.gpu
def test_transform_system_hidpi_viewport_and_reconfiguration(draw_transform):
    make, _ = draw_transform
    dimensions = SimpleNamespace(size=(16, 16), physical_size=(32, 32))
    system = TransformSystem(canvas=dimensions)
    system.visual_transform = STTransform(translate=(8, 8))
    system.configure(viewport=(8, 8, 16, 16))
    np.testing.assert_allclose(system.get_transform('visual', 'document').map([1, 2]),
                               [9, 10, 0, 1])
    np.testing.assert_allclose(system.get_transform('canvas', 'framebuffer').map([4, 6]),
                               [8, 20, 0, 1])
    np.testing.assert_allclose(system.get_transform('framebuffer', 'canvas').map([8, 20]),
                               [4, 6, 0, 1])
    live = system.get_transform('visual', 'render')
    render = make(live.shader_map(), sample=True)
    _assert_mapped_pixel(render, (0, 0, 0, 1), [102, 102])
    with pytest.raises(ValueError, match='unknown'):
        system.get_transform('unknown', 'render')
    system.configure(fbo_rect=(0, 0, 32, 32), fbo_size=(64, 64),
                     viewport=(0, 0, 32, 32))
    system.visual_transform = STTransform(translate=(5, 11))
    np.testing.assert_allclose(system.get_transform('visual', 'render').map([0, 0]),
                               [0.25, 0.25, 0, 1])
    assert system.pixel_scale == 4
    _assert_mapped_pixel(render, (0, 0, 0, 1), [108, 105])
    _assert_mapped_pixel(render, (2, 2, 0, 1), [121, 99])
