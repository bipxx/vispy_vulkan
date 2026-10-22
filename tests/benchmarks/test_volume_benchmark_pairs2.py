# SPDX-License-Identifier: AGPL-3.0-only
"""Observer-free controller wiring; these checks do not qualify GPU timings."""
from pathlib import Path
import copy
import json

import pytest

from tools import volume_benchmark_pairs2 as pairs


def test_controller_restores_all_bindings_after_failure():
    legacy = pairs.legacy
    before = legacy.adapter, legacy.launch_worker, legacy.sources, legacy.verify_run
    with pytest.raises(RuntimeError, match='intentional'):
        with pairs.controller():
            assert legacy.adapter is not before[0]
            assert legacy.sources is pairs.sources
            # Existing worker receipt checks keep their original source epoch.
            assert legacy.adapter.sources() == before[0].sources()
            raise RuntimeError('intentional')
    assert (legacy.adapter, legacy.launch_worker, legacy.sources, legacy.verify_run) == before


def test_launch_replaces_only_worker_entry_point(monkeypatch, tmp_path):
    legacy = pairs.legacy
    captured = {}
    def launch(arguments, **kwargs):
        captured.update(arguments=arguments, kwargs=kwargs)
        return 'waited'
    monkeypatch.setattr(legacy, 'launch_worker', launch)
    arguments = ['python', '-I', '-B', legacy.bench.ROOT/'tools/volume_benchmark_adapter.py', '--frames', '1000']
    settings = dict(directory=tmp_path, environment='environment', environment_evidence='evidence', timeout=900, launch_id='nonce')
    with pairs.controller():
        assert legacy.launch_worker(arguments, **settings) == 'waited'
    assert captured['arguments'] == arguments[:3] + [legacy.bench.ROOT/'tools/volume_benchmark_adapter2.py'] + arguments[4:]
    assert captured['kwargs'] == settings
    assert arguments[3] == legacy.bench.ROOT/'tools/volume_benchmark_adapter.py'


