"""Independent ordinary input hardware criteria; authored before candidate."""
import hashlib
import json
import os
from pathlib import Path
import uuid
import numpy as np
import pytest

from tools.fixture_ordinary_input_capacity import (
    ACTIVE_COUNT, CASES, CORNERS, OPEN_GATES, SIZE, SPARSE_BASE, TOPOLOGIES,
    array_record, configure, contract, draw, expected_image, expected_topology,
    index_ids, make_program, set_lane, specification, topology_data, vertex_source,
)

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = ROOT / "build/evidence/ordinary-input-authoring-2/authoring.json"
RESIDENT = ("vertex_input_conversion_builds", "vertex_input_conversion_bytes",
            "point_conversion_builds", "point_conversion_bytes", "geometry_upload_bytes",
            "buffer_uploads", "pipeline_misses", "portable_shader_misses")


def load_authoring():
    value = json.loads(AUTHORING.read_text())
    assert value["GPU_used"] is False and value["candidate_seen"] is False
    assert value["contract"] == contract()
    for source, digest in value["sources_sha256"].items():
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest, source
    return value


def test_ordinary_analytic_criteria_and_owned_sources_were_frozen():
    load_authoring()


def test_all_thirty_input_lanes_have_separate_analytic_pixel_witnesses():
    name = "indexed_uint32_divisor2"
    expected = expected_image(name)
    masks = []
    for lane in range(ACTIVE_COUNT - 1):
        changed = expected_image(name, disabled_lanes=(lane,))
        mask = np.any(changed != expected, axis=2)
        assert np.count_nonzero(mask) == (48 if lane == 0 else 96)
        assert not any(np.array_equal(mask, other) for other in masks)
        masks.append(mask)
    source = vertex_source()
    assert source.count("in float a_lane") == ACTIVE_COUNT - 1
    for lane in range(ACTIVE_COUNT - 1):
        assert f"energy = a_lane{lane};" in source
    assert "gl_InstanceID" in source and "gl_VertexID >= 16777217" in source
    assert len(OPEN_GATES) == 4


def test_original_selection_order_first_sparse_and_topology_contracts():
    for name in CASES:
        spec = specification(name)
        if name.startswith("indexed"):
            ids = index_ids(spec)
            assert ids[:6].tolist() != list(range(6))
            assert len(np.unique(ids)) < len(ids)
            assert len(np.unique(ids)) == 6 * spec["lanes"]
        if spec["sparse"]:
            assert int(index_ids(spec).min()) > 2 ** 24
            assert SPARSE_BASE % 6 == 0
    missing = expected_image("affine_nonzero_first")
    first_cell = missing[SIZE[1] - 6:SIZE[1] - 2, 2:8, :3]
    assert np.count_nonzero(np.any(first_cell, axis=2)) == 12
    assert missing[SIZE[1] - 1 - 2, 2, :3].tolist() == [0, 0, 0]
    assert missing[SIZE[1] - 1 - 5, 7, :3].tolist() == [255, 255, 255]
    topology = {mode: expected_topology(mode) for mode in TOPOLOGIES}
    assert np.array_equal(topology["triangles"], topology["triangle_strip"])
    assert np.array_equal(topology["triangles"], topology["triangle_fan"])
    assert np.count_nonzero(topology["lines"][..., 0]) == 24
    assert np.count_nonzero(topology["line_strip"][..., 0]) == 22
    assert np.count_nonzero(topology["line_loop"][..., 0]) == 44


def test_public_cpu_layouts_preserve_padding_and_scalar_revision_regions():
    from vispy import gloo
    for name in CASES:
        program, bindings, indices = make_program(gloo, name)
        if name == "native_interleaved":
            owners = {id(record["owner"]) for record in bindings.values() if not record["constant"]}
            assert len(owners) == 3
            fields = bindings["a_lane1"]["array"]
            before = fields.copy()
            set_lane(program, bindings, 1, 0., selected_cell=1)
            after = bindings["a_lane1"]["array"]
            for field in before.dtype.names:
                if field != "lane1":
                    assert np.array_equal(before[field], after[field]), field
            assert np.array_equal(before["lane1"][:6], after["lane1"][:6])
            assert np.array_equal(before["lane1"][12:], after["lane1"][12:])
            assert np.all(after["lane1"][6:12] == 0)
        elif not specification(name)["sparse"]:
            assert len({id(record["owner"]) for record in bindings.values() if not record["constant"]}) > 8
    assert contract()["GPU_used"] is False and contract()["candidate_seen"] is False


