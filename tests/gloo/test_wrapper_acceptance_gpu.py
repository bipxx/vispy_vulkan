# SPDX-License-Identifier: AGPL-3.0-only
"""Reviewed public gloo acceptance cases on tiny headless Dawn targets."""

from contextlib import contextmanager
import time

import numpy as np
import pytest

from vispy import app, gloo
from vispy.gloo.context import forget_canvas, get_current_canvas, set_current_canvas

pytestmark = pytest.mark.gpu
BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
BLUE = (0, 0, 255, 255)

VERTEX = """
attribute vec2 a_position;
uniform float u_z;
void main() { gl_Position = vec4(a_position, u_z, 1.0); }
"""
FRAGMENT = """
uniform vec4 u_color;
void main() { gl_FragColor = u_color; }
"""
TRIANGLE = [(-1, -1), (3, -1), (-1, 3)]
# Window y = 4.5 puts the line on the center of row 3 in top-down readback.
LINE = [(-.75, .125), (.75, .125)]


@contextmanager
def headless_canvas(samples=0):
    from vispy import _dawn

    canvas = app.Canvas(app='dawn_headless', show=False, size=(8, 8),
                        config={'samples': samples, 'stencil_size': 8})
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.set_stencil_mask(255)
        gloo.clear(color='black', depth=1., stencil=0)
        gloo.finish()
        yield canvas
    finally:
        canvas.close()
        _dawn.process_events()


@pytest.fixture
def target(request):
    with headless_canvas(samples=getattr(request, 'param', 0)) as canvas:
        yield canvas


@pytest.fixture
def draw(target):
    programs = {}

    def render(color, z=0., mode='triangles'):
        if mode not in programs:
            program = programs[mode] = gloo.Program(VERTEX, FRAGMENT)
            program['a_position'] = np.array(
                LINE if mode == 'lines' else TRIANGLE, dtype=np.float32)
        program = programs[mode]
        program['u_z'] = z
        program['u_color'] = color
        program.draw(mode)

    yield render
    for program in programs.values():
        program.delete()
    target.context.flush_commands()


def pixels():
    return gloo.read_pixels((0, 0, 8, 8))


def center(mode='color'):
    out_type = 'float' if mode == 'depth' else 'unsigned_byte'
    value = gloo.read_pixels((0, 0, 8, 8), mode=mode, out_type=out_type)[4, 4]
    return value if mode == 'color' else value.item()


@pytest.mark.parametrize('again', [False, True], ids=['ordinary', 'recovery'])
def test_forget_canvas_routes_to_survivor(target, again):
    with headless_canvas() as second:
        set_current_canvas(target)
        set_current_canvas(second)
        forget_canvas(second)
        if again:
            forget_canvas(second)
            forget_canvas(second)
        assert get_current_canvas() is target
        gloo.clear(color='green' if again else 'red')
        np.testing.assert_array_equal(center(), (0, 128, 0, 255) if again else RED)
        set_current_canvas(second)
        np.testing.assert_array_equal(center(), BLACK)
        set_current_canvas(target)


def test_set_current_canvas_routes_to_selected_target(target):
    with headless_canvas() as second:
        set_current_canvas(target)
        set_current_canvas(second)
        assert get_current_canvas() is second
        gloo.clear(color='red')
        np.testing.assert_array_equal(center(), RED)
        set_current_canvas(target)
        np.testing.assert_array_equal(center(), BLACK)


def test_set_current_canvas_none_preserves_selection(target):
    with pytest.raises(AttributeError):
        set_current_canvas(None)
    assert get_current_canvas() is target
    gloo.clear(color='blue')
    np.testing.assert_array_equal(center(), BLUE)


@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_clear_zero_depth_preserves_stencil(target, invalid_first):
    gloo.clear(color='red', depth=.75, stencil=7)
    assert center('depth') == pytest.approx(.75)
    if invalid_first:
        gloo.clear(color=False, depth=float('nan'), stencil=False)
        with pytest.raises((RuntimeError, ValueError), match='finite'):
            center('depth')
        assert center('depth') == pytest.approx(.75)
    gloo.clear(color=False, depth=0., stencil=False)
    assert center('depth') == 0.
    assert center('stencil') == 7
    np.testing.assert_array_equal(center(), RED)


def test_finish_completes_without_presentation(target):
    from vispy import _dawn

    before = _dawn.probe()
    gloo.clear(color='red')
    gloo.finish()
    after = _dawn.probe()
    assert after['finish_calls'] == before['finish_calls'] + 1
    assert after['pending_tickets'] == 0
    assert after['application_presents'] == before['application_presents']
    np.testing.assert_array_equal(center(), RED)


