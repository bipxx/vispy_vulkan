# SPDX-License-Identifier: AGPL-3.0-only
"""Copy-on-write copies a texture's CPU shadow only when it must (plan P3; user, 2026-10-30).

A texture or vertex buffer updated between two draws of one frame is copied on write, because the first draw still
holds the current revision. When that revision is settled (current on the GPU, nothing pending), its holders read
only its GPU texture, so its shadow moves to the new revision instead of being copied, and an entire update copies
nothing. A device loss rebuilds a live revision from its own pixels, so a revision whose shadow moved is never read
again. Each texture test samples a texture texel for texel into the left and then the right half of one framebuffer
in one batch, so the first draw is still pending when the update arrives. Textures are 128x128: at 64x64, a separate
bug that predates P3 makes a small staged patch read as zeros when a 16 KiB texture upload follows it in the same
frame, with or without copy-on-write (run perf-profile-261, p3_debug_variants.py).
"""
import numpy as np
import pytest

from vispy import app, gloo, _dawn

pytestmark = pytest.mark.gpu
N = 128
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
TEXTURE_COUNTERS = ("texture_copy_on_write", "texture_shadow_moves", "texture_copy_on_write_bytes")
BUFFER_COUNTERS = ("buffer_copy_on_write", "buffer_copy_on_write_bytes")


def headless():
    return app.Canvas(app="dawn_headless", size=(16, 16), show=False)


def changes(before, after, names):
    return {name: after[name] - before[name] for name in names}


def image(rng):
    return rng.integers(0, 256, (N, N, 4), dtype=np.uint8)


class Halves:
    """A texture drawn texel for texel into either half of a framebuffer twice its width."""

    def __init__(self, data):
        self.texture = gloo.Texture2D(data, interpolation="nearest")
        self.fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(N, 2 * N, 4)))
        self.program = gloo.Program(VERTEX, FRAGMENT)
        self.program["a_position"] = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32)
        self.program["u_texture"] = self.texture

    def draw(self, half):
        gloo.set_viewport(half * N, 0, N, N)
        self.program.draw("triangle_strip")

    def read(self):
        with self.fbo:
            pixels = gloo.read_pixels(viewport=(0, 0, 2 * N, N))
        pixels = pixels[::-1]  # read_pixels puts the top row first; the texture's first row is drawn at the bottom
        return pixels[:, :N], pixels[:, N:]

    def settle(self):
        """Draw and read once, so the texture is uploaded and current, and no frame is left in flight."""
        with self.fbo:
            self.draw(0)
        self.read()
        probe = _dawn.probe()  # retires completed frames first
        assert probe["pending_tickets"] == 0
        return probe


def patched(data, patch, row, column):
    result = data.copy()
    result[row:row + patch.shape[0], column:column + patch.shape[1]] = patch
    return result


def test_a_patch_between_two_draws_moves_the_shadow_instead_of_copying_it():
    rng = np.random.default_rng(311)
    data, patch = image(rng), rng.integers(0, 256, (8, 16, 4), dtype=np.uint8)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        before = scene.settle()
        with scene.fbo:
            scene.draw(0)
            scene.texture.set_data(patch, offset=(8, 24))
            scene.draw(1)
        left, right = scene.read()
        after = _dawn.probe()
    canvas.close()
    assert np.array_equal(left, data)
    assert np.array_equal(right, patched(data, patch, 8, 24))
    assert changes(before, after, TEXTURE_COUNTERS) == {
        "texture_copy_on_write": 1, "texture_shadow_moves": 1, "texture_copy_on_write_bytes": 0}


def test_an_entire_update_between_two_draws_copies_no_shadow():
    rng = np.random.default_rng(312)
    data, update = image(rng), image(rng)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        before = scene.settle()
        with scene.fbo:
            scene.draw(0)
            scene.texture.set_data(update)
            scene.draw(1)
        left, right = scene.read()
        after = _dawn.probe()
    canvas.close()
    assert np.array_equal(left, data)
    assert np.array_equal(right, update)
    assert changes(before, after, TEXTURE_COUNTERS) == {
        "texture_copy_on_write": 1, "texture_shadow_moves": 1, "texture_copy_on_write_bytes": 0}


