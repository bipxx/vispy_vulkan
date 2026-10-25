# SPDX-License-Identifier: AGPL-3.0-only
"""Pixel-exact scissor boundaries on actual single/multisample storage.

Clear and ordinary draw share the same independent rectangle oracle. No Tk,
shader discard, sample-count substitution or favorable retry hides the defect.
"""
import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu


def expected_rectangle(width, height, rectangle):
    image = np.zeros((height, width, 4), np.uint8)
    image[:, :, 3] = 255
    x, y, w, h = rectangle
    image[height - y - h:height - y, x:x + w] = [255, 0, 0, 255]
    return image


@pytest.mark.parametrize('samples', [0, 4])
@pytest.mark.parametrize('size', [(256, 128), (257, 129), (301, 177)])
@pytest.mark.parametrize('route', ['clear', 'draw'])
@pytest.mark.parametrize('region', ['left', 'right', 'upper', 'inset'])
def test_scissor_has_exact_integer_boundaries(samples, size, route, region):
    width, height = size
    rectangle = {'left': (0, 0, width // 2, height),
                 'right': (width // 2, 0, width - width // 2, height),
                 'upper': (0, height // 2, width, height - height // 2),
                 'inset': (17, 23, 101, 77)}[region]
    application = app.Application('dawn_headless')
    canvas = app.Canvas(app=application, size=size, show=False, config={'samples': samples})
    program = source = None
    try:
        canvas.set_current()
        assert gloo.get_gl_configuration()['sample_count'] == max(1, samples)
        gloo.set_viewport(0, 0, width, height)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False,
                       cull_face=False, scissor_test=False)
        gloo.set_color_mask(True, True, True, True)
        gloo.clear(color=(0, 0, 0, 1))
        gloo.set_scissor(*rectangle)
        gloo.set_state(scissor_test=True)
        if route == 'clear':
            gloo.clear(color=(1, 0, 0, 1))
        else:
            source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
            program = gloo.Program('attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}',
                                   'void main(){gl_FragColor=vec4(1,0,0,1);}')
            program['position'] = source
            program.draw('triangles')
        actual = gloo.read_pixels((0, 0, width, height), alpha=True)
        np.testing.assert_array_equal(actual, expected_rectangle(width, height, rectangle))
    finally:
        canvas.set_current()
        for obj in (program, source):
            if obj is not None:
                obj.delete()
        canvas.context.flush_commands()
        canvas.close()
        application.quit()
        _dawn.process_events()
