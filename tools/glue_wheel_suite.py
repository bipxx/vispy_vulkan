# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh original Glue references and isolated installed-wheel comparisons."""
from __future__ import annotations
import argparse
from email.parser import BytesParser
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

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT / 'tools'))
    from fixture_glue_extensions import CASES, assert_landmarks, render
    from smooth_line_parity import smooth_line_difference
    from image_wheel_runner import installed_environment, run_logged, sha, write
    from mesh_layout_process import process_stamp, worker_terminal, native_modules, assert_wheel_module_origins, normalized_path
else:
    from .fixture_glue_extensions import CASES, assert_landmarks, render
    from .smooth_line_parity import smooth_line_difference
    from .image_wheel_runner import installed_environment, run_logged, sha, write
    from .mesh_layout_process import process_stamp, worker_terminal, native_modules, assert_wheel_module_origins, normalized_path

LOCK_SHA256 = '6dbfd71fd13b1a76dd33012027355cd482984b416f07b1b405a1fa4e3b7467ff'
BSD_SHA256 = 'a28bb857d763513c810ca843558c12cf97f64b990b855c1ce7f5e291e52fc25c'
AGPL_SHA256 = '0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0'
FRB_SHA256 = '33d940f7427cb22935662b83947d4e846db67336950ed7ec0c0a52a3a470b792'
UPSTREAM_WHEEL_SHA256 = 'c4862155e735009b1af6aeda45ea94a72e1a375d6086c89273455d66238bb18e'
UPSTREAM_EXTRAS = {
    'vispy/version.py': '706b070ac109e5178da29425be0036ee52db19f653f00de5810e57db784108a4',
    'vispy/visuals/text/_sdf_cpu.cp310-win_amd64.pyd': '4ccf7978fe136fd7af3773445431e24b20d36dd9b5377df9b3e407663ff8977e',
    'vispy/visuals/text/_sdf_cpu.cp311-win_amd64.pyd': '64eaac187c0bed04ab1a5ce7226cd028fb7aace2793e9c6190fad7734b2eb831',
    'vispy/visuals/text/_sdf_cpu.cp312-win_amd64.pyd': '8a4f322600e1e68ac8e71f9e86cce0b5dcaaeca3ae65e7a8edb22e5dcc11d24c',
}
ZERO_FIELDS = ('pending_tickets', 'live_buffer_bytes', 'live_cpu_buffer_bytes', 'live_texture_bytes',
               'deferred_frames', 'queued_frames', 'vk_memory_live_allocations', 'vk_memory_live_bytes')
WORK_FIELDS = ('draw_calls', 'pipeline_misses', 'vk_queue_submits')
SOURCES = ('tools/glue_wheel_suite.py', 'tools/fixture_glue_extensions.py', 'tools/fixture_glue.py',
           'tools/fixture_gloo.py', 'tools/image_wheel_runner.py', 'tools/fixture_image_extensions.py',
           'tools/mesh_layout_process.py', 'tools/oracle_glue_requirements.txt',
           'tools/oracle_glue_admission.json', 'compat/upstream_manifest.json',
           'LICENSE', 'LICENSE-BSD', 'tools/smooth_line_parity.py')
# Decision D5: scatter_axes draws smooth (antialiased) axes, so its frame uses the smooth-line criterion.
SMOOTH_LINE = frozenset({'scatter_axes'})
VISPY_BLOCK = r'(?m)^vispy==0\.17\.0 \\\n(?:    --hash=sha256:[a-f0-9]+(?: \\)?\n)+'


def sources():
    return {name: sha(ROOT / name) for name in SOURCES}


def runtime_requirements():
    path = ROOT / 'tools/oracle_glue_requirements.txt'
    assert sha(path) == LOCK_SHA256
    # Preserve the full pinned host closure; only replace the renderer artifact.
    original = path.read_text(encoding='utf-8')
    changed, count = re.subn(VISPY_BLOCK, '', original)
    assert count == 1, 'One exact original VisPy requirement block required'
    return changed


