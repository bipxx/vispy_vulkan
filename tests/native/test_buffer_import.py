# SPDX-License-Identifier: AGPL-3.0-only
"""A buffer upload copies straight from its payload's host block (plan P6; D26, extended to buffers by the user,
2026-10-31: "continue", to "Import buffer uploads the same way").

A whole update of a buffer with a payload of at least 1 MiB keeps the payload's host block as the buffer's bytes
instead of copying it. When the device has Dawn's HostMappedPointer feature, the GPU copies a revision whose size is
a multiple of 4 bytes from the block's import before the render pass that reads it, so the upload makes no staging
copy; the frame's Ticket holds the block until the copy has retired. A revision replaced while a frame still reads it
takes the GPU buffer of one that has retired, so a buffer streamed every frame allocates nothing once warm. Every
other upload keeps queue.WriteBuffer, and VISPY_DAWN_HOST_IMPORT=0 turns imports off. Cells are drawn one per pixel,
their colors from the streamed buffer, into either slot of a framebuffer two slots wide and read back; the expected
counters depend on whether the device has the feature.
"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from vispy import app, gloo, _dawn

pytestmark = pytest.mark.gpu
W, H = 256, 192  # cells per slot, one per pixel
CELLS = W * H
FRAMES = 4
COUNTERS = ("buffer_import_copies", "buffer_import_fallbacks", "buffer_shadow_transfers", "buffer_pool_reuses",
            "host_imports")
CELL = np.dtype([("a_cell", np.float32, 2), ("a_color", np.float32, 4)])  # 24 bytes: 1.125 MiB per instance buffer
VERTEX = np.dtype([("a_position", np.float32, 2), ("a_color", np.float32, 4)])
CORNERS = np.array([[0, 0], [1, 0], [0, 1], [0, 1], [1, 0], [1, 1]], np.float32)
XY = np.stack(np.meshgrid(np.arange(W), np.arange(H)), -1).reshape(-1, 2).astype(np.float32)  # cell c = (c % W, c // W)
SIZE = "vec2(%d.0, %d.0)" % (W, H)
INSTANCED = """
attribute vec2 a_corner;
attribute vec2 a_cell;
attribute vec4 a_color;
varying vec4 v_color;
void main() { gl_Position = vec4((a_cell + a_corner) / SIZE * 2.0 - 1.0, 0.0, 1.0); v_color = a_color; }
""".replace("SIZE", SIZE)
PER_VERTEX = """
attribute vec2 a_position;
attribute vec4 a_color;
varying vec4 v_color;
void main() { gl_Position = vec4(a_position / SIZE * 2.0 - 1.0, 0.0, 1.0); v_color = a_color; }
""".replace("SIZE", SIZE)
POINTS = """
attribute vec2 a_cell;
attribute vec4 a_color;
varying vec4 v_color;
void main() {
    gl_Position = vec4((a_cell + 0.5) / SIZE * 2.0 - 1.0, 0.0, 1.0);
    gl_PointSize = 1.0;
    v_color = a_color;
}
""".replace("SIZE", SIZE)
FRAGMENT = """
varying vec4 v_color;
void main() { gl_FragColor = v_color; }
"""


def headless():
    return app.Canvas(app="dawn_headless", size=(16, 16), show=False)


def changes(before, after, names=COUNTERS):
    return {name: after[name] - before[name] for name in names}


def levels(rng, count=CELLS):
    return rng.integers(0, 256, (count, 4), dtype=np.uint8)


def picture(colors):
    """The slot that cells of these colors draw, bottom row first."""
    return colors.reshape(H, W, 4)


def imports():
    return bool(_dawn.device_info()["host_mapped_pointer"])


def retire():
    """Retire completed frames, so that their Tickets release what they hold."""
    probe = _dawn.probe()
    assert probe["pending_tickets"] == 0
    return probe


def allocations():
    probe = _dawn.probe()
    assert "vk_memory_allocate_calls" in probe, "the Vulkan memory telemetry layer is required"
    return probe["buffer_allocations"], probe["vk_memory_allocate_calls"]


class Cells:
    """One cell per pixel, colored from a streamed buffer: instanced quads (the route of vispy's instanced markers,
    which napari draws), six vertices per cell, or points."""

    def __init__(self, route):
        self.route = route
        self.fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(H, 2 * W, 4)))
        if route == "instanced":
            self.program = gloo.Program(INSTANCED, FRAGMENT)
            self.program["a_corner"] = gloo.VertexBuffer(CORNERS)
        else:
            self.program = gloo.Program(PER_VERTEX if route == "vertices" else POINTS, FRAGMENT)
        self.buffer = gloo.VertexBuffer(self.payload(np.zeros((CELLS, 4), np.uint8)))
        for name in self.buffer.dtype.names:
            view = self.buffer[name]
            if route == "instanced":
                view.divisor = 1
            self.program[name] = view

    def payload(self, colors, start=0):
        """The records of cells start onwards, with these colors."""
        cells = XY[start:start + len(colors)]
        if self.route == "vertices":
            data = np.zeros(6 * len(colors), VERTEX)
            data["a_position"] = (cells[:, None, :] + CORNERS).reshape(-1, 2)
            data["a_color"] = np.repeat(colors / 255.0, 6, axis=0)
        else:
            data = np.zeros(len(colors), CELL)
            data["a_cell"] = cells
            data["a_color"] = colors / 255.0
        return data

    def settle(self):
        """Run the construction's commands, so that later counters see only the test's own."""
        self.read()
        retire()

    def draw(self, slot):
        gloo.set_viewport(slot * W, 0, W, H)
        self.program.draw("points" if self.route == "points" else "triangles")

    def read(self):
        with self.fbo:
            pixels = gloo.read_pixels(viewport=(0, 0, 2 * W, H))
        pixels = pixels[::-1]  # read_pixels puts the top row first
        return pixels[:, :W], pixels[:, W:]

    def frame(self, first, second):
        """Upload first and draw it into slot 0, upload second and draw it into slot 1, read both, and retire."""
        with self.fbo:
            self.buffer.set_data(self.payload(first))
            self.draw(0)
            self.buffer.set_data(self.payload(second))
            self.draw(1)
        pixels = self.read()
        retire()
        return pixels


@pytest.mark.parametrize("route", ["instanced", "vertices"])
def test_a_streamed_buffer_copies_from_its_block_and_warm_frames_allocate_nothing(route):
    rng = np.random.default_rng(2661)
    canvas = headless()
    with canvas:
        scene = Cells(route)
        for index in range(3):  # warm the blocks, their imports, the retired GPU buffers and the readback path
            first, second = levels(rng), levels(rng)
            left, right = scene.frame(first, second)
            assert np.array_equal(left, picture(first)) and np.array_equal(right, picture(second)), index
        before, start = _dawn.probe(), allocations()
        for index in range(FRAMES):
            first, second = levels(rng), levels(rng)
            left, right = scene.frame(first, second)
            assert np.array_equal(left, picture(first)) and np.array_equal(right, picture(second)), index
        after, uploaded = _dawn.probe(), allocations()
        for index in range(FRAMES):  # the same draws without an upload, each showing the last one
            with scene.fbo:
                scene.draw(0)
                scene.draw(1)
            left, right = scene.read()
            assert np.array_equal(left, picture(second)) and np.array_equal(right, picture(second)), index
            retire()
        read_only = allocations()
        available = imports()
        nbytes = scene.payload(first).nbytes
    canvas.close()
    # Per frame: the first update rewrites the idle revision in place, and the second, while the first draw holds
    # it, makes a revision that takes the GPU buffer of the one retired with the previous frame.
    assert changes(before, after) == {"buffer_import_copies": 2 * FRAMES if available else 0,
                                      "buffer_import_fallbacks": 0 if available else 2 * FRAMES,
                                      "buffer_shadow_transfers": 2 * FRAMES, "buffer_pool_reuses": FRAMES,
                                      "host_imports": 0}
    assert after["buffer_import_bytes"] - before["buffer_import_bytes"] == (2 * FRAMES * nbytes if available else 0)
    assert [(uploaded[i] - start[i]) - (read_only[i] - uploaded[i]) for i in range(2)] == [0, 0]


INDEXED_W, INDEXED_H = 128, 64  # 8,192 cells, each with two quads of its own colors: 65,536 vertices


@pytest.mark.parametrize("dtype, total", [(np.uint32, 262146), (np.uint16, 524289)])  # 1,048,584 and 1,048,578 bytes
def test_an_index_buffer_copies_from_its_block_when_its_size_is_a_multiple_of_4_bytes(dtype, total):
    rng = np.random.default_rng(2662 + total)
    cells = INDEXED_W * INDEXED_H
    xy = np.stack(np.meshgrid(np.arange(INDEXED_W), np.arange(INDEXED_H)), -1).reshape(-1, 2).astype(np.float32)
    quad = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], np.float32)
    colors = levels(rng, 2 * cells).reshape(cells, 2, 4)
    vertices = np.zeros((cells, 2, 4), VERTEX)
    vertices["a_position"] = xy[:, None, None, :] + quad
    vertices["a_color"] = (colors / 255.0)[:, :, None, :]
    size = "vec2(%d.0, %d.0)" % (INDEXED_W, INDEXED_H)
    first = (np.arange(cells) * 8)[:, None] + np.array([0, 1, 2, 2, 1, 3])

    def indices(choice):  # each cell's triangles from quad 0 or 1, then degenerate triangles up to `total` indices
        result = np.zeros(total, dtype)
        result[:6 * cells] = (first + 4 * choice[:, None]).reshape(-1)
        return result

    canvas = headless()
    with canvas:
        fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(INDEXED_H, INDEXED_W, 4)))
        program = gloo.Program(PER_VERTEX.replace(SIZE, size), FRAGMENT)
        program.bind(gloo.VertexBuffer(vertices.reshape(-1)))
        index = gloo.IndexBuffer(indices(np.zeros(cells, np.int64)))
        before = None
        for frame in range(2 + FRAMES):  # two warm frames
            if frame == 2:
                before = _dawn.probe()
            choice = rng.integers(0, 2, cells)
            index.set_data(indices(choice))
            with fbo:
                gloo.set_viewport(0, 0, INDEXED_W, INDEXED_H)
                program.draw("triangles", index)
                pixels = gloo.read_pixels(viewport=(0, 0, INDEXED_W, INDEXED_H))[::-1]
            retire()
            assert np.array_equal(pixels, colors[np.arange(cells), choice].reshape(INDEXED_H, INDEXED_W, 4)), frame
        after = _dawn.probe()
        available = imports()
    canvas.close()
    copied = available and np.dtype(dtype).itemsize * total % 4 == 0
    assert changes(before, after) == {"buffer_import_copies": FRAMES if copied else 0,
                                      "buffer_import_fallbacks": 0 if copied else FRAMES,
                                      "buffer_shadow_transfers": FRAMES, "buffer_pool_reuses": 0, "host_imports": 0}


def test_patches_of_a_block_backed_buffer_land_while_a_frame_holds_it_and_once_it_is_idle():
    rng = np.random.default_rng(2663)
    first, patch, later = levels(rng), levels(rng, 1000), levels(rng, 500)
    held, idle = first.copy(), first.copy()
    held[4096:5096] = patch
    idle[4096:5096] = patch
    idle[20000:20500] = later
    canvas = headless()
    with canvas:
        scene = Cells("instanced")
        scene.settle()
        before = _dawn.probe()
        with scene.fbo:
            scene.buffer.set_data(scene.payload(first))
            scene.draw(0)  # holds the block-backed revision when the patch arrives
            scene.buffer.set_subdata(scene.payload(patch, 4096), offset=4096)
            scene.draw(1)
        left, right = scene.read()
        retire()
        middle = _dawn.probe()
        scene.buffer.set_subdata(scene.payload(later, 20000), offset=20000)  # no frame holds it now
        with scene.fbo:
            scene.draw(1)
        right_later = scene.read()[1]
        retire()
        after = _dawn.probe()
    canvas.close()
    assert np.array_equal(left, picture(first)) and np.array_equal(right, picture(held))
    assert np.array_equal(right_later, picture(idle))
    nbytes = CELLS * CELL.itemsize
    assert changes(before, middle, ("buffer_shadow_transfers", "buffer_copy_on_write", "buffer_copy_on_write_bytes")) \
        == {"buffer_shadow_transfers": 1, "buffer_copy_on_write": 1, "buffer_copy_on_write_bytes": nbytes}
    assert changes(middle, after, ("buffer_shadow_transfers", "buffer_copy_on_write")) == \
        {"buffer_shadow_transfers": 0, "buffer_copy_on_write": 0}


def test_points_read_a_block_backed_buffer():
    rng = np.random.default_rng(2664)
    canvas = headless()
    with canvas:
        scene = Cells("points")
        scene.settle()
        before = _dawn.probe()
        for index in range(2):
            first, second = levels(rng), levels(rng)
            left, right = scene.frame(first, second)
            assert np.array_equal(left, picture(first)) and np.array_equal(right, picture(second)), index
        after = _dawn.probe()
    canvas.close()
    assert changes(before, after, ("buffer_shadow_transfers",)) == {"buffer_shadow_transfers": 4}


def test_a_device_loss_reuploads_a_block_backed_buffer_and_imports_resume():
    rng = np.random.default_rng(2665)
    canvas = headless()
    with canvas:
        scene = Cells("instanced")
        first, second = levels(rng), levels(rng)
        left, right = scene.frame(first, second)
        assert np.array_equal(left, picture(first)) and np.array_equal(right, picture(second))
        _dawn.lose_device()  # the rebuild uploads the live revision from its block again
        with scene.fbo:
            scene.draw(0)
            scene.draw(1)
        left, right = scene.read()
        retire()
        assert np.array_equal(left, picture(second)) and np.array_equal(right, picture(second))
        before = _dawn.probe()
        for index in range(FRAMES):
            first, second = levels(rng), levels(rng)
            left, right = scene.frame(first, second)
            assert np.array_equal(left, picture(first)) and np.array_equal(right, picture(second)), index
        after = _dawn.probe()
        available = imports()
    canvas.close()
    moved = changes(before, after)
    assert moved["buffer_import_copies"] + moved["buffer_import_fallbacks"] == 2 * FRAMES
    assert moved["buffer_import_copies"] >= 1 if available else moved["buffer_import_copies"] == 0


CHILD = r"""
import json, sys
sys.path[:0] = json.loads(sys.argv[1])
import numpy as np
from vispy import app, gloo, _dawn
assert _dawn.__file__ == sys.argv[2], (_dawn.__file__, sys.argv[2])
frames = int(sys.argv[3])
rng = np.random.default_rng(2666)
cells = 49152
canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
with canvas:
    fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(192, 256, 4)))
    program = gloo.Program("attribute vec2 a_position; attribute vec4 a_color; varying vec4 v_color;"
                           "void main() { gl_Position = vec4(a_position, 0.0, 1.0); v_color = a_color; }",
                           "varying vec4 v_color; void main() { gl_FragColor = v_color; }")
    dtype = [("a_position", np.float32, 2), ("a_color", np.float32, 4)]
    def payload():
        data = np.zeros(cells, dtype)
        data["a_position"][:3] = [[-1, -1], [3, -1], [-1, 3]]  # one triangle covers the target
        data["a_color"][:3] = rng.integers(0, 256, 4) / 255.0
        return data
    buffer = gloo.VertexBuffer(payload())
    program.bind(buffer)
    ok = True
    before = None
    for frame in range(2 + frames):
        if frame == 2:
            before = _dawn.probe()
        colors = []
        with fbo:
            for slot in range(2):
                data = payload()
                buffer.set_data(data)
                colors.append(np.round(data["a_color"][0] * 255).astype(np.uint8))
                gloo.set_viewport(slot * 128, 0, 128, 192)
                program.draw("triangles")
            pixels = gloo.read_pixels(viewport=(0, 0, 256, 192))
        ok = ok and bool((pixels[:, :128] == colors[0]).all() and (pixels[:, 128:] == colors[1]).all())
        assert _dawn.probe()["pending_tickets"] == 0
    after = _dawn.probe()
    info = _dawn.device_info()
canvas.close()
moved = {name: after[name] - before[name] for name in ("buffer_import_copies", "buffer_import_fallbacks",
                                                        "buffer_pool_reuses")}
print(json.dumps({"host_mapped_pointer": bool(info["host_mapped_pointer"]), **moved, "ok": ok}))
"""


def test_imports_can_be_turned_off():
    env = dict(os.environ, VISPY_DAWN_HOST_IMPORT="0")
    child = subprocess.run([sys.executable, "-B", "-c", CHILD, json.dumps(sys.path), _dawn.__file__, str(FRAMES)],
                           env=env, capture_output=True, text=True, timeout=120)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout.splitlines()[-1]) == {"host_mapped_pointer": False, "buffer_import_copies": 0,
                                                         "buffer_import_fallbacks": 2 * FRAMES,
                                                         "buffer_pool_reuses": FRAMES, "ok": True}
