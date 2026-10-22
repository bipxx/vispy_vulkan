# SPDX-License-Identifier: AGPL-3.0-only
"""Controller joins on actual prior diagnostics; these are not five new pairs."""
import copy
import json
import os
import math
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace

import pytest
from tools import volume_benchmark_pairs as pairs

ROOT = pairs.bench.ROOT
PACKET = ROOT / 'tests/reference/volume-benchmark-diagnostics'
NAME = 'volume-256-1024-mip-resident'
QUALITY = ROOT / 'compat/scientific-admissions/volume-native58-cp312-numpy246-v5'
HARDWARE = ROOT / 'compat/hardware/windows-rtx4090-61088-pyqt6.json'


@pytest.fixture(autouse=True)
def isolated_hold(monkeypatch, tmp_path):
    monkeypatch.setattr(pairs, 'GLOBAL_HOLD', tmp_path/'global-hold.json')


@pytest.fixture(scope='module')
def actual():
    assert pairs.bench.sha256(PACKET / 'manifest.json') == 'd16dfa08fe376215cc421a1e6c22f609ce12d1a3306753652664d60b38cc74c5'
    manifest = pairs.read(PACKET / 'manifest.json')
    assert manifest['scope'].startswith('Actual prior one-run-per-role')
    assert manifest['paired_performance_qualified'] is False
    for relative, digest in manifest['files'].items():
        assert pairs.bench.sha256(PACKET / relative) == digest
    return pairs.adapter.load_admission(QUALITY / (NAME + '.json'), NAME)


def process(kind):
    parent = pairs.read(PACKET / kind / 'parent.json')
    return dict(**parent['process'], launch_id=parent['worker']['launch_id'],
        actual_worker_terminal=parent['actual_worker_terminal'], worker_sha256=parent['worker_sha256'])


@pytest.mark.parametrize('kind', ['upstream', 'candidate'])
def test_actual_raw_diagnostics_revalidate_complete_samples_and_counter_snapshots(actual, kind):
    run, validation = pairs.verify_run(PACKET / kind, kind, NAME, 0, actual, process(kind), warmup=100, frames=1000)
    assert validation['status'] == 'verified'
    assert validation['samples']['raw_completion_count'] == 1100
    assert validation['samples']['gpu_map_count'] == 1100
    assert validation['measured_work']['status'] == 'passed'
    assert pairs.adapter.OVERHEAD_GAP in run['instrumentation_gaps']


def test_actual_capture_pairs_recompute_full_rgba_and_visible_changes(actual):
    original, candidate = (pairs.read(PACKET / kind / 'run.json') for kind in ('upstream', 'candidate'))
    quality = pairs.compare_pair(NAME, PACKET / 'upstream', PACKET / 'candidate', original, candidate)
    assert quality['status'] == 'passed' and len(quality['comparisons']) == 3
    assert max(row['interior_max_abs_u8'] for row in quality['comparisons']) == 1
    assert len(quality['changed_frame_checks']) == 2
    hardware = pairs.bench.validate_hardware(pairs.read(HARDWARE), dict(upstream=[original], candidate=[candidate]))
    assert hardware['status'] == 'passed', hardware


@pytest.mark.parametrize('mutation', ['exit', 'wait', 'terminal', 'timeout', 'nonce', 'receipt', 'pid', 'index', 'frames'])
def test_missing_or_mismatched_process_and_request_joins_fail(actual, mutation):
    receipt = process('upstream')
    index, frames = 0, 1000
    if mutation == 'exit': receipt['process_exit'] = 1
    if mutation == 'wait': receipt['child_waited'] = False
    if mutation == 'terminal': receipt['actual_worker_terminal']['terminal'] = False
    if mutation == 'timeout': receipt['timed_out'] = True
    if mutation == 'nonce': receipt['launch_id'] = 'different'
    if mutation == 'receipt': receipt['worker_sha256'] = '0' * 64
    if mutation == 'pid': receipt['pid'] = 1
    if mutation == 'index': index = 1
    if mutation == 'frames': frames = 1001
    with pytest.raises(ValueError):
        pairs.verify_run(PACKET / 'upstream', 'upstream', NAME, index, actual, receipt, warmup=100, frames=frames)


