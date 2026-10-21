"""Actual public user-input capacity; analytic fixture has no OpenGL-limit claim."""
import hashlib
import json
import os
from pathlib import Path
import uuid

import numpy as np
import pytest

from tools.fixture_point_capacity import (CASES, FRAGMENT, SIZE, draw, expected_image,
                                        make_program, update_lane, vertex_source)

ROOT = Path(__file__).resolve().parents[2]
RESIDENT = ("point_conversion_builds", "point_conversion_bytes", "geometry_upload_bytes",
            "buffer_uploads", "pipeline_misses", "portable_shader_misses")


@pytest.fixture
def capacity_evidence(request):
    from vispy import _dawn, app
    base = os.environ.get("VISPY_POINT_CAPACITY_EVIDENCE")
    output = (Path(base) if base else ROOT / "build/evidence/point-input-capacity" / uuid.uuid4().hex) / request.node.name
    output.mkdir(parents=True, exist_ok=False)
    canvas = app.Canvas(app="dawn_headless", size=SIZE)
    records, images = {}, {}
    try:
        canvas.set_current()
        device = _dawn.device_info()
        assert device["ok"] and device["backend"] == "Vulkan" and not device["software"]
        records["device"] = device
        records["native_sha256"] = hashlib.sha256(Path(_dawn.__file__).read_bytes()).hexdigest()
        records["scope"] = "Analytic point capacity/primitive-policy gate, not upstream parity beyond its granted limits"
        yield canvas, device, records, images
    finally:
        try:
            (output / "records.json").write_text(json.dumps(records, indent=2) + "\n")
            for name, image in images.items():
                np.save(output / f"{name}.npy", image, allow_pickle=False)
        finally:
            canvas.close()


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_all_granted_point_inputs_are_active_and_preserve_exact_ids(name, capacity_evidence):
    from vispy import _dawn, gloo
    canvas, device, records, images = capacity_evidence
    count = int(gloo.gl.glGetParameter(gloo.gl.GL_MAX_VERTEX_ATTRIBS))
    assert count == device["max_vertex_attributes"] >= 2
    program, bindings, indices = make_program(gloo, name, count)

    def capture(phase, expected):
        before = _dawn.probe()
        image = draw(canvas, gloo, program, indices, name)
        after = _dawn.probe()
        records[phase] = {"before": before, "after": after}
        images[phase] = image.copy()
        images[f"{phase}-expected"] = expected.copy()
        np.testing.assert_array_equal(image, expected)
        assert after["native_draw_calls"] > before["native_draw_calls"]
        return before, after

    expected = expected_image(name)
    capture("cold-full-capacity", expected)
    assert device["core_features_and_limits"] and device["max_point_vertex_attributes"] == count
    assert device["max_storage_buffers_per_shader_stage"] > 0
    assert device["max_storage_buffer_binding_size"] >= 8
    before, after = capture("resident", expected)
    assert all(after[key] == before[key] for key in RESIDENT)
    assert after["live_cpu_buffer_bytes"] > 0
    assert after["sampled_peak_live_cpu_buffer_bytes"] >= after["live_cpu_buffer_bytes"]

    if name == "uint32_divisor2":
        # Every scalar input must independently change the actual image.
        # Each restores zero before the next input is exercised.
        for lane in range(count - 1):
            update_lane(program, bindings, lane, 1.)
            before, after = capture(f"active-lane-{lane}", expected_image(name, energized=True))
            assert after["point_conversion_builds"] > before["point_conversion_builds"]
            update_lane(program, bindings, lane, 0.)
            capture(f"restored-lane-{lane}", expected)
        positions = np.tile(np.array([3.5, 4.5], np.float32), (8, 1))
        program["a_position"].set_data(positions)
        capture("active-position", expected_image(name, position_shift=1))
        program["a_position"].set_data(np.tile(np.array([2.5, 4.5], np.float32), (8, 1)))
        capture("restored-position", expected)

    before, after = capture("updated-resident", expected)
    assert all(after[key] == before[key] for key in RESIDENT)
    loss_baseline = _dawn.probe()
    _dawn.lose_device()
    _, recovered = capture("loss-recovery", expected)
    assert recovered["device_generation"] > loss_baseline["device_generation"]
    assert recovered["point_conversion_builds"] == loss_baseline["point_conversion_builds"]
    assert recovered["point_conversion_bytes"] == loss_baseline["point_conversion_bytes"]
    assert recovered["geometry_upload_bytes"] > loss_baseline["geometry_upload_bytes"]
    assert recovered["portable_shader_misses"] == loss_baseline["portable_shader_misses"]


@pytest.mark.gpu
def test_point_inputs_above_granted_limit_fail_contextually(capacity_evidence):
    from vispy import gloo
    canvas, device, records, images = capacity_evidence
    count = device["max_vertex_attributes"] + 1
    program, bindings, indices = make_program(gloo, "uint8", count)
    with pytest.raises(RuntimeError, match=r"active.*inputs.*exceed.*attribute limit") as error:
        draw(canvas, gloo, program, indices, "uint8")
    records["expected_error"] = {"requested_active_inputs": count, "message": str(error.value)}


@pytest.mark.gpu
def test_same_program_points_triangles_lines_and_strip_keep_primitive_artifacts(capacity_evidence):
    from vispy import _dawn, gloo
    canvas, device, records, images = capacity_evidence
    vertex = """attribute vec2 a_position; varying vec4 v_color;
    void main(){gl_Position=vec4(a_position,0,1);gl_PointSize=1.;v_color=vec4(1,0,0,1);}"""
    fragment = "varying vec4 v_color; void main(){gl_FragColor=v_color;}"
    program = gloo.Program(vertex, fragment)
    pixels = np.array([[10.5, 8.5], [30.5, 8.5], [20.5, 24.5]], np.float32)
    program["a_position"] = gloo.VertexBuffer((pixels / SIZE * 2 - 1).astype(np.float32))

    def capture(mode, indices=None):
        gloo.set_viewport(0, 0, *SIZE)
        gloo.set_state(blend=False, depth_test=False)
        gloo.set_clear_color((0, 0, 0, 1))
        gloo.clear()
        program.draw(mode, indices)
        image = gloo.read_pixels(alpha=True)
        images[mode] = image.copy()
        return image

    points = capture("points")
    expected = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    expected[..., 3] = 255
    for column, y in pixels.astype(int):
        expected[SIZE[1] - 1 - y, column] = (255, 0, 0, 255)
    np.testing.assert_array_equal(points, expected)
    triangles = capture("triangles")
    assert triangles[SIZE[1] - 1 - 12, 20].tolist() == [255, 0, 0, 255]
    lines = capture("lines", gloo.IndexBuffer(np.array([0, 1], np.uint16)))
    assert lines[SIZE[1] - 1 - 8, 20].tolist() == [255, 0, 0, 255]
    strip = capture("triangle_strip")
    np.testing.assert_array_equal(strip, triangles)
    before = _dawn.probe()
    np.testing.assert_array_equal(capture("points"), points)
    after = _dawn.probe()
    records["point-reuse"] = {"before": before, "after": after}
    assert all(after[key] == before[key] for key in RESIDENT)
