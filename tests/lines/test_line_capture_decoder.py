"""Pure transport controls for actual allocation endpoint capture metadata.

These tests import no renderer and make no GPU qualification claim. Synthetic
typed rows exercise the independent decoder, including its unchanged legacy
format and the fresh-before-carry allocation phase.
"""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from tools import fixture_line_endpoints_dawn as f


def _control(count=65, instances=2, primitive="line_strip"):
    selected = count // 2 * 2 if primitive == "lines" else count
    rows, width = selected * instances, 32
    position = np.arange(rows * 4, dtype=np.float32).reshape(rows, 4)
    position[0, 0] = np.float32(-0.0)
    identity = np.empty((rows, 2), dtype=np.uint32)
    identity[:, 0] = np.arange(rows, dtype=np.uint32) + np.uint32(16777217)
    identity[:, 1] = np.uint32(0xFFFFFFFF)
    data = np.full((rows, width), 0xA7, dtype=np.uint8)
    data[:, :16] = position.view(np.uint8).reshape(rows, 16)
    data[:, 16:24] = identity.view(np.uint8).reshape(rows, 8)
    declared = [
        {"name": "gl_Position", "glsl_type": "vec4", "qualifier": "", "array_length": 1, "shape": [4]},
        {"name": "v_identity", "glsl_type": "uvec2", "qualifier": "flat", "array_length": 1, "shape": [2]},
    ]
    fields = [
        {"name": "gl_Position", "type": "vec4", "interpolation": "", "offset": 0, "size": 16,
         "array_stride": 0, "matrix_stride": 0, "array_size": 0},
        {"name": "v_identity", "type": "uvec2", "interpolation": "flat", "offset": 16, "size": 8,
         "array_stride": 0, "matrix_stride": 0, "array_size": 0},
    ]
    case = {"contract": {"selection": {"count": count, "instances": instances, "original_primitive": primitive},
                         "GL_TF_transport_only": {"fields": declared}},
            "expected": {"gl_Position": position, "v_identity": identity}}
    raw = np.full(((rows + 63) // 64) * 64 * width + 16, f.CANARY, dtype=np.uint8)
    raw[:data.size] = data.reshape(-1)
    record = {"status": "completed", "error": "", "capture_id": 1, "ticket_id": 2,
              "device_generation": 3, "evaluator_key": "decoder-control-no-renderer",
              "rows": rows, "row_bytes": width, "fields": fields, "data": data, "raw_data": raw}
    return case, record


def _chunked(record, counts):
    record = deepcopy(record)
    first, offset, chunks, raw_parts = 0, 0, [], []
    width = record["row_bytes"]
    for count, output in counts:
        extent = max(((count + 63) // 64) * 64 * width + 16, output * width) if count else 0
        raw = np.full(extent, f.CANARY, dtype=np.uint8)
        if count:
            raw[:count * width] = record["data"][first:first + count].reshape(-1)
        chunks.append({"first_row": first, "rows": count, "output_rows": output,
                       "raw_offset": offset, "raw_bytes": extent})
        raw_parts.append(raw)
        first += count
        offset += extent
    assert first == record["rows"]
    record["raw_data"] = np.concatenate(raw_parts)
    record["chunks"] = chunks
    record["capture_phase"] = "evaluated_before_carry"
    return record


def test_legacy_schema_and_exact_typed_rows_are_unchanged():
    case, record = _control()
    assert "chunks" not in record and "capture_phase" not in record
    decoded = f.decode(record, case)
    assert np.signbit(decoded["gl_Position"][0, 0])
    assert decoded["v_identity"][0].tolist() == [16777217, 4294967295]
    assert set(record) == {"status", "error", "capture_id", "ticket_id", "device_generation", "evaluator_key",
                           "rows", "row_bytes", "fields", "data", "raw_data"}


@pytest.mark.parametrize("primitive,count,instances,parts", [
    ("line_strip", 65, 2, [(64, 64), (1, 2), (64, 64), (1, 2)]),
    ("line_loop", 65, 2, [(64, 66), (1, 3), (0, 2), (64, 64), (1, 2), (0, 2)]),
    ("lines", 67, 2, [(64, 64), (2, 2), (64, 64), (2, 2)]),
])
def test_chunks_preserve_fresh_typed_rows_instance_order_and_closing_only_parts(primitive, count, instances, parts):
    case, legacy = _control(count, instances, primitive)
    record = _chunked(legacy, parts)
    decoded = f.decode(record, case)
    for name, wanted in case["expected"].items():
        f.exact(wanted, decoded[name])
        assert decoded[name].flags.owndata and not np.shares_memory(decoded[name], record["data"])
    assert not np.shares_memory(record["data"], record["raw_data"])
    if primitive == "line_loop":
        first = record["chunks"][0]
        assert first["raw_bytes"] == 66 * record["row_bytes"]
        assert np.all(record["raw_data"][64 * record["row_bytes"]:first["raw_bytes"]] == f.CANARY)
        assert sum(chunk["rows"] == 0 for chunk in record["chunks"]) == 2


@pytest.mark.parametrize("fault", [
    "empty", "tuple", "missing_descriptor_field", "extra_descriptor_field", "missing_phase", "wrong_phase",
    "logical_gap", "logical_overlap", "logical_reorder", "raw_gap", "raw_overlap", "raw_reorder",
    "missing_chunk", "extra_raw", "truncated_raw", "wrong_extent", "undersized_output", "excess_carries",
    "first_u32_overflow", "rows_u32_overflow", "output_u32_overflow", "offset_u64_overflow", "bytes_u64_overflow",
    "negative", "bool", "float", "evaluated_bits", "fresh_guard", "trailing_guard", "alias",
    "closing_raw", "closing_output", "closing_destination", "partial_failure", "failure_message",
])
def test_malformed_chunk_capture_cannot_decode_success(fault):
    case, record = _control(65, 1, "line_loop")
    record = _chunked(record, [(64, 66), (1, 3), (0, 2)])
    parts, width = record["chunks"], record["row_bytes"]
    if fault == "empty": record["chunks"] = []
    elif fault == "tuple": record["chunks"] = tuple(parts)
    elif fault == "missing_descriptor_field": del parts[0]["output_rows"]
    elif fault == "extra_descriptor_field": parts[0]["padded_rows"] = 64
    elif fault == "missing_phase": del record["capture_phase"]
    elif fault == "wrong_phase": record["capture_phase"] = "after_carry"
    elif fault == "logical_gap": parts[1]["first_row"] += 1
    elif fault == "logical_overlap": parts[1]["first_row"] -= 1
    elif fault == "logical_reorder": parts[0], parts[1] = parts[1], parts[0]
    elif fault == "raw_gap": parts[1]["raw_offset"] += 1
    elif fault == "raw_overlap": parts[1]["raw_offset"] -= 1
    elif fault == "raw_reorder": parts[0]["raw_offset"], parts[1]["raw_offset"] = parts[1]["raw_offset"], parts[0]["raw_offset"]
    elif fault == "missing_chunk": del parts[1]
    elif fault == "extra_raw": record["raw_data"] = np.append(record["raw_data"], np.uint8(f.CANARY))
    elif fault == "truncated_raw": record["raw_data"] = record["raw_data"][:-1]
    elif fault == "wrong_extent": parts[0]["raw_bytes"] -= 16
    elif fault == "undersized_output": parts[0]["output_rows"] = 63
    elif fault == "excess_carries": parts[0]["output_rows"] = 67
    elif fault == "first_u32_overflow": parts[0]["first_row"] = 1 << 32
    elif fault == "rows_u32_overflow": parts[0]["rows"] = 1 << 32
    elif fault == "output_u32_overflow": parts[0]["output_rows"] = 1 << 32
    elif fault == "offset_u64_overflow": parts[0]["raw_offset"] = 1 << 64
    elif fault == "bytes_u64_overflow": parts[0]["raw_bytes"] = 1 << 64
    elif fault == "negative": parts[0]["rows"] = -1
    elif fault == "bool": parts[0]["first_row"] = False
    elif fault == "float": parts[0]["raw_offset"] = 0.0
    elif fault == "evaluated_bits": record["raw_data"][0] ^= np.uint8(1)
    elif fault == "fresh_guard": record["raw_data"][64 * width] = 0
    elif fault == "trailing_guard": record["raw_data"][-1] = 0
    elif fault == "alias":
        record["data"] = record["raw_data"][:record["data"].size].reshape(record["data"].shape)
    elif fault == "closing_raw": parts[-1]["raw_bytes"] = 16
    elif fault == "closing_output": parts[-1]["output_rows"] = 1
    elif fault == "closing_destination": parts[-1]["first_row"] -= 1
    elif fault == "partial_failure": record["status"] = "map_error"
    elif fault == "failure_message": record["error"] = "one chunk failed mapping"
    with pytest.raises(AssertionError):
        f.decode(record, case)


def test_terminal_partial_capture_preserves_raw_evidence_but_cannot_expose_logical_success():
    case, record = _control(65, 1, "line_loop")
    record = _chunked(record, [(64, 66), (1, 3), (0, 2)])
    raw = record["raw_data"]
    record.update(status="map_error", error="second chunk map failed", data=np.empty(0, dtype=np.uint8))
    f.rejected(record)
    assert record["raw_data"] is raw and record["chunks"][-1]["rows"] == 0
    with pytest.raises(AssertionError):
        f.decode(record, case)
    record["data"] = np.empty((0, record["row_bytes"]), dtype=np.uint8)
    with pytest.raises(AssertionError):
        f.rejected(record)
