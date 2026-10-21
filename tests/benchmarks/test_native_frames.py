"""Native frame telemetry records final GPU work without a completion wait."""

import time

import numpy as np
import pytest

from vispy import _dawn, app, gloo
from tools.fixture_gloo import FULL, VERT, FRAG, TEX_VERT, TEX_FRAG, UV

COMPILER_TIMINGS = ("shader_normalize_ns", "shader_parse_ns", "shader_link_ns",
                    "shader_spirv_ns", "shader_reflect_ns", "shader_cpu_build_ns")
COMPILER_CALLS = ("shader_normalizations", "shader_parse_calls", "shader_link_calls", "shader_spirv_stages")

pytestmark = pytest.mark.gpu


def _records(canvas_id, count):
    records = []
    deadline = time.monotonic() + 5
    while len(records) < count:
        records.extend(_dawn.benchmark_completions(canvas_id))
        assert time.monotonic() < deadline, "final frame completion timed out"
        if len(records) < count:
            time.sleep(.001)
    return records


@pytest.mark.parametrize("vsync", [False, True])
def test_actual_qt_presentations_have_owned_nonblocking_frame_timestamps(vsync):
    canvas = app.Canvas(app="pyqt6", size=(32, 24), show=True, vsync=vsync)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.app.process_events()
        canvas.set_current()
        gloo.set_viewport(0, 0, 32, 24)
        program = gloo.Program(VERT, FRAG)
        program["a_position"] = gloo.VertexBuffer(FULL)
        program["u_color"] = (1, 0, 0, 1)
        program.draw("triangles")
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        surface = _dawn.benchmark_surface_info(canvas_id)
        assert surface["attached"] and surface["vsync_requested"] == vsync
        assert surface["present_mode"] in ("immediate", "mailbox", "fifo")
        assert surface["pacing_disabled"] == (not vsync and surface["present_mode"] == "immediate")
        if vsync:
            assert surface["present_mode"] == "fifo"
        before = _dawn.probe()
        for frame_id in range(12):
            deadline = time.monotonic() + 5
            while not _dawn.frame_ready(canvas_id):
                assert time.monotonic() < deadline
                time.sleep(.001)
            _dawn.benchmark_begin_frame(canvas_id, frame_id)
            program["u_color"] = (frame_id / 11, 0, 0, 1)
            program.draw("triangles")
            _dawn.present(canvas_id)
        records = _records(canvas_id, 12)
        after = _dawn.probe()
        assert [record["frame_id"] for record in records] == list(range(12))
        assert all(record["presented"] and record["status"] == "success" for record in records)
        assert all(record["counter_capture"] == "submission" for record in records)
        assert all(0 < record["submit_latency_ns"] <= record["completion_latency_ns"] for record in records)
        assert all(record["completion_timestamp_ns"] > record["completion_latency_ns"] for record in records)
        assert after["completion_waits"] == before["completion_waits"]
        assert after["finish_calls"] == before["finish_calls"]
        assert after["application_presents"] - before["application_presents"] == 12
        assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == 12
        assert after["texture_uploads"] == before["texture_uploads"]
        assert after["buffer_uploads"] == before["buffer_uploads"]
        assert after["pipeline_misses"] == before["pipeline_misses"]
        assert after["native_interpret_ns"] > before["native_interpret_ns"]
        assert after["native_submit_ns"] > before["native_submit_ns"]
        assert after["binding_decode_ns"] > before["binding_decode_ns"]
        assert after["native_commands"] > before["native_commands"]
        assert after["command_encoders"] - before["command_encoders"] == 12
        assert after["render_passes"] - before["render_passes"] == 36
        assert after["native_draw_calls"] - before["native_draw_calls"] == 36
        assert after["draw_calls"] - before["draw_calls"] == 12
        assert all(after[key] == before[key] for key in COMPILER_TIMINGS + COMPILER_CALLS)
        assert after["texture_conversion_ns"] == before["texture_conversion_ns"]
        assert after["texture_upload_cpu_ns"] == before["texture_upload_cpu_ns"]
        assert all(after[key] == before[key] for key in
                   ("timestamp_query_sets", "timestamp_resolves", "timestamp_readbacks"))
        assert _dawn.benchmark_gpu_timings(canvas_id) == []
        assert after["descriptor_samples"] - before["descriptor_samples"] >= 13
        assert 1 <= after["peak_pending_tickets"] <= after["frame_slots"]
        assert after["sampled_peak_live_texture_bytes"] >= after["live_texture_bytes"] > 0
        assert after["peak_shader_cache_bytes"] >= after["shader_cache_bytes"]
        # Later retirement/probe calls must not replace a frame's counters.
        assert [record["counters"]["dawn_queue_submits"] for record in records] == list(
            range(before["dawn_queue_submits"] + 1, before["dawn_queue_submits"] + 13))
        assert [record["counters"]["draw_calls"] for record in records] == list(
            range(before["draw_calls"] + 1, before["draw_calls"] + 13))
        assert _dawn.benchmark_completions(canvas_id) == []
        print("native frame telemetry", surface, "frames", len(records), "GPU waits", 0)
    finally:
        canvas.close()


