# SPDX-License-Identifier: AGPL-3.0-only
"""Uniform writes follow public command order, including overlapping array writes."""
import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('type_name,initial,indexed,replacement,expression,first,second', [
    ('float', [[0.], [0.]], [.25], [[.75], [.5]], 'u_values[0]', .25, .75),
    ('int', [[0], [0]], [17], [[35], [9]], 'float(u_values[0])', 17., 35.),
    ('bool', [[False], [False]], [True], [[False], [True]], '(u_values[0] ? 1.0 : 0.0)', 1., 0.),
    ('mat2', [[0., 0., 0., 0.], [0., 0., 0., 0.]], [.1, .25, .5, .9],
     [[.3, .75, .2, .8], [.4, .5, .6, .7]], 'u_values[0][0][1]', .25, .75),
])
@pytest.mark.parametrize('draw_before_whole', [False, True])
def test_later_whole_array_replaces_earlier_element_write(
        type_name, initial, indexed, replacement, expression, first, second, draw_before_whole):
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), show=False, config={'samples': 0})
    program = positions = None
    try:
        canvas.set_current()
        program = gloo.Program(
            'attribute vec2 position; void main(){gl_Position=vec4(position,0,1);}',
            'uniform ' + type_name + ' u_values[2]; uniform float u_expected; '
            'void main(){gl_FragColor=abs(' + expression + '-u_expected)<0.00001 '
            '? vec4(0,1,0,1) : vec4(1,0,0,1);}')
        positions = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program['position'] = positions
        gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, scissor_test=False)

        def check(expected):
            program['u_expected'] = expected
            program.draw('triangles')
            np.testing.assert_array_equal(
                gloo.read_pixels((0, 0, 8, 8), alpha=True),
                np.broadcast_to(np.array([0, 255, 0, 255], np.uint8), (8, 8, 4)))

        program['u_values'] = initial
        program['u_values[0]'] = indexed
        if draw_before_whole:
            check(first)
        program['u_values'] = replacement
        check(second)
        program['u_values[0]'] = indexed
        check(first)
    finally:
        canvas.set_current()
        for value in (program, positions):
            if value is not None:
                value.delete()
        canvas.context.flush_commands()
        canvas.close()
