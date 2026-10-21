"""Independent pre-Ticket failure/terminal-record controls.

These controls use an invalid negative DRAW range and no submitted work.
They do not qualify pipeline-failure rollback, output parity or GPU maps.
The original basic11/lifetime7 sources and expected arrays stay unchanged.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import time
import traceback

import pytest

from tools import fixture_line_endpoints_dawn as f

NO_PRESENT = (1 << 64) - 1
ZERO_WORK = ("pending_tickets", "pending_draws", "queued_frames",
             "pending_timestamp_frames", "line_resource_pool_busy_slots")
ZERO_EXECUTION = ("dawn_queue_submits", "draw_calls", "compute_passes",
                  "line_endpoint_dispatches", "line_endpoint_rows",
                  "timestamp_query_sets", "timestamp_resolves", "timestamp_readbacks")
CONTROLS = {
    "cancel-unpainted": ("cancelled", "cancelled", "native_present"),
    "abort-paint": ("failed", "submission_error", "qt_paint"),
    "destroy-owner": ("cancelled", "cancelled", "native_present"),
}


def failed_unsubmitted(receipt, timing, frame_id, generation, token, control):
    """An unsuccessful zero-submit owner must never claim measured work."""
    receipt_status, timing_status, scope = CONTROLS[control]
    for row in (receipt, timing):
        assert type(row["frame_id"]) is int and row["frame_id"] == frame_id
        assert type(row["paint_token"]) is int and row["paint_token"] == token
        assert row["frame_scope"] == scope
        assert type(row["submission_count"]) is int and row["submission_count"] == 0
        assert type(row["last_present_submission_index"]) is int
        assert row["last_present_submission_index"] == NO_PRESENT
        assert isinstance(row["error"], str) and row["error"]
    assert receipt["status"] == receipt_status
    assert receipt["ownership_closed"] is True and receipt["ownership_retired"] is True
    assert receipt["presented"] is False and receipt["present_count"] == 0
    assert receipt["counters_captured"] is False
    assert receipt["counter_capture"] == "unavailable_unsubmitted"
    assert timing["status"] == timing_status and timing["device_generation"] == generation
    assert timing["passes"] == [] and timing["render_span_ns"] == timing["pass_sum_ns"] == 0


def no_work(before, after):
    assert all(type(after[key]) is int and after[key] == 0 for key in ZERO_WORK)
    for key in ZERO_EXECUTION:
        assert type(before[key]) is type(after[key]) is int
        assert after[key] == before[key], key


def _save(folder, label, value):
    (folder / (label + ".json")).write_bytes(
        (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _collect(native, canvas, folder):
    """Consume actual retained records, including after canvas destruction."""
    receipts, timings, probes = [], [], []
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        native.process_events()
        receipts.extend(native.benchmark_completions(canvas))
        timings.extend(native.benchmark_gpu_timings(canvas))
        probes.append(native.probe())
        _save(folder, "collection", {"receipts": receipts, "timings": timings, "probes": probes})
        assert len(receipts) <= 1 and len(timings) <= 1, "duplicate terminal ownership records"
        if len(receipts) == len(timings) == 1 and all(probes[-1][key] == 0 for key in ZERO_WORK):
            return receipts[0], timings[0], probes[-1]
        time.sleep(.001)
    raise AssertionError("failed owner or terminal timing record did not drain")


def _native():
    context = f.activation_before_native(os.environ)
    from vispy import _dawn
    origin = Path(_dawn.__file__).resolve()
    assert origin.parent == f.ROOT / "src/vispy"
    assert f.sha(origin) == context["activation"]["activated"][origin.name]
    return _dawn, context


@pytest.mark.gpu
@pytest.mark.parametrize("control", tuple(CONTROLS))
def test_native_rejected_unsubmitted_draw_terminal_records_drain_and_slots_recover(control):
    native, context = _native()
    case = f.load_case("matrices_arrays")
    root = Path(os.environ["VISPY_LINE_ENDPOINTS_EVIDENCE"]).resolve()
    assert root.is_relative_to(f.ROOT / "build/evidence")
    folder = root / ("pre-ticket-" + control)
    folder.mkdir(parents=True, exist_ok=False)
    _save(folder, "context", context)
    canvas = native.register_canvas(8, 8, 1, False)
    commands, draw, delete = f.commands(case, 710000)
    old_slots = native.probe()["frame_slots"]
    live = True
    try:
        device = native.device_info()
        _save(folder, "device", device)
        assert device["ok"] is True and device["software"] is False
        native.execute(canvas, commands, [])
        configured = native.benchmark_configure_gpu_timing(canvas, True)
        assert configured["enabled"] is True and configured["supported"] is True
        frame_id = 101
        before = native.probe()
        assert all(before[key] == 0 for key in ZERO_WORK)
        native.benchmark_begin_frame(canvas, frame_id)
        token = native.begin_canvas_paint(canvas) if control == "abort-paint" else 0
        # Negative first is a public DRAW range error, before evaluator/resource
        # preparation. No candidate pixels or shader-output expectation is used.
        rejected_draw = (draw[0], draw[1], draw[2], [-1, 2], draw[4])
        with pytest.raises(RuntimeError, match="DRAW first exceeds native nonnegative count range") as error:
            native.execute(canvas, [rejected_draw], [])
        _save(folder, "rejected-range", {"error": str(error.value)})
        after_rejection = native.probe()
        for key in ZERO_EXECUTION:
            assert after_rejection[key] == before[key], key
        assert after_rejection["pending_tickets"] == after_rejection["pending_draws"] == 0
        reason = "independent rejected unsubmitted DRAW control"
        if control == "cancel-unpainted":
            native.benchmark_cancel_frame(canvas, frame_id, reason)
        elif control == "abort-paint":
            native.abort_canvas_paint(canvas, token, reason)
        else:
            native.execute(canvas, delete, [])
            native.destroy_canvas(canvas)
            live = False
        # A failed timing record intentionally survives teardown. Slot changes
        # must refuse until actual terminal records have been consumed.
        with pytest.raises(RuntimeError, match="submissions and query callbacks are idle"):
            native.configure_frame_slots(1 if old_slots != 1 else 2)
        receipt, timing, after = _collect(native, canvas, folder)
        failed_unsubmitted(receipt, timing, frame_id, before["device_generation"], token, control)
        no_work(before, after)
        assert native.benchmark_completions(canvas) == []
        assert native.benchmark_gpu_timings(canvas) == []
        new_slots = 1 if old_slots != 1 else 2
        native.configure_frame_slots(new_slots)
        assert native.probe()["frame_slots"] == new_slots
        native.configure_frame_slots(old_slots)
        _save(folder, "accepted", {"receipt": receipt, "timing": timing,
                                 "before": before, "after": after,
                                 "restored_slots": native.probe()["frame_slots"],
                                 "scope": "zero-submit rejected range/owner/terminal record recovery only"})
    except BaseException:
        (folder / "failure.txt").write_bytes(traceback.format_exc().encode("utf-8"))
        raise
    finally:
        cleanup_errors = []
        if live:
            try:
                try:
                    native.execute(canvas, delete, [])
                finally:
                    native.destroy_canvas(canvas)
            except BaseException:
                cleanup_errors.append(traceback.format_exc())
        # Preserve uncollected unexpected records in cleanup artifacts. Failure
        # does not authorize a successful owner or silent disposal assertion.
        try:
            native.process_events()
            _save(folder, "cleanup", {"receipts": native.benchmark_completions(canvas),
                                     "timings": native.benchmark_gpu_timings(canvas),
                                     "probe": native.probe()})
        except BaseException:
            cleanup_errors.append(traceback.format_exc())
        try:
            native.configure_frame_slots(old_slots)
        except BaseException:
            cleanup_errors.append(traceback.format_exc())
        if cleanup_errors:
            _save(folder, "cleanup-errors", cleanup_errors)
            raise AssertionError("native cleanup failed; all cleanup stages attempted")


def _rejected_record(control):
    receipt_status, timing_status, scope = CONTROLS[control]
    common = {"frame_id": 101, "paint_token": 7 if control == "abort-paint" else 0,
              "frame_scope": scope, "submission_count": 0,
              "last_present_submission_index": NO_PRESENT, "error": "failed owner"}
    receipt = {**common, "status": receipt_status, "ownership_closed": True,
               "ownership_retired": True, "presented": False, "present_count": 0,
               "counters_captured": False, "counter_capture": "unavailable_unsubmitted"}
    timing = {**common, "status": timing_status, "device_generation": 4,
              "passes": [], "render_span_ns": 0, "pass_sum_ns": 0}
    return receipt, timing


@pytest.mark.parametrize("control", tuple(CONTROLS))
def test_cpu_failure_predicate_accepts_only_unsubmitted_failed_owner(control):
    receipt, timing = _rejected_record(control)
    failed_unsubmitted(receipt, timing, 101, 4, receipt["paint_token"], control)


@pytest.mark.parametrize("target,key,value", [
    ("receipt", "status", "success"), ("receipt", "ownership_closed", False),
    ("receipt", "ownership_retired", False), ("receipt", "submission_count", 1),
    ("receipt", "counters_captured", True), ("receipt", "presented", True),
    ("receipt", "counter_capture", "submission"), ("receipt", "frame_id", True),
    ("timing", "status", "success"), ("timing", "error", ""),
    ("timing", "passes", [{"kind": "line_endpoints"}]),
    ("timing", "device_generation", 5), ("timing", "render_span_ns", 1),
])
def test_cpu_failure_predicate_rejects_false_work_or_ownership(target, key, value):
    receipt, timing = copy.deepcopy(_rejected_record("cancel-unpainted"))
    (receipt if target == "receipt" else timing)[key] = value
    with pytest.raises(AssertionError):
        failed_unsubmitted(receipt, timing, 101, 4, 0, "cancel-unpainted")


@pytest.mark.parametrize("counter", ZERO_EXECUTION + ZERO_WORK)
def test_cpu_failure_counter_guard_rejects_executed_or_live_work(counter):
    before = {key: 0 for key in ZERO_WORK + ZERO_EXECUTION}
    after = dict(before)
    after[counter] = 1
    with pytest.raises(AssertionError):
        no_work(before, after)
