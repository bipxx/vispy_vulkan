# SPDX-License-Identifier: AGPL-3.0-only
"""GL-shaped state operations must preserve actual GLIR rendering order."""
import numpy as np
import pytest

from vispy import app, gloo, _dawn
from vispy.gloo import gl
from vispy.gloo.gl.dawn import DawnCompatibilityError

pytestmark = pytest.mark.gpu

FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)


@pytest.fixture
def raw_scene(request):
    samples = getattr(request, 'param', 0)
    canvas = app.Canvas(app='dawn_headless', size=(16, 12), config={'samples': samples})
    canvas.set_current()
    canvas.context.set_viewport(0, 0, 16, 12)
    program = gloo.Program('attribute vec2 a_position; uniform float u_depth; '
                           'void main(){gl_Position=vec4(a_position,u_depth,1.0);}',
                           'uniform vec4 u_color; void main(){gl_FragColor=u_color;}')
    source = gloo.VertexBuffer(FULL)
    program['a_position'] = source
    program['u_depth'] = 0.
    program['u_color'] = (0, 1, 0, 1)
    gl.glClearColor(0, 0, 0, 1)
    gl.glClearDepth(1.)
    gl.glClearStencil(0)
    gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT) | int(gl.GL_STENCIL_BUFFER_BIT))
    configuration = _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)
    assert configuration['samples'] == samples and configuration['configuration_source'] == 'allocated_target'
    try:
        yield canvas, program, source
    finally:
        program.delete()
        source.delete()
        canvas.context.flush_commands()
        canvas.close()


def pixels():
    return gloo.read_pixels((0, 0, 16, 12), alpha=True)


@pytest.mark.parametrize('comparison,passes', [
    (gl.GL_NEVER, False), (gl.GL_LESS, False), (gl.GL_EQUAL, True), (gl.GL_LEQUAL, True),
    (gl.GL_GREATER, False), (gl.GL_NOTEQUAL, False), (gl.GL_GEQUAL, True), (gl.GL_ALWAYS, True),
])
def test_raw_depth_comparisons_at_exact_far_endpoint(raw_scene, comparison, passes):
    _, program, _ = raw_scene
    gl.glEnable(int(gl.GL_DEPTH_TEST))
    gl.glDepthFunc(int(comparison))
    program['u_depth'] = 1.
    program.draw('triangles')
    assert np.all(pixels() == ([0, 255, 0, 255] if passes else [0, 0, 0, 255]))


@pytest.mark.parametrize('write_depth,expected', [(True, [255, 0, 0, 255]), (False, [0, 0, 255, 255])])
def test_raw_depth_write_mask_and_queued_draw_order(raw_scene, write_depth, expected):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LESS)
    gl.glDepthMask(write_depth)
    program['u_depth'], program['u_color'] = -.5, (1, 0, 0, 1)
    program.draw('triangles')
    program['u_depth'], program['u_color'] = .5, (0, 0, 1, 1)
    program.draw('triangles')
    assert np.all(pixels() == expected)


def test_raw_depth_range_clamping_and_invalid_recovery(raw_scene):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LESS)
    gl.glClearDepth(.6)
    gl.glClear(gl.GL_DEPTH_BUFFER_BIT)
    gl.glDepthRange(.5, 1.)  # NDC zero becomes .75 and fails against .6.
    program.draw('triangles')
    assert np.all(pixels() == [0, 0, 0, 255])
    with pytest.raises(RuntimeError, match='glDepthRange'):
        gl.glDepthRange(float('nan'), 1.)
    with pytest.raises(RuntimeError, match='glDepthFunc'):
        gl.glDepthFunc(123456)
    program.draw('triangles')
    assert np.all(pixels() == [0, 0, 0, 255])
    gl.glDepthRange(-2., 3.)  # Clamps to [0,1], so the next .5 passes.
    program.draw('triangles')
    assert np.all(pixels() == [0, 255, 0, 255])


