# SPDX-License-Identifier: AGPL-3.0-only
"""Depth-range mapping must preserve original clipping and captured draw state."""
import numpy as np
import pytest
from vispy import _dawn, app, gloo
from vispy.gloo import gl

pytestmark = pytest.mark.gpu
SIZE = (24, 16)
FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
VERTEX = ('attribute vec2 position; uniform float z; uniform float w; '
          'void main(){gl_Position=vec4(position*w,z*w,w);gl_PointSize=5.;}')


@pytest.fixture
def scene():
    canvas = app.Canvas(app='dawn_headless', size=SIZE)
    canvas.set_current()
    program = gloo.Program(VERTEX, 'uniform vec4 color;void main(){gl_FragColor=color;}')
    source = gloo.VertexBuffer(FULL)
    program['position'] = source
    program['z'], program['w'], program['color'] = -.5, 1., (1, 0, 0, 1)
    gl.glViewport(0, 0, *SIZE)
    gl.glClearColor(0, 0, 0, 1)
    try:
        yield canvas, program, source
    finally:
        program.delete()
        source.delete()
        canvas.context.flush_commands()
        canvas.close()


def read():
    return gloo.read_pixels((0, 0, *SIZE), alpha=True)


@pytest.mark.parametrize('near,far', [(1., 0.), (.8, .2), (2., -1.), (.4, .4), (0., 1.)])
@pytest.mark.parametrize('comparison', [gl.GL_LESS, gl.GL_GREATER])
def test_depth_range_ordering_clamps_and_equal_endpoints(scene, near, far, comparison):
    _, program, _ = scene
    gl.glDepthRange(near, far)
    n, f = np.clip([near, far], 0, 1)
    assert gl.glGetParameter(gl.GL_DEPTH_RANGE) == tuple(float(np.float32(x)) for x in (n, f))
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(comparison)
    gl.glClearDepth(1. if comparison == gl.GL_LESS else 0.)
    gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
    program.draw('triangles')
    program['z'], program['color'] = .5, (0, 0, 1, 1)
    program.draw('triangles')
    second = n != f and ((n < f) == (comparison == gl.GL_GREATER))
    assert np.all(read() == ([0, 0, 255, 255] if second else [255, 0, 0, 255]))


@pytest.mark.parametrize('depth_test,write_mask', [(False, True), (True, False)])
def test_reversed_range_preserves_disabled_test_and_write_mask(scene, depth_test, write_mask):
    _, program, _ = scene
    gl.glDepthRange(1., 0.)
    (gl.glEnable if depth_test else gl.glDisable)(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LESS)
    gl.glClearDepth(1.)
    gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
    gl.glDepthMask(write_mask)
    program.draw('triangles')
    program['z'], program['color'] = -.75, (0, 0, 1, 1)
    program.draw('triangles')
    assert np.all(read() == [0, 0, 255, 255])


@pytest.mark.parametrize('mode,width', [('triangles', 1.), ('lines', 1.), ('lines', 6.), ('points', 1.)])
def test_reversed_depth_matches_readback_for_ordinary_generated_lines_and_points(scene, mode, width):
    _, program, source = scene
    if mode == 'lines':
        source.set_data(np.array([[-.75, 0], [.75, 0]], np.float32))
    elif mode == 'points':
        source.set_data(np.array([[0, 0]], np.float32))
    gl.glDepthRange(.8, .2)
    gl.glLineWidth(width)
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_ALWAYS)
    gl.glClearDepth(0.)
    gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
    program['w'] = 2.
    program.draw(mode)
    color = read()
    drawn = color[:, :, 0] == 255
    assert np.any(drawn)
    depth = gloo.read_pixels((0, 0, *SIZE), mode='depth', out_type='float')
    assert np.allclose(depth.reshape(SIZE[1], SIZE[0])[drawn], .65, atol=2e-6)


def test_reversed_range_keeps_original_clip_planes(scene):
    _, program, _ = scene
    gl.glDepthRange(.8, .2)
    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    for z in (-1.5, 1.5):
        program['z'] = z
        program.draw('triangles')
    assert np.all(read() == [0, 0, 0, 255])


def test_queued_forward_reverse_forward_draws_keep_their_own_shader_orientation(scene):
    canvas, program, _ = scene
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LESS)
    gl.glClearDepth(.5)
    gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
    for column, near, far in [(0, 0., 1.), (8, 1., 0.), (16, 0., 1.)]:
        canvas.context.glir.command('FUNC', 'glDepthRange', near, far)
        canvas.context.glir.command('FUNC', 'glEnable', 'scissor_test')
        canvas.context.glir.command('FUNC', 'glScissor', column, 0, 8, 16)
        program.draw('triangles')
    image = read()
    assert np.all(image[:, :8] == [255, 0, 0, 255])
    assert np.all(image[:, 8:16] == [0, 0, 0, 255])
    assert np.all(image[:, 16:] == [255, 0, 0, 255])


