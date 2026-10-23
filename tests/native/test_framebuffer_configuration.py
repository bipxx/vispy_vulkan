"""Actual Dawn target configuration without native OpenGL framebuffer queries."""

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu


def query(canvas):
    canvas.context.flush_commands()
    return _dawn.framebuffer_config(int(canvas._backend._dawn_canvas_id))


@pytest.mark.parametrize("samples", [0, 4])
def test_canvas_configuration_uses_storage_not_requested_gl_defaults(samples):
    canvas = app.Canvas(app="dawn_headless", size=(7, 5), show=False,
                        config={"samples": samples, "depth_size": 16, "stencil_size": 0})
    try:
        canvas.set_current()
        config = query(canvas)
        assert [config[n + "_size"] for n in ("red", "green", "blue", "alpha")] == [8] * 4
        assert config["depth_size"] is None and config["depth_size_minimum"] == 24
        assert config["depth_size_exact"] is False and config["stencil_size"] == 8
        assert config["depth_stencil_format"] == "depth24plus-stencil8"
        assert config["samples"] == samples and config["sample_count"] == max(1, samples)
        assert (config["width"], config["height"], config["framebuffer_id"]) == (7, 5, 0)
        assert not config["double_buffer"] and not config["stereo"] and not config["srgb"]
        assert config["configuration_source"] == "allocated_target"
        before = _dawn.probe()
        assert query(canvas) == config
        after = _dawn.probe()
        for name in ("dawn_queue_submits", "completion_waits", "texture_uploads", "texture_upload_bytes"):
            assert after[name] == before[name], name
    finally:
        canvas.close()


@pytest.mark.parametrize("channels,format_name,internal,bits", [
    (1, "red", "r32f", 32), (2, "rg", "rg16f", 16),
    (3, "rgb", "rgb8", 8), (4, "rgba", "rgba16f", 16),
])
def test_fbo_configuration_uses_frozen_storage_and_does_not_upload(channels, format_name, internal, bits):
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False, config={"samples": 4})
    try:
        canvas.set_current()
        texture = gloo.Texture2D(np.zeros((3, 6, channels), np.float32),
                                 format=format_name, internalformat=internal)
        fbo = gloo.FrameBuffer(color=texture)
        with fbo:
            canvas.context.flush_commands()
            before = _dawn.probe()
            config = _dawn.framebuffer_config(int(canvas._backend._dawn_canvas_id))
            after = _dawn.probe()
            physical_channels = 4 if channels == 3 else channels
            expected = [bits if physical_channels >= count else 0 for count in (1, 2, 4, 4)]
            assert [config[n + "_size"] for n in ("red", "green", "blue", "alpha")] == expected
            assert config["depth_size"] == config["stencil_size"] == 0
            assert config["depth_size_exact"] and config["sample_count"] == 1 and config["samples"] == 0
            assert (config["width"], config["height"], config["framebuffer_id"]) == (6, 3, fbo.id)
            for name in ("texture_uploads", "texture_upload_bytes", "dawn_queue_submits", "completion_waits"):
                assert after[name] == before[name], name
        assert query(canvas)["framebuffer_id"] == 0
        fbo.delete()
        texture.delete()
        canvas.context.flush_commands()
    finally:
        canvas.close()


@pytest.mark.parametrize("kind", ["depth", "stencil"])
def test_fbo_configuration_separates_logical_attachments_from_native_backing(kind):
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    try:
        canvas.set_current()
        color = gloo.RenderBuffer((4, 6), format="color")
        attachment = gloo.RenderBuffer((4, 6), format=kind)
        fbo = gloo.FrameBuffer(color=color, **{kind: attachment})
        with fbo:
            config = query(canvas)
            assert config["depth_stencil_format"] == "depth24plus-stencil8"
            assert config["backing_depth_size_minimum"] == 24 and config["backing_stencil_size"] == 8
            assert config["has_depth_attachment"] == (kind == "depth")
            assert config["has_stencil_attachment"] == (kind == "stencil")
            if kind == "depth":
                assert config["depth_size"] is None
            else:
                assert config["depth_size"] == 0
            assert config["stencil_size"] == (8 if kind == "stencil" else 0)
        fbo.delete()
        color.delete()
        attachment.delete()
        canvas.context.flush_commands()
    finally:
        canvas.close()


def test_missing_canvas_configuration_fails_instead_of_returning_defaults():
    with pytest.raises(RuntimeError, match="missing canvas"):
        _dawn.framebuffer_config(0)


def test_configuration_query_recreates_lost_default_target_without_gl_fallback():
    canvas = app.Canvas(app="dawn_headless", size=(7, 5), show=False, config={"samples": 4})
    try:
        canvas.set_current()
        before = query(canvas)
        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device()
        assert _dawn.probe()["device_generation"] == generation
        assert _dawn.framebuffer_config(int(canvas._backend._dawn_canvas_id)) == before
        assert _dawn.probe()["device_generation"] > generation
        assert _dawn.device_info()["backend"] == "Vulkan"
    finally:
        canvas.close()
