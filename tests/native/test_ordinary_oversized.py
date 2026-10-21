"""Future matching-epoch gate for actual >64MiB current payload ownership."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import numpy as np
import pytest

from tools.fixture_ordinary_oversized import (
    CASES, CORNERS, FRAGMENT, HISTORY_BYTES, HISTORY_ENTRIES, SAMPLE_LIMITS,
    SIZE, SPARSE_BASE, configure, contract, draw, expected_image, make_program,
    plan, revise, tail_indices, vertex_source,
)

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = ROOT / "build/evidence/ordinary-oversized-authoring-2/authoring.json"
RESIDENT = (
    "vertex_input_conversion_builds", "vertex_input_conversion_bytes",
    "point_conversion_builds", "point_conversion_bytes", "buffer_uploads",
    "geometry_upload_bytes", "texture_uploads", "texture_upload_bytes",
    "buffer_allocations", "texture_allocations", "pipeline_misses",
    "portable_shader_misses", "uniform_upload_bytes", "completion_waits", "finish_calls",
)


def _assert_resident(before, after, phase):
    for name in RESIDENT:
        assert after[name] == before[name], (phase, name, before[name], after[name])


@pytest.mark.parametrize("name", CASES)
def test_cpu_actual_payload_alone_exceeds_budget_with_legal_grants(name):
    p = plan(name, SAMPLE_LIMITS)
    assert p.target_bytes > HISTORY_BYTES
    assert p.target_bytes <= HISTORY_BYTES + max(24, p.stride * 6)
    assert p.target_bytes < SAMPLE_LIMITS["max_buffer_size"]
    assert p.lanes > SAMPLE_LIMITS["max_vertex_buffers"]
    assert p.lanes <= SAMPLE_LIMITS["max_vertex_attributes"]
    assert p.stride <= SAMPLE_LIMITS["max_vertex_buffer_array_stride"]
    assert p.count % 6 == 0
    assert p.instances % 4 == 0 if name == CASES[2] else p.instances == 1
    assert p.geometry_upload_bytes > p.target_bytes
    assert p.geometry_buffers in (2, 3)


@pytest.mark.parametrize("name", CASES)
def test_cpu_limits_are_checked_before_constructing_payloads(name):
    p = plan(name, SAMPLE_LIMITS)
    for key, value in (("max_buffer_size", p.target_bytes - 1),
                       ("max_vertex_buffer_array_stride", p.stride - 1),
                       ("max_storage_buffers_per_shader_stage", 0),
                       ("max_storage_buffer_binding_size", 3),
                       ("max_vertex_attributes", p.lanes - 1)):
        with pytest.raises(ValueError):
            plan(name, {**SAMPLE_LIMITS, key: value})
    with pytest.raises(ValueError, match="draw-count"):
        plan(name, {**SAMPLE_LIMITS, "max_buffer_size": 2 ** 63}, budget=2 ** 40)


def test_cpu_sparse_original_order_first_and_divisor_math_have_pixel_witnesses():
    for name in CASES:
        p = plan(name, SAMPLE_LIMITS)
        image, changed = expected_image(p), expected_image(p, revised=True)
        visible = np.any(image[..., :3], axis=2)
        assert np.count_nonzero(visible) == 48 * (4 if name == CASES[2] else 1)
        assert not np.array_equal(image, changed)
        assert np.all(image[..., 3] == 255) and np.all(changed[..., 3] == 255)
        assert np.count_nonzero(np.any(image != changed, axis=2)) == np.count_nonzero(visible)
        assert set(np.unique(image)).issubset({0, 255})
        source = vertex_source(p)
        assert "uniform" not in source + FRAGMENT and "texture" not in source + FRAGMENT
        for lane in range(p.lanes):
            assert f"a_lane{lane}" in source.split("float energy = ")[1].split(";")[0]
    sparse = plan(CASES[0], SAMPLE_LIMITS)
    assert SPARSE_BASE > 2 ** 24
    assert tail_indices(sparse).tolist() == [SPARSE_BASE + n for n in (3, 4, 5, 0, 1, 2)]
    assert tail_indices(sparse, revised=True).tolist() == [SPARSE_BASE + n for n in (3, 5, 4, 0, 2, 1)]
    affine = plan(CASES[1], SAMPLE_LIMITS)
    assert affine.first == 3 and affine.visible_first % 2 == 1
    instanced = plan(CASES[2], SAMPLE_LIMITS)
    ids = np.arange(instanced.instances - 4, instanced.instances, dtype=np.uint32)
    assert (ids // 2).tolist() == [instanced.source_rows - 2] * 2 + [instanced.source_rows - 1] * 2
    assert (ids % 2).tolist() == [0, 1, 0, 1]
    # Every diagonal center is strictly inside exactly one triangle.
    for dx in range(8):
        for dy in range(6):
            assert 6 * (dx + .5) + 8 * (dy + .5) != 48


@pytest.mark.parametrize("name", CASES)
def test_cpu_public_construction_uses_small_scaled_payloads_without_a_context(name):
    from vispy import gloo
    p = plan(name, SAMPLE_LIMITS, budget=256)
    program, buffers, indices = make_program(gloo, p)
    assert len([name for name in program._code_variables if name.startswith("a_lane")]) == p.lanes
    if indices is not None:
        assert indices.size == p.count and indices.dtype == np.dtype(np.uint32)
    if name == CASES[2]:
        assert all(buffer.size * buffer.divisor == p.instances for buffer in buffers[1:])
    revise(program, buffers, indices, p)
    assert contract()["GPU_used"] is False and contract()["candidate_seen"] is False


@pytest.mark.parametrize("hidden_wait", ("completion_waits", "finish_calls"))
def test_cpu_resident_gate_rejects_hidden_waits_before_separate_readback(hidden_wait):
    before = {name: 10 for name in RESIDENT}
    _assert_resident(before, before.copy(), "resident")
    after = {**before, hidden_wait: 11}
    with pytest.raises(AssertionError, match=hidden_wait):
        _assert_resident(before, after, "resident")


def test_cpu_retirement_observes_actual_work_counters_without_finish():
    class PendingWork:
        calls = 0

        def process_events(self):
            self.calls += 1

        def probe(self):
            return {"pending_tickets": int(self.calls < 2), "queued_frames": 0, "pending_draws": 0}

        def finish(self):
            raise AssertionError("retirement must not wait on the queue")

    native = PendingWork()
    assert _retire(native) == {"pending_tickets": 0, "queued_frames": 0, "pending_draws": 0}
    assert native.calls == 2


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _authoring():
    value = json.loads(AUTHORING.read_text(encoding="utf-8"))
    assert value["GPU_used"] is False and value["candidate_seen"] is False
    assert value["contract"] == contract()
    for name, digest in value["sources_sha256"].items():
        assert _sha(ROOT / name) == digest, name
    return value


def _activation(native):
    # Deliberately fails on old28; a capability dictionary alone cannot qualify
    # an unbuilt source packet. Root supplies a reviewed later activation.
    path = Path(os.environ.get("VISPY_ORDINARY_OVERSIZED_ACTIVATION", ROOT / "build/evidence/native-pass-29/activation.json"))
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value["epoch"]) is int and value["epoch"] >= 29
    base = Path(native.__file__).parent
    for name, digest in value["activated"].items():
        artifact = base / "visuals/text" / name if name.startswith("_sdf_cpu.") else base / name
        assert _sha(artifact) == digest, name
    assert _sha(native.__file__) == value["activated"][Path(native.__file__).name]
    return {"path": str(path), "sha256": _sha(path), "epoch": value["epoch"]}


def _retire(native, *, timeout=120.):
    """Actual asynchronous Ticket retirement, not a timer or encoding proxy."""
    deadline = time.monotonic() + timeout
    while True:
        native.process_events()
        value = native.probe()
        if all(value[name] == 0 for name in ("pending_tickets", "queued_frames", "pending_draws")):
            return value
        if time.monotonic() >= deadline:
            raise AssertionError({"retirement_timeout": value})
        time.sleep(.001)


@pytest.fixture
def oversized_evidence(request):
    from vispy import _dawn, app, gloo
    records, images = {}, {}
    base = Path(os.environ.get("VISPY_ORDINARY_OVERSIZED_EVIDENCE", ROOT / "build/evidence/ordinary-oversized-candidate" / uuid.uuid4().hex))
    output = base / request.node.name
    output.mkdir(parents=True, exist_ok=False)
    canvas = None
    try:
        records["authoring"] = _authoring()
        records["activation"] = _activation(_dawn)
        canvas = app.Canvas(app="dawn_headless", size=SIZE, show=False)
        canvas.set_current()
        device = _dawn.device_info()
        assert device["ok"] and not device["software"]
        assert device["backend"] == "Vulkan" and device["last_vertex_provoking"]
        assert int(gloo.gl.glGetParameter(gloo.gl.GL_MAX_VERTEX_ATTRIBS)) == int(device["max_vertex_attributes"])
        required = ("vertex_input_current_entries", "vertex_input_current_bytes", "vertex_input_cache_entries", "vertex_input_cache_bytes", "live_cpu_buffer_bytes")
        assert all(name in _dawn.probe() for name in required)
        configure(gloo)
        canvas.context.flush_commands()
        canvas.swap_buffers()
        baseline = _retire(_dawn)
        records.update(device=device, baseline=baseline, native_sha256=_sha(_dawn.__file__),
                       gauge_scope="current and historical views overlap; CPU/GPU actual capacities separately deduplicated")
        yield canvas, records, images
    finally:
        try:
            (output / "records.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
            for name, image in images.items():
                np.save(output / f"{name}.npy", image, allow_pickle=False)
        finally:
            if canvas is not None:
                canvas.close()


def _ownership(p, baseline, value):
    assert 1 <= value["vertex_input_current_entries"] - baseline["vertex_input_current_entries"] <= 6
    assert value["vertex_input_current_bytes"] - baseline["vertex_input_current_bytes"] >= p.target_bytes
    assert 0 <= value["vertex_input_cache_entries"] - baseline["vertex_input_cache_entries"] <= HISTORY_ENTRIES
    assert 0 <= value["vertex_input_cache_bytes"] - baseline["vertex_input_cache_bytes"] <= HISTORY_BYTES
    assert value["live_cpu_buffer_bytes"] - baseline["live_cpu_buffer_bytes"] >= p.target_bytes
    assert value["live_buffer_bytes"] - baseline["live_buffer_bytes"] >= p.target_bytes


def _frame(canvas, program, indices, p, phase, records, images, *, revised=False, resident=False):
    from vispy import _dawn, gloo
    before = _retire(_dawn)
    draw(canvas, gloo, program, indices, p)
    prepared = _dawn.probe()
    assert prepared["pending_draws"] == 2  # explicit clear + user DRAW
    canvas.swap_buffers()
    after = _retire(_dawn)
    records[phase] = {"before": before, "prepared": prepared, "after_retirement_before_readback": after,
                      "all_tickets_retired": True, "quality_readbacks_in_counter_interval": 0}
    assert after["draw_calls"] - before["draw_calls"] == 1
    assert after["dawn_queue_submits"] - before["dawn_queue_submits"] == 1
    assert after["retired_tickets"] - before["retired_tickets"] == 1
    if resident:
        _assert_resident(before, after, phase)
    _ownership(p, records["baseline"], after)
    image = gloo.read_pixels(alpha=True)
    expected = expected_image(p, revised=revised)
    images[phase], images[phase + "-expected"] = image.copy(), expected.copy()
    records[phase]["after_separate_quality_readback"] = _retire(_dawn)
    np.testing.assert_array_equal(image, expected)
    return before, after


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_actual_oversized_current_payload_survives_retirement_revision_loss_and_delete(name, oversized_evidence):
    from vispy import _dawn, gloo
    canvas, records, images = oversized_evidence
    p = plan(name, records["device"])
    records["actual_limit_checked_plan"] = asdict(p)
    assert p.target_bytes > HISTORY_BYTES
    program, buffers, indices = make_program(gloo, p)
    before, cold = _frame(canvas, program, indices, p, "cold", records, images)
    assert cold["vertex_input_conversion_builds"] > before["vertex_input_conversion_builds"]
    assert cold["vertex_input_conversion_bytes"] - before["vertex_input_conversion_bytes"] >= p.target_bytes
    for n in range(3):
        _frame(canvas, program, indices, p, f"retired-resident-{n}", records, images, resident=True)
    revise(program, buffers, indices, p)
    before, revised = _frame(canvas, program, indices, p, "revision", records, images, revised=True)
    assert revised["vertex_input_conversion_builds"] > before["vertex_input_conversion_builds"]
    assert revised["vertex_input_conversion_bytes"] - before["vertex_input_conversion_bytes"] >= p.target_bytes
    assert revised["geometry_upload_bytes"] - before["geometry_upload_bytes"] >= p.target_bytes
    _frame(canvas, program, indices, p, "revised-retired-resident", records, images, revised=True, resident=True)
    before_loss = _retire(_dawn)
    _dawn.lose_device()
    _, recovered = _frame(canvas, program, indices, p, "loss-recovery", records, images, revised=True)
    assert recovered["device_generation"] > before_loss["device_generation"]
    for key in ("vertex_input_conversion_builds", "vertex_input_conversion_bytes", "point_conversion_builds", "point_conversion_bytes", "portable_shader_misses"):
        assert recovered[key] == before_loss[key], key
    assert recovered["geometry_upload_bytes"] - before_loss["geometry_upload_bytes"] == p.geometry_upload_bytes
    assert recovered["buffer_uploads"] - before_loss["buffer_uploads"] == p.geometry_buffers
    _frame(canvas, program, indices, p, "recovered-retired-resident", records, images, revised=True, resident=True)
    if name in (CASES[0], CASES[2]):
        before_delete = _retire(_dawn)
        source = indices if name == CASES[0] else buffers[1]
        source.delete()
        canvas.context.flush_commands()
        after_delete = _retire(_dawn)
        records["source-delete"] = {"before": before_delete, "after": after_delete}
        assert before_delete["vertex_input_current_bytes"] - after_delete["vertex_input_current_bytes"] >= p.target_bytes
        assert before_delete["live_cpu_buffer_bytes"] - after_delete["live_cpu_buffer_bytes"] >= p.target_bytes
    before_delete = _retire(_dawn)
    program.delete()
    canvas.context.flush_commands()
    after_delete = _retire(_dawn)
    records["program-delete"] = {"before": before_delete, "after": after_delete}
    assert after_delete["vertex_input_current_entries"] == records["baseline"]["vertex_input_current_entries"]
    assert after_delete["vertex_input_cache_entries"] == records["baseline"]["vertex_input_cache_entries"]
    if name == CASES[1]:
        assert before_delete["vertex_input_current_bytes"] - after_delete["vertex_input_current_bytes"] >= p.target_bytes
        assert before_delete["live_cpu_buffer_bytes"] - after_delete["live_cpu_buffer_bytes"] >= p.target_bytes
