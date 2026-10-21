"""CPU contracts for benchmark math and admission; these acquire no GPU."""

from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

SCRIPT = Path(os.environ.get('VISPY_BENCHMARK_SCRIPT', str(Path(__file__).resolve().parents[2] / "tools/benchmark_frames.py")))
SPEC = importlib.util.spec_from_file_location("benchmark_frames_contract", SCRIPT)
BENCH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BENCH
SPEC.loader.exec_module(BENCH)


def teardown_module():
    forbidden=[name for name in sys.modules if name=='vispy' or name.startswith(('vispy.','PyQt','PySide','OpenGL','qtpy'))]
    assert not forbidden, 'CPU metrics tests imported a renderer/provider: '+repr(forbidden)


def runs(median=10.0, p95=12.0):
    return [{"status": "measured", "warmup_frames": 100, "measured_frames": 1000,
             "run_index": index, "vsync": False, "surface": {"pacing_disabled": True},
             "boundary": {"presented": True, "gpu_completion": True},
             "latency": {"count": 1000, "median_ms": median, "p95_ms": p95},
             "counter_delta": dict.fromkeys(_WORK_ZERO_FIELDS, 0),
             "_release_upstream_completed_samples": _cpu_completed_pacing_samples(1100)}
            for index in range(5)]


def _cpu_pacing_receipt(frame):
    # Explicit CPU-only raw ownership evidence for pure admission fixtures.
    before=dict(qt_current_context=11,qt_scene_context=12,qt_current_surface=13,qt_top_level_surface=13,
        qt_current_thread=14,qt_native_thread=14,qt_context_thread=14,qt_surface_thread=14,
        qt_thread_id=15,expected_hwnd=16,qt_context_valid=True,qt_scene_sharing=True,qt_surface_is_top_level=True,
        native=dict(hglrc=17,hdc=18,window=16,thread_id=15))
    return dict(schema=1,frame_id=frame,status='observed',platform='win32',interval=0,errors=[],
        owned_after_closed_paint=True,extension='WGL_EXT_swap_control',extension_source='ARB',getter_abi='WINFUNCTYPE(c_int,void)',
        before=before,after=json.loads(json.dumps(before)))


def _cpu_completed_pacing_samples(count):
    return[dict(frame_id=i,status='success',presented=True,scene_and_presentation_syncs_signaled=True,
        presentation_pacing=_cpu_pacing_receipt(i))for i in range(count)]


class _CPUOwnedPacing:
    """Only the old end-to-end fake collector test uses this explicit fake."""
    def __init__(self):self.records=[];self.formats={}
    def observe(self,frame_id,*,closed_frame_id):
        assert frame_id==closed_frame_id
        receipt=_cpu_pacing_receipt(frame_id);self.records.append(receipt);return json.loads(json.dumps(receipt))
    def metadata(self):return dict(pacing_disabled=bool(self.records),explicit_CPU_fake=True)


# Explicit synthetic evidence for both API roles. These are observations under
# CPU doubles, never inherited hardware benchmark measurements.
_WORK_ZERO_FIELDS = (
    'texture_uploads','buffer_uploads','geometry_upload_bytes','texture_conversion_ns',
    'point_conversion_builds','point_conversion_bytes','vertex_input_conversion_builds','vertex_input_conversion_bytes',
    'line_endpoint_conversion_builds','line_endpoint_conversion_bytes','pipeline_misses','portable_shader_misses',
    'shader_normalizations','shader_parse_calls','shader_link_calls','shader_spirv_stages',
    'shader_module_creations','render_pipeline_creations','compute_pipeline_creations','completion_waits','finish_calls',
    'gl_texture_upload_calls','gl_texture_upload_bytes','gl_buffer_upload_calls','gl_buffer_upload_bytes',
    'gl_shader_compile_calls','gl_program_link_calls','gl_finish_calls','gl_blocking_client_wait_calls',
    'gl_server_wait_calls','gl_readback_calls','gl_failed_api_calls',
)


def gate(reference, candidate, **kwargs):
    return BENCH.release_gate(reference, candidate, quality_passed=True, same_hardware=True, **kwargs)


def test_fixed_catalog_covers_primary_quality_and_update_variants():
    catalog = BENCH.CATALOG.values()
    assert len(BENCH.CATALOG) == 66
    images = [item for item in catalog if item.family == "image"]
    assert {item.shape for item in images} == {(4096, 4096, 1), (4096, 4096, 4)}
    assert {item.viewport for item in images} == {(3840, 2160)}
    assert {item.layers for item in images} == {1, 8}
    assert {item.update for item in images} == {"resident", "full", "patch"}
    points = [item for item in catalog if item.family == "points"]
    assert all(item.shape[0] == 1_000_000 and item.edge_width == item.antialias == 1 for item in points)
    assert {item.method for item in points} == {"points", "instanced"}
    assert {item.update for item in points} == {"resident", "color", "positions"}
    assert {item.spherical for item in points} == {True, False}
    volumes = [item for item in catalog if item.family == "volume"]
    assert {item.shape[0] for item in volumes} == {256, 512}
    assert {item.viewport for item in volumes} == {(1024, 1024), (2048, 2048)}
    assert {item.method for item in volumes} == {"mip", "translucent", "iso"}
    assert all(item.relative_step_size == .8 and item.interpolation == "linear" for item in volumes)


def test_statistics_use_completed_nanoseconds_and_retain_variability():
    result = BENCH.metrics([1_000_000, 2_000_000, 3_000_000, 4_000_000, 100_000_000])
    assert result["median_ms"] == 3
    assert result["p95_ms"] == pytest.approx(80.8)
    assert result["mad_ms"] == 1
    assert result["stdev_ms"] > 30
    assert result["count"] == 5
    assert BENCH.percentile([10], 0) == BENCH.percentile([10], 1) == 10


@pytest.mark.parametrize("samples", [[], [0], [-1], [float("nan")], [float("inf")]])
def test_invalid_latencies_cannot_qualify(samples):
    with pytest.raises(ValueError):
        BENCH.metrics(samples)


def test_schedule_alternates_pair_order_without_mixing_processes():
    assert BENCH.alternating_schedule(5) == [(0, "upstream"), (0, "candidate"),
                                           (1, "candidate"), (1, "upstream"),
                                           (2, "upstream"), (2, "candidate"),
                                           (3, "candidate"), (3, "upstream"),
                                           (4, "upstream"), (4, "candidate")]
    with pytest.raises(ValueError):
        BENCH.alternating_schedule(4)


def test_resident_gate_requires_speedup_and_p95():
    assert gate(runs(12, 15), runs(10, 15))["status"] == "passed"
    assert gate(runs(12, 15), runs(10, 15.01))["status"] == "failed"
    assert gate(runs(12, 15), runs(10.01, 12))["status"] == "failed"


def test_update_gate_allows_at_most_ten_percent_median_regression():
    assert gate(runs(10, 15), runs(11, 18), update=True)["status"] == "passed"
    assert gate(runs(10, 15), runs(11.01, 18), update=True)["status"] == "failed"


@pytest.mark.parametrize("change", [
    {"status": "blocked"}, {"measured_frames": 999}, {"warmup_frames": 99},
    {"boundary": {"gpu_completion": True, "presented": False}}, {"vsync": True},
    {"surface": {"pacing_disabled": False}}, {"run_index": 2},
    {"latency": {"count": 1000, "median_ms": float("nan"), "p95_ms": 12}},
    {"instrumentation_gaps": ["GPU query timing"]},
])
def test_incomplete_evidence_is_unproven_even_when_fast(change):
    candidate = runs(1, 2)
    candidate[0].update(change)
    assert gate(runs(), candidate)["status"] == "unproven"
    assert BENCH.release_gate(runs(), runs(1, 2))["status"] == "unproven"


def test_quality_uses_fixed_interior_and_predeclared_edge_rules():
    reference = np.zeros((20, 50, 4), np.uint8)
    candidate = reference.copy()
    candidate[0, 0] = 2
    assert BENCH.compare_quality(reference, candidate)["status"] == "passed"
    candidate[0, 0] = 3
    assert BENCH.compare_quality(reference, candidate)["status"] == "failed"
    assert BENCH.compare_quality(reference, candidate, exact=True)["status"] == "failed"
    edge = np.ones((20, 50), bool)
    assert BENCH.compare_quality(reference, candidate, edge_mask=edge)["status"] == "passed"
    candidate[0, 1] = 255
    assert BENCH.compare_quality(reference, candidate, edge_mask=edge)["status"] == "failed"
    assert BENCH.compare_quality(reference, candidate, edge_mask=np.zeros((1, 1), bool))["status"] == "failed"
    assert BENCH.compare_quality(reference[..., :3], candidate[..., :3])["status"] == "failed"


def test_admission_requires_matching_workload_data_checks_and_hashes(tmp_path):
    workload = next(iter(BENCH.CATALOG.values()))
    evidence = tmp_path / "oracle.npy"
    np.save(evidence, np.zeros((2, 2, 4), np.uint8))
    admission = {"schema": 1, "status": "passed", "workload_sha256": BENCH.value_sha256(asdict(workload)),
                 "benchmark_data_sha256": "retained-input-digest",
                 "checks": {name: "passed" for name in BENCH.SCIENTIFIC_CHECKS[workload.family]},
                 "evidence": [{"file": "oracle.npy", "sha256": BENCH.sha256(evidence)}]}
    BENCH.write_json(tmp_path / "admission.json", admission)
    plan = {"scientific_admission": "admission.json"}
    captures = [{"data_sha256": "retained-input-digest"}] * 10
    assert BENCH.validate_admission(plan, workload, captures, tmp_path)["status"] == "passed"
    assert BENCH.validate_admission(plan, workload, [{"data_sha256": "different"}], tmp_path)["status"] == "unproven"
    admission["checks"].pop("interpolation")
    BENCH.write_json(tmp_path / "admission.json", admission)
    assert BENCH.validate_admission(plan, workload, captures, tmp_path)["status"] == "unproven"
    evidence.write_bytes(b"modified")
    assert BENCH.validate_admission(plan, workload, captures, tmp_path)["status"] == "unproven"
    assert BENCH.validate_admission(None, workload, captures, tmp_path)["status"] == "unproven"


def test_hardware_identity_compares_actual_adapter_and_host_provenance():
    identities = {"upstream": {"vendor": "NVIDIA", "renderer": "designated GPU", "version": "driver 1"},
                  "candidate": {"vendor_id": 4318, "device_id": 123, "driver": "driver 1", "backend": "Vulkan"}}
    hardware = {"schema": 1, "adapter_id": "designated GPU serial/PCI", "driver": "driver 1",
                "presentation_environment": {"desktop": "same", "scaling": 1}, "renderers": identities}
    provenance = {"python": "3.12.8", "platform": "Windows", "machine": "AMD64", "qt_runtime": "6.11.0",
                  "runner_sha256": "actual-script-digest", "versions": {"numpy": "2.5.3", "PyQt6": "6.11.0"},
                  "environment": {"QT_SCALE_FACTOR": "1"}}
    captures = {kind: [{"renderer": dict(identity), "provenance": dict(provenance)}]
                for kind, identity in identities.items()}
    assert BENCH.validate_hardware(hardware, captures)["status"] == "passed"
    captures["candidate"][0]["renderer"]["device_id"] = 456
    assert BENCH.validate_hardware(hardware, captures)["status"] == "unproven"
    captures["candidate"][0]["renderer"]["device_id"] = 123
    captures["candidate"][0]["provenance"]["python"] = "3.14.0"
    assert BENCH.validate_hardware(hardware, captures)["status"] == "unproven"