@pytest.mark.parametrize('equation,expected', [
    (gl.GL_FUNC_ADD, [255, 191, 255, 191]),
    (gl.GL_FUNC_SUBTRACT, [0, 64, 64, 64]),
    (gl.GL_FUNC_REVERSE_SUBTRACT, [128, 0, 0, 0]),
    (gl.GL_MIN, [64, 64, 128, 64]), (gl.GL_MAX, [191, 128, 191, 128]),
])
def test_raw_blend_equations_and_integer_enums(raw_scene, equation, expected):
    _, program, _ = raw_scene
    gloo.clear(color=(.75, .25, .5, .25))
    gl.glEnable(int(gl.GL_BLEND))
    # Min/max ignore factors; zero deliberately exposes incorrect lowering.
    factor = gl.GL_ZERO if equation in (gl.GL_MIN, gl.GL_MAX) else gl.GL_ONE
    gl.glBlendFunc(int(factor), int(factor))
    gl.glBlendEquation(int(equation))
    program['u_color'] = (.25, .5, .75, .5)
    program.draw('triangles')
    assert np.all(np.abs(pixels().astype(int) - expected) <= 1)


def test_raw_separate_blend_and_constant_updates(raw_scene):
    _, program, _ = raw_scene
    gloo.clear(color=(1, 0, 0, 64 / 255))
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_ZERO, gl.GL_ONE)
    gl.glBlendEquationSeparate(gl.GL_FUNC_ADD, gl.GL_FUNC_REVERSE_SUBTRACT)
    program['u_color'] = (0, 0, 1, .5)
    program.draw('triangles')
    image = pixels()
    assert np.all(np.abs(image[..., :3].astype(int) - [128, 0, 128]) <= 1)
    assert np.all(image[..., 3] == 64)
    # Make the alpha equation independently observable: ADD would produce .75,
    # while reverse-subtract clamps .25 - .5 to zero. The preceding phase
    # separately proves that alpha factors differ from the RGB factors.
    gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_ONE, gl.GL_ONE)
    gloo.clear(color=(1, 0, 0, 64 / 255))
    program.draw('triangles')
    assert np.all(pixels()[..., 3] == 0)
    gl.glBlendEquation(gl.GL_FUNC_ADD)
    gl.glBlendFunc(gl.GL_CONSTANT_ALPHA, gl.GL_ZERO)
    gl.glEnable(gl.GL_SCISSOR_TEST)
    program['u_color'] = (1, 1, 1, 1)
    for x, alpha in ((0, .25), (8, .75)):
        gl.glScissor(x, 0, 8, 12)
        gl.glBlendColor(.1, .2, .3, alpha)
        program.draw('triangles')
    gl.glDisable(gl.GL_SCISSOR_TEST)
    image = pixels().astype(int)
    assert np.all(np.abs(image[:, :8] - 64) <= 1)
    assert np.all(np.abs(image[:, 8:] - 191) <= 1)


@pytest.mark.parametrize('front,cull,visible', [
    (gl.GL_CCW, gl.GL_BACK, True), (gl.GL_CW, gl.GL_BACK, False),
    (gl.GL_CCW, gl.GL_FRONT, False), (gl.GL_CW, gl.GL_FRONT, True),
    (gl.GL_CCW, gl.GL_FRONT_AND_BACK, False),
])
def test_raw_culling_and_front_face(raw_scene, front, cull, visible):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_CULL_FACE)
    gl.glFrontFace(front)
    gl.glCullFace(cull)
    program.draw('triangles')
    assert np.all(pixels() == ([0, 255, 0, 255] if visible else [0, 0, 0, 255]))


