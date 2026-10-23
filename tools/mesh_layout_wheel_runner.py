# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh wheel environments and waited per-scene processes for regression tests."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
import uuid
try:
    from .fixture_mesh_layout_extensions import CASES
    from .mesh_layout_process import worker_terminal
except ImportError:
    from fixture_mesh_layout_extensions import CASES
    from mesh_layout_process import worker_terminal

ROOT=Path(__file__).resolve().parents[1]


def write(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_environment(environment):
    result=dict(environment)
    for name in ('PYTHONPATH','PYTHONHOME','VISPY_APP_BACKEND','VISPY_GL_BACKEND'):result.pop(name,None)
    for name in list(result):
        upper=name.upper()
        required=(upper.startswith(('VISPY_TEST_','VISPY_MESH_LAYOUT_')) or upper=='VISPY_EXPECTED_BACKEND')
        if upper.startswith(('VK_','DAWN_')) or upper.startswith('VISPY_') and not required:result.pop(name,None)
    result['PYTHONDONTWRITEBYTECODE']='1'
    return result


def run_logged(arguments,*,cwd,environment,log):
    log=Path(log)
    with log.open('xb') as stream:
        with subprocess.Popen([str(value) for value in arguments],cwd=cwd,env=environment,
                stdout=stream,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as process:
            exit_code=process.wait()
            pid=process.pid
    return dict(arguments=[str(value) for value in arguments],pid=pid,process_exit=exit_code,
                child_waited=True,log=str(log),log_sha256=sha(log))


@contextmanager
def installed_environment(wheel,evidence,*,environment=None):
    """Own and remove only the newly created external environment, even on failure."""
    wheel=Path(wheel).resolve(strict=True)
    evidence=Path(evidence).resolve()
    assert not evidence.exists(), 'Fresh scene-suite evidence directory required'
    evidence.mkdir(parents=True)
    env=clean_environment(os.environ if environment is None else environment)
    repository=Path(env.get('VISPY_MESH_LAYOUT_REPOSITORY',ROOT)).resolve(strict=True)
    supplied=env.get('VISPY_MESH_LAYOUT_PYTHON')
    owner=None
    stages=[]
    setup=dict(schema=1,wheel=str(wheel),wheel_sha256=sha(wheel),owned_environment=not bool(supplied),stages=stages)
    try:
        if supplied:
            python=Path(supplied).resolve(strict=True)
        else:
            uv=shutil.which('uv')
            assert uv is not None, 'uv is required for a clean hashed wheel environment'
            temporary_parent=Path(tempfile.gettempdir()).resolve()
            owner=Path(tempfile.mkdtemp(prefix='vispy-mesh-layout-wheel-')).resolve()
            assert owner.parent==temporary_parent and not owner.is_relative_to(ROOT) and not owner.is_relative_to(repository)
            setup['owned_root']=str(owner)
            venv=owner/'venv'
            requested_python=env.get('VISPY_TEST_PYTHON',sys.executable)
            commands=[([uv,'venv',str(venv),'--python',requested_python],owner)]
            python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            runtime=evidence/'runtime-requirements.txt'
            supplied_requirements=env.get('VISPY_TEST_RUNTIME_REQUIREMENTS')
            if supplied_requirements:
                runtime.write_bytes(Path(supplied_requirements).resolve(strict=True).read_bytes())
            else:
                commands.append(([uv,'export','--locked','--no-default-groups','--no-emit-project',
                                  '--output-file',str(runtime)],ROOT))
            wheel_requirements=evidence/'wheel-requirements.txt'
            wheel_requirements.write_text(f'vispy @ {wheel.as_uri()} --hash=sha256:{setup["wheel_sha256"]}\n',encoding='utf-8')
            commands.extend([
                ([uv,'pip','install','--python',str(python),'--require-hashes','--only-binary',':all:',
                  '--requirements',str(runtime)],owner),
                ([uv,'pip','install','--python',str(python),'--no-deps','--require-hashes',
                  '--requirements',str(wheel_requirements)],owner)])
            for index,(arguments,cwd) in enumerate(commands):
                stage=run_logged(arguments,cwd=cwd,environment=env,log=evidence/f'setup-{index}.log')
                stages.append(stage)
                assert stage['process_exit']==0, stage
            setup['runtime_requirements_sha256']=sha(runtime)
        identity_log=evidence/'python-identity.log'
        identity=run_logged([python,'-I','-B','-c',
            'import json,sys; print(json.dumps(dict(prefix=sys.prefix,executable=sys.executable,version=sys.version)))'],
            cwd=Path(python).parent,environment=env,log=identity_log)
        stages.append(identity)
        assert identity['process_exit']==0, identity
        setup['interpreter']=json.loads(identity_log.read_text(encoding='utf-8').strip())
        prefix=Path(setup['interpreter']['prefix']).resolve()
        assert not prefix.is_relative_to(ROOT) and not prefix.is_relative_to(repository), 'External consumer prefix required'
        setup['python']=str(python)
        setup['status']='READY_FOR_REQUIRED_SCENES'
        write(evidence/'setup.json',setup)
        yield python,env
    except BaseException:
        if not (evidence/'setup.json').exists():
            setup.update(status='FAILED_PRESERVED',error=traceback.format_exc())
            write(evidence/'setup.json',setup)
        raise
    finally:
        cleanup=dict(schema=1,all_setup_children_waited=all(stage['child_waited'] for stage in stages),
                     owned_environment=owner is not None,wheel_preserved=False)
        try:
            try:cleanup['wheel_preserved']=sha(wheel)==setup['wheel_sha256']
            except BaseException:cleanup['wheel_observation_error']=traceback.format_exc()
            if owner is not None:
                assert not (evidence/'worker-termination-unverified.json').exists(), 'Worker termination must be resolved before deleting its environment'
                # A single deletion of this invocation's literal mkdtemp root.
                # A cleanup failure is reported and never retried here.
                resolved=owner.resolve(strict=True)
                assert resolved==owner and owner.parent==Path(tempfile.gettempdir()).resolve()
                assert owner.name.startswith('vispy-mesh-layout-wheel-') and not owner.is_relative_to(ROOT) and not owner.is_relative_to(repository)
                cleanup['owned_root']=str(owner)
                shutil.rmtree(owner)
                cleanup['owned_root_removed']=not owner.exists()
                assert cleanup['owned_root_removed']
            assert cleanup['wheel_preserved'], 'Supplied wheel changed during the scene suite'
            cleanup['status']=('PASS_OWNED_ENVIRONMENT_TEARDOWN' if owner else
                               'EXISTING_ENVIRONMENT_UNCHANGED' if supplied else 'NO_OWNED_ENVIRONMENT_CREATED')
        except BaseException:
            cleanup.update(status='FAILED_PRESERVED',error=traceback.format_exc())
            raise
        finally:
            write(evidence/'environment-teardown.json',cleanup)


def run_case(name,python,wheel,evidence,environment):
    if name not in CASES:raise ValueError(f'Unknown required scene: {name}')
    evidence=Path(evidence).resolve(strict=True)
    assert not (evidence/'worker-termination-unverified.json').exists(), 'Previous worker termination is unresolved'
    backend=environment.get('VISPY_EXPECTED_BACKEND','Vulkan')
    assert backend in ('Vulkan','Metal')
    repository=Path(environment.get('VISPY_MESH_LAYOUT_REPOSITORY',ROOT)).resolve(strict=True)
    reference=Path(environment.get('VISPY_MESH_LAYOUT_REFERENCE',ROOT/'tests/reference/mesh-layout-opengl')).resolve(strict=True)
    launch_id=uuid.uuid4().hex
    arguments=[python,'-I','-B',ROOT/'tools/mesh_layout_wheel_probe.py','--launch-id',launch_id,
        '--case',name,'--repository',repository,'--wheel',Path(wheel).resolve(),
        '--reference',reference,'--output',evidence/name,'--backend',backend]
    if environment.get('VISPY_MESH_LAYOUT_ALLOW_SOFTWARE')=='1':arguments.append('--allow-software')
    observed=run_logged(arguments,cwd=Path(python).parent,environment=environment,log=evidence/(name+'.stdout.log'))
    observed['launch_id']=launch_id
    report=evidence/name/'result.json'
    observed['report_present']=report.is_file()
    if observed['report_present']:
        observed['report_sha256']=sha(report)
        observed['worker']=json.loads(report.read_bytes())
        try:
            assert observed['worker']['launch_id']==launch_id, 'Worker launch ID differs'
            observed['actual_worker_pid']=observed['worker']['pid']
            observed['actual_worker_terminal']=worker_terminal(observed['worker'],observed['pid'])
            assert observed['actual_worker_terminal']['terminal'], 'Actual worker is not terminal'
        except BaseException:
            observed['worker_admission_error']=traceback.format_exc()
            write(evidence/'worker-termination-unverified.json',observed)
    else:
        write(evidence/'worker-termination-unverified.json',observed)
    write(evidence/(name+'.process.json'),observed)
    return observed