def test_dry_run_writes_plan_without_importing_or_measuring_vispy(tmp_path):
    name = "image-scalar-1-translucent-resident"
    assert BENCH.main(["--reference-python", str(tmp_path / "reference/python.exe"),
                       "--candidate-python", str(tmp_path / "candidate/python.exe"),
                       "--output", str(tmp_path / "planned"), "--workloads", name, "--dry-run"]) == 0
    request = json.loads((tmp_path / "planned/request.json").read_text())
    assert request["status"] == "planned"
    assert request["warmup"] == 100 and request["frames"] == 1000 and request["repetitions"] == 5
    assert not (tmp_path / "planned/manifest.json").exists()


def _python_telemetry_fixture(*, fail=False):
    ticks = iter(range(0, 100_000, 10))
    pack = SimpleNamespace(pack_commands=lambda commands: (tuple(commands), []))

    def parse(commands):
        packed, arrays = pack.pack_commands(commands)
        if fail:
            raise ValueError('real parser failure')
        return len(packed), arrays

    parser = SimpleNamespace(parse=parse)
    canvas = SimpleNamespace(context=SimpleNamespace(shared=SimpleNamespace(parser=parser)),
                             _backend=SimpleNamespace(_vispy_swap_buffers=lambda: 'presented'))
    canvas.draw_visual = lambda visual: parser.parse([('DRAW', visual)])
    original = (canvas.draw_visual, parser.parse, canvas._backend._vispy_swap_buffers, pack.pack_commands)
    telemetry = BENCH.PythonFrameTelemetry(canvas, pack_module=pack, clock=lambda: next(ticks))
    return canvas, pack, telemetry, original


def test_python_timing_tracks_nested_parser_work_and_retains_frame_before_async_completion():
    canvas, pack, telemetry, original = _python_telemetry_fixture()
    try:
        telemetry.begin(7)
        assert telemetry.update(lambda frame: frame * 4, 7) == 28
        assert canvas.draw_visual(11) == (1, [])
        assert canvas._backend._vispy_swap_buffers() == 'presented'
        first = dict(telemetry.frames[7])
        assert first['python_update_calls'] == first['python_draw_calls'] == first['python_glir_parse_calls'] == first['python_glir_pack_calls'] == 1
        assert 0 < first['python_glir_pack_ns'] < first['python_glir_parse_inclusive_ns'] < first['python_draw_inclusive_ns']
        assert first['python_draw_exclusive_ns'] == first['python_draw_inclusive_ns'] - first['python_glir_parse_inclusive_ns']
        telemetry.begin(8)
        telemetry.update(lambda frame: 0, 8)
        canvas.draw_visual(12)
        canvas._backend._vispy_swap_buffers()
        # A later completion can read frame 7 after frame 8 was presented.
        assert telemetry.frames[7] == first
        canvas.draw_visual(13)  # an unsolicited repaint is counted separately
        assert telemetry.frames[7] == first and telemetry.frames[8]['python_draw_calls'] == 1
        assert telemetry.snapshot()['unattributed_draw_calls'] == 1
    finally:
        telemetry.close()
    assert (canvas.draw_visual, canvas.context.shared.parser.parse, canvas._backend._vispy_swap_buffers, pack.pack_commands) == original
    telemetry.close()


def test_python_telemetry_rejects_coalesced_duplicate_and_unmatched_updates():
    canvas, _, telemetry, _ = _python_telemetry_fixture()
    try:
        with pytest.raises(RuntimeError, match='matching begun frame'):
            telemetry.update(lambda frame: 0, 1)
        telemetry.begin(1)
        with pytest.raises(RuntimeError, match='coalesced or repeated'):
            telemetry.begin(2)
        canvas._backend._vispy_swap_buffers()
        with pytest.raises(RuntimeError, match='coalesced or repeated'):
            telemetry.begin(1)
    finally:
        telemetry.close()


@pytest.mark.parametrize("paint_name", ["paintGL", "paintEvent"])
def test_python_telemetry_keeps_post_swap_alpha_flush_in_owning_paint(paint_name):
    ticks = iter(range(0, 100_000, 10))
    pack = SimpleNamespace(pack_commands=lambda commands: (tuple(commands), []))
    parser = SimpleNamespace(parse=lambda commands: pack.pack_commands(commands))
    backend = SimpleNamespace(_vispy_swap_buffers=lambda: "presented")
    canvas = SimpleNamespace(context=SimpleNamespace(shared=SimpleNamespace(parser=parser)), _backend=backend)
    canvas.draw_visual = lambda visual: parser.parse([("DRAW", visual)])

    def paint():
        canvas.draw_visual(1)
        backend._vispy_swap_buffers()
        assert telemetry.current is telemetry.frames[9]
        with pytest.raises(RuntimeError, match="coalesced or repeated"):
            telemetry.begin(10)
        parser.parse([("COLOR_MASK", False, False, False, True), ("CLEAR",)])
        return "painted"

    setattr(backend, paint_name, paint)
    telemetry = BENCH.PythonFrameTelemetry(canvas, pack_module=pack, clock=lambda: next(ticks))
    try:
        assert telemetry.paint_methods == [paint_name]
        telemetry.begin(9)
        assert getattr(backend, paint_name)() == "painted"
        assert telemetry.current is None
        frame = telemetry.frames[9]
        assert frame["python_draw_calls"] == frame["python_paint_calls"] == 1
        assert frame["python_glir_parse_calls"] == frame["python_glir_pack_calls"] == 2
        assert frame["python_paint_tail_glir_parse_calls"] == 1
        assert 0 < frame["python_paint_tail_glir_parse_ns"] < frame["python_paint_inclusive_ns"]
        assert telemetry.snapshot()["unattributed_glir_parse_calls"] == 0
        before = frame.copy()
        parser.parse([("UNSOLICITED",)])
        assert telemetry.snapshot()["unattributed_glir_parse_calls"] == 1
        assert telemetry.snapshot()["unattributed_glir_pack_calls"] == 1
        assert telemetry.frames[9] == before
    finally:
        telemetry.close()
    assert getattr(backend, paint_name) is paint


def test_python_telemetry_restores_paint_and_retains_tail_exception_timing():
    ticks = iter(range(0, 100_000, 10))
    parser = SimpleNamespace(parse=lambda commands: (_ for _ in ()).throw(ValueError("tail parse failure")))
    backend = SimpleNamespace(_vispy_swap_buffers=lambda: "presented")
    canvas = SimpleNamespace(context=SimpleNamespace(shared=SimpleNamespace(parser=parser)), _backend=backend,
                             draw_visual=lambda visual: None)

    def paint():
        backend._vispy_swap_buffers()
        parser.parse([("CLEAR",)])

    backend.paintGL = paint
    telemetry = BENCH.PythonFrameTelemetry(canvas, clock=lambda: next(ticks))
    try:
        telemetry.begin(3)
        with pytest.raises(ValueError, match="tail parse failure"):
            backend.paintGL()
        assert telemetry.current is None
        assert telemetry.frames[3]["python_paint_tail_glir_parse_calls"] == 1
        assert telemetry.frames[3]["python_paint_tail_glir_parse_ns"] > 0
    finally:
        telemetry.close()
    assert backend.paintGL is paint


def test_python_parser_failure_keeps_exception_timing_and_restores_wrapped_methods():
    canvas, pack, telemetry, original = _python_telemetry_fixture(fail=True)
    try:
        telemetry.begin(1)
        with pytest.raises(ValueError, match='real parser failure'):
            canvas.draw_visual(9)
        assert telemetry.frames[1]['python_draw_calls'] == 1
        assert telemetry.frames[1]['python_glir_parse_calls'] == 1
        assert telemetry.frames[1]['python_glir_parse_inclusive_ns'] > 0
    finally:
        telemetry.close()
    assert (canvas.draw_visual, canvas.context.shared.parser.parse, canvas._backend._vispy_swap_buffers, pack.pack_commands) == original


def _gpu_record(frame_id, *, status='success'):
    return {'frame_id': frame_id, 'status': status, 'error': '', 'quantization_ns': 65536,
            'submission_count': 2, 'render_span_ns': 7, 'pass_sum_ns': 6,
            'passes': [{'submission_index': 0, 'kind': 'scene', 'begin_ns': 10, 'end_ns': 12, 'elapsed_ns': 2},
                       {'submission_index': 1, 'kind': 'presentation', 'begin_ns': 13, 'end_ns': 17, 'elapsed_ns': 4}]}


def _completion_record(frame_id, *, status='success', presented=True):
    return {'frame_id': frame_id, 'status': status, 'presented': presented,
            'completion_latency_ns': 123, 'completion_timestamp_ns': 456,
            'counters': {'draws': 2}}


def test_completion_receipts_join_out_of_order_and_own_data_in_each_phase():
    samples = BENCH.FrameCompletionSamples()
    samples.begin(0, 'warmup')
    warm = _completion_record(0)
    samples.collect([warm], 'warmup')
    warm['counters']['draws'] = 99
    samples.begin(1, 'measured')
    samples.begin(2, 'measured')
    samples.collect([_completion_record(2), _completion_record(1)], 'measured')
    assert samples.count('warmup') == 1 and samples.count('measured') == 2
    assert [record['frame_id'] for record in samples.samples('measured')] == [1, 2]
    assert [record['frame_id'] for record in samples.observed] == [0, 2, 1]
    joined = samples.samples('warmup')
    assert joined[0]['counters']['draws'] == 2
    joined[0]['counters']['draws'] = 100
    assert samples.results[0]['counters']['draws'] == samples.observed[0]['counters']['draws'] == 2


@pytest.mark.parametrize('bad_id', [True, 1.0, '1', -1, None])
def test_invalid_completion_id_cannot_be_coerced_into_an_issued_frame(bad_id):
    samples = BENCH.FrameCompletionSamples()
    samples.begin(1, 'measured')
    batch = [_completion_record(bad_id), _completion_record(1)]
    with pytest.raises(RuntimeError, match='invalid completion frame identity'):
        samples.collect(batch, 'measured')
    assert samples.observed == batch and not samples.results


@pytest.mark.parametrize('failure', ['duplicate', 'unissued', 'wrong-phase', 'failed', 'unpresented'])
def test_bad_completion_retains_entire_received_batch_and_fails_admission(failure):
    samples = BENCH.FrameCompletionSamples()
    samples.begin(0, 'warmup')
    samples.begin(1, 'measured')
    phase = 'warmup'
    bad = _completion_record(0)
    if failure == 'duplicate':
        samples.collect([bad], phase)
    elif failure == 'unissued':
        bad['frame_id'] = 2
    elif failure == 'wrong-phase':
        phase = 'measured'
    elif failure == 'failed':
        bad['status'] = 'device_lost'
    else:
        bad['presented'] = False
    batch = [bad, _completion_record(1, status='cancelled')]
    with pytest.raises(RuntimeError, match=failure if failure in ('duplicate', 'unissued', 'wrong-phase') else 'failed or unpresented'):
        samples.collect(batch, phase)
    batch[1]['status'] = 'changed-after-poll'
    assert samples.observed[-2]['frame_id'] == bad['frame_id']
    assert samples.observed[-1]['status'] == 'cancelled'
    assert samples.count('measured') == 0