@pytest.mark.parametrize('near,far', [(.2, .8), (.8, .2), (1., 0.)])
def test_explicit_fragment_depth_is_window_depth_not_depth_range_mapped(scene, near, far):
    _, _, source = scene
    program = gloo.Program(VERTEX, 'uniform float explicit_depth;void main(){'
                           'gl_FragDepth=explicit_depth;gl_FragColor=vec4(1,0,0,1);}')
    program['position'] = source
    program['z'], program['w'], program['explicit_depth'] = .5, 1., .1
    try:
        gl.glDepthRange(near, far)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)
        gl.glClearDepth(.15)
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
        program.draw('triangles')
        assert np.all(read() == [255, 0, 0, 255])
    finally:
        program.delete()


@pytest.mark.parametrize('mode,width', [('triangles', 1.), ('lines', 6.), ('points', 1.)])
@pytest.mark.parametrize('aliases', [False, True])
def test_fragment_coordinate_depth_stays_logical_with_explicit_depth_output(scene, mode, width, aliases):
    _, _, source = scene
    if mode == 'lines':
        source.set_data(np.array([[-.75, 0], [.75, 0]], np.float32))
    elif mode == 'points':
        source.set_data(np.array([[0, 0]], np.float32))
    fragment = ('#define COORD gl_FragCoord\n#define DEPTH gl_FragDepth\n'
                'void main(){DEPTH=.1;gl_FragColor=vec4(COORD.z,0,0,1);}') if aliases else (
                'void main(){gl_FragDepth=.1;gl_FragColor=vec4(gl_FragCoord.z,0,0,1);}')
    program = gloo.Program(VERTEX, fragment)
    program['position'] = source
    program['z'], program['w'] = -.5, 2.
    try:
        gl.glDepthRange(.8, .2)
        gl.glLineWidth(width)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)
        gl.glClearDepth(.15)
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
        program.draw(mode)
        image = read()
        drawn = image[:, :, 0] > 0
        assert np.any(drawn)
        assert np.all(np.abs(image[:, :, 0][drawn].astype(int) - 166) <= 1)
        depth = gloo.read_pixels((0, 0, *SIZE), mode='depth', out_type='float')
        assert np.allclose(depth.reshape(SIZE[1], SIZE[0])[drawn], .1, atol=2e-6)
    finally:
        program.delete()


def test_reversed_range_preserves_indexed_and_instanced_identity(scene):
    _, _, source = scene
    program = gloo.Program(
        '#version 130\nin vec2 position;in float instance_bias;flat out int lane;void main(){'
        'lane=gl_InstanceID;gl_Position=vec4(position,-.5+float(gl_VertexID)*.125+instance_bias,1);}',
        '#version 130\nflat in int lane;out vec4 color;void main(){'
        'if((gl_FragCoord.x<12.)!=(lane==0))discard;'
        'color=lane==0?vec4(1,0,0,1):vec4(0,0,1,1);}')
    indices = gloo.IndexBuffer(np.array([2, 0, 1], np.uint16))
    program['position'] = source
    instances = gloo.VertexBuffer(np.zeros(2, np.float32), divisor=1)
    program['instance_bias'] = instances
    try:
        gl.glDepthRange(1., 0.)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_GREATER)
        gl.glClearDepth(.5)
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
        program.draw('triangles', indices)
        image = read()
        assert np.all(image[:, :12] == [255, 0, 0, 255])
        assert np.all(image[:, 12:] == [0, 0, 255, 255])
    finally:
        program.delete()
        indices.delete()
        instances.delete()


@pytest.mark.parametrize('explicit', [False, True])
def test_reversed_orientation_and_fragment_controls_recover_after_device_loss(scene, explicit):
    _, original, source = scene
    program = original
    if explicit:
        program = gloo.Program(VERTEX, 'void main(){gl_FragDepth=.1;'
                               'gl_FragColor=vec4(gl_FragCoord.z,0,0,1);}')
        program['position'] = source
        program['z'], program['w'] = -.5, 1.
    try:
        gl.glDepthRange(.8, .2)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS if explicit else gl.GL_GREATER)
        gl.glClearDepth(.15 if explicit else .5)
        for lost in (False, True):
            if lost:
                _dawn.lose_device()
                _dawn.process_events()
            gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
            program.draw('triangles')
            image = read()
            assert np.all(np.abs(image[:, :, 0].astype(int) - (166 if explicit else 255)) <= 1)
            assert np.all(image[:, :, 1:3] == 0)
    finally:
        if explicit:
            program.delete()