def test_finish_pre_submit_failure_and_recovery(target):
    from vispy import _dawn

    before = _dawn.probe()
    _dawn.diagnostic_submission_controls(False, 'before-submit')
    try:
        gloo.clear(color='red')
        with pytest.raises(RuntimeError, match='diagnostic submission failure: before-submit'):
            gloo.finish()
        assert _dawn.probe()['dawn_queue_submits'] == before['dawn_queue_submits']
    finally:
        _dawn.diagnostic_submission_controls(False, '')
    gloo.clear(color='blue')
    gloo.finish()
    np.testing.assert_array_equal(center(), BLUE)


def test_flush_submits_without_wait_or_presentation(target):
    from vispy import _dawn

    before = _dawn.probe()
    gloo.clear(color='red')
    gloo.flush()
    after = _dawn.probe()
    assert after['dawn_queue_submits'] > before['dawn_queue_submits']
    assert after['completion_waits'] == before['completion_waits']
    assert after['application_presents'] == before['application_presents']
    np.testing.assert_array_equal(center(), RED)


def test_flush_retries_work_retained_at_capacity(target):
    from vispy import _dawn

    slots = _dawn.probe()['frame_slots']
    _dawn.configure_frame_slots(1)
    try:
        _dawn.diagnostic_submission_controls(True, '')
        gloo.clear(color='red')
        gloo.flush()
        before = _dawn.probe()
        assert before['pending_tickets'] == 1
        gloo.clear(color='green')
        with pytest.raises(RuntimeError, match='glFlush.*capacity'):
            gloo.flush()
        blocked = _dawn.probe()
        assert blocked['dawn_queue_submits'] == before['dawn_queue_submits']
        assert blocked['pending_draws'] > 0

        _dawn.diagnostic_submission_controls(False, '')
        deadline = time.monotonic() + 5
        while _dawn.probe()['pending_tickets']:
            _dawn.process_events()
            assert time.monotonic() < deadline, 'released submission did not retire'
            time.sleep(.001)
        gloo.flush()  # Retry without issuing another clear.
        assert _dawn.probe()['dawn_queue_submits'] == before['dawn_queue_submits'] + 1
        np.testing.assert_array_equal(center(), (0, 128, 0, 255))
    finally:
        _dawn.diagnostic_submission_controls(False, '')
        gloo.finish()
        _dawn.configure_frame_slots(slots)


@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_set_blend_color(target, draw, invalid_first):
    gloo.set_state(blend=True)
    gloo.set_blend_func('constant_color', 'zero', 'one', 'zero')
    gloo.set_blend_color((.25, .5, .75, .5))
    if invalid_first:
        with pytest.raises(ValueError):
            gloo.set_blend_color((.1, .2))
    draw((1, 1, 1, 1))
    np.testing.assert_allclose(center(), (64, 128, 191, 255), atol=1, rtol=0)
    gloo.clear(color='black')
    gloo.set_blend_color((.75, .25, .5, 1))
    draw((1, 1, 1, 1))
    np.testing.assert_allclose(center(), (191, 64, 128, 255), atol=1, rtol=0)


def test_set_blend_equation_max(target, draw):
    gloo.set_state(blend=True)
    gloo.set_blend_func('one', 'one')
    gloo.clear(color=(.8, .2, .4, 1))
    gloo.set_blend_equation('max', 'max')
    draw((.3, .7, .9, 1))
    np.testing.assert_allclose(center(), (204, 179, 230, 255), atol=3, rtol=0)


def test_set_blend_equation_invalid_mode_recovers(target, draw):
    gloo.set_blend_equation('bogus')
    with pytest.raises(RuntimeError, match='glBlendEquationSeparate.*bogus'):
        gloo.finish()
    gloo.set_state(blend=True)
    gloo.set_blend_equation('max')
    gloo.set_blend_func('one', 'one')
    gloo.clear(color='red')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), (255, 255, 0, 255))


def test_set_blend_func_separate_rgb_and_alpha(target, draw):
    gloo.clear(color='red')
    gloo.set_state(blend=True)
    gloo.set_blend_func('src_alpha', 'one_minus_src_alpha', 'zero', 'one')
    draw((0, 0, 1, .5))
    np.testing.assert_allclose(center(), (128, 0, 128, 255), atol=1, rtol=0)