@pytest.mark.parametrize('enabled', [True, False])
def test_gpu_drain_admits_receipts_even_after_maps_complete_or_queries_disabled(enabled):
    samples = BENCH.FrameCompletionSamples()
    samples.begin(0, 'warmup')
    samples.collect([_completion_record(0)], 'warmup')
    collector = BENCH.CandidateCompletions.__new__(BENCH.CandidateCompletions)
    collector.gpu_metadata = {'enabled': enabled}
    collector.gpu_frames = BENCH.GPUFrameSamples()
    collector.gpu_frames.begin(0)
    collector.gpu_frames.collect([_gpu_record(0)])
    events = []
    collector.canvas = SimpleNamespace(app=SimpleNamespace(process_events=lambda: events.append('events')))
    collector.poll = lambda: [_completion_record(0, status='device_lost')]
    with pytest.raises(RuntimeError, match='duplicate completion frame'):
        collector.drain_gpu(0, 1, 1, completions=samples, phase='warmup')
    assert events == ['events'] and samples.observed[-1]['status'] == 'device_lost'


@pytest.mark.parametrize('enabled', [True, False])
@pytest.mark.parametrize('late', ['unissued', 'wrong-phase'])
def test_gpu_drain_rejects_late_unissued_or_wrong_phase_receipts(enabled, late):
    samples = BENCH.FrameCompletionSamples()
    samples.begin(0, 'warmup')
    samples.collect([_completion_record(0)], 'warmup')
    if late == 'wrong-phase':
        samples.begin(1, 'measured')
    collector = BENCH.CandidateCompletions.__new__(BENCH.CandidateCompletions)
    collector.gpu_metadata = {'enabled': enabled}
    collector.gpu_frames = BENCH.GPUFrameSamples()
    collector.gpu_frames.begin(0)
    collector.gpu_frames.collect([_gpu_record(0)])
    collector.canvas = SimpleNamespace(app=SimpleNamespace(process_events=lambda: None))
    collector.poll = lambda: [_completion_record(1), _completion_record(2, status='cancelled')]
    with pytest.raises(RuntimeError, match=late):
        collector.drain_gpu(0, 1, 1, completions=samples, phase='warmup')
    assert [record['frame_id'] for record in samples.observed] == [0, 1, 2]
    assert samples.observed[-1]['status'] == 'cancelled'


@pytest.mark.parametrize('bad_id', [True, 1.9, '1', -1, None])
@pytest.mark.parametrize('operation', ['begin', 'collect', 'join'])
def test_gpu_frame_ids_are_strict_without_losing_rejected_maps(bad_id, operation):
    gpu = BENCH.GPUFrameSamples()
    gpu.begin(1)
    with pytest.raises(RuntimeError, match='invalid GPU timing frame identity'):
        if operation == 'begin':
            gpu.begin(bad_id)
        elif operation == 'collect':
            gpu.collect([_gpu_record(bad_id), _gpu_record(1)])
        else:
            gpu.collect([_gpu_record(1)])
            gpu.join([{'frame_id': bad_id}])
    if operation == 'collect':
        assert len(gpu.observed) == 2 and gpu.observed[-1]['frame_id'] == 1
        assert not gpu.results


@pytest.mark.parametrize('failure', ['warm-map-failure', 'warm-drain-unissued', 'warm-scope-failure'])
def test_worker_exports_raw_samples_and_issued_phases_after_warm_failure(monkeypatch, tmp_path, failure):
    # Drive the real worker orchestration with CPU-only backend doubles.
    # These captures/timestamps are synthetic and provide no GPU evidence.
    workload_name = next(iter(BENCH.CATALOG))
    workload = BENCH.CATALOG[workload_name]
    closed = []
    canvas = SimpleNamespace(
        app=SimpleNamespace(process_events=lambda: None), physical_size=workload.viewport,
        set_current=lambda: None, update=lambda: None,
        render=lambda **kwargs: np.zeros((1, 1, 4), np.uint8),
        close=lambda: closed.append('canvas'))
    native = SimpleNamespace(
        benchmark_begin_frame=lambda *args: None, benchmark_completions=lambda *args: [],
        benchmark_surface_info=lambda *args: {}, benchmark_frame_request_ready=lambda *args: True,
        device_info=lambda: {'software': False, 'backend': 'Vulkan'})
    monkeypatch.setitem(sys.modules, 'vispy', SimpleNamespace(_dawn=native))
    monkeypatch.setitem(sys.modules, 'vispy.gloo', SimpleNamespace(dawn_parser=SimpleNamespace()))
    monkeypatch.setattr(BENCH, 'package_provenance', lambda kind: {'synthetic_CPU_only': True})
    _install_fake_fresh_qt_setup(monkeypatch)
    monkeypatch.setattr(BENCH, 'build_scene', lambda *args: (canvas, lambda frame_id: 0, 'synthetic'))

    class Collector(BENCH.CandidateCompletions):
        def __init__(self, canvas):
            self.canvas = canvas
            self.native = native
            self.canvas_id = 1
            self.gpu_metadata = {'enabled': True}
            self.gpu_frames = BENCH.GPUFrameSamples()
            self.telemetry = {'frame_ownership_scope': 'whole_qt_paint_v1'} if failure == 'warm-scope-failure' else {}
            self.boundary = {'presented': True, 'gpu_completion': True, 'whole_qt_paint_scope_verified': False}
            self.surface = {'pacing_disabled': True}
            self.pending = None
            self.completed = False

        def begin(self, frame_id):
            self.pending = frame_id
            self.gpu_frames.begin(frame_id)

        def poll(self):
            if self.pending is not None:
                frame_id, self.pending = self.pending, None
                status = 'device_lost' if failure == 'warm-map-failure' else 'success'
                self.gpu_frames.collect([_gpu_record(frame_id, status=status)])
                self.completed = True
                return [_completion_record(frame_id)]
            if self.completed and failure == 'warm-drain-unissued':
                return [_completion_record(99), _completion_record(100, status='cancelled')]
            return []

    class PythonTelemetry:
        def __init__(self, *args, **kwargs):
            self.paint_methods = ['paintEvent']

        def begin(self, frame_id):
            pass

        def update(self, function, frame_id):
            return function(frame_id)

        def close(self):
            closed.append('telemetry')

    monkeypatch.setattr(BENCH, 'CandidateCompletions', Collector)
    monkeypatch.setattr(BENCH, 'PythonFrameTelemetry', PythonTelemetry)
    options = SimpleNamespace(worker='candidate', workload=workload_name, output=tmp_path,
                              run_index=0, warmup=1, frames=1, queue_depth=1, vsync=False, timeout=1)
    assert BENCH.run_worker(options) == 2
    result = json.loads((tmp_path / 'run.json').read_text())
    assert result['status'] == ('failed' if failure == 'warm-drain-unissued' else 'blocked')
    expected_error = {'warm-map-failure': 'device_lost', 'warm-drain-unissued': 'unissued',
                      'warm-scope-failure': 'complete Qt paint ownership'}[failure]
    assert expected_error in result['error']
    assert json.loads((tmp_path / 'issued-frames.json').read_text()) == {'0': 'warmup'}
    receipts = json.loads((tmp_path / 'observed-samples.json').read_text())
    assert [record['frame_id'] for record in receipts] == ([0, 99, 100] if failure == 'warm-drain-unissued' else [0])
    gpu = json.loads((tmp_path / 'observed-gpu-timings.json').read_text())
    assert gpu[0]['status'] == ('device_lost' if failure == 'warm-map-failure' else 'success')
    for key in ('issued_frames', 'observed_samples', 'observed_gpu_timings'):
        assert BENCH.sha256(tmp_path / result[key]['file']) == result[key]['sha256']
    assert closed == ['telemetry', 'canvas']
    assert not (tmp_path / 'samples.json').exists()


def test_legacy_candidate_can_request_without_paint_readiness_api():
    collector = BENCH.CandidateCompletions.__new__(BENCH.CandidateCompletions)
    collector.telemetry = {}
    collector.native = SimpleNamespace()
    assert collector.request_ready() is True


@pytest.mark.parametrize('ready', [False, True])
def test_paint_candidate_request_readiness_uses_native_canvas(ready):
    collector = _paint_scope_fixture(enabled=False)
    calls = []
    collector.canvas_id = 21
    collector.native = SimpleNamespace(
        benchmark_frame_request_ready=lambda canvas_id: calls.append(canvas_id) or ready)
    assert collector.request_ready() is ready
    assert calls == [21]


@pytest.mark.parametrize('ready', [0, 1, 'true', None, np.bool_(True)])
def test_paint_candidate_rejects_nonboolean_request_readiness(ready):
    collector = _paint_scope_fixture(enabled=False)
    collector.canvas_id = 21
    collector.native = SimpleNamespace(benchmark_frame_request_ready=lambda canvas_id: ready)
    with pytest.raises(BENCH.InstrumentationUnavailable, match='readiness must be a boolean'):
        collector.request_ready()


@pytest.mark.parametrize('api', [None, 1])
def test_paint_candidate_requires_request_readiness_api(api):
    collector = _paint_scope_fixture(enabled=False)
    collector.native = SimpleNamespace(benchmark_frame_request_ready=api)
    with pytest.raises(BENCH.InstrumentationUnavailable, match='request readiness is absent'):
        collector.request_ready()


def test_worker_defers_request_until_paint_but_keeps_gpu_frames_in_flight(monkeypatch, tmp_path):
    # Drive the actual worker phase. Paint is deferred for two event polls and
    # its synthetic GPU receipt for two more; no GPU evidence is produced.
    workload_name = next(iter(BENCH.CATALOG))
    workload = BENCH.CATALOG[workload_name]
    tick, reserved = 0, None
    in_flight, ready_receipts, beginnings, readiness = {}, [], [], []
    closed = []

    def process_events():
        nonlocal tick, reserved
        tick += 1
        if reserved is not None and tick >= reserved[1]:
            frame_id, reserved = reserved[0], None
            in_flight[frame_id] = tick + 2
        for frame_id, due in list(in_flight.items()):
            if tick >= due:
                ready_receipts.append(_completion_record(frame_id))
                del in_flight[frame_id]

    def begin(canvas_id, frame_id):
        nonlocal reserved
        assert canvas_id == 21 and reserved is None
        beginnings.append((frame_id, tick, sorted(in_flight)))
        reserved = (frame_id, tick + 2)

    def request_ready(canvas_id):
        assert canvas_id == 21
        readiness.append(reserved is None)
        return reserved is None

    def poll_receipts(canvas_id):
        result = list(ready_receipts)
        ready_receipts.clear()
        return result

    native = SimpleNamespace(
        benchmark_begin_frame=begin, benchmark_completions=poll_receipts,
        benchmark_surface_info=lambda canvas_id: {'pacing_disabled': True},
        benchmark_telemetry_info=lambda: {'frame_ownership_scope': 'whole_qt_paint_v1'},
        benchmark_frame_request_ready=request_ready, process_events=lambda: None,
        device_info=lambda: {'software': False, 'backend': 'Vulkan'})
    canvas = SimpleNamespace(
        _backend=SimpleNamespace(_dawn_canvas_id=21),
        app=SimpleNamespace(process_events=process_events), physical_size=workload.viewport,
        set_current=lambda: None, update=lambda: None,
        render=lambda **kwargs: np.zeros((1, 1, 4), np.uint8),
        close=lambda: closed.append('canvas'))
    monkeypatch.setitem(sys.modules, 'vispy', SimpleNamespace(_dawn=native))
    monkeypatch.setitem(sys.modules, 'vispy.gloo', SimpleNamespace(dawn_parser=SimpleNamespace()))
    monkeypatch.setattr(BENCH, 'package_provenance', lambda kind: {'synthetic_CPU_only': True})
    _install_fake_fresh_qt_setup(monkeypatch)
    monkeypatch.setattr(BENCH, 'build_scene', lambda *args: (canvas, lambda frame_id: 0, 'synthetic'))
    class Collector(BENCH.CandidateCompletions):
        def verify_scope(self, samples):
            assert [sample['frame_id'] for sample in samples] == [0, 1]
            raise BENCH.InstrumentationUnavailable('synthetic stop after completed warm phase')

    class PythonTelemetry:
        def __init__(self, *args, **kwargs):
            self.paint_methods = ['paintEvent']

        def begin(self, frame_id):
            pass

        def update(self, function, frame_id):
            return function(frame_id)

        def close(self):
            closed.append('telemetry')

    monkeypatch.setattr(BENCH, 'CandidateCompletions', Collector)
    monkeypatch.setattr(BENCH, 'PythonFrameTelemetry', PythonTelemetry)
    options = SimpleNamespace(worker='candidate', workload=workload_name, output=tmp_path,
                              run_index=0, warmup=2, frames=1, queue_depth=2, vsync=False, timeout=1)
    assert BENCH.run_worker(options) == 2
    result = json.loads((tmp_path / 'run.json').read_text())
    assert result['error'] == 'synthetic stop after completed warm phase'
    assert beginnings == [(0, 2, []), (1, 4, [0])]
    assert readiness[:3] == [True, False, True]
    assert json.loads((tmp_path / 'issued-frames.json').read_text()) == {'0': 'warmup', '1': 'warmup'}
    assert [record['frame_id'] for record in json.loads((tmp_path / 'observed-samples.json').read_text())] == [0, 1]
    assert closed == ['telemetry', 'canvas']


