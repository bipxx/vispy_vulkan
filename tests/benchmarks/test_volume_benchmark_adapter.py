# SPDX-License-Identifier: AGPL-3.0-only
"""Actual saved geometry plus fault tests; synthetic rows are not timing proof."""
import copy
import ast
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

from tools import volume_benchmark_adapter as adapter
from tools import volume_benchmark_geometry as geometry


NAME = adapter.suite.CASES[0]
PACKET = adapter.benchmark.ROOT / 'compat/scientific-admissions/volume-native58-cp312-numpy246-v5'


def saved_observation(name=NAME):
    folder = adapter.suite.load_reference(adapter.science.ORIGINAL_ROOT, adapter.science.LARGE_ORIGINAL_SHA, name)
    initial = adapter.science.read(folder / 'initial.json')
    repeat = adapter.science.read(folder / 'repeat.json')
    expected = geometry.reference_geometry(initial)
    ledger = geometry.GeometryObservation(expected, frame_limit=102)
    ledger.observe(initial['commands'], saved=True)
    ledger.bind(initial['geometry_ids'])
    ledger.active = True
    ledger.begin_window(100, 2)
    ledger.observe(repeat['commands'], 100, saved=True)
    ledger.observe(repeat['commands'], 101, saved=True)
    ledger.end_window()
    return expected, ledger


def counters():
    values = dict.fromkeys(adapter.benchmark.OPENGL_RESIDENT_ZERO + adapter.benchmark._work.OPENGL_NO_WAIT, 0)
    values.update(gl_buffer_upload_calls=4, gl_buffer_upload_bytes=304)
    return values


@pytest.fixture(scope='module')
def saved():
    return saved_observation()


@pytest.mark.parametrize('name', adapter.suite.CASES)
def test_all_actual_original_cube_streams_join_the_raw_upload_totals(name):
    expected, ledger = saved_observation(name)
    result = geometry.validate_geometry(ledger.snapshot(), expected, first_frame=100,
                                       frame_count=2, raw_counters=counters())
    assert result['status'] == 'passed', result
    assert result['uploads'] == 4 and result['bytes'] == 304


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'offset', 'payload', 'dtype', 'shape',
    'size', 'delete', 'create', 'unknown_id', 'unowned', 'errors', 'reference', 'binding'])
def test_any_changed_or_unaccounted_geometry_fails(saved, mutation):
    expected, ledger = saved
    record = ledger.snapshot()
    rows = record['frames']['100']
    if mutation == 'missing': record['frames'].pop('100')
    if mutation == 'extra': rows.append(copy.deepcopy(rows[1]))
    if mutation == 'offset': rows[1][2] = 4
    if mutation == 'payload': rows[1][3]['array']['sha256'] = '0' * 64
    if mutation == 'dtype': rows[1][3]['array']['dtype'] = '<u4'
    if mutation == 'shape': rows[1][3]['array']['shape'] = [24]
    if mutation == 'size': rows[0][2] = 100
    if mutation == 'delete': rows.append(['DELETE', rows[0][1]])
    if mutation == 'create': rows.insert(0, ['CREATE', 500, 'VertexBuffer'])
    if mutation == 'unknown_id': rows[1][1] = 500
    if mutation == 'unowned': record['unattributed'].append(rows[1])
    if mutation == 'errors': record['errors'].append('incomplete observation')
    if mutation == 'reference': record['expected']['VertexBuffer']['size'] = 100
    if mutation == 'binding': record['geometry_ids']['VertexBuffer'] = 500
    assert geometry.validate_geometry(record, expected, first_frame=100, frame_count=2,
                                     raw_counters=counters())['status'] != 'passed'


@pytest.mark.parametrize('key,value', [('gl_buffer_upload_calls', 5), ('gl_buffer_upload_bytes', 305),
    ('gl_buffer_upload_calls', True), ('gl_buffer_upload_bytes', None)])
def test_raw_upload_counters_must_account_for_exactly_the_attested_stream(saved, key, value):
    expected, ledger = saved
    raw = counters(); raw[key] = value
    assert geometry.validate_geometry(ledger.snapshot(), expected, first_frame=100,
                                     frame_count=2, raw_counters=raw)['status'] != 'passed'


def test_allowance_retains_raw_counts_and_only_removes_the_two_zero_requirements(saved):
    expected, ledger = saved
    run = dict(workload=asdict(adapter.benchmark.CATALOG[NAME]), warmup_frames=100,
        measured_frames=2, counter_delta=counters(), original_geometry=ledger.snapshot())
    original = copy.deepcopy(run)
    assert geometry.GENERIC_WORK_GATE(run, 'upstream')['status'] == 'failed'
    result = geometry.measured_work_gate(run, 'upstream', expected=expected)
    assert result['status'] == 'passed'
    assert set(result['allowed_observed_work']) == set(geometry.BUFFER_COUNTERS)
    assert run == original
    run['counter_delta']['gl_readback_calls'] = 1
    assert geometry.measured_work_gate(run, 'upstream', expected=expected)['status'] == 'failed'


