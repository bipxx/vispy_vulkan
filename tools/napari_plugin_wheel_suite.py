# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh original and installed candidate napari-threedee overlay workflows."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from importlib import metadata
import os
from pathlib import Path
import re
import sys
import traceback
import uuid
import zipfile
ROOT=Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0,str(ROOT/'tools'))
    import glue_wheel_suite as base
    import oracle_napari_threedee_overlay_capture as capture
    from fixture_napari_threedee_overlay import CASES,SIZE,assert_landmarks,render
    from image_wheel_runner import installed_environment,run_logged,sha,write
    from mesh_layout_process import process_stamp,worker_terminal,native_modules,assert_wheel_module_origins,normalized_path
    from smooth_line_parity import smooth_line_difference
else:
    from . import glue_wheel_suite as base
    from . import oracle_napari_threedee_overlay_capture as capture
    from .fixture_napari_threedee_overlay import CASES,SIZE,assert_landmarks,render
    from .image_wheel_runner import installed_environment,run_logged,sha,write
    from .mesh_layout_process import process_stamp,worker_terminal,native_modules,assert_wheel_module_origins,normalized_path
    from .smooth_line_parity import smooth_line_difference
ZERO_FIELDS=base.ZERO_FIELDS
WORK_FIELDS=base.WORK_FIELDS
package_hashes=base.package_hashes
assert_locked_upstream=base.assert_locked_upstream
UPSTREAM_WHEEL_SHA256=base.UPSTREAM_WHEEL_SHA256
INPUTS=ROOT/'tests/reference/napari-plugin-wheel-inputs'
INPUTS_SHA256='da2dfaa21a2882f7bb04f98975f6e5c19ee40cdcad573232f3a03ea9c0452a36'
PLUGIN_WHEEL=INPUTS/'napari_threedee-0.0.29-py3-none-any.whl'
ASCIITREE_WHEEL=INPUTS/'asciitree-0.3.3-py3-none-any.whl'
ASCIITREE_SHA256='d3c865c2cea5e56b52c090526c3ea87287356eaa7f8f4d78d4a872ca1c4cef10'
ASCIITREE_SOURCE_SHA256='4aa4b9b649f85e3fcb343363d97564aa1fb62e249677f2e18a96765145cc0f6e'
ASCIITREE_BLOCK=base.VISPY_BLOCK.replace('vispy==0\\.17\\.0','asciitree==0\\.3\\.3')
RUNTIME='compat/host-environments/napari-threedee-upstream-numpy246-windows-cpython312-pyqt6.txt'
LEGACY='tests/reference/napari-threedee-overlay-opengl'
LEGACY_SHA256='b4a118f6320af8f8d12010948ff00964fe5966f967003ab40cb887af37ddc77e'
SOURCES=tuple(dict.fromkeys((*base.SOURCES,'tools/napari_plugin_wheel_suite.py','tools/smooth_line_parity.py',
    'tools/fixture_napari_threedee_overlay.py','tools/oracle_napari_threedee_overlay_capture.py',RUNTIME,
    PLUGIN_WHEEL.relative_to(ROOT).as_posix(),ASCIITREE_WHEEL.relative_to(ROOT).as_posix(),
    *((INPUTS/name).relative_to(ROOT).as_posix() for name in ('manifest.json','asciitree-build.json',
       'asciitree-0.3.3.tar.gz','asciitree-build-source.txt','napari-threedee-LICENSE.txt','asciitree-LICENSE.txt')),
    *(str(Path('compat/host-environments')/name).replace('\\','/') for name in capture.PROOFS))))


def sources():
    assert sha(INPUTS/'manifest.json')==INPUTS_SHA256
    inputs=json.loads((INPUTS/'manifest.json').read_bytes())
    assert inputs['schema']==1 and not inputs['rendering_qualified'] and not inputs['release_qualified']
    for name,digest in inputs['files'].items():
        assert Path(name).name==name and sha(INPUTS/name)==digest
    return {name:sha(ROOT/name) for name in SOURCES}


