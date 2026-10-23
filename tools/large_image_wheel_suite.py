# SPDX-License-Identifier: AGPL-3.0-only
"""Full-frame installed-wheel large-image quality and camera residency checks.

Run upstream first, then candidate against the SHA-bound complete upstream
manifest. Readback is deliberate. This suite does not qualify frame timing.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT/'tools'))
try:
    from .fixture_large_image import CASES, STAGES, SIDE, PAN, render, case_contract, quality_result, residency_result, assert_framebuffer_draws
    from .color_volume_wheel_suite import SOURCES as COLOR_SOURCES, ORIGINAL_SHA, ZEROS, runtime_requirements, verify_package
    from .image_wheel_runner import installed_environment, run_logged, write, sha
    from .mesh_layout_process import process_stamp, worker_terminal, native_modules, assert_wheel_module_origins
except ImportError:
    from fixture_large_image import CASES, STAGES, SIDE, PAN, render, case_contract, quality_result, residency_result, assert_framebuffer_draws
    from color_volume_wheel_suite import SOURCES as COLOR_SOURCES, ORIGINAL_SHA, ZEROS, runtime_requirements, verify_package
    from image_wheel_runner import installed_environment, run_logged, write, sha
    from mesh_layout_process import process_stamp, worker_terminal, native_modules, assert_wheel_module_origins

CANDIDATE_SHA = '105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81'
SOURCES = COLOR_SOURCES + ('tools/large_image_wheel_suite.py', 'tools/fixture_large_image.py', 'tools/benchmark_work.py')


def sources():
    return {name: sha(ROOT/name) for name in SOURCES}


def assert_successful_parent(manifest, kind):
    assert kind in ('upstream', 'candidate')
    assert manifest['kind'] == kind
    assert manifest['status'] == 'PASS_ALL_' + kind.upper() + '_LARGE_IMAGES'
    assert not manifest.get('error')
    assert manifest['required_cases_without_verified_result'] == []
    assert manifest['cases'] == list(CASES)
    assert set(manifest['workers']) == set(CASES)
    for row in manifest['workers'].values():
        assert row['process_exit'] == 0 and row['child_waited'] is True
        assert row['actual_worker_terminal']['terminal'] is True
        assert row['worker_status'] == 'PASS_' + kind.upper() + '_LARGE_IMAGE'


def load_reference(directory, digest, name):
    assert name in CASES
    directory = Path(directory)
    assert sha(directory/'manifest.json') == digest
    manifest = json.loads((directory/'manifest.json').read_bytes())
    assert_successful_parent(manifest, 'upstream')
    assert manifest['sources_sha256'] == sources() and manifest['wheel_sha256'] == ORIGINAL_SHA
    worker_path = directory/name/'result.json'
    assert sha(worker_path) == manifest['workers'][name]['report_sha256']
    worker = json.loads(worker_path.read_bytes())
    assert worker['status'] == 'PASS_UPSTREAM_LARGE_IMAGE' and worker['case'] == name
    assert worker['process_exit'] == 0 and worker['kind'] == 'upstream'
    assert worker['sources_sha256'] == sources() and worker['wheel_sha256'] == ORIGINAL_SHA
    for leaf, digest in worker['artifacts'].items():
        assert Path(leaf).name == leaf and sha(directory/name/leaf) == digest
    assert set(worker['stages']) == set(STAGES)
    for stage in STAGES:
        assert worker['stages'][stage]['analytic']['passed'] is True
        assert stage+'.npz' in worker['artifacts'] and stage+'.json' in worker['artifacts']
    return directory/name


def assert_stage(name, stage, rgba, metadata, kind, reference):
    import numpy as np
    analytic = quality_result(name, stage, rgba)
    result = dict(analytic=analytic)
    dx, dy = PAN if stage == 'pan' else (0, 0)
    assert metadata['camera_rect'] == [dx, dy, SIDE, SIDE]
    assert metadata['source_texture_id'] != metadata['target_texture_id']
    result['glir_draws_on_owned_framebuffer'] = assert_framebuffer_draws(metadata['commands'], metadata['framebuffer_id'])
    if kind == 'candidate':
        with np.load(reference/(stage+'.npz'), allow_pickle=False) as saved:
            original = saved['rgba']
            assert original.shape == rgba.shape and original.dtype == rgba.dtype
            # All channels, all pixels, no masks and no image adjustment.
            result['exact_original'] = bool(np.array_equal(original, rgba))
        delta = metadata['counter_delta']
        if stage != 'baseline':
            result['residency'] = residency_result(delta)
        else:
            assert delta['texture_uploads'] > 0 and delta['texture_upload_bytes'] >= SIDE*SIDE*4
        assert result['exact_original'], 'Exact full-frame original comparison failed'
        if stage != 'baseline':
            assert result['residency']['passed'], result['residency']
    if stage != 'baseline':
        assert not any(row[0] == 'DATA' for row in metadata['commands']), 'Resident frame resubmitted GLIR data'
    assert analytic['passed'], analytic
    return result


def worker(args):
    import numpy as np
    from importlib import metadata as distributions
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert sha(args.wheel) == (ORIGINAL_SHA if args.kind == 'upstream' else CANDIDATE_SHA)
    args.output.mkdir(parents=True, exist_ok=False)
    held = sources()
    result = dict(status='FAILED_PRESERVED', process_exit=1, case=args.case, kind=args.kind,
                  pid=os.getpid(), process_stamp=process_stamp(), launch_id=args.launch_id,
                  sources_sha256=held, wheel_sha256=sha(args.wheel), stages={}, performance_qualified=False)
    dawn = qapp = package = installed = None
    try:
        import vispy
        from vispy import app, gloo
        package = Path(vispy.__file__).resolve().parent
        assert package.is_relative_to(Path(sys.prefix).resolve())
        assert not Path(sys.prefix).resolve().is_relative_to(ROOT)
        assert vispy.__version__ == distributions.version('vispy') == (
            '0.17.0' if args.kind == 'upstream' else '0.17.0+vulkan.1')
        installed = verify_package(args.wheel, package, args.kind)
        result['installed_wheel_payloads_sha256'] = installed
        result['dependencies'] = {n: distributions.version(n) for n in (
            'numpy', 'freetype-py', 'hsluv', 'kiwisolver', 'packaging', 'PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'PyOpenGL')}
        reference = None
        if args.kind == 'upstream':
            app.use_app('pyqt6')
            from PyQt6 import QtWidgets
            qapp = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            qapp.setQuitOnLastWindowClosed(False)
            control = app.Canvas(app='pyqt6', size=(2, 2), show=False)
            try:
                control.set_current(); gloo.clear(); gloo.finish()
                result['renderer'] = {k: str(gloo.gl.glGetParameter(getattr(gloo.gl, n))) for k, n in (
                    ('vendor', 'GL_VENDOR'), ('renderer', 'GL_RENDERER'), ('version', 'GL_VERSION'))}
                assert 'NVIDIA' in result['renderer']['vendor']
                assert 'GeForce RTX 4090' in result['renderer']['renderer']
                assert 'Dawn' not in result['renderer']['renderer'] and '610.88' in result['renderer']['version']
            finally:
                control.close()
        else:
            reference = load_reference(args.reference, args.reference_sha256, args.case)
            from vispy import _dawn
            dawn = _dawn

        def capture(stage, rgba, row):
            # Persist raw pixels and counters/GLIR before applying any gates.
            with (args.output/(stage+'.npz')).open('xb') as stream:
                np.savez_compressed(stream, rgba=rgba)
            write(args.output/(stage+'.json'), row)

        commands, shaders, parameters = render(args.case, 'pyqt6' if args.kind == 'upstream' else 'dawn_headless', capture)
        write(args.output/'commands.json', commands)
        write(args.output/'shaders.json', shaders)
        write(args.output/'parameters.json', parameters)
        assert commands and shaders
        assert parameters['source_texture_shape'] == ([SIDE, SIDE, 1] if args.case.startswith('scalar_') else [SIDE, SIDE, 4])
        for stage in STAGES:
            row = json.loads((args.output/(stage+'.json')).read_bytes())
            with np.load(args.output/(stage+'.npz'), allow_pickle=False) as saved:
                rgba = saved['rgba']
                result['stages'][stage] = assert_stage(args.case, stage, rgba, row, args.kind, reference)
        if dawn is not None:
            device = dict(dawn.device_info()); result['device'] = device
            assert device['ok'] and device['backend'] == 'Vulkan' and not device['software']
            assert device['vendor_id'] == 4318 and device['device_id'] == 9860
        result.update(status='PASS_'+args.kind.upper()+'_LARGE_IMAGE', process_exit=0,
                      compared_pixels=SIDE*SIDE*len(STAGES), excluded_pixels=0)
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        try:
            if qapp is not None:
                from PyQt6 import QtCore
                qapp.closeAllWindows(); qapp.processEvents()
                QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
                qapp.processEvents()
                result['visible_windows_after_close'] = sum(w.isVisible() for w in qapp.topLevelWidgets())
                assert result['visible_windows_after_close'] == 0
            if package is not None and installed is not None:
                records = native_modules((ROOT, args.repository))
                assert_wheel_module_origins(records, package, {n:h for n,h in installed.items() if n.startswith('vispy/')},
                                            [dawn.__file__] if dawn else [])
                if dawn is None:
                    assert not any('_dawn' in Path(r['path']).name.lower() or 'vispy_submit' in Path(r['path']).name.lower() for r in records)
                write(args.output/'native-modules.json', records)
                result['native_origins_verified'] = True
        except BaseException:
            result.update(status='FAILED_PRESERVED', process_exit=1, origin_cleanup_error=traceback.format_exc())
        finally:
            try:
                if dawn is not None:
                    dawn.shutdown()
                    counters = dict(dawn.probe())
                    result['shutdown_zeros'] = {key:counters[key] for key in ZEROS}
                    assert all(value == 0 for value in result['shutdown_zeros'].values())
                assert sources() == held
                assert sha(args.wheel) == result['wheel_sha256']
                if installed is not None:
                    assert verify_package(args.wheel, package, args.kind) == installed
                result['cleanup_passed'] = True
            except BaseException:
                result.update(status='FAILED_PRESERVED', process_exit=1, cleanup_error=traceback.format_exc())
        result['artifacts'] = {p.name:sha(p) for p in args.output.iterdir() if p.is_file()}
        write(args.output/'result.json', result)
    return result['process_exit']


def run(args):
    assert not args.output.exists()
    assert sha(args.wheel) == (ORIGINAL_SHA if args.kind == 'upstream' else CANDIDATE_SHA)
    if args.kind == 'candidate':
        for name in CASES:
            load_reference(args.reference, args.reference_sha256, name)
    held = sources()
    args.output.mkdir(parents=True)
    runtime = args.output/'runtime.txt'
    runtime.write_text(runtime_requirements(), encoding='utf-8')
    env = dict(os.environ)
    for key in list(env):
        if key.upper().startswith(('VISPY_IMAGE_', 'VISPY_TEST_')):
            env.pop(key)
    env['VISPY_TEST_PYTHON'] = sys.executable
    env['VISPY_TEST_RUNTIME_REQUIREMENTS'] = str(runtime.resolve())
    result = dict(kind=args.kind, cases=list(CASES), sources_sha256=held,
                  wheel_sha256=sha(args.wheel), pid=os.getpid(), process_stamp=process_stamp(),
                  status='FAILED_REQUIRED_LARGE_IMAGES', workers={}, performance_qualified=False)
    try:
        with installed_environment(args.wheel, args.output/'environment', environment=env) as (python, environment):
            for name in CASES:
                nonce = uuid.uuid4().hex
                command = [python, '-I', '-B', Path(__file__), '--worker', '--kind', args.kind,
                           '--case', name, '--launch-id', nonce, '--wheel', args.wheel,
                           '--repository', args.repository, '--output', args.output/name]
                if args.kind == 'candidate':
                    command += ['--reference', args.reference, '--reference-sha256', args.reference_sha256]
                observed = run_logged(command, cwd=Path(python).parent, environment=environment, log=args.output/(name+'.log'))
                try:
                    report = args.output/name/'result.json'
                    child = json.loads(report.read_bytes())
                    assert child['launch_id'] == nonce
                    observed.update(report_sha256=sha(report), actual_worker_terminal=worker_terminal(child, observed['pid']))
                    assert observed['actual_worker_terminal']['terminal']
                except BaseException:
                    write(args.output/'environment/worker-termination-unverified.json', dict(**observed, error=traceback.format_exc()))
                    raise
                observed['worker_status'] = child['status']
                result['workers'][name] = observed
                write(args.output/(name+'.process.json'), observed)
        assert set(result['workers']) == set(CASES) and sources() == held
        assert sha(args.wheel) == result['wheel_sha256']
        if all(row['process_exit'] == 0 and row['worker_status'] == 'PASS_'+args.kind.upper()+'_LARGE_IMAGE'
               for row in result['workers'].values()):
            result['status'] = 'PASS_ALL_'+args.kind.upper()+'_LARGE_IMAGES'
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        result['required_cases_without_verified_result'] = [name for name in CASES if name not in result['workers']]
        write(args.output/'manifest.json', result)
    return 0 if result['status'] == 'PASS_ALL_'+args.kind.upper()+'_LARGE_IMAGES' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--kind', choices=('upstream', 'candidate'), required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--reference-sha256')
    parser.add_argument('--launch-id')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.wheel = args.wheel.resolve(strict=True)
    args.repository = args.repository.resolve(strict=True)
    return worker(args) if args.worker else run(args)


if __name__ == '__main__':
    raise SystemExit(main())