def test_other_workloads_and_candidate_never_get_the_original_allowance(saved):
    expected, ledger = saved
    run = dict(workload=dict(family='image'), counter_delta=counters())
    assert geometry.measured_work_gate(run, 'upstream', expected=expected)['status'] == 'failed'
    native = dict.fromkeys(adapter.benchmark.NATIVE_RESIDENT_ZERO + adapter.benchmark._work.NATIVE_NO_WAIT, 0)
    native['buffer_uploads'] = 1
    assert geometry.measured_work_gate(dict(workload=dict(family='volume'), counter_delta=native),
                                       'candidate', expected=expected)['status'] == 'failed'


def test_full_update_still_requires_the_exact_original_cube_proof():
    run = dict(workload=dict(family='volume'), counter_delta=counters())
    assert geometry.GENERIC_WORK_GATE(run, 'upstream', update=True)['status'] == 'passed'
    assert geometry.measured_work_gate(run, 'upstream', update=True)['status'] == 'unproven'


def test_live_parser_hook_passes_the_identical_batch_and_restores_method():
    calls = []
    original = lambda batch: calls.append(batch) or 'executed'
    owner = SimpleNamespace(parse=original)
    canvas = SimpleNamespace(context=SimpleNamespace(shared=SimpleNamespace(parser=owner)))
    ledger = geometry.GeometryObservation({}, frame_limit=2)
    hook = adapter.ParserObservation(canvas, ledger)
    data = np.zeros(8, dtype=[('a_position', '<f4', (3,))])
    batch = [['CREATE', 1, 'VertexBuffer'], ['SIZE', 1, 96], ['DATA', 1, 0, data]]
    assert owner.parse(batch) == 'executed'
    assert calls == [batch] and calls[0] is batch
    assert ledger.snapshot()['cold'][2][3]['array']['bytes'] == 96
    hook.close()
    assert owner.parse is original


def test_live_hook_does_not_replace_a_renderer_exception():
    def fail(batch): raise RuntimeError('renderer failure')
    owner = SimpleNamespace(parse=fail)
    canvas = SimpleNamespace(context=SimpleNamespace(shared=SimpleNamespace(parser=owner)))
    hook = adapter.ParserObservation(canvas, geometry.GeometryObservation({}, frame_limit=1))
    with pytest.raises(RuntimeError, match='renderer failure'): owner.parse([])
    hook.close()
    assert owner.parse is fail


def test_observer_rejects_saved_dict_payloads_in_live_mode():
    ledger = geometry.GeometryObservation({}, frame_limit=1)
    ledger.observe([['CREATE', 1, 'VertexBuffer'], ['DATA', 1, 0, {'array': {}}]])
    assert ledger.errors


def test_worker_context_restores_all_hooks_after_failure(monkeypatch, saved):
    monkeypatch.setattr(adapter, 'expected_geometry', lambda name: saved[0])
    options = SimpleNamespace(workload=NAME, warmup=100, frames=1000)
    names = ('package_provenance', 'build_scene', 'PythonFrameTelemetry', 'measured_work_gate')
    original = {name: getattr(adapter.benchmark, name) for name in names}
    with pytest.raises(RuntimeError, match='injected worker failure'):
        with adapter.worker_adapter(options, None, {}):
            assert all(getattr(adapter.benchmark, name) is not value for name, value in original.items())
            raise RuntimeError('injected worker failure')
    assert all(getattr(adapter.benchmark, name) is value for name, value in original.items())


def test_completed_scientific_set_is_required_before_worker():
    record = adapter.load_admission(PACKET / (NAME + '.json'), NAME)
    assert record['workload'] == NAME
    with pytest.raises(ValueError, match='Registered volume admission'):
        adapter.load_admission(PACKET / (NAME + '.json'), adapter.suite.CASES[-1])


def test_frozen_producers_still_match_the_actual_original_reference():
    adapter.suite.load_reference(adapter.science.ORIGINAL_ROOT, adapter.science.LARGE_ORIGINAL_SHA, NAME)
    assert 'vispy' not in __import__('sys').modules