def upstream_lock_hashes():
    path = ROOT / 'tools/oracle_glue_requirements.txt'
    assert sha(path) == LOCK_SHA256
    block = re.search(VISPY_BLOCK, path.read_text(encoding='utf-8'))
    assert block is not None
    return set(re.findall(r'sha256:([a-f0-9]{64})', block.group()))


def assert_locked_upstream(wheel):
    digest = sha(wheel)
    assert digest == UPSTREAM_WHEEL_SHA256 and digest in upstream_lock_hashes(), 'Original upstream wheel is not the locked CP312 artifact'


def package_hashes(wheel, package, kind):
    hashes = {}
    if kind == 'upstream':
        assert_locked_upstream(wheel)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        metadata_names = [name for name in names if name.endswith('.dist-info/METADATA')]
        wheel_names = [name for name in names if name.endswith('.dist-info/WHEEL')]
        assert len(metadata_names) == len(wheel_names) == 1
        headers = BytesParser().parsebytes(archive.read(metadata_names[0]))
        version = '0.17.0' if kind == 'upstream' else '0.17.0+vulkan.1'
        assert headers['Name'].lower() == 'vispy' and headers['Version'] == metadata.version('vispy') == version
        from packaging.tags import parse_tag, sys_tags
        tags = BytesParser().parsebytes(archive.read(wheel_names[0])).get_all('Tag', [])
        assert set().union(*(parse_tag(tag) for tag in tags)) & set(sys_tags())
        for name in names:
            if not name.startswith('vispy/') or name.endswith('/'):
                continue
            path = (package / Path(name).relative_to('vispy')).resolve()
            assert path.is_relative_to(package)
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            assert sha(path) == digest, name
            hashes[name] = digest
        if kind == 'upstream':
            assert not any('_dawn' in name or 'vispy_submit' in name for name in names)
            licenses = [name for name in names if 'license' in Path(name).name.lower()]
            assert any(hashlib.sha256(archive.read(name)).hexdigest() == BSD_SHA256 for name in licenses)
            pinned = json.loads((ROOT / 'compat/upstream_manifest.json').read_bytes())['files']
            checked = {name[6:]: digest for name, digest in hashes.items() if name[6:] in pinned}
            assert len(pinned) == 517 and set(checked) == set(pinned)
            assert all(pinned[name] == digest for name, digest in checked.items())
            assert {name: digest for name, digest in hashes.items() if name[6:] not in pinned} == UPSTREAM_EXTRAS
        else:
            assert hashes['vispy/_licenses/LICENSE'] == AGPL_SHA256
            assert hashes['vispy/_licenses/LICENSE-BSD'] == BSD_SHA256
    return hashes


def compare(name, image, original, params, expected):
    import numpy as np
    assert name in CASES and image.shape == original.shape == (128, 128, 4)
    assert image.dtype == original.dtype == np.uint8
    actual, reference = dict(params), dict(expected)
    assert 'QOpenGLWidget' in reference.pop('native_mro')
    assert 'QOpenGLWidget' not in actual.pop('native_mro')
    assert actual == reference, (name, 'Original host state/inputs differ')
    if name in SMOOTH_LINE:
        reason = smooth_line_difference(image, original)
        assert reason is None, (name, 'Smooth-line Glue frame differs', reason)
    else:
        assert np.array_equal(image, original), (name, 'Exact full Glue frame differs')
    assert_landmarks(name, image)


def load_reference(directory, digest, name):
    directory = Path(directory)
    assert sha(directory / 'manifest.json') == digest, 'Fresh reference manifest differs'
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    assert manifest.get('status') == 'PASS_ALL_FIVE_UPSTREAM_GLUE' and manifest.get('kind') == 'upstream'
    assert manifest['cases'] == list(CASES) and manifest['sources_sha256'] == sources()
    assert set(manifest['workers']) == set(CASES)
    assert manifest['wheel_sha256'] == UPSTREAM_WHEEL_SHA256
    record = manifest['workers'][name]
    report_path = directory / name / 'result.json'
    assert sha(report_path) == record['report_sha256']
    worker = json.loads(report_path.read_bytes())
    assert worker == record['worker'] and worker['status'] == 'PASS_UPSTREAM_GLUE_CASE'
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
    assert_landmarks(name, image)
    assert params == worker['parameters'] and 'QOpenGLWidget' in params['native_mro']
    image.setflags(write=False)
    return image, params


