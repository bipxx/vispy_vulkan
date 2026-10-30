"""Full texture uploads copy through pooled mapped staging buffers (perf-profile-261, step C).

Every frame's bytes must reach the texture, whether the upload takes a pooled buffer (at least 4 MiB) or keeps
queue.WriteTexture (smaller); and once warm, uploads must not allocate memory of their own. Each frame reads the
texture back through a framebuffer, which allocates its own readback buffer, so the uploads' share is the
difference between frames with an upload and the same number of frames that only read.
"""
import numpy as np
import pytest

from vispy import app, gloo, _dawn

pytestmark = pytest.mark.gpu
FRAMES = 5


def counts():
    probe = _dawn.probe()
    assert "vk_memory_allocate_calls" in probe, "the Vulkan memory telemetry layer is required"
    return probe["buffer_allocations"], probe["vk_memory_allocate_calls"]


@pytest.mark.parametrize("size", [1536, 256])  # 9 MiB, pooled; 256 KiB, WriteTexture
def test_every_full_upload_lands_and_warm_uploads_allocate_nothing(size):
    rng = np.random.default_rng(261 + size)
    canvas = app.Canvas(app="dawn_headless", size=(64, 64), show=False)
    with canvas:
        texture = gloo.Texture2D(rng.integers(0, 256, (size, size, 4), dtype=np.uint8))
        fbo = gloo.FrameBuffer(color=texture)

        def frame(upload):
            data = rng.integers(0, 256, (size, size, 4), dtype=np.uint8) if upload else None
            if upload:
                texture.set_data(data)
            with fbo:
                image = gloo.read_pixels(viewport=(0, 0, size, size))
            return data, image

        for _ in range(3):  # warm the pool and the readback path
            frame(True)
        start = counts()
        for index in range(FRAMES):
            data, image = frame(True)
            assert np.array_equal(image, data[::-1]), index  # read_pixels puts the top row first
        uploaded = counts()
        last = image
        for index in range(FRAMES):
            _, image = frame(False)
            assert np.array_equal(image, last), index
        read_only = counts()
    canvas.close()
    upload_share = [(uploaded[i] - start[i]) - (read_only[i] - uploaded[i]) for i in range(2)]
    print("size", size, "allocations with uploads", [uploaded[i] - start[i] for i in range(2)],
          "read only", [read_only[i] - uploaded[i] for i in range(2)], "uploads' share", upload_share)
    assert upload_share == [0, 0]


VERTEX = """
attribute vec2 a_position;
varying vec2 v_texcoord;
void main() { v_texcoord = (a_position + 1.0) / 2.0; gl_Position = vec4(a_position, 0.0, 1.0); }
"""
FRAGMENT = """
uniform sampler2D u_texture;
varying vec2 v_texcoord;
void main() { gl_FragColor = texture2D(u_texture, v_texcoord); }
"""


def test_a_staged_upload_lost_with_its_encoder_is_uploaded_again():
    # A pooled staging copy is recorded in the frame's encoder. When that encoder is never submitted, the texture
    # must stay pending, so its next use uploads it again instead of reading the texture's previous contents.
    rng = np.random.default_rng(262)
    canvas = app.Canvas(app="dawn_headless", size=(64, 64), show=False)
    with canvas:
        texture = gloo.Texture2D(rng.integers(0, 256, (1536, 1536, 4), dtype=np.uint8))  # 9 MiB, pooled
        fbo = gloo.FrameBuffer(color=texture)
        with fbo:
            gloo.read_pixels(viewport=(0, 0, 1536, 1536))  # the texture holds its first contents
        program = gloo.Program(VERTEX, FRAGMENT)
        program["a_position"] = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32)
        program["u_texture"] = texture
        data = rng.integers(0, 256, (1536, 1536, 4), dtype=np.uint8)
        texture.set_data(data)
        _dawn.diagnostic_submission_controls(False, "before-submit")
        try:
            with pytest.raises(RuntimeError, match="diagnostic submission failure: before-submit"):
                program.draw("triangle_strip")
                gloo.flush()
        finally:
            _dawn.diagnostic_submission_controls(False, "")
        with fbo:
            image = gloo.read_pixels(viewport=(0, 0, 1536, 1536))
    canvas.close()
    assert np.array_equal(image, data[::-1])  # read_pixels puts the top row first
