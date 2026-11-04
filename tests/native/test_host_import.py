# SPDX-License-Identifier: AGPL-3.0-only
"""A full texture upload copies straight from its CPU shadow (plan P5; user, 2026-10-31: D26).

A DATA payload of at least 1 MiB is captured into a page-aligned host block, which a full update makes the texture's
CPU shadow. When the device has Dawn's HostMappedPointer feature, a full upload that needs no conversion and whose
rows are a multiple of 256 bytes copies from that block through an imported buffer, so it makes no staging copy. The
frame's Ticket holds the block until its copy has retired, and a block is written only while nothing else holds it.
Imports pin host memory, so they stay within a limit by releasing idle ones. Every other upload keeps the staging
path, and VISPY_DAWN_HOST_IMPORT=0 turns imports off. Each texture is drawn texel for texel into either half of a
framebuffer twice its width and read back; the expected counters depend on whether the device has the feature.
"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from vispy import app, gloo, _dawn

pytestmark = pytest.mark.gpu
N = 512  # 512x512 RGBA8: 1 MiB, rows of 2048 bytes
FRAMES = 4
COUNTERS = ("host_import_copies", "host_import_fallbacks", "host_imports", "host_import_evictions")
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
QUAD = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32)


def headless():
    return app.Canvas(app="dawn_headless", size=(16, 16), show=False)


def changes(before, after, names=COUNTERS):
    return {name: after[name] - before[name] for name in names}


def image(rng, size=N):
    return rng.integers(0, 256, (size, size, 4), dtype=np.uint8)


def imports():
    return bool(_dawn.device_info()["host_mapped_pointer"])


def retire():
    """Retire completed frames, so that their Tickets release what they hold."""
    probe = _dawn.probe()
    assert probe["pending_tickets"] == 0
    return probe


def patched(data, patch, row, column):
    result = data.copy()
    result[row:row + patch.shape[0], column:column + patch.shape[1]] = patch
    return result


class Halves:
    """A texture drawn texel for texel into either half of a framebuffer twice its width."""

    def __init__(self, data):
        self.size = data.shape[0]
        self.texture = gloo.Texture2D(data, interpolation="nearest")
        self.fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(self.size, 2 * self.size, 4)))
        self.program = gloo.Program(VERTEX, FRAGMENT)
        self.program["a_position"] = QUAD
        self.program["u_texture"] = self.texture

    def draw(self, half):
        gloo.set_viewport(half * self.size, 0, self.size, self.size)
        self.program.draw("triangle_strip")

    def read(self):
        with self.fbo:
            pixels = gloo.read_pixels(viewport=(0, 0, 2 * self.size, self.size))
        pixels = pixels[::-1]  # read_pixels puts the top row first; the texture's first row is drawn at the bottom
        return pixels[:, :self.size], pixels[:, self.size:]

    def frame(self, data, half):
        """Upload data in full, draw it into one half, read it back, and retire the frame."""
        self.texture.set_data(data)
        with self.fbo:
            self.draw(half)
        pixels = self.read()[half]
        retire()
        return pixels


def allocations():
    probe = _dawn.probe()
    assert "vk_memory_allocate_calls" in probe, "the Vulkan memory telemetry layer is required"
    return probe["buffer_allocations"], probe["vk_memory_allocate_calls"]


def test_full_uploads_copy_from_their_shadow_and_warm_uploads_allocate_nothing():
    rng = np.random.default_rng(2651)
    canvas = headless()
    with canvas:
        scene = Halves(image(rng))
        for index in range(3):  # warm the blocks, their imports and the readback path
            data = image(rng)
            assert np.array_equal(scene.frame(data, index % 2), data), index
        before, start = _dawn.probe(), allocations()
        for index in range(FRAMES):
            data = image(rng)
            assert np.array_equal(scene.frame(data, index % 2), data), index
        after, uploaded = _dawn.probe(), allocations()
        half = (FRAMES - 1) % 2
        for index in range(FRAMES):  # the same frames without an upload, each drawing and reading the last upload
            with scene.fbo:
                scene.draw(half)
            assert np.array_equal(scene.read()[half], data), index
            retire()
        read_only = allocations()
        available = imports()
    canvas.close()
    assert changes(before, after) == {"host_import_copies": FRAMES if available else 0,
                                      "host_import_fallbacks": 0 if available else FRAMES,
                                      "host_imports": 0, "host_import_evictions": 0}
    assert after["host_import_bytes"] - before["host_import_bytes"] == (FRAMES * N * N * 4 if available else 0)
    assert [(uploaded[i] - start[i]) - (read_only[i] - uploaded[i]) for i in range(2)] == [0, 0]


@pytest.mark.parametrize("size", [520, 1040])  # rows of 2080 and 4160 bytes; queue.WriteTexture, then a pooled lease
def test_rows_that_are_not_a_multiple_of_256_bytes_upload_through_staging(size):
    rng = np.random.default_rng(2652 + size)
    canvas = headless()
    with canvas:
        scene = Halves(image(rng, size))
        scene.read()
        before = retire()
        for index in range(FRAMES):
            data = image(rng, size)
            assert np.array_equal(scene.frame(data, index % 2), data), index
        after = _dawn.probe()
    canvas.close()
    assert changes(before, after) == {"host_import_copies": 0, "host_import_fallbacks": FRAMES, "host_imports": 0,
                                      "host_import_evictions": 0}


def test_a_patch_while_a_full_upload_is_in_flight_copies_its_block():
    # Completions are held, so the frame that copies the full update from its block stays in flight. The patch's
    # revision takes the settled shadow, which is that block: writing it in place could change what the copy reads.
    rng = np.random.default_rng(2653)
    data, update, patch = image(rng), image(rng), rng.integers(0, 256, (8, 16, 4), dtype=np.uint8)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        scene.read()
        retire()
        _dawn.diagnostic_submission_controls(True, "")
        try:
            scene.texture.set_data(update)
            with scene.fbo:
                scene.draw(0)
            gloo.flush()
            before = _dawn.probe()
            assert before["pending_tickets"] >= 1  # completion delivery is held, not a timing guess
            scene.texture.set_data(patch, offset=(8, 24))
            with scene.fbo:
                scene.draw(1)
            gloo.flush()
            after = _dawn.probe()
        finally:
            _dawn.diagnostic_submission_controls(False, "")
        left, right = scene.read()
        available = imports()
    canvas.close()
    assert np.array_equal(left, update)
    assert np.array_equal(right, patched(update, patch, 8, 24))
    names = ("texture_copy_on_write", "texture_shadow_moves", "texture_copy_on_write_bytes")
    assert changes(before, after, names) == {"texture_copy_on_write": 1, "texture_shadow_moves": 1,
                                             "texture_copy_on_write_bytes": N * N * 4 if available else 0}


def test_a_device_loss_rebuilds_a_texture_from_its_block_and_imports_resume():
    rng = np.random.default_rng(2654)
    data = image(rng)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        with scene.fbo:
            scene.draw(0)  # uploads the texture from its block
        assert np.array_equal(scene.read()[0], data)
        retire()
        _dawn.lose_device()  # the rebuild uploads the live revision from its block again
        with scene.fbo:
            scene.draw(1)
        assert np.array_equal(scene.read()[1], data)
        retire()
        before = _dawn.probe()
        for index in range(FRAMES):
            update = image(rng)
            assert np.array_equal(scene.frame(update, index % 2), update), index
        after = _dawn.probe()
        available = imports()
    canvas.close()
    moved = changes(before, after)
    assert moved["host_import_copies"] + moved["host_import_fallbacks"] == FRAMES
    assert moved["host_import_copies"] >= (1 if available else 0) and (available or moved["host_import_copies"] == 0)


def test_the_import_limit_releases_idle_imports():
    rng = np.random.default_rng(2655)
    limit = 3 << 19  # 1.5 MiB: one 1 MiB block imported at a time
    canvas = headless()
    with canvas:
        first, second = Halves(image(rng)), Halves(image(rng))
        first.read()
        second.read()
        retire()
        _dawn.diagnostic_host_import_limit(limit)
        try:
            before = _dawn.probe()
            for index in range(FRAMES):
                for scene in (first, second):
                    data = image(rng)
                    assert np.array_equal(scene.frame(data, index % 2), data), index
                    assert _dawn.probe()["host_import_pinned_bytes"] <= limit
            after = _dawn.probe()
        finally:
            _dawn.diagnostic_host_import_limit(0)
        available = imports()
    canvas.close()
    moved = changes(before, after)
    assert moved["host_import_copies"] + moved["host_import_fallbacks"] == 2 * FRAMES
    if available:
        assert moved["host_import_copies"] >= 1 and moved["host_import_evictions"] >= 1
    else:
        assert moved["host_import_copies"] == 0


BUFFER_VERTEX = """
attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
"""
BUFFER_FRAGMENT = """
void main() { gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0); }
"""
RED, BLACK = [255, 0, 0, 255], [0, 0, 0, 255]


def test_payloads_of_a_vertex_buffer_and_a_patch_from_blocks_land():
    rng = np.random.default_rng(2656)
    vertices = np.zeros((1 << 17, 2), np.float32)  # 1 MiB; the first six vertices cover the target
    vertices[:6] = [[-1, -1], [1, -1], [-1, 1], [-1, 1], [1, -1], [1, 1]]
    left_only = np.zeros_like(vertices)
    left_only[:6] = [[-1, -1], [0, -1], [-1, 1], [-1, 1], [0, -1], [0, 1]]
    data, patch = image(rng, 1024), rng.integers(0, 256, (512, 512, 4), dtype=np.uint8)  # the patch is 1 MiB
    canvas = headless()
    with canvas:
        target = gloo.FrameBuffer(color=gloo.Texture2D(shape=(64, 64, 4)))
        program = gloo.Program(BUFFER_VERTEX, BUFFER_FRAGMENT)
        buffer = gloo.VertexBuffer(vertices)
        program["a_position"] = buffer
        indices = gloo.IndexBuffer(np.arange(6, dtype=np.uint32))
        frames = []
        for update in (None, left_only):
            if update is not None:
                buffer.set_data(update)
            with target:
                gloo.set_viewport(0, 0, 64, 64)
                gloo.clear(color="black")
                program.draw("triangles", indices)
                frames.append(gloo.read_pixels(viewport=(0, 0, 64, 64)))
        scene = Halves(data)
        scene.read()
        scene.texture.set_data(patch, offset=(256, 128))
        with scene.fbo:
            scene.draw(1)
        right = scene.read()[1]
    canvas.close()
    assert (frames[0] == RED).all()
    assert (frames[1][:, :32] == RED).all() and (frames[1][:, 32:] == BLACK).all()
    assert np.array_equal(right, patched(data, patch, 256, 128))


CHILD = r"""
import json, sys
sys.path[:0] = json.loads(sys.argv[1])
import numpy as np
from vispy import app, gloo, _dawn
assert _dawn.__file__ == sys.argv[2], (_dawn.__file__, sys.argv[2])
frames = int(sys.argv[3])
rng = np.random.default_rng(2657)
canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
with canvas:
    texture = gloo.Texture2D(rng.integers(0, 256, (512, 512, 4), dtype=np.uint8), interpolation="nearest")
    fbo = gloo.FrameBuffer(color=texture)
    with fbo:
        gloo.read_pixels(viewport=(0, 0, 512, 512))
    before = _dawn.probe()
    ok = True
    for _ in range(frames):
        data = rng.integers(0, 256, (512, 512, 4), dtype=np.uint8)
        texture.set_data(data)
        with fbo:
            ok = ok and bool(np.array_equal(gloo.read_pixels(viewport=(0, 0, 512, 512)), data[::-1]))
    after = _dawn.probe()
    info = _dawn.device_info()
canvas.close()
print(json.dumps({"host_mapped_pointer": bool(info["host_mapped_pointer"]),
                  "copies": after["host_import_copies"] - before["host_import_copies"],
                  "fallbacks": after["host_import_fallbacks"] - before["host_import_fallbacks"], "ok": ok}))
"""


def test_imports_can_be_turned_off():
    env = dict(os.environ, VISPY_DAWN_HOST_IMPORT="0")
    child = subprocess.run([sys.executable, "-B", "-c", CHILD, json.dumps(sys.path), _dawn.__file__, str(FRAMES)],
                           env=env, capture_output=True, text=True, timeout=120)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout.splitlines()[-1]) == {"host_mapped_pointer": False, "copies": 0,
                                                         "fallbacks": FRAMES, "ok": True}