def test_raw_stencil_masked_replace_and_masked_clear(raw_scene):
    _, program, _ = raw_scene
    gl.glClearStencil(0x30)
    gl.glClear(gl.GL_STENCIL_BUFFER_BIT)
    gl.glEnable(gl.GL_STENCIL_TEST)
    gl.glStencilMask(0x0f)
    gl.glStencilFunc(gl.GL_ALWAYS, 0x0f, 0xff)
    gl.glStencilOp(gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE)
    gl.glColorMask(False, False, False, False)
    program.draw('triangles')
    gl.glColorMask(True, True, True, True)
    gl.glStencilFunc(gl.GL_EQUAL, 0x3f, 0xff)
    gl.glStencilOp(gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP)
    program.draw('triangles')
    assert np.all(pixels() == [0, 255, 0, 255])
    gl.glClearStencil(0)
    gl.glClear(gl.GL_STENCIL_BUFFER_BIT)  # Only low four bits clear; 0x30 survives.
    gl.glStencilFunc(gl.GL_EQUAL, 0x30, 0xff)
    program['u_color'] = (0, 0, 1, 1)
    program.draw('triangles')
    assert np.all(pixels() == [0, 0, 255, 255])


def test_raw_distinct_front_back_stencil_state(raw_scene):
    _, program, source = raw_scene
    gl.glEnable(gl.GL_STENCIL_TEST)
    gl.glEnable(gl.GL_SCISSOR_TEST)
    for face, reference, x, positions in ((gl.GL_FRONT, 3, 0, FULL), (gl.GL_BACK, 7, 8, FULL[::-1])):
        gl.glStencilFuncSeparate(face, gl.GL_ALWAYS, reference, 0xff)
        gl.glStencilMaskSeparate(face, 0xff)
        gl.glStencilOpSeparate(face, gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE)
        gl.glScissor(x, 0, 8, 12)
        gl.glColorMask(False, False, False, False)
        source.set_data(positions)
        program.draw('triangles')
    gl.glDisable(gl.GL_SCISSOR_TEST)
    gl.glColorMask(True, True, True, True)
    for face, reference, color, positions in ((gl.GL_FRONT, 3, (0, 1, 0, 1), FULL),
                                              (gl.GL_BACK, 7, (0, 0, 1, 1), FULL[::-1])):
        gl.glStencilFuncSeparate(face, gl.GL_EQUAL, reference, 0xff)
        gl.glStencilOpSeparate(face, gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP)
        source.set_data(positions)
        program['u_color'] = color
        program.draw('triangles')
    image = pixels()
    assert np.all(image[:, :8] == [0, 255, 0, 255])
    assert np.all(image[:, 8:] == [0, 0, 255, 255])


STENCIL_VALUES = [
    pytest.param(gl.GL_KEEP, 0x35, 0xa6, 0xff, 0x35, id='keep'),
    pytest.param(gl.GL_ZERO, 0x35, 0xa6, 0xff, 0x00, id='zero'),
    pytest.param(gl.GL_REPLACE, 0x35, 0xa6, 0xff, 0xa6, id='replace'),
    pytest.param(gl.GL_INVERT, 0x35, 0xa6, 0xff, 0xca, id='invert'),
    pytest.param(gl.GL_INCR, 0x35, 0xa6, 0xff, 0x36, id='increment'),
    pytest.param(gl.GL_INCR, 0xff, 0xa6, 0xff, 0xff, id='increment-saturates'),
    pytest.param(gl.GL_DECR, 0x35, 0xa6, 0xff, 0x34, id='decrement'),
    pytest.param(gl.GL_DECR, 0x00, 0xa6, 0xff, 0x00, id='decrement-saturates'),
    pytest.param(gl.GL_INCR_WRAP, 0xff, 0xa6, 0xff, 0x00, id='increment-wraps'),
    pytest.param(gl.GL_INCR_WRAP, 0x35, 0xa6, 0xff, 0x36, id='increment-wrap-interior'),
    pytest.param(gl.GL_DECR_WRAP, 0x00, 0xa6, 0xff, 0xff, id='decrement-wraps'),
    pytest.param(gl.GL_DECR_WRAP, 0x35, 0xa6, 0xff, 0x34, id='decrement-wrap-interior'),
    pytest.param(gl.GL_INVERT, 0xa5, 0xa6, 0x0f, 0xaa, id='masked-invert'),
    pytest.param(gl.GL_INCR, 0xaf, 0xa6, 0x0f, 0xa0, id='increment-before-mask'),
    pytest.param(gl.GL_DECR, 0xa0, 0xa6, 0x0f, 0xaf, id='decrement-before-mask'),
    pytest.param(gl.GL_REPLACE, 0xa5, 0x3c, 0x0f, 0xac, id='masked-replace'),
]


