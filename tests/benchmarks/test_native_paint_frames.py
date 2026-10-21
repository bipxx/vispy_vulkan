"""CPU-authored gates for a matching whole-Qt-paint native epoch.

Only tests marked gpu create a Canvas. Required unavailable instrumentation
fails qualification explicitly; these tests do not substitute mocked records.
"""
import copy
import time
import traceback

import numpy as np
import pytest

from tools.fixture_native_paint_frames import (
    Evidence, FRAME_IDS, PaintHarness, PHASES, QUERY_COUNTERS, RESIDENT,
    SIZE, UNSUBMITTED_INDEX, check_success, check_timing, contract,
    expected_pixels, presented_bgra_to_rgba, require_full_paint_api,
)


def test_cpu_declared_paint_passes_cover_alpha_and_both_presentations():
    value = contract()
    assert value["candidate_seen"] is True and value["GPU_used"] is False
    assert value["matching_native28_hardware_seen"] is True
    assert value["frames"] == list(range(12))
    assert list(value["issued_phases"].values()).count("warmup") == 4
    assert list(value["issued_phases"].values()).count("measured") == 8
    for name, expected in (("normal", [0, 0, 0, 0, 1, 1, 1]),
                           ("intermediate", [0, 0, 1, 2, 2, 2])):
        layout = value[name]
        assert layout["pass_submission_indices"] == expected
        pairs = list(zip(layout["pass_kinds"], expected))
        conversions = [index for kind, index in pairs if kind == "surface_conversion"]
        assert len(set(conversions)) == layout["presents"] == 2
        assert max(conversions) == layout["last_present"]
        assert ("clear", layout["last_present"]) in pairs
        assert pairs[:2] == [("clear", 0), ("scene", 0)]
        assert layout["scene_draws"] == 1
        assert layout["native_draws"] == len(expected) - 1
    assert "buffer_upload_cpu_ns" not in value["resident_unchanged_counters"]
    assert value["transient_uniforms"]["bytes_per_paint"] == 32
    assert all(key in value["resident_unchanged_counters"] for key in
               ("buffer_uploads", "geometry_upload_bytes", "texture_uploads", "point_conversion_builds",
                "vertex_input_conversion_builds", "portable_shader_misses", "completion_waits"))
    assert any("acquisition-fault" in scope and "OPEN" in scope for scope in value["scope_limits"])


def test_cpu_binary_quality_is_fixed_before_any_candidate():
    for frame_id in FRAME_IDS:
        pixels = expected_pixels(frame_id)
        assert pixels.shape == (SIZE[1], SIZE[0], 4) and pixels.dtype == np.uint8
        assert np.unique(pixels.reshape(-1, 4), axis=0).tolist() == [
            [255, 0, 0, 64] if frame_id % 2 else [0, 255, 0, 64]]


def test_cpu_raw_bgra_mapping_preserves_asymmetric_rows_alpha_and_source():
    # A padded row stride and four distinct RGBA values catch row flips,
    # double channel swaps, alpha changes and view/ownership mistakes.
    backing = np.array([
        [[7, 13, 19, 23], [29, 31, 37, 41], [0, 0, 0, 0]],
        [[43, 47, 53, 59], [61, 67, 71, 73], [0, 0, 0, 0]],
    ], np.uint8)
    raw = backing[:, :2]
    before = backing.copy()
    expected = np.array([
        [[19, 13, 7, 23], [37, 31, 29, 41]],
        [[53, 47, 43, 59], [71, 67, 61, 73]],
    ], np.uint8)
    converted = presented_bgra_to_rgba(raw)
    np.testing.assert_array_equal(converted, expected)
    assert converted.dtype == np.uint8 and converted.shape == (2, 2, 4)
    assert converted.flags.owndata and converted.flags.c_contiguous
    assert not np.shares_memory(converted, raw)
    np.testing.assert_array_equal(converted[..., [2, 1, 0, 3]], raw)
    converted[0, 0] = [1, 2, 3, 4]
    np.testing.assert_array_equal(backing, before)
    for invalid in (raw.astype(np.float32), raw[..., :3], raw[0], raw[:0], raw.tolist()):
        with pytest.raises(ValueError, match="nonempty uint8 HxWx4 BGRA"):
            presented_bgra_to_rgba(invalid)


