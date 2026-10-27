# SPDX-License-Identifier: AGPL-3.0-only
"""Finite public glStencilOp coverage; both faces must change on one call."""
import numpy as np
import pytest

from vispy import _dawn, gloo
from vispy.gloo import gl
from test_dawn_immediate_state import FULL, pixels, raw_scene

pytestmark = pytest.mark.gpu

# Literal stored values, not an implementation of the candidate's operation.
# Back write masks are 0x7f for full-front masks and 0xf0 for low-nibble masks.
VALUES = [
    pytest.param(gl.GL_KEEP, 0x35, 0x6a, 0xa6, 0xff, 0x35, 0x6a, 0x6a, id='keep'),
    pytest.param(gl.GL_ZERO, 0x35, 0xb6, 0xa6, 0xff, 0x00, 0x00, 0x80, id='zero'),
    pytest.param(gl.GL_REPLACE, 0x35, 0x5b, 0xa6, 0xff, 0xa6, 0xa6, 0x26, id='replace'),
    pytest.param(gl.GL_INVERT, 0x35, 0x96, 0xa6, 0xff, 0xca, 0x69, 0xe9, id='invert'),
    pytest.param(gl.GL_INCR, 0x35, 0x6f, 0xa6, 0xff, 0x36, 0x70, 0x70, id='increment'),
    pytest.param(gl.GL_INCR, 0xff, 0xff, 0xa6, 0xff, 0xff, 0xff, 0xff, id='increment-saturates'),
    pytest.param(gl.GL_DECR, 0x35, 0x80, 0xa6, 0xff, 0x34, 0x7f, 0xff, id='decrement'),
    pytest.param(gl.GL_DECR, 0x00, 0x00, 0xa6, 0xff, 0x00, 0x00, 0x00, id='decrement-saturates'),
    pytest.param(gl.GL_INCR_WRAP, 0xff, 0xff, 0xa6, 0xff, 0x00, 0x00, 0x80, id='increment-wraps'),
    pytest.param(gl.GL_INCR_WRAP, 0x35, 0x7f, 0xa6, 0xff, 0x36, 0x80, 0x00, id='increment-wrap-interior'),
    pytest.param(gl.GL_DECR_WRAP, 0x00, 0x00, 0xa6, 0xff, 0xff, 0xff, 0x7f, id='decrement-wraps'),
    pytest.param(gl.GL_DECR_WRAP, 0x35, 0x80, 0xa6, 0xff, 0x34, 0x7f, 0xff, id='decrement-wrap-interior'),
    pytest.param(gl.GL_INVERT, 0xa5, 0x3c, 0xa6, 0x0f, 0xaa, 0x33, 0xcc, id='masked-invert'),
    pytest.param(gl.GL_INCR, 0xaf, 0x9f, 0xa6, 0x0f, 0xa0, 0x90, 0xaf, id='increment-before-mask'),
    pytest.param(gl.GL_DECR, 0xa0, 0x90, 0xa6, 0x0f, 0xaf, 0x9f, 0x80, id='decrement-before-mask'),
    pytest.param(gl.GL_REPLACE, 0xa5, 0x96, 0x3c, 0x0f, 0xac, 0x9c, 0x36, id='masked-replace'),
]


def seed_halves(front, back):
    gl.glStencilMask(0xff)
    gl.glEnable(gl.GL_SCISSOR_TEST)
    for x, value in ((0, front), (8, back)):
        gl.glScissor(x, 0, 8, 12)
        gl.glClearStencil(value)
        gl.glClear(gl.GL_STENCIL_BUFFER_BIT)


def draw_halves(program, source):
    for x, positions in ((0, FULL), (8, FULL[::-1])):
        gl.glScissor(x, 0, 8, 12)
        source.set_data(positions)
        program.draw('triangles')


def assert_halves(program, source, front, back):
    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glDisable(gl.GL_SCISSOR_TEST)
    gl.glColorMask(True, True, True, True)
    gl.glStencilMask(0)
    gl.glStencilOpSeparate(gl.GL_FRONT_AND_BACK, gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP)
    gloo.clear(color=(0, 0, 0, 1), depth=False, stencil=False)
    gl.glEnable(gl.GL_SCISSOR_TEST)
    for face, x, positions, expected, color in (
        (gl.GL_FRONT, 0, FULL, front, (0, 1, 0, 1)),
        (gl.GL_BACK, 8, FULL[::-1], back, (0, 0, 1, 1)),
    ):
        gl.glScissor(x, 0, 8, 12)
        source.set_data(positions)
        for reference, paint in ((expected, color), (expected ^ 0xff, (1, 0, 0, 1))):
            gl.glStencilFuncSeparate(face, gl.GL_EQUAL, reference, 0xff)
            program['u_color'] = paint
            program.draw('triangles')
            literal = [0, 255, 0, 255] if face == gl.GL_FRONT else [0, 0, 255, 255]
            np.testing.assert_array_equal(pixels()[:, x:x+8], np.broadcast_to(literal, (12, 8, 4)))
    expected_image = np.empty((12, 16, 4), dtype=np.uint8)
    expected_image[:, :8] = [0, 255, 0, 255]
    expected_image[:, 8:] = [0, 0, 255, 255]
    np.testing.assert_array_equal(pixels(), expected_image)


