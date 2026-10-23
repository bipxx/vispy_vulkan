# SPDX-License-Identifier: AGPL-3.0-only
"""Failure propagation and actual full-upload/resident stage admission."""
from copy import deepcopy
import json
import math
import numpy as np
import pytest
from tools import large_volume_wheel_suite as suite
from tools.fixture_large_image import RESIDENT_ZERO


def parent(kind):
    return dict(kind=kind, cases=list(suite.CASES),
        status='PASS_ALL_'+kind.upper()+'_LARGE_VOLUMES', required_cases_without_verified_result=[],
        workers={name:dict(process_exit=0, child_waited=True, actual_worker_terminal=dict(terminal=True),
                           worker_status='PASS_'+kind.upper()+'_LARGE_VOLUME') for name in suite.CASES})


@pytest.mark.parametrize('kind', ('upstream', 'candidate'))
def test_parent_requires_all_24_terminal_cases(kind):
    suite.assert_successful_parent(parent(kind), kind)


@pytest.mark.parametrize('mutation', ('exit', 'wait', 'terminal', 'worker', 'parent', 'error', 'missing', 'cases'))
def test_other_23_successes_do_not_hide_any_process_or_parent_failure(mutation):
    result = parent('candidate'); row = result['workers'][suite.CASES[-1]]
    if mutation == 'exit': row['process_exit'] = 1
    if mutation == 'wait': row['child_waited'] = False
    if mutation == 'terminal': row['actual_worker_terminal']['terminal'] = False
    if mutation == 'worker': row['worker_status'] = 'FAILED_PRESERVED'
    if mutation == 'parent': result['status'] = 'FAILED_REQUIRED_LARGE_VOLUMES'
    if mutation == 'error': result['error'] = 'teardown error'
    if mutation == 'missing': result['required_cases_without_verified_result'] = [suite.CASES[-1]]
    if mutation == 'cases': result['cases'].pop()
    with pytest.raises(AssertionError):suite.assert_successful_parent(result, 'candidate')


def stage_metadata(update):
    delta = dict.fromkeys(RESIDENT_ZERO, 0)
    delta.update(draw_calls=1, vk_queue_submits=1, completion_waits=1, finish_calls=1,
                 vk_memory_live_allocations=0, vk_memory_live_bytes=0,
                 vk_memory_allocation_count=0,vk_memory_free_count=0,
                 vk_memory_allocated_bytes=0,vk_memory_freed_bytes=0)
    snapshot = dict(vk_memory_available=True, vk_memory_complete=True,
                    vk_memory_active_devices=1, vk_memory_tracking_devices=1,device_generation=1)
    row = dict(probe_frame=7, requested_update_bytes=0, source_texture_id=1, target_texture_id=2,
               framebuffer_id=3, commands=[['CURRENT', 0, 0], ['FRAMEBUFFER', 3, True], ['FUNC', 'glClear', 0x4100], ['DRAW', 4]],
               camera_state=dict(azimuth=30+8*math.sin(7*2*math.pi/180), elevation=20, distance=640, fov=45),
               counter_delta=delta, counter_before=snapshot, counter_after=dict(snapshot))
    if update:
        row['camera_state']['azimuth'] = 30
        row['requested_update_bytes'] = 256**3*4
        row['commands'].insert(2, ['DATA', 1, (0,0,0), dict(array=dict(
            bytes=256**3*4, dtype='<f4', shape=[256,256,256,1], sha256='1'*64))])
        delta.update(texture_uploads=1, texture_upload_bytes=256**3*4)
    return row


@pytest.mark.parametrize('update', (False, True))
def test_correct_camera_full_source_and_resident_work_are_required(tmp_path, monkeypatch, update):
    # Explicit CPU-only stage double: full-sized image quality is exercised by
    # actual graphics, not claimed by this small fault-admission control.
    monkeypatch.setattr(suite, 'assert_nonblank', lambda *args: None)
    rgba = np.zeros((1,1,4), np.uint8)
    np.savez_compressed(tmp_path/'probe7.npz', rgba=rgba)
    row = stage_metadata(update)
    (tmp_path/'probe7.json').write_text(json.dumps(row), encoding='utf-8')
    name = 'volume-256-1024-mip-'+('full' if update else 'resident')
    assert suite.assert_stage(name, 'probe7', rgba, row, 'candidate', tmp_path)['comparison']['status'] == 'passed'
    if update:
        broken = deepcopy(row); broken['commands'][2][3]['array']['bytes'] -= 4
        with pytest.raises(AssertionError):suite.assert_stage(name, 'probe7', rgba, broken, 'candidate', tmp_path)
        broken = deepcopy(row); broken['requested_update_bytes'] = 0
        with pytest.raises(AssertionError):suite.assert_stage(name, 'probe7', rgba, broken, 'candidate', tmp_path)
    else:
        broken = deepcopy(row); broken['counter_delta']['texture_uploads'] = 1
        with pytest.raises(AssertionError):suite.assert_stage(name, 'probe7', rgba, broken, 'candidate', tmp_path)
        broken = deepcopy(row); broken['camera_state']['azimuth'] = 30
        with pytest.raises(AssertionError):suite.assert_stage(name, 'probe7', rgba, broken, 'candidate', tmp_path)
    broken = deepcopy(row); broken['camera_state']['distance'] = 641
    with pytest.raises(AssertionError):suite.assert_stage(name, 'probe7', rgba, broken, 'candidate', tmp_path)


