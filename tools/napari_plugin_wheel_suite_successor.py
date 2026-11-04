# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh original and installed candidate napari-threedee overlay workflows on napari 0.10.0 (decisions D30, D31).

Successor of tools/napari_plugin_wheel_suite.py, which pins napari 0.9.2 through its runtime lock, host versions,
reference packet and capture tool, and stays bound to its evidence. Each step here is the retained suite's own code
(the same code object) reading this module's inputs: the overlay successor fixture's render; the napari 0.10.0
overlay packet as the retained original, with its oracle lock (host-lock.txt) as the runtime; and these sources.
Three steps are this module's own:
- runtime_requirements: the lock's asciitree 1.0.0 has a wheel, so only VisPy is replaced (the retained runtime also
  replaced an sdist-only asciitree 0.3.3);
- plugin_info: the plugin successor capture's registration check, the locked host versions and the whole lock;
- verify_saved: the retained check, reading HOST_VERSIONS and PLUGIN_WHEEL_SHA256.
Another napari release needs its overlay packet and these pins.
"""
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
import types
import uuid
import zipfile
if not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import napari_plugin_wheel_suite as retained
    from fixture_napari_threedee_overlay_successor import CASES,SIZE,assert_landmarks,render
    from napari_host_packets import LOCK_SNAPSHOT,lock_mismatches
    from napari_plugin_wheel_suite import (ROOT,INPUTS,INPUTS_SHA256,PLUGIN_WHEEL,UPSTREAM_WHEEL_SHA256,WORK_FIELDS,
        ZERO_FIELDS,assert_locked_upstream,assert_wheel_module_origins,base,compare,installed_environment,
        interpreter_policy,native_modules,normalized_path,package_hashes,process_stamp,read_extras,run_logged,sha,
        worker_terminal,write)
else:
    from . import napari_plugin_wheel_suite as retained
    from .fixture_napari_threedee_overlay_successor import CASES,SIZE,assert_landmarks,render
    from .napari_host_packets import LOCK_SNAPSHOT,lock_mismatches
    from .napari_plugin_wheel_suite import (ROOT,INPUTS,INPUTS_SHA256,PLUGIN_WHEEL,UPSTREAM_WHEEL_SHA256,WORK_FIELDS,
        ZERO_FIELDS,assert_locked_upstream,assert_wheel_module_origins,base,compare,installed_environment,
        interpreter_policy,native_modules,normalized_path,package_hashes,process_stamp,read_extras,run_logged,sha,
        worker_terminal,write)
LEGACY='tests/reference/napari-threedee-overlay-opengl-napari-0.10.0'
LEGACY_SHA256='70b2241a0dc5567f4300e89f28117836b8f276177c6eec79f25c36054de556c9'
RUNTIME=f'{LEGACY}/{LOCK_SNAPSHOT}'
HOST_VERSIONS={'napari':'0.10.0','napari-threedee':'0.0.29','numpy':'2.4.6','PyQt6':'6.12.0'}
PLUGIN_WHEEL_SHA256='de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e'
SOURCES=tuple(dict.fromkeys((*base.SOURCES,'tools/napari_plugin_wheel_suite_successor.py',
    'tools/napari_plugin_wheel_suite.py','tools/smooth_line_parity.py','tools/fixture_napari_threedee_overlay_successor.py',
    'tools/fixture_napari_threedee_overlay.py','tools/napari_world_position.py','tools/napari_host_packets.py',
    'tools/oracle_napari_plugin_successor_capture.py','tools/oracle_napari_threedee_overlay_capture.py',RUNTIME,
    PLUGIN_WHEEL.relative_to(ROOT).as_posix(),
    *((INPUTS/name).relative_to(ROOT).as_posix() for name in ('manifest.json','napari-threedee-LICENSE.txt')),
    *(f'compat/host-environments/{name}' for name in retained.capture.PROOFS))))


def _retained(function):
    """The retained step's own code, reading this module's inputs."""
    return types.FunctionType(function.__code__,globals(),function.__name__,function.__defaults__,function.__closure__)


sources=_retained(retained.sources)
legacy_reference=_retained(retained.legacy_reference)
registration_control=_retained(retained.registration_control)
load_reference=_retained(retained.load_reference)
worker=_retained(retained.worker)
run=_retained(retained.run)
main=_retained(retained.main)


def runtime_requirements():
    original=(ROOT/RUNTIME).read_text(encoding='utf-8')
    blocks=re.findall(base.VISPY_BLOCK,original)
    assert len(blocks)==1
    assert sha(PLUGIN_WHEEL)==PLUGIN_WHEEL_SHA256
    return original.replace(blocks[0],'',1)+f'\nnapari-threedee @ {PLUGIN_WHEEL.as_uri()} --hash=sha256:{PLUGIN_WHEEL_SHA256}\n'


def plugin_info():
    # Workers run this file as a script, so tools/ is first on sys.path, as the plugin successor capture needs.
    import oracle_napari_plugin_successor_capture as capture
    record=capture.plugin_provenance('overlay',None)
    assert record['plugin_wheel_sha256']==PLUGIN_WHEEL_SHA256
    versions={name:metadata.version(name) for name in HOST_VERSIONS}
    assert versions==HOST_VERSIONS and not lock_mismatches(ROOT/RUNTIME)
    assert Path(record['plugin_origin']).is_relative_to(Path(sys.prefix).resolve())
    assert Path(record['napari_origin']).is_relative_to(Path(sys.prefix).resolve())
    return record,versions


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
    assert cpu['plugin']['plugin_wheel_sha256']==PLUGIN_WHEEL_SHA256
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
    assert cpu['versions']==HOST_VERSIONS
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
        assert report['host_versions']==HOST_VERSIONS
        assert report['plugin']['plugin_files_sha256']==expected_plugin
        assert report['plugin']['plugin_wheel_sha256']==PLUGIN_WHEEL_SHA256
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


if __name__=='__main__':raise SystemExit(main())