def test_failed_warm_gpu_map_and_rejected_batch_remain_visible():
    gpu = BENCH.GPUFrameSamples()
    gpu.begin(0)
    gpu.collect([_gpu_record(0, status='device_lost')])
    with pytest.raises(BENCH.InstrumentationUnavailable, match='device_lost'):
        gpu.join([_completion_record(0)])
    batch = [_gpu_record(4), _gpu_record(5, status='cancelled')]
    with pytest.raises(RuntimeError, match='unissued or duplicate'):
        gpu.collect(batch)
    batch[1]['status'] = 'changed-after-poll'
    assert [record['frame_id'] for record in gpu.observed] == [0, 4, 5]
    assert gpu.observed[-1]['status'] == 'cancelled'


def test_partial_qt_paint_boundary_cannot_pass_release_gate_without_gap_labels():
    candidate = runs()
    for run in candidate:
        run['boundary']['whole_qt_paint_scope_verified'] = False
    result = gate(runs(12, 15), candidate)
    assert result['status'] == 'unproven'
    assert 'completion ownership through the final Qt paint submission is unproven' in result['reasons']


def _paint_scope_fixture(*, enabled=True):
    collector = BENCH.CandidateCompletions.__new__(BENCH.CandidateCompletions)
    collector.telemetry = {'frame_ownership_scope': 'whole_qt_paint_v1'}
    collector.boundary = {'whole_qt_paint_scope_verified': False}
    collector.gpu_metadata = {'enabled': enabled}
    return collector


def _paint_scope_sample(frame_id=0, token=10):
    sample = _completion_record(frame_id)
    sample.update(frame_scope='qt_paint', paint_token=token, ownership_closed=True,
                  ownership_retired=True, submission_count=4, present_count=2,
                  last_present_submission_index=2, counters_captured=True, counter_capture='submission')
    timing = _gpu_record(frame_id)
    timing.update(frame_scope='qt_paint', paint_token=token, submission_count=4,
                  last_present_submission_index=2)
    # Submissions1/3 can contain no render passes; submission3 follows the
    # final actual presentation. Their absence is legitimate, not a lost map.
    timing['passes'][0].update(kind='surface_conversion', submission_index=0)
    timing['passes'][1].update(kind='surface_conversion', submission_index=2)
    sample['gpu_timing'] = timing
    return sample


@pytest.mark.parametrize('enabled', [False, True])
def test_scope_requires_receipts_and_joins_final_presentation_despite_copy_only_gaps(enabled):
    collector = _paint_scope_fixture(enabled=enabled)
    assert collector.verify_scope([]) is False
    warm = _paint_scope_sample()
    measured = _paint_scope_sample(1, 11)
    original = BENCH.copy.deepcopy([warm, measured])
    if not enabled:
        warm.pop('gpu_timing')
        measured.pop('gpu_timing')
        original = BENCH.copy.deepcopy([warm, measured])
    assert collector.verify_scope([warm]) is True
    assert collector.verify_scope([measured]) is True
    assert [warm, measured] == original
    assert collector.boundary['verified_paint_frames'] == 2
    assert collector.boundary['final_presentation_gpu_pass_verified'] is enabled


def test_old_capability_keeps_scope_gate_off_even_with_plausible_receipts():
    collector = _paint_scope_fixture()
    collector.telemetry = {}
    assert collector.verify_scope([_paint_scope_sample()]) is False
    assert collector.boundary['whole_qt_paint_scope_verified'] is False


@pytest.mark.parametrize('field,value', [
    ('frame_id', True), ('status', 'cancelled'), ('presented', False),
    ('frame_scope', 'native_present'), ('paint_token', 0), ('paint_token', True),
    ('paint_token', '10'), ('ownership_closed', False), ('ownership_retired', False),
    ('counters_captured', False), ('counters_captured', 1),
    ('counter_capture', 'unavailable_snapshot'), ('counters', None), ('counters', {}),
    ('submission_count', 0), ('submission_count', 4.0), ('present_count', 0),
    ('present_count', 5), ('present_count', True),
    ('last_present_submission_index', -1), ('last_present_submission_index', 4),
    ('last_present_submission_index', True),
])
def test_scope_capability_cannot_admit_incomplete_or_coerced_receipt(field, value):
    collector = _paint_scope_fixture()
    sample = _paint_scope_sample()
    sample[field] = value
    with pytest.raises(BENCH.InstrumentationUnavailable, match='complete Qt paint ownership'):
        collector.verify_scope([sample])
    assert collector.boundary['whole_qt_paint_scope_verified'] is False


@pytest.mark.parametrize('field,value', [
    ('frame_scope', 'native_present'), ('paint_token', 11), ('paint_token', True),
    ('frame_id', 1), ('frame_id', False), ('submission_count', 3),
    ('submission_count', 4.0), ('status', 'map_failure'),
    ('last_present_submission_index', 3), ('last_present_submission_index', True),
])
def test_scope_rejects_gpu_maps_with_different_ownership(field, value):
    collector = _paint_scope_fixture()
    sample = _paint_scope_sample()
    sample['gpu_timing'][field] = value
    with pytest.raises(BENCH.InstrumentationUnavailable, match='different paint ownership'):
        collector.verify_scope([sample])
    assert collector.boundary['whole_qt_paint_scope_verified'] is False


@pytest.mark.parametrize('failure', ['bool-index', 'outside', 'missing-final', 'duplicate-index', 'wrong-last'])
def test_scope_requires_each_actual_presentation_and_the_declared_final_one(failure):
    collector = _paint_scope_fixture()
    sample = _paint_scope_sample()
    passes = sample['gpu_timing']['passes']
    if failure == 'bool-index':
        passes[0]['submission_index'] = False
    elif failure == 'outside':
        passes[0]['submission_index'] = 4
    elif failure == 'missing-final':
        passes.pop()
    elif failure == 'duplicate-index':
        passes[1]['submission_index'] = 0
    else:
        sample['last_present_submission_index'] = 3
        sample['gpu_timing']['last_present_submission_index'] = 3
    with pytest.raises(BENCH.InstrumentationUnavailable, match='outside owned submissions|final owned presentation'):
        collector.verify_scope([sample])
    assert collector.boundary['whole_qt_paint_scope_verified'] is False


@pytest.mark.parametrize('collision', ['token', 'frame'])
def test_scope_tokens_are_unique_across_warm_and_measured_phases(collision):
    collector = _paint_scope_fixture()
    assert collector.verify_scope([_paint_scope_sample()])
    sample = _paint_scope_sample(1, 10) if collision == 'token' else _paint_scope_sample(0, 11)
    with pytest.raises(BENCH.InstrumentationUnavailable, match='multiple'):
        collector.verify_scope([sample])
    assert collector.boundary['whole_qt_paint_scope_verified'] is False
    assert collector._verified_paint_tokens == {10: 0}


def test_gpu_maps_join_out_of_order_without_changing_completion_latency():
    gpu = BENCH.GPUFrameSamples()
    gpu.begin(10)
    gpu.begin(11)
    completions = [{'frame_id': 10, 'completion_latency_ns': 123},
                   {'frame_id': 11, 'completion_latency_ns': 456}]
    gpu.collect([_gpu_record(11)])
    assert not gpu.complete(10, 2)
    with pytest.raises(BENCH.InstrumentationUnavailable, match='not received'):
        gpu.join(completions)
    gpu.collect([_gpu_record(10)])
    assert gpu.complete(10, 2)
    gpu.join(completions)
    assert [item['gpu_timing']['frame_id'] for item in completions] == [10, 11]
    assert [item['completion_latency_ns'] for item in completions] == [123, 456]
    assert completions[0]['gpu_timing']['submission_count'] == 2
    assert completions[0]['gpu_timing']['render_span_ns'] != completions[0]['gpu_timing']['pass_sum_ns']


def test_gpu_quantized_zero_intervals_remain_valid_and_results_own_their_data():
    gpu = BENCH.GPUFrameSamples()
    gpu.begin(1)
    record = _gpu_record(1)
    for interval in record['passes']:
        interval.update(begin_ns=65536, end_ns=65536, elapsed_ns=0)
    record.update(pass_sum_ns=0, render_span_ns=0)
    gpu.collect([record])
    record['passes'][0]['end_ns'] = 99999
    completion = {'frame_id': 1}
    gpu.join([completion])
    assert completion['gpu_timing']['render_span_ns'] == 0
    completion['gpu_timing']['passes'][0]['end_ns'] = 123456
    assert gpu.results[1]['passes'][0]['end_ns'] == 65536


def test_duplicate_unissued_and_failed_gpu_maps_cannot_qualify():
    gpu = BENCH.GPUFrameSamples()
    gpu.begin(1)
    with pytest.raises(RuntimeError, match='duplicate GPU timing frame'):
        gpu.begin(1)
    with pytest.raises(RuntimeError, match='unissued or duplicate'):
        gpu.collect([_gpu_record(2)])
    gpu.collect([_gpu_record(1, status='device_lost')])
    with pytest.raises(RuntimeError, match='unissued or duplicate'):
        gpu.collect([_gpu_record(1)])
    completion = {'frame_id': 1}
    with pytest.raises(BENCH.InstrumentationUnavailable, match='device_lost'):
        gpu.join([completion])
    assert completion['gpu_timing']['status'] == gpu.results[1]['status'] == 'device_lost'


def test_counter_deltas_exclude_status_flags_and_process_gauges():
    before = {'allocate_calls': 2, 'cpu_ns': 1.5, 'vk_memory_available': False,
              'vk_memory_complete': True, 'peak_live_bytes': 32, 'live_bytes': 16,
              'changed_type': 1, 'removed': 5, 'point_conversion_builds': 2,
              'point_conversion_bytes': 128, 'live_cpu_buffer_bytes': 512}
    after = {'allocate_calls': 5, 'cpu_ns': 4.5, 'vk_memory_available': True,
             'vk_memory_complete': False, 'peak_live_bytes': 64, 'live_bytes': 8,
             'changed_type': True, 'new_event': 9, 'point_conversion_builds': 3,
             'point_conversion_bytes': 256, 'live_cpu_buffer_bytes': 1024}
    assert BENCH.counter_delta(before, after, peaks=['peak_live_bytes'],
                               gauges=['live_bytes', 'live_cpu_buffer_bytes']) == {
                                   'allocate_calls': 3, 'cpu_ns': 3.0,
                                   'point_conversion_builds': 1, 'point_conversion_bytes': 128}
    assert before['vk_memory_available'] is False and after['vk_memory_complete'] is False