def assert_stencil_value(program, face, expected):
    """Observe stored stencil through independently expected color visibility."""
    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glColorMask(True, True, True, True)
    gl.glStencilMaskSeparate(face, 0)
    gl.glStencilOpSeparate(face, gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP)
    gloo.clear(color=(0, 0, 0, 1), depth=False, stencil=False)
    for reference, color in ((expected, (0, 1, 0, 1)),
                             (expected ^ 0xff, (1, 0, 0, 1))):
        gl.glStencilFuncSeparate(face, gl.GL_EQUAL, reference, 0xff)
        program['u_color'] = color
        program.draw('triangles')
        # The complementary reference must not overwrite the successful probe.
        np.testing.assert_array_equal(pixels(), np.broadcast_to([0, 255, 0, 255], (12, 16, 4)))


@pytest.mark.parametrize('routing', ['shared', 'split'])
@pytest.mark.parametrize('operation,seed,reference,mask,expected', STENCIL_VALUES)
@pytest.mark.parametrize('branch', ['stencil-fail', 'depth-fail', 'pass'])
@pytest.mark.parametrize('face', [gl.GL_FRONT, gl.GL_BACK], ids=['front', 'back'])
def test_raw_stencil_operation_values_and_boundaries(raw_scene, face, branch, routing,
                                                     operation, seed, reference, mask, expected):
    canvas, program, source = raw_scene
    config = _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)
    assert config['stencil_size'] == 8 and config['depth_stencil_format'] == 'depth24plus-stencil8'
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glFrontFace(gl.GL_CCW)
    source.set_data(FULL if face == gl.GL_FRONT else FULL[::-1])
    gl.glStencilMask(0xff)
    gl.glClearStencil(seed)
    gl.glClear(gl.GL_STENCIL_BUFFER_BIT)
    gl.glEnable(gl.GL_STENCIL_TEST)
    other = gl.GL_BACK if face == gl.GL_FRONT else gl.GL_FRONT
    gl.glStencilFuncSeparate(other, gl.GL_NEVER, reference, 0xff)
    gl.glStencilMaskSeparate(other, mask if routing == 'shared' else 0)
    gl.glStencilOpSeparate(other, gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP)
    gl.glStencilFuncSeparate(face, gl.GL_NEVER if branch == 'stencil-fail' else gl.GL_ALWAYS,
                            reference, 0xff)
    gl.glStencilMaskSeparate(face, mask)
    operations = [gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP]
    operations[['stencil-fail', 'depth-fail', 'pass'].index(branch)] = operation
    gl.glStencilOpSeparate(face, *operations)
    gl.glEnable(gl.GL_DEPTH_TEST)
    # Both comparisons fail in the first branch, proving stencil-fail priority.
    gl.glDepthFunc(gl.GL_ALWAYS if branch == 'pass' else gl.GL_NEVER)
    gl.glDepthMask(False)
    gl.glColorMask(False, False, False, False)
    # These exact native fields select one pipeline or ordered face projection.
    cid = canvas._backend._dawn_canvas_id
    front = tuple(_dawn.state_parameter(cid, int(selector)) for selector in
                  (gl.GL_STENCIL_REF, gl.GL_STENCIL_VALUE_MASK, gl.GL_STENCIL_WRITEMASK))
    back = tuple(_dawn.state_parameter(cid, int(selector)) for selector in
                 (gl.GL_STENCIL_BACK_REF, gl.GL_STENCIL_BACK_VALUE_MASK, gl.GL_STENCIL_BACK_WRITEMASK))
    assert (front == back) is (routing == 'shared')
    program.draw('triangles')
    assert_stencil_value(program, face, expected)


