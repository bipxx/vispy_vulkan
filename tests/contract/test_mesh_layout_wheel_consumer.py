# SPDX-License-Identifier: AGPL-3.0-only
"""Provider-free wheel provenance and waited-process/owned-cleanup controls."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import pytest
from tools import mesh_layout_wheel_runner as runner
from tools.mesh_layout_wheel_probe import verify_wheel_package


def test_all_wheel_package_members_are_compared_and_one_change_refuses(tmp_path):
    package=tmp_path/'vispy'
    members={'vispy/__init__.py':b'original module',
             'vispy/_licenses/LICENSE':b'AGPL text',
             'vispy/_licenses/LICENSE-BSD':b'original BSD text',
             'vispy/nested/program.py':b'program source'}
    wheel=tmp_path/'synthetic.whl'
    with zipfile.ZipFile(wheel,'w') as archive:
        for name,body in members.items():
            archive.writestr(name,body)
            destination=tmp_path/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(body)
    assert verify_wheel_package(wheel,package)=={name:hashlib.sha256(body).hexdigest() for name,body in members.items()}
    (package/'nested/program.py').write_bytes(b'changed after installation')
    with pytest.raises(AssertionError,match='Installed wheel member differs'):verify_wheel_package(wheel,package)


def test_child_is_really_waited_and_logs_cannot_be_overwritten(tmp_path):
    log=tmp_path/'child.log'
    args=[sys.executable,'-I','-B','-c','print("waited CPU child")']
    result=runner.run_logged(args,cwd=tmp_path,environment=runner.clean_environment(os.environ),log=log)
    assert result['pid']>0 and result['child_waited'] and result['process_exit']==0
    assert log.read_text().strip()=='waited CPU child'
    with pytest.raises(FileExistsError):runner.run_logged(args,cwd=tmp_path,environment=os.environ.copy(),log=log)


def test_setup_failure_cleans_only_the_new_owned_root(tmp_path,monkeypatch):
    wheel=tmp_path/'wheel.whl';wheel.write_bytes(b'not installed by this control')
    def fail(*args,**kwargs):raise RuntimeError('controlled pre-install failure')
    monkeypatch.setattr(runner.shutil,'which',lambda name:'unused-uv')
    monkeypatch.setattr(runner,'run_logged',fail)
    evidence=tmp_path/'evidence'
    with pytest.raises(RuntimeError,match='controlled pre-install'):
        with runner.installed_environment(wheel,evidence,environment={}):
            pytest.fail('Failed setup cannot yield a consumer')
    setup=json.loads((evidence/'setup.json').read_bytes())
    cleanup=json.loads((evidence/'environment-teardown.json').read_bytes())
    assert setup['status']=='FAILED_PRESERVED'
    assert cleanup['status']=='PASS_OWNED_ENVIRONMENT_TEARDOWN'
    assert cleanup['owned_root_removed'] and not Path(cleanup['owned_root']).exists()
    assert wheel.read_bytes()==b'not installed by this control'


def test_missing_uv_does_not_create_an_owned_environment(tmp_path,monkeypatch):
    wheel=tmp_path/'wheel.whl';wheel.write_bytes(b'untouched')
    monkeypatch.setattr(runner.shutil,'which',lambda name:None)
    evidence=tmp_path/'evidence'
    with pytest.raises(AssertionError,match='uv is required'):
        with runner.installed_environment(wheel,evidence,environment={}):pass
    cleanup=json.loads((evidence/'environment-teardown.json').read_bytes())
    assert not cleanup['owned_environment'] and cleanup['status']=='NO_OWNED_ENVIRONMENT_CREATED'


def test_required_axes_case_is_not_filtered_from_regressions():
    assert len(runner.CASES)==13 and 'axes_colorbar' in runner.CASES
    with pytest.raises(ValueError,match='Unknown required scene'):
        runner.run_case('omit-required-axis',None,None,None,{})


def test_an_existing_in_repository_environment_cannot_pass_preflight(tmp_path,monkeypatch):
    wheel=tmp_path/'wheel.whl';wheel.write_bytes(b'untouched')
    def identity(*args,**kwargs):
        log=kwargs['log']
        log.write_text(json.dumps(dict(prefix=str(runner.ROOT/'fake-prefix'),executable=sys.executable)),encoding='utf-8')
        return dict(pid=1,process_exit=0,child_waited=True,log=str(log),log_sha256=runner.sha(log))
    monkeypatch.setattr(runner,'run_logged',identity)
    evidence=tmp_path/'evidence'
    with pytest.raises(AssertionError,match='External consumer prefix'):
        with runner.installed_environment(wheel,evidence,environment={'VISPY_MESH_LAYOUT_PYTHON':sys.executable}):
            pytest.fail('Repository environment must not pass external origin preflight')
    assert json.loads((evidence/'setup.json').read_bytes())['status']=='FAILED_PRESERVED'
    assert json.loads((evidence/'environment-teardown.json').read_bytes())['status']=='EXISTING_ENVIRONMENT_UNCHANGED'


def test_the_axes_colorbar_scene_uses_the_smooth_line_criterion_and_other_scenes_stay_unchanged():
    # Decision D5 (W14): only axes_colorbar changes; the pinned fixture's comparison still decides every other scene.
    import numpy as np
    from tools.fixture_mesh_layout_extensions import BACKGROUND,SIZE
    from tools.mesh_layout_smooth_line import SMOOTH_LINE,compare
    assert SMOOTH_LINE=={'axes_colorbar'}
    frame=np.empty((SIZE[1],SIZE[0],4),np.uint8);frame[...]=BACKGROUND
    frame[40:60,40:120]=(240,240,240,255)
    compare('axes_colorbar',frame,frame.copy())
    edge=frame.copy();edge[40,40:120,:3]-=32
    compare('axes_colorbar',edge,frame)
    interior=frame.copy();interior[50,80,0]-=1
    with pytest.raises(AssertionError,match='interior'):
        compare('axes_colorbar',interior,frame)
    with pytest.raises(AssertionError):
        compare('grid_clipping',edge,frame)