def _gpu_records(canvas_id, count, records=None):
    records = [] if records is None else records
    deadline = time.monotonic() + 5
    while len(records) < count:
        records.extend(_dawn.benchmark_gpu_timings(canvas_id))
        assert time.monotonic() < deadline, "asynchronous GPU timing map timed out"
        if len(records) < count:
            time.sleep(.001)
    return records


def _check_gpu_record(record, configuration, submission_count, pass_count):
    assert record["submission_count"] == submission_count
    assert record["device_generation"] == configuration["device_generation"]
    assert record["quantization_ns"] == configuration["quantization_ns"]
    if not configuration["supported"]:
        assert record["status"] == "unsupported_feature"
        assert record["error"] and record["passes"] == []
        assert record["render_span_ns"] == record["pass_sum_ns"] == 0
        return
    assert record["status"] == "success" and not record["error"], record
    assert len(record["passes"]) == pass_count
    quantum = record["quantization_ns"]
    for row in record["passes"]:
        assert row["end_ns"] >= row["begin_ns"]
        assert row["elapsed_ns"] == row["end_ns"] - row["begin_ns"]
        if quantum:
            assert row["begin_ns"] % quantum == row["end_ns"] % quantum == 0
    assert record["render_span_ns"] == max(row["end_ns"] for row in record["passes"]) - min(
        row["begin_ns"] for row in record["passes"])
    assert record["pass_sum_ns"] == sum(row["elapsed_ns"] for row in record["passes"])


def test_opt_in_gpu_queries_cover_twelve_actual_qt_render_and_conversion_frames():
    canvas = app.Canvas(app="pyqt6", size=(32, 24), show=True, vsync=False)
    canvas_id = canvas._backend._dawn_canvas_id
    saved = None
    try:
        canvas.app.process_events()
        canvas.set_current()
        gloo.set_viewport(0, 0, 32, 24)
        program = gloo.Program(VERT, FRAG)
        program["a_position"] = gloo.VertexBuffer(FULL)
        program["u_color"] = (1, 0, 0, 1)
        program.draw("triangles")
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        configuration = _dawn.benchmark_configure_gpu_timing(canvas_id)
        assert configuration["enabled"] and configuration["max_queries_per_frame"] == 4096
        assert configuration["max_submissions_per_frame"] == 64
        before = _dawn.probe()
        gpu_records = []
        for frame_id in range(12):
            deadline = time.monotonic() + 5
            gpu_records.extend(_dawn.benchmark_gpu_timings(canvas_id))
            while not _dawn.frame_ready(canvas_id):
                gpu_records.extend(_dawn.benchmark_gpu_timings(canvas_id))
                assert time.monotonic() < deadline
                time.sleep(.001)
            _dawn.benchmark_begin_frame(canvas_id, frame_id)
            program["u_color"] = (frame_id / 11, 0, 0, 1)
            program.draw("triangles")
            _dawn.present(canvas_id)
        completions = _records(canvas_id, 12)
        gpu_records = _gpu_records(canvas_id, 12, gpu_records)
        after = _dawn.probe()
        assert [row["frame_id"] for row in gpu_records] == list(range(12))
        assert [row["frame_id"] for row in completions] == list(range(12))
        assert all(row["status"] == "success" and row["presented"] for row in completions)
        for row in gpu_records:
            _check_gpu_record(row, configuration, submission_count=1, pass_count=3)
            if configuration["supported"]:
                assert [item["kind"] for item in row["passes"]] == [
                    "scene", "present_capture", "surface_conversion"]
        assert after["completion_waits"] == before["completion_waits"]
        assert after["finish_calls"] == before["finish_calls"]
        assert after["pending_timestamp_frames"] == 0
        assert after["peak_pending_timestamp_frames"] <= after["frame_slots"]
        expected = 12 if configuration["supported"] else 0
        assert after["timestamp_query_sets"] - before["timestamp_query_sets"] == expected
        assert after["timestamp_resolves"] - before["timestamp_resolves"] == expected
        assert after["timestamp_readbacks"] - before["timestamp_readbacks"] == expected
        if configuration["supported"]:
            assert sum(len(row["passes"]) for row in gpu_records) == after["render_passes"] - before["render_passes"]
        saved = [dict(row, passes=[dict(item) for item in row["passes"]]) for row in gpu_records]
        _dawn.benchmark_configure_gpu_timing(canvas_id, False)
        assert _dawn.benchmark_gpu_timings(canvas_id) == []
        assert saved == gpu_records
        print("actual asynchronous GPU queries", configuration, "records", len(gpu_records))
    finally:
        canvas.close()
    # Returned Python records own their arrays after native canvas/query teardown.
    assert saved is not None and len(saved) == 12


