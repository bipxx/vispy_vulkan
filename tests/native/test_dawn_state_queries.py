# SPDX-License-Identifier: AGPL-3.0-only
"""Logical native query state, distinct from effective pipeline state."""
import numpy as np
import pytest
from vispy import _dawn, app, gloo
from vispy.gloo import gl
from vispy.gloo.dawn_parser import _STATE_QUERY_PARAMETERS

pytestmark = pytest.mark.gpu


@pytest.fixture
def canvas():
    c = app.Canvas(app='dawn_headless', size=(16, 12), show=False)
    c.set_current()
    try:
        yield c
    finally:
        c.close()


def test_native_pristine_state_has_complete_typed_defaults_without_allocating():
    cid = _dawn.register_canvas(17, 13, 0, False)
    try:
        before = _dawn.probe()
        expected = {0xBE2: 0, 0xB72: 1, 0xB74: 0x201, 0xB70: (0., 1.),
                    0xB93: -1, 0x8CA5: -1, 0xB21: 1., 0x8005: (0., 0., 0., 0.),
                    0xC23: (1, 1, 1, 1), 0xC10: (0, 0, 17, 13), 0xBA2: (0, 0, 17, 13)}
        assert _dawn.state_query_contract_version == 1
        for code in _STATE_QUERY_PARAMETERS | {0xBA2}:
            value = _dawn.state_parameter(cid, code)
            assert type(value) in (int, float, tuple)
            if code in expected:
                assert value == expected[code]
                assert type(value) is type(expected[code])
        after = _dawn.probe()
        for name in ('dawn_queue_submits', 'completion_waits', 'finish_calls',
                     'application_presents', 'texture_allocations', 'buffer_allocations'):
            assert after[name] == before[name], name
    finally:
        _dawn.destroy_canvas(cid)


def test_queries_report_disabled_state_and_minmax_factors_before_any_draw(canvas):
    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glDepthMask(True)
    gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_ZERO, gl.GL_ONE)
    gl.glBlendEquationSeparate(gl.GL_MIN, gl.GL_MAX)
    assert gl.glGetParameter(gl.GL_DEPTH_WRITEMASK) == 1
    assert gl.glGetParameter(gl.GL_DEPTH_TEST) == 0
    for code, expected in [(0x80C9, 0x302), (0x80C8, 0x303), (0x80CB, 0), (0x80CA, 1),
                           (0x8009, 0x8007), (0x883D, 0x8008)]:
        assert gl.glGetParameter(code) == expected


@pytest.mark.parametrize('mask,expected', [(0xffffffff, -1), (0x80000000, -2147483648), (0x7fffffff, 2147483647), (0, 0)])
def test_stencil_queries_preserve_signed_bit_patterns_and_independent_faces(canvas, mask, expected):
    gl.glStencilMaskSeparate(gl.GL_FRONT, mask)
    gl.glStencilMaskSeparate(gl.GL_BACK, 0x13579)
    gl.glStencilFuncSeparate(gl.GL_FRONT, gl.GL_LESS, 17, mask)
    gl.glStencilFuncSeparate(gl.GL_BACK, gl.GL_GREATER, 29, 0x2468)
    gl.glStencilOpSeparate(gl.GL_FRONT, gl.GL_INCR_WRAP, gl.GL_DECR, gl.GL_INVERT)
    gl.glStencilOpSeparate(gl.GL_BACK, gl.GL_REPLACE, gl.GL_KEEP, gl.GL_ZERO)
    for code, value in [(0xB98, expected), (0xB93, expected), (0x8CA5, 0x13579),
                        (0x8CA4, 0x2468), (0xB97, 17), (0x8CA3, 29),
                        (0xB92, 0x201), (0x8800, 0x204), (0xB94, 0x8507),
                        (0xB95, 0x1E03), (0xB96, 0x150A), (0x8801, 0x1E01),
                        (0x8802, 0x1E00), (0x8803, 0)]:
        assert gl.glGetParameter(code) == value


def test_queued_state_is_visible_without_implicit_submission(canvas):
    canvas.context.glir.command('FUNC', 'glBlendColor', .1, .2, .3, .4)
    canvas.context.glir.command('FUNC', 'glDepthMask', False)
    before = _dawn.probe()
    assert gl.glGetParameter(gl.GL_BLEND_COLOR) == tuple(float(np.float32(x)) for x in (.1, .2, .3, .4))
    assert gl.glGetParameter(gl.GL_DEPTH_WRITEMASK) == 0
    after = _dawn.probe()
    for name in ('dawn_queue_submits', 'completion_waits', 'finish_calls', 'application_presents'):
        assert after[name] == before[name], name
    with pytest.raises(RuntimeError, match='glDepthRange'):
        gl.glDepthRange(float('nan'), 1.)
    assert gl.glGetParameter(gl.GL_DEPTH_RANGE) == (0., 1.)