@pytest.mark.parametrize('routing', ['shared', 'split'])
@pytest.mark.parametrize('branch', ['stencil-fail', 'depth-fail', 'pass'])
@pytest.mark.parametrize('operation,front_seed,back_seed,reference,mask,front_expected,back_shared,back_split', VALUES)
def test_public_stencil_op_updates_both_faces(raw_scene, routing, branch, operation,
        front_seed, back_seed, reference, mask, front_expected, back_shared, back_split):
    canvas, program, source = raw_scene
    config = _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)
    assert config['stencil_size'] == 8 and config['depth_stencil_format'] == 'depth24plus-stencil8'
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glFrontFace(gl.GL_CCW)
    seed_halves(front_seed, back_seed)
    gl.glEnable(gl.GL_STENCIL_TEST)
    gl.glStencilFunc(gl.GL_NEVER if branch == 'stencil-fail' else gl.GL_ALWAYS, reference, 0xff)
    gl.glStencilMaskSeparate(gl.GL_FRONT, mask)
    back_mask = mask if routing == 'shared' else (0x7f if mask == 0xff else 0xf0)
    gl.glStencilMaskSeparate(gl.GL_BACK, back_mask)
    # A stale selected operation must disagree with each face's literal oracle,
    # including wrap boundaries where INVERT can coincide with the target op.
    # Each nonzero write mask makes INVERT distinguishable when KEEP is right.
    index = ['stencil-fail', 'depth-fail', 'pass'].index(branch)
    back_expected = back_shared if routing == 'shared' else back_split
    front_prior = [gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP]
    back_prior = [gl.GL_INVERT, gl.GL_INVERT, gl.GL_INVERT]
    front_prior[index] = gl.GL_KEEP if front_expected != front_seed else gl.GL_INVERT
    back_prior[index] = gl.GL_KEEP if back_expected != back_seed else gl.GL_INVERT
    gl.glStencilOpSeparate(gl.GL_FRONT, *front_prior)
    gl.glStencilOpSeparate(gl.GL_BACK, *back_prior)
    operations = [gl.GL_KEEP, gl.GL_KEEP, gl.GL_KEEP]
    operations[index] = operation
    gl.glStencilOp(*operations)
    cid = canvas._backend._dawn_canvas_id
    front = tuple(_dawn.state_parameter(cid, int(s)) for s in
        (gl.GL_STENCIL_REF, gl.GL_STENCIL_VALUE_MASK, gl.GL_STENCIL_WRITEMASK))
    back = tuple(_dawn.state_parameter(cid, int(s)) for s in
        (gl.GL_STENCIL_BACK_REF, gl.GL_STENCIL_BACK_VALUE_MASK, gl.GL_STENCIL_BACK_WRITEMASK))
    assert (front == back) is (routing == 'shared')
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_ALWAYS if branch == 'pass' else gl.GL_NEVER)
    gl.glDepthMask(False)
    gl.glColorMask(False, False, False, False)
    draw_halves(program, source)
    assert_halves(program, source, front_expected, back_expected)


def test_public_stencil_op_rejection_preserves_both_faces_and_recovers(raw_scene):
    _, program, source = raw_scene
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glFrontFace(gl.GL_CCW)
    seed_halves(0x30, 0x60)
    gl.glEnable(gl.GL_STENCIL_TEST)
    gl.glStencilFunc(gl.GL_NEVER, 0, 0xff)
    gl.glStencilOp(gl.GL_INCR, gl.GL_KEEP, gl.GL_KEEP)
    with pytest.raises(RuntimeError, match='glStencilOp'):
        gl.glStencilOp(gl.GL_ZERO, gl.GL_KEEP, 123456)
    gl.glColorMask(False, False, False, False)
    draw_halves(program, source)
    assert_halves(program, source, 0x31, 0x61)
    gl.glStencilMask(0xff)
    gl.glStencilFunc(gl.GL_ALWAYS, 0, 0xff)
    gl.glStencilOp(gl.GL_KEEP, gl.GL_KEEP, gl.GL_INVERT)
    gl.glColorMask(False, False, False, False)
    draw_halves(program, source)
    assert_halves(program, source, 0xce, 0x9e)