def test_declared_native_high_water_marks_are_reported_without_event_deltas():
    before = dict.fromkeys(BENCH.NATIVE_PEAKS, 1)
    before.update(point_conversion_builds=2, point_conversion_bytes=128,
                  live_cpu_buffer_bytes=512, sampled_peak_live_cpu_buffer_bytes=1024,
                  future_provider_peak=7)
    after = dict(before, point_conversion_builds=3, point_conversion_bytes=256,
                 live_cpu_buffer_bytes=1024, sampled_peak_live_cpu_buffer_bytes=2048,
                 peak_pending_timestamp_frames=2, future_provider_peak=9)
    summary = BENCH.native_counter_summary(before, after, telemetry={
        'gauges': ['live_cpu_buffer_bytes'],
        'high_water_marks': ['sampled_peak_live_cpu_buffer_bytes', 'future_provider_peak'],
    }, backend='Metal')
    assert summary['counter_delta'] == {
        'point_conversion_builds': 1, 'point_conversion_bytes': 128,
    }
    assert summary['native_high_water_marks']['sampled_peak_live_cpu_buffer_bytes'] == 2048
    assert summary['native_high_water_marks']['future_provider_peak'] == 9
    assert summary['native_high_water_marks']['peak_pending_timestamp_frames'] == 2
    assert summary['missing_native_high_water_marks'] == []
    assert 'process lifetime' in summary['high_water_scope']
    incomplete = BENCH.native_counter_summary(before, after, telemetry={
        'high_water_marks': ['provider_declared_but_absent'],
    }, backend='Metal')
    assert incomplete['missing_native_high_water_marks'] == ['provider_declared_but_absent']


@pytest.mark.parametrize('corrupt', ['backwards', 'sum', 'span', 'empty', 'no_submission'])
def test_incomplete_or_inconsistent_gpu_intervals_cannot_qualify(corrupt):
    gpu = BENCH.GPUFrameSamples()
    gpu.begin(1)
    record = _gpu_record(1)
    if corrupt == 'backwards':
        record['passes'][0]['end_ns'] = 9
    elif corrupt == 'sum':
        record['pass_sum_ns'] = 7
    elif corrupt == 'span':
        record['render_span_ns'] = 6
    elif corrupt == 'empty':
        record['passes'] = []
    else:
        record['submission_count'] = 0
    gpu.collect([record])
    with pytest.raises(BENCH.InstrumentationUnavailable):
        gpu.join([{'frame_id': 1}])


@pytest.mark.parametrize('field', [
    'vertex_input_conversion_builds','vertex_input_conversion_bytes','texture_conversion_ns',
    'line_endpoint_conversion_builds','shader_normalizations','shader_parse_calls','shader_link_calls',
    'shader_spirv_stages','shader_module_creations','render_pipeline_creations','compute_pipeline_creations',
])
def test_release_rejects_observed_resident_work_even_with_fast_complete_samples(field):
    reference,candidate=runs(12,15),runs(10,14)
    candidate[2]['counter_delta'][field]=1
    result=gate(reference,candidate)
    assert result['status']!='passed'
    assert any(field in reason for reason in result['reasons'])


@pytest.mark.parametrize('kind,field', [('candidate','vertex_input_conversion_builds'),('upstream','gl_shader_compile_calls')])
@pytest.mark.parametrize('invalid', ['missing', True, None, -1, 0.0, float('nan'), float('inf')])
def test_release_requires_typed_actual_zero_work_evidence(kind,field,invalid):
    reference,candidate=runs(12,15),runs(10,14)
    target=(candidate if kind=='candidate' else reference)[0]['counter_delta']
    if invalid=='missing':target.pop(field)
    else:target[field]=invalid
    result=gate(reference,candidate)
    assert result['status']=='unproven'
    assert any(field in reason for reason in result['reasons'])


@pytest.mark.parametrize('field',['gl_texture_upload_calls','gl_buffer_upload_bytes','gl_shader_compile_calls','gl_program_link_calls'])
def test_release_rejects_real_upstream_resident_upload_compile_work(field):
    reference,candidate=runs(12,15),runs(10,14)
    reference[1]['counter_delta'][field]=1
    assert gate(reference,candidate)['status']!='passed'


def test_resident_transient_uniforms_and_cache_hit_times_remain_legal():
    reference,candidate=runs(12,15),runs(10,14)
    for run in candidate:
        run['counter_delta'].update(buffer_upload_cpu_ns=100,uniform_upload_bytes=64,
            shader_cache_lookup_ns=20,pipeline_cache_lookup_ns=30,pipeline_hits=1)
    assert gate(reference,candidate)['status']=='passed'


@pytest.mark.parametrize('kind,field',[('candidate','completion_waits'),('candidate','finish_calls'),
    ('upstream','gl_finish_calls'),('upstream','gl_blocking_client_wait_calls'),('upstream','gl_readback_calls')])
def test_updates_still_forbid_deliberate_waits_and_readbacks(kind,field):
    reference,candidate=runs(10,15),runs(10,16)
    target=(candidate if kind=='candidate' else reference)[0]['counter_delta']
    target[field]=1
    assert gate(reference,candidate,update=True)['status']!='passed'


def test_shared_measured_work_validator_used_by_worker_and_release_gate():
    import inspect
    assert 'measured_work_gate(result, options.worker' in inspect.getsource(BENCH.run_worker)
    assert 'measured_work_gate(run, kind' in inspect.getsource(BENCH.release_gate)
    for kind in ('upstream','candidate'):
        assert BENCH.measured_work_gate(runs()[0],kind)['status']=='passed'
        assert BENCH.measured_work_gate({},kind)['status']=='unproven'


class _ObservedBytes:
    def __init__(self,size):self.nbytes=size


class _ProtocolGL:
    """Explicit CPU fake; no GL import, device, shader or framebuffer exists."""
    GL_TIMESTAMP=1;GL_QUERY_COUNTER_BITS=2;GL_QUERY_RESULT_AVAILABLE=3;GL_QUERY_RESULT=4
    GL_SYNC_GPU_COMMANDS_COMPLETE=5;GL_TIMEOUT_EXPIRED=6;GL_ALREADY_SIGNALED=7;GL_CONDITION_SATISFIED=8
    def __init__(self):
        self.calls=[];self.values={};self.available={};self.next_time=10;self.next_name=100
        self.fail=None;self.fence_status=self.GL_ALREADY_SIGNALED
    def _call(self,name,*args):
        self.calls.append((name,args))
        if self.fail==name:raise ValueError('original GL failure '+name)
        return 'original-result'
    def glGetQueryiv(self,*args):self._call('bits',*args);return 64
    def glGenQueries(self,count):self._call('gen-queries',count);return list(range(1,count+1))
    def glQueryCounter(self,query,target):
        self._call('timestamp',query,target);self.values[query]=self.next_time;self.next_time+=10;self.available[query]=False
    def glGetQueryObjectiv(self,query,pname):self._call('available',query,pname);return int(self.available[query])
    def glGetQueryObjectui64v(self,query,pname,output):
        self._call('result',query,pname)
        assert self.available[query], 'blocking result read attempted before availability'
        output[0]=self.values[query]
        return 'wrapper return deliberately ignored'
    def glDeleteQueries(self,*args):return self._call('delete-queries',*args)
    def glBufferData(self,*args):return self._call('buffer-data',*args)
    def glBufferSubData(self,*args):return self._call('buffer-sub',*args)
    def glTexImage2D(self,*args):return self._call('texture-size2D',*args)
    def glTexSubImage2D(self,*args):return self._call('texture-data2D',*args)
    def glTexImage3D(self,*args):return self._call('texture-size3D',*args)
    def glTexSubImage3D(self,*args):return self._call('texture-data3D',*args)
    def glCompileShader(self,*args):return self._call('compile',*args)
    def glLinkProgram(self,*args):return self._call('link',*args)
    def glDrawArrays(self,*args):return self._call('draw',*args)
    def glClear(self,*args):return self._call('clear',*args)
    def glFinish(self,*args):return self._call('finish',*args)
    def glWaitSync(self,*args):return self._call('server-wait',*args)
    def glReadPixels(self,*args):return self._call('read-pixels',*args)
    def glClientWaitSync(self,*args):self._call('client-wait',*args);return self.fence_status
    def glFenceSync(self,*args):self._call('fence',*args);return object()
    def glFlush(self,*args):return self._call('flush',*args)
    def glDeleteSync(self,*args):return self._call('delete-fence',*args)
    def glGenBuffers(self,n):self._call('gen-buffers',n);return [100+i for i in range(n)] if n!=1 else 100
    def glGenTextures(self,n):self._call('gen-textures',n);return 200
    def glDeleteBuffers(self,*args):return self._call('delete-buffers',*args)
    def glDeleteTextures(self,*args):return self._call('delete-textures',*args)


def _protocol_adapter(gl):
    return SimpleNamespace(
        glBufferData=lambda target,data,usage:gl.glBufferData(target,data if isinstance(data,int) else data.nbytes,None if isinstance(data,int) else data,usage),
        glBufferSubData=lambda target,offset,data:gl.glBufferSubData(target,offset,data.nbytes,data),
        glTexImage2D=lambda target,level,internal,fmt,typ,data:gl.glTexImage2D(target,level,internal,8,6,0,fmt,typ,None if isinstance(data,tuple) else data),
        glTexSubImage2D=lambda target,level,x,y,fmt,typ,data:gl.glTexSubImage2D(target,level,x,y,8,6,fmt,typ,data),
        # Cached aliases, as in real _pyopengl2, must also be observed.
        glCompileShader=gl.glCompileShader,glLinkProgram=gl.glLinkProgram,
        glCreateBuffer=lambda:gl.glGenBuffers(1),glCreateTexture=lambda:gl.glGenTextures(1))


def _protocol_canvas(gl,body=None):
    class Signal:
        def __init__(self):self.callbacks=[]
        def connect(self,callback):self.callbacks.append(callback)
        def disconnect(self,callback):self.callbacks.remove(callback)
        def emit(self):
            for callback in tuple(self.callbacks):callback()
    scene=SimpleNamespace(format=lambda:SimpleNamespace(swapInterval=lambda:0))
    current={'value':scene}
    canvas=SimpleNamespace(native=SimpleNamespace(context=lambda:scene,frameSwapped=Signal()),_backend=SimpleNamespace(),
        set_current=lambda:current.update(value=scene),app=SimpleNamespace(process_events=lambda:None))
    def paint():
        canvas.set_current()
        gl.glDrawArrays(1,0,3)
        if body is not None:body(canvas,current)
        gl.glClear(1)  # The real Qt alpha tail follows events.draw.
        gl.glFlush()
        return 'original-paint-result'
    canvas._backend.paintGL=paint
    qt=SimpleNamespace(currentContext=lambda:current['value'],areSharing=lambda a,b:True)
    return canvas,current,qt