@pytest.mark.parametrize('kind', ['upstream', 'candidate'])
@pytest.mark.parametrize('mutation', ['none', 'role', 'wheel', 'native', 'source', 'workload', 'device'])
def test_saved_run_revalidation_checks_actual_artifact_workload_and_device(saved, kind, mutation):
    expected, ledger = saved
    admission = adapter.science.read(PACKET / (NAME + '.json'))
    artifact = admission['artifacts'][kind]
    original = adapter.science.read(adapter.science.ORIGINAL_ROOT / NAME / 'result.json')
    candidate = adapter.science.read(adapter.science.LARGE_ROOT / NAME / 'result.json')
    native = dict.fromkeys(adapter.benchmark.NATIVE_RESIDENT_ZERO + adapter.benchmark._work.NATIVE_NO_WAIT, 0)
    run = dict(workload=asdict(adapter.benchmark.CATALOG[NAME]), warmup_frames=100, measured_frames=2,
        data_sha256=admission['benchmark_data_sha256'], original_geometry=ledger.snapshot(),
        renderer=copy.deepcopy(original['renderer'] if kind == 'upstream' else candidate['device']),
        counter_delta=counters() if kind == 'upstream' else native,
        provenance=dict(kind=kind, wheel_sha256=artifact['wheel_sha256'],
            installed_package_sha256=copy.deepcopy(artifact['installed_package_sha256']),
            python='3.12.8', versions=dict(numpy='2.4.6'), adapter_sources_sha256=adapter.sources()))
    provenance = run['provenance']
    role = kind
    if mutation == 'role': role = 'candidate' if kind == 'upstream' else 'upstream'
    if mutation == 'wheel': provenance['wheel_sha256'] = '0' * 64
    if mutation == 'native':
        key = next(key for key in provenance['installed_package_sha256'] if key.endswith('.pyd'))
        provenance['installed_package_sha256'][key] = '0' * 64
    if mutation == 'source': provenance.pop('adapter_sources_sha256')
    if mutation == 'workload': run['workload']['viewport'] = [8, 8]
    if mutation == 'device': run['renderer'] = dict(software=True)
    result = adapter.measured_work_gate(run, role, admission=admission, expected=expected)
    assert result['status'] == ('passed' if mutation == 'none' else 'unproven'), result


def live_cube_arrays(side):
    """Execute ONLY the pinned original pure array/preparation method bodies."""
    root = adapter.benchmark.ROOT
    pins = adapter.science.read(root / 'compat/upstream_manifest.json')['files']
    bodies = {}
    for relative, method in [('visuals/volume.py', '_create_vertex_data'), ('gloo/buffer.py', '_prepare_data')]:
        source = root / 'third_party/parity/vispy/vispy' / relative
        assert adapter.benchmark.sha256(source) == pins[relative]
        tree = ast.parse(source.read_text(encoding='utf-8'))
        if relative == 'gloo/buffer.py':
            tree = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'VertexBuffer')
        node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == method)
        namespace = dict(np=np)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
        bodies[method] = namespace[method]
    class Buffer:
        def __init__(self, vertex=False): self.vertex = vertex; self._last_dim = 3
        def set_data(self, data):
            self.data = bodies['_prepare_data'](self, data) if self.vertex else data
    vertex, index = Buffer(True), Buffer()
    bodies['_create_vertex_data'](SimpleNamespace(_vol_shape=(side, side, side), _vertices=vertex, _index_buffer=index))
    return vertex.data, index.data


@pytest.mark.parametrize('side', [256, 512])
def test_actual_original_array_methods_reproduce_pinned_live_payloads(side):
    expected = adapter.expected_geometry(f'volume-{side}-1024-mip-resident')
    for kind, array in zip(geometry.BUFFER_TYPES, live_cube_arrays(side)):
        assert geometry.array_record(array) == expected[kind]['payload']


def test_live_capture_defers_hashing_and_rejects_large_arrays_before_copy(monkeypatch):
    array = np.arange(24, dtype=np.float32).reshape(8, 3)
    expected = geometry.array_record(array)
    def forbidden(*args, **kwargs): raise RuntimeError('hashing must be deferred')
    with monkeypatch.context() as patch:
        patch.setattr(geometry.hashlib, 'sha256', forbidden)
        captured = geometry.capture_payload(array)
        with pytest.raises(ValueError, match='Unexpected geometry payload size'):
            geometry.capture_payload(np.zeros((100, 100), np.float32)[::2])
    array.fill(0)
    assert geometry.array_record(captured) == expected


def test_unbounded_observer_overhead_cannot_become_a_release_pass(monkeypatch, saved):
    monkeypatch.setattr(adapter, 'expected_geometry', lambda name: saved[0])
    monkeypatch.setattr(adapter.benchmark, 'release_gate', lambda *args, **kwargs: dict(status='passed', speedup=1.21))
    result = adapter.release_gate([], [], admission=dict(workload=NAME), quality_passed=True, same_hardware=True)
    assert result['status'] == 'unproven' and adapter.OVERHEAD_GAP in result['reasons']
    assert result['observed_release_metrics']['speedup'] == 1.21


def test_pre_warm_expose_is_retained_outside_measured_window(saved):
    expected, previous = saved
    record = previous.snapshot()
    record['unattributed'] = copy.deepcopy(record['frames']['100'])
    record['measured_window']['unattributed_before'] = 4
    record['measured_window']['unattributed_after'] = 4
    assert geometry.validate_geometry(record, expected, first_frame=100, frame_count=2,
                                     raw_counters=counters())['status'] == 'passed'
    record['measured_window']['unattributed_before'] = 0
    assert geometry.validate_geometry(record, expected, first_frame=100, frame_count=2,
                                     raw_counters=counters())['status'] != 'passed'
