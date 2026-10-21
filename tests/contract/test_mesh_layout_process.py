# SPDX-License-Identifier: AGPL-3.0-only
"""Real launcher-hop observation and native image byte-origin controls, without GPU."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from tools import mesh_layout_process as process
from tools import mesh_layout_wheel_runner as runner


def test_real_python_worker_is_bound_through_its_actual_launch_chain(tmp_path):
    launch=uuid.uuid4().hex
    helper=Path(process.__file__).resolve()
    code='import json,runpy,os; h=runpy.run_path('+repr(str(helper))+'); print(json.dumps(dict(pid=os.getpid(),launch_id='+repr(launch)+',process_stamp=h["process_stamp"]())))'
    observed=runner.run_logged([sys.executable,'-I','-B','-c',code],cwd=tmp_path,
        environment=runner.clean_environment(os.environ),log=tmp_path/'identity.log')
    worker=json.loads((tmp_path/'identity.log').read_text())
    assert observed['child_waited'] and observed['process_exit']==0 and worker['launch_id']==launch
    terminal=process.worker_terminal(worker,observed['pid'])
    assert terminal['terminal']
    assert worker['pid']==observed['pid'] or worker['process_stamp']['parent_pid']==observed['pid']


def test_self_inventory_observes_native_paths_and_excludes_before_hashing():
    records=process.native_modules((runner.ROOT,))
    assert len(records)>3 and all(Path(item['path']).is_absolute() for item in records)
    assert all(item['sha256'] is None for item in records if item['excluded_root'])
    assert any(item['sha256'] for item in records if not item['excluded_root'])


def test_repository_native_image_refuses_even_with_a_recorded_hash(tmp_path):
    package=tmp_path/'package'
    path=process.normalized_path(package/'native.pyd')
    rows=[dict(path=path,sha256='a'*64,excluded_root=True)]
    with pytest.raises(AssertionError,match='Repository native image'):
        process.assert_wheel_module_origins(rows,package,{'vispy/native.pyd':'a'*64},[path])


def test_a_vispy_layer_outside_the_wheel_package_is_not_accepted(tmp_path):
    package=tmp_path/'package'
    native=process.normalized_path(package/'native.pyd')
    external=process.normalized_path(tmp_path/'other/VkLayer_vispy_submit.dll')
    rows=[dict(path=native,sha256='a'*64,excluded_root=False),dict(path=external,sha256='b'*64,excluded_root=False)]
    with pytest.raises(AssertionError,match='not a supplied-wheel member'):
        process.assert_wheel_module_origins(rows,package,{'vispy/native.pyd':'a'*64},[native])


def test_clean_worker_environment_retains_only_declared_harness_controls():
    original=dict(PATH='system-path',VK_LAYER_PATH='repository-layer',VK_ICD_FILENAMES='other-driver',
        DAWN_TOGGLES='other',VISPY_APP_BACKEND='other',VISPY_RANDOM_RENDER_OPTION='other',
        VISPY_TEST_WHEEL='archive',VISPY_MESH_LAYOUT_REFERENCE='reference',VISPY_EXPECTED_BACKEND='Vulkan')
    cleaned=runner.clean_environment(original)
    assert cleaned['PATH']=='system-path'
    assert cleaned['VISPY_TEST_WHEEL']=='archive' and cleaned['VISPY_MESH_LAYOUT_REFERENCE']=='reference'
    assert cleaned['VISPY_EXPECTED_BACKEND']=='Vulkan'
    assert not any(name.startswith(('VK_','DAWN_')) for name in cleaned)
    assert 'VISPY_RANDOM_RENDER_OPTION' not in cleaned and 'VISPY_APP_BACKEND' not in cleaned
