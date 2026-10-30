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
