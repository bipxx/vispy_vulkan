"""Native cached point conversion must survive residency, revisions and loss."""
import hashlib
import json
import os
from pathlib import Path
import uuid

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
RESIDENT_COUNTERS = (
    "point_conversion_builds", "point_conversion_bytes", "buffer_uploads",
    "geometry_upload_bytes", "pipeline_misses", "portable_shader_misses",
)


@pytest.fixture
def point_evidence(request):
    from vispy import app, gloo, _dawn

    base = os.environ.get("VISPY_POINT_LIFECYCLE_EVIDENCE")
    output = Path(base) if base else ROOT / "build/evidence/point-conversion-lifecycle" / uuid.uuid4().hex
    output = output / request.node.name
    output.mkdir(parents=True, exist_ok=False)
    canvas = app.Canvas(app="dawn_headless", size=(48, 32))
    records = {}
    images = {}
    try:
        canvas.set_current()
        device = _dawn.device_info()
        assert device["ok"] and device["backend"] == "Vulkan" and not device["software"]
        records["environment"] = {
            "device_info": device,
            "native_origin": _dawn.__file__,
            "native_sha256": hashlib.sha256(Path(_dawn.__file__).read_bytes()).hexdigest(),
            "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "scope": "Native reuse/revision/loss contract; captures use explicit completion barriers",
        }
        yield canvas, records, images
    finally:
        try:
            (output / "counters.json").write_text(json.dumps(records, indent=2) + "\n")
            for phase, image in images.items():
                np.save(output / f"{phase}.npy", image, allow_pickle=False)
        finally:
            canvas.close()


def point_program():
    from vispy import gloo

    program = gloo.Program(
        "attribute vec2 a_position; attribute vec4 a_color; attribute float a_size; "
        "uniform vec2 u_offset; varying vec4 v_color; "
        "void main(){gl_Position=vec4(a_position+u_offset,0.,1.); "
        "gl_PointSize=a_size; v_color=vec4(a_color.rgb*(.5+.5*float((gl_VertexID+gl_InstanceID)%2)),a_color.a);}",
        "varying vec4 v_color; void main(){vec2 p=gl_PointCoord-vec2(.5); "
        "if(dot(p,p)>.25)discard; gl_FragColor=v_color;}")
    program["u_offset"] = (0., 0.)
    return program


def assert_resident(before, after):
    for counter in RESIDENT_COUNTERS:
        assert after[counter] == before[counter], (counter, before[counter], after[counter])


def projected_region(image, position):
    """Fixed six-pixel margin around the input position in top-left readback."""
    height, width = image.shape[:2]
    center_x = (position[0] + 1) * width / 2
    center_y = (1 - position[1]) * height / 2
    rows, columns = np.indices((height, width))
    return (np.abs(columns + .5 - center_x) <= 6) & (np.abs(rows + .5 - center_y) <= 6)