def test_cpu_old_epoch_is_rejected_before_canvas_creation():
    with pytest.raises(RuntimeError, match="matching full-paint native epoch required"):
        require_full_paint_api(object())


@pytest.fixture
def paint_factory(request):
    opened = []

    def create(**options):
        evidence = Evidence(request.node.name)
        harness = PaintHarness.__new__(PaintHarness)
        # Retain the partially initialized owner if a real setup fails.
        opened.append((harness, evidence))
        try:
            harness.__init__(evidence, **options)
        except BaseException:
            evidence.value.update(outcome="failed-setup", assertion_traceback=traceback.format_exc())
            evidence.save()
            raise
        return harness

    try:
        yield create
    finally:
        for harness, evidence in reversed(opened):
            try:
                if hasattr(harness, "evidence"):
                    harness.close()
            except BaseException:
                evidence.value["cleanup_error"] = traceback.format_exc()
                evidence.save()
                raise


def _snapshot(harness, name):
    value = dict(harness.native.probe())
    harness.evidence.value["snapshots"][name] = copy.deepcopy(value)
    harness.evidence.save()
    return value


def _bounded(harness, point):
    probe = _snapshot(harness, point)
    assert 0 <= probe["pending_tickets"] <= probe["frame_slots"]
    assert 0 <= probe["queued_frames"] <= probe["frame_slots"]
    assert 0 <= probe["pending_timestamp_frames"] <= probe["frame_slots"]
    return probe


def _drain_success(harness, expected):
    deadline = time.monotonic() + 10
    while True:
        harness.canvas.app.process_events()
        harness.collect("success-drain", "measured")
        _bounded(harness, "drain")
        receipt_ids = set(harness.completions.results)
        gpu_ids = set(harness.collector.gpu_frames.results)
        if receipt_ids == set(expected) and (not harness.collector.gpu_metadata["enabled"] or gpu_ids == set(expected)):
            return
        assert time.monotonic() < deadline, "closed paints did not asynchronously retire all owned work"
        time.sleep(.001)