@pytest.mark.parametrize('face', [gl.GL_FRONT, gl.GL_BACK], ids=['front', 'back'])
def test_invalid_stencil_operation_preserves_prior_state_and_recovers(raw_scene, face):
    _, program, source = raw_scene
    source.set_data(FULL if face == gl.GL_FRONT else FULL[::-1])
    gl.glFrontFace(gl.GL_CCW)
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glStencilMask(0xff)
    gl.glClearStencil(0x30)
    gl.glClear(gl.GL_STENCIL_BUFFER_BIT)
    gl.glEnable(gl.GL_STENCIL_TEST)
    gl.glStencilFuncSeparate(face, gl.GL_NEVER, 0, 0xff)
    gl.glStencilOpSeparate(face, gl.GL_INCR, gl.GL_KEEP, gl.GL_KEEP)
    with pytest.raises(RuntimeError, match='glStencilOpSeparate'):
        gl.glStencilOpSeparate(face, gl.GL_ZERO, gl.GL_KEEP, 123456)
    gl.glColorMask(False, False, False, False)
    program.draw('triangles')
    assert_stencil_value(program, face, 0x31)
    # A valid mutation must work on the same resources after the rejection.
    gl.glStencilMaskSeparate(face, 0xff)
    gl.glStencilFuncSeparate(face, gl.GL_ALWAYS, 0, 0xff)
    gl.glStencilOpSeparate(face, gl.GL_KEEP, gl.GL_KEEP, gl.GL_INVERT)
    gl.glColorMask(False, False, False, False)
    program.draw('triangles')
    assert_stencil_value(program, face, 0xce)


@pytest.mark.parametrize('units,expected', [(1., [255, 0, 0, 255]), (-1., [0, 0, 255, 255])])
def test_raw_polygon_offset_changes_depth_visibility(raw_scene, units, expected):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LEQUAL)
    program['u_color'] = (1, 0, 0, 1)
    program.draw('triangles')
    gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
    gl.glPolygonOffset(0., units)
    program['u_color'] = (0, 0, 1, 1)
    program.draw('triangles')
    assert np.all(pixels() == expected)


@pytest.mark.parametrize('factor,units', [(1e300, 1.), (0., 1e300), (-1e300, 1.), (0., -1e300)])
def test_raw_polygon_offset_overflow_rejects_before_mutating_state(raw_scene, factor, units):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LEQUAL)
    program['u_color'] = (1, 0, 0, 1)
    program.draw('triangles')
    gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
    gl.glPolygonOffset(0., 1.)
    with pytest.raises(RuntimeError, match='glPolygonOffset'):
        gl.glPolygonOffset(factor, units)
    program['u_color'] = (0, 0, 1, 1)
    program.draw('triangles')
    assert np.all(pixels() == [255, 0, 0, 255])
    gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
    program.draw('triangles')
    assert np.all(pixels() == [0, 0, 255, 255])


@pytest.mark.parametrize('raw_scene', [4], indirect=True)
@pytest.mark.parametrize('value,invert,visible', [(0., False, False), (0., True, True), (1., False, True), (1., True, False)])
def test_raw_sample_coverage_endpoints(raw_scene, value, invert, visible):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_SAMPLE_COVERAGE)
    gl.glSampleCoverage(value, invert)
    program.draw('triangles')
    assert np.all(pixels() == ([0, 255, 0, 255] if visible else [0, 0, 0, 255]))


