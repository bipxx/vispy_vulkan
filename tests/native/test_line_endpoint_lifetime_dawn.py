"""Independent future-native endpoint lifetime gates, authored before execution.

The eight admitted D1 outputs remain the oracle. The matrix revision below is
an explicit binary-exact analytic extension of the original declared formula.
These are headless private ABI ownership gates, not visible Qt/line raster gates.
Quality collection may wait and is kept outside resident intervals. A missing
real submitted/queued witness is an unresolved hardware failure, never a skip.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import pytest

from tools import fixture_line_endpoints_dawn as f

RESIDENT_ZERO = (
    "buffer_allocations", "bind_group_creations", "buffer_uploads", "geometry_upload_bytes",
    "texture_allocations", "texture_uploads", "texture_upload_bytes",
    "line_endpoint_conversion_builds", "line_endpoint_conversion_bytes", "line_endpoint_upload_bytes",
    "vertex_input_conversion_builds", "vertex_input_conversion_bytes", "point_conversion_builds",
    "shader_normalizations", "shader_parse_calls", "shader_link_calls", "shader_spirv_stages",
    "shader_module_creations", "render_pipeline_creations", "compute_pipeline_creations",
    "pipeline_misses", "portable_shader_misses", "line_evaluator_misses", "completion_waits", "finish_calls",
)
POOL_GAUGES = ("line_resource_pool_slots", "line_resource_pool_busy_slots", "line_resource_pool_bytes")
QUERY_COUNTERS = ("timestamp_query_sets", "timestamp_resolves", "timestamp_readbacks")
NO_SURFACE_PRESENT = (1 << 64) - 1
OBSERVATION_ATTEMPTS = 16


def matrix_revision():
    """Fixed B input/output from original GLSL, not any candidate layout/data.

    B adds .5 to source X and transform translation, .5 to basis diagonal,
    .25 to both offsets, changes flip true->false, flags17->9. C restores A.
    Multiplication/addition stages are float32 and every value is binary exact.
    """
    original = f.load_case("matrices_arrays")
    revised = {**original, "arrays": dict(original["arrays"]), "expected": {}}
    position = original["arrays"]["input-buffer-vertex"].copy()
    position[:, 0] += np.float32(.5)
    transform = original["arrays"]["input-uniform-u_transform"].copy()
    transform[0, 3] += np.float32(.5)
    basis = original["arrays"]["input-uniform-u_basis"].copy()
    basis += np.eye(3, dtype=np.float32) * np.float32(.5)
    offsets = original["arrays"]["input-uniform-u_offsets"].copy() + np.float32(.25)
    revised["arrays"].update({"input-buffer-vertex": position,
                              "input-uniform-u_transform": transform,
                              "input-uniform-u_basis": basis,
                              "input-uniform-u_offsets": offsets})
    contract = copy.deepcopy(original["contract"])
    contract["uniforms"]["u_flip"]["value"] = False
    contract["uniforms"]["u_flags"]["value"] = 9
    revised["contract"] = contract
    ids = original["expected"]["v_ids"].copy()
    vertex_ids = ids[:, 0].astype(np.int32)
    selected = position[vertex_ids]
    clip = np.empty_like(selected)
    # Match the explicit original diagonal/translation expression, no BLAS.
    clip[:, 0] = selected[:, 0] * transform[0, 0] + selected[:, 3] * transform[0, 3]
    clip[:, 1] = selected[:, 1] * transform[1, 1] + selected[:, 3] * transform[1, 3]
    clip[:, 2] = selected[:, 2] + selected[:, 3] * transform[2, 3]
    clip[:, 3] = selected[:, 3]
    bases = np.repeat(basis[None], len(ids), axis=0)
    for row, identity in enumerate(vertex_ids):
        bases[row] += np.eye(3, dtype=np.float32) * (np.float32(identity) * np.float32(.5))
    arrays = np.empty((len(ids), 2, 2), dtype=np.float32)
    arrays[:, 0] = selected[:, :2] + offsets[0]
    arrays[:, 1] = selected[:, 2:] + offsets[1]
    codes = original["expected"]["v_codes"].copy()
    codes[:, 1, 0] = vertex_ids
    codes[:, 1, 1] = 9
    revised["expected"] = {"gl_Position": clip, "v_ids": ids, "v_basis": bases,
                            "v_array": arrays, "v_codes": codes}
    for value in (*revised["expected"].values(), position, transform, basis, offsets):
        value.flags.writeable = False
    return original, revised


def revision_commands(case, program, vertex_buffer):
    result = [("DATA", vertex_buffer, 0, f.blob(case["arrays"]["input-buffer-vertex"]))]
    for name in ("u_transform", "u_basis", "u_offsets", "u_flip", "u_flags"):
        metadata = case["contract"]["uniforms"][name]
        kind = metadata["type"]
        if name in {"u_flip", "u_flags"}:
            value = np.asarray([metadata["value"]], dtype=np.bool_ if name == "u_flip" else np.uint32)
        else:
            value = case["arrays"]["input-uniform-" + name]
            if kind.startswith("mat"):
                value = value.T.copy()
        result.append(("UNIFORM", program, name, kind, f.blob(value)))
    return result


def uniform_only_revision():
    """Original A vertex data with exactly the declared B uniforms.

    This independent third expectation isolates uniform transport from DATA.
    The original GLSL and logical vertex/instance selection remain unchanged.
    """
    original, revised = matrix_revision()
    result = {**revised, "arrays": dict(revised["arrays"]),
              "expected": {name: value.copy() for name, value in revised["expected"].items()}}
    position = original["arrays"]["input-buffer-vertex"]
    result["arrays"]["input-buffer-vertex"] = position
    ids = result["expected"]["v_ids"][:, 0].astype(np.int32)
    selected = position[ids]
    transform = result["arrays"]["input-uniform-u_transform"]
    clip = result["expected"]["gl_Position"]
    clip[:, 0] = selected[:, 0] * transform[0, 0] + selected[:, 3] * transform[0, 3]
    clip[:, 1] = selected[:, 1] * transform[1, 1] + selected[:, 3] * transform[1, 3]
    clip[:, 2] = selected[:, 2] + selected[:, 3] * transform[2, 3]
    clip[:, 3] = selected[:, 3]
    offsets = result["arrays"]["input-uniform-u_offsets"]
    result["expected"]["v_array"][:, 0] = selected[:, :2] + offsets[0]
    result["expected"]["v_array"][:, 1] = selected[:, 2:] + offsets[1]
    for value in result["expected"].values():
        value.flags.writeable = False
    return original, result


def uniform_only_commands(case, program):
    # Reuse unchanged original typed transport, omitting the DATA command.
    return [value for value in revision_commands(case, program, 0) if value[0] == "UNIFORM"]


def _delta(after, before, key):
    assert type(after[key]) is int and type(before[key]) is int
    value = after[key] - before[key]
    assert value >= 0, "cumulative counter must not reset: " + key
    return value


def _resident(before, after, frames, rows):
    for key in RESIDENT_ZERO:
        assert _delta(after, before, key) == 0, "resident cost: " + key
    for key in QUERY_COUNTERS:
        assert _delta(after, before, key) == 0, "queries disabled: " + key
    for key in ("draw_calls", "line_endpoint_dispatches", "compute_passes", "dawn_queue_submits", "retired_tickets"):
        assert _delta(after, before, key) == frames, "real execution: " + key
    assert _delta(after, before, "line_endpoint_rows") == rows * frames
    assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
    assert after["line_resource_pool_busy_slots"] == before["line_resource_pool_busy_slots"] == 0
    assert after["line_resource_pool_slots"] == before["line_resource_pool_slots"] > 0
    assert after["line_resource_pool_bytes"] == before["line_resource_pool_bytes"] > 0
    assert _delta(after, before, "line_resource_pool_hits") >= frames
    assert _delta(after, before, "line_resource_pool_evictions") == 0
    assert _delta(after, before, "line_resource_pool_deferrals") == 0
    # Identical UBO byte shadows may avoid writes; cumulative bytes stay monotonic.
    assert _delta(after, before, "uniform_upload_bytes") >= 0


def _changed_ubo_upload(before, after):
    # Used only with the fixed, intentionally different A/B uniform commands.
    assert _delta(after, before, "uniform_upload_bytes") > 0, "changed UBO bytes require an actual upload"


def _receipt(record, frame_id, generation, *, status="success", token=0, submissions=1):
    assert record["frame_id"] == frame_id and type(record["frame_id"]) is int
    assert record["paint_token"] == token
    assert record["frame_scope"] == ("qt_paint" if token else "native_present")
    assert record["status"] == status
    assert record["ownership_closed"] is True and record["ownership_retired"] is True
    assert record["submission_count"] == submissions
    assert record["present_count"] == 0 and record["presented"] is False
    assert record["last_present_submission_index"] == NO_SURFACE_PRESENT
    assert record["counters_captured"] is True and record["counter_capture"] == "submission"
    assert record["counters"]["device_generation"] == generation
    if status == "success":
        assert record["error"] == ""
    else:
        assert isinstance(record["error"], str) and record["error"]


def _timing(record, receipt, generation):
    assert record["status"] == "success" and record["error"] == ""
    assert record["frame_id"] == receipt["frame_id"] and record["paint_token"] == 0
    assert record["frame_scope"] == "native_present" and record["device_generation"] == generation
    assert record["submission_count"] == receipt["submission_count"] == 1
    assert record["last_present_submission_index"] == NO_SURFACE_PRESENT
    passes = record["passes"]
    assert [row["kind"] for row in passes] == ["line_endpoints", "scene", "present_capture"]
    assert all(row["submission_index"] == 0 for row in passes)
    for row in passes:
        assert all(type(row[k]) is int and row[k] >= 0 for k in ("begin_ns", "end_ns", "elapsed_ns"))
        assert row["begin_ns"] <= row["end_ns"]
        assert row["elapsed_ns"] == row["end_ns"] - row["begin_ns"]
    assert record["pass_sum_ns"] == sum(row["elapsed_ns"] for row in passes)
    assert record["render_span_ns"] == max(row["end_ns"] for row in passes) - min(row["begin_ns"] for row in passes)


def test_cpu_matrix_revision_uses_fixed_binary_exact_shader_formula():
    original, revised = matrix_revision()
    assert original["expected"]["gl_Position"][0].tolist() == [1.3125, -.75, .28125, 1.25]
    assert revised["expected"]["gl_Position"][0].tolist() == [2.9375, -.75, .28125, 1.25]
    assert revised["expected"]["v_array"][0].tolist() == [[1.375, .25], [-.125, 2.5]]
    assert np.diag(revised["expected"]["v_basis"][0]).tolist() == [2., 3., 4.]
    assert revised["expected"]["v_codes"][0].tolist() == [[1, 0], [1, 9]]
    assert original["vertex"] == revised["vertex"] and original["fragment"] == revised["fragment"]
    assert original["contract"]["selection"] == revised["contract"]["selection"]
    for key in revised["expected"]:
        assert not np.shares_memory(original["expected"][key], revised["expected"][key])
        assert not revised["expected"][key].flags.writeable
    f.exact(original["expected"]["v_ids"], revised["expected"]["v_ids"])
    for key in ("gl_Position", "v_array", "v_basis", "v_codes"):
        with pytest.raises(AssertionError):
            f.exact(revised["expected"][key], original["expected"][key])


def test_cpu_revision_transport_is_full_DATA_and_exact_matrix_scalar_carriers():
    original, revised = matrix_revision()
    original_hashes = {key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in original["arrays"].items()}
    commands = revision_commands(revised, 600000, 600003)
    assert [value[0] for value in commands] == ["DATA"] + ["UNIFORM"] * 5
    assert commands[0][1:3] == (600003, 0)
    assert commands[0][3]["__bytes__"] == revised["arrays"]["input-buffer-vertex"].tobytes()
    for key in ("u_transform", "u_basis"):
        value = next(value[4] for value in commands if value[:3] == ("UNIFORM", 600000, key))
        assert value["__bytes__"] == np.ascontiguousarray(revised["arrays"]["input-uniform-" + key].T).tobytes()
    flags = next(value[4] for value in commands if value[:3] == ("UNIFORM", 600000, "u_flags"))
    assert flags["dtype"] == "<u4" and np.frombuffer(flags["__bytes__"], "<u4").tolist() == [9]
    assert original_hashes == {key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in original["arrays"].items()}


def test_cpu_uniform_only_expectation_preserves_A_data_and_original_shader_formula():
    original, uniform = uniform_only_revision()
    assert uniform["vertex"] == original["vertex"] and uniform["fragment"] == original["fragment"]
    f.exact(original["arrays"]["input-buffer-vertex"], uniform["arrays"]["input-buffer-vertex"])
    assert uniform["contract"]["selection"] == original["contract"]["selection"]
    assert uniform["expected"]["gl_Position"][0].tolist() == [1.9375, -.75, .28125, 1.25]
    assert uniform["expected"]["v_array"][0].tolist() == [[.875, .25], [-.125, 2.5]]
    assert np.diag(uniform["expected"]["v_basis"][0]).tolist() == [2., 3., 4.]
    assert uniform["expected"]["v_codes"][0].tolist() == [[1, 0], [1, 9]]
    f.exact(original["expected"]["v_ids"], uniform["expected"]["v_ids"])
    for key in ("gl_Position", "v_array", "v_basis", "v_codes"):
        with pytest.raises(AssertionError): f.exact(uniform["expected"][key], original["expected"][key])
    assert all(not value.flags.writeable for value in uniform["expected"].values())


def test_cpu_uniform_only_transport_changes_five_uniforms_without_input_revision():
    original, uniform = uniform_only_revision()
    setup, _, _ = f.commands(original, 600000)
    updates = uniform_only_commands(uniform, 600000)
    assert len(updates) == 5 and {value[0] for value in updates} == {"UNIFORM"}
    assert [value[2] for value in updates] == ["u_transform", "u_basis", "u_offsets", "u_flip", "u_flags"]
    for value in updates:
        baseline = next(command for command in setup if command[:3] == value[:3])
        assert baseline[3] == value[3] and baseline[4]["dtype"] == value[4]["dtype"]
        assert baseline[4]["shape"] == value[4]["shape"]
        assert baseline[4]["__bytes__"] != value[4]["__bytes__"], value[2]


def _resident_control():
    """Counter predicate unit values, not a mocked native device or renderer."""
    before = {key: 100 for key in RESIDENT_ZERO + QUERY_COUNTERS}
    before.update({key: 100 for key in ("draw_calls", "line_endpoint_dispatches", "compute_passes", "dawn_queue_submits", "retired_tickets", "line_endpoint_rows", "line_resource_pool_hits", "line_resource_pool_evictions", "line_resource_pool_deferrals", "uniform_upload_bytes")})
    before.update({"pending_tickets": 0, "pending_draws": 0, "queued_frames": 0,
                   "line_resource_pool_slots": 1, "line_resource_pool_busy_slots": 0, "line_resource_pool_bytes": 8192})
    after = dict(before)
    for key in ("draw_calls", "line_endpoint_dispatches", "compute_passes", "dawn_queue_submits", "retired_tickets", "line_resource_pool_hits"):
        after[key] += 12
    after["line_endpoint_rows"] += 72
    after["uniform_upload_bytes"] += 12 * 256
    return before, after


@pytest.mark.parametrize("uniform_bytes", (0, 12 * 256))
def test_cpu_resident_predicate_accepts_zero_or_positive_unchanged_UBO_writes(uniform_bytes):
    before, after = _resident_control()
    after["uniform_upload_bytes"] = before["uniform_upload_bytes"] + uniform_bytes
    _resident(before, after, 12, 6)


def test_cpu_changed_UBO_control_requires_positive_bytes_and_rejects_counter_reset():
    before = {"uniform_upload_bytes": 100}
    _changed_ubo_upload(before, {"uniform_upload_bytes": 104})
    with pytest.raises(AssertionError, match="changed UBO bytes require an actual upload"):
        _changed_ubo_upload(before, {"uniform_upload_bytes": 100})
    with pytest.raises(AssertionError, match="cumulative counter must not reset"):
        _changed_ubo_upload(before, {"uniform_upload_bytes": 99})
    resident_before, resident_after = _resident_control()
    resident_after["uniform_upload_bytes"] = resident_before["uniform_upload_bytes"] - 1
    with pytest.raises(AssertionError, match="cumulative counter must not reset"):
        _resident(resident_before, resident_after, 12, 6)


@pytest.mark.parametrize("counter", RESIDENT_ZERO)
def test_cpu_resident_predicate_rejects_every_hidden_cost(counter):
    before, after = _resident_control()
    _resident(before, after, 12, 6)
    after[counter] += 1
    with pytest.raises(AssertionError, match="resident cost"):
        _resident(before, after, 12, 6)


@pytest.mark.parametrize("counter", ("draw_calls", "line_endpoint_dispatches", "line_endpoint_rows", "dawn_queue_submits", "retired_tickets"))
def test_cpu_resident_predicate_rejects_skipped_draw_dispatch_upload_or_retirement(counter):
    before, after = _resident_control()
    after[counter] = before[counter]
    with pytest.raises(AssertionError):
        _resident(before, after, 12, 6)


def test_cpu_lifetime_guard_precedes_import_and_quality_is_outside_warm_interval():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    native = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_native")
    guard = next(i for i, n in enumerate(native.body) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "activation_before_native")
    imports = [i for i, n in enumerate(native.body) if isinstance(n, ast.ImportFrom) and n.module == "vispy"]
    assert imports and min(imports) > guard
    assert not any(isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("vispy") for n in tree.body)
    warm = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_warm_frames")
    calls = {n.func.attr for n in ast.walk(warm) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not {"finish", "diagnostic_line_endpoints", "read_pixels", "read_presented"} & calls
    assert {"benchmark_begin_frame", "execute", "present"} <= calls


def _json(value):
    if isinstance(value, bytes): return {"hex": value.hex(), "bytes": len(value)}
    if isinstance(value, np.ndarray): return {"dtype": value.dtype.str, "shape": list(value.shape)}
    raise TypeError(type(value).__name__)


def _save(folder, label, value):
    if isinstance(value, np.ndarray):
        np.save(folder / (label + ".npy"), value, allow_pickle=False)
    else:
        (folder / (label + ".json")).write_text(json.dumps(value, indent=2, sort_keys=True, default=_json) + "\n", encoding="utf-8")


def _records(folder, label, records):
    _save(folder, label + "-metadata", [{k: v for k, v in row.items() if k not in {"data", "raw_data"}} for row in records])
    for i, row in enumerate(records):
        _save(folder, f"{label}-{i}-data", row["data"])
        _save(folder, f"{label}-{i}-raw", row["raw_data"])


def _native():
    context = f.activation_before_native(os.environ)
    from vispy import _dawn
    origin = Path(_dawn.__file__).resolve()
    assert origin.parent == f.ROOT / "src/vispy"
    assert f.sha(origin) == context["activation"]["activated"][origin.name]
    assert all(callable(getattr(_dawn, name, None)) for name in (
        "diagnostic_configure_line_endpoints", "diagnostic_line_endpoints", "benchmark_begin_frame",
        "benchmark_completions", "benchmark_gpu_timings", "benchmark_configure_gpu_timing",
        "begin_canvas_paint", "abort_canvas_paint", "execute", "probe", "process_events", "lose_device"))
    return _dawn, context


def _setup(name, capture=True):
    case = f.load_case("matrices_arrays")
    native, context = _native()
    base = Path(os.environ.get("VISPY_LINE_ENDPOINTS_EVIDENCE", "")).resolve()
    assert "VISPY_LINE_ENDPOINTS_EVIDENCE" in os.environ and base.is_relative_to(f.ROOT / "build/evidence")
    folder = base / name
    folder.mkdir(parents=True, exist_ok=False)
    _save(folder, "context", {**context, "D1_checked_inputs": case["checked_inputs"]})
    canvas = native.register_canvas(8, 8, 1, False)
    commands, draw, delete = f.commands(case, 600000)
    try:
        info = native.device_info()
        _save(folder, "device", info)
        assert info["ok"] is True and info["software"] is False
        assert info["max_compute_workgroup_size_x"] >= 64 and info["max_compute_invocations_per_workgroup"] >= 64
        assert info["max_storage_buffers_per_shader_stage"] >= 2
        native.execute(canvas, commands, [])
        timing = native.benchmark_configure_gpu_timing(canvas, False)
        native.diagnostic_configure_line_endpoints(canvas, True, capture=capture)
        probe = native.probe()
        assert all(key in probe for key in POOL_GAUGES + RESIDENT_ZERO)
        _save(folder, "commands", {"setup": commands, "draw": draw, "delete": delete, "capture": capture})
        _save(folder, "initial", {"timing": timing, "probe": probe})
    except BaseException:
        (folder / "setup-failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        try: native.execute(canvas, delete, [])
        finally: native.destroy_canvas(canvas)
        raise
    return native, canvas, case, commands, draw, delete, folder


def _drain(native, canvas, *, receipts=0, maps=0, folder=None, label="drain"):
    completion, timing, ledger = [], [], []
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        native.process_events()
        completion.extend(native.benchmark_completions(canvas))
        timing.extend(native.benchmark_gpu_timings(canvas))
        probe = native.probe()
        ledger.append(probe)
        if folder is not None:
            _save(folder, label, {"receipts": completion, "timings": timing, "probes": ledger})
        assert len(completion) <= receipts and len(timing) <= maps, "extra ownership records"
        if probe["pending_tickets"] == probe["queued_frames"] == probe["pending_draws"] == 0 and len(completion) == receipts and len(timing) == maps:
            return probe, completion, timing
        time.sleep(.001)
    raise AssertionError("actual Ticket/owner/query retirement incomplete; retained same event history")


def _close(native, canvas, delete, folder):
    try:
        _drain(native, canvas, folder=folder, label="cleanup-drain")
    finally:
        try: native.execute(canvas, delete, [])
        finally: native.destroy_canvas(canvas)


def _warm_frames(native, canvas, draw, folder, count, start_id):
    rows = []
    for number in range(count):
        frame_id = start_id + number
        native.benchmark_begin_frame(canvas, frame_id)
        native.execute(canvas, [draw], [])
        native.present(canvas)
        after, completion, timing = _drain(native, canvas, receipts=1, folder=folder, label=f"frame-{frame_id}")
        assert timing == []
        _receipt(completion[0], frame_id, after["device_generation"])
        rows.append(completion[0])
    return rows


def _quality(native, canvas, draw, case, folder, label):
    native.diagnostic_configure_line_endpoints(canvas, True, capture=True)
    native.execute(canvas, [draw], [])
    native.present(canvas)
    captures = native.diagnostic_line_endpoints(canvas)
    _records(folder, label, captures)
    assert len(captures) == 1
    decoded = f.decode(captures[0], case)
    for key, value in decoded.items(): _save(folder, label + "-decoded-" + key, value)
    assert native.diagnostic_line_endpoints(canvas) == []
    native.diagnostic_configure_line_endpoints(canvas, True, capture=False)
    return captures[0]


@pytest.mark.gpu
def test_native_capture_off_resident_dispatch_and_paired_render_reuse_no_hidden_costs():
    native, canvas, case, commands, draw, delete, folder = _setup("capture-off-resident", capture=False)
    try:
        _warm_frames(native, canvas, draw, folder, 2, 1)
        before = native.probe()
        receipts = _warm_frames(native, canvas, draw, folder, 12, 3)
        after = native.probe()
        _save(folder, "resident", {"before": before, "after": after, "receipts": receipts,
                                  "scope": "capture-off pool residency; uniform writes included, quality maps excluded"})
        _resident(before, after, 12, 6)
        assert native.diagnostic_line_endpoints(canvas) == []
        _quality(native, canvas, draw, case, folder, "quality-after-resident")
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        _close(native, canvas, delete, folder)


@pytest.mark.gpu
def test_native_query_on_maps_actual_endpoint_compute_scene_and_capture_pass_pairs():
    native, canvas, case, commands, draw, delete, folder = _setup("query-on-compute", capture=False)
    try:
        configured = native.benchmark_configure_gpu_timing(canvas, True)
        _save(folder, "query-configured", configured)
        assert configured["enabled"] is True and configured["supported"] is True, "unavailable actual timestamp feature remains an unresolved gate"
        before = native.probe()
        native.benchmark_begin_frame(canvas, 1)
        native.execute(canvas, [draw], [])
        native.present(canvas)
        after, receipts, timings = _drain(native, canvas, receipts=1, maps=1, folder=folder)
        _receipt(receipts[0], 1, before["device_generation"])
        _timing(timings[0], receipts[0], before["device_generation"])
        for key in QUERY_COUNTERS:
            assert _delta(after, before, key) == 1, key
        assert _delta(after, before, "compute_passes") == _delta(after, before, "line_endpoint_dispatches") == 1
        assert _delta(after, before, "line_endpoint_rows") == 6
        assert _delta(after, before, "draw_calls") == _delta(after, before, "retired_tickets") == 1
        assert _delta(after, before, "completion_waits") == _delta(after, before, "finish_calls") == 0
        assert native.diagnostic_line_endpoints(canvas) == []
        native.benchmark_configure_gpu_timing(canvas, False)
        _quality(native, canvas, draw, case, folder, "quality-after-timing")
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        _close(native, canvas, delete, folder)


@pytest.mark.gpu
def test_native_pending_matrix_uniform_DATA_revisions_preserve_A_B_A_original_outputs():
    native, canvas, case, commands, draw, delete, folder = _setup("pending-matrix-revisions")
    original, revised = matrix_revision()
    vertex_buffer = next(command[1] for command in commands if command[0] == "CREATE" and command[2] == "VertexBuffer")
    old_hashes = {key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in original["arrays"].items()}
    variants = [original, revised, original]
    _save(folder, "revision-plan", {"B": revision_commands(revised, draw[1], vertex_buffer),
                                   "restore-A": revision_commands(original, draw[1], vertex_buffer)})
    for sequence, variant in enumerate(variants):
        for key, value in variant["expected"].items(): _save(folder, f"expected-{sequence}-" + key, value)
    try:
        before = native.probe()
        native.execute(canvas, [draw], [])
        native.execute(canvas, revision_commands(revised, draw[1], vertex_buffer) + [draw], [])
        native.execute(canvas, revision_commands(original, draw[1], vertex_buffer) + [draw], [])
        pending = native.probe()
        _save(folder, "pending", {"before": before, "pending": pending})
        assert pending["pending_draws"] - before["pending_draws"] == 3
        for key in ("draw_calls", "line_endpoint_dispatches", "line_endpoint_rows", "dawn_queue_submits", "completion_waits", "finish_calls"):
            assert pending[key] == before[key], "no intermediate submit/read: " + key
        native.present(canvas)
        after, _, _ = _drain(native, canvas, folder=folder)
        captures = native.diagnostic_line_endpoints(canvas)
        _records(folder, "pending-revisions", captures)
        assert len(captures) == 3 and len({value["ticket_id"] for value in captures}) == 1
        assert [value["capture_id"] for value in captures] == sorted({value["capture_id"] for value in captures})
        for sequence, (record, variant) in enumerate(zip(captures, variants)):
            assert record["device_generation"] == before["device_generation"]
            decoded = f.decode(record, variant)
            for key, value in decoded.items(): _save(folder, f"actual-{sequence}-" + key, value)
        assert _delta(after, before, "line_endpoint_dispatches") == _delta(after, before, "draw_calls") == 3
        assert _delta(after, before, "line_endpoint_rows") == 18
        assert _delta(after, before, "dawn_queue_submits") == _delta(after, before, "retired_tickets") == 1
        assert old_hashes == {key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in original["arrays"].items()}
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        _close(native, canvas, delete, folder)


@pytest.mark.gpu
def test_native_warmed_uniform_only_change_has_isolated_positive_upload_and_exact_outputs():
    native, canvas, original, commands, draw, delete, folder = _setup("isolated-changed-UBO", capture=False)
    _, uniform = uniform_only_revision()
    updates = uniform_only_commands(uniform, draw[1])
    _save(folder, "uniform-only-commands", updates)
    for key, value in uniform["expected"].items(): _save(folder, "expected-uniform-only-" + key, value)
    try:
        _warm_frames(native, canvas, draw, folder, 2, 1)
        before = native.probe()
        assert before["pending_tickets"] == before["pending_draws"] == before["queued_frames"] == 0
        native.benchmark_begin_frame(canvas, 3)
        native.execute(canvas, updates + [draw], [])
        pending = native.probe()
        _save(folder, "uniform-only-pending", {"before": before, "pending": pending})
        assert pending["pending_draws"] - before["pending_draws"] == 1
        assert _delta(pending, before, "uniform_upload_bytes") == 0
        assert _delta(pending, before, "dawn_queue_submits") == 0
        native.present(canvas)
        after, receipts, timings = _drain(native, canvas, receipts=1, folder=folder, label="uniform-only-retirement")
        _receipt(receipts[0], 3, before["device_generation"])
        assert timings == []
        _save(folder, "isolated-changed-UBO-probes", {"before": before, "after": after,
              "scope": "previous A fully resident and retired; only five UBO values change; no DATA or input revision; quality read excluded"})
        _resident(before, after, 1, 6)
        _changed_ubo_upload(before, after)
        resident_before = native.probe()
        _warm_frames(native, canvas, draw, folder, 2, 4)
        resident_after = native.probe()
        _resident(resident_before, resident_after, 2, 6)
        _quality(native, canvas, draw, uniform, folder, "uniform-only-quality-after-measurement")
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        _close(native, canvas, delete, folder)


def _submitted_owner(native, canvas, draw, folder, label):
    """Observe real unfinished work; finite observations do not fabricate delay."""
    ledger = []
    for sequence in range(OBSERVATION_ATTEMPTS):
        frame_id = sequence + 1
        native.benchmark_begin_frame(canvas, frame_id)
        token = native.begin_canvas_paint(canvas)
        before = native.probe()
        native.execute(canvas, [draw], [])
        native.present(canvas)
        submitted = native.probe()  # This API polls; a fast Ticket may retire here.
        ledger.append({"frame_id": frame_id, "token": token, "before": before, "submitted": submitted})
        _save(folder, label, ledger)
        if _delta(submitted, before, "dawn_queue_submits") == 1 and submitted["pending_tickets"] > 0:
            return frame_id, token, before, submitted
        native.end_canvas_paint(canvas, token)
        _, receipts, _ = _drain(native, canvas, receipts=1, folder=folder, label=f"unobserved-{sequence}")
        _receipt(receipts[0], frame_id, before["device_generation"], token=token)
        records = native.diagnostic_line_endpoints(canvas)
        _records(folder, f"unobserved-{sequence}", records)
        assert len(records) == 1
        f.decode(records[0], f.load_case("matrices_arrays"))
    raise AssertionError("no actual unfinished submitted Ticket observed; cancellation hardware gate unresolved")


@pytest.mark.gpu
def test_native_cancelled_submitted_endpoint_stays_failed_until_real_Ticket_retirement():
    native, canvas, case, commands, draw, delete, folder = _setup("submitted-cancellation")
    try:
        frame_id, token, before, submitted = _submitted_owner(native, canvas, draw, folder, "submission-witnesses")
        reason = "independent cancellation after witnessed actual Queue.Submit"
        native.abort_canvas_paint(canvas, token, reason)
        after_abort = native.probe()
        _save(folder, "after-abort", after_abort)
        after, receipts, _ = _drain(native, canvas, receipts=1, folder=folder)
        _receipt(receipts[0], frame_id, before["device_generation"], status="failed", token=token)
        captures = native.diagnostic_line_endpoints(canvas)
        _records(folder, "cancelled", captures)
        assert len(captures) == 1
        f.rejected(captures[0])
        assert captures[0]["status"] == "failed" and captures[0]["error"] == reason
        assert captures[0]["ticket_id"] > 0 and captures[0]["device_generation"] == before["device_generation"]
        assert _delta(after, before, "retired_tickets") == 1
        assert _delta(after, before, "line_endpoint_dispatches") == _delta(after, before, "draw_calls") == 1
        assert after["line_resource_pool_busy_slots"] == 0
        _save(folder, "scope", {"submitted_witness": True, "post_abort_ticket_still_live_observed": after_abort["pending_tickets"] > 0,
                               "resource_release_at_actual_processing": "live gauge sampled only; probe polls, no pre-processing diagnostic collector observation exists",
                               "lost_or_cancelled_work_has_no_successful_logical_outputs": True})
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        _close(native, canvas, delete, folder)


@pytest.mark.gpu
def test_native_cancelled_queued_endpoint_has_real_backpressure_and_no_second_dispatch():
    native, canvas, case, commands, draw, delete, folder = _setup("queued-cancellation")
    old_slots = native.probe()["frame_slots"]
    ledger, witnessed = [], False
    try:
        native.configure_frame_slots(1)
        for sequence in range(OBSERVATION_ATTEMPTS):
            frame_id = sequence + 1
            before = native.probe()
            native.benchmark_begin_frame(canvas, frame_id)
            token = native.begin_canvas_paint(canvas)
            native.execute(canvas, [draw], [])
            native.present(canvas)
            native.execute(canvas, [draw], [])
            native.present(canvas)
            queued = native.probe()
            real_queue = queued["queued_frames"] == 1 and _delta(queued, before, "deferred_frames") > 0
            ledger.append({"frame_id": frame_id, "token": token, "before": before, "observed": queued, "real_queue": real_queue})
            _save(folder, "queue-witnesses", ledger)
            if real_queue:
                assert _delta(queued, before, "dawn_queue_submits") == _delta(queued, before, "draw_calls") == _delta(queued, before, "line_endpoint_dispatches") == 1
                reason = "independent actual queued endpoint owner cancellation"
                native.abort_canvas_paint(canvas, token, reason)
                after, receipts, _ = _drain(native, canvas, receipts=1, folder=folder)
                _receipt(receipts[0], frame_id, before["device_generation"], status="failed", token=token)
                captures = native.diagnostic_line_endpoints(canvas)
                _records(folder, "queued-cancelled", captures)
                assert len(captures) == 2
                assert sorted(row["ticket_id"] == 0 for row in captures) == [False, True]
                for row in captures:
                    f.rejected(row)
                    assert row["status"] == "failed" and row["error"] == reason
                assert _delta(after, before, "dawn_queue_submits") == _delta(after, before, "retired_tickets") == 1
                assert _delta(after, before, "line_endpoint_dispatches") == 1 and _delta(after, before, "line_endpoint_rows") == 6
                witnessed = True
                break
            native.end_canvas_paint(canvas, token)
            _, receipts, _ = _drain(native, canvas, receipts=1, folder=folder, label=f"not-queued-{sequence}")
            _receipt(receipts[0], frame_id, before["device_generation"], token=token, submissions=2)
            captures = native.diagnostic_line_endpoints(canvas)
            _records(folder, f"not-queued-{sequence}", captures)
            assert len(captures) == 2
            for row in captures: f.decode(row, case)
        assert witnessed, "no real queued batch/deferred witness; queued cancellation gate unresolved"
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        # Slot policy and object deletion remain attempted if the drain fails.
        try:
            _drain(native, canvas, folder=folder, label="slot-restore-drain")
        finally:
            try: native.configure_frame_slots(old_slots)
            finally: _close(native, canvas, delete, folder)


@pytest.mark.gpu
def test_native_actual_device_loss_rejects_submitted_capture_and_recovers_CPU_inputs_once():
    native, canvas, case, commands, draw, delete, folder = _setup("device-loss-recovery")
    try:
        # Measure the packed input byte count without guessing native layout.
        native.diagnostic_configure_line_endpoints(canvas, True, capture=False)
        cold = native.probe()
        _warm_frames(native, canvas, draw, folder, 1, 1)
        warmed = native.probe()
        packed_bytes = _delta(warmed, cold, "line_endpoint_upload_bytes")
        assert packed_bytes > 0 and _delta(warmed, cold, "line_endpoint_conversion_builds") == 1
        native.diagnostic_configure_line_endpoints(canvas, True, capture=True)
        # Distinct larger IDs avoid the helper's monotonic reservation sequence.
        native.benchmark_begin_frame(canvas, 100)
        token = native.begin_canvas_paint(canvas)
        before_loss = native.probe()
        native.execute(canvas, [draw], [])
        native.present(canvas)
        submitted = native.probe()
        _save(folder, "loss-submitted-witness", {"before": before_loss, "submitted": submitted, "token": token})
        assert _delta(submitted, before_loss, "dawn_queue_submits") == 1 and submitted["pending_tickets"] > 0, "actual unfinished submitted loss witness required"
        native.lose_device()
        lost, receipts, _ = _drain(native, canvas, receipts=1, folder=folder, label="loss-retirement")
        assert receipts[0]["frame_id"] == 100 and receipts[0]["paint_token"] == token
        assert receipts[0]["status"] == "device_lost" and receipts[0]["error"]
        assert receipts[0]["ownership_closed"] is True and receipts[0]["ownership_retired"] is True
        captures = native.diagnostic_line_endpoints(canvas)
        _records(folder, "lost-capture", captures)
        assert len(captures) == 1
        f.rejected(captures[0])
        assert captures[0]["status"] == "device_lost" and captures[0]["ticket_id"] > 0
        assert captures[0]["device_generation"] == before_loss["device_generation"]
        # Loss cancels logically; no claim of physical completion of old work.
        native.diagnostic_configure_line_endpoints(canvas, True, capture=False)
        before_recovery = native.probe()
        _warm_frames(native, canvas, draw, folder, 1, 101)
        recovered = native.probe()
        _save(folder, "recovery", {"before": before_recovery, "after": recovered, "cold_packed_bytes": packed_bytes})
        assert recovered["device_generation"] > before_loss["device_generation"]
        assert _delta(recovered, before_recovery, "line_endpoint_conversion_builds") == 0
        assert _delta(recovered, before_recovery, "line_endpoint_conversion_bytes") == 0
        assert _delta(recovered, before_recovery, "line_endpoint_upload_bytes") == packed_bytes
        assert _delta(recovered, before_recovery, "portable_shader_misses") == 0
        before_resident = native.probe()
        _warm_frames(native, canvas, draw, folder, 2, 102)
        after_resident = native.probe()
        _resident(before_resident, after_resident, 2, 6)
        _quality(native, canvas, draw, case, folder, "surviving-program-quality")
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        _close(native, canvas, delete, folder)