@pytest.mark.gpu
@pytest.mark.parametrize("queries,vsync,intermediate", [
    (False, False, False), (True, False, False),
    (True, True, False), (True, False, True),
], ids=["queries-off", "queries-on", "fifo", "actual-intermediate"])
def test_twelve_real_qt_paints_join_every_owned_submission(paint_factory, queries, vsync, intermediate):
    harness = paint_factory(queries=queries, vsync=vsync, intermediate=intermediate,
                            frame_slots=1 if vsync else None)
    try:
        before = _snapshot(harness, "resident-before")
        for frame_id in FRAME_IDS:
            deadline = time.monotonic() + 10
            while not harness.native.frame_ready(harness.canvas_id):
                harness.canvas.app.process_events()
                harness.collect("frame-ready-backpressure", PHASES[frame_id])
                _bounded(harness, "backpressure")
                assert time.monotonic() < deadline, "nonblocking capacity never became ready"
                time.sleep(.001)
            harness.issue(frame_id, PHASES[frame_id])
            harness.dispatch(frame_id)
            harness.collect("after-real-paint-return", PHASES[frame_id])
            _bounded(harness, f"after-paint-{frame_id}")
        _drain_success(harness, FRAME_IDS)
        samples = harness.completions.samples("warmup") + harness.completions.samples("measured")
        assert harness.completions.issued == PHASES
        assert [row["frame_id"] for row in harness.raw_receipts] == list(FRAME_IDS), "successful owners must publish once in FIFO order"
        assert len({row["paint_token"] for row in samples}) == len(FRAME_IDS)
        assert harness.seen == {frame_id: 1 for frame_id in FRAME_IDS}
        if queries:
            harness.collector.gpu_frames.join(samples)
            assert [row["frame_id"] for row in harness.raw_gpu] == list(FRAME_IDS)
        else:
            assert harness.raw_gpu == []
        for sample in samples:
            check_success(sample, harness.scene_before[sample["frame_id"]], intermediate=intermediate)
            if queries:
                check_timing(sample["gpu_timing"], sample, intermediate=intermediate)
        assert harness.collector.verify_scope(samples) is True
        assert harness.collector.boundary["whole_qt_paint_scope_verified"] is True
        after = _snapshot(harness, "resident-after")
        for name in RESIDENT:
            assert after[name] == before[name], f"resident paint changed {name}"
        layout = contract()["intermediate" if intermediate else "normal"]
        submissions = len(FRAME_IDS) * layout["submissions"]
        assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == submissions
        assert after["application_presents"] - before["application_presents"] == 24
        assert after["draw_calls"] - before["draw_calls"] == 12
        assert after["native_draw_calls"] - before["native_draw_calls"] == 12 * layout["native_draws"]
        assert after["uniform_upload_bytes"] - before["uniform_upload_bytes"] == 12 * contract()["transient_uniforms"]["bytes_per_paint"]
        assert after["pending_tickets"] == after["queued_frames"] == after["pending_timestamp_frames"] == 0
        for name in QUERY_COUNTERS:
            assert after[name] - before[name] == (submissions if queries else 0)
        if queries:
            assert after["render_passes"] - before["render_passes"] == sum(len(row["passes"]) for row in harness.raw_gpu)
        assert harness.native.benchmark_completions(harness.canvas_id) == []
        assert harness.native.benchmark_gpu_timings(harness.canvas_id) == []
        harness.evidence.value.update(samples=copy.deepcopy(samples), boundary=copy.deepcopy(harness.collector.boundary),
                                     transient_uniform_upload_bytes=after["uniform_upload_bytes"] - before["uniform_upload_bytes"],
                                     uniform_inclusive_buffer_upload_cpu_ns=after["buffer_upload_cpu_ns"] - before["buffer_upload_cpu_ns"],
                                     actual_deferred_frames=after["deferred_frames"] - before["deferred_frames"],
                                     deferred_path_qualified=after["deferred_frames"] > before["deferred_frames"])
        harness.evidence.save()
        # Explicit waiting quality capture follows all resident assertions.
        raw_bgra = np.asarray(harness.native.read_presented(harness.canvas_id, 0, 0, *SIZE)).copy()
        np.save(harness.evidence.output / "final-presented-bgra.npy", raw_bgra, allow_pickle=False)
        pixels = presented_bgra_to_rgba(raw_bgra)
        np.save(harness.evidence.output / "final-presented.npy", pixels, allow_pickle=False)
        np.testing.assert_array_equal(pixels, expected_pixels(FRAME_IDS[-1]))
        harness.evidence.value["outcome"] = "passed"
    except BaseException:
        harness.evidence.value.update(outcome="failed", assertion_traceback=traceback.format_exc())
        raise
    finally:
        harness.evidence.save()


def _terminal(harness, frame_id):
    deadline = time.monotonic() + 10
    while not any(row["frame_id"] == frame_id for row in harness.raw_receipts) or not any(row["frame_id"] == frame_id for row in harness.raw_gpu):
        harness.poll_native("terminal-drain")
        assert time.monotonic() < deadline, "typed terminal owner/query result not retained"
        time.sleep(.001)
    receipts = [row for row in harness.raw_receipts if row["frame_id"] == frame_id]
    maps = [row for row in harness.raw_gpu if row["frame_id"] == frame_id]
    assert len(receipts) == len(maps) == 1
    row, timing = receipts[0], maps[0]
    assert row["status"] != "success" and row["error"]
    assert row["ownership_closed"] is True and row["ownership_retired"] is True
    assert timing["status"] != "success" and timing["error"] and timing["passes"] == []
    # A failed row is deliberately rejected by both release collectors.
    with pytest.raises(RuntimeError, match="failed or unpresented"):
        harness.completions.collect([row], PHASES[frame_id])
    harness.collector.gpu_frames.collect([timing])
    from tools.benchmark_frames import InstrumentationUnavailable
    with pytest.raises(InstrumentationUnavailable):
        harness.collector.gpu_frames.join([copy.deepcopy(row)])
    return row, timing


