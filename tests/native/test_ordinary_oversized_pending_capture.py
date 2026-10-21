"""Independent future30 oversized snapshots, Tickets and bounded working sets."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import pytest

from tools import fixture_ordinary_oversized as retired
from tools import fixture_ordinary_oversized_pending as f

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = ROOT / "build/evidence/ordinary-oversized-pending-authoring-5/authoring.json"
ACTIVATION = ROOT / "build/evidence/native-pass-30/activation.json"
HANDOFF = ROOT / "build/evidence/native-pass-30-build-handoff-1/result.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _check_header(path, expected, actual, activation):
    assert Path(path).resolve() == ACTIVATION, "canonical30 activation required before native import"
    assert len(expected) == 64 and set(expected) <= set("0123456789abcdef"), "explicit activation pin required"
    assert expected == actual, "activation substitution"
    assert type(activation.get("epoch")) is int and activation["epoch"] == 30, "exact epoch30 required"


def _activation_before_native():
    path = Path(os.environ.get("VISPY_OVERSIZED_PENDING_ACTIVATION", "")).resolve()
    expected = os.environ.get("VISPY_OVERSIZED_PENDING_ACTIVATION_SHA256", "")
    assert path == ACTIVATION and len(expected) == 64, "explicit canonical30 context required before native import"
    value = _read(path)
    _check_header(path, expected, _sha(path), value)
    handoff_sha = os.environ.get("VISPY_OVERSIZED_PENDING_HANDOFF_SHA256", "")
    assert len(handoff_sha) == 64 and _sha(HANDOFF) == handoff_sha, "explicit matching30 handoff required"
    h = _read(HANDOFF)
    assert h["status"] == "passed_read_only_terminal_build_handoff" and h["process_exit"] == 0
    assert h["source_tree_sha256"] == value["native_source_tree_sha256"]
    assert h["native_binary_hashes"] == value["activated"]
    assert h["proof_input_hashes"] == value["proof_input_hashes"]
    for name, digest in value["proof_input_hashes"].items():
        assert _sha(ACTIVATION.parent / name) == digest
    frozen = _read(ACTIVATION.parent / "frozen-inputs.json")
    assert type(frozen["epoch"]) is int and frozen["epoch"] == 30
    assert frozen["source_tree_sha256"] == h["source_tree_sha256"]
    for name, digest in value["activated"].items():
        base = ROOT / ("src/vispy/visuals/text" if name.startswith("_sdf_cpu.") else "src/vispy")
        assert _sha(base / name) == digest
    return {"path": str(path), "sha256": expected, "handoff_sha256": handoff_sha, "activation": value}


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_pending_pixels_distinguish_every_old_and_new_region(name):
    p = retired.plan(name, f.SAMPLE_LIMITS)
    old, new = retired.expected_image(p), retired.expected_image(p, revised=True)
    combined = f.expected_pending(p)
    assert p.target_bytes > 64 * 1024 * 1024
    assert np.count_nonzero(np.any(old[..., :3], axis=2)) == (192 if name == f.CASES[2] else 48)
    np.testing.assert_array_equal(combined[12:], old[12:])
    np.testing.assert_array_equal(combined[:12], new[12:])
    assert not np.array_equal(old, new) and np.all(combined[..., 3] == 255)
    # Revised affine/instance shaders deliberately produce some opaque black
    # triangles. Exact arrays still prove those pixels; RGB occupancy does not.
    assert np.count_nonzero(np.any(combined[..., :3], axis=2)) == (
        np.count_nonzero(np.any(old[..., :3], axis=2)) +
        np.count_nonzero(np.any(new[..., :3], axis=2)))
    assert not np.array_equal(combined, f.shift_band(new, 12)), "skipped old draw must fail"
    assert not np.array_equal(combined, f.overlay(old, f.shift_band(old, 12))), "lost revision must fail"


@pytest.mark.parametrize("layouts", (2, 5))
def test_cpu_working_payloads_and_grants_are_checked_before_allocation(layouts):
    w = f.working_plan(f.SAMPLE_LIMITS, layouts=layouts)
    assert w.payload_bytes_per_layout > f.HISTORY_BYTES
    assert (w.minimum_payload_graph_bytes < f.WORKING_BYTES) == (layouts == 2)
    assert w.source_rows * 4 < f.SAMPLE_LIMITS["max_buffer_size"]
    assert w.base.first == 3 and w.base.count % 6 == 0
    with pytest.raises(ValueError):
        f.working_plan({**f.SAMPLE_LIMITS, "max_buffer_size": w.base.target_bytes - 1}, layouts=layouts)
    with pytest.raises(ValueError):
        f.working_plan({**f.SAMPLE_LIMITS, "max_vertex_buffer_array_stride": w.base.stride - 1}, layouts=layouts)
    with pytest.raises(ValueError):
        f.working_plan(f.SAMPLE_LIMITS, layouts=3)


def test_cpu_working_pixels_use_original_ids_and_last_vertex_halfplanes():
    w = f.working_plan(f.SAMPLE_LIMITS, layouts=5)
    images = [f.expected_working(w, layout) for layout in range(5)]
    assert len({image.tobytes() for image in images}) == 5
    for layout, image in enumerate(images):
        first = w.base.first + (layout + 1) * w.base.count - 6
        for dy in range(6):
            for dx in range(8):
                distance = 6 * (dx + .5) + 8 * (dy + .5)
                assert distance != 48
                vertex = first + (2 if distance < 48 else 5)
                np.testing.assert_array_equal(image[23 - (4 + dy), 4 + 2 * layout + dx],
                    [255 * (vertex % 2), 255, 255 * (layout % 2), 255])
    ordered = f.overlay(f.overlay(images[0], f.shift_band(images[1], 3)), f.shift_band(images[0], 6))
    wrong = f.overlay(f.overlay(images[0], f.shift_band(images[0], 6)), f.shift_band(images[1], 3))
    assert not np.array_equal(ordered, wrong), "middle/final reorder must change pixels"
    source = f.working_vertex_source(w)
    assert "gl_VertexID" in source and "uniform" not in source and "texture" not in source
    for lane in range(w.base.lanes):
        assert f"a_lane{lane}" in source.split("float energy = ")[1].split(";")[0]


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_scaled_public_construction_and_actual_emitter_revisions(name):
    from vispy import gloo
    p = retired.plan(name, f.SAMPLE_LIMITS, budget=256)
    program, buffers, indices = retired.make_program(gloo, p)
    queue = program.glir
    initial = queue.clear()
    assert any(command[0] == "ATTRIBUTE" for command in initial)
    retired.revise(program, buffers, indices, p)
    revised = queue.clear()
    if name == f.CASES[1]:
        assert any(c[:3] == ("ATTRIBUTE", program.id, "a_lane0") for c in revised)
    else:
        source = indices if indices is not None else buffers[1]
        revised += source.glir.clear()
        assert any(c[0] == "DATA" and c[1] == source.id for c in revised)
    f.delete_sources(program, buffers, indices)
    assert any(c[0] == "DELETE" for c in queue.clear())


def test_cpu_scaled_working_inputs_do_not_change_between_selectors():
    from vispy import gloo
    w = f.working_plan(f.SAMPLE_LIMITS, layouts=5, budget=256)
    program, buffers, _ = f.make_working_program(gloo, w)
    commands = program.glir.clear()
    assert all(buffer.dtype.itemsize == 4 and len(buffer.dtype.names) == 1
               and buffer.dtype.fields[buffer.dtype.names[0]][0] == np.dtype(np.float32)
               for buffer in buffers)
    assert buffers[0].size == w.source_rows
    # Actual upstream queue commands are generated without a Canvas or parser.
    for layout in (0, 1, 0):
        program.glir.command("DRAW", program.id, "triangles", (w.base.first + layout * w.base.count, w.base.count), 1)
    draw_commands = program.glir.clear()
    assert [c[0] for c in draw_commands] == ["DRAW"] * 3
    assert draw_commands[0] == draw_commands[2] and draw_commands[0] != draw_commands[1]
    assert any(c[0] == "ATTRIBUTE" for c in commands)
    f.delete_sources(program, buffers, None)


def test_cpu_actual_nested_numpy_glir_fields_serialize_without_losing_array_identity():
    values = np.asarray([(1.,)], dtype=[("f0", np.float32)])
    command = ("ATTRIBUTE", 7, "a_lane0", "float", (np.float32(1.), np.int32(2)))
    assert json.loads(json.dumps(f.command_record(command))) == ["ATTRIBUTE", 7, "a_lane0", "float", [1., 2]]
    data = f.command_record(("DATA", 7, 0, values))
    assert data[-1]["sha256"] == hashlib.sha256(values.tobytes()).hexdigest()
    assert data[-1]["dtype_descriptor"] == repr(values.dtype.descr)
    np.testing.assert_array_equal(values["f0"], [1.])


def test_cpu_old_unpinned_substituted_and_bool_epochs_are_rejected():
    good = "a" * 64
    _check_header(ACTIVATION, good, good, {"epoch": 30})
    for path, expected, actual, value in (
        (ACTIVATION.with_name("fake.json"), good, good, {"epoch": 30}),
        (ACTIVATION, "", good, {"epoch": 30}),
        (ACTIVATION, good, "b" * 64, {"epoch": 30}),
        (ACTIVATION, good, good, {"epoch": 29}),
        (ACTIVATION, good, good, {"epoch": True}),
    ):
        with pytest.raises(AssertionError):
            _check_header(path, expected, actual, value)


def test_cpu_every_resident_cost_and_working_budget_violation_is_rejected():
    before = {name: 10 for name in f.RESIDENT}
    f.assert_resident(before, dict(before))
    for name in f.RESIDENT:
        with pytest.raises(AssertionError):
            f.assert_resident(before, {**before, name: 11})
    baseline = {name: 0 for name in ("vertex_input_oversized_entries", "vertex_input_oversized_bytes", "vertex_input_current_entries", "vertex_input_cache_entries", "vertex_input_cache_bytes")}
    good = {**baseline, "vertex_input_oversized_entry_limit": 8, "vertex_input_oversized_byte_limit": f.WORKING_BYTES}
    f.assert_working_bounds(baseline, good)
    for name, value in (("vertex_input_oversized_entries", 9), ("vertex_input_oversized_bytes", f.WORKING_BYTES + 1), ("vertex_input_current_entries", 7), ("vertex_input_cache_bytes", f.HISTORY_BYTES + 1)):
        with pytest.raises(AssertionError):
            f.assert_working_bounds(baseline, {**good, name: value})


def _submitted(before, value):
    assert before["pending_tickets"] == 0
    assert value["dawn_queue_submits"] == before["dawn_queue_submits"] + 1
    assert value["pending_tickets"] > 0 and value["pending_draws"] == 0


def _executed(before, after, *, draws=1):
    assert after["draw_calls"] - before["draw_calls"] == draws
    assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == 1
    assert after["retired_tickets"] - before["retired_tickets"] == 1
    assert after["pending_draws"] == after["pending_tickets"] == 0


def test_cpu_same_pixel_skipped_draw_extra_submit_or_unretired_work_cannot_pass():
    before = {"draw_calls": 10, "dawn_queue_submits": 20, "retired_tickets": 20}
    good = {"draw_calls": 11, "dawn_queue_submits": 21, "retired_tickets": 21,
            "pending_draws": 0, "pending_tickets": 0}
    _executed(before, good)
    for key, value in (("draw_calls", 10), ("dawn_queue_submits", 22),
                       ("retired_tickets", 20), ("pending_draws", 1), ("pending_tickets", 1)):
        with pytest.raises(AssertionError):
            _executed(before, {**good, key: value})


def _receipt(rows, *, success):
    assert len(rows) == 1
    row = rows[0]
    assert row["ownership_closed"] and row["ownership_retired"]
    assert row["submission_count"] == 1 and row["presented"] is False
    assert row["frame_scope"] in ("native_present", "qt_paint")
    if success:
        assert row["status"] == "success" and row["counters_captured"]
    else:
        assert row["status"] in ("device_lost", "failed", "cancelled")
    return row


def test_cpu_ticket_witness_and_loss_admission_reject_successful_or_unsubmitted_work():
    before = {"pending_tickets": 0, "dawn_queue_submits": 10}
    submitted = {"pending_tickets": 1, "pending_draws": 0, "dawn_queue_submits": 11}
    _submitted(before, submitted)
    for wrong in ({**submitted, "pending_tickets": 0}, {**submitted, "pending_draws": 2},
                  {**submitted, "dawn_queue_submits": 10}):
        with pytest.raises(AssertionError):
            _submitted(before, wrong)
    row = {"status": "device_lost", "ownership_closed": True, "ownership_retired": True,
           "submission_count": 1, "presented": False, "frame_scope": "qt_paint", "counters_captured": False}
    assert _receipt([row], success=False) == row
    for wrong in ({**row, "status": "success"}, {**row, "ownership_retired": False},
                  {**row, "submission_count": 0}, {**row, "presented": True}):
        with pytest.raises(AssertionError):
            _receipt([wrong], success=False)
    with pytest.raises(AssertionError):
        _receipt([row, row], success=False)


def _retire(native, canvas_id, records, *, timeout=120.):
    deadline = time.monotonic() + timeout
    while True:
        native.process_events()
        incoming = native.benchmark_completions(canvas_id)
        records.setdefault("raw_completion_batches", []).append(incoming)
        value = dict(native.probe())
        if all(value[name] == 0 for name in ("pending_tickets", "queued_frames", "pending_draws", "pending_timestamp_frames")):
            return value
        assert time.monotonic() < deadline, {"unretired_actual_work": value}
        time.sleep(.001)


def test_cpu_retirement_pumps_exported_events_and_preserves_receipts_without_finish():
    class Native:
        polls = 0

        def process_events(self):
            self.polls += 1

        def benchmark_completions(self, canvas_id):
            assert canvas_id == 7
            return [{"frame_id": 19}] if self.polls == 2 else []

        def probe(self):
            busy = int(self.polls == 1)
            return {"pending_tickets": busy, "queued_frames": 0,
                    "pending_draws": 0, "pending_timestamp_frames": busy}

    native, records = Native(), {}
    assert _retire(native, 7, records)["pending_tickets"] == 0
    assert native.polls == 2 and records["raw_completion_batches"] == [[], [{"frame_id": 19}]]


class Evidence:
    def __init__(self, name):
        base = Path(os.environ["VISPY_OVERSIZED_PENDING_EVIDENCE"])
        self.output = base / name
        self.output.mkdir(parents=True, exist_ok=False)
        self.value = {"contract": f.contract(), "GPU_used": False, "images": {}, "filtered_GLIR": []}

    def save(self):
        (self.output / "records.json").write_text(json.dumps(self.value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def image(self, name, actual, expected):
        np.save(self.output / (name + ".npy"), actual, allow_pickle=False)
        np.save(self.output / (name + "-expected.npy"), expected, allow_pickle=False)
        self.value["images"][name] = {"actual": f.array_record(actual), "expected": f.array_record(expected)}
        self.save()
        np.testing.assert_array_equal(actual, expected)


@pytest.fixture
def hardware(request):
    # This guard deliberately precedes any native import or device creation.
    activation = _activation_before_native()
    from vispy import _dawn as native, app, gloo
    evidence = Evidence(request.node.name)
    canvas = None
    parser = original_parse = None
    try:
        authored = _read(AUTHORING)
        assert authored["contract"] == f.contract() and authored["GPU_used"] is False
        for name, checksum in authored["sources_sha256"].items():
            assert _sha(ROOT / name) == checksum
        assert Path(native.__file__).resolve() == ROOT / "src/vispy/_dawn.cp312-win_amd64.pyd"
        assert _sha(native.__file__) == activation["activation"]["activated"][Path(native.__file__).name]
        canvas = app.Canvas(app="dawn_headless", size=f.SIZE, show=False)
        canvas.set_current()
        cid = canvas._backend._dawn_canvas_id
        device = native.device_info()
        assert device["ok"] and not device["software"] and device["backend"] == "Vulkan" and device["last_vertex_provoking"]
        required = ("vertex_input_oversized_entries", "vertex_input_oversized_bytes", "vertex_input_oversized_entry_limit", "vertex_input_oversized_byte_limit", "vertex_input_oversized_evictions")
        assert all(key in native.probe() for key in required), "matching oversized working-set native API required"
        parser = canvas.context.shared.parser
        original_parse = parser.parse

        def observe(commands):
            evidence.value["filtered_GLIR"].append([f.command_record(c) for c in commands])
            return original_parse(commands)

        parser.parse = observe
        f.configure(gloo, clear=True)
        canvas.context.flush_commands()
        canvas.swap_buffers()
        baseline = _retire(native, cid, evidence.value)
        evidence.value.update(GPU_used=True, activation=activation, authoring=authored, device=device,
                              native_origin=native.__file__, native_sha256=_sha(native.__file__), baseline=baseline)
        evidence.save()
        yield canvas, native, gloo, cid, evidence
    except BaseException:
        evidence.value["assertion_traceback"] = traceback.format_exc()
        raise
    finally:
        evidence.save()
        if parser is not None and original_parse is not None:
            parser.parse = original_parse
        if canvas is not None:
            canvas.close()


def _cold(canvas, native, gloo, cid, e, program, indices, p):
    retired.draw(canvas, gloo, program, indices, p)
    canvas.swap_buffers()
    return _retire(native, cid, e.value)


def _capture(canvas, native, gloo, cid, e, name, expected):
    before_read = _retire(native, cid, e.value)
    e.value[name + "-before-quality-read"] = before_read
    e.image(name, gloo.read_pixels((0, 0, *f.SIZE), alpha=True), expected)
    _retire(native, cid, e.value)
    return before_read


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
def test_pending_old_revision_new_snapshots_survive_one_final_submission(name, hardware):
    canvas, native, gloo, cid, e = hardware
    p = retired.plan(name, e.value["device"])
    program, buffers, indices = retired.make_program(gloo, p)
    before = _cold(canvas, native, gloo, cid, e, program, indices, p)
    f.draw_revision(canvas, gloo, program, indices, p)
    first = dict(native.probe())
    retired.revise(program, buffers, indices, p)
    f.draw_revision(canvas, gloo, program, indices, p, clear=False, band=12)
    pending = dict(native.probe())
    e.value.update(plan=asdict(p), before=before, first_pending=first, both_pending=pending)
    assert first["pending_draws"] == 2 and pending["pending_draws"] == 3
    assert pending["draw_calls"] == before["draw_calls"] and pending["dawn_queue_submits"] == before["dawn_queue_submits"]
    assert pending["completion_waits"] == before["completion_waits"] and pending["finish_calls"] == before["finish_calls"]
    canvas.swap_buffers()
    after = _capture(canvas, native, gloo, cid, e, "old-new", f.expected_pending(p))
    _executed(before, after, draws=2)
    f.delete_sources(program, buffers, indices)
    canvas.context.flush_commands()


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
def test_source_and_program_delete_before_present_preserve_queued_snapshots(name, hardware):
    canvas, native, gloo, cid, e = hardware
    p = retired.plan(name, e.value["device"])
    program, buffers, indices = retired.make_program(gloo, p)
    before = _cold(canvas, native, gloo, cid, e, program, indices, p)
    f.draw_revision(canvas, gloo, program, indices, p)
    retired.revise(program, buffers, indices, p)
    f.draw_revision(canvas, gloo, program, indices, p, clear=False, band=12)
    prepared = dict(native.probe())
    f.delete_sources(program, buffers, indices)
    canvas.context.flush_commands()
    deleted = dict(native.probe())
    e.value.update(plan=asdict(p), before=before, before_delete=prepared, after_delete_pending=deleted)
    assert prepared["pending_draws"] == deleted["pending_draws"] == 3
    assert deleted["pending_tickets"] == 0 and deleted["dawn_queue_submits"] == before["dawn_queue_submits"]
    assert deleted["live_cpu_buffer_bytes"] - e.value["baseline"]["live_cpu_buffer_bytes"] >= 2 * p.target_bytes
    canvas.swap_buffers()
    after = _capture(canvas, native, gloo, cid, e, "deleted-old-new", f.expected_pending(p))
    _executed(before, after, draws=2)
    assert after["vertex_input_current_entries"] == e.value["baseline"]["vertex_input_current_entries"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
def test_submitted_ticket_retains_deleted_sources_until_real_retirement(name, hardware):
    canvas, native, gloo, cid, e = hardware
    p = retired.plan(name, e.value["device"])
    program, buffers, indices = retired.make_program(gloo, p)
    before = _cold(canvas, native, gloo, cid, e, program, indices, p)
    native.benchmark_begin_frame(cid, 0)
    f.draw_revision(canvas, gloo, program, indices, p)
    canvas.swap_buffers()
    submitted = dict(native.probe())
    _submitted(before, submitted)
    f.delete_sources(program, buffers, indices)
    canvas.context.flush_commands()
    deleted = dict(native.probe())
    e.value.update(plan=asdict(p), before=before, submitted=submitted, deleted_before_retirement=deleted)
    assert deleted["pending_tickets"] > 0
    assert deleted["live_buffer_bytes"] - e.value["baseline"]["live_buffer_bytes"] >= p.target_bytes
    after = _capture(canvas, native, gloo, cid, e, "submitted-deleted", retired.expected_image(p))
    _executed(before, after)
    rows = [r for batch in e.value["raw_completion_batches"] for r in batch]
    _receipt(rows, success=True)
    assert after["vertex_input_current_entries"] == e.value["baseline"]["vertex_input_current_entries"]
    # DELETE objects leave the native registry on the following real GLIR
    # parse. The separate quality read performs that parse after retirement.
    released = dict(native.probe())
    e.value["after_retirement_and_delete_registry_collection"] = released
    assert released["live_cpu_buffer_bytes"] == e.value["baseline"]["live_cpu_buffer_bytes"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
def test_submitted_loss_does_not_replay_deleted_program_and_recovers_survivor(name, hardware):
    canvas, native, gloo, cid, e = hardware
    p = retired.plan(name, e.value["device"])
    survivor, kept, keep_index = retired.make_program(gloo, p)
    before = _cold(canvas, native, gloo, cid, e, survivor, keep_index, p)
    temporary, discarded, discard_index = retired.make_program(gloo, p)
    native.benchmark_begin_frame(cid, 0)
    token = native.begin_canvas_paint(cid)
    f.draw_revision(canvas, gloo, temporary, discard_index, p)
    canvas.swap_buffers()
    submitted = dict(native.probe())
    _submitted(before, submitted)
    assert submitted["draw_calls"] - before["draw_calls"] == 1
    f.delete_sources(temporary, discarded, discard_index)
    canvas.context.flush_commands()
    e.value.update(plan=asdict(p), before_loss=before, submitted_loss=submitted, deleted_loss_pending=dict(native.probe()))
    assert e.value["deleted_loss_pending"]["pending_tickets"] > 0, "loss must observe a real outstanding Ticket"
    native.lose_device()
    native.abort_canvas_paint(cid, token, "actual submitted device-loss test cleanup")
    lost = _retire(native, cid, e.value)
    rows = [r for batch in e.value["raw_completion_batches"] for r in batch]
    _receipt(rows, success=False)
    before_recovery = dict(native.probe())
    f.draw_revision(canvas, gloo, survivor, keep_index, p)
    canvas.swap_buffers()
    recovered = _retire(native, cid, e.value)
    e.value.update(loss_terminal=rows[0], after_logical_loss_retirement=lost, recovery_before=before_recovery, recovered=recovered)
    assert recovered["device_generation"] > before["device_generation"]
    for key in ("vertex_input_conversion_builds", "vertex_input_conversion_bytes", "point_conversion_builds", "portable_shader_misses"):
        assert recovered[key] == before_recovery[key], key
    assert recovered["buffer_uploads"] - before_recovery["buffer_uploads"] == p.geometry_buffers
    assert recovered["geometry_upload_bytes"] - before_recovery["geometry_upload_bytes"] == p.geometry_upload_bytes
    assert recovered["draw_calls"] - before_recovery["draw_calls"] == 1, "deleted Program must not replay"
    _capture(canvas, native, gloo, cid, e, "survivor-recovered", retired.expected_image(p))
    warm_before = _retire(native, cid, e.value)
    f.draw_revision(canvas, gloo, survivor, keep_index, p)
    canvas.swap_buffers()
    warm_after = _retire(native, cid, e.value)
    f.assert_resident(warm_before, warm_after)
    e.value.update(recovered_warm_before=warm_before, recovered_warm_after=warm_after)
    f.delete_sources(survivor, kept, keep_index)
    canvas.context.flush_commands()


def _working_frame(hardware, program, w, layout, phase, *, resident=False):
    canvas, native, gloo, cid, e = hardware
    before = _retire(native, cid, e.value)
    f.draw_working(canvas, gloo, program, w, layout)
    canvas.swap_buffers()
    after = _retire(native, cid, e.value)
    e.value[phase] = {"layout": layout, "before": before, "after_retirement_before_read": after}
    _executed(before, after)
    if resident:
        f.assert_resident(before, after)
    f.assert_working_bounds(e.value["baseline"], after)
    _capture(canvas, native, gloo, cid, e, phase, f.expected_working(w, layout))
    return before, after


@pytest.mark.gpu
def test_unchanged_affine_a_b_a_working_set_reuses_both_oversized_graphs(hardware):
    canvas, native, gloo, cid, e = hardware
    w = f.working_plan(e.value["device"], layouts=2)
    program, buffers, _ = f.make_working_program(gloo, w)
    e.value["working_plan"] = asdict(w)
    _working_frame(hardware, program, w, 0, "cold-A")
    _, built = _working_frame(hardware, program, w, 1, "cold-B")
    assert built["vertex_input_oversized_entries"] - e.value["baseline"]["vertex_input_oversized_entries"] >= 2
    assert built["vertex_input_oversized_bytes"] - e.value["baseline"]["vertex_input_oversized_bytes"] >= 2 * w.payload_bytes_per_layout
    for index, layout in enumerate((0, 1, 0, 1)):
        _working_frame(hardware, program, w, layout, f"resident-{index}", resident=True)
    f.delete_sources(program, buffers, None)
    canvas.context.flush_commands()
    deleted = _retire(native, cid, e.value)
    assert deleted["vertex_input_oversized_entries"] == e.value["baseline"]["vertex_input_oversized_entries"]


@pytest.mark.gpu
def test_five_unchanged_oversized_selections_evict_within_declared_working_budget(hardware):
    canvas, native, gloo, cid, e = hardware
    w = f.working_plan(e.value["device"], layouts=5)
    assert w.minimum_payload_graph_bytes > f.WORKING_BYTES
    program, buffers, _ = f.make_working_program(gloo, w)
    e.value["working_plan"] = asdict(w)
    initial = dict(native.probe())
    for index, layout in enumerate((0, 1, 2, 3, 4)):
        _working_frame(hardware, program, w, layout, f"overbudget-{index}")
    after = dict(native.probe())
    assert after["vertex_input_oversized_evictions"] > initial["vertex_input_oversized_evictions"]
    # Five graphs cannot fit; the most recent exact key must remain resident.
    _working_frame(hardware, program, w, 4, "overbudget-current-resident", resident=True)
    f.delete_sources(program, buffers, None)
    canvas.context.flush_commands()
    _retire(native, cid, e.value)


@pytest.mark.gpu
def test_actual_cached_queued_batches_keep_order_and_bounded_backpressure(hardware):
    canvas, native, gloo, cid, e = hardware
    w = f.working_plan(e.value["device"], layouts=2)
    program, buffers, _ = f.make_working_program(gloo, w)
    _working_frame(hardware, program, w, 0, "queue-cold-A")
    _working_frame(hardware, program, w, 1, "queue-cold-B")
    idle = _retire(native, cid, e.value)
    old_slots = idle["frame_slots"]
    native.configure_frame_slots(1)
    sequence = [(0, 0), (1, 3), (0, 6)]
    expected = np.zeros((f.SIZE[1], f.SIZE[0], 4), np.uint8)
    expected[..., 3] = 255
    probes = []
    try:
        before = dict(native.probe())
        for index, (layout, band) in enumerate(sequence):
            if index == 2:
                deadline = time.monotonic() + 120
                while not native.frame_ready(cid):
                    native.process_events()
                    assert time.monotonic() < deadline
                    time.sleep(.001)
            f.draw_working(canvas, gloo, program, w, layout, clear=index == 0, band=band, repeats=4)
            canvas.swap_buffers()
            value = dict(native.probe())
            probes.append(value)
            assert 0 <= value["pending_tickets"] <= 1 and 0 <= value["queued_frames"] <= 1
            expected = f.overlay(expected, f.expected_working(w, layout, band=band))
        after = _retire(native, cid, e.value)
        e.value.update(queue_sequence=sequence, queue_before=before, actual_queue_probes=probes, queue_after=after)
        assert any(p["queued_frames"] > 0 for p in probes), "required real queued branch was not witnessed"
        assert after["deferred_frames"] > before["deferred_frames"], "no native backpressure witness"
        assert after["draw_calls"] - before["draw_calls"] == 12
        assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == 3
        f.assert_resident(before, after)
        _capture(canvas, native, gloo, cid, e, "ordered-queued", expected)
    finally:
        try:
            _retire(native, cid, e.value)
        finally:
            try:
                native.configure_frame_slots(old_slots)
            finally:
                f.delete_sources(program, buffers, None)
                canvas.context.flush_commands()



def test_cpu_full_target_capture_ignores_shifted_draw_viewport():
    import ast

    baseline_path = ROOT / "tests/native/test_ordinary_oversized_pending.py"
    assert _sha(baseline_path) == "985739a747d948ee55cfff22ca4bed0ce5414d969ab613b6c973828c2daf4c6b"
    tree = ast.parse(baseline_path.read_text(encoding="utf-8"))
    baseline_capture = next(node for node in tree.body
                            if isinstance(node, ast.FunctionDef) and node.name == "_capture")
    namespace = {"_retire": _retire}
    exec(compile(ast.Module(body=[baseline_capture], type_ignores=[]), str(baseline_path), "exec"), namespace)

    # This stub proves the read rectangle and retirement boundary only. It does
    # not stand in for GPU execution or relax the full-frame pixel assertion.
    for band in (6, 12):
        events = []
        original_viewport = (0, band, *f.SIZE)
        expected = np.arange(f.SIZE[0] * f.SIZE[1] * 4, dtype=np.uint16).reshape(
            f.SIZE[1], f.SIZE[0], 4).astype(np.uint8)
        retained = expected.copy()

        class Native:
            def process_events(self):
                events.append("poll")

            def benchmark_completions(self, canvas_id):
                assert canvas_id == 7
                return []

            def probe(self):
                return {key: 0 for key in ("pending_tickets", "queued_frames",
                                           "pending_draws", "pending_timestamp_frames")}

        class Gloo:
            viewport = original_viewport

            def read_pixels(self, viewport=None, *, alpha=False):
                requested = self.viewport if viewport is None else tuple(viewport)
                events.append(("read", requested, alpha))
                x, y, width, height = requested
                if x < 0 or y < 0 or x + width > f.SIZE[0] or y + height > f.SIZE[1]:
                    raise RuntimeError("read_pixels rectangle exceeds target bounds")
                assert requested == (0, 0, *f.SIZE) and alpha is True
                return retained.copy()

        class CaptureEvidence:
            def __init__(self):
                self.value = {}
                self.images = []

            def image(self, name, actual, wanted):
                assert name + "-before-quality-read" in self.value
                assert events[-2:] == ["poll", ("read", (0, 0, *f.SIZE), True)]
                np.testing.assert_array_equal(actual, wanted)
                assert wanted is expected
                self.images.append((name, actual.copy()))

        native, gloo, legacy_evidence = Native(), Gloo(), CaptureEvidence()
        with pytest.raises(RuntimeError, match="rectangle exceeds target bounds"):
            namespace["_capture"](object(), native, gloo, 7, legacy_evidence, "legacy", expected)
        assert events == ["poll", ("read", original_viewport, True)]
        assert not legacy_evidence.images and "legacy-before-quality-read" in legacy_evidence.value
        assert gloo.viewport == original_viewport

        events.clear()
        evidence = CaptureEvidence()
        result = _capture(object(), native, gloo, 7, evidence, "full-target", expected)
        assert events == ["poll", ("read", (0, 0, *f.SIZE), True), "poll"]
        assert result == evidence.value["full-target-before-quality-read"]
        assert len(evidence.value["raw_completion_batches"]) == 2
        assert len(evidence.images) == 1
        assert gloo.viewport == original_viewport
        np.testing.assert_array_equal(expected, retained)
        np.testing.assert_array_equal(evidence.images[0][1], retained)