def test_set_blend_func_mixed_constants_recover(target, draw):
    gloo.set_state(blend=True)
    gloo.set_blend_func('constant_color', 'constant_alpha', 'one', 'zero')
    with pytest.raises(RuntimeError, match=r'(?i)constant.*alpha'):
        draw((1, 0, 0, 1))
        gloo.finish()
    gloo.set_blend_func('one', 'zero')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), GREEN)


@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_set_clear_color(target, invalid_first):
    gloo.set_clear_color('red', alpha=.5)
    if invalid_first:
        with pytest.raises(ValueError):
            gloo.set_clear_color('not-a-color')
    gloo.clear(color=True, depth=False, stencil=False)
    np.testing.assert_allclose(center(), (255, 0, 0, 128), atol=1, rtol=0)


@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_set_clear_depth(target, invalid_first):
    gloo.set_clear_depth(.75)
    gloo.clear(color=False, depth=True, stencil=False)
    assert center('depth') == pytest.approx(.75, abs=.0001)
    if invalid_first:
        gloo.set_clear_depth(float('nan'))
        with pytest.raises(RuntimeError, match='glClearDepth.*finite'):
            gloo.finish()
        gloo.clear(color=False, depth=True, stencil=False)
        assert center('depth') == pytest.approx(.75, abs=.0001)


@pytest.mark.parametrize('value', [211, 93], ids=['ordinary', 'recovery'])
def test_set_clear_stencil(target, value):
    gloo.set_clear_stencil(value)
    if value == 93:
        with pytest.raises(ValueError):
            gloo.set_clear_stencil('bad')
    gloo.clear(color=False, depth=False, stencil=True)
    assert center('stencil') == value


@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_set_color_mask(target, invalid_first):
    if invalid_first:
        with pytest.raises(TypeError):
            gloo.set_color_mask(True, False, True)
    gloo.set_color_mask(invalid_first, not invalid_first, False, True)
    gloo.clear(color='white')
    np.testing.assert_array_equal(center(), RED if invalid_first else GREEN)


def test_set_cull_face_both(target, draw):
    gloo.set_state(cull_face=True)
    gloo.set_cull_face('front_and_back')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(pixels(), np.broadcast_to(BLACK, (8, 8, 4)))


def test_set_cull_face_invalid_mode_recovers(target, draw):
    gloo.set_state(cull_face=True)
    gloo.set_cull_face('banana')
    with pytest.raises(RuntimeError, match='glCullFace.*banana'):
        gloo.finish()
    gloo.set_cull_face('back')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), GREEN)


def test_set_depth_func_less(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_func('less')
    draw((1, 0, 0, 1), z=-.5)
    draw((0, 0, 1, 1), z=.5)
    draw((0, 1, 0, 1), z=-.5)  # Equal depth also fails under less.
    np.testing.assert_array_equal(center(), RED)


def test_set_depth_func_invalid_comparator_recovers(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_func('bogus')
    with pytest.raises(RuntimeError, match='glDepthFunc.*bogus'):
        gloo.finish()
    gloo.set_depth_func('never')
    draw((1, 0, 0, 1))
    np.testing.assert_array_equal(center(), BLACK)


def test_set_depth_mask_false_preserves_depth(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_func('less')
    gloo.set_depth_mask(False)
    draw((1, 0, 0, 1), z=-.5)
    draw((0, 0, 1, 1), z=.5)
    np.testing.assert_array_equal(center(), BLUE)
    assert center('depth') == 1.


def test_set_depth_mask_missing_flag_recovers(target, draw):
    with pytest.raises(TypeError):
        gloo.set_depth_mask()
    gloo.set_state(depth_test=True)
    gloo.set_depth_mask(False)
    gloo.set_depth_mask(True)
    draw((1, 0, 0, 1))
    assert center('depth') == pytest.approx(.5, abs=.001)


def test_set_depth_range_reversed(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_range(1, 0)
    draw((1, 0, 0, 1), z=-.25)
    assert center('depth') == pytest.approx(.625, abs=.001)


def test_set_depth_range_nonfinite_recovers(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_range(float('nan'), 1)
    with pytest.raises(RuntimeError, match='glDepthRange.*finite'):
        gloo.finish()
    gloo.set_depth_range(0, 1)
    draw((1, 0, 0, 1))
    assert center('depth') == pytest.approx(.5, abs=.001)


def test_set_front_face_switches_winding(target, draw):
    gloo.set_state(cull_face=True)
    gloo.set_cull_face('back')
    gloo.set_front_face('cw')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), BLACK)
    gloo.set_front_face('ccw')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), GREEN)


def test_set_front_face_invalid_winding_recovers(target, draw):
    gloo.set_state(cull_face=True)
    gloo.set_cull_face('back')
    gloo.set_front_face('sideways')
    with pytest.raises(RuntimeError, match='glFrontFace.*sideways'):
        gloo.finish()
    gloo.set_front_face('ccw')
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), GREEN)