@pytest.mark.parametrize('mutation', ['duplicate', 'unpresented', 'phase', 'cpu', 'latency', 'python_delta', 'counter_delta', 'pacing', 'gpu_interval'])
def test_invalid_original_samples_fail_after_hash_join(monkeypatch, mutation):
    run = pairs.read(PACKET / 'upstream/run.json')
    original = pairs.read
    def changed(path):
        data = original(path)
        if mutation == 'duplicate' and Path(path).name == 'observed-samples.json': data[1] = copy.deepcopy(data[0])
        if mutation == 'unpresented' and Path(path).name == 'observed-samples.json': data[0]['presented'] = False
        if mutation == 'phase' and Path(path).name == 'issued-frames.json': data['0'] = 'measured'
        if mutation == 'cpu' and Path(path).name == 'samples.json': data[0]['python_cpu']['python_draw_calls'] = 0
        if mutation == 'pacing' and Path(path).name == 'observed-samples.json': data[0]['presentation_pacing']['interval'] = 1
        if mutation == 'gpu_interval' and Path(path).name == 'observed-opengl-timings.json': data[0]['elapsed_ns'] += 1
        return data
    if mutation == 'latency': run['latency']['median_ms'] += 1
    if mutation == 'python_delta': run['python_counters_before']['python_update_ns'] += 1
    if mutation == 'counter_delta': run['counter_delta']['gl_buffer_upload_calls'] += 1
    monkeypatch.setattr(pairs, 'read', changed)
    with pytest.raises((ValueError, RuntimeError)):
        pairs.validate_samples(PACKET / 'upstream', run, 'upstream')


@pytest.mark.parametrize('mutation', ['ownership', 'gpu_map', 'allocation', 'counter_delta'])
def test_invalid_native_paint_gpu_and_allocation_proofs_fail(monkeypatch, mutation):
    run = pairs.read(PACKET / 'candidate/run.json')
    original = pairs.read
    def changed(path):
        data = original(path)
        if mutation == 'ownership' and Path(path).name == 'observed-samples.json': data[0]['ownership_closed'] = False
        if mutation == 'gpu_map' and Path(path).name == 'observed-gpu-timings.json': data[0]['pass_sum_ns'] += 1
        return data
    if mutation == 'allocation': run['measured_allocation_window'] = {}
    if mutation == 'counter_delta': run['counter_delta']['buffer_uploads'] += 1
    monkeypatch.setattr(pairs, 'read', changed)
    with pytest.raises((ValueError, RuntimeError, KeyError)):
        pairs.validate_samples(PACKET / 'candidate', run, 'candidate')


def test_artifact_changes_and_nonleaf_names_fail(tmp_path):
    file = tmp_path / 'samples.json'; file.write_text('[]')
    digest = pairs.bench.sha256(file)
    assert pairs.leaf(tmp_path, dict(file=file.name, sha256=digest)) == file.resolve()
    file.write_text('[1]')
    with pytest.raises(ValueError, match='hash differs'): pairs.leaf(tmp_path, dict(file=file.name, sha256=digest))
    with pytest.raises(ValueError, match='leaf'): pairs.leaf(tmp_path, dict(file='../samples.json', sha256=digest))


def test_alternating_five_pair_schedule_is_fixed():
    assert pairs.bench.alternating_schedule(5) == [(0,'upstream'),(0,'candidate'),(1,'candidate'),(1,'upstream'),
        (2,'upstream'),(2,'candidate'),(3,'candidate'),(3,'upstream'),(4,'upstream'),(4,'candidate')]


@pytest.mark.parametrize('field,value', [('warmup',99),('frames',999),('repetitions',4),('queue_depth',4),('timeout',float('nan'))])
def test_preregistered_counts_and_deadlines_cannot_be_weakened(tmp_path, field, value):
    options = SimpleNamespace(warmup=100, frames=1000, repetitions=5, queue_depth=3,
        timeout=600, worker_timeout=3600, workloads=[NAME], output=tmp_path/'new')
    setattr(options,field,value)
    with pytest.raises(ValueError): pairs.preflight(options)


def test_actual_cpu_child_wait_and_nonce_join_remove_only_owned_cwd(tmp_path):
    directory = tmp_path/'worker'; evidence = tmp_path/'environment'; evidence.mkdir()
    program = ("import sys,json,os;from pathlib import Path;sys.path.insert(0,sys.argv[3]);"
        "from tools.mesh_layout_process import process_stamp;d=Path(sys.argv[1]);d.mkdir();"
        "r=dict(launch_id=sys.argv[2],pid=os.getpid(),process_stamp=process_stamp(),process_exit=0);"
        "[(d/n).write_text(json.dumps(r)) for n in ('worker-start.json','worker.json')]")
    result = pairs.launch_worker([sys.executable,'-I','-B','-c',program,str(directory),'test-nonce',str(ROOT)],
        directory=directory, environment=dict(os.environ), environment_evidence=evidence, timeout=30, launch_id='test-nonce')
    assert result['child_waited'] and result['actual_worker_terminal']['terminal'] and result['process_exit']==0
    assert result['cwd_removed'] and not Path(result['cwd']).exists()
    assert not (evidence/'worker-termination-unverified.json').exists()


