"""Public stencil capture improves on stock VisPy; raw GL remains explicit."""
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
CASES = ('stencil_float', 'stencil_u8', 'stencil_crop_float', 'stencil_noalpha_u8')


@pytest.fixture
def stencil_target():
    from vispy import _dawn, app, gloo
    canvas = app.Canvas(app='dawn_headless', size=(8, 6), show=False)
    canvas.set_current()
    color = gloo.Texture2D(np.zeros((6, 8, 4), np.uint8))
    packed = gloo.RenderBuffer((6, 8), format=0x88F0)
    target = gloo.FrameBuffer(color=color, depth=packed, stencil=packed)
    vertices = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    program = gloo.Program(
        'attribute vec2 a_position; void main(){gl_Position=vec4(a_position,-0.5,1.);}',
        'void main(){gl_FragColor=vec4(0.,1.,0.,1.);}')
    program['a_position'] = vertices
    try:
        with target:
            gloo.set_viewport(0, 0, 8, 6)
            gloo.set_state(blend=False, scissor_test=False, depth_test=True, stencil_test=True)
            gloo.set_depth_mask(True)
            gloo.set_stencil_mask(255)
            gloo.set_clear_depth(1.)
            gloo.set_clear_stencil(3)
            gloo.clear(color=(0., 0., 0., 1.), depth=True, stencil=True)
            gloo.set_state(scissor_test=True)
            gloo.set_scissor(4, 3, 3, 2)
            gloo.set_clear_stencil(203)
            gloo.clear(color=False, depth=False, stencil=True)
            gloo.set_scissor(1, 1, 3, 2)
            gloo.set_depth_func('always')
            gloo.set_stencil_func('always', 37, 255)
            gloo.set_stencil_op('keep', 'keep', 'replace')
            program.draw('triangles')
            gloo.set_state(scissor_test=False)
            yield gloo
    finally:
        for obj in (program, vertices, target, packed, color):
            obj.delete()
        gloo.flush()
        canvas.close()
        _dawn.process_events()
    names = ('pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
             'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
             'line_resource_pool_busy_slots', 'line_resource_pool_bytes')
    gauges = {name: _dawn.probe()[name] for name in names}
    assert not any(gauges.values()), gauges


def capture(gloo, name):
    viewport = (2, 1, 4, 3) if 'crop' in name else (0, 0, 8, 6)
    out_type = 'unsigned_byte' if name.endswith('u8') else 'float'
    return gloo.read_pixels(viewport, mode='stencil', out_type=out_type,
                            alpha='noalpha' not in name)


@pytest.mark.parametrize('name', CASES)
def test_public_stencil_capture_values_crop_type_and_mutation(stencil_target, name):
    gloo = stencil_target
    image = capture(gloo, name)
    reference = np.load(Path(__file__).resolve().parents[1] /
                        'reference/stencil-capture-opengl' / (name + '.npy'), allow_pickle=False)
    assert image.dtype == reference.dtype and image.shape == reference.shape
    np.testing.assert_array_equal(image, reference)
    # Mutation through the public wrapper, without an explicit finish/read barrier.
    gloo.clear(color=False, depth=False, stencil=29)
    changed = capture(gloo, name)
    assert changed.shape == image.shape and changed.dtype == image.dtype
    assert np.all(changed == 29)


@pytest.mark.parametrize('name', CASES)
def test_raw_stencil_read_refuses_then_public_wrapper_recovers(stencil_target, name):
    from vispy.gloo.gl.dawn import DawnCompatibilityError
    gloo = stencil_target
    viewport = (2, 1, 4, 3) if 'crop' in name else (0, 0, 8, 6)
    data_type = gloo.gl.GL_UNSIGNED_BYTE if name.endswith('u8') else gloo.gl.GL_FLOAT
    with pytest.raises(DawnCompatibilityError, match='glReadPixels.*not supported'):
        gloo.gl.glReadPixels(*viewport, 0x1901, data_type)
    # Refusal must neither consume pending draws nor corrupt the selected target.
    reference = np.load(Path(__file__).resolve().parents[1] /
                        'reference/stencil-capture-opengl' / (name + '.npy'), allow_pickle=False)
    np.testing.assert_array_equal(capture(gloo, name), reference)
    gloo.clear(color=False, depth=False, stencil=29)
    assert np.all(capture(gloo, name) == 29)