@pytest.mark.parametrize("entire", [False, True])
def test_an_update_of_a_revision_not_yet_uploaded_copies_only_a_patched_shadow(entire):
    rng = np.random.default_rng(313)
    data, first = image(rng), rng.integers(0, 256, (8, 16, 4), dtype=np.uint8)
    second = image(rng) if entire else rng.integers(0, 256, (16, 8, 4), dtype=np.uint8)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        before = scene.settle()
        with scene.fbo:
            scene.texture.set_data(first, offset=(0, 0))  # nothing else holds the texture: patched in place
            scene.draw(0)  # holds the revision with its patch not yet uploaded
            scene.texture.set_data(second, offset=None if entire else (40, 8))
            scene.draw(1)
        left, right = scene.read()
        after = _dawn.probe()
    canvas.close()
    assert np.array_equal(left, patched(data, first, 0, 0))
    assert np.array_equal(right, second if entire else patched(patched(data, first, 0, 0), second, 40, 8))
    assert changes(before, after, TEXTURE_COUNTERS) == {
        "texture_copy_on_write": 1, "texture_shadow_moves": 0, "texture_copy_on_write_bytes": 0 if entire else N * N * 4}


def test_a_moved_shadow_survives_a_device_loss_before_its_frame_is_submitted():
    rng = np.random.default_rng(314)
    data, patch = image(rng), rng.integers(0, 256, (8, 16, 4), dtype=np.uint8)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        scene.settle()
        with scene.fbo:
            scene.draw(0)
            scene.texture.set_data(patch, offset=(8, 24))  # the shadow moves; the patch waits for this frame
            scene.draw(1)
        _dawn.diagnostic_submission_controls(False, "before-submit")
        try:
            with pytest.raises(RuntimeError, match="diagnostic submission failure: before-submit"):
                gloo.flush()
        finally:
            _dawn.diagnostic_submission_controls(False, "")
        _dawn.lose_device()  # rebuilds the patched revision, whose base gave it its shadow
        with scene.fbo:
            scene.draw(1)
        _, right = scene.read()
    canvas.close()
    assert np.array_equal(right, patched(data, patch, 8, 24))


def test_a_rejected_patch_returns_the_moved_shadow():
    rng = np.random.default_rng(315)
    data = image(rng)
    canvas = headless()
    with canvas:
        scene = Halves(data)
        scene.settle()
        with scene.fbo:
            scene.draw(0)
        # Three channels for a four-channel texture: the native DATA check rejects it after the shadow moved.
        scene.texture._glir.command("DATA", scene.texture.id, (0, 0), np.zeros((8, 8, 3), np.uint8))
        with pytest.raises(RuntimeError, match="channel count differs"):
            gloo.flush()
        _dawn.lose_device()  # the rebuild reads the live revision's shadow
        with scene.fbo:
            scene.draw(1)
        _, right = scene.read()
    canvas.close()
    assert np.array_equal(right, data)


BUFFER_VERTEX = """
attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
"""
BUFFER_FRAGMENT = """
void main() { gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0); }
"""
SQUARE = np.array([[-1, -1], [1, -1], [-1, 1], [-1, 1], [1, -1], [1, 1]], np.float32)  # two triangles
RED, BLACK = [255, 0, 0, 255], [0, 0, 0, 255]


@pytest.mark.parametrize("whole", [True, False])
def test_a_vertex_buffer_update_between_two_draws_copies_old_bytes_only_for_a_partial_update(whole):
    canvas = headless()
    with canvas:
        fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(N, 2 * N, 4)))
        vbo = gloo.VertexBuffer(SQUARE)
        program = gloo.Program(BUFFER_VERTEX, BUFFER_FRAGMENT)
        program["a_position"] = vbo

        def draw(half):
            gloo.set_viewport(half * N, 0, N, N)
            program.draw("triangles")

        def read():
            with fbo:
                pixels = gloo.read_pixels(viewport=(0, 0, 2 * N, N))[::-1]
            return pixels[:, :N], pixels[:, N:]

        with fbo:
            draw(0)
        read()
        before = _dawn.probe()
        assert before["pending_tickets"] == 0
        with fbo:
            gloo.clear(color=(0, 0, 0, 1))
            draw(0)
            if whole:
                vbo.set_data((SQUARE * [1, 0.5] - [0, 0.5]).astype(np.float32))  # the lower half
            else:
                vbo.set_subdata(np.zeros((3, 2), np.float32), offset=3)  # the second triangle collapses
            draw(1)
        left, right = read()
        after = _dawn.probe()
    canvas.close()
    assert (left == RED).all()
    if whole:
        assert (right[:N // 2] == RED).all() and (right[N // 2:] == BLACK).all()
    else:  # the first triangle, below the diagonal
        assert (right[0, 0] == RED).all() and (right[N - 1, N - 1] == BLACK).all()
    assert changes(before, after, BUFFER_COUNTERS) == {
        "buffer_copy_on_write": 1, "buffer_copy_on_write_bytes": 0 if whole else SQUARE.nbytes}
