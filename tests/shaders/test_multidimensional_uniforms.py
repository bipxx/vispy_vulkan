# SPDX-License-Identifier: AGPL-3.0-only
"""Render multidimensional uploads against independent one-dimensional scalars."""
import numpy as np
import pytest
from vispy import app, gloo

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('gtype,components', [('float', 1), ('int', 1), ('bool', 1),
                                            ('vec3', 3), ('bvec3', 3), ('mat2', 4),
                                            ('mat2x3', 6), ('mat2x4', 8),
                                            ('mat3x2', 6), ('mat3x4', 12),
                                            ('mat4x2', 8), ('mat4x3', 12)])
@pytest.mark.parametrize('intermediate_draws', [False, True])
@pytest.mark.parametrize('topology', ['triangles', 'lines'])
def test_nested_uniform_upload_order(gtype, components, intermediate_draws, topology):
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), show=False, config={'samples': 0})
    program = positions = None
    try:
        canvas.set_current()
        checks = []
        for row in range(2):
            for column in range(3):
                for component in range(components):
                    element = 'grid[%d][%d]' % (row, column)
                    if gtype in ('vec3', 'bvec3'):
                        element += '[%d]' % component
                    elif gtype.startswith('mat'):
                        rows = int(gtype[-1])
                        element += '[%d][%d]' % (component // rows, component % rows)
                    checks.append('abs(float(%s)-expected[%d])<0.00001' %
                                  (element, (row * 3 + column) * components + component))
        program = gloo.Program(
            'attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}',
            'uniform %s grid[2][3];uniform float expected[%d];' % (gtype, 6 * components) +
            'void main(){gl_FragColor=(' + '&&'.join(checks) +
            ')?vec4(0,1,0,1):vec4(1,0,0,1);}')
        vertices = ([[-1, -1], [3, -1], [-1, 3]] if topology == 'triangles'
                    else [[-.8, 0], [.8, 0]])
        positions = gloo.VertexBuffer(np.array(vertices, np.float32))
        program['position'] = positions
        gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, scissor_test=False, line_width=4)
        dtype = np.int32 if gtype in ('int', 'bool') else np.float32
        expected = np.arange(6 * components, dtype=dtype).reshape(2, 3, components) - 3
        if gtype in ('bool', 'bvec3'):
            expected = (expected % 2).astype(dtype)

        def check():
            program['expected'] = expected.astype(np.float32).reshape(-1, 1)
            gloo.clear(color=(1, 0, 0, 1))
            program.draw(topology)
            pixels = gloo.read_pixels((0, 0, 8, 8), alpha=True)
            if topology == 'lines':
                pixels = pixels[3:5, 3:5]
            np.testing.assert_array_equal(pixels,
                np.broadcast_to(np.array([0, 255, 0, 255], np.uint8), pixels.shape))

        program['grid'] = expected.copy()
        if intermediate_draws:
            check()
        expected[1, 2] = 1 if gtype in ('bool', 'bvec3') else -7
        program['grid[1][2]'] = expected[1, 2].copy()
        if intermediate_draws:
            check()
        expected[1] = 0 if gtype in ('bool', 'bvec3') else 13
        program['grid[1]'] = expected[1].copy()
        check()  # Subarray must retire the prior leaf override.
        expected[:] = 1 if gtype in ('bool', 'bvec3') else -17
        program['grid'] = expected.copy()
        check()  # Whole write must retire the subarray override.
        expected[0, 1] = 0 if gtype in ('bool', 'bvec3') else 29
        program['grid[0][1]'] = expected[0, 1].copy()
        check()  # A later leaf remains visible over the whole value.
    finally:
        canvas.set_current()
        for item in (program, positions):
            if item is not None:
                item.delete()
        canvas.context.flush_commands()
        canvas.close()
