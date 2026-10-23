"""Literal floating sampler-array resources, retained snapshots and recovery."""
from contextlib import contextmanager

import numpy as np
import pytest

from vispy import app, gloo

VERTEX = "attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}"
FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)


def pixels(color):
    return np.tile(np.asarray(color, np.uint8), (2, 2, 1))


def test_public_sampler_array_elements_emit_distinct_texture_binding_names():
    p = gloo.Program(VERTEX, "uniform sampler2D images[2];void main(){gl_FragColor=texture2D(images[0],vec2(.5));}")
    a = gloo.Texture2D(pixels([255, 0, 0, 255]))
    b = gloo.Texture2D(pixels([0, 255, 0, 255]))
    try:
        p["images[0]"] = a
        p["images[1]"] = b
        commands = [command for command in p.glir._shared._commands if command[0] == "TEXTURE"]
        assert commands == [("TEXTURE", p.id, "images[0]", a.id), ("TEXTURE", p.id, "images[1]", b.id)]
    finally:
        p.delete(); a.delete(); b.delete()


@contextmanager
def scene(fragment):
    from vispy import _dawn
    canvas = app.Canvas(app="dawn_headless", size=(16, 8), show=False)
    owned = []
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 16, 8)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
        source = gloo.VertexBuffer(FULL)
        p = gloo.Program(VERTEX, fragment)
        p["position"] = source
        a = gloo.Texture2D(pixels([255, 0, 0, 255]), interpolation="nearest")
        b = gloo.Texture2D(pixels([0, 255, 0, 255]), interpolation="nearest")
        p["images[0]"] = a; p["images[1]"] = b
        owned.extend((source, a, b, p))
        yield canvas, p, a, b, owned
    finally:
        canvas.set_current()
        for obj in reversed(owned):
            obj.delete()
        canvas.context.flush_commands()
        canvas.close()
        _dawn.process_events()
        after = _dawn.probe()
        assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
        assert _dawn.device_info()["backend"] == "Vulkan"


def split_fragment(helper=False):
    read = "sample_image" if helper else "texture2D"
    function = "vec4 sample_image(sampler2D image,vec2 uv){return texture2D(image,uv);}" if helper else ""
    return f"""uniform sampler2D images[2];{function}
    void main(){{vec4 a={read}(images[0],vec2(.5));vec4 b={read}(images[1],vec2(.5));
    gl_FragColor=gl_FragCoord.x<8.0?a:b;}}"""


def draw(p):
    gloo.set_clear_color((0, 0, 0, 1));gloo.clear(color=True, depth=False, stencil=False)
    p.draw("triangles")
    return gloo.read_pixels()


@pytest.mark.gpu
@pytest.mark.parametrize("helper", [False, True])
def test_literal_elements_sample_distinct_textures_directly_and_through_helpers(helper):
    with scene(split_fragment(helper)) as (_, p, a, b, owned):
        image = draw(p)
        assert np.all(image[:, :8] == [255, 0, 0, 255])
        assert np.all(image[:, 8:] == [0, 255, 0, 255])


@pytest.mark.gpu
def test_queued_array_texture_mutations_and_deletion_keep_each_draws_captured_revision():
    fragment = """uniform sampler2D images[2];uniform float weight;
    void main(){vec4 a=texture2D(images[0],vec2(.5));vec4 b=texture2D(images[1],vec2(.5));gl_FragColor=mix(a,b,weight);}"""
    with scene(fragment) as (_, p, a, b, owned):
        gloo.set_clear_color((0, 0, 0, 1));gloo.clear(color=True, depth=False, stencil=False)
        gloo.set_viewport(0, 0, 8, 8);p["weight"] = 0.;p.draw("triangles")
        a.set_data(pixels([0, 0, 255, 255]));b.set_data(pixels([255, 255, 0, 255]))
        gloo.set_viewport(8, 0, 8, 8);p["weight"] = 1.;p.draw("triangles")
        b.delete();owned.remove(b)
        image = gloo.read_pixels((0, 0, 16, 8))
        assert image.shape == (8, 16, 4), "snapshot checks require both viewport tiles"
        assert np.all(image[:, :8] == [255, 0, 0, 255]), "earlier array element observed a later revision"
        assert np.all(image[:, 8:] == [255, 255, 0, 255]), "captured array element did not survive deletion"


@pytest.mark.gpu
def test_array_element_rebinding_and_device_recovery_keep_independent_resources():
    from vispy import _dawn
    with scene(split_fragment()) as (canvas, p, a, b, owned):
        initial = draw(p)
        assert np.all(initial[:, :8] == [255, 0, 0, 255])
        replacement = gloo.Texture2D(pixels([0, 0, 255, 255]), interpolation="nearest")
        owned.append(replacement);p["images[0]"] = replacement
        b.set_data(pixels([255, 255, 0, 255]))
        revised = draw(p)
        assert np.all(revised[:, :8] == [0, 0, 255, 255])
        assert np.all(revised[:, 8:] == [255, 255, 0, 255])
        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device();canvas.set_current();gloo.set_viewport(0, 0, 16, 8)
        recovered = draw(p)
        assert _dawn.probe()["device_generation"] > generation
        np.testing.assert_array_equal(recovered, revised)