def test_GL_attribution_observes_payloads_cached_aliases_and_nested_adapters_once():
    gl=_ProtocolGL();adapter=_protocol_adapter(gl);ticks=iter(range(0,10000,10))
    old=(adapter.glBufferData,adapter.glCompileShader,gl.glBufferData,gl.glCompileShader)
    telemetry=BENCH.OpenGLAttribution([('vispy',adapter),('raw',gl)],clock=lambda:next(ticks))
    data=_ObservedBytes(192)
    try:
        assert adapter.glBufferData(1,data,2)=='original-result'
        adapter.glBufferData(1,4096,2) # actual allocation without host payload
        adapter.glBufferSubData(1,4,data)
        adapter.glTexImage2D(1,0,2,3,4,(6,8))
        adapter.glTexSubImage2D(1,0,0,0,3,4,data)
        gl.glTexSubImage3D(1,0,0,0,0,8,6,1,3,4,data)
        adapter.glCompileShader(5);adapter.glLinkProgram(6)
        snapshot=telemetry.snapshot()
        assert snapshot['gl_buffer_upload_calls']==2 and snapshot['gl_buffer_upload_bytes']==384
        assert snapshot['gl_buffer_storage_calls']==2 and snapshot['gl_buffer_storage_requested_bytes']==4288
        assert snapshot['gl_texture_storage_calls']==1
        assert snapshot['gl_texture_upload_calls']==2 and snapshot['gl_texture_upload_bytes']==384
        assert snapshot['gl_shader_compile_calls']==snapshot['gl_program_link_calls']==1
        assert snapshot['gl_shader_compile_cpu_ns']>0 and snapshot['gl_program_link_cpu_ns']>0
        assert telemetry.metadata()['errors']==[]
        assert gl.calls[0][1][2] is data # original payload object was passed through
    finally:telemetry.close()
    assert (adapter.glBufferData,adapter.glCompileShader,gl.glBufferData,gl.glCompileShader)==old


def test_GL_attribution_records_actual_descriptor_names_and_requested_storage_not_driver_memory():
    gl=_ProtocolGL();adapter=_protocol_adapter(gl)
    telemetry=BENCH.OpenGLAttribution([('vispy',adapter),('raw',gl)])
    try:
        assert adapter.glCreateBuffer()==100
        assert adapter.glCreateTexture()==200
        gl.glDeleteBuffers(1,[100]);gl.glDeleteTextures([200])
        values=telemetry.snapshot()
        for kind in ('buffer','texture'):
            assert values['gl_'+kind+'_create_calls']==values['gl_'+kind+'_created_names']==1
            assert values['gl_'+kind+'_delete_calls']==values['gl_'+kind+'_deleted_names']==1
            assert values['gl_'+kind+'_live_descriptors']==0
            assert values['gl_'+kind+'_peak_live_descriptors']==1
        assert 'not physical or opaque driver allocation' in telemetry.metadata()['allocation_scope']
    finally:telemetry.close()


def test_GL_attribution_retains_original_failure_time_and_true_wait_operations():
    gl=_ProtocolGL();telemetry=BENCH.OpenGLAttribution([('raw',gl)])
    try:
        gl.fail='compile'
        with pytest.raises(ValueError,match='original GL failure compile'):gl.glCompileShader(7)
        gl.fail=None
        gl.glClientWaitSync(object(),0,0);gl.glClientWaitSync(object(),0,1)
        gl.glWaitSync(object(),0,-1);gl.glFinish();gl.glReadPixels(0,0,1,1,0,0,None)
        values=telemetry.snapshot()
        assert values['gl_failed_api_calls']==values['gl_shader_compile_calls']==1
        assert values['gl_shader_compile_cpu_ns']>=0
        assert values['gl_zero_timeout_poll_calls']==values['gl_blocking_client_wait_calls']==1
        assert values['gl_server_wait_calls']==values['gl_finish_calls']==values['gl_readback_calls']==1
    finally:telemetry.close()


def test_GL_attribution_unknown_payload_cannot_silently_become_zero():
    gl=_ProtocolGL();telemetry=BENCH.OpenGLAttribution([('raw',gl)])
    try:
        gl.glTexSubImage2D(1,0,0,0,1,1,1,1,object())
        with pytest.raises(RuntimeError,match='incomplete upstream GL attribution'):telemetry.snapshot()
        assert telemetry.errors[0]['operation']=='glTexSubImage2D'
    finally:telemetry.close()


def test_GL_timestamp_pool_is_bounded_async_same_context_and_covers_alpha_tail():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    originals=(canvas.set_current,canvas._backend.paintGL)
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext,capacity=3)
    try:
        for frame in range(3):
            queries.begin(frame)
            assert canvas._backend.paintGL()=='original-paint-result'
        assert not queries.ready()
        with pytest.raises(RuntimeError,match='pool is busy'):queries.begin(3)
        assert len([c for c in gl.calls if c[0]=='gen-queries'])==1
        assert len(queries.ids)==6
        queries.poll()
        assert not any(c[0]=='result' for c in gl.calls)
        for query in gl.available:gl.available[query]=True
        queries.poll()
        assert len(queries.pending)==0 and len(queries.results)==3 and len(queries.free)==3
        samples=[{'frame_id':frame} for frame in range(3)];queries.join(samples)
        for record in samples:
            timing=record['opengl_gpu_timing']
            assert timing['elapsed_ns']==10 and timing['scope']=='upstream_vispy_paint'
            assert timing['same_scene_context_verified'] and timing['includes_alpha_tail']
            assert timing['qt_compositor_included'] is timing['scanout_included'] is False
        first=[name for name,args in gl.calls]
        assert first.index('timestamp')<first.index('draw')<first.index('clear')<first.index('flush')<first.index('timestamp',first.index('timestamp')+1)
        samples[0]['opengl_gpu_timing']['begin_ns']=-1
        assert queries.results[0]['begin_ns']==10
    finally:queries.close()
    assert (canvas.set_current,canvas._backend.paintGL)==originals
    assert not any(name in ('finish','client-wait','server-wait','read-pixels') for name,args in gl.calls)


@pytest.mark.parametrize('failure',['sharing-context','missing-context','paint-exception','no-current-call'])
def test_GL_timestamp_context_or_paint_failure_never_restores_context_to_fake_ownership(failure):
    gl=_ProtocolGL()
    def body(canvas,current):
        if failure=='sharing-context':current['value']=object()
        if failure=='missing-context':current['value']=None
        if failure=='paint-exception':raise ValueError('actual original paint failure')
    canvas,current,qt=_protocol_canvas(gl,body)
    if failure=='no-current-call':canvas._backend.paintGL=lambda:None
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext)
    queries.begin(0)
    with pytest.raises((RuntimeError,ValueError)):
        canvas._backend.paintGL()
    assert not any(name=='result' for name,args in gl.calls)
    assert not queries.pending[0]['ended']
    if failure in ('sharing-context','missing-context'):
        assert current['value']!=canvas.native.context()
    current['value']=canvas.native.context()
    queries.close()


@pytest.mark.parametrize('bad',[True,-1,1.0,None])
def test_GL_query_frame_identity_is_strict(bad):
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext)
    try:
        with pytest.raises(RuntimeError,match='malformed'):queries.begin(bad)
        assert not queries.pending
    finally:queries.close()


def test_GL_query_invalid_result_is_retained_and_rejected_without_changing_completion():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext)
    try:
        queries.begin(7);canvas._backend.paintGL()
        for query in gl.available:gl.available[query]=True
        gl.values[2]=0 # A representable uint64 end before its begin remains invalid.
        queries.poll()
        assert queries.observed[0]['status']=='invalid_timestamp'
        with pytest.raises(RuntimeError,match='invalid upstream GPU'):queries.join([{'frame_id':7}])
    finally:queries.close()


def test_GL_reference_fence_and_late_query_have_separate_actual_boundaries():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter)
    try:
        collector.begin(0);canvas._backend.paintGL();canvas.native.frameSwapped.emit()
        records=collector.poll()
        assert len(records)==1 and records[0]['status']=='success' and records[0]['presented'] is True
        before=dict(records[0]);assert 'opengl_gpu_timing' not in records[0]
        assert records[0]['opengl_paint_counters']['gl_draw_calls']==1
        assert records[0]['opengl_paint_counters']['gl_clear_calls']==1
        completions=BENCH.FrameCompletionSamples();completions.begin(0,'measured');completions.collect(records,'measured')
        for query in gl.available:gl.available[query]=True
        collector.drain_gpu(0,1,1,completions=completions,phase='measured')
        samples=completions.samples('measured');collector.queries.join(samples)
        assert {key:value for key,value in samples[0].items() if key!='opengl_gpu_timing'}==before
        assert collector.counters()['gl_application_presents']==1
        assert collector.counters()['gl_zero_timeout_poll_calls']==2
        assert collector.counters()['gl_finish_calls']==collector.counters()['gl_blocking_client_wait_calls']==0
        assert collector.boundary['scanout_measured'] is False
    finally:collector.close()
    assert canvas.native.frameSwapped.callbacks==[]


def test_GL_reference_rejects_frameSwapped_before_the_owning_paint_tail():
    gl=_ProtocolGL()
    def early_present(canvas,current):canvas.native.frameSwapped.emit()
    canvas,current,qt=_protocol_canvas(gl,early_present);adapter=_protocol_adapter(gl)
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter)
    try:
        collector.begin(0);canvas._backend.paintGL()
        assert collector.failure and 'precedes' in collector.failure
        # The later scene paint may close its own fence, but no presentation
        # fence was created at the invalid early signal.
        assert len([1 for name,args in gl.calls if name=='fence'])==1
        with pytest.raises(BENCH.InstrumentationUnavailable,match='precedes'):collector.poll()
        assert not collector.fences
    finally:collector.close()


def test_GL_unowned_actual_present_is_reported_and_pending_sync_is_deleted_on_close():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter)
    collector.begin(0);canvas._backend.paintGL();canvas.native.frameSwapped.emit()
    canvas.native.frameSwapped.emit() # actual extra signal, never silently attributed to frame0
    assert collector.counters()['gl_application_presents']==2
    assert collector.counters()['gl_unattributed_presents']==1
    assert len(collector.fences)==1
    collector.close()
    assert len([1 for name,args in gl.calls if name=='delete-fence'])==2
    assert not collector.queries.ready()
    assert not any(name in ('finish','client-wait','server-wait') for name,args in gl.calls)


def test_GL_presentation_fence_is_owned_before_flush_failure_and_deleted_on_close():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter)
    collector.begin(0);canvas._backend.paintGL()
    scene_fence=collector.paint_fences[0]
    gl.fail='flush' # Real API failure only AFTER a presentation sync was created.
    canvas.native.frameSwapped.emit()
    assert collector.failure and 'original GL failure flush' in collector.failure
    assert len(collector.fences)==1 and collector.fences[0][:2]==collector.waiting
    presentation_fence=collector.fences[0][2]
    assert presentation_fence is not scene_fence
    with pytest.raises(BENCH.InstrumentationUnavailable,match='original GL failure flush'):
        collector.poll()
    collector.close()
    deleted=[args[0] for name,args in gl.calls if name=='delete-fence']
    assert len(deleted)==2 and scene_fence in deleted and presentation_fence in deleted
    assert not collector.fences and not collector.paint_fences and not collector.queries.ids
    assert canvas.native.frameSwapped.callbacks==[]
    assert not any(name in ('finish','client-wait','server-wait') for name,args in gl.calls)


