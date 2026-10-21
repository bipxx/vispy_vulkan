"""Early probe: presentation pass, three submit counters, resident pan."""

import numpy as np
import pytest

from vispy import app, gloo
from vispy import _dawn

pytestmark = pytest.mark.gpu


def test_resident_pan_has_three_submit_counters_and_no_reupload():
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    texture = np.zeros((8, 8, 4), np.uint8)
    texture[..., 0] = 255
    texture[..., 3] = 255
    with canvas:
        program = gloo.Program(
            """
            attribute vec2 a_position;
            attribute vec2 a_texcoord;
            uniform vec2 u_pan;
            varying vec2 v_texcoord;
            void main() {
                v_texcoord = a_texcoord;
                gl_Position = vec4(a_position + u_pan, 0.0, 1.0);
            }
            """,
            """
            uniform sampler2D u_texture;
            varying vec2 v_texcoord;
            void main() { gl_FragColor = texture2D(u_texture, v_texcoord); }
            """,
        )
        program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program["a_texcoord"] = gloo.VertexBuffer(np.array([[0, 0], [1, 0], [0, 1]], np.float32))
        program["u_texture"] = gloo.Texture2D(texture, interpolation="nearest")
        program["u_pan"] = (0, 0)
        program.draw("triangles")
        _dawn.present(canvas._backend._dawn_canvas_id)
        before = _dawn.probe()
        program["u_pan"] = (0.01, 0)
        program.draw("triangles")
        _dawn.present(canvas._backend._dawn_canvas_id)
        after = _dawn.probe()
    print("application_presents", after["application_presents"])
    print("dawn_queue_submits", after["dawn_queue_submits"])
    print("vk_queue_submits", after["vk_queue_submits"])
    print("presentation_passes", after["presentation_passes"])
    print("texture_uploads", before["texture_uploads"], after["texture_uploads"])
    assert after["application_presents"] >= 1
    assert after["dawn_queue_submits"] >= 1
    assert after["vk_queue_submits"] >= 1
    assert after["vk_queue_submits"] == _dawn.layer_vk_submit_count()
    assert after["presentation_passes"] >= 1
    assert after["texture_uploads"] == before["texture_uploads"]
    assert after["finish_calls"] == before["finish_calls"]


def test_presentation_y_flip_is_bgra_of_the_color_target():
    canvas = app.Canvas(app="dawn_headless", size=(4, 3), show=False)

    def draw(event):
        gloo.set_clear_color((0, 0, 0, 1))
        gloo.clear()
        program = gloo.Program(
            "attribute vec2 a_position; void main() { gl_Position = vec4(a_position, 0.0, 1.0); }",
            "void main() { gl_FragColor = vec4(gl_FragCoord.y / 3.0, 0.0, 1.0 - gl_FragCoord.y / 3.0, 1.0); }",
        )
        program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program.draw("triangles")

    canvas.events.draw.connect(draw)
    canvas.set_current()
    canvas.events.draw()
    cid = canvas._backend._dawn_canvas_id
    _dawn.present(cid)
    color = np.array(_dawn.read_pixels(cid, 0, 0, 4, 3, True))
    presented = np.array(_dawn.read_presented(cid, 0, 0, 4, 3))
    rgba = presented.copy()
    rgba[..., 0] = presented[..., 2]
    rgba[..., 2] = presented[..., 0]
    print("presentation flip", color[0, 0].tolist(), presented[0, 0].tolist(), "match", np.array_equal(rgba, color))
    assert color[0, 0, 0] != color[-1, 0, 0]
    assert np.array_equal(rgba, color)
    assert "presentation flip format=bgra8unorm" in "\n".join(_dawn.debug_trace())