@pytest.mark.gpu
def test_indexed_point_conversion_reuses_cpu_payloads_and_reuploads_after_loss(point_evidence):
    from vispy import gloo, _dawn

    canvas, records, images = point_evidence
    program = point_program()
    positions = gloo.VertexBuffer(np.array([[-.65,-.5],[-.2,.5],[.3,-.5],[.7,.5]], np.float32))
    colors = gloo.VertexBuffer(np.tile(np.array([1,0,0,1],np.float32),(4,1)))
    indices = gloo.IndexBuffer(np.array([3,0,3,1],np.uint16))
    program["a_position"], program["a_color"], program["a_size"] = positions, colors, 3.

    def draw(phase):
        canvas.set_current()
        before = _dawn.probe()
        gloo.set_viewport(0,0,48,32)
        gloo.set_clear_color((0,0,0,1))
        gloo.clear()
        gloo.set_state(blend=False,depth_test=False)
        program.draw("points",indices)
        image = gloo.read_pixels(alpha=True)
        after = _dawn.probe()
        records[phase] = {"before":before,"after":after}
        images[phase] = image.copy()
        assert np.any(image[...,:3]), "Native point draw produced no fragments"
        assert after["native_draw_calls"] > before["native_draw_calls"]
        assert after["dawn_queue_submits"] > before["dawn_queue_submits"]
        return before,after,image

    before,cold,first = draw("cold")
    assert cold["point_conversion_builds"] > before["point_conversion_builds"]
    assert cold["point_conversion_bytes"] > before["point_conversion_bytes"]
    for n in range(3):
        before,after,image = draw(f"resident-{n}")
        assert np.array_equal(first,image)
        assert_resident(before, after)
    colors.set_subdata(np.array([[0,1,0,1]],np.float32),offset=1)
    before,after,recolored = draw("middle-color-patch")
    assert after["point_conversion_builds"]>before["point_conversion_builds"]
    assert after["geometry_upload_bytes"]>before["geometry_upload_bytes"]
    assert not np.array_equal(first,recolored)
    changed_vertex = projected_region(first, (-.2, .5))
    assert np.array_equal(first[~changed_vertex], recolored[~changed_vertex])
    fragments = changed_vertex & (first[..., 0] > 0)
    assert fragments.any()
    assert np.all(recolored[fragments] == np.array([0, 255, 0, 255], np.uint8))
    indices.set_data(np.array([2,0,2,1],np.uint16))
    before,after,reindexed = draw("index-revision")
    assert after["point_conversion_builds"]>before["point_conversion_builds"]
    assert not np.array_equal(recolored,reindexed)
    assert np.array_equal(recolored[changed_vertex], reindexed[changed_vertex])
    unchanged_vertex = projected_region(first, (-.65, -.5))
    assert np.array_equal(recolored[unchanged_vertex], reindexed[unchanged_vertex])
    removed_vertex = projected_region(first, (.7, .5))
    added_vertex = projected_region(first, (.3, -.5))
    assert not np.any(reindexed[removed_vertex, :3])  # original index three is no longer selected
    assert np.any(reindexed[added_vertex, :3])  # original index two is now selected
    program["a_size"] = 7.
    before,after,resized = draw("constant-size-revision")
    assert after["point_conversion_builds"] > before["point_conversion_builds"]
    assert after["geometry_upload_bytes"]>before["geometry_upload_bytes"]
    assert np.count_nonzero(resized[...,:3])>np.count_nonzero(reindexed[...,:3])
    before,after,unchanged = draw("updated-resident")
    assert np.array_equal(resized, unchanged)
    assert_resident(before, after)
    before_loss = _dawn.probe()
    _dawn.lose_device()
    _,after,recovered = draw("device-loss-recovery")
    assert np.array_equal(resized,recovered)
    assert after["device_generation"]>before_loss["device_generation"]
    assert after["point_conversion_builds"]==before_loss["point_conversion_builds"]
    assert after["point_conversion_bytes"]==before_loss["point_conversion_bytes"]
    assert after["geometry_upload_bytes"]>before_loss["geometry_upload_bytes"]
    assert after["portable_shader_misses"]==before_loss["portable_shader_misses"]


@pytest.mark.gpu
def test_point_revisions_retain_pending_draws_until_one_final_capture(point_evidence):
    from vispy import gloo, _dawn

    canvas, records, images = point_evidence
    program = point_program()
    positions = gloo.VertexBuffer(np.array([[-.15, -.15], [0, .15], [.15, -.15]], np.float32))
    colors = gloo.VertexBuffer(np.tile(np.array([1, 0, 0, 1], np.float32), (3, 1)))
    indices = gloo.IndexBuffer(np.array([2, 0, 1], np.uint16))
    program["a_position"], program["a_color"], program["a_size"] = positions, colors, 3.
    gloo.set_viewport(0, 0, 48, 32)
    gloo.set_clear_color((0, 0, 0, 1))
    gloo.clear()
    gloo.set_state(blend=False, depth_test=False)
    before = _dawn.probe()
    program["u_offset"] = (-.5, 0.)
    program.draw("points", indices)
    old_pending = _dawn.probe()
    colors.set_data(np.tile(np.array([0, 1, 0, 1], np.float32), (3, 1)))
    program["a_size"] = 5.
    program["u_offset"] = (.5, 0.)
    program.draw("points", indices)
    new_pending = _dawn.probe()
    colors.set_data(np.tile(np.array([0, 0, 1, 1], np.float32), (3, 1)))
    canvas.context.flush_commands()
    overwritten = _dawn.probe()
    image = gloo.read_pixels(alpha=True)
    after = _dawn.probe()
    records["pending-revisions"] = {
        "before": before, "old_pending": old_pending, "new_pending": new_pending,
        "latest_unrendered_revision": overwritten, "after": after, "readbacks": 1,
    }
    images["pending-revisions"] = image
    assert old_pending["pending_draws"] > before["pending_draws"]
    assert new_pending["pending_draws"] > old_pending["pending_draws"]
    assert new_pending["point_conversion_builds"] > old_pending["point_conversion_builds"]
    assert overwritten["native_draw_calls"] == before["native_draw_calls"]
    assert overwritten["dawn_queue_submits"] == before["dawn_queue_submits"]
    assert overwritten["completion_waits"] == before["completion_waits"]
    assert overwritten["finish_calls"] == before["finish_calls"]
    assert after["native_draw_calls"] >= before["native_draw_calls"] + 2
    left, right = image[:, :24], image[:, 24:]
    assert np.any(left[..., 0]) and not np.any(left[..., 1:3])
    assert np.any(right[..., 1]) and not np.any(right[..., [0, 2]])
    assert not np.any(image[..., 2]), "Latest unrendered blue revision changed pending red/green draws"