def test_default_rectangle_queries_follow_target_until_explicit_override(canvas):
    assert gl.glGetParameter(gl.GL_SCISSOR_BOX) == (0, 0, 16, 12)
    texture = gloo.Texture2D(np.zeros((5, 7, 4), np.uint8))
    fbo = gloo.FrameBuffer(color=texture)
    try:
        with fbo:
            assert gl.glGetParameter(gl.GL_SCISSOR_BOX) == (0, 0, 7, 5)
            gl.glScissor(1, 2, 3, 2)
            assert gl.glGetParameter(gl.GL_SCISSOR_BOX) == (1, 2, 3, 2)
        assert gl.glGetParameter(gl.GL_SCISSOR_BOX) == (1, 2, 3, 2)
    finally:
        fbo.delete()
        texture.delete()
        canvas.context.flush_commands()


def test_canvas_isolation_close_and_missing_native_owner(canvas):
    gl.glLineWidth(3.)
    other = app.Canvas(app='dawn_headless', size=(9, 7), show=False)
    try:
        other.set_current()
        gl.glLineWidth(5.)
        assert gl.glGetParameter(gl.GL_LINE_WIDTH) == 5.
        canvas.set_current()
        assert gl.glGetParameter(gl.GL_LINE_WIDTH) == 3.
        cid = other._backend._dawn_canvas_id
        other.close()
        canvas.set_current()
        assert gl.glGetParameter(gl.GL_LINE_WIDTH) == 3.
        with pytest.raises(RuntimeError, match='missing canvas'):
            _dawn.state_parameter(cid, 0xB21)
    finally:
        other.close()


def test_enabled_default_scissor_preserves_full_target_clear(canvas):
    gl.glEnable(gl.GL_SCISSOR_TEST)
    gl.glClearColor(1, 0, 0, 1)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    assert np.all(gloo.read_pixels((0, 0, 16, 12), alpha=True) == [255, 0, 0, 255])


@pytest.mark.parametrize('command,args,expected', [
    ('glEnable', (0xBE2,), {0xBE2: 1}),
    ('glEnable', (0xB71,), {0xB71: 1}),
    ('glDepthFunc', (0x206,), {0xB74: 0x206}),
    ('glDepthRange', (.25, .75), {0xB70: (.25, .75)}),
    ('glClearDepth', (.375,), {0xB73: .375}),
    ('glClearStencil', (-1,), {0xB91: -1}),
    ('glEnable', (0xB90,), {0xB90: 1}),
    ('glEnable', (0xB44,), {0xB44: 1}),
    ('glCullFace', (0x404,), {0xB45: 0x404}),
    ('glFrontFace', (0x900,), {0xB46: 0x900}),
    ('glClearColor', (-1, .25, .75, 2), {0xC22: (0., .25, .75, 1.)}),
    ('glColorMask', (0, 1, 0, 1), {0xC23: (0, 1, 0, 1)}),
    ('glEnable', (0xC11,), {0xC11: 1}),
    ('glLineWidth', (2.5,), {0xB21: 2.5}),
    ('glEnable', (0xB20,), {0xB20: 1}),
    ('glEnable', (0x8037,), {0x8037: 1}),
    ('glPolygonOffset', (.5, -.25), {0x8038: .5, 0x2A00: -.25}),
    ('glDisable', (0x809D,), {0x809D: 0}),
    ('glEnable', (0x809E,), {0x809E: 1}),
    ('glEnable', (0x80A0,), {0x80A0: 1}),
    ('glSampleCoverage', (.25, True), {0x80AA: .25, 0x80AB: 1}),
])
def test_mutated_state_families_return_public_types(canvas, command, args, expected):
    getattr(gl, command)(*args)
    for code, value in expected.items():
        actual = gl.glGetParameter(code)
        assert actual == value
        assert type(actual) is type(value)


def test_query_matches_queued_clear_output_and_retained_state_after_loss(canvas):
    gloo.set_color_mask(False, True, False, True)
    gloo.clear(color=(1, 1, 1, 1))
    assert gl.glGetParameter(gl.GL_COLOR_WRITEMASK) == (0, 1, 0, 1)
    assert np.all(gloo.read_pixels((0, 0, 16, 12), alpha=True) == [0, 255, 0, 255])
    gl.glLineWidth(2.5)
    _dawn.lose_device()
    _dawn.process_events()
    assert gl.glGetParameter(gl.GL_LINE_WIDTH) == 2.5
    gl.glColorMask(True, True, True, True)
    gl.glClearColor(0, 0, 1, 1)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    assert np.all(gloo.read_pixels((0, 0, 16, 12), alpha=True) == [0, 0, 255, 255])