def runtime_requirements():
    original=(ROOT/RUNTIME).read_text(encoding='utf-8')
    blocks=re.findall(base.VISPY_BLOCK,original)
    assert len(blocks)==1
    dependency=re.findall(ASCIITREE_BLOCK,original)
    assert len(dependency)==1 and ASCIITREE_SOURCE_SHA256 in dependency[0]
    assert sha(PLUGIN_WHEEL)==capture.WHEEL_SHA
    assert sha(ASCIITREE_WHEEL)==ASCIITREE_SHA256
    return (original.replace(blocks[0],'',1).replace(dependency[0],'',1)
        +f'\nnapari-threedee @ {PLUGIN_WHEEL.as_uri()} --hash=sha256:{capture.WHEEL_SHA}\n'
        +f'asciitree @ {ASCIITREE_WHEEL.as_uri()} --hash=sha256:{ASCIITREE_SHA256}\n')


def plugin_info():
    # Preserve the original checker and its globals while selecting the exact
    # same wheel from the portable input bundle in this single-purpose worker.
    previous=capture.WHEEL
    try:
        capture.WHEEL=PLUGIN_WHEEL
        record=capture.plugin_provenance()
    finally:
        capture.WHEEL=previous
    versions={name:metadata.version(name) for name in ('napari','napari-threedee','numpy','PyQt6')}
    assert versions=={'napari':'0.9.2','napari-threedee':'0.0.29','numpy':'2.4.6','PyQt6':'6.11.0'}
    assert metadata.version('asciitree')=='0.3.3'
    assert Path(record['plugin_origin']).is_relative_to(Path(sys.prefix).resolve())
    assert Path(record['napari_origin']).is_relative_to(Path(sys.prefix).resolve())
    return record,versions


def interpreter_policy():
    assert not sys.flags.isolated and sys.flags.no_user_site and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert sys.flags.hash_randomization==0 and os.environ.get('PYTHONHASHSEED')=='0'
    assert 'PYTHONPATH' not in os.environ and 'PYTHONHOME' not in os.environ
    assert os.environ.get('VISPY_PYQT5_SHARE_CONTEXT')=='true'
    return dict(hash_randomization=int(sys.flags.hash_randomization),hash_seed='0',
        no_user_site=True,dont_write_bytecode=True,context_sharing='true',mode='clean-environment-no-user-site')


def read_extras(directory,name):
    import numpy as np
    expected={'before'} if name in ('selection','translation','miss') else set()
    actual={p.stem.removeprefix('extra-') for p in Path(directory).glob('extra-*.npy')}
    assert actual==expected
    return {key:np.load(Path(directory)/('extra-'+key+'.npy'),allow_pickle=False) for key in expected}


def compare(name,image,original,params,expected,extras,original_extras):
    import numpy as np
    assert name in CASES and image.shape==original.shape==(SIZE[1],SIZE[0],4)
    assert image.dtype==original.dtype==np.uint8
    actual,reference=dict(params),dict(expected)
    assert 'QOpenGLWidget' in reference.pop('native_mro')
    assert 'QOpenGLWidget' not in actual.pop('native_mro')
    assert actual==reference, 'Original plugin inputs, Qt events or callback state differ'
    # Smooth-line coverage is driver-defined: interiors exact, antialiased edges bounded.
    reason=smooth_line_difference(image,original)
    assert reason is None, ('Plugin frame differs beyond smooth-line edges',reason)
    assert set(extras)==set(original_extras)
    for key in extras:
        reason=smooth_line_difference(extras[key],original_extras[key])
        assert reason is None, ('Auxiliary frame differs beyond smooth-line edges',key,reason)
    assert_landmarks(name,image,params,extras)


