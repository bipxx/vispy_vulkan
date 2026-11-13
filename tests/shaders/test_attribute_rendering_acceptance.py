# SPDX-License-Identifier: AGPL-3.0-only
"""Independent matrix geometry plus retained aggregate-input pixel oracles."""
import json
import numpy as np
import pytest
from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('interleaved', [False, True])
@pytest.mark.parametrize('divisor', [1, 2])
def test_nonsymmetric_matrix_instances_partial_update_and_loss(interleaved, divisor):
    size = 16
    canvas = app.Canvas(app='dawn_headless', size=(size, size), config={'samples': 0})
    owned = []
    try:
        canvas.set_current();gloo.set_viewport(0, 0, size, size)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
        vertex = ('attribute vec2 position;attribute mat3x2 transform;varying vec4 color;'
                  'void main(){vec2 point=transform*vec3(position,1);'
                  'point.y+=float(gl_InstanceID%%%d)*.5;gl_Position=vec4(point,0,1);'
                  'color=gl_InstanceID/%d==0?vec4(1,0,0,1):vec4(0,0,1,1);}') % (divisor, divisor)
        program = gloo.Program(vertex, 'varying vec4 color;void main(){gl_FragColor=color;}')
        positions = gloo.VertexBuffer(np.array([[-.5, -.5], [.5, -.5], [-.5, .5],
                                                [-.5, .5], [.5, -.5], [.5, .5]], np.float32))
        dtype = ([('prefix', np.float32, 3)] if interleaved else []) + [('transform', np.float32, (3, 2))]
        records = np.zeros(2, dtype=dtype)
        sy, ty = (1., 0.) if divisor == 1 else (.5, -.25)
        for index, tx in enumerate((-.5, .5)):
            records['transform'][index] = [[.5, 0.], [.25, sy], [tx, ty]]
        matrices = gloo.VertexBuffer(records, divisor=divisor)
        owned.extend([positions, matrices, program]);program['position'] = positions
        program['transform'] = matrices['transform']
        def check(right_tx):
            gloo.clear(color=(0, 0, 0, 1));program.draw('triangles')
            actual = gloo.read_pixels((0, 0, size, size), alpha=True)
            expected = np.zeros((size, size, 4), np.uint8);expected[:, :, 3] = 255
            # Pixel-center inverse of x=.5*u+.25*v+tx, y=sy*v+ty+lane*.5.
            # The constants keep every selected sample away from polygon edges.
            for row in range(size):
                y = 1. - 2. * (row + .5) / size
                for column in range(size):
                    x = 2. * (column + .5) / size - 1.
                    for index, tx in enumerate((-.5, right_tx)):
                        for lane in range(divisor):
                            v = (y - ty - lane * .5) / sy
                            u = (x - .25 * v - tx) / .5
                            if abs(u) < .5 and abs(v) < .5:
                                expected[row, column] = (255, 0, 0, 255) if index == 0 else (0, 0, 255, 255)
            np.testing.assert_array_equal(actual, expected)
        check(.5)
        update = records[1:].copy();update['transform'][0, 2, 0] = .375
        matrices.set_subdata(update, offset=1)
        check(.375)
        generation = _dawn.probe()['device_generation']
        _dawn.lose_device();canvas.set_current();gloo.set_viewport(0, 0, size, size)
        check(.375)
        assert _dawn.probe()['device_generation'] > generation
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()


@pytest.mark.parametrize('group', ['raw', 'indexed', 'composed'])
def test_existing_aggregate_input_pixel_oracles(group):
    from tools.aggregate_attribute_smoke import (
        aggregate_attribute_checks, aggregate_indexed_checks, composed_attribute_checks)
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), config={'samples': 0})
    try:
        canvas.set_current();gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
        if group == 'raw':
            report = aggregate_attribute_checks(gloo, np, _dawn.device_info()['max_vertex_attributes'])
        elif group == 'indexed':report = aggregate_indexed_checks(gloo, np)
        else:report = composed_attribute_checks(gloo, np)
        print('ATTRIBUTE_FIXTURE_RESULT=' + json.dumps(dict(group=group, report=report)))
    finally:
        canvas.context.flush_commands();canvas.close();_dawn.process_events()


@pytest.mark.parametrize('mode', ['triangles', 'points', 'lines'])
def test_attribute_route_limits_and_raster_refusal_recovery(mode):
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), config={'samples': 0})
    owned = []
    try:
        canvas.set_current();gloo.set_viewport(0, 0, 16, 16)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
        gloo.set_line_width(5)
        limit = _dawn.device_info()['max_point_vertex_attributes' if mode == 'points' else 'max_vertex_attributes']
        assert 2 <= limit <= 64, 'This finite boundary fixture needs a revised budget for larger grants'
        vertices = dict(triangles=[[-1, -1], [3, -1], [-1, 3]], points=[[0, 0]], lines=[[-.75, 0], [.75, 0]])
        positions = gloo.VertexBuffer(np.asarray(vertices[mode], np.float32));owned.append(positions)
        def program(count):
            terms = ['%d.*values[%d]' % (index + 1, index) for index in range(count)]
            vertex = ('attribute vec2 position;attribute vec4 values[%d];varying vec4 color;'
                      'void main(){gl_Position=vec4(position,0,1);gl_PointSize=5.;color=(%s)/%d.;}') % (
                          count, '+'.join(terms), count * (count + 1) // 2)
            result = gloo.Program(vertex, 'varying vec4 color;void main(){gl_FragColor=color;}')
            owned.append(result);result['position'] = positions
            result['values'] = tuple([0., 1., 0., 1.] * (count - 1) + [0., 0., 1., 1.])
            return result
        # Raster/point inputs obey the attribute grant. Generated wide lines
        # evaluate inputs in compute and instead obey storage/compute grants.
        extra = program(limit)
        if mode == 'lines':
            gloo.clear(color=(0, 0, 0, 1));extra.draw(mode)
            actual = gloo.read_pixels((0, 0, 16, 16), alpha=True)[8, 8].astype(np.int16)
            blue = 2. / (limit + 1)
            expected = np.rint(np.array([0., 1. - blue, blue, 1.]) * 255).astype(np.int16)
            assert np.all(np.abs(actual - expected) <= 1)
        else:
            with pytest.raises(RuntimeError, match='exceed granted attribute limit'):
                extra.draw(mode)
        # The raster routes recover on that same canvas at the exact grant.
        accepted = program(limit - 1)
        gloo.clear(color=(0, 0, 0, 1));accepted.draw(mode)
        actual = gloo.read_pixels((0, 0, 16, 16), alpha=True)[8, 8].astype(np.int16)
        blue = 2. / limit
        expected = np.rint(np.array([0., 1. - blue, blue, 1.]) * 255).astype(np.int16)
        assert np.all(np.abs(actual - expected) <= 1), (mode, limit, actual, expected)
    finally:
        canvas.set_current()
        for resource in reversed(owned):resource.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()