def test_raw_line_width_updates_preserve_prior_draw_coverage(raw_scene):
    _, program, source = raw_scene
    source.set_data(np.array([[-.75, 0], [.75, 0]], np.float32))
    gl.glLineWidth(5.)
    program.draw('lines')
    gl.glLineWidth(1.)
    program['u_color'] = (0, 0, 1, 1)
    program.draw('lines')
    image = pixels()
    green = np.all(image[..., :3] == [0, 255, 0], axis=-1)
    blue = np.all(image[..., :3] == [0, 0, 255], axis=-1)
    assert green[:, 4:12].sum() >= 16 and blue[:, 4:12].sum() >= 8
    assert np.all(image[:2] == [0, 0, 0, 255]) and np.all(image[-2:] == [0, 0, 0, 255])


@pytest.mark.parametrize('raw_scene', [4], indirect=True)
@pytest.mark.parametrize('alpha,visible', [(0., False), (1., True)])
def test_raw_alpha_to_coverage_endpoints(raw_scene, alpha, visible):
    _, program, _ = raw_scene
    gl.glEnable(gl.GL_SAMPLE_ALPHA_TO_COVERAGE)
    program['u_color'] = (0, 1, 0, alpha)
    program.draw('triangles')
    assert np.all(pixels() == ([0, 255, 0, 255] if visible else [0, 0, 0, 255]))


@pytest.mark.parametrize('name,arguments', [
    ('glViewport', (0, 0, -1, 12)), ('glScissor', (0, 0, 16, -1)),
    ('glClearColor', (float('nan'), 0, 0, 1)), ('glClearDepth', (float('nan'),)),
    ('glClearStencil', (2**40,)), ('glClear', (-1,)),
    ('glEnable', (123456,)), ('glDisable', (123456,)),
    ('glColorMask', (True, float('nan'), True, True)), ('glDepthMask', (float('nan'),)),
    ('glDepthRange', (0., float('nan'))), ('glDepthFunc', (123456,)),
    ('glFrontFace', (123456,)), ('glCullFace', (123456,)), ('glLineWidth', (0.,)),
    ('glPolygonOffset', (float('nan'), 0.)), ('glBlendColor', (0., 0., float('inf'), 1.)),
    ('glBlendFunc', (gl.GL_ONE, 123456)),
    ('glBlendFuncSeparate', (gl.GL_ONE, gl.GL_ZERO, gl.GL_ONE, 123456)),
    ('glBlendEquation', (123456,)), ('glBlendEquationSeparate', (gl.GL_FUNC_ADD, 123456)),
    ('glStencilFunc', (123456, 0, 255)), ('glStencilFuncSeparate', (gl.GL_FRONT, 123456, 0, 255)),
    ('glStencilMask', (2**40,)), ('glStencilMaskSeparate', (gl.GL_FRONT, 2**40)),
    ('glStencilOp', (gl.GL_KEEP, gl.GL_KEEP, 123456)),
    ('glStencilOpSeparate', (gl.GL_FRONT, gl.GL_KEEP, gl.GL_KEEP, 123456)),
    ('glSampleCoverage', (float('nan'), False)),
])
def test_invalid_raw_parameters_leave_next_draw_usable(raw_scene, name, arguments):
    canvas, program, _ = raw_scene
    with pytest.raises(RuntimeError, match=name):
        getattr(gl, name)(*arguments)
    assert canvas.context.get_viewport() == (0, 0, 16, 12)
    program.draw('triangles')
    assert np.all(pixels() == [0, 255, 0, 255])


@pytest.mark.parametrize('selector', [3379.75, np.float64(3379), '3379', True, object()])
def test_queries_do_not_silently_coerce_noninteger_selectors(selector):
    with pytest.raises(TypeError, match='integer query enum'):
        gl.glGetParameter(selector)


