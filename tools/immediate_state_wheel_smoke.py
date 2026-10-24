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
            for name in (Path(native.__file__).name, 'gloo/gl/dawn.py'):
                path = package / name
                expected = hashlib.sha256(archive.read('vispy/' + name)).hexdigest()
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                assert actual == expected, 'loaded wheel member differs: ' + name
                origins[name] = actual
        assert Path(dawn.__file__).resolve() == package / 'gloo/gl/dawn.py'
        canvas = app.Canvas(app='dawn_headless', size=(12, 8))
        canvas.set_current()
        gl.glViewport(0, 0, 12, 8)
        gloo.clear(color='blue')
        gl.glScissor(0, 0, 6, 8)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glClearColor(1, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glFinish()
        image = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        assert np.all(image[:, :6] == [255, 0, 0, 255])
        assert np.all(image[:, 6:] == [0, 0, 255, 255])
        assert canvas.context.get_viewport() == (0, 0, 12, 8)
        result.update(status='PASS', verified_members=origins, checked_pixels=96,
                      device=native.device_info())
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