def test_set_hint_unsupported_on_dawn_recovers(target):
    gloo.set_hint('line_smooth_hint', 'nicest')
    with pytest.raises(RuntimeError, match='(?i)glHint.*(unsupported|not supported)'):
        gloo.finish()
    gloo.clear(color=(0, 1, 0, 1))
    np.testing.assert_array_equal(center(), GREEN)


@pytest.mark.parametrize('width,rows', [(3, slice(2, 5)), (1, slice(3, 4))],
                         ids=['ordinary', 'recovery'])
def test_set_line_width(target, draw, width, rows):
    if width == 1:
        with pytest.raises(RuntimeError, match='width'):
            gloo.set_line_width(-1)
    gloo.set_line_width(width)
    draw((1, 0, 0, 1), mode='lines')
    expected = np.tile(BLACK, (8, 1))
    expected[rows] = RED
    np.testing.assert_array_equal(pixels()[:, 4], expected)


def test_set_polygon_offset_signed_bias(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_func('less')
    draw((1, 0, 0, 1))
    gloo.set_state(polygon_offset_fill=True)
    gloo.set_polygon_offset(0, -8)
    draw((0, 1, 0, 1))
    np.testing.assert_array_equal(center(), GREEN)


def test_set_polygon_offset_fractional_bias_recovers(target, draw):
    gloo.set_state(depth_test=True)
    gloo.set_depth_func('less')
    draw((1, 0, 0, 1))
    gloo.finish()
    gloo.set_state(polygon_offset_fill=True)
    gloo.set_polygon_offset(0, .5)
    with pytest.raises(RuntimeError, match='(?i)fractional'):
        draw((0, 1, 0, 1))
        gloo.finish()
    gloo.set_polygon_offset(0, -16)
    draw((0, 0, 1, 1))
    np.testing.assert_array_equal(center(), BLUE)


@pytest.mark.parametrize('target', [4], indirect=True, ids=['4x-msaa'])
@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_set_sample_coverage(target, draw, invalid_first):
    assert gloo.get_gl_configuration()['samples'] == 4
    # Queue capability changes alongside gloo's parameter changes and draws.
    target.context.glir.command('FUNC', 'glEnable', 'sample_coverage')
    if invalid_first:
        gloo.set_sample_coverage(float('nan'), False)
        with pytest.raises(RuntimeError, match=(
            r'^GLIR FUNC object=context glSampleCoverage: '
            r'FUNC glSampleCoverage: argument must be finite$'
        )):
            gloo.finish()
        gloo.set_sample_coverage(0, True)
        draw((1, 1, 1, 1))
        np.testing.assert_array_equal(center()[:3], (255, 255, 255))
    else:
        gloo.set_sample_coverage(.25, False)
        draw((1, 1, 1, 1))
        np.testing.assert_allclose(center()[:3], (64, 64, 64), atol=2, rtol=0)

        target.context.glir.command('FUNC', 'glDisable', 'sample_coverage')
        gloo.clear(color='black', depth=False, stencil=False)
        draw((1, 1, 1, 1))
        np.testing.assert_array_equal(center()[:3], (255, 255, 255))

        target.context.glir.command('FUNC', 'glEnable', 'sample_coverage')
        gloo.clear(color='black', depth=False, stencil=False)
        draw((1, 1, 1, 1))
        np.testing.assert_allclose(center()[:3], (64, 64, 64), atol=2, rtol=0)


@pytest.mark.parametrize('target', [4], indirect=True, ids=['4x-msaa'])
@pytest.mark.parametrize('capability', ['sample_coverage', 'sample_alpha_to_coverage'])
def test_clear_scissored_msaa_region_ignores_draw_coverage(target, capability):
    gloo.clear(color='white', depth=False, stencil=False)
    gloo.set_state(scissor_test=True)
    target.context.glir.command('FUNC', 'glEnable', capability)
    gloo.set_scissor(2, 1, 3, 2)
    gloo.set_sample_coverage(0, False)
    gloo.clear(color=(0, 0, 0, 0), depth=False, stencil=False)

    expected = np.full((8, 8, 4), 255, np.uint8)
    expected[5:7, 2:5] = 0
    np.testing.assert_array_equal(pixels(), expected)


@pytest.mark.parametrize('invalid_first', [False, True], ids=['ordinary', 'recovery'])
def test_set_scissor(target, invalid_first):
    if invalid_first:
        gloo.set_scissor(2, 1, -1, 2)
        with pytest.raises(RuntimeError, match='glScissor'):
            gloo.finish()
    gloo.set_scissor(2, 1, 3, 2)
    gloo.set_state(scissor_test=True)
    gloo.clear(color='red')
    expected = np.tile(BLACK, (8, 8, 1))
    expected[5:7, 2:5] = RED
    np.testing.assert_array_equal(pixels(), expected)


def test_set_state_translucent_with_override(target, draw):
    gloo.clear(color='red', depth=0.)
    gloo.set_state('translucent', depth_test=False)
    draw((0, 0, 1, .5))
    np.testing.assert_allclose(center(), (128, 0, 128, 255), atol=1, rtol=0)


def test_set_state_invalid_preset_recovers(target, draw):
    gloo.clear(color='red', depth=0.)
    gloo.set_state('translucent', depth_test=False)
    with pytest.raises(ValueError, match='preset.*bogus'):
        gloo.set_state('bogus')
    gloo.set_state('opaque', depth_test=False)
    draw((0, 0, 1, .5))
    np.testing.assert_allclose(center(), (0, 0, 255, 128), atol=1, rtol=0)


def test_set_stencil_func_masks_comparison(target, draw):
    gloo.clear(color=False, depth=False, stencil=0xA3)
    gloo.set_state(stencil_test=True)
    gloo.set_stencil_func('equal', 0x03, 0x0F)
    draw((1, 0, 0, 1))
    np.testing.assert_array_equal(center(), RED)


def test_set_stencil_func_invalid_comparator_recovers(target, draw):
    gloo.set_state(stencil_test=True)
    gloo.set_stencil_func('bogus', 3, 255)
    with pytest.raises(RuntimeError, match='glStencilFuncSeparate.*bogus'):
        gloo.finish()
    gloo.set_stencil_func('never', 3, 255)
    draw((1, 0, 0, 1))
    np.testing.assert_array_equal(center(), BLACK)


def test_set_stencil_mask_preserves_unmasked_bits(target, draw):
    gloo.clear(color=False, depth=False, stencil=0xA5)
    gloo.set_stencil_mask(0x0F)
    gloo.set_state(stencil_test=True)
    gloo.set_stencil_func('always', 0x3C, 255)
    gloo.set_stencil_op('keep', 'keep', 'replace')
    draw((1, 0, 0, 1))
    assert center('stencil') == 0xAC


def test_set_stencil_mask_invalid_face_recovers(target):
    gloo.set_stencil_mask(15, 'sideways')
    with pytest.raises(RuntimeError, match='glStencilMaskSeparate.*sideways'):
        gloo.finish()
    gloo.set_stencil_mask(255)
    gloo.clear(color=False, depth=False, stencil=9)
    assert center('stencil') == 9


def test_set_stencil_op_increments_on_stencil_fail(target, draw):
    gloo.clear(color=False, depth=False, stencil=7)
    gloo.set_state(stencil_test=True)
    gloo.set_stencil_func('never', 0, 255)
    gloo.set_stencil_op('incr', 'keep', 'keep')
    draw((1, 0, 0, 1))
    assert center('stencil') == 8


def test_set_stencil_op_invalid_operation_recovers(target, draw):
    gloo.set_state(stencil_test=True)
    gloo.set_stencil_op('bogus', 'keep', 'keep')
    with pytest.raises(RuntimeError, match='glStencilOpSeparate.*bogus'):
        gloo.finish()
    gloo.set_stencil_op('keep', 'keep', 'replace')
    gloo.set_stencil_func('always', 9, 255)
    draw((1, 0, 0, 1))
    assert center('stencil') == 9


def test_set_viewport_tuple_changes_raster_placement(target, draw):
    gloo.set_viewport((2, 1, 3, 4))
    draw((1, 0, 0, 1))
    expected = np.tile(BLACK, (8, 8, 1))
    expected[3:7, 2:5] = RED
    np.testing.assert_array_equal(pixels(), expected)


def test_set_viewport_malformed_tuple_preserves_default_read_region(target):
    gloo.set_viewport((2, 1, 3, 4))
    with pytest.raises(ValueError):
        gloo.set_viewport((2, 1, 3))
    image = gloo.read_pixels()
    assert image.shape == (4, 3, 4)
    np.testing.assert_array_equal(image, np.broadcast_to(BLACK, (4, 3, 4)))
