"""Existing one-level LOD/gradient semantics, evaluated operands and filtering.

No test invents a mip payload: public textures have one actual level and only
nearest/linear filters. Multi-level storage remains a separate unqualified API.
"""
from contextlib import contextmanager

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu
FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
LINE = np.array([[-.75, 0], [.75, 0]], np.float32)
COMMON = """uniform float requested_level;uniform float gradient;float counter=0.;
float next_level(){counter+=1.;return requested_level;}
vec2 next_dx(){counter+=2.;return vec2(gradient,0.);}
vec2 next_dy(){counter+=3.;return vec2(0.,gradient);}
"""


@contextmanager
def scene(vertex, fragment, positions, texture):
    canvas = app.Canvas(app="dawn_headless", size=(16, 8), show=False)
    source = p = None
    try:
        canvas.set_current();gloo.set_viewport(0, 0, 16, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False,
                       line_smooth=False)
        source = gloo.VertexBuffer(positions);p = gloo.Program(vertex, fragment)
        p["position"] = source;p["image"] = texture
        p["requested_level"] = 2.;p["gradient"] = 2.
        yield canvas, p
    finally:
        canvas.set_current()
        if p is not None:p.delete()
        if source is not None:source.delete()
        texture.delete();canvas.context.flush_commands();canvas.close();_dawn.process_events()
        after = _dawn.probe()
        assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
        assert after["line_resource_pool_busy_slots"] == 0
        assert _dawn.device_info()["backend"] == "Vulkan"


def read(p, mode="triangles"):
    gloo.set_clear_color((0, 0, 0, 1));gloo.clear(color=True, depth=False, stencil=False)
    if mode == "lines":gloo.set_line_width(3)
    p.draw(mode)
    return gloo.read_pixels()


def near_byte(values, expected):
    assert np.max(np.abs(values.astype(np.int16) - expected)) <= 1


@pytest.mark.parametrize("function", ["textureLod", "texture2DLod", "textureGrad", "texture2DGradEXT"])
@pytest.mark.parametrize("filters", [("nearest", "linear"), ("linear", "nearest")])
@pytest.mark.parametrize("minifying", [False, True])
def test_finite_float_lod_gradient_operands_execute_once_and_select_the_actual_filter(function, filters, minifying):
    gradients = "Grad" in function
    args = "next_dx(),next_dy()" if gradients else "next_level()"
    fragment = "uniform sampler2D image;" + COMMON + f"""
    void main(){{vec4 value={function}(image,vec2(.5),{args});
    gl_FragColor=vec4(value.r,counter/8.,0,1);}}"""
    vertex = "attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}"
    data = np.array([[[0, 0, 0, 255], [255, 255, 255, 255]],
                     [[0, 0, 0, 255], [255, 255, 255, 255]]], np.uint8)
    texture = gloo.Texture2D(data, interpolation=filters)
    with scene(vertex, fragment, FULL, texture) as (_, p):
        p["requested_level"] = 2. if minifying else -2.
        p["gradient"] = 2. if minifying else .125
        image = read(p)
        selected_filter = filters[0] if minifying else filters[1]
        near_byte(image[..., 0], 255 if selected_filter == "nearest" else 128)
        near_byte(image[..., 1], 159 if gradients else 32)
        assert np.all(image[..., 2] == 0) and np.all(image[..., 3] == 255)


def integer_texture(signed):
    if signed:
        data = np.array([[-2147483648, -1], [0, -16777217]], np.int32)
    else:
        data = np.array([[0, 4294967295], [1, 2147483648]], np.uint32)
    return gloo.Texture2D(data, internalformat="r32i" if signed else "r32ui", interpolation="nearest")


@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("gradients", [False, True])
@pytest.mark.parametrize("route", ["fragment", "vertex", "line-endpoint"])
def test_integer_nearest_actual_single_level_lod_gradient_preserves_operands_in_every_route(signed, gradients, route):
    sampler = "isampler2D" if signed else "usampler2D"
    vector = "ivec4" if signed else "uvec4"
    mask = "255" if signed else "255u"
    function = "textureGrad" if gradients else "textureLod"
    args = "next_dx(),next_dy()" if gradients else "next_level()"
    sample = f"{vector} value={function}(image,vec2(.75,.25),{args});"
    red = f"float(value.r&{mask})/255."
    if route == "fragment":
        vertex = "attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}"
        fragment = (f"uniform {sampler} image;" + COMMON + "void main(){" + sample +
                    f"gl_FragColor=vec4({red},counter/8.,0,1);}}")
    else:
        vertex = (f"attribute vec2 position;uniform {sampler} image;out vec2 sampled;" +
                  COMMON + "void main(){" + sample +
                  f"sampled=vec2({red},counter/8.);gl_Position=vec4(position,0,1);}}")
        fragment = "in vec2 sampled;void main(){gl_FragColor=vec4(sampled,0,1);}"
    texture = integer_texture(signed)
    with scene(vertex, fragment, LINE if route == "line-endpoint" else FULL, texture) as (_, p):
        image = read(p, "lines" if route == "line-endpoint" else "triangles")
        if route == "line-endpoint":
            colored = image[..., 0] > 0
            assert 12 < np.count_nonzero(colored) < 80
            assert np.all(image[[0, -1], :, :3] == 0)
            image = image[colored]
        near_byte(image[..., 0], 255)
        near_byte(image[..., 1], 159 if gradients else 32)
        assert np.all(image[..., 2] == 0) and np.all(image[..., 3] == 255)


@pytest.mark.parametrize("gradients", [False, True])
def test_generated_integer_endpoint_captures_wrap_policy_and_rebuilds_after_recovery(gradients):
    function = "textureGrad" if gradients else "textureLod"
    args = "next_dx(),next_dy()" if gradients else "next_level()"
    vertex = ("attribute vec2 position;uniform usampler2D image;out vec2 sampled;" + COMMON +
              f"void main(){{uvec4 value={function}(image,vec2(-.25,.25),{args});" +
              "sampled=vec2(float(value.r)/255.,counter/8.);gl_Position=vec4(position,0,1);}")
    fragment = "in vec2 sampled;void main(){gl_FragColor=vec4(sampled,0,1);}"
    texture = gloo.Texture2D(np.array([[17, 223], [31, 251]], np.uint32),
                            internalformat="r32ui", interpolation="nearest", wrapping="repeat")
    with scene(vertex, fragment, LINE, texture) as (canvas, p):
        repeated = read(p, "lines")
        covered = repeated[..., 1] > 0
        assert np.any(covered)
        near_byte(repeated[covered, 0], 223)
        texture.wrapping = "clamp_to_edge"
        clamped = read(p, "lines")
        covered = clamped[..., 1] > 0
        assert np.any(covered)
        near_byte(clamped[covered, 0], 17)
        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device();canvas.set_current();gloo.set_viewport(0, 0, 16, 8)
        recovered = read(p, "lines")
        np.testing.assert_array_equal(recovered, clamped)
        assert _dawn.probe()["device_generation"] > generation