@pytest.mark.parametrize('selector,field', [
    (gl.GL_MAX_TEXTURE_SIZE, 'max_texture_dimension_2d'),
    (gl.GL_MAX_VERTEX_ATTRIBS, 'max_vertex_attributes'),
    (gl.GL_MAX_3D_TEXTURE_SIZE, 'max_texture_dimension_3d'),
])
def test_integer_queries_report_actual_granted_limits_without_submission(selector, field):
    before = _dawn.probe()
    info = _dawn.device_info()
    for value in (selector, int(selector), np.int64(selector)):
        result = gl.glGetParameter(value)
        assert type(result) is int and result == info[field]
    after = _dawn.probe()
    for name in ('dawn_queue_submits', 'completion_waits', 'finish_calls', 'texture_uploads'):
        assert after[name] == before[name], name


def test_target_queries_refuse_a_closed_canvas_even_if_native_owner_remains(raw_scene):
    canvas, _, _ = raw_scene
    was_closed = canvas._closed
    canvas._closed = True  # A failed native release can retain its ID for retry.
    try:
        for selector in (gl.GL_VIEWPORT, gl.GL_SAMPLES, gl.GL_STEREO, gl.GL_DOUBLEBUFFER):
            with pytest.raises(RuntimeError, match='current Dawn canvas'):
                gl.glGetParameter(selector)
    finally:
        canvas._closed = was_closed


def test_raw_clear_and_scissor_preserve_queued_gloo_work():
    canvas = app.Canvas(app='dawn_headless', size=(12, 8))
    try:
        canvas.set_current()
        gl.glViewport(0, 0, 12, 8)
        assert canvas.context.get_viewport() == (0, 0, 12, 8)
        gloo.clear(color='blue')  # Queued before the raw state changes.
        gl.glScissor(0, 0, 6, 8)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glClearColor(1, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glFinish()
        image = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        assert np.all(image[:, :6] == [255, 0, 0, 255])
        assert np.all(image[:, 6:] == [0, 0, 255, 255])
        assert gl.glGetError() == gl.GL_NO_ERROR
    finally:
        canvas.close()


def test_raw_state_respects_framebuffer_binding_and_canvas_selection():
    first = app.Canvas(app='dawn_headless', size=(8, 8))
    second = app.Canvas(app='dawn_headless', size=(8, 8))
    try:
        first.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.clear(color='blue')
        color = gloo.Texture2D(np.zeros((8, 8, 4), dtype=np.uint8))
        target = gloo.FrameBuffer(color=color)
        with target:
            gl.glClearColor(1, 0, 0, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [255, 0, 0, 255])
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 0, 255, 255])
        second.set_current()
        gl.glViewport(0, 0, 8, 8)
        gl.glClearColor(0, 1, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 255, 0, 255])
        first.set_current()
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 0, 255, 255])
        target.delete()
        color.delete()
        first.context.flush_commands()
    finally:
        first.close()
        second.close()


def test_raw_color_mask_and_invalid_state_are_not_silently_ignored():
    canvas = app.Canvas(app='dawn_headless', size=(8, 8))
    try:
        canvas.set_current()
        gl.glViewport(0, 0, 8, 8)
        gloo.clear(color=(0, 0, 1, 1))
        gl.glColorMask(True, False, False, False)
        gl.glClearColor(1, 1, 0, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        image = gloo.read_pixels((0, 0, 8, 8), alpha=True)
        assert np.all(image == [255, 0, 255, 255])
        with pytest.raises(RuntimeError, match='glViewport'):
            gl.glViewport(0, 0, -1, 8)
        assert canvas.context.get_viewport() == (0, 0, 8, 8)
        gl.glColorMask(True, True, True, True)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [255, 255, 0, 0])
        with pytest.raises(DawnCompatibilityError, match='glCreateProgram'):
            gl.glCreateProgram()
        with pytest.raises(DawnCompatibilityError, match='glDrawArrays'):
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
        with pytest.raises(DawnCompatibilityError, match='buffer mask'):
            gl.glClear(1)
    finally:
        canvas.close()
    with pytest.raises(DawnCompatibilityError, match='current Dawn canvas'):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