def cache_control(args):
    """Exercise the real pinned Glue model/cache without constructing an app."""
    result = dict(status='FAILED_CPU_CACHE_CONTROL', process_exit=1, pid=os.getpid(),
        process_stamp=process_stamp(), launch_id=args.launch_id, graphics_invoked=False)
    try:
        import numpy as np
        import glue
        from glue.core import Data
        from glue.core.fixed_resolution_buffer import compute_fixed_resolution_buffer, invalidate_cache
        assert sha(Path(glue.__file__).parent / 'core/fixed_resolution_buffer.py') == FRB_SHA256
        assert metadata.version('glue-core') == '1.27.0'
        assert Path(glue.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
        data = Data(intensity=np.ones((4, 4, 4), np.float32))
        component = data.id['intensity']
        def sample():
            return compute_fixed_resolution_buffer(data, [(0, 3, 4)] * 3,
                target_cid=component, cache_id='glue-wheel-cache-control')
        original = sample()
        assert np.all(original == 1)
        data.update_components({component: np.zeros((4, 4, 4), np.float32)})
        assert np.all(data[component] == 0)
        stale = sample()
        assert np.all(stale == 1), 'Pinned original cache issue did not reproduce'
        invalidate_cache(data)
        data.update_components({component: np.full((4, 4, 4), 2, np.float32)})
        fresh = sample()
        assert np.all(fresh == 2), 'Invalidation-before-update did not refresh the buffer'
        from qtpy.QtWidgets import QApplication
        assert QApplication.instance() is None and 'vispy._dawn' not in sys.modules
        result.update(status='PASS_REAL_GLUE_CPU_CACHE_PROTOCOL', process_exit=0,
            same_dataset_and_component=True, stale_buffer_reproduced=True, invalidation_before_update_passed=True,
            qapplication_created=False, dawn_imported=False)
    except BaseException:
        result['error'] = traceback.format_exc()
    write(args.output, result)
    return result['process_exit']


def worker(args):
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert args.case in CASES and len(args.launch_id) == 32 and all(c in '0123456789abcdef' for c in args.launch_id)
    args.output.mkdir(parents=True, exist_ok=False)
    held = sources()
    wheel_digest = sha(args.wheel)
    result = dict(schema=1, status='FAILED_PRESERVED', process_exit=1, case=args.case, kind=args.kind,
        pid=os.getpid(), launch_id=args.launch_id, process_stamp=process_stamp(), sources_sha256=held,
        wheel_sha256=wheel_digest, cleanup_passed=False, native_origins_verified=False, render_attempted=False)
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
        import glue, glue_qt, glue_vispy_viewers
        from glue_qt.utils import get_qapp
        from qtpy import API_NAME, QT_VERSION
        assert API_NAME == 'PyQt6'
        host = Path(glue_vispy_viewers.__file__).resolve().parent
        admission = json.loads((ROOT / 'tools/oracle_glue_admission.json').read_bytes())
        observed = {name: sha(host / name) for name in admission['source_files']}
        assert all(observed[name] == row['sha256'] for name, row in admission['source_files'].items())
        assert sha(Path(glue.__file__).parent / 'core/fixed_resolution_buffer.py') == FRB_SHA256
        versions = {name: metadata.version(name) for name in ('glue-core', 'glue-qt', 'glue-vispy-viewers', 'PyQt6')}
        assert versions == {'glue-core': '1.27.0', 'glue-qt': '0.4.2', 'glue-vispy-viewers': '1.4.0', 'PyQt6': '6.11.0'}
        origins = {module.__name__: str(Path(module.__file__).resolve()) for module in (glue, glue_qt, glue_vispy_viewers)}
        assert all(Path(origin).is_relative_to(prefix) for origin in origins.values())
        qapp = get_qapp()
        qapp.setQuitOnLastWindowClosed(False)
        result.update(prefix=str(prefix), package=str(package), installed_package_sha256=installed,
            host_sources_sha256=observed, host_versions=versions, host_origins=origins, qt_version=QT_VERSION,
            qt_platform=qapp.platformName(), python=sys.version)
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
            original, expected = load_reference(args.reference, args.reference_sha256, args.case)
            result['reference_manifest_sha256'] = args.reference_sha256
        result['render_attempted'] = True
        image, commands, shaders, params = render(args.case)
        import numpy as np
        np.save(args.output / 'rgba.npy', image, allow_pickle=False)
        write(args.output / 'commands.json', commands)
        write(args.output / 'shaders.json', shaders)
        write(args.output / 'parameters.json', params)
        assert commands and shaders
        assert_landmarks(args.case, image)
        if args.kind == 'upstream':
            assert 'QOpenGLWidget' in params['native_mro']
        else:
            compare(args.case, image, original, params, expected)
            after = dict(dawn.probe())
            result['native_work_delta'] = {key: after[key] - before[key] for key in WORK_FIELDS}
            assert all(value > 0 for value in result['native_work_delta'].values())
            device = dict(dawn.device_info())
            assert device['ok'] and device['backend'] == 'Vulkan' and not device['software']
            assert device['vendor_id'] == 4318 and device['device_id'] == 9860
            result['device'] = device
        result.update(status='PASS_UPSTREAM_GLUE_CASE' if args.kind == 'upstream' else 'PASS_CANDIDATE_GLUE_CASE',
            process_exit=0, parameters=params, compared_pixels=128 * 128, excluded_pixels=0)
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        try:
            try:
                if result['render_attempted']:
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
    env = dict(os.environ)
    # Reuse the tested owned-environment lifecycle; all worker choices are argv.
    for name in list(env):
        if name.upper().startswith('VISPY_IMAGE_'):
            env.pop(name)
    env['VISPY_IMAGE_REPOSITORY'] = str(args.repository)
    env['VISPY_TEST_RUNTIME_REQUIREMENTS'] = str(runtime.resolve())
    result = dict(schema=1, kind=args.kind, cases=list(CASES), sources_sha256=held,
        wheel_sha256=wheel_digest, workers={},
        status='FAILED_BLOCKS_CANDIDATE' if args.kind == 'upstream' else 'FAILED_REQUIRED_GLUE_CASES',
        original_release_complete=False)
    try:
        with installed_environment(args.wheel, args.output / 'environment', environment=env) as (python, environment):
            launch = uuid.uuid4().hex
            command = [python, '-I', '-B', Path(__file__), '--cache-control', '--kind', args.kind,
                '--launch-id', launch, '--wheel', args.wheel, '--repository', args.repository,
                '--output', args.output / 'cache-control.json']
            control = run_logged(command, cwd=Path(python).parent, environment=environment,
                log=args.output / 'cache-control.stdout.log')
            try:
                cpu = json.loads((args.output / 'cache-control.json').read_bytes())
                assert cpu['launch_id'] == launch
                control.update(worker=cpu, launch_id=launch, actual_worker_terminal=worker_terminal(cpu, control['pid']))
                assert control['actual_worker_terminal']['terminal']
            except BaseException:
                write(args.output / 'environment/worker-termination-unverified.json', dict(error=traceback.format_exc()))
                raise
            result['cache_control'] = control
            assert control['process_exit'] == cpu['process_exit'] == 0
            assert cpu['status'] == 'PASS_REAL_GLUE_CPU_CACHE_PROTOCOL'
            for name in CASES:
                launch = uuid.uuid4().hex
                command = [python, '-I', '-B', Path(__file__), '--worker', '--kind', args.kind,
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
            result['status'] = 'PASS_ALL_FIVE_UPSTREAM_GLUE' if args.kind == 'upstream' else 'PASS_ALL_FIVE_CANDIDATE_GLUE'
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
    expected_status = 'PASS_ALL_FIVE_UPSTREAM_GLUE' if kind == 'upstream' else 'PASS_ALL_FIVE_CANDIDATE_GLUE'
    allowed = {expected_status} if kind == 'upstream' else {expected_status, 'FAILED_REQUIRED_GLUE_CASES'}
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
    control = manifest['cache_control']
    cpu = json.loads((directory / 'cache-control.json').read_bytes())
    assert cpu == control['worker'] and cpu['launch_id'] == control['launch_id']
    assert control['child_waited'] and control['actual_worker_terminal']['terminal']
    assert control['process_exit'] == cpu['process_exit'] == 0
    assert cpu['status'] == 'PASS_REAL_GLUE_CPU_CACHE_PROTOCOL'
    assert cpu['stale_buffer_reproduced'] and cpu['invalidation_before_update_passed']
    assert not cpu['qapplication_created'] and not cpu['dawn_imported']
    with zipfile.ZipFile(wheel) as archive:
        expected_package = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
            if name.startswith('vispy/') and not name.endswith('/')}
    admission = json.loads((ROOT / 'tools/oracle_glue_admission.json').read_bytes())
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
        assert normalized_path(Path(report['prefix']).resolve()) == normalized_path(Path(setup['interpreter']['prefix']).resolve())
        assert Path(report['package']).is_relative_to(Path(report['prefix']))
        assert report['visible_windows_after_close'] == 0
        assert report['host_sources_sha256'] == {key: value['sha256'] for key, value in admission['source_files'].items()}
        assert report['host_versions'] == {'glue-core': '1.27.0', 'glue-qt': '0.4.2', 'glue-vispy-viewers': '1.4.0', 'PyQt6': '6.11.0'}
        assert all(Path(origin).is_relative_to(Path(report['prefix'])) for origin in report['host_origins'].values())
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
        assert_landmarks(name, image)
        assert report['compared_pixels'] == 128 * 128 and report['excluded_pixels'] == 0
        if kind == 'upstream':
            assert report['status'] == 'PASS_UPSTREAM_GLUE_CASE'
            assert 'NVIDIA' in report['renderer']['vendor'] and 'RTX 4090' in report['renderer']['renderer']
            assert 'QOpenGLWidget' in params['native_mro']
            assert all('_dawn' not in Path(row['path']).name.lower() and 'vispy_submit' not in Path(row['path']).name.lower() for row in modules)
        else:
            assert report['status'] == 'PASS_CANDIDATE_GLUE_CASE'
            assert report['reference_manifest_sha256'] == reference_sha256
            original, expected = load_reference(reference, reference_sha256, name)
            compare(name, image, original, params, expected)
            assert set(report['native_work_delta']) == set(WORK_FIELDS)
            assert all(value > 0 for value in report['native_work_delta'].values())
        passed.append(name)
    assert manifest['status'] == ('FAILED_REQUIRED_GLUE_CASES' if failed else expected_status)
    return dict(status='VERIFIED_CANDIDATE_GLUE_REQUIRED_FAILURES' if failed else 'VERIFIED_ALL_FIVE_' + kind.upper() + '_GLUE',
        cases=list(CASES), passed=passed, failed=failed, all_required_passed=not failed,
        pixels=len(passed) * 128 * 128, actual_workers_terminal=True, owned_environment_removed=True,
        real_cpu_cache_protocol_passed=True, platform_or_release_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('upstream', 'candidate'), required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--reference-sha256')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--cache-control', action='store_true')
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--launch-id')
    args = parser.parse_args()
    assert not sys.flags.optimize
    if args.cache_control:
        return cache_control(args)
    return worker(args) if args.worker else run(args)


if __name__ == '__main__':
    raise SystemExit(main())