@pytest.fixture
def ordinary_evidence(request):
    from vispy import _dawn, app, gloo
    base = os.environ.get("VISPY_ORDINARY_CAPACITY_EVIDENCE")
    output = (Path(base) if base else ROOT / "build/evidence/ordinary-input-capacity" / uuid.uuid4().hex) / request.node.name
    output.mkdir(parents=True, exist_ok=False)
    canvas = app.Canvas(app="dawn_headless", size=SIZE)
    records, images = {}, {}
    try:
        canvas.set_current()
        load_authoring()
        device = _dawn.device_info()
        assert device["ok"] and not device["software"]
        assert device["max_vertex_attributes"] == ACTIVE_COUNT
        assert int(gloo.gl.glGetParameter(gloo.gl.GL_MAX_VERTEX_ATTRIBS)) == ACTIVE_COUNT
        assert device["max_vertex_buffers"] == 8
        records.update(device=device, native_sha256=hashlib.sha256(Path(_dawn.__file__).read_bytes()).hexdigest(),
                       fixture_contract=contract(), scope="full granted30 analytic input gate; no unsupported full30 OpenGL oracle claim",
                       open_gates=list(OPEN_GATES))
        yield canvas, records, images
    finally:
        try:
            (output / "records.json").write_text(json.dumps(records, indent=2) + "\n")
            for name, image in images.items():
                np.save(output / f"{name}.npy", image, allow_pickle=False)
        finally:
            canvas.close()


def check_capture(canvas, records, images, program, indices, name, phase, expected, **options):
    from vispy import _dawn, gloo
    before = _dawn.probe()
    actual = draw(canvas, gloo, program, indices, name, **options)
    after = _dawn.probe()
    records[phase] = {"before": before, "after": after}
    images[phase], images[phase + "-expected"] = actual.copy(), expected.copy()
    np.testing.assert_array_equal(actual, expected)
    assert after["native_draw_calls"] > before["native_draw_calls"]
    return before, after


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_ordinary_native_affine_indexed_full_inputs_warm_and_loss(name, ordinary_evidence):
    from vispy import _dawn, gloo
    canvas, records, images = ordinary_evidence
    program, bindings, indices = make_program(gloo, name)
    expected = expected_image(name)
    before, after = check_capture(canvas, records, images, program, indices, name, "cold", expected)
    delta = after["vertex_input_conversion_builds"] - before["vertex_input_conversion_builds"]
    if specification(name)["route"] == "Native":
        assert delta == 0
    else:
        assert delta > 0
    before, after = check_capture(canvas, records, images, program, indices, name, "resident", expected)
    assert all(after[key] == before[key] for key in RESIDENT)
    if name in ("native_interleaved", "affine_nonzero_first", "indexed_uint32_divisor2"):
        for lane in range(ACTIVE_COUNT - 1):
            set_lane(program, bindings, lane, 0.)
            check_capture(canvas, records, images, program, indices, name, f"disabled-lane-{lane}", expected_image(name, disabled_lanes=(lane,)))
            set_lane(program, bindings, lane, 1.)
            # Lane0 originally has divisor2 values[1,0]; restore its exact rows.
            if lane == 0 and specification(name)["divisor"]:
                binding = bindings["a_lane0"]
                binding["array"] = np.array([1., 0.], np.float32)
                binding["owner"].set_subdata(binding["array"], offset=0)
            check_capture(canvas, records, images, program, indices, name, f"restored-lane-{lane}", expected)
    before, after = check_capture(canvas, records, images, program, indices, name, "updated-resident", expected)
    assert all(after[key] == before[key] for key in RESIDENT)
    baseline = _dawn.probe()
    _dawn.lose_device()
    _, after = check_capture(canvas, records, images, program, indices, name, "same-program-loss-recovery", expected)
    assert after["device_generation"] > baseline["device_generation"]
    assert after["vertex_input_conversion_builds"] == baseline["vertex_input_conversion_builds"]
    assert after["vertex_input_conversion_bytes"] == baseline["vertex_input_conversion_bytes"]
    assert after["portable_shader_misses"] == baseline["portable_shader_misses"]
    assert after["geometry_upload_bytes"] > baseline["geometry_upload_bytes"]


