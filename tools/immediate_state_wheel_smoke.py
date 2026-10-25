# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise GLIR state compatibility in an external installed wheel.

Functional pixels and exact loaded source/native bytes only; not aggregate
OpenGL absence or upstream parity qualification.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sysconfig
import traceback
import zipfile


def uniform_array_update_checks(gloo, np, width, height):
    """Independent exact-pixel checks for overlapping public uniform assignments."""
    cases = [
        ('float', [[0.], [0.]], [.25], [[.75], [.5]], 'u_values[0]', .25, .75),
        ('int', [[0], [0]], [17], [[35], [9]], 'float(u_values[0])', 17., 35.),
        ('bool', [[False], [False]], [True], [[False], [True]], '(u_values[0]?1.0:0.0)', 1., 0.),
        ('mat2', [[0., 0., 0., 0.]] * 2, [.1, .25, .5, .9],
         [[.3, .75, .2, .8], [.4, .5, .6, .7]], 'u_values[0][0][1]', .25, .75),
    ]
    gloo.set_viewport(0, 0, width, height)
    gloo.set_state(blend=False, depth_test=False, scissor_test=False)
    positions = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    results = []
    try:
        for type_name, initial, indexed, replacement, expression, first, second in cases:
            for draw_before_whole in (False, True):
                program = gloo.Program(
                    'attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}',
                    'uniform ' + type_name + ' u_values[2];uniform float u_expected;'
                    'void main(){gl_FragColor=abs(' + expression + '-u_expected)<0.00001'
                    '?vec4(0,1,0,1):vec4(1,0,0,1);}')
                try:
                    program['position'] = positions

                    def check(expected):
                        program['u_expected'] = expected
                        program.draw('triangles')
                        image = gloo.read_pixels((0, 0, width, height), alpha=True)
                        assert np.all(image == [0, 255, 0, 255]), (type_name, draw_before_whole, expected)

                    program['u_values'] = initial
                    program['u_values[0]'] = indexed
                    if draw_before_whole:
                        check(first)
                    program['u_values'] = replacement
                    check(second)
                    program['u_values[0]'] = indexed
                    check(first)
                    results.append({'type': type_name, 'draw_before_whole': draw_before_whole, 'status': 'PASS'})
                finally:
                    program.delete()
    finally:
        positions.delete()
        gloo.flush()
    return results


def _multidimensional_uniform_case(gloo, np, gtype, components, intermediate_draws, topology):
    """Compare every nested component against an independent 1D scalar upload."""
    program = positions = None
    try:
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
        for item in (program, positions):
            if item is not None:
                item.delete()
        gloo.flush()


def multidimensional_uniform_checks(gloo, np):
    """Installed-wheel nested arrays, matrices, write order and line consumers."""
    results = []
    cases = [('float', 1), ('int', 1), ('bool', 1), ('vec3', 3), ('bvec3', 3),
             ('mat2', 4), ('mat2x3', 6), ('mat2x4', 8), ('mat3x2', 6),
             ('mat3x4', 12), ('mat4x2', 8), ('mat4x3', 12)]
    for gtype, components in cases:
        for topology in ('triangles', 'lines'):
            for intermediate_draws in (False, True):
                _multidimensional_uniform_case(gloo, np, gtype, components, intermediate_draws, topology)
                results.append({'type': gtype, 'topology': topology,
                                'intermediate_draws': intermediate_draws, 'status': 'PASS'})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; use a fresh receipt')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {'status': 'FAIL', 'scope': 'installed functional state compatibility'}
    canvas = native = None
    try:
        import numpy as np
        import vispy
        from vispy import app, gloo, _dawn as native
        from vispy.gloo import gl
        from vispy.gloo.gl import dawn
        package = Path(vispy.__file__).resolve().parent
        package.relative_to(Path(sysconfig.get_path('platlib')).resolve())
        origins = {}
        with zipfile.ZipFile(args.wheel) as archive:
            assert any(name.endswith('.dist-info/WHEEL') for name in archive.namelist()), 'not a wheel'
            for name in (Path(native.__file__).name, 'gloo/gl/dawn.py',
                         'gloo/dawn_parser.py', 'gloo/wrappers.py',
                         'gloo/program.py', 'gloo/glir.py'):
                path = package / name
                expected = hashlib.sha256(archive.read('vispy/' + name)).hexdigest()
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                assert actual == expected, 'loaded wheel member differs: ' + name
                origins[name] = actual
        assert Path(dawn.__file__).resolve() == package / 'gloo/gl/dawn.py'
        result['verified_members'] = origins
        canvas = app.Canvas(app='dawn_headless', size=(12, 8))
        canvas.set_current()
        gl.glViewport(0, 0, 12, 8)
        assert native.submission_contract_version >= 1
        counter_names = ('dawn_queue_submits', 'finish_calls', 'completion_waits', 'application_presents')
        def counters():
            values = native.probe()
            return {key: values[key] for key in counter_names}
        synchronization = []
        for route, synchronize in (('gloo.flush', gloo.flush), ('gl.glFlush', gl.glFlush)):
            before = counters()
            gloo.clear(color='blue')
            synchronize()
            after = counters()
            assert after['dawn_queue_submits'] > before['dawn_queue_submits'], route
            assert all(after[key] == before[key] for key in counter_names[1:]), route
            synchronization.append(dict(route=route, before=before, after=after))
        gl.glScissor(0, 0, 6, 8)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glClearColor(1, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        before = counters()
        gl.glFinish()
        after = counters()
        assert after['finish_calls'] == before['finish_calls'] + 1
        assert after['completion_waits'] > before['completion_waits']
        assert after['application_presents'] == before['application_presents']
        synchronization.append(dict(route='gl.glFinish', before=before, after=after))
        image = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        assert np.all(image[:, :6] == [255, 0, 0, 255])
        assert np.all(image[:, 6:] == [0, 0, 255, 255])
        assert canvas.context.get_viewport() == (0, 0, 12, 8)
        result['uniform_array_updates'] = uniform_array_update_checks(gloo, np, 12, 8)
        result['multidimensional_uniforms'] = multidimensional_uniform_checks(gloo, np)
        result.update(status='PASS', verified_members=origins, checked_pixels=96,
                      device=native.device_info(), synchronization=synchronization)
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        try:
            if canvas is not None:
                canvas.close()
            if native is not None:
                gc.collect()
                native.process_events()
                native.shutdown()
                probe = dict(native.probe())
                fields = ('pending_tickets', 'queued_frames', 'live_buffer_bytes',
                          'live_cpu_buffer_bytes', 'live_texture_bytes',
                          'canvas_texture_bytes', 'transient_buffer_bytes',
                          'line_resource_pool_busy_slots', 'line_resource_pool_bytes')
                result['shutdown_gauges'] = {key: probe[key] for key in fields}
                assert not any(result['shutdown_gauges'].values())
        except BaseException:
            result.update(status='FAIL', cleanup_error=traceback.format_exc())
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
