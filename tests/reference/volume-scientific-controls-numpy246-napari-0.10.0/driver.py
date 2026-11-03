"""Requalify the unchanged small volume controls on napari 0.10.0, in the large benchmark's NumPy profile.

The successor of tests/reference/volume-scientific-controls-numpy246/driver.py (D31, run napari-010-volume-admission-307):
the same 17 cases on the same native58 wheel (105698c7) and the same NumPy 2.4.6 / PyQt6 6.11.0 profile, with napari
and npe2 at 0.10.0, run through Phase 4's successor runner and probe (tools/volume_wheel_runner_successor.py), which
compare against the 0.10.0 reference packets. As the retained driver: an owned uv cache in system TEMP removed after
the run, the runner's owned environment, every worker checked, and the sources this run reads hashed before and after.
Usage (repository root): uv run --no-sync --frozen python -B <this script>
"""
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import traceback

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tools'))
from volume_wheel_runner_successor import installed_environment, run_case, write, sha
from volume_wheel_runner import clean_environment
from volume_wheel_probe_successor import SOURCES, CASES, DIRECT_CASES
from mesh_layout_process import process_stamp

RUN = ROOT / 'build/runs/napari-010-volume-admission-307'
W = ROOT / 'build/work/napari-010-volume-admission-307'
PROFILE = 'compat/host-environments/volume-scientific-controls-numpy246-napari-0.10.0-windows-cpython312-pyqt6.txt'
WHEEL = ROOT / 'build/native58-wheels-windows-cp312-root-2/wheels/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
WHEEL_SHA256 = '105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81'
FILES = tuple(SOURCES) + ('tools/volume_wheel_runner_successor.py', 'tools/volume_wheel_runner.py', PROFILE, 'LICENSE',
                          'LICENSE-BSD', 'LICENSING.md', 'build/runs/napari-010-volume-admission-307/run_controls.py')


def held():
    return {name: sha(ROOT / name) for name in FILES}


def main():
    assert (W / '.build-hygiene-owner.json').is_file(), 'scratch not registered'
    sources = held()
    assert sha(WHEEL) == WHEEL_SHA256
    out = W / 'controls'
    out.mkdir(exist_ok=False)
    cache = Path(tempfile.mkdtemp(prefix='vispy-volume-admission-cache-')).resolve()
    assert cache.parent == Path(tempfile.gettempdir()).resolve() and not cache.is_relative_to(ROOT)
    env = clean_environment(os.environ)
    for name in list(env):
        if name.upper().startswith(('VISPY_TEST_', 'VISPY_VOLUME_WHEEL_')):
            env.pop(name)
    env.update(VISPY_TEST_PYTHON=sys.executable, VISPY_TEST_RUNTIME_REQUIREMENTS=str(ROOT / PROFILE),
               VISPY_VOLUME_WHEEL_REPOSITORY=str(ROOT), VISPY_VOLUME_WHEEL_REFERENCE=str(ROOT / 'tests/reference'),
               VISPY_EXPECTED_BACKEND='Vulkan', UV_CACHE_DIR=str(cache))
    result = dict(status='FAILED_PRESERVED', pid=os.getpid(), process_stamp=process_stamp(), cases={},
                  wheel_sha256=WHEEL_SHA256, sources_sha256=sources, profile_sha256=sha(ROOT / PROFILE),
                  full_release_qualified=False)
    try:
        with installed_environment(WHEEL, out / 'environment', environment=env) as (python, environment):
            for case in CASES:
                row = run_case(case, python, WHEEL, out / 'environment', environment)
                result['cases'][case] = dict(process_exit=row['process_exit'], report_sha256=row.get('report_sha256'),
                                             actual_worker_terminal=row.get('actual_worker_terminal'),
                                             launch_id=row['launch_id'])
                if (out / 'environment/worker-termination-unverified.json').exists():
                    raise RuntimeError('Actual worker termination must be resolved before continuing')
                worker = row['worker']
                assert row['process_exit'] == worker['process_exit'] == 0, worker.get('error', case)
                assert worker['status'] == 'PASS_INSTALLED_WHEEL_VOLUME_CASE'
                assert worker['dependencies']['numpy'] == '2.4.6'
                assert worker['wheel_sha256'] == WHEEL_SHA256 and worker['native_origins_verified'] and worker['cleanup_passed']
                device = worker['device']
                assert device['ok'] and not device['software'] and device['backend'] == 'Vulkan'
                assert device['vendor_id'] == 4318 and device['device_id'] == 9860 and '610.88' in device['driver']
                assert len(worker['shutdown_zeros']) == 8 and set(worker['shutdown_zeros'].values()) == {0}
                if case not in DIRECT_CASES:  # the categorical cases run napari
                    assert worker['host']['napari'] == '0.10.0' and worker['host']['numba'] == '0.68.0', worker['host']
        assert set(result['cases']) == set(CASES) and held() == sources and sha(WHEEL) == WHEEL_SHA256
        result['status'] = 'PASS_ALL17_NUMPY246_VOLUME_CONTROLS'
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        unresolved = (out / 'environment/worker-termination-unverified.json').exists()
        if not unresolved:
            assert cache.parent == Path(tempfile.gettempdir()).resolve() and cache.name.startswith('vispy-volume-admission-cache-')
            shutil.rmtree(cache)
        result.update(owned_cache=str(cache), owned_cache_removed=not cache.exists(),
                      cache_preserved_for_unverified_worker=unresolved)
        write(out / 'result.json', result)
    print(json.dumps(dict(status=result['status'], result_sha256=sha(out / 'result.json'))), flush=True)
    return 0 if result['status'] == 'PASS_ALL17_NUMPY246_VOLUME_CONTROLS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