@pytest.mark.gpu
@pytest.mark.parametrize("action,status", [("error", "failed"), ("loss", "device_lost"), ("detach", "failed")])
def test_real_paint_terminal_paths_never_admit_intermediate_present_as_success(paint_factory, action, status):
    harness = paint_factory(queries=True)
    try:
        before = _snapshot(harness, "before-terminal-request")
        harness.issue(0, "warmup", action=action)
        if action == "detach":
            harness.dispatch(0)
        else:
            match = "glLineWidth" if action == "error" else "intentional native-paint device loss"
            with pytest.raises(RuntimeError, match=match):
                harness.dispatch(0)
        row, timing = _terminal(harness, 0)
        assert row["status"] == status and row["frame_scope"] == "qt_paint" and row["paint_token"] > 0
        assert timing["frame_scope"] == "qt_paint" and timing["paint_token"] == row["paint_token"]
        if action == "error":
            assert row["submission_count"] == row["present_count"] == 0
            assert row["last_present_submission_index"] == UNSUBMITTED_INDEX
            assert row["counters_captured"] is False and row["counter_capture"] == "unavailable_unsubmitted"
        else:
            # The first genuine autoswap occurred; it cannot qualify the failed final paint.
            assert row["presented"] is True and row["present_count"] == 1
            assert row["last_present_submission_index"] == 0
            assert row["submission_count"] == (2 if action == "detach" else 1)
            if action == "detach":
                assert row["counters_captured"] is True and row["counter_capture"] == "submission"
                assert row["counters"]["dawn_queue_submits"] - before["dawn_queue_submits"] == 2
                assert not harness.native.benchmark_surface_info(harness.canvas_id)["attached"]
        after = _snapshot(harness, "after-terminal-retirement")
        assert after["completion_waits"] == before["completion_waits"]
        assert after["finish_calls"] == before["finish_calls"]
        harness.evidence.value.update(outcome="passed-terminal-rejection", terminal_receipt=row, terminal_gpu_map=timing)
    except BaseException:
        harness.evidence.value.update(outcome="failed", assertion_traceback=traceback.format_exc())
        raise
    finally:
        harness.evidence.save()


@pytest.mark.gpu
def test_matching_unpainted_request_cancel_is_retained_without_submission(paint_factory):
    harness = paint_factory(queries=True)
    try:
        before = _snapshot(harness, "before-unpainted-cancel")
        harness.evidence.value["issued"].append({"frame_id": 0, "phase": "warmup", "action": "cancel-without-update"})
        harness.evidence.save()
        harness.collector.begin(0)
        harness.completions.begin(0, "warmup")
        harness.native.benchmark_cancel_frame(harness.canvas_id, 0, "public test-owned unpainted request cancellation")
        row, timing = _terminal(harness, 0)
        assert row["status"] == "cancelled" and timing["status"] == "cancelled"
        assert row["paint_token"] == 0 and row["frame_scope"] == "native_present"
        assert row["submission_count"] == row["present_count"] == 0 and row["presented"] is False
        assert row["last_present_submission_index"] == UNSUBMITTED_INDEX
        assert row["counters_captured"] is False and row["counter_capture"] == "unavailable_unsubmitted"
        after = _snapshot(harness, "after-unpainted-cancel")
        assert all(after[key] == before[key] for key in RESIDENT + QUERY_COUNTERS)
        assert after["dawn_queue_submits"] == before["dawn_queue_submits"]
        assert after["application_presents"] == before["application_presents"]
        harness.evidence.value.update(outcome="passed-terminal-rejection", terminal_receipt=row, terminal_gpu_map=timing)
    except BaseException:
        harness.evidence.value.update(outcome="failed", assertion_traceback=traceback.format_exc())
        raise
    finally:
        harness.evidence.save()