def legacy_reference(name):
    import numpy as np
    directory=ROOT/LEGACY
    assert sha(directory/'manifest.json')==LEGACY_SHA256
    manifest=json.loads((directory/'manifest.json').read_bytes())
    assert not manifest['errors'] and set(manifest['fixtures'])==set(CASES)
    record=manifest['fixtures'][name]
    bodies={}
    for role,artifact in record['artifacts'].items():
        assert Path(artifact['file']).name==artifact['file']
        body=(directory/artifact['file']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==artifact['sha256']
        bodies[role]=body
    image=np.load(io.BytesIO(bodies['rgba']),allow_pickle=False)
    params=json.loads(bodies['parameters'])
    assert params==record['parameters']
    extras={'before':np.load(io.BytesIO(bodies['before']),allow_pickle=False)} if 'before' in bodies else {}
    assert_landmarks(name,image,params,extras)
    return image,params,extras


def registration_control(args):
    result=dict(status='FAILED_PLUGIN_REGISTRATION_CONTROL',process_exit=1,pid=os.getpid(),
        process_stamp=process_stamp(),launch_id=args.launch_id,graphics_invoked=False)
    try:
        result['interpreter_policy']=interpreter_policy()
        from qtpy import QtWidgets,QtGui
        assert QtWidgets.QApplication.instance() is None and QtGui.QOpenGLContext.currentContext() is None
        plugin,versions=plugin_info()
        assert QtWidgets.QApplication.instance() is None and QtGui.QOpenGLContext.currentContext() is None
        assert not any(n=='_dawn' or n.endswith('._dawn') for n in sys.modules)
        result.update(status='PASS_REAL_PLUGIN_REGISTRATION',process_exit=0,plugin=plugin,versions=versions,
            qapplication_created=False,dawn_imported=False)
    except BaseException:result['error']=traceback.format_exc()
    write(args.output,result)
    return result['process_exit']


def load_reference(directory, digest, name):
    directory = Path(directory)
    assert sha(directory / 'manifest.json') == digest, 'Fresh reference manifest differs'
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    assert manifest.get('status') == 'PASS_ALL_FIVE_UPSTREAM_PLUGIN' and manifest.get('kind') == 'upstream'
    assert manifest['cases'] == list(CASES) and manifest['sources_sha256'] == sources()
    assert set(manifest['workers']) == set(CASES)
    assert manifest['wheel_sha256'] == UPSTREAM_WHEEL_SHA256
    record = manifest['workers'][name]
    report_path = directory / name / 'result.json'
    assert sha(report_path) == record['report_sha256']
    worker = json.loads(report_path.read_bytes())
    assert worker == record['worker'] and worker['status'] == 'PASS_UPSTREAM_PLUGIN_CASE'
    assert worker['case'] == name and worker['process_exit'] == record['process_exit'] == 0
    assert worker['launch_id'] == record['launch_id']
    assert record['actual_worker_terminal']['terminal'] and record['child_waited']
    assert worker['cleanup_passed'] and worker['native_origins_verified']
    bodies = {}
    for leaf, checksum in worker['artifacts'].items():
        assert Path(leaf).name == leaf
        body = (directory / name / leaf).read_bytes()
        assert hashlib.sha256(body).hexdigest() == checksum
        bodies[leaf] = body
    import numpy as np
    image = np.load(io.BytesIO(bodies['rgba.npy']), allow_pickle=False)
    params = json.loads(bodies['parameters.json'])
    extras=read_extras(directory/name,name)
    assert_landmarks(name,image,params,extras)
    assert params == worker['parameters'] and 'QOpenGLWidget' in params['native_mro']
    image.setflags(write=False)
    return image, params, extras

def worker(args):
    policy=interpreter_policy()
    assert args.case in CASES and len(args.launch_id) == 32 and all(c in '0123456789abcdef' for c in args.launch_id)
    args.output.mkdir(parents=True, exist_ok=False)
    held = sources()
    wheel_digest = sha(args.wheel)
    result = dict(schema=1, status='FAILED_PRESERVED', process_exit=1, case=args.case, kind=args.kind,
        pid=os.getpid(), launch_id=args.launch_id, process_stamp=process_stamp(), sources_sha256=held,
        wheel_sha256=wheel_digest, cleanup_passed=False, native_origins_verified=False, render_attempted=False,
        interpreter_policy=policy)
    dawn = None
    package = None
    installed = None
    try:
        prefix = Path(sys.prefix).resolve()
        assert not prefix.is_relative_to(ROOT) and not prefix.is_relative_to(args.repository.resolve())
        import vispy
        package = Path(vispy.__file__).resolve().parent
        assert package.is_relative_to(prefix)
        installed = package_hashes(args.wheel, package, args.kind)
        direct = metadata.distribution('vispy').read_text('direct_url.json')
        if direct:
            assert not json.loads(direct).get('dir_info', {}).get('editable', False)
        os.environ['QT_API'] = 'pyqt6'
        os.environ['QT_SCALE_FACTOR'] = '1'
        assert os.environ.get('QT_QPA_PLATFORM') != 'offscreen'
        vispy.use(app='pyqt6', **({'gl': 'gl+'} if args.kind == 'upstream' else {}))
        plugin,versions=plugin_info()
        from qtpy import QtWidgets,API_NAME,QT_VERSION
        assert API_NAME=='PyQt6'
        qapp=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        qapp.setQuitOnLastWindowClosed(False)
        result.update(prefix=str(prefix),package=str(package),installed_package_sha256=installed,
            plugin=plugin,host_versions=versions,qt_version=QT_VERSION,qt_platform=qapp.platformName(),python=sys.version)
        if args.kind == 'upstream':
            from vispy import app, gloo
            probe = app.Canvas(app='pyqt6', size=(2, 2), show=False)
            try:
                probe.set_current()
                gloo.clear(color=True, depth=False, stencil=False)
                gloo.finish()
                renderer = {key: str(gloo.gl.glGetParameter(getattr(gloo.gl, enum))) for key, enum in
                    (('vendor', 'GL_VENDOR'), ('renderer', 'GL_RENDERER'), ('version', 'GL_VERSION'))}
                assert 'NVIDIA' in renderer['vendor'] and 'RTX 4090' in renderer['renderer'], renderer
                result['renderer'] = renderer
                result['renderer_probe_separate_canvas'] = True
            finally:
                probe.close()
        else:
            from vispy import _dawn
            dawn = _dawn
            result['native_module'] = str(Path(dawn.__file__).resolve())
            before = dict(dawn.probe())
            original, expected, original_extras = load_reference(args.reference, args.reference_sha256, args.case)
            result['reference_manifest_sha256'] = args.reference_sha256
        result['render_attempted'] = True
        image, commands, shaders, params, extras = render(args.case)
        import numpy as np
        np.save(args.output / 'rgba.npy', image, allow_pickle=False)
        write(args.output / 'commands.json', commands)
        write(args.output / 'shaders.json', shaders)
        write(args.output / 'parameters.json', params)
        for key,value in extras.items():
            assert key=='before'
            np.save(args.output/('extra-'+key+'.npy'),value,allow_pickle=False)
        assert commands and shaders
        assert_landmarks(args.case,image,params,extras)
        if args.kind == 'upstream':
            old_image,old_params,old_extras=legacy_reference(args.case)
            assert np.array_equal(image,old_image), 'Fresh upstream differs from retained original frame'
            assert params==old_params, 'Fresh upstream fixture state differs from retained original'
            assert set(extras)==set(old_extras)
            for key in extras:assert np.array_equal(extras[key],old_extras[key])
            result['retained_reference_manifest_sha256']=LEGACY_SHA256
            assert 'QOpenGLWidget' in params['native_mro']
        else:
            compare(args.case,image,original,params,expected,extras,original_extras)
            after = dict(dawn.probe())
            result['native_work_delta'] = {key: after[key] - before[key] for key in WORK_FIELDS}
            assert all(value > 0 for value in result['native_work_delta'].values())
            device = dict(dawn.device_info())
            assert device['ok'] and device['backend'] == 'Vulkan' and not device['software']
            assert device['vendor_id'] == 4318 and device['device_id'] == 9860
            result['device'] = device
        result.update(status='PASS_UPSTREAM_PLUGIN_CASE' if args.kind == 'upstream' else 'PASS_CANDIDATE_PLUGIN_CASE',
            process_exit=0, parameters=params, compared_pixels=SIZE[0] * SIZE[1], excluded_pixels=0)
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        try:
            try:
                if result['render_attempted']:
                    from qtpy import QtCore
                    qapp.closeAllWindows()
                    qapp.processEvents()
                    QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
                    qapp.processEvents()
                    result['visible_windows_after_close'] = sum(widget.isVisible() for widget in qapp.topLevelWidgets())
                    assert result['visible_windows_after_close'] == 0
                if package is not None and installed is not None:
                    records = native_modules((ROOT, args.repository))
                    write(args.output / 'native-modules.json', records)
                    required = [result['native_module']] if dawn is not None else []
                    assert_wheel_module_origins(records, package, installed, required)
                    if args.kind == 'upstream':
                        assert all('_dawn' not in Path(row['path']).name.lower() and 'vispy_submit' not in Path(row['path']).name.lower() for row in records)
                    result['native_origins_verified'] = True
            finally:
                if dawn is not None:
                    try:
                        if result['render_attempted'] and 'device' not in result:
                            result['device'] = dict(dawn.device_info())
                    finally:
                        dawn.shutdown()
                    counters = dict(dawn.probe())
                    result['shutdown_zeros'] = {key: counters[key] for key in ZERO_FIELDS}
                    assert all(value == 0 for value in result['shutdown_zeros'].values())
            assert sha(args.wheel) == wheel_digest and sources() == held
            if package is not None and installed is not None:
                assert package_hashes(args.wheel, package, args.kind) == installed
            if args.kind == 'candidate':
                assert sha(args.reference / 'manifest.json') == args.reference_sha256
            result['cleanup_passed'] = True
        except BaseException:
            result.update(status='FAILED_PRESERVED', process_exit=1, cleanup_error=traceback.format_exc())
        result['artifacts'] = {path.name: sha(path) for path in args.output.iterdir() if path.is_file()}
        write(args.output / 'result.json', result)
    return result['process_exit']

def run(args):
    assert not args.output.exists()
    if args.kind == 'upstream':
        assert_locked_upstream(args.wheel)
    if args.kind == 'candidate':
        assert args.reference and args.reference_sha256
        for name in CASES:
            load_reference(args.reference, args.reference_sha256, name)
    held, wheel_digest = sources(), sha(args.wheel)
    args.output.mkdir(parents=True)
    runtime = args.output / 'runtime-requirements.txt'
    runtime.write_text(runtime_requirements(), encoding='utf-8', newline='\n')
    env = dict(os.environ,PYTHONHASHSEED='0',QT_API='pyqt6',QT_SCALE_FACTOR='1')
    # Reuse the tested owned-environment lifecycle; all worker choices are argv.
    for name in list(env):
        if name.upper().startswith('VISPY_IMAGE_'):
            env.pop(name)
    env['VISPY_IMAGE_REPOSITORY'] = str(args.repository)
    env['VISPY_TEST_RUNTIME_REQUIREMENTS'] = str(runtime.resolve())
    result = dict(schema=1, kind=args.kind, cases=list(CASES), sources_sha256=held,
        wheel_sha256=wheel_digest, workers={},
        status='FAILED_BLOCKS_CANDIDATE' if args.kind == 'upstream' else 'FAILED_REQUIRED_PLUGIN_CASES',
        original_release_complete=False)
    try:
        with installed_environment(args.wheel, args.output / 'environment', environment=env) as (python, environment):
            launch = uuid.uuid4().hex
            command = [python, '-s', '-B', Path(__file__), '--registration-control', '--kind', args.kind,
                '--launch-id', launch, '--wheel', args.wheel, '--repository', args.repository,
                '--output', args.output / 'registration-control.json']
            control = run_logged(command, cwd=Path(python).parent, environment=environment,
                log=args.output / 'registration-control.stdout.log')
            try:
                cpu = json.loads((args.output / 'registration-control.json').read_bytes())
                assert cpu['launch_id'] == launch
                control.update(worker=cpu, launch_id=launch, actual_worker_terminal=worker_terminal(cpu, control['pid']))
                assert control['actual_worker_terminal']['terminal']
            except BaseException:
                write(args.output / 'environment/worker-termination-unverified.json', dict(error=traceback.format_exc()))
                raise
            result['registration_control'] = control
            assert control['process_exit'] == cpu['process_exit'] == 0
            assert cpu['status'] == 'PASS_REAL_PLUGIN_REGISTRATION'
            for name in CASES:
                launch = uuid.uuid4().hex
                command = [python, '-s', '-B', Path(__file__), '--worker', '--kind', args.kind,
                    '--case', name, '--launch-id', launch, '--wheel', args.wheel, '--repository', args.repository,
                    '--output', args.output / name]
                if args.kind == 'candidate':
                    command += ['--reference', args.reference, '--reference-sha256', args.reference_sha256]
                observed = run_logged(command, cwd=Path(python).parent, environment=environment, log=args.output / (name + '.stdout.log'))
                report = args.output / name / 'result.json'
                try:
                    worker_report = json.loads(report.read_bytes())
                    assert worker_report['launch_id'] == launch
                    observed.update(worker=worker_report, report_sha256=sha(report), launch_id=launch,
                        actual_worker_terminal=worker_terminal(worker_report, observed['pid']))
                    assert observed['actual_worker_terminal']['terminal']
                except BaseException:
                    write(args.output / 'environment/worker-termination-unverified.json', dict(error=traceback.format_exc()))
                    raise
                result['workers'][name] = observed
                write(args.output / (name + '.process.json'), observed)
        assert sources() == held and sha(args.wheel) == wheel_digest
        assert set(result['workers']) == set(CASES)
        if all(row['process_exit'] == row['worker']['process_exit'] == 0 for row in result['workers'].values()):
            result['status'] = 'PASS_ALL_FIVE_UPSTREAM_PLUGIN' if args.kind == 'upstream' else 'PASS_ALL_FIVE_CANDIDATE_PLUGIN'
    except BaseException:
        result['error'] = traceback.format_exc()
    result['artifacts'] = {path.relative_to(args.output).as_posix(): sha(path) for path in args.output.rglob('*') if path.is_file()}
    write(args.output / 'manifest.json', result)
    print(json.dumps(dict(status=result['status'], manifest_sha256=sha(args.output / 'manifest.json'))))
    return int(not result['status'].startswith('PASS_ALL_FIVE_'))

def verify_saved(directory, digest, wheel, kind, *, reference=None, reference_sha256=None):
    """Read completed evidence only; do not import a provider or recreate an env."""
    import numpy as np
    directory = Path(directory).resolve()
    assert sha(directory / 'manifest.json') == digest
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    expected_status = 'PASS_ALL_FIVE_UPSTREAM_PLUGIN' if kind == 'upstream' else 'PASS_ALL_FIVE_CANDIDATE_PLUGIN'
    allowed = {expected_status} if kind == 'upstream' else {expected_status, 'FAILED_REQUIRED_PLUGIN_CASES'}
    assert manifest['status'] in allowed and manifest['kind'] == kind
    assert manifest['cases'] == list(CASES) and set(manifest['workers']) == set(CASES)
    assert manifest['sources_sha256'] == sources() and manifest['wheel_sha256'] == sha(wheel)
    actual = {path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()}
    assert actual == set(manifest['artifacts']) | {'manifest.json'}
    for name, checksum in manifest['artifacts'].items():
        path = (directory / name).resolve()
        assert path.is_relative_to(directory)
        assert sha(path) == checksum, name
    setup = json.loads((directory / 'environment/setup.json').read_bytes())
    cleanup = json.loads((directory / 'environment/environment-teardown.json').read_bytes())
    assert setup['status'] == 'READY_FOR_REQUIRED_SCENES' and setup['owned_environment']
    assert setup['wheel_sha256'] == manifest['wheel_sha256']
    assert all(row['process_exit'] == 0 and row['child_waited'] for row in setup['stages'])
    assert cleanup['status'] == 'PASS_OWNED_ENVIRONMENT_TEARDOWN'
    assert cleanup['owned_root_removed'] and cleanup['wheel_preserved'] and cleanup['all_setup_children_waited']
    assert cleanup['owned_root'] == setup['owned_root'] and not Path(cleanup['owned_root']).exists()
    control = manifest['registration_control']
    cpu = json.loads((directory / 'registration-control.json').read_bytes())
    assert cpu == control['worker'] and cpu['launch_id'] == control['launch_id']
    assert control['child_waited'] and control['actual_worker_terminal']['terminal']
    assert control['process_exit'] == cpu['process_exit'] == 0
    assert cpu['status'] == 'PASS_REAL_PLUGIN_REGISTRATION'
    assert cpu['plugin']['plugin_wheel_sha256']==capture.WHEEL_SHA
    assert not cpu['qapplication_created'] and not cpu['dawn_imported']
    expected_policy=dict(hash_randomization=0,hash_seed='0',no_user_site=True,dont_write_bytecode=True,
        context_sharing='true',mode='clean-environment-no-user-site')
    assert cpu['interpreter_policy']==expected_policy
    with zipfile.ZipFile(wheel) as archive:
        expected_package = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
            if name.startswith('vispy/') and not name.endswith('/')}
    with zipfile.ZipFile(PLUGIN_WHEEL) as archive:
        expected_plugin={name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith('napari_threedee/') and not name.endswith('/')}
    assert cpu['plugin']['plugin_files_sha256']==expected_plugin
    assert cpu['versions']=={'napari':'0.9.2','napari-threedee':'0.0.29','numpy':'2.4.6','PyQt6':'6.11.0'}
    passed, failed = [], []
    for name in CASES:
        row = manifest['workers'][name]
        assert row == json.loads((directory / (name + '.process.json')).read_bytes())
        report = directory / name / 'result.json'
        assert sha(report) == row['report_sha256']
        report = json.loads(report.read_bytes())
        assert report == row['worker'] and report['launch_id'] == row['launch_id']
        assert report['case'] == name and report['kind'] == kind
        assert report['process_stamp']['pid'] == report['pid']
        if report['pid'] != row['pid']:
            assert os.name == 'nt' and report['process_stamp']['parent_pid'] == row['pid']
            assert report['process_stamp']['windows_creation_time'] > 0
        assert row['child_waited'] and row['actual_worker_terminal']['terminal']
        assert row['process_exit'] == report['process_exit']
        assert row['process_exit'] in ((0,) if kind == 'upstream' else (0, 1))
        assert report['cleanup_passed'] and report['native_origins_verified'] and report['render_attempted']
        assert report['sources_sha256'] == sources() and report['wheel_sha256'] == manifest['wheel_sha256']
        assert report['installed_package_sha256'] == expected_package
        assert report['interpreter_policy']==expected_policy
        assert normalized_path(Path(report['prefix']).resolve()) == normalized_path(Path(setup['interpreter']['prefix']).resolve())
        assert Path(report['package']).is_relative_to(Path(report['prefix']))
        assert report['visible_windows_after_close'] == 0
        assert report['host_versions']=={'napari':'0.9.2','napari-threedee':'0.0.29','numpy':'2.4.6','PyQt6':'6.11.0'}
        assert report['plugin']['plugin_files_sha256']==expected_plugin
        assert report['plugin']['plugin_wheel_sha256']==capture.WHEEL_SHA
        assert Path(report['plugin']['plugin_origin']).is_relative_to(Path(report['prefix']))
        assert Path(report['plugin']['napari_origin']).is_relative_to(Path(report['prefix']))
        for leaf, checksum in report['artifacts'].items():
            assert Path(leaf).name == leaf and sha(directory / name / leaf) == checksum
        modules = json.loads((directory / name / 'native-modules.json').read_bytes())
        required = [report['native_module']] if kind == 'candidate' else []
        assert_wheel_module_origins(modules, report['package'], expected_package, required)
        if kind == 'candidate':
            assert set(report['shutdown_zeros']) == set(ZERO_FIELDS)
            assert all(value == 0 for value in report['shutdown_zeros'].values())
            assert report['device']['backend'] == 'Vulkan' and not report['device']['software']
            assert report['device']['vendor_id'] == 4318 and report['device']['device_id'] == 9860
        if row['process_exit']:
            assert kind == 'candidate' and report['status'] == 'FAILED_PRESERVED'
            failed.append(dict(case=name, error=report.get('error'), cleanup_error=report.get('cleanup_error')))
            continue
        image = np.load(directory / name / 'rgba.npy', allow_pickle=False)
        params = json.loads((directory / name / 'parameters.json').read_bytes())
        assert params == report['parameters']
        assert json.loads((directory / name / 'commands.json').read_bytes())
        assert json.loads((directory / name / 'shaders.json').read_bytes())
        extras=read_extras(directory/name,name)
        assert_landmarks(name,image,params,extras)
        assert report['compared_pixels'] == SIZE[0] * SIZE[1] and report['excluded_pixels'] == 0
        if kind == 'upstream':
            assert report['retained_reference_manifest_sha256']==LEGACY_SHA256
            old_image,old_params,old_extras=legacy_reference(name)
            assert np.array_equal(image,old_image) and params==old_params and set(extras)==set(old_extras)
            for key in extras:assert np.array_equal(extras[key],old_extras[key])
            assert report['status'] == 'PASS_UPSTREAM_PLUGIN_CASE'
            assert 'NVIDIA' in report['renderer']['vendor'] and 'RTX 4090' in report['renderer']['renderer']
            assert 'QOpenGLWidget' in params['native_mro']
            assert all('_dawn' not in Path(row['path']).name.lower() and 'vispy_submit' not in Path(row['path']).name.lower() for row in modules)
        else:
            assert report['status'] == 'PASS_CANDIDATE_PLUGIN_CASE'
            assert report['reference_manifest_sha256'] == reference_sha256
            original, expected, original_extras = load_reference(reference, reference_sha256, name)
            compare(name,image,original,params,expected,extras,original_extras)
            assert set(report['native_work_delta']) == set(WORK_FIELDS)
            assert all(value > 0 for value in report['native_work_delta'].values())
        passed.append(name)
    assert manifest['status'] == ('FAILED_REQUIRED_PLUGIN_CASES' if failed else expected_status)
    return dict(status='VERIFIED_CANDIDATE_PLUGIN_REQUIRED_FAILURES' if failed else 'VERIFIED_ALL_FIVE_' + kind.upper() + '_PLUGIN',
        cases=list(CASES), passed=passed, failed=failed, all_required_passed=not failed,
        pixels=len(passed) * SIZE[0] * SIZE[1], actual_workers_terminal=True, owned_environment_removed=True,
        real_cpu_registration_passed=True, platform_or_release_qualified=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('upstream', 'candidate'), required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--reference-sha256')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--registration-control', action='store_true')
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--launch-id')
    args = parser.parse_args()
    assert not sys.flags.optimize
    # Restore the retained oracle policy before any VisPy/Qt import. The shared
    # environment sanitizer removes inherited VISPY_* choices.
    os.environ['VISPY_PYQT5_SHARE_CONTEXT']='true'
    if args.registration_control:
        return registration_control(args)
    return worker(args) if args.worker else run(args)

if __name__=='__main__':raise SystemExit(main())
