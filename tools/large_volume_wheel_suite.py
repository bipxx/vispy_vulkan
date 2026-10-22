# SPDX-License-Identifier: AGPL-3.0-only
"""Actual large-volume benchmark workload quality and camera residency checks.

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
    from .fixture_large_volume import CASES, STAGES, render, case_contract, compare_frames, assert_nonblank, residency_result, assert_framebuffer_draws, assert_owned_clear, change_discrimination, UPDATE_ZERO
    from .color_volume_wheel_suite import SOURCES as COLOR_SOURCES, ORIGINAL_SHA, ZEROS, runtime_requirements, verify_package
    from .image_wheel_runner import installed_environment, run_logged, write, sha
    from .mesh_layout_process import process_stamp, worker_terminal, native_modules, assert_wheel_module_origins
except ImportError:
    from fixture_large_volume import CASES, STAGES, render, case_contract, compare_frames, assert_nonblank, residency_result, assert_framebuffer_draws, assert_owned_clear, change_discrimination, UPDATE_ZERO
    from color_volume_wheel_suite import SOURCES as COLOR_SOURCES, ORIGINAL_SHA, ZEROS, runtime_requirements, verify_package
    from image_wheel_runner import installed_environment, run_logged, write, sha
    from mesh_layout_process import process_stamp, worker_terminal, native_modules, assert_wheel_module_origins

CANDIDATE_SHA = '105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81'
VERSIONS = {'numpy':'2.4.6', 'freetype-py':'2.5.1', 'hsluv':'5.0.4', 'kiwisolver':'1.5.1',
            'packaging':'26.3', 'PyQt6':'6.11.0', 'PyQt6-Qt6':'6.11.2', 'PyQt6-sip':'13.13.0', 'PyOpenGL':'3.1.10'}
SOURCES = COLOR_SOURCES + ('tools/large_volume_wheel_suite.py', 'tools/fixture_large_volume.py',
    'tools/fixture_large_image.py', 'tools/benchmark_frames.py', 'tools/benchmark_work.py',
    'tools/benchmark_opengl.py', 'tools/benchmark_pacing.py')


def sources():
    return {name: sha(ROOT/name) for name in SOURCES}


def assert_successful_parent(manifest, kind):
    assert kind in ('upstream', 'candidate')
    assert manifest['kind'] == kind
    assert manifest['status'] == 'PASS_ALL_' + kind.upper() + '_LARGE_VOLUMES'
    assert not manifest.get('error')
    assert manifest['required_cases_without_verified_result'] == []
    assert manifest['cases'] == list(CASES)
    assert set(manifest['workers']) == set(CASES)
    for row in manifest['workers'].values():
        assert row['process_exit'] == 0 and row['child_waited'] is True
        assert row['actual_worker_terminal']['terminal'] is True
        assert row['worker_status'] == 'PASS_' + kind.upper() + '_LARGE_VOLUME'


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
    assert worker['status'] == 'PASS_UPSTREAM_LARGE_VOLUME' and worker['case'] == name
    assert worker['process_exit'] == 0 and worker['kind'] == 'upstream'
    assert worker['sources_sha256'] == sources() and worker['wheel_sha256'] == ORIGINAL_SHA
    assert {'parameters.json', 'commands.json', 'shaders.json', 'native-modules.json'}.issubset(worker['artifacts'])
    for leaf, digest in worker['artifacts'].items():
        assert Path(leaf).name == leaf and sha(directory/name/leaf) == digest
    assert set(worker['stages']) == set(STAGES)
    for stage in STAGES:
        assert worker['stages'][stage]['nonblank'] is True
        assert stage+'.npz' in worker['artifacts'] and stage+'.json' in worker['artifacts']
    return directory/name


def assert_stage(name, stage, rgba, metadata, kind, reference, *, legacy_geometry=None):
    import math
    import numpy as np
    spec = case_contract(name)
    assert_nonblank(name, rgba)
    result = dict(nonblank=True)
    result['glir_draws_on_owned_framebuffer'] = assert_framebuffer_draws(metadata['commands'], metadata['framebuffer_id'])
    assert_owned_clear(metadata['commands'], metadata['framebuffer_id'])
    assert metadata['source_texture_id'] != metadata['target_texture_id']
    frame = spec['probe_frames'][STAGES.index(stage)]
    resident = spec['workload']['update'] == 'resident'
    expected_bytes = int(np.prod(spec['workload']['shape']))*4
    expected_azimuth = 30 + (8*math.sin(frame*2*math.pi/180) if resident and frame is not None else 0)
    assert metadata['probe_frame'] == frame
    assert metadata['requested_update_bytes'] == (expected_bytes if not resident and frame is not None else 0)
    state = metadata['camera_state']
    assert abs(state['azimuth']-expected_azimuth) <= 1e-12
    assert state['elevation'] == 20 and state['fov'] == 45
    assert state['distance'] == spec['camera']['distance']
    uploads = [row for row in metadata['commands'] if row[0] == 'DATA' and row[1] == metadata['source_texture_id']]
    needs_upload = stage == 'initial' or (not resident and frame is not None)
    assert len(uploads) == (1 if needs_upload else 0)
    if uploads:
        payload = uploads[0][3]['array']
        assert payload['bytes'] == expected_bytes
        assert payload['dtype'] == '<f4' and payload['shape'] == list(spec['workload']['shape']) + [1]
        result['source_upload_sha256'] = payload['sha256']
    if kind == 'candidate':
        original_metadata = json.loads((reference/(stage+'.json')).read_bytes())
        assert metadata['camera_state'] == original_metadata['camera_state']
        if uploads:
            original_uploads = [row for row in original_metadata['commands']
                                if row[0] == 'DATA' and row[1] == original_metadata['source_texture_id']]
            assert len(original_uploads) == 1 and uploads[0][3] == original_uploads[0][3]
        with np.load(reference/(stage+'.npz'), allow_pickle=False) as saved:
            original = saved['rgba']
            result['comparison'] = compare_frames(original, rgba)
        assert result['comparison']['status'] == 'passed', result['comparison']
        delta = metadata['counter_delta']
        for snapshot in (metadata['counter_before'], metadata['counter_after']):
            assert snapshot['vk_memory_available'] is True and snapshot['vk_memory_complete'] is True
            assert type(snapshot['vk_memory_active_devices']) is int and snapshot['vk_memory_active_devices'] > 0
            assert snapshot['vk_memory_tracking_devices'] == snapshot['vk_memory_active_devices']
        assert metadata['counter_before']['device_generation'] == metadata['counter_after']['device_generation']
        assert type(delta['draw_calls']) is int and delta['draw_calls'] > 0
        assert type(delta['vk_queue_submits']) is int and delta['vk_queue_submits'] > 0
        if needs_upload:
            assert delta['texture_uploads'] > 0 and delta['texture_upload_bytes'] >= expected_bytes
            if stage != 'initial':
                assert delta['texture_uploads'] == 1 and delta['texture_upload_bytes'] == expected_bytes
                for key in UPDATE_ZERO:
                    assert type(delta.get(key)) is int and delta[key] == 0, key
        else:
            result['residency'] = residency_result(delta)
            assert result['residency']['passed'], result['residency']
        if stage != 'initial':
            # These are live gauges, not monotonically increasing event counts.
            # Retiring warmup allocations may decrease them. Require no growth
            # AND exact event conservation, rejecting resets or missing data.
            for live, allocated, freed in (
                ('vk_memory_live_allocations','vk_memory_allocation_count','vk_memory_free_count'),
                ('vk_memory_live_bytes','vk_memory_allocated_bytes','vk_memory_freed_bytes')):
                assert type(delta.get(live)) is int and delta[live] <= 0, live
                assert type(delta.get(allocated)) is int and delta[allocated] >= 0, allocated
                assert type(delta.get(freed)) is int and delta[freed] >= 0, freed
                assert delta[live] == delta[allocated]-delta[freed], live
    if stage != 'initial':
        assert not any(row[0] in ('CREATE', 'DELETE') for row in metadata['commands'])
        sizes = [row for row in metadata['commands'] if row[0] == 'SIZE']
        for row in sizes:
            if kind == 'upstream' and legacy_geometry is not None and row[1] in legacy_geometry:
                assert row[2:] == legacy_geometry[row[1]]['size']
                continue
            assert needs_upload, 'Resident stage must not resize or reallocate'
            assert row[1] == metadata['source_texture_id']
            assert row[2] == list(spec['workload']['shape']) + [1] and row[4] == 'r32f'
        for row in metadata['commands']:
            if row[0] != 'DATA':continue
            if row[1] == metadata['source_texture_id']:
                assert needs_upload
            else:
                assert kind == 'upstream' and legacy_geometry is not None and row[1] in legacy_geometry
                assert row[2:] == legacy_geometry[row[1]]['data'], 'Original repeated geometry changed'
    return result


def worker(args):
    import numpy as np
    from importlib import metadata as distributions
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert sys.platform == 'win32' and sys.implementation.name == 'cpython' and sys.version_info[:3] == (3,12,8)
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
        assert result['dependencies'] == VERSIONS
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
            app.use_app('pyqt6')
            from PyQt6 import QtWidgets
            qapp = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            qapp.setQuitOnLastWindowClosed(False)

        def capture(stage, rgba, row):
            # Persist raw pixels and counters/GLIR before applying any gates.
            with (args.output/(stage+'.npz')).open('xb') as stream:
                np.savez_compressed(stream, rgba=rgba)
            write(args.output/(stage+'.json'), row)

        commands, shaders, parameters = render(args.case, args.kind, capture)
        write(args.output/'commands.json', commands)
        write(args.output/'shaders.json', shaders)
        write(args.output/'parameters.json', parameters)
        assert commands and shaders
        assert parameters['source_texture_shape'] == list(parameters['workload']['shape']) + [1]
        controls = parameters['actual_volume_controls']; workload = parameters['workload']
        for key in ('method', 'interpolation', 'threshold', 'gamma', 'relative_step_size'):
            assert controls[key] == workload[key], key
        assert controls['clim'] == list(workload['clim']) and controls['texture_format'] == 'r32f'
        expected_map = np.tile(np.array([0,.25,.5,.75,1],np.float32)[:,None], (1,4))
        if workload['colormap'] != 'density-alpha':expected_map[:,3] = 1
        np.testing.assert_allclose(controls['colormap_samples'], expected_map, rtol=0, atol=1e-7)
        identities = set()
        initial_size = None
        legacy_geometry = {}
        geometry_ids = None
        if reference is not None:
            prior = json.loads((reference/'parameters.json').read_bytes())
            for key in case_contract(args.case):
                assert json.loads(json.dumps(parameters[key])) == prior[key], key
            assert parameters['data_sha256'] == prior['data_sha256']
        for stage in STAGES:
            row = json.loads((args.output/(stage+'.json')).read_bytes())
            identities.add(tuple(row[key] for key in ('source_texture_id', 'target_texture_id', 'framebuffer_id')))
            sizes = [cmd for cmd in row['commands'] if cmd[0] == 'SIZE' and cmd[1] == row['source_texture_id']]
            if stage == 'initial':
                assert sizes
                initial_size = sizes[-1][2:]
                geometry_ids = row['geometry_ids']
                assert len(geometry_ids) == len(set(geometry_ids)) == 2
                for identifier, object_type in zip(geometry_ids, ('VertexBuffer','IndexBuffer')):
                    assert ['CREATE',identifier,object_type] in row['commands']
                    created_sizes = [cmd for cmd in row['commands'] if cmd[0] == 'SIZE' and cmd[1] == identifier]
                    created_data = [cmd for cmd in row['commands'] if cmd[0] == 'DATA' and cmd[1] == identifier]
                    assert len(created_sizes) == len(created_data) == 1
                    legacy_geometry[identifier] = dict(size=created_sizes[0][2:],data=created_data[0][2:])
            else:
                assert all(cmd[2:] == initial_size for cmd in sizes)
                assert row['geometry_ids'] == geometry_ids
            with np.load(args.output/(stage+'.npz'), allow_pickle=False) as saved:
                rgba = saved['rgba']
                result['stages'][stage] = assert_stage(args.case, stage, rgba, row, args.kind, reference,
                    legacy_geometry=legacy_geometry if args.kind == 'upstream' else None)
        assert len(identities) == 1
        assert result['stages']['initial']['source_upload_sha256'] == parameters['data_sha256']
        with np.load(args.output/'initial.npz', allow_pickle=False) as initial, np.load(args.output/'repeat.npz', allow_pickle=False) as repeat:
            assert np.array_equal(initial['rgba'], repeat['rgba']), 'Unchanged repeat must equal initial exactly'
        if reference is not None:
            assert parameters['actual_volume_controls'] == prior['actual_volume_controls']
            with np.load(reference/'initial.npz', allow_pickle=False) as original, np.load(args.output/'initial.npz', allow_pickle=False) as candidate:
                for stage in ('probe7', 'probe73'):
                    with np.load(reference/(stage+'.npz'), allow_pickle=False) as original_probe, np.load(args.output/(stage+'.npz'), allow_pickle=False) as candidate_probe:
                        check = change_discrimination(original['rgba'], original_probe['rgba'], candidate['rgba'], candidate_probe['rgba'])
                        result['stages'][stage]['change_discrimination'] = check
                        assert check['passed'], check
        if dawn is not None:
            device = dict(dawn.device_info()); result['device'] = device
            assert device['ok'] and device['backend'] == 'Vulkan' and not device['software']
            assert device['vendor_id'] == 4318 and device['device_id'] == 9860
            assert device['device'] == 'NVIDIA GeForce RTX 4090' and '610.88' in device['driver']
        result.update(status='PASS_'+args.kind.upper()+'_LARGE_VOLUME', process_exit=0,
                      compared_pixels=parameters['workload']['viewport'][0]*parameters['workload']['viewport'][1]*len(STAGES), excluded_pixels=0)
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
                  status='FAILED_REQUIRED_LARGE_VOLUMES', workers={}, performance_qualified=False)
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
        if all(row['process_exit'] == 0 and row['worker_status'] == 'PASS_'+args.kind.upper()+'_LARGE_VOLUME'
               for row in result['workers'].values()):
            result['status'] = 'PASS_ALL_'+args.kind.upper()+'_LARGE_VOLUMES'
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        result['required_cases_without_verified_result'] = [name for name in CASES if name not in result['workers']]
        write(args.output/'manifest.json', result)
    return 0 if result['status'] == 'PASS_ALL_'+args.kind.upper()+'_LARGE_VOLUMES' else 1


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
    if args.reference is not None:
        args.reference = args.reference.resolve(strict=True)
    return worker(args) if args.worker else run(args)


if __name__ == '__main__':
    raise SystemExit(main())