def test_gpu_frame_aggregates_real_intermediate_submission_without_extra_completion_or_wait():
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.clear(color=(0, 0, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        configuration = _dawn.benchmark_configure_gpu_timing(canvas_id)
        before = _dawn.probe()
        _dawn.benchmark_begin_frame(canvas_id, 0)
        gloo.clear(color=(1, 0, 0, 1))
        canvas.context.flush_commands()
        _dawn.benchmark_submit_intermediate(canvas_id)
        assert _dawn.benchmark_completions(canvas_id) == []
        with pytest.raises(RuntimeError, match="previous frame"):
            _dawn.benchmark_begin_frame(canvas_id, 1)
        gloo.clear(color=(0, 1, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        completions = _records(canvas_id, 1)
        record = _gpu_records(canvas_id, 1)[0]
        after = _dawn.probe()
        _check_gpu_record(record, configuration, submission_count=2, pass_count=3)
        if configuration["supported"]:
            assert [row["submission_index"] for row in record["passes"]] == [0, 1, 1]
            assert [row["kind"] for row in record["passes"]] == ["clear", "clear", "present_capture"]
        assert completions[0]["status"] == "success" and completions[0]["counter_capture"] == "submission"
        assert completions[0]["counters"]["dawn_queue_submits"] == before["dawn_queue_submits"] + 2
        assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == 2
        assert after["completion_waits"] == before["completion_waits"]
        assert after["finish_calls"] == before["finish_calls"]
        assert _dawn.benchmark_completions(canvas_id) == []
    finally:
        canvas.close()


@pytest.mark.parametrize("submit", [False, True])
def test_gpu_query_loss_is_owned_and_recovery_uses_a_new_generation(submit):
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.clear(color=(0, 0, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        configuration = _dawn.benchmark_configure_gpu_timing(canvas_id)
        _dawn.benchmark_begin_frame(canvas_id, 0)
        gloo.clear(color=(1, 0, 0, 1))
        canvas.context.flush_commands()
        if submit:
            _dawn.benchmark_submit_intermediate(canvas_id)
        _dawn.lose_device()
        lost = _gpu_records(canvas_id, 1)[0]
        assert lost["status"] == ("device_lost" if configuration["supported"] else "unsupported_feature")
        assert lost["device_generation"] == configuration["device_generation"]
        assert lost["submission_count"] == int(submit)
        assert lost["error"] and lost["passes"] == []
        assert lost["render_span_ns"] == lost["pass_sum_ns"] == 0
        completion = _records(canvas_id, 1)[0]
        assert completion["status"] == "device_lost"
        assert completion["counter_capture"] == ("submission" if submit else "unavailable_unsubmitted")
        recovered = _dawn.benchmark_configure_gpu_timing(canvas_id)
        assert recovered["device_generation"] > configuration["device_generation"]
        _dawn.benchmark_begin_frame(canvas_id, 1)
        gloo.clear(color=(0, 1, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        _records(canvas_id, 1)
        _check_gpu_record(_gpu_records(canvas_id, 1)[0], recovered, submission_count=1, pass_count=2)
        assert _dawn.probe()["pending_timestamp_frames"] == 0
    finally:
        canvas.close()


def test_gpu_queries_include_offscreen_and_final_sampler_render_passes():
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        color = gloo.Texture2D(np.zeros((8, 8, 4), np.uint8), interpolation="nearest")
        framebuffer = gloo.FrameBuffer(color=color)
        offscreen = gloo.Program(VERT, FRAG)
        offscreen["a_position"] = gloo.VertexBuffer(FULL)
        offscreen["u_color"] = (0, 1, 0, 1)
        onscreen = gloo.Program(TEX_VERT, TEX_FRAG)
        onscreen["a_position"] = gloo.VertexBuffer(FULL)
        onscreen["a_texcoord"] = gloo.VertexBuffer(UV)
        onscreen["u_texture"] = color

        def draw():
            with framebuffer:
                gloo.set_viewport(0, 0, 8, 8)
                offscreen.draw("triangles")
            gloo.set_viewport(0, 0, 8, 8)
            onscreen.draw("triangles")

        draw()
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        configuration = _dawn.benchmark_configure_gpu_timing(canvas_id)
        before = _dawn.probe()
        _dawn.benchmark_begin_frame(canvas_id, 0)
        draw()
        _dawn.present(canvas_id)
        completion = _records(canvas_id, 1)[0]
        record = _gpu_records(canvas_id, 1)[0]
        after = _dawn.probe()
        _check_gpu_record(record, configuration, submission_count=1, pass_count=3)
        if configuration["supported"]:
            assert [row["kind"] for row in record["passes"]] == ["framebuffer", "scene", "present_capture"]
        assert completion["status"] == "success"
        assert after["render_passes"] - before["render_passes"] == 3
        assert after["completion_waits"] == before["completion_waits"]
        # Quality capture follows both completion and query collection, outside
        # the sampled frame and its timestamps.
        assert np.all(gloo.read_pixels((0, 0, 8, 8)) == [0, 255, 0, 255])
    finally:
        canvas.close()


def test_gpu_frame_counts_explicit_capture_copy_submissions_without_fabricating_passes():
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        gloo.clear(color=(0, 0, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        configuration = _dawn.benchmark_configure_gpu_timing(canvas_id)
        before = _dawn.probe()
        _dawn.benchmark_begin_frame(canvas_id, 0)
        gloo.clear(color=(1, 0, 0, 1))
        canvas.context.flush_commands()
        # An explicit public capture intentionally waits; this regression
        # tests its real intermediate render/copy submissions, not the
        # no-wait interactive benchmark route.
        assert np.all(gloo.read_pixels((0, 0, 8, 8)) == [255, 0, 0, 255])
        _dawn.present(canvas_id)
        completion = _records(canvas_id, 1)[0]
        record = _gpu_records(canvas_id, 1)[0]
        _check_gpu_record(record, configuration, submission_count=2, pass_count=2)
        assert completion["counter_capture"] == "submission" and completion["status"] == "success"
        assert completion["counters"]["dawn_queue_submits"] == before["dawn_queue_submits"] + 2
        if configuration["supported"]:
            assert [row["submission_index"] for row in record["passes"]] == [0, 0]
            assert [row["kind"] for row in record["passes"]] == ["clear", "present_capture"]
    finally:
        canvas.close()


def test_actual_vulkan_allocation_handle_bytes_and_frees_survive_device_loss():
    # Start a fresh device to make these actual allocation deltas independent
    # of slabs retained by earlier tests. Pinned Dawn dedicates allocations
    # exceeding its default 4MiB suballocation threshold.
    _dawn.lose_device()
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        before = _dawn.probe()
        if _dawn.device_info()["backend"].lower() != "vulkan":
            assert not before["vk_memory_available"]
            return
        assert before["vk_memory_available"] and before["vk_memory_complete"], before
        canvas.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        program = gloo.Program(VERT, FRAG)
        vertices = np.tile(FULL, (300_000, 1))  # 14.4MB dedicated vertex allocation.
        program["a_position"] = gloo.VertexBuffer(vertices)
        program["u_color"] = (0, 1, 0, 1)
        program.draw("triangles", gloo.IndexBuffer(np.arange(len(FULL), dtype=np.uint16)))
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)
        live = _dawn.probe()
        assert live["vk_memory_allocation_count"] > before["vk_memory_allocation_count"]
        assert live["vk_memory_allocated_bytes"] - before["vk_memory_allocated_bytes"] >= vertices.nbytes
        assert live["vk_memory_live_bytes"] >= vertices.nbytes
        assert live["vk_memory_peak_live_bytes"] >= live["vk_memory_live_bytes"]
        assert live["vk_memory_peak_live_allocations"] >= live["vk_memory_live_allocations"]
        assert live["vk_memory_allocate_failures"] == before["vk_memory_allocate_failures"]
        assert live["vk_memory_tracking_errors"] == live["vk_memory_retired_allocations"] == 0
        _dawn.lose_device()
        released = _dawn.probe()
        assert released["vk_memory_free_count"] > live["vk_memory_free_count"]
        assert released["vk_memory_freed_bytes"] - live["vk_memory_freed_bytes"] >= vertices.nbytes
        assert released["vk_memory_live_bytes"] < live["vk_memory_live_bytes"]
        assert released["vk_memory_peak_live_bytes"] >= live["vk_memory_peak_live_bytes"]
        assert released["vk_memory_tracking_errors"] == released["vk_memory_retired_allocations"] == 0
        assert not released["vk_memory_available"] and not released["vk_memory_complete"]
        _dawn.benchmark_configure_gpu_timing(canvas_id, False)
        assert _dawn.device_info()["ok"]
        recovered = _dawn.probe()
        assert recovered["vk_memory_available"] and recovered["vk_memory_complete"]
        assert recovered["vk_memory_allocation_count"] >= released["vk_memory_allocation_count"]
        print("actual Vulkan handle allocation/free bytes", before, live, released, recovered)
    finally:
        canvas.close()


def test_headless_completion_does_not_claim_actual_surface_presentation():
    canvas = app.Canvas(app="dawn_headless", size=(4, 4), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        _dawn.benchmark_begin_frame(canvas_id, 0)
        with pytest.raises(RuntimeError, match="previous frame"):
            _dawn.benchmark_begin_frame(canvas_id, 1)
        gloo.clear(color=(1, 0, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        submitted = _dawn.probe()
        # A later batch does not belong to the already submitted frame, even
        # if its completion is still waiting to be consumed.
        _dawn.execute(canvas_id, [("FUNC", "glViewport", 0, 0, 4, 4)], [])
        future = _dawn.probe()
        records = _records(canvas_id, 1)
        assert records[0]["status"] == "success" and not records[0]["presented"]
        assert records[0]["counter_capture"] == "submission"
        assert records[0]["counters"]["native_commands"] == submitted["native_commands"]
        assert future["native_commands"] == submitted["native_commands"] + 1
        assert not _dawn.benchmark_surface_info(canvas_id)["pacing_disabled"]
        with pytest.raises(RuntimeError, match="IDs must increase"):
            _dawn.benchmark_begin_frame(canvas_id, 0)
        _dawn.benchmark_begin_frame(canvas_id, 1)
        gloo.clear(color=(0, 1, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        assert _records(canvas_id, 1)[0]["frame_id"] == 1
    finally:
        canvas.close()


def test_cold_shader_stage_time_is_not_replayed_by_cache_or_device_recovery():
    # A source-provenance comment makes this an actual miss in any suite order.
    vertex = f"// telemetry identity {time.perf_counter_ns()}\n" + VERT
    before = _dawn.probe()
    first = _dawn.compile_variant(vertex, FRAG)
    assert first["ok"] and not first["cache_hit"], first["error"]
    cold = _dawn.probe()
    assert all(cold[key] > before[key] for key in COMPILER_TIMINGS)
    assert cold["shader_normalizations"] - before["shader_normalizations"] == 1
    assert cold["shader_parse_calls"] - before["shader_parse_calls"] == 2
    assert cold["shader_link_calls"] - before["shader_link_calls"] == 1
    assert cold["shader_spirv_stages"] - before["shader_spirv_stages"] == 2
    assert cold["shader_module_creations"] - before["shader_module_creations"] == 2
    assert cold["render_pipeline_creations"] - before["render_pipeline_creations"] == 1
    assert _dawn.compile_variant(vertex, FRAG)["cache_hit"]
    warm = _dawn.probe()
    assert all(warm[key] == cold[key] for key in COMPILER_TIMINGS + COMPILER_CALLS)
    assert warm["shader_cache_lookup_ns"] > cold["shader_cache_lookup_ns"]
    assert warm["device_cache_lookup_ns"] > cold["device_cache_lookup_ns"]
    assert warm["shader_module_creation_ns"] == cold["shader_module_creation_ns"]
    device_before_loss = _dawn.device_info()
    assert device_before_loss["ok"], device_before_loss["error"]
    _dawn.lose_device()
    recovered_device = _dawn.device_info()
    recovered_probe = _dawn.probe()
    assert recovered_device["ok"], recovered_device["error"]
    assert int(recovered_device["loss_count"]) == int(device_before_loss["loss_count"]) + 1
    assert recovered_probe["device_generation"] > warm["device_generation"]
    repeated_device = _dawn.device_info()
    assert repeated_device["ok"], repeated_device["error"]
    assert int(repeated_device["loss_count"]) == int(recovered_device["loss_count"])
    assert _dawn.probe()["device_generation"] == recovered_probe["device_generation"]
    recovered = _dawn.compile_variant(vertex, FRAG)
    assert recovered["ok"], recovered["error"]
    after = _dawn.probe()
    assert all(after[key] == cold[key] for key in COMPILER_TIMINGS + COMPILER_CALLS)
    assert after["shader_module_creations"] - cold["shader_module_creations"] == 2
    assert after["render_pipeline_creations"] - cold["render_pipeline_creations"] == 1


def test_texture_conversion_and_upload_time_track_dirty_data_and_preserve_warm_reuse():
    canvas = app.Canvas(app="dawn_headless", size=(3, 2), show=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 3, 2)
        program = gloo.Program(TEX_VERT, TEX_FRAG)
        program["a_position"] = gloo.VertexBuffer(FULL)
        program["a_texcoord"] = gloo.VertexBuffer(UV)
        texture = gloo.Texture2D(np.full((2, 3, 4), [255, 0, 0, 255], np.uint8),
                                 interpolation="nearest", wrapping="clamp_to_edge")
        program["u_texture"] = texture
        before = _dawn.probe()
        program.draw("triangles")
        assert np.all(gloo.read_pixels((0, 0, 3, 2)) == [255, 0, 0, 255])
        cold = _dawn.probe()
        assert cold["texture_conversion_ns"] > before["texture_conversion_ns"]
        assert cold["texture_upload_cpu_ns"] > before["texture_upload_cpu_ns"]
        assert cold["buffer_upload_cpu_ns"] > before["buffer_upload_cpu_ns"]
        assert cold["binding_decode_bytes"] > before["binding_decode_bytes"]
        assert cold["texture_upload_bytes"] - before["texture_upload_bytes"] >= 512
        _dawn.benchmark_begin_frame(canvas_id, 0)
        program.draw("triangles")
        canvas.context.flush_commands()
        _dawn.present(canvas_id)
        _records(canvas_id, 1)
        warm = _dawn.probe()
        for key in ("texture_conversion_ns", "texture_upload_cpu_ns", "texture_upload_bytes", "texture_uploads",
                    "buffer_upload_cpu_ns", "geometry_upload_bytes", "buffer_uploads"):
            assert warm[key] == cold[key], key
        # Row padding and native ordered upload of a sparse source patch are
        # measured; public texture contents remain unchanged outside it.
        texture[0:1, 1:2] = np.array([[[0, 0, 255, 255]]], np.uint8)
        program.draw("triangles")
        patched = gloo.read_pixels((0, 0, 3, 2))
        assert np.count_nonzero(np.all(patched == [0, 0, 255, 255], axis=2)) == 1
        assert np.count_nonzero(np.all(patched == [255, 0, 0, 255], axis=2)) == 5
        after = _dawn.probe()
        assert after["texture_conversion_ns"] > warm["texture_conversion_ns"]
        assert after["texture_upload_cpu_ns"] > warm["texture_upload_cpu_ns"]
        assert after["texture_upload_bytes"] - warm["texture_upload_bytes"] == 256
    finally:
        canvas.close()


def test_shown_scene_python_hooks_attribute_twelve_actual_presentations():
    from vispy import scene
    from vispy.gloo import dawn_parser
    from tools.benchmark_frames import PythonFrameTelemetry

    canvas = scene.SceneCanvas(app="pyqt6", size=(32, 24), show=True, vsync=False)
    canvas_id = canvas._backend._dawn_canvas_id
    telemetry = None
    try:
        view = canvas.central_widget.add_view()
        image = scene.visuals.Image(np.ones((2, 3), np.float32), cmap="grays", clim=(0, 1),
                                    interpolation="nearest", parent=view.scene)
        view.camera = scene.PanZoomCamera(aspect=None)
        view.camera.set_range(x=(0, 3), y=(0, 2), margin=0)
        canvas.app.process_events()
        _dawn.finish(canvas_id)
        telemetry = PythonFrameTelemetry(canvas, pack_module=dawn_parser)
        before = _dawn.probe()
        records = []
        for frame_id in range(12):
            deadline = time.monotonic() + 5
            while not _dawn.frame_ready(canvas_id):
                canvas.app.process_events()
                assert time.monotonic() < deadline
            _dawn.benchmark_begin_frame(canvas_id, frame_id)
            telemetry.begin(frame_id)
            telemetry.update(lambda index: setattr(image, "opacity", (index + 1) / 12), frame_id)
            canvas.update()
            while len(records) <= frame_id:
                canvas.app.process_events()
                records.extend(_dawn.benchmark_completions(canvas_id))
                assert time.monotonic() < deadline
        after = _dawn.probe()
        assert [record["frame_id"] for record in records] == list(range(12))
        assert all(record["status"] == "success" and record["presented"] for record in records)
        for frame_id in range(12):
            sample = telemetry.frames[frame_id]
            assert sample["python_update_calls"] == sample["python_draw_calls"] == 1
            assert sample["python_paint_calls"] == 1
            assert sample["python_paint_tail_glir_parse_calls"] > 0
            assert sample["python_paint_tail_glir_parse_ns"] > 0
            assert sample["python_glir_parse_calls"] > 0 and sample["python_glir_pack_calls"] > 0
            assert sample["python_update_ns"] > 0 and sample["python_glir_pack_ns"] > 0
            assert sample["python_draw_inclusive_ns"] >= sample["python_draw_exclusive_ns"] >= 0
        assert telemetry.current is None
        assert after["finish_calls"] == before["finish_calls"]
        assert after["completion_waits"] == before["completion_waits"]
        assert after["texture_uploads"] == before["texture_uploads"]
        assert after["buffer_uploads"] == before["buffer_uploads"]
        assert all(after[key] == before[key] for key in COMPILER_TIMINGS + COMPILER_CALLS)
        info = _dawn.benchmark_telemetry_info()
        assert info["counter_capture"] == "submission" and info["timings_enabled"] == "always"
        assert info["gpu_timestamps_available"] == _dawn.device_info()["timestamp_query"]
        assert info["gpu_timing_collection"] == "per-canvas opt-in, off by default"
        assert not info["scanout_timestamps_available"]
        assert "sampled_peak_live_texture_bytes" in info["high_water_marks"]
        print("shown scene hook attribution", len(records), "frames", telemetry.snapshot())
    finally:
        if telemetry is not None:
            telemetry.close()
        canvas.close()
