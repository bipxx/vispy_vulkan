"""Default MSAA capture selects actual samplezero; it never averages depth/index.

OpenGL4.6 section18.2.3 permits implementation-selected depth/stencil reduction.
The Vulkan backend deliberately chooses sample0, independently of other drivers.
"""
from contextlib import contextmanager

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu
SIZE = (12, 8)
FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
DEPTH = [.125, .25, .5, .75]
STENCIL = [17, 68, 129, 251]
VERTEX = "attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}"
FRAGMENT = """uniform int selected;uniform float value;
void main(){if(gl_SampleID!=selected)discard;
gl_SampleMask[0]=1<<gl_SampleID;gl_FragDepth=value;gl_FragColor=vec4(1);}
"""


@contextmanager
def scene(samples=4):
    canvas = app.Canvas(app="dawn_headless", size=SIZE, show=False, config={"samples": samples})
    owned = []
    try:
        canvas.set_current()
        source = gloo.VertexBuffer(FULL)
        program = gloo.Program(VERTEX, FRAGMENT)
        program["position"] = source
        owned.extend((source, program))
        gloo.set_state(blend=False, depth_test=True, depth_func="always", depth_mask=True,
                       stencil_test=True, scissor_test=False, cull_face=False)
        gloo.set_stencil_mask(255)
        gloo.set_stencil_op("keep", "keep", "replace")
        yield canvas, program, owned
    finally:
        canvas.set_current()
        for obj in reversed(owned):obj.delete()
        canvas.context.flush_commands();canvas.close();_dawn.process_events()
        after = _dawn.probe()
        assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
        assert after["line_resource_pool_busy_slots"] == 0
        assert _dawn.device_info()["backend"] == "Vulkan"


def fill(program, samples, size=SIZE, left_only=False):
    gloo.set_viewport(0, 0, *size)
    gloo.set_state(scissor_test=False)
    gloo.set_clear_depth(.875);gloo.set_clear_stencil(9)
    gloo.clear(color=True, depth=True, stencil=True)
    if left_only:
        gloo.set_state(scissor_test=True);gloo.set_scissor(0, 0, size[0] // 2, size[1])
    # Each queued DRAW writes one actual sample with a different depth/index.
    # Sample0 is neither the arithmeticmean nor any later draw's sample.
    for sample in range(max(1, samples)):
        program["selected"] = sample;program["value"] = DEPTH[sample]
        gloo.set_stencil_func("always", STENCIL[sample], 255)
        program.draw("triangles")
    gloo.set_state(scissor_test=False)


def assert_values(image, mode, out_type, expected):
    assert image.shape[-1] == 1
    actual = image[..., 0]
    if mode == "depth" and out_type == "unsigned_byte":
        expected = np.floor(np.asarray(expected) * 255 + .5)
        assert np.max(np.abs(actual.astype(float) - expected)) <= 1
    else:
        np.testing.assert_allclose(actual, expected, atol=1e-6 if mode == "depth" else 0)


@pytest.mark.parametrize("samples", [0, 4])
@pytest.mark.parametrize("mode", ["depth", "stencil"])
@pytest.mark.parametrize("out_type", ["float", "unsigned_byte"])
def test_actual_selected_sample_and_background_survive_full_and_cropped_capture(samples, mode, out_type):
    with scene(samples) as (_, program, _):
        fill(program, samples, left_only=True)
        selected = DEPTH[0] if mode == "depth" else STENCIL[0]
        background = .875 if mode == "depth" else 9
        expected = np.full((8, 12), background);expected[:, :6] = selected
        assert_values(gloo.read_pixels(mode=mode, out_type=out_type), mode, out_type, expected)
        # Crop crosses both authored and untouched pixels; invariantrows avoid
        # conflating sample selection with API image-row orientation.
        crop = (3, 2, 6, 3)
        assert_values(gloo.read_pixels(crop, mode=mode, out_type=out_type), mode, out_type,
                      expected[2:5, 3:9])


@pytest.mark.parametrize("mode", ["depth", "stencil"])
def test_single_sample_fbo_on_multisampled_canvas_retains_its_own_capture_path(mode):
    with scene() as (canvas, program, owned):
        color = gloo.RenderBuffer((8, 12), format="color")
        attachment = gloo.RenderBuffer((8, 12), format=mode)
        fbo = gloo.FrameBuffer(color=color, **{mode: attachment})
        owned.extend((color, attachment, fbo))
        with fbo:
            gloo.set_clear_depth(.375);gloo.set_clear_stencil(193)
            gloo.clear(color=True, depth=mode == "depth", stencil=mode == "stencil")
            canvas.context.flush_commands()
            assert _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)["sample_count"] == 1
            assert_values(gloo.read_pixels(mode=mode, out_type="float"), mode, "float",
                          .375 if mode == "depth" else 193)
        fill(program, 4)
        assert_values(gloo.read_pixels(mode=mode, out_type="float"), mode, "float",
                      DEPTH[0] if mode == "depth" else STENCIL[0])


@pytest.mark.parametrize("mode", ["depth", "stencil"])
def test_selected_sample_capture_recreates_bindings_after_resize_and_device_recovery(mode):
    with scene() as (canvas, program, _):
        fill(program, 4)
        expected = DEPTH[0] if mode == "depth" else STENCIL[0]
        assert_values(gloo.read_pixels(mode=mode, out_type="float"), mode, "float", expected)
        canvas.size = (16, 10)
        fill(program, 4, (16, 10))
        resized = gloo.read_pixels(mode=mode, out_type="float")
        assert resized.shape == (10, 16, 1)
        assert_values(resized, mode, "float", expected)
        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device();canvas.set_current()
        fill(program, 4, (16, 10))
        assert_values(gloo.read_pixels(mode=mode, out_type="float"), mode, "float", expected)
        assert _dawn.probe()["device_generation"] > generation
