"""Public single-sample depth textures: uploaded values and retained GPU writes."""
from contextlib import contextmanager

import numpy as np
import pytest

from vispy import app, gloo

SIZE = (12, 8)
FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
VERTEX = "attribute vec2 position;uniform float z;void main(){gl_Position=vec4(position,z*2.-1.,1);}"
FRAGMENT = "uniform vec4 color;void main(){gl_FragColor=color;}"


def test_public_depth_texture_emits_full_and_offset_data_with_fixed_depth_storage():
    texture = gloo.Texture2D(np.full((8, 12), .75, np.float32), format="depth_component",
                            internalformat="depth_component", interpolation="nearest")
    try:
        texture.set_data(np.full((2, 3), .25, np.float32), offset=(1, 2))
        commands = texture.glir._shared._commands
        sizes = [c for c in commands if c[0] == "SIZE"]
        assert sizes and all(c[2:] == ((8, 12, 1), "depth_component", "depth_component") for c in sizes)
        data = [c for c in commands if c[0] == "DATA"]
        assert [c[2] for c in data] == [(0, 0), (1, 2)]
        assert [c[3].shape for c in data] == [(8, 12, 1), (2, 3, 1)]
        assert all(c[3].dtype == np.float32 for c in data)
    finally:
        texture.delete()


@contextmanager
def scene(data, explicit_internal=True):
    from vispy import _dawn
    canvas = app.Canvas(app="dawn_headless", size=SIZE, show=False)
    owned = []
    try:
        canvas.set_current()
        color = gloo.RenderBuffer((SIZE[1], SIZE[0]), format="color")
        depth = gloo.Texture2D(data, format="depth_component", interpolation="nearest",
                              internalformat="depth_component" if explicit_internal else None)
        fbo = gloo.FrameBuffer(color=color, depth=depth)
        source = gloo.VertexBuffer(FULL)
        p = gloo.Program(VERTEX, FRAGMENT)
        p["position"] = source
        owned.extend((color, depth, fbo, source, p))
        with fbo:
            gloo.set_viewport(0, 0, *SIZE)
            gloo.set_state(blend=False, depth_test=True, depth_func="less", depth_mask=True,
                           stencil_test=False, scissor_test=False, cull_face=False)
            gloo.set_clear_color((0, 0, 0, 1))
            gloo.clear(color=True, depth=False, stencil=False)
            yield canvas, depth, p
    finally:
        canvas.set_current()
        for obj in reversed(owned):obj.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()
        after = _dawn.probe()
        assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
        assert after["line_resource_pool_busy_slots"] == 0
        assert _dawn.device_info()["backend"] == "Vulkan"


def draw(p, z, color, rectangle=None):
    p["z"] = z;p["color"] = color
    gloo.set_state(scissor_test=rectangle is not None)
    if rectangle is not None:gloo.set_scissor(*rectangle)
    p.draw("triangles")


def depth_pixels():
    return gloo.read_pixels(mode="depth", out_type="float")[..., 0]


@pytest.mark.gpu
@pytest.mark.parametrize("dtype", [np.float32, np.uint16])
@pytest.mark.parametrize("explicit_internal", [False, True])
def test_full_depth_payload_controls_real_depth_test_and_reports_exact_storage(dtype, explicit_internal):
    from vispy import _dawn
    data = np.tile(np.array([.25] * 6 + [.75] * 6, np.float32), (8, 1))
    if dtype == np.uint16:data = np.round(data * 65535).astype(dtype)
    with scene(data, explicit_internal) as (canvas, _, p):
        canvas.context.flush_commands()
        config = _dawn.framebuffer_config(int(canvas._backend._dawn_canvas_id))
        assert config["depth_stencil_format"] == "depth32float"
        assert config["depth_size"] == config["depth_size_minimum"] == 32 and config["depth_size_exact"]
        assert config["backing_stencil_size"] == config["stencil_size"] == 0
        draw(p, .5, (0, 1, 0, 1))
        image = gloo.read_pixels()
        assert np.all(image[:, :6, :3] == 0)
        np.testing.assert_array_equal(image[:, 6:, :3], np.tile([0, 255, 0], (8, 6, 1)))
        actual = depth_pixels()
        np.testing.assert_allclose(actual[:, :6], float(data[0, 0]) / (65535 if dtype == np.uint16 else 1), atol=1e-6)
        np.testing.assert_allclose(actual[:, 6:], .5, atol=1e-6)


@pytest.mark.gpu
@pytest.mark.parametrize("flush_between", [False, True])
def test_partial_depth_upload_preserves_gpu_written_untouched_pixels_and_queued_revisions(flush_between):
    with scene(np.full((8, 12), .75, np.float32)) as (_, depth, p):
        draw(p, .1, (1, 0, 0, 1), (0, 0, 6, 8))
        if flush_between:gloo.finish()
        depth.set_data(np.full((8, 6), .8, np.float32), offset=(0, 6))
        draw(p, .5, (0, 0, 1, 1))
        image = gloo.read_pixels()
        np.testing.assert_array_equal(image[:, :6, :3], np.tile([255, 0, 0], (8, 6, 1)))
        np.testing.assert_array_equal(image[:, 6:, :3], np.tile([0, 0, 255], (8, 6, 1)))
        actual = depth_pixels()
        np.testing.assert_allclose(actual[:, :6], .1, atol=1e-6)
        np.testing.assert_allclose(actual[:, 6:], .5, atol=1e-6)


@pytest.mark.gpu
def test_full_replacement_does_not_change_already_queued_depth_snapshot():
    with scene(np.full((8, 12), .75, np.float32)) as (_, depth, p):
        draw(p, .5, (1, 0, 0, 1), (0, 0, 6, 8))
        depth.set_data(np.full((8, 12), .25, np.float32))
        draw(p, .5, (0, 1, 0, 1), (6, 0, 6, 8))
        image = gloo.read_pixels()
        np.testing.assert_array_equal(image[:, :6, :3], np.tile([255, 0, 0], (8, 6, 1)))
        assert np.all(image[:, 6:, :3] == 0)
        np.testing.assert_allclose(depth_pixels(), .25, atol=1e-6)


@pytest.mark.gpu
def test_offset_depth_patches_before_allocation_and_after_readback_use_actual_mixed_dtype_values():
    with scene(np.full((8, 12), .75, np.float32)) as (_, depth, _):
        depth.set_data(np.zeros((2, 3), np.uint8), offset=(1, 2))
        expected = np.full((8, 12), .75, np.float32);expected[1:3, 2:5] = 0
        np.testing.assert_allclose(depth_pixels(), expected[::-1], atol=1e-6)
        depth.set_data(np.full((3, 2), 65535, np.uint16), offset=(4, 8))
        expected[4:7, 8:10] = 1
        np.testing.assert_allclose(depth_pixels(), expected[::-1], atol=1e-6)


@pytest.mark.gpu
def test_depth_upload_recovery_recreates_pipeline_and_actual_attachment_from_retained_cpu_data():
    from vispy import _dawn
    with scene(np.full((8, 12), .75, np.float32)) as (canvas, _, p):
        initial = depth_pixels()
        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device();canvas.set_current();gloo.set_viewport(0, 0, *SIZE)
        np.testing.assert_allclose(depth_pixels(), initial, atol=1e-6)
        draw(p, .5, (0, 1, 0, 1))
        assert np.all(gloo.read_pixels()[..., 1] == 255)
        assert _dawn.probe()["device_generation"] > generation