@pytest.mark.gpu
def test_ordinary_pending_middle_region_and_constant_preserve_old_draw(ordinary_evidence):
    from vispy import _dawn, gloo
    canvas, records, images = ordinary_evidence
    name = "indexed_uint32_divisor2"
    program, bindings, indices = make_program(gloo, name)
    check_capture(canvas, records, images, program, indices, name, "prewarm", expected_image(name))
    before = _dawn.probe()
    records["pending-two-draws"] = {"before": before}
    assert before["pending_draws"] == 0
    draw(canvas, gloo, program, indices, name, clear=True, read=False)
    old_pending = _dawn.probe()
    records["pending-two-draws"]["old_pending"] = old_pending
    # pending_draws includes the queued CLEAR snapshot as well as scene DRAW.
    assert old_pending["pending_draws"] == 2
    assert old_pending["draw_calls"] == before["draw_calls"]
    set_lane(program, bindings, 7, 0., selected_cell=7)
    set_lane(program, bindings, 1, 0.)
    draw(canvas, gloo, program, indices, name, phase=1, clear=False, read=False)
    pending = _dawn.probe()
    actual = gloo.read_pixels(alpha=True)
    expected = expected_image(name)
    upper = expected_image(name, phase=1, disabled_lanes=(1, 7))
    expected[:SIZE[1] - 128] = upper[:SIZE[1] - 128]
    after = _dawn.probe()
    records["pending-two-draws"] = {"before": before, "old_pending": old_pending, "pending": pending, "after": after,
                                    "explicit_reads_between_dependent_draws": 0, "final_reads": 1,
                                    "retained_snapshots": "one CLEAR plus two scene DRAWs",
                                    "middle_patch_element_offset": 42, "middle_patch_elements": 6,
                                    "scalar_source_bytes": 4 * 174}
    images["pending-two-draws"], images["pending-two-draws-expected"] = actual, expected
    np.testing.assert_array_equal(actual, expected)
    assert pending["pending_draws"] == 3
    assert pending["draw_calls"] == before["draw_calls"]
    assert after["draw_calls"] - before["draw_calls"] == 2
    assert after["pending_draws"] == 0
    assert pending["completion_waits"] == before["completion_waits"]
    assert pending["vk_queue_submits"] == before["vk_queue_submits"]


@pytest.mark.gpu
def test_same_program_points_ordinary_points_retains_primitive_inputs(ordinary_evidence):
    from vispy import gloo
    canvas, records, images = ordinary_evidence
    name = "indexed_uint32_divisor2"
    program, bindings, indices = make_program(gloo, name)
    expected_points = expected_image(name, mode="points")
    check_capture(canvas, records, images, program, indices, name, "first-points", expected_points, mode="points")
    check_capture(canvas, records, images, program, indices, name, "ordinary-triangles", expected_image(name))
    before, after = check_capture(canvas, records, images, program, indices, name, "resident-original-points", expected_points, mode="points")
    assert all(after[key] == before[key] for key in RESIDENT)
    before, after = check_capture(canvas, records, images, program, indices, name, "resident-original-triangles", expected_image(name))
    assert all(after[key] == before[key] for key in RESIDENT)


@pytest.mark.gpu
@pytest.mark.parametrize("mode", TOPOLOGIES)
def test_ordinary_full_input_supported_topology_pixels(mode, ordinary_evidence):
    from vispy import _dawn, gloo
    canvas, records, images = ordinary_evidence
    name = "indexed_uint8"
    program, bindings, indices = make_program(gloo, name)
    positions, ids = topology_data(mode)
    position = bindings["position"]
    updated = position["array"].copy()
    updated["position"][:6] = positions
    position["owner"].set_subdata(updated[:6], offset=0)
    program["u_corner_scale"] = 0.
    indices = gloo.IndexBuffer(ids)
    expected = expected_topology(mode)
    before, after = check_capture(canvas, records, images, program, indices, name, "topology-cold", expected, mode=mode)
    before, after = check_capture(canvas, records, images, program, indices, name, "topology-resident", expected, mode=mode)
    assert all(after[key] == before[key] for key in RESIDENT)
    if mode.startswith("line") and records["device"]["backend"] == "Vulkan":
        assert records["device"]["bresenham_lines"]
        assert after["bresenham_line_pipelines"] > 0


@pytest.mark.gpu
@pytest.mark.parametrize("mode", ("triangles", "triangle_strip", "triangle_fan"))
def test_ordinary_compact_indices_preserve_original_last_vertex(mode, ordinary_evidence):
    from vispy import _dawn, gloo
    canvas, records, images = ordinary_evidence
    name = "indexed_uint8"
    program, bindings, unused_indices = make_program(gloo, name)
    positions, ids = topology_data(mode)
    position = bindings["position"]
    updated = position["array"].copy()
    updated["position"][:6] = positions
    position["owner"].set_subdata(updated[:6], offset=0)
    program["u_corner_scale"], program["u_flat_probe"] = 0., 1.
    indices = gloo.IndexBuffer(ids)
    _, after = check_capture(canvas, records, images, program, indices, name, "original-last-vertex", expected_topology(mode), mode=mode)
    if records["device"]["backend"] == "Vulkan":
        assert records["device"]["last_vertex_provoking"]
        assert after["last_vertex_pipelines"] > 0