def test_unexpected_launch_target_is_rejected_before_launch(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail('unexpected worker was launched')
    monkeypatch.setattr(pairs.legacy, 'launch_worker', forbidden)
    with pairs.controller(), pytest.raises(ValueError, match='Unexpected legacy worker'):
        pairs.legacy.launch_worker(['python', '-I', '-B', Path('other.py')], directory=tmp_path)


def test_directory_binding_is_per_run_and_json_portable(monkeypatch, tmp_path):
    observed = []
    def gate(run, kind, **kwargs):
        observed.append((run['_observer_free_directory'], kind, kwargs))
        return {'status': 'passed'}
    monkeypatch.setattr(pairs.adapter, 'measured_work_gate', gate)
    run = {'instrumentation_gaps': ['scanout', 'allocator']}
    for directory in (tmp_path/'first', tmp_path/'second'):
        with pairs.controller(directory):
            assert pairs.legacy.adapter.measured_work_gate(run, 'candidate', admission={'workload': 'case'})['status'] == 'passed'
    assert [row[0] for row in observed] == [str((tmp_path/name).resolve()) for name in ('first', 'second')]
    assert run['instrumentation_gaps'] == ['scanout', 'allocator']


def test_missing_directory_fails_closed():
    with pairs.controller(), pytest.raises(ValueError, match='directory missing'):
        pairs.legacy.adapter.measured_work_gate({}, 'upstream', admission={})


def test_release_uses_new_work_gate_without_removing_gaps(monkeypatch):
    bench = pairs.legacy.bench
    name = 'volume-256-1024-mip-resident'
    admission = {'workload': name}
    run = {'instrumentation_gaps': ['scanout', 'allocator', 'old observer gap']}
    before = bench.measured_work_gate
    def measured(value, kind, **kwargs):
        assert value is run and kwargs == dict(admission=admission, update=False)
        return {'status': 'passed'}
    def release(originals, candidates, **kwargs):
        assert originals == [run] and candidates == [run]
        assert kwargs == dict(update=False, quality_passed=True, same_hardware=True)
        assert bench.measured_work_gate(run, 'upstream')['status'] == 'passed'
        assert run['instrumentation_gaps'] == ['scanout', 'allocator', 'old observer gap']
        raise RuntimeError('intentional release failure')
    monkeypatch.setattr(pairs.adapter, 'measured_work_gate', measured)
    monkeypatch.setattr(bench, 'release_gate', release)
    with pytest.raises(RuntimeError, match='intentional release failure'):
        pairs.release_gate([run], [run], admission=admission, quality_passed=True, same_hardware=True)
    assert bench.measured_work_gate is before


def test_source_closure_includes_both_controller_versions():
    sources = pairs.sources()
    assert len(sources) == 26
    for name in ('tools/volume_benchmark_pairs.py', 'tools/volume_benchmark_pairs2.py'):
        assert sources[name] == pairs.legacy.bench.sha256(pairs.legacy.bench.ROOT/name)


@pytest.mark.parametrize('gap', ['input-to-visible scanout measurement', 'complete driver/allocator allocation peak accounting', 'old observer gap'])
def test_real_frozen_release_gate_cannot_pass_with_retained_gap(monkeypatch, gap):
    root = pairs.legacy.bench.ROOT/'tests/reference/volume-benchmark-diagnostics'
    originals = [json.loads((root/'upstream/run.json').read_bytes()) for _ in range(5)]
    candidates = [json.loads((root/'candidate/run.json').read_bytes()) for _ in range(5)]
    raw = json.loads((root/'upstream/observed-samples.json').read_bytes())
    for kind, runs in (('upstream', originals), ('candidate', candidates)):
        for index, run in enumerate(runs):
            run['run_index'] = index
            run['instrumentation_gaps'] = []
            run['latency'] = dict(count=1000, median_ms=10 if kind=='upstream' else 5, p95_ms=12 if kind=='upstream' else 6)
            if kind == 'upstream':run['_release_upstream_completed_samples'] = raw
    monkeypatch.setattr(pairs.adapter, 'measured_work_gate', lambda *args, **kwargs: dict(status='passed', reasons=[]))
    settings = dict(admission={'workload': 'volume-256-1024-mip-resident'}, quality_passed=True, same_hardware=True)
    assert pairs.release_gate(originals, candidates, **settings)['status'] == 'passed'
    originals[0]['instrumentation_gaps'] = [gap]
    result = pairs.release_gate(originals, candidates, **settings)
    assert result['status'] == 'unproven'
    assert result['reasons'] == ['required performance instrumentation remains incomplete']
    assert originals[0]['instrumentation_gaps'] == [gap]


@pytest.mark.parametrize('mismatch', [False, True])
def test_verify_binds_actual_directory_and_both_new_worker_maps(monkeypatch, tmp_path, mismatch):
    held = pairs.adapter.sources()
    for name in ('worker-start.json', 'worker.json'):
        value = copy.deepcopy(held)
        if mismatch and name == 'worker.json':value['tools/volume_benchmark_adapter2.py'] = '0'*64
        (tmp_path/name).write_text(json.dumps(dict(observer_free_sources_sha256=value)))
    def verify(directory, *args, **kwargs):
        assert directory == tmp_path
        run = {}
        pairs.legacy.adapter.measured_work_gate(run, 'upstream', admission={})
        assert run['_observer_free_directory'] == str(tmp_path.resolve())
        return 'verified'
    monkeypatch.setattr(pairs.legacy, 'verify_run', verify)
    monkeypatch.setattr(pairs.adapter, 'measured_work_gate', lambda *args, **kwargs: dict(status='passed'))
    if mismatch:
        with pytest.raises(ValueError, match='start/finish source identity differs'):pairs.verify_run(tmp_path)
    else:assert pairs.verify_run(tmp_path) == 'verified'