def test_GL_query_pool_constructor_failure_rolls_back_real_method_wrappers_and_queries():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    old=canvas.set_current
    canvas._backend.paintGL=len # a C builtin has no required Python paint body
    with pytest.raises(RuntimeError,match='Python Qt paintGL'):
        BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext)
    assert canvas.set_current is old and canvas._backend.paintGL is len
    assert len([1 for name,args in gl.calls if name=='delete-queries'])==1


def test_GL_query_result_retention_bound_fails_without_dropping_pending_record():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext,capacity=1,result_limit=1)
    try:
        queries.begin(0);canvas._backend.paintGL()
        for query in gl.available:gl.available[query]=True
        queries.poll()
        queries.begin(1);canvas._backend.paintGL()
        for query in gl.available:gl.available[query]=True
        with pytest.raises(RuntimeError,match='result retention'):queries.poll()
        assert set(queries.results)=={0} and set(queries.pending)=={1}
    finally:queries.close()


def test_GL_resource_descriptor_bound_is_explicit_not_a_silent_counter_reset():
    gl=_ProtocolGL();adapter=_protocol_adapter(gl)
    telemetry=BENCH.OpenGLAttribution([('vispy',adapter),('raw',gl)],descriptor_limit=1)
    try:
        adapter.glCreateBuffer();adapter.glCreateTexture()
        with pytest.raises(RuntimeError,match='descriptor bound'):telemetry.snapshot()
        assert telemetry.totals['gl_buffer_created_names']==telemetry.totals['gl_texture_created_names']==1
    finally:telemetry.close()


def test_GL_texture_storage_records_actual_requested_descriptor_without_inventing_driver_bytes():
    gl=_ProtocolGL();telemetry=BENCH.OpenGLAttribution([('raw',gl)])
    try:
        gl.glTexImage3D(1,0,17,7,6,5,0,3,4,None)
        metadata=telemetry.metadata()
        assert metadata['recent_texture_storage_descriptors']==[dict(operation='glTexImage3D',dimensions=[7,6,5],
            internal_format=17,success=True,scope='requested texture storage descriptor; no inferred driver bytes')]
        assert telemetry.snapshot()['gl_texture_storage_calls']==1
        assert telemetry.snapshot()['gl_texture_upload_bytes']==0
    finally:telemetry.close()


def test_GL_queries_are_same_context_but_presentation_sync_can_use_verified_sharing_context():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter)
    try:
        collector.begin(0);canvas._backend.paintGL()
        sharing_compositor=object();current['value']=sharing_compositor
        canvas.native.frameSwapped.emit()
        assert current['value'] is sharing_compositor # callback never forces a context
        assert collector.boundary['presentation_context_is_scene_context'] is False
        with pytest.raises(RuntimeError,match='different or missing'):collector.queries.poll()
        records=collector.poll() # explicit existing owner-context fence polling
        assert len(records)==1 and records[0]['scene_and_presentation_syncs_signaled'] is True
        assert records[0]['opengl_fence_contexts']==dict(presentation_context_is_scene_context=False,compatible_share_group_verified=True)
        assert current['value'] is canvas.native.context()
    finally:collector.close()


def test_GL_completion_requires_both_scene_and_presentation_syncs_without_query_readback_wait():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter)
    try:
        collector.begin(0);canvas._backend.paintGL();canvas.native.frameSwapped.emit()
        scene_fence=collector.paint_fences[0]
        real_wait=gl.glClientWaitSync
        def pending_scene(sync,flags,timeout):
            real_wait(sync,flags,timeout)
            return gl.GL_TIMEOUT_EXPIRED if sync is scene_fence else gl.GL_ALREADY_SIGNALED
        gl.glClientWaitSync=pending_scene
        assert collector.poll()==[]
        assert len(collector.fences)==1 and set(collector.paint_fences)=={0}
        gl.glClientWaitSync=real_wait
        records=collector.poll()
        assert len(records)==1 and records[0]['scene_and_presentation_syncs_signaled'] is True
        assert not any(name=='result' for name,args in gl.calls)
    finally:collector.close()


def test_upstream_worker_observes_cold_GL_then_measures_and_joins_timestamp_samples_under_CPU_fakes(monkeypatch,tmp_path):
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    name='image-scalar-1-translucent-resident';workload=BENCH.CATALOG[name]
    gl.GL_VENDOR=11;gl.GL_RENDERER=12;gl.GL_VERSION=13
    gl.glGetString=lambda token:b'explicit CPU fake'
    canvas.physical_size=workload.viewport
    canvas.render=lambda **kw:np.zeros((1,1,4),np.uint8)
    canvas.close=lambda:None
    pending={'value':False}
    canvas.update=lambda:pending.update(value=True)
    def events():
        if pending['value']:
            pending['value']=False;canvas._backend.paintGL()
            canvas.native.frameSwapped.emit()
            for query in gl.available:gl.available[query]=True
    canvas.app.process_events=events
    def build(*args):
        adapter.glCompileShader(1);adapter.glLinkProgram(2)
        adapter.glBufferData(1,_ObservedBytes(64),2)
        adapter.glTexSubImage2D(1,0,0,0,3,4,_ObservedBytes(192))
        return canvas,lambda frame:0,'explicit-CPU-fake-data'
    monkeypatch.setitem(sys.modules,'vispy',SimpleNamespace(use=lambda **kw:None))
    monkeypatch.setitem(sys.modules,'vispy.gloo',SimpleNamespace(gl=adapter))
    monkeypatch.setitem(sys.modules,'OpenGL',SimpleNamespace(GL=gl))
    monkeypatch.setitem(sys.modules,'PyQt6',SimpleNamespace())
    monkeypatch.setitem(sys.modules,'PyQt6.QtGui',SimpleNamespace(QOpenGLContext=qt))
    monkeypatch.setattr(BENCH,'package_provenance',lambda kind:dict(explicit_CPU_fake=True))
    _install_fake_fresh_qt_setup(monkeypatch)
    monkeypatch.setattr(BENCH,'build_scene',build)
    monkeypatch.setattr(BENCH,'make_presentation_pacing',lambda canvas:_CPUOwnedPacing())
    class PythonTelemetry:
        def __init__(self,*a,**kw):self.frames={};self.paint_methods=['paintGL']
        def begin(self,frame):self.frames[frame]=dict(python_update_calls=1,python_draw_calls=1)
        def update(self,fn,frame):return fn(frame)
        def snapshot(self):return dict(unattributed_draw_calls=0,unattributed_glir_parse_calls=0)
        def close(self):pass
    monkeypatch.setattr(BENCH,'PythonFrameTelemetry',PythonTelemetry)
    options=SimpleNamespace(worker='upstream',workload=name,output=tmp_path,run_index=0,
        warmup=1,frames=2,queue_depth=3,vsync=False,timeout=1)
    assert BENCH.run_worker(options)==0
    result=json.loads((tmp_path/'run.json').read_text())
    assert result['provenance']==dict(explicit_CPU_fake=True)
    assert result['qt_presentation_setup']['actual_context_swap_interval']==0
    assert result['opengl_cold_counters_before']['gl_shader_compile_calls']==0
    assert result['opengl_cold_counters_after']['gl_shader_compile_calls']==1
    assert result['opengl_cold_counters_after']['gl_buffer_upload_bytes']==64
    assert result['measured_work_validation']['status']=='passed'
    assert result['counter_delta']['gl_shader_compile_calls']==result['counter_delta']['gl_texture_upload_calls']==0
    samples=json.loads((tmp_path/'samples.json').read_text())
    assert len(samples)==2 and all(s['scene_and_presentation_syncs_signaled'] for s in samples)
    assert all(s['opengl_gpu_timing']['includes_alpha_tail'] and not s['opengl_gpu_timing']['qt_compositor_included'] for s in samples)
    assert len(json.loads((tmp_path/'observed-opengl-timings.json').read_text()))==3
    assert result['instrumentation_gaps']==['input-to-visible scanout measurement','complete driver/allocator allocation peak accounting']


def test_GL_dispatch_rebinding_cannot_turn_real_compile_calls_into_false_zero_counters():
    gl=_ProtocolGL();adapter=_protocol_adapter(gl)
    original=adapter.glCompileShader
    telemetry=BENCH.OpenGLAttribution([('vispy',adapter),('raw',gl)])
    try:
        adapter.glCompileShader=original # simulates gloo.use_gl replacing the dispatch table
        adapter.glCompileShader(9)
        assert telemetry.metadata()['call_hooks_unchanged'] is False
        with pytest.raises(RuntimeError,match='call hooks changed'):telemetry.snapshot()
    finally:telemetry.close()


@pytest.mark.parametrize('start,elapsed',[(2**53+7,11),(2**63+17,23),(2**64-50,49)])
def test_GL_timestamp_uint64_client_output_is_exact_without_implicit_allocation(start,elapsed):
    import ctypes
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext)
    outputs=[]
    original=gl.glGetQueryObjectui64v
    def explicit(query,pname,output):
        assert isinstance(output,ctypes.Array) and output._type_ is ctypes.c_uint64
        assert len(output)==1 and ctypes.sizeof(output)==8
        outputs.append(output)
        original(query,pname,output)
        return -999 # The client output, not wrapper return, is authoritative.
    gl.glGetQueryObjectui64v=explicit
    try:
        queries.begin(0);canvas._backend.paintGL()
        pair=queries.pending[0]['queries']
        gl.values[pair[0]],gl.values[pair[1]]=start,start+elapsed
        for query in pair:gl.available[query]=True
        queries.poll()
        record=queries.results[0]
        assert type(record['begin_ns']) is type(record['end_ns']) is int
        assert record['begin_ns']==start and record['end_ns']==start+elapsed and record['elapsed_ns']==elapsed
        assert len(outputs)==2 and outputs[0] is not outputs[1]
    finally:queries.close()


def test_GL_explicit_uint64_read_failure_retains_pending_pair_and_close_deletes_queries():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl)
    original_current,original_paint=canvas.set_current,canvas._backend.paintGL
    queries=BENCH.OpenGLPaintQueries(gl,canvas,qt.currentContext)
    try:
        queries.begin(0);canvas._backend.paintGL()
        pair=queries.pending[0]['queries']
        gl.available[pair[0]]=True
        queries.poll()
        assert not any(name=='result' for name,args in gl.calls) # BOTH available first.
        gl.available[pair[1]]=True;gl.fail='result'
        with pytest.raises(ValueError,match='original GL failure result'):queries.poll()
        assert set(queries.pending)=={0} and not queries.results
        current['value']=object()
        with pytest.raises(RuntimeError,match='different or missing'):queries.poll()
        current['value']=canvas.native.context()
    finally:queries.close()
    assert not queries.ids and len([1 for name,args in gl.calls if name=='delete-queries'])==1
    assert canvas.set_current is original_current and canvas._backend.paintGL is original_paint


def _fake_qt_presentation(*, application=None, current=None, ignore_request=False):
    """Explicit CPU Qt protocol, with no real Qt import or application."""
    calls=[]
    class Format:
        default={'swap_interval':1,'depth':24,'stencil':8,'samples':0,'version':(2,0),'profile':'unchanged'}
        def __init__(self,other):self.values=dict(other.values)
        def swapInterval(self):return self.values['swap_interval']
        def setSwapInterval(self,value):calls.append(('request',value));self.values['swap_interval']=value
        @classmethod
        def defaultFormat(cls):
            calls.append(('default-read',))
            result=object.__new__(cls);result.values=dict(cls.default);return result
        @classmethod
        def setDefaultFormat(cls,value):
            calls.append(('default-write',dict(value.values)))
            if not ignore_request:cls.default=dict(value.values)
    def instance():calls.append(('application-check',));return application
    def current_context():calls.append(('context-check',));return current
    core=SimpleNamespace(QCoreApplication=SimpleNamespace(instance=instance))
    gui=SimpleNamespace(QSurfaceFormat=Format,QOpenGLContext=SimpleNamespace(currentContext=current_context))
    return core,gui,calls