def test_unverified_timeout_preserves_owned_cwd_and_environment_marker(tmp_path, monkeypatch):
    directory=tmp_path/'worker';evidence=tmp_path/'environment';evidence.mkdir()
    class FakeProcess:
        pid=12345
        def __init__(self,*args,**kwargs):
            directory.mkdir();(directory/'worker-start.json').write_text(json.dumps(dict(launch_id='nonce',pid=12346,process_stamp={})))
            self.waits=0
        def wait(self,timeout):
            self.waits+=1
            if self.waits==1:raise pairs.subprocess.TimeoutExpired('fake',timeout)
            return 1
        def terminate(self):pass
        def poll(self):return 1
    monkeypatch.setattr(pairs.subprocess,'Popen',FakeProcess)
    monkeypatch.setattr(pairs,'worker_terminal',lambda worker,pid:dict(terminal=False,mode='simulated_unverified'))
    ticks=iter([0,0,2]);monkeypatch.setattr(pairs.time,'monotonic',lambda:next(ticks))
    try:
        with pytest.raises(ValueError,match='termination or deadline'):
            pairs.launch_worker(['fake'],directory=directory,environment={},environment_evidence=evidence,timeout=1,launch_id='nonce')
        record=pairs.read(directory.with_suffix('.process.json'));owner=Path(record['cwd'])
        assert record['timed_out'] and owner.exists() and not record['cwd_removed']
        assert (evidence/'worker-termination-unverified.json').exists()
        assert pairs.GLOBAL_HOLD.exists()
        with pytest.raises(ValueError,match='every controller invocation'):
            pairs.launch_worker(['fake'],directory=tmp_path/'different-output',environment={},environment_evidence=tmp_path/'other-env',timeout=1,launch_id='new')
    finally:
        # FakeProcess created no child: this test owns the retained scratch.
        if 'owner' in locals() and owner.exists():
            assert owner.parent==Path(tempfile.gettempdir()).resolve() and owner.name.startswith('vispy-volume-pair-worker-')
            shutil.rmtree(owner)


def test_previous_unverified_worker_prevents_any_new_process(tmp_path, monkeypatch):
    evidence=tmp_path/'environment';evidence.mkdir();(evidence/'worker-termination-unverified.json').write_text('{}')
    def forbidden(*args,**kwargs):raise AssertionError('No process should start')
    monkeypatch.setattr(pairs.subprocess,'Popen',forbidden)
    with pytest.raises(ValueError,match='Previous actual worker'):
        pairs.launch_worker(['unused'],directory=tmp_path/'worker',environment={},environment_evidence=evidence,timeout=1,launch_id='nonce')
    assert not (tmp_path/'worker').exists()


@pytest.mark.parametrize('direction',[float('inf'),float('-inf')])
@pytest.mark.parametrize('field,ulps,accepted', [('stdev_ms',1,True),('stdev_ms',2,False),('median_ms',1,False),('p95_ms',1,False)])
def test_only_descriptive_stdev_allows_one_ulp_between_python_statistics_versions(field, ulps, accepted, direction):
    run=pairs.read(PACKET/'upstream/run.json')
    samples=pairs.read(PACKET/'upstream/samples.json')
    recomputed=pairs.bench.metrics([sample['completion_latency_ns'] for sample in samples])
    run['latency'][field]=recomputed[field]
    for _ in range(ulps):run['latency'][field]=math.nextafter(run['latency'][field],direction)
    if accepted:
        result=pairs.validate_samples(PACKET/'upstream',run,'upstream')
        assert result['statistics_recomputed']
    else:
        with pytest.raises(ValueError):pairs.validate_samples(PACKET/'upstream',run,'upstream')


def test_interrupt_is_preserved_after_owned_launcher_wait(tmp_path, monkeypatch):
    directory=tmp_path/'worker';evidence=tmp_path/'env';evidence.mkdir()
    class Interrupted:
        pid=12345
        def __init__(self,*args,**kwargs):
            self.waits=0;directory.mkdir();(directory/'worker-start.json').write_text(json.dumps(dict(launch_id='nonce',pid=12345,process_stamp={})))
        def wait(self,timeout):
            self.waits+=1
            if self.waits==1:raise KeyboardInterrupt
            return 1
        def poll(self):return None
        def terminate(self):pass
    monkeypatch.setattr(pairs.subprocess,'Popen',Interrupted)
    monkeypatch.setattr(pairs,'worker_terminal',lambda worker,pid:dict(terminal=True,mode='simulated_wait'))
    with pytest.raises(KeyboardInterrupt):
        pairs.launch_worker(['fake'],directory=directory,environment={},environment_evidence=evidence,timeout=30,launch_id='nonce')
    record=pairs.read(directory.with_suffix('.process.json'))
    assert record['interrupted'] and record['child_waited'] and record['cwd_removed']
