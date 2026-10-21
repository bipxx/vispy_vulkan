"""Future matching-native D1 acceptance; CPU tests never import a renderer.

Pure binary format controls test a decoder, not a mocked renderer or GPU
success. Actual hardware cases require a canonical future activation first.
Quality collection may wait; resident intervals must exclude it.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import pytest

from tools import fixture_line_endpoints_dawn as f


def _binary_control(case):
    """Declared decoder-only binary format; intentionally not native layout."""
    fields, cursor = [], 0
    rows = len(next(iter(case["expected"].values())))
    for declared in case["contract"]["GL_TF_transport_only"]["fields"]:
        tail = f.TYPES[declared["glsl_type"]][1]
        components = tail[0] if tail else 1
        matrix_stride = components * 4 + 8 if len(tail) == 2 else 0
        element = matrix_stride * tail[1] if matrix_stride else components * 4
        count = declared["array_length"]
        array_stride = element + 8 if count > 1 else 0
        size = array_stride * count if count > 1 else element
        cursor = ((cursor + 7) // 8) * 8
        fields.append({"name": declared["name"], "type": declared["glsl_type"],
                       "interpolation": "" if declared["name"] == "gl_Position" else declared["qualifier"],
                       "offset": cursor, "size": size, "array_stride": array_stride,
                       "matrix_stride": matrix_stride, "array_size": count if count > 1 else 0})
        cursor += size
    width = ((cursor + 15) // 16) * 16 + 16
    data = np.full((rows, width), 0xA7, np.uint8)
    for field, declared in zip(fields, case["contract"]["GL_TF_transport_only"]["fields"]):
        values = case["expected"][field["name"]]
        count = declared["array_length"]
        for row in range(rows):
            for index in range(count):
                target = values[row, index] if count > 1 else values[row]
                start = field["offset"] + index * field["array_stride"]
                if field["matrix_stride"]:
                    for column in range(target.shape[1]):
                        packed = np.ascontiguousarray(target[:, column]).view(np.uint8)
                        at = start + column * field["matrix_stride"]
                        data[row, at:at + packed.size] = packed
                else:
                    packed = np.asarray(target, dtype=values.dtype).reshape(-1).view(np.uint8)
                    data[row, start:start + packed.size] = packed
    raw = np.full(((rows + 63) // 64) * 64 * width + 16, f.CANARY, np.uint8)
    raw[:data.size] = data.reshape(-1)
    return {"status": "completed", "error": "", "capture_id": 1, "ticket_id": 2,
            "device_generation": 3, "evaluator_key": "decoder-format-control-only",
            "rows": rows, "row_bytes": width, "fields": list(reversed(fields)),
            "data": data, "raw_data": raw}


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_reflected_decoder_reads_admitted_bits_in_an_independent_binary_layout(name):
    case = f.load_case(name)
    record = _binary_control(case)
    result = f.decode(record, case)
    assert set(result) == set(case["expected"])
    assert all(value.flags.owndata for value in result.values())
    assert all(not np.shares_memory(value, record["data"]) for value in result.values())
    if name == "raw_high_ids":
        assert np.signbit(result["gl_Position"][0, 0])
        assert result["v_unsigned"][0].tolist() == [16777217, 4294967295]
    if name == "logical_count65":
        assert record["raw_data"].size == 128 * record["row_bytes"] + 16
        assert result["v_visits"].tolist() == [1] * 65


@pytest.mark.parametrize("fault", ("status", "ticket", "generation", "type", "qualifier", "duplicate",
                                   "overlap", "extent", "array", "matrix", "canary", "missing_padding", "bits", "alias"))
def test_cpu_reflected_decoder_rejects_false_or_malformed_success(fault):
    case = f.load_case("matrices_arrays")
    record = _binary_control(case)
    field = next(v for v in record["fields"] if v["name"] == "v_basis")
    if fault == "status": record["status"] = "cancelled"
    elif fault == "ticket": record["ticket_id"] = 0
    elif fault == "generation": record["device_generation"] = True
    elif fault == "type": field["type"] = "vec4"
    elif fault == "qualifier": field["interpolation"] = "smooth"
    elif fault == "duplicate": record["fields"][0] = record["fields"][1]
    elif fault == "overlap": field["offset"] = 0
    elif fault == "extent": field["size"] = record["row_bytes"]
    elif fault == "array": next(v for v in record["fields"] if v["name"] == "v_array")["array_stride"] = 4
    elif fault == "matrix": field["matrix_stride"] = 4
    elif fault == "canary": record["raw_data"][record["data"].size] = 0
    elif fault == "missing_padding": record["raw_data"] = record["raw_data"][:-1]
    elif fault == "bits":
        record["data"][0, field["offset"]] ^= 1
        record["raw_data"][:record["data"].size] = record["data"].reshape(-1)
    elif fault == "alias": record["data"] = record["raw_data"][:record["data"].size].reshape(record["data"].shape)
    with pytest.raises(AssertionError):
        f.decode(record, case)


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_private_command_transport_retains_original_sources_payloads_and_IDs(name):
    case = f.load_case(name)
    commands, draw, deletes = f.commands(case, 1000)
    assert [c[3] for c in commands if c[0] == "DATA" and isinstance(c[3], str)] == [case["vertex"], case["fragment"]]
    assert draw[2] == "line_strip" and draw[4] == case["contract"]["selection"]["instances"]
    assert len({c[1] for c in commands if c[0] == "CREATE"}) == len(deletes)
    assert {c[1] for c in commands if c[0] == "CREATE"} == {c[1] for c in deletes}
    if name == "raw_high_ids":
        assert draw[3] == [16777217, 4]
        value = next(c[4] for c in commands if c[:3] == ("ATTRIBUTE", 1000, "a_unsigned"))
        assert value == [0, 16777217, 4294967295] and all(type(v) is int for v in value)
    if name.startswith("indexed_"):
        payload = [c[3] for c in commands if c[0] == "DATA" and isinstance(c[3], dict)][-1]
        assert payload["__bytes__"] == case["arrays"]["input-indices"].tobytes()
        assert draw[3][1] == {"indexed_u8": "unsigned_byte", "indexed_u16": "unsigned_short", "indexed_u32": "unsigned_int"}[name]
    if name == "interleaved_divisors":
        assert next(c[5] for c in commands if c[:3] == ("ATTRIBUTE", 1000, "a_one")) == 1
        assert next(c[5] for c in commands if c[:3] == ("ATTRIBUTE", 1000, "a_two")) == 2
    if name == "matrices_arrays":
        for key in ("u_transform", "u_basis"):
            payload = next(c[4] for c in commands if c[:3] == ("UNIFORM", 1000, key))
            assert payload["__bytes__"] == np.ascontiguousarray(case["arrays"]["input-uniform-" + key].T).tobytes()


@pytest.mark.parametrize("fault", ("old_epoch", "bool_epoch", "copied_path", "substituted_hash", "metadata_epoch"))
def test_cpu_canonical_future_context_rejects_old_or_substituted_activation(fault):
    epoch, digest = 31, "a" * 64
    path = f.ROOT / "build/evidence/native-pass-31/activation.json"
    expected, checksum, activation = digest, digest, {"epoch": 31}
    if fault == "old_epoch": epoch = 30
    elif fault == "bool_epoch": epoch = True
    elif fault == "copied_path": path = f.ROOT / "build/elsewhere/native-pass-31/activation.json"
    elif fault == "substituted_hash": checksum = "b" * 64
    elif fault == "metadata_epoch": activation = {"epoch": 30}
    with pytest.raises(AssertionError):
        f.context_header(path, expected, checksum, activation, epoch)


def test_cpu_canonical_header_is_strict_and_import_follows_the_guard():
    f.context_header(f.ROOT / "build/evidence/native-pass-31/activation.json", "a" * 64, "a" * 64, {"epoch": 31}, 31)
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    native = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_native")
    guard = next(i for i, n in enumerate(native.body) if isinstance(n, ast.Assign) and
                 isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "activation_before_native")
    imports = [i for i, n in enumerate(native.body) if isinstance(n, ast.ImportFrom) and n.module == "vispy"]
    assert imports and min(imports) > guard
    assert not any(isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("vispy") for n in tree.body)
    helper = ast.parse(Path(f.__file__).read_text(encoding="utf-8"))
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) and
                   any(name.startswith(("vispy", "OpenGL", "PyQt", "PySide")) for name in
                       ([n.module or ""] if isinstance(n, ast.ImportFrom) else [a.name for a in n.names]))
                   for n in ast.walk(helper))


def _json_value(value):
    if isinstance(value, bytes): return {"hex": value.hex(), "bytes": len(value)}
    if isinstance(value, np.ndarray): return {"dtype": value.dtype.str, "shape": list(value.shape)}
    raise TypeError(type(value).__name__)


def _native():
    context = f.activation_before_native(os.environ)
    from vispy import _dawn
    path = Path(_dawn.__file__).resolve()
    assert path.parent == f.ROOT / "src/vispy"
    assert f.sha(path) == context["activation"]["activated"][path.name]
    assert all(callable(getattr(_dawn, name, None)) for name in (
        "diagnostic_configure_line_endpoints", "diagnostic_line_endpoints", "register_canvas",
        "execute", "present", "process_events", "probe", "shutdown")), "actual API required"
    return _dawn, context


def _folder(name):
    path = Path(os.environ.get("VISPY_LINE_ENDPOINTS_EVIDENCE", "")).resolve()
    assert "VISPY_LINE_ENDPOINTS_EVIDENCE" in os.environ
    assert path.is_relative_to(f.ROOT / "build/evidence")
    folder = path / name
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def _save(folder, label, value):
    if isinstance(value, np.ndarray):
        np.save(folder / (label + ".npy"), value, allow_pickle=False)
    else:
        (folder / (label + ".json")).write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_value) + "\n", encoding="utf-8")


def _save_records(folder, records):
    for index, record in enumerate(records):
        # Raw failure evidence is persisted before admission assertions.
        _save(folder, f"capture-{index}-data", record["data"])
        _save(folder, f"capture-{index}-raw", record["raw_data"])
        _save(folder, f"capture-{index}-metadata", {k: v for k, v in record.items() if k not in {"data", "raw_data"}})


def _setup(native, case, first_id, folder):
    canvas = native.register_canvas(8, 8, 1, False)
    info = native.device_info()
    _save(folder, "device", info)
    assert info["ok"] is True and info["software"] is False
    assert info["max_compute_workgroup_size_x"] >= 64 and info["max_compute_invocations_per_workgroup"] >= 64
    assert info["max_storage_buffers_per_shader_stage"] >= 2
    commands, draw, delete = f.commands(case, first_id)
    _save(folder, "commands", {"setup": commands, "draw": draw, "delete": delete,
                               "transport_scope": "private typed native ABI; no public integer constant admission"})
    try:
        native.execute(canvas, commands, [])
        native.benchmark_configure_gpu_timing(canvas, False)
        native.diagnostic_configure_line_endpoints(canvas, True)
    except BaseException:
        (folder / "setup-failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        try: native.execute(canvas, delete, [])
        finally: native.destroy_canvas(canvas)
        raise
    return canvas, draw, delete


def _retire(native, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        native.process_events()
        p = native.probe()
        if p["pending_tickets"] == p["queued_frames"] == p["pending_draws"] == 0:
            return p
        time.sleep(.001)
    raise AssertionError("actual Ticket retirement did not complete")


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
def test_native_admitted_original_outputs_padding_queryoff_and_owned_storage(name):
    case = f.load_case(name)
    native, context = _native()
    folder = _folder(name)
    _save(folder, "context", {**context, "D1_checked_inputs": case["checked_inputs"]})
    canvas, draw, delete = _setup(native, case, 510000, folder)
    retained = None
    try:
        before = native.probe()
        assert before["pending_tickets"] == before["pending_draws"] == before["queued_frames"] == 0
        native.execute(canvas, [draw], [])
        pending = native.probe()
        _save(folder, "pending", {"before": before, "pending": pending})
        assert pending["pending_draws"] - before["pending_draws"] == 1
        for key in ("dawn_queue_submits", "draw_calls", "line_endpoint_dispatches", "line_endpoint_rows"):
            assert pending[key] == before[key], key
        native.present(canvas)
        submitted = native.probe()
        _save(folder, "submitted", submitted)
        assert submitted["dawn_queue_submits"] - before["dawn_queue_submits"] == 1
        assert submitted["draw_calls"] - before["draw_calls"] == 1
        assert submitted["line_endpoint_dispatches"] - before["line_endpoint_dispatches"] == 1
        rows = case["contract"]["selection"]["count"] * case["contract"]["selection"]["instances"]
        assert submitted["line_endpoint_rows"] - before["line_endpoint_rows"] == rows
        records = native.diagnostic_line_endpoints(canvas)
        _save_records(folder, records)
        after = native.probe()
        _save(folder, "after-quality", after)
        assert len(records) == 1
        retained = records[0]
        assert retained["device_generation"] == before["device_generation"]
        decoded = f.decode(retained, case)
        for key, value in decoded.items(): _save(folder, "decoded-" + key, value)
        assert after["retired_tickets"] - before["retired_tickets"] == 1
        assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
        for key in ("timestamp_query_sets", "timestamp_resolves", "timestamp_readbacks"):
            assert after[key] == before[key], "query-disabled endpoint evaluation"
        assert native.benchmark_gpu_timings(canvas) == []
        assert native.diagnostic_line_endpoints(canvas) == []
        held = {k: hashlib.sha256(retained[k].tobytes()).hexdigest() for k in ("data", "raw_data")}
        native.execute(canvas, delete, [])
        native.destroy_canvas(canvas)
        canvas = None
        assert held == {k: hashlib.sha256(retained[k].tobytes()).hexdigest() for k in held}
        f.decode(retained, case)
        _save(folder, "ownership-after-close", held)
    except BaseException:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        if canvas is not None:
            try: native.execute(canvas, delete, [])
            finally: native.destroy_canvas(canvas)


@pytest.mark.gpu
def test_native_diagnostic_disabled_does_not_create_endpoint_work_or_records():
    case = f.load_case("logical_count65")
    native, context = _native()
    folder = _folder("diagnostic-disabled")
    _save(folder, "context", context)
    canvas, draw, delete = _setup(native, case, 520000, folder)
    try:
        native.diagnostic_configure_line_endpoints(canvas, False)
        before = native.probe()
        native.execute(canvas, [draw], [])
        native.present(canvas)
        records = native.diagnostic_line_endpoints(canvas)
        _save_records(folder, records)
        after = native.probe()
        _save(folder, "probes", {"before": before, "after": after})
        assert records == []
        assert after["draw_calls"] - before["draw_calls"] == 1
        assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == 1
        for key in ("line_endpoint_dispatches", "line_endpoint_rows", "line_endpoint_conversion_builds", "line_endpoint_upload_bytes"):
            assert after[key] == before[key], key
        assert after["pending_tickets"] == 0
    finally:
        try: native.execute(canvas, delete, [])
        finally: native.destroy_canvas(canvas)


@pytest.mark.gpu
def test_native_pending_abort_returns_failure_and_recovers_diagnostic_capacity():
    case = f.load_case("logical_count65")
    native, context = _native()
    folder = _folder("pending-abort-capacity")
    _save(folder, "context", context)
    canvas, draw, delete = _setup(native, case, 530000, folder)
    ledger = []
    previous_capture_id = 0
    try:
        before = native.probe()
        # Exceeds the actual128-record bound without retaining cancelled work.
        for sequence in range(130):
            native.benchmark_begin_frame(canvas, sequence + 1)
            token = native.begin_canvas_paint(canvas)
            native.execute(canvas, [draw], [])
            pending = native.probe()
            assert pending["pending_draws"] == 1
            reason = "x" * 8192 if sequence == 0 else f"independent pending endpoint abort {sequence}"
            native.abort_canvas_paint(canvas, token, reason)
            records = native.diagnostic_line_endpoints(canvas)
            captures = folder / f"abort-{sequence:03}"
            captures.mkdir()
            _save_records(captures, records)
            assert len(records) == 1
            f.rejected(records[0])
            assert records[0]["status"] == "failed"
            assert records[0]["capture_id"] > previous_capture_id
            previous_capture_id = records[0]["capture_id"]
            assert records[0]["device_generation"] == before["device_generation"]
            assert records[0]["error"] == reason[:4096], "bounded diagnostic error contract"
            assert records[0]["ticket_id"] == 0 and records[0]["raw_data"].size == 0
            completions = native.benchmark_completions(canvas)
            assert len(completions) == 1 and completions[0]["status"] == "failed"
            assert completions[0]["frame_id"] == sequence + 1 and completions[0]["paint_token"] == token
            assert completions[0]["frame_scope"] == "qt_paint" and completions[0]["ownership_closed"] is True
            assert completions[0]["submission_count"] == completions[0]["present_count"] == 0
            assert completions[0]["presented"] is False and completions[0]["ownership_retired"] is True
            after = native.probe()
            ledger.append({"sequence": sequence, "token": token, "pending": pending,
                           "after": after, "completions": completions,
                           "capture": {k: v for k, v in records[0].items() if k not in {"data", "raw_data"}}})
            _save(folder, "abort-ledger", ledger)
            assert after["pending_draws"] == after["queued_frames"] == after["pending_tickets"] == 0
            for key in ("line_endpoint_dispatches", "dawn_queue_submits", "retired_tickets"):
                assert after[key] == before[key], "unsubmitted abort cannot become GPU success"
    finally:
        try: native.execute(canvas, delete, [])
        finally: native.destroy_canvas(canvas)


@pytest.mark.gpu
def test_native_retired_uncollected_shutdown_never_maps_stale_device_storage():
    case = f.load_case("logical_count65")
    native, context = _native()
    folder = _folder("retired-uncollected-shutdown")
    _save(folder, "context", context)
    canvas, draw, delete = _setup(native, case, 540000, folder)
    shut = False
    try:
        before = native.probe()
        native.execute(canvas, [draw], [])
        native.present(canvas)
        retired = _retire(native)
        _save(folder, "retired-before-shutdown", {"before": before, "retired": retired})
        assert retired["retired_tickets"] - before["retired_tickets"] == 1
        assert retired["line_endpoint_dispatches"] - before["line_endpoint_dispatches"] == 1
        # Deliberately leave the actual retired readback uncollected.
        native.shutdown()
        shut = True
        records = native.diagnostic_line_endpoints(canvas)
        _save_records(folder, records)
        assert len(records) == 1
        f.rejected(records[0])
        assert records[0]["status"] == "cancelled"
        assert records[0]["ticket_id"] > 0
        assert records[0]["device_generation"] == before["device_generation"]
        assert native.diagnostic_line_endpoints(canvas) == []
    finally:
        if not shut:
            try: native.execute(canvas, delete, [])
            finally: native.destroy_canvas(canvas)