def _install_fake_fresh_qt_setup(monkeypatch):
    core,gui,calls=_fake_qt_presentation()
    original=BENCH.configure_qt_presentation
    monkeypatch.setattr(BENCH,'configure_qt_presentation',lambda vsync,record:original(vsync,record,qt_core=core,qt_gui=gui))
    return core,gui,calls


@pytest.mark.parametrize('vsync',[False,True])
def test_Qt_default_pacing_is_configured_before_any_application_without_changing_quality(vsync):
    core,gui,calls=_fake_qt_presentation()
    before=dict(gui.QSurfaceFormat.default)
    observation={}
    returned=BENCH.configure_qt_presentation(vsync,observation,qt_core=core,qt_gui=gui)
    assert returned is observation
    assert observation['previous_default_swap_interval']==1
    assert observation['requested_default_swap_interval']==observation['readback_default_swap_interval']==int(vsync)
    assert observation['preexisting_application'] is observation['preexisting_current_GL_context'] is False
    assert gui.QSurfaceFormat.default==dict(before,swap_interval=int(vsync))
    assert [event[0] for event in calls]==['application-check','context-check','default-read','request','default-write','default-read']
    assert 'not actual presentation evidence' in observation['scope']


@pytest.mark.parametrize('existing',['application','current-context'])
def test_Qt_pacing_setup_rejects_preexisting_application_or_current_context_without_mutation(existing):
    core,gui,calls=_fake_qt_presentation(application=object() if existing=='application' else None,
        current=object() if existing=='current-context' else None)
    observation={}
    with pytest.raises(BENCH.InstrumentationUnavailable,match='fresh process before application/context'):
        BENCH.configure_qt_presentation(False,observation,qt_core=core,qt_gui=gui)
    assert not any(event[0] in ('default-read','default-write','request') for event in calls)
    assert observation['preexisting_application'] is (existing=='application')
    assert observation['preexisting_current_GL_context'] is (existing=='current-context')


def test_Qt_pacing_setup_retains_ignored_default_request_and_refuses():
    core,gui,calls=_fake_qt_presentation(ignore_request=True)
    observation={}
    with pytest.raises(BENCH.InstrumentationUnavailable,match='immediate readback'):
        BENCH.configure_qt_presentation(False,observation,qt_core=core,qt_gui=gui)
    assert observation['previous_default_swap_interval']==observation['readback_default_swap_interval']==1
    assert observation['requested_default_swap_interval']==0


@pytest.mark.parametrize('bad',[None,0,1,'false'])
def test_Qt_pacing_setup_requires_boolean_intent(bad):
    with pytest.raises(ValueError,match='boolean vsync'):
        BENCH.configure_qt_presentation(bad)


@pytest.mark.parametrize('kind',['upstream','candidate'])
@pytest.mark.parametrize('vsync',[False,True])
def test_both_real_worker_branches_configure_default_before_scene_creation(monkeypatch,tmp_path,kind,vsync):
    gl=_ProtocolGL();adapter=_protocol_adapter(gl)
    native=SimpleNamespace(benchmark_begin_frame=lambda:None,benchmark_completions=lambda:None,benchmark_surface_info=lambda:None)
    monkeypatch.setitem(sys.modules,'vispy',SimpleNamespace(use=lambda **kw:None,_dawn=native))
    monkeypatch.setitem(sys.modules,'vispy.gloo',SimpleNamespace(gl=adapter))
    monkeypatch.setitem(sys.modules,'OpenGL',SimpleNamespace(GL=gl))
    core,gui,calls=_install_fake_fresh_qt_setup(monkeypatch)
    monkeypatch.setattr(BENCH,'package_provenance',lambda role:dict(explicit_CPU_fake=True))
    def build(*args):
        assert calls[-1][0]=='default-read'
        assert gui.QSurfaceFormat.default['swap_interval']==int(vsync)
        raise RuntimeError('explicit fake scene reached after default setup')
    monkeypatch.setattr(BENCH,'build_scene',build)
    options=SimpleNamespace(worker=kind,workload='image-scalar-1-translucent-resident',output=tmp_path,
        run_index=0,warmup=1,frames=1,queue_depth=1,vsync=vsync,timeout=1)
    assert BENCH.run_worker(options)==2
    result=json.loads((tmp_path/'run.json').read_text())
    assert 'explicit fake scene reached' in result['error']
    assert result['qt_presentation_setup']['readback_default_swap_interval']==int(vsync)
    assert result['qt_presentation_setup']['preexisting_application'] is False


@pytest.mark.parametrize('scene_format,interval,accepted',[(1,0,True),(0,1,False),(0,-1,False),(0,None,False),(0,False,False),(0,0.0,False)])
def test_actual_owned_receipt_controls_collector_not_scene_format(scene_format,interval,accepted):
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);adapter=_protocol_adapter(gl)
    canvas.native.context().format=lambda:SimpleNamespace(swapInterval=lambda:scene_format)
    class Observer(_CPUOwnedPacing):
        def observe(self,frame_id,*,closed_frame_id):
            value=super().observe(frame_id,closed_frame_id=closed_frame_id)
            value['interval']=interval;self.records[-1]=json.loads(json.dumps(value));return value
    observer=Observer();collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=adapter,
        pacing_observer=observer,require_unpaced=True)
    try:
        assert collector.surface['scene_context_swap_interval']==scene_format
        assert collector.surface['pacing_disabled']is False
        collector.begin(0);canvas._backend.paintGL();canvas.native.frameSwapped.emit()
        assert len(observer.records)==1 and observer.records[0]['interval']==interval and type(observer.records[0]['interval'])is type(interval)
        if accepted:
            rows=collector.poll();assert len(rows)==1
            BENCH._pacing.validate_completed_samples(rows,[0])
        else:
            assert collector.failure and len(collector.paint_fences)==1 and not collector.fences
            with pytest.raises(BENCH.InstrumentationUnavailable):collector.poll()
    finally:collector.close()
    assert not collector.paint_fences and not collector.fences and not collector.queries.ids
    assert canvas.native.frameSwapped.callbacks==[]
    assert not any(name in('finish','server-wait')for name,args in gl.calls)


def test_pacing_getter_not_called_for_unowned_or_unclosed_presentation():
    gl=_ProtocolGL()
    def early(canvas,current):canvas.native.frameSwapped.emit()
    canvas,current,qt=_protocol_canvas(gl,early);observer=_CPUOwnedPacing()
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=_protocol_adapter(gl),pacing_observer=observer,require_unpaced=True)
    try:
        canvas.native.frameSwapped.emit();assert observer.records==[]
        collector.begin(0);canvas._backend.paintGL()
        assert collector.failure and 'precedes'in collector.failure and observer.records==[]
        assert not collector.fences and set(collector.paint_fences)=={0}
    finally:collector.close()


def test_raw_completion_keeps_immutable_receipt_and_later_failure_does_not_rewrite_it():
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);observer=_CPUOwnedPacing()
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=_protocol_adapter(gl),pacing_observer=observer,require_unpaced=True)
    try:
        collector.begin(0);canvas._backend.paintGL();canvas.native.frameSwapped.emit();rows=collector.poll()
        before=json.loads(json.dumps(rows))
        observer.records[0]['before']['native']['hglrc']=0
        assert rows==before
        collector.verify_pacing(rows,[0])
    finally:collector.close()


@pytest.mark.parametrize('mutation',['missing','interval1','interval_bool','interval_float','bad_frame','bad_hwnd','bad_thread','bad_context','unstable','unknown','sample_none','duplicate','gap','reordered'])
def test_release_gate_independently_rechecks_every_upstream_raw_receipt(mutation):
    reference=runs(12,15);candidate=runs(10,15)
    row=reference[0]['_release_upstream_completed_samples'][500]
    if mutation=='missing':row.pop('presentation_pacing')
    elif mutation=='interval1':row['presentation_pacing']['interval']=1
    elif mutation=='interval_bool':row['presentation_pacing']['interval']=False
    elif mutation=='interval_float':row['presentation_pacing']['interval']=0.0
    elif mutation=='bad_frame':row['presentation_pacing']['frame_id']=499
    elif mutation=='bad_hwnd':row['presentation_pacing']['before']['native']['window']=99;row['presentation_pacing']['after']['native']['window']=99
    elif mutation=='bad_thread':row['presentation_pacing']['before']['native']['thread_id']=99;row['presentation_pacing']['after']['native']['thread_id']=99
    elif mutation=='bad_context':row['presentation_pacing']['before']['native']['hglrc']=0;row['presentation_pacing']['after']['native']['hglrc']=0
    elif mutation=='unstable':row['presentation_pacing']['after']['native']['hdc']=99
    elif mutation=='unknown':row['presentation_pacing']['status']='unproven'
    elif mutation=='sample_none':reference[0]['_release_upstream_completed_samples'][500]=None
    elif mutation=='duplicate':reference[0]['_release_upstream_completed_samples'][500]=reference[0]['_release_upstream_completed_samples'][499]
    elif mutation=='gap':reference[0]['_release_upstream_completed_samples'].pop(500)
    else:
        rows=reference[0]['_release_upstream_completed_samples'];rows[499],rows[500]=rows[500],rows[499]
    # All producer summary booleans and the final sample remain passing.
    assert reference[0]['surface']['pacing_disabled']is True
    assert reference[0]['_release_upstream_completed_samples'][-1]['presentation_pacing']['interval']==0
    result=gate(reference,candidate)
    assert result['status']=='unproven'and any('each completed upstream sample'in reason for reason in result['reasons'])


@pytest.mark.parametrize('missing',[True,False])
def test_closed_paint_missing_or_unshared_current_retains_unproven_snapshot_without_native_query(missing):
    gl=_ProtocolGL();canvas,current,qt=_protocol_canvas(gl);thread=object();native_queries=[]
    top=SimpleNamespace(thread=lambda:thread,winId=lambda:1)
    canvas.native.window=lambda:SimpleNamespace(windowHandle=lambda:top)
    canvas.native.thread=lambda:thread
    foreign=SimpleNamespace(surface=lambda:top,thread=lambda:thread,isValid=lambda:True)
    qt.areSharing=lambda a,b:False
    qt_thread=SimpleNamespace(currentThread=lambda:thread,currentThreadId=lambda:1)
    def denied():native_queries.append(True);raise AssertionError('native query before Qt ownership')
    observer=BENCH._pacing.WindowsPresentationPacing(canvas,qt,qt_thread,native_factory=denied,platform='win32')
    collector=BENCH.OpenGLCompletions(canvas,gl=gl,qt_context=qt,gl_adapter=_protocol_adapter(gl),pacing_observer=observer,require_unpaced=True)
    try:
        collector.begin(0);canvas._backend.paintGL();current['value']=None if missing else foreign
        canvas.native.frameSwapped.emit()
        assert collector.failure and len(observer.records)==1 and not native_queries
        row=collector.presentation_receipts[0]
        assert row['status']=='unproven'and row['owned_after_closed_paint']is True and row['errors']
        assert row['before']['qt_current_context']==(None if missing else id(foreign))
        assert not collector.fences and set(collector.paint_fences)=={0}
    finally:canvas.set_current();collector.close()
    assert not collector.paint_fences and not collector.queries.ids