def test_selector_and_old_native_rejection_preserve_actual_queued_work(canvas, monkeypatch):
    gloo.clear(color=(1, 0, 0, 1))
    pending = canvas.context.glir._shared._commands
    snapshot = list(pending)
    for code in (True, '2930', 999999):
        with pytest.raises((TypeError, RuntimeError)):
            gl.glGetParameter(code)
        assert canvas.context.glir._shared._commands is pending
        assert pending == snapshot
    with monkeypatch.context() as patch:
        patch.setattr(_dawn, 'state_query_contract_version', 0)
        with pytest.raises(RuntimeError, match='matching native state-query'):
            gl.glGetParameter(gl.GL_DEPTH_WRITEMASK)
        assert canvas.context.glir._shared._commands is pending
        assert pending == snapshot
    assert gl.glGetParameter(gl.GL_COLOR_CLEAR_VALUE) == (1., 0., 0., 1.)
    assert np.all(gloo.read_pixels((0, 0, 16, 12), alpha=True) == [255, 0, 0, 255])


def test_native_default_rectangles_track_resize_and_explicit_values_survive():
    cid = _dawn.register_canvas(17, 13, 0, False)
    try:
        _dawn.configure_canvas(cid, 23, 19, 0)
        assert _dawn.viewport(cid) == [0, 0, 23, 19]
        assert _dawn.state_parameter(cid, 0xC10) == (0, 0, 23, 19)
        _dawn.execute(cid, [('FUNC', 'glViewport', 1, 2, 7, 5),
                            ('FUNC', 'glScissor', 2, 3, 4, 6)], [])
        _dawn.configure_canvas(cid, 31, 29, 0)
        assert _dawn.state_parameter(cid, 0xBA2) == (1, 2, 7, 5)
        assert _dawn.state_parameter(cid, 0xC10) == (2, 3, 4, 6)
    finally:
        _dawn.destroy_canvas(cid)


def test_valid_query_propagates_native_queued_failure_and_preserves_committed_prefix(canvas):
    canvas.context.glir.command('FUNC', 'glLineWidth', 3.)
    canvas.context.glir.command('FUNC', 'glDepthRange', float('nan'), 1.)
    with pytest.raises(RuntimeError, match='glDepthRange'):
        gl.glGetParameter(gl.GL_LINE_WIDTH)
    assert _dawn.state_parameter(canvas._backend._dawn_canvas_id, 0xB21) == 3.
    gl.glLineWidth(4.)
    assert gl.glGetParameter(gl.GL_LINE_WIDTH) == 4.


@pytest.mark.parametrize('samples,expected', [(0, 0), (4, 1)])
def test_sample_buffers_query_uses_actual_configuration(samples, expected):
    c = app.Canvas(app='dawn_headless', size=(7, 5), config={'samples': samples})
    try:
        c.set_current()
        assert gl.glGetParameter(gl.GL_SAMPLE_BUFFERS) == expected
        assert _dawn.framebuffer_config(c._backend._dawn_canvas_id)['sample_count'] == max(1, samples)
    finally:
        c.close()


@pytest.mark.parametrize('viewport', [
    (0, 0, 3), (0, 0, 3, 4, 5), [[0, 0, 3, 4]], ('invalid', 0, 3, 4),
])
def test_invalid_readback_viewport_preserves_native_queue(canvas, viewport):
    gloo.set_viewport(0, 0, 16, 12)
    gloo.clear(color=(1, 0, 0, 1))
    pending = canvas.context.glir._shared._commands
    snapshot = list(pending)
    assert snapshot
    with pytest.raises(ValueError):
        gloo.read_pixels(viewport=viewport)
    assert canvas.context.glir._shared._commands is pending
    assert pending == snapshot
    actual = gloo.read_pixels((0, 0, 16, 12), alpha=True)
    assert actual.shape == (12, 16, 4)
    np.testing.assert_array_equal(actual, np.full((12, 16, 4), [255, 0, 0, 255], np.uint8))


def test_default_readback_resolves_native_queued_viewport(canvas):
    gloo.set_viewport(0, 0, 16, 12)
    gloo.clear(color=(0, 0, 1, 1))
    gloo.finish()
    gloo.set_viewport(1, 2, 7, 5)
    gloo.clear(color=(0, 1, 0, 1))
    actual = gloo.read_pixels(alpha=True)
    assert actual.shape == (5, 7, 4)
    np.testing.assert_array_equal(actual, np.full((5, 7, 4), [0, 255, 0, 255], np.uint8))
