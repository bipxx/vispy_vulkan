"""Requalify unchanged small controls in the large benchmark's NumPy profile."""
from pathlib import Path
import json,os,runpy,shutil,sys,tempfile,traceback
ROOT=Path(__file__).resolve().parents[2];PREP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from volume_wheel_runner import installed_environment,run_case,write,sha,clean_environment
from volume_wheel_probe import SOURCES,CASES
from mesh_layout_process import process_stamp
loader=ROOT/'build/native58-activation-root-1/build_loader.py'
assert sha(loader)=='8ed806014a374d14c5cb0d362f7986693dbed804ee16782af5d5a519cf75544b'
READER=runpy.run_path(str(loader),run_name='_controls1')['Reader'](ROOT)
PROFILE='compat/host-environments/volume-scientific-controls-numpy246-windows-cpython312-pyqt6.txt'
FILES=tuple(SOURCES)+('tools/volume_wheel_runner.py',PROFILE,'LICENSE','LICENSE-BSD','LICENSING.md',
                     'build/volume-admission-prep-root-1/run_controls1.py')
def held():return {name:sha(READER.path(name)) for name in FILES}

def main():
    seal=json.loads((PREP/'controls-source-seal1.json').read_bytes());assert held()==seal['sources']
    wheel=READER.path('build/native58-wheels-windows-cp312-root-2/wheels/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl')
    wheel_hash='105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81';assert sha(wheel)==wheel_hash
    out=ROOT/'build/volume-admission-controls-root-1';out.mkdir(exist_ok=False)
    cache=Path(tempfile.mkdtemp(prefix='vispy-volume-admission-cache-')).resolve()
    assert cache.parent==Path(tempfile.gettempdir()).resolve() and not cache.is_relative_to(ROOT)
    env=clean_environment(os.environ)
    for name in list(env):
        if name.upper().startswith(('VISPY_TEST_','VISPY_VOLUME_WHEEL_')):env.pop(name)
    env.update(VISPY_TEST_PYTHON=sys.executable,VISPY_TEST_RUNTIME_REQUIREMENTS=str(ROOT/PROFILE),
               VISPY_VOLUME_WHEEL_REPOSITORY=str(ROOT),VISPY_VOLUME_WHEEL_REFERENCE=str(ROOT/'tests/reference'),
               VISPY_EXPECTED_BACKEND='Vulkan',UV_CACHE_DIR=str(cache))
    result=dict(status='FAILED_PRESERVED',pid=os.getpid(),process_stamp=process_stamp(),cases={},
                wheel_sha256=wheel_hash,sources_sha256=seal['sources'],profile_sha256=sha(ROOT/PROFILE),
                full_release_qualified=False)
    try:
        with installed_environment(wheel,out/'environment',environment=env) as (python,environment):
            for case in CASES:
                row=run_case(case,python,wheel,out/'environment',environment)
                result['cases'][case]=dict(process_exit=row['process_exit'],report_sha256=row.get('report_sha256'),
                    actual_worker_terminal=row.get('actual_worker_terminal'),launch_id=row['launch_id'])
                if (out/'environment/worker-termination-unverified.json').exists():
                    raise RuntimeError('Actual worker termination must be resolved before continuing')
                worker=row['worker']
                assert row['process_exit']==worker['process_exit']==0,worker.get('error',case)
                assert worker['status']=='PASS_INSTALLED_WHEEL_VOLUME_CASE'
                assert worker['dependencies']['numpy']=='2.4.6'
                assert worker['wheel_sha256']==wheel_hash and worker['native_origins_verified'] and worker['cleanup_passed']
                device=worker['device'];assert device['ok'] and not device['software'] and device['backend']=='Vulkan'
                assert device['vendor_id']==4318 and device['device_id']==9860 and '610.88' in device['driver']
                assert len(worker['shutdown_zeros'])==8 and set(worker['shutdown_zeros'].values())=={0}
        assert set(result['cases'])==set(CASES) and held()==seal['sources'] and sha(wheel)==wheel_hash
        result['status']='PASS_ALL17_NUMPY246_VOLUME_CONTROLS'
    except BaseException:result['error']=traceback.format_exc()
    finally:
        unresolved=(out/'environment/worker-termination-unverified.json').exists()
        if not unresolved:
            assert cache.parent==Path(tempfile.gettempdir()).resolve() and cache.name.startswith('vispy-volume-admission-cache-')
            shutil.rmtree(cache)
        result.update(owned_cache=str(cache),owned_cache_removed=not cache.exists(),cache_preserved_for_unverified_worker=unresolved)
        write(out/'result.json',result)
    print(json.dumps(dict(status=result['status'],result_sha256=sha(out/'result.json'))),flush=True)
    return 0 if result['status']=='PASS_ALL17_NUMPY246_VOLUME_CONTROLS' else 1

if __name__=='__main__':raise SystemExit(main())