@pytest.mark.parametrize('mutation', ('data', 'size', 'create', 'delete', 'draw-before-bind', 'clear-before-bind', 'color-only-clear', 'growth', 'unavailable-memory', 'shader', 'duplicate-upload'))
def test_resident_and_full_stage_faults_are_rejected(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(suite, 'assert_nonblank', lambda *args: None)
    update = mutation in ('shader', 'duplicate-upload')
    row = stage_metadata(update); original = deepcopy(row)
    rgba = np.zeros((1,1,4), np.uint8)
    np.savez_compressed(tmp_path/'probe7.npz', rgba=rgba)
    (tmp_path/'probe7.json').write_text(json.dumps(original), encoding='utf-8')
    if mutation == 'data': row['commands'].insert(2, ['DATA', 99, 0, {}])
    if mutation == 'size': row['commands'].insert(2, ['SIZE', 1, [256,256,256,1], 'red', 'r32f'])
    if mutation == 'create': row['commands'].insert(2, ['CREATE', 99, 'Texture3D'])
    if mutation == 'delete': row['commands'].insert(2, ['DELETE', 1])
    if mutation == 'draw-before-bind': row['commands'].insert(1, ['DRAW', 4])
    if mutation == 'clear-before-bind': row['commands'].insert(1, ['FUNC', 'glClear', 0x4100])
    if mutation == 'color-only-clear': row['commands'][2][2] = 0x4000
    if mutation == 'growth': row['counter_delta']['vk_memory_live_bytes'] = 1
    if mutation == 'unavailable-memory': row['counter_before'] = dict(row['counter_before'], vk_memory_available=False)
    if mutation == 'shader': row['counter_delta']['shader_module_creations'] = 1
    if mutation == 'duplicate-upload': row['counter_delta']['texture_upload_bytes'] *= 2
    name = 'volume-256-1024-mip-'+('full' if update else 'resident')
    with pytest.raises(AssertionError):suite.assert_stage(name, 'probe7', rgba, row, 'candidate', tmp_path)


def test_full_replace_accepts_identical_size_and_legitimate_upload_conversion(tmp_path, monkeypatch):
    monkeypatch.setattr(suite, 'assert_nonblank', lambda *args: None)
    row = stage_metadata(True)
    row['commands'].insert(2, ['SIZE', 1, [256,256,256,1], 'red', 'r32f'])
    row['counter_delta']['texture_conversion_ns'] = 123
    rgba = np.zeros((1,1,4), np.uint8)
    np.savez_compressed(tmp_path/'probe7.npz', rgba=rgba)
    (tmp_path/'probe7.json').write_text(json.dumps(row), encoding='utf-8')
    assert suite.assert_stage('volume-256-1024-mip-full', 'probe7', rgba, row, 'candidate', tmp_path)['comparison']['status'] == 'passed'


def test_only_upstream_can_repeat_byte_identical_attested_legacy_cube_geometry(monkeypatch):
    monkeypatch.setattr(suite,'assert_nonblank',lambda *args:None)
    row=stage_metadata(False)
    payload=dict(array=dict(bytes=96,dtype='|V12',shape=[8,1],sha256='2'*64))
    witness={9:dict(size=[96],data=[0,payload])}
    row['commands'][2:2]=[['SIZE',9,96],['DATA',9,0,payload]]
    name='volume-256-1024-mip-resident';rgba=np.zeros((1,1,4),np.uint8)
    suite.assert_stage(name,'probe7',rgba,row,'upstream',None,legacy_geometry=witness)
    broken=deepcopy(row);broken['commands'][2][2]=97
    with pytest.raises(AssertionError):suite.assert_stage(name,'probe7',rgba,broken,'upstream',None,legacy_geometry=witness)
    with pytest.raises(AssertionError):suite.assert_stage(name,'probe7',rgba,row,'upstream',None)


@pytest.mark.parametrize('mutation',('valid-free','unexplained-decrease','negative-event','generation-change','missing-event'))
def test_live_memory_decline_requires_conserved_frees_and_same_device(tmp_path,monkeypatch,mutation):
    monkeypatch.setattr(suite,'assert_nonblank',lambda *args:None)
    row=stage_metadata(False);d=row['counter_delta']
    d.update(vk_memory_live_allocations=-1,vk_memory_live_bytes=-4194304,
             vk_memory_free_count=1,vk_memory_freed_bytes=4194304)
    rgba=np.zeros((1,1,4),np.uint8);np.savez_compressed(tmp_path/'probe7.npz',rgba=rgba)
    (tmp_path/'probe7.json').write_text(json.dumps(row),encoding='utf-8')
    if mutation=='unexplained-decrease':d['vk_memory_free_count']=0
    if mutation=='negative-event':d['vk_memory_allocation_count']=-1
    if mutation=='generation-change':row['counter_after']['device_generation']=2
    if mutation=='missing-event':del d['vk_memory_freed_bytes']
    if mutation=='valid-free':
        suite.assert_stage('volume-256-1024-mip-resident','probe7',rgba,row,'candidate',tmp_path)
    else:
        with pytest.raises(AssertionError):suite.assert_stage('volume-256-1024-mip-resident','probe7',rgba,row,'candidate',tmp_path)
