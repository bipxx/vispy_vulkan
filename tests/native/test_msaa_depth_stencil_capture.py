# SPDX-License-Identifier: AGPL-3.0-only
"""Default-target depth/stencil capture with uniform samples, not edge parity."""
import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (12, 8)


@pytest.mark.parametrize('samples', [0, 4])
@pytest.mark.parametrize('mode', ['depth', 'stencil'])
@pytest.mark.parametrize('out_type', ['float', 'unsigned_byte'])
@pytest.mark.parametrize('crop', [False, True])
def test_default_depth_stencil_capture_values_crop_mutation_and_restore(
        samples, mode, out_type, crop):
    from vispy import _dawn, app, gloo

    canvas = app.Canvas(app='dawn_headless', size=SIZE, show=False,
                        config={'samples': samples})
    program = vertices = None
    viewport = (2, 1, 7, 5) if crop else (0, 0, *SIZE)
    try:
        canvas.set_current()
        vertices = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program = gloo.Program(
            'attribute vec2 position; void main(){gl_Position=vec4(position,-0.5,1.);}',
            'void main(){gl_FragColor=vec4(0.,1.,0.,1.);}')
        program['position'] = vertices
        gloo.set_viewport(0, 0, *SIZE)
        gloo.set_state(blend=False, cull_face=False, depth_test=True,
                       stencil_test=True, scissor_test=False)
        gloo.set_depth_mask(True)
        gloo.set_depth_func('always')
        gloo.set_stencil_mask(255)
        gloo.set_stencil_func('always', 37, 255)
        gloo.set_stencil_op('keep', 'keep', 'replace')

        def pattern():
            gloo.set_state(scissor_test=False)
            gloo.clear(color=(0., 0., 0., 1.), depth=.75, stencil=3)
            gloo.set_state(scissor_test=True)
            gloo.set_scissor(1, 1, 5, 4)
            # Full triangle plus integer scissor gives equal values in every
            # covered sample. This cannot distinguish sample-zero from an
            # average or another sample at a partially covered edge.
            program.draw('triangles')
            gloo.set_state(scissor_test=False)

        def expected(mutated=False):
            value = (.5 if mutated else .75) if mode == 'depth' else (29 if mutated else 3)
            image = np.full((SIZE[1], SIZE[0], 1), value, np.float32)
            if not mutated:
                # Public readback arrays are top-left; viewport/scissor is
                # bottom-left. This asymmetric region makes flips observable.
                image[3:7, 1:6] = .25 if mode == 'depth' else 37
            x, y, width, height = viewport
            image = image[SIZE[1] - y - height:SIZE[1] - y, x:x + width]
            if out_type == 'unsigned_byte':
                image = (np.floor(image.astype(np.float64) * 255 + .5).astype(np.uint8)
                         if mode == 'depth' else image.astype(np.uint8))
            return image

        def capture(mutated=False):
            image = gloo.read_pixels(viewport, mode=mode, out_type=out_type, alpha=False)
            reference = expected(mutated)
            assert image.shape == reference.shape and image.dtype == reference.dtype
            if mode == 'depth' and out_type == 'float':
                np.testing.assert_allclose(image, reference, rtol=0, atol=1e-6)
            else:
                np.testing.assert_array_equal(image, reference)
            return image

        def assert_color_pattern():
            color = gloo.read_pixels((0, 0, *SIZE), alpha=True)
            reference = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
            reference[..., 3] = 255
            reference[3:7, 1:6] = [0, 255, 0, 255]
            np.testing.assert_array_equal(color, reference)

        pattern()
        before = capture()
        assert_color_pattern()
        configuration = _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)
        assert configuration['framebuffer_id'] == 0
        assert configuration['sample_count'] == max(1, samples)
        assert configuration['depth_stencil_format'] == 'depth24plus-stencil8'
        gloo.clear(color=False, depth=.5, stencil=29)
        capture(mutated=True)
        # Check before pattern() can repair an unintended color modification.
        assert_color_pattern()
        # Invalid region shape is refused; a subsequent draw/capture must
        # still restore the original values.
        with pytest.raises(ValueError, match='viewport'):
            gloo.read_pixels((0, 0, 1), mode=mode, out_type=out_type)
        pattern()
        restored = capture()
        np.testing.assert_array_equal(restored, before)
        assert_color_pattern()
    finally:
        if program is not None:
            program.delete()
        if vertices is not None:
            vertices.delete()
        canvas.close()
        _dawn.process_events()
