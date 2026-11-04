# SPDX-License-Identifier: AGPL-3.0-only
"""A staged texture patch reaches the GPU when a new texture's first upload follows it in the same frame (B20).

A frame copies a patch into its texture from a staging buffer, in the frame's own encoder, so that a patch made between
two draws reaches only the second. While queue.WriteBuffer filled that staging buffer, a new texture's first upload
later in the same batch made the copy read zeros on the NVIDIA GeForce RTX 4090's Vulkan driver (610.88): the patch's
texels were zero on the GPU in that frame and in later ones, while the CPU shadow was right. It needed a fresh
process and less than about 64 KiB of the batch's small uploads (run b20-staged-patch-264), so each case runs in a
child interpreter.
"""
import json
import subprocess
import sys

import pytest
from vispy import _dawn

pytestmark = pytest.mark.gpu

CHILD = r'''
import json
from pathlib import Path
import sys
sys.path[:0] = json.loads(sys.argv[1])
import vispy
vispy.__path__.insert(0, str(Path(sys.argv[2]).parent))
import numpy as np
from vispy import app, gloo, _dawn
assert Path(_dawn.__file__).resolve() == Path(sys.argv[2]).resolve()
side, other_side, rows, columns = (int(value) for value in sys.argv[3:7])
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
rng = np.random.default_rng(320)
data = rng.integers(0, 256, (side, side, 4), dtype=np.uint8)
patch = rng.integers(0, 256, (rows, columns, 4), dtype=np.uint8)
other_data = rng.integers(0, 256, (other_side, other_side, 4), dtype=np.uint8)
canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
with canvas:
    texture = gloo.Texture2D(data, interpolation="nearest")
    fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(side, 2 * side, 4)))
    program = gloo.Program(VERTEX, FRAGMENT)
    program["a_position"] = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32)

    def draw(sampled, half):
        program["u_texture"] = sampled
        gloo.set_viewport(half * side, 0, side, side)
        program.draw("triangle_strip")

    def left():
        with fbo:
            pixels = gloo.read_pixels(viewport=(0, 0, 2 * side, side))
        return pixels[::-1][:, :side]  # read_pixels puts the top row first

    with fbo:
        draw(texture, 0)
    left()
    assert _dawn.probe()["pending_tickets"] == 0  # the texture is uploaded and current, and no frame is in flight
    other = gloo.Texture2D(shape=(other_side, other_side, 4), interpolation="nearest")
    with fbo:
        texture.set_data(patch, offset=(0, 0))  # staged, not yet uploaded
        draw(texture, 0)
        other.set_data(other_data)  # the new texture's first upload
        draw(other, 1)
    shown = left()[:rows, :columns]
    with fbo:
        draw(texture, 0)
    later = left()[:rows, :columns]
canvas.close()
print(json.dumps({name: "patch" if np.array_equal(region, patch) else "zeros" if not region.any() else "other"
                  for name, region in (("frame", shown), ("later", later))}))
'''


@pytest.mark.parametrize("side, other_side, rows, columns", [
    (64, 64, 8, 16),  # run perf-profile-261's case: a 16 KiB upload after a 2 KiB staged patch
    (64, 32, 32, 64),  # whole rows, without row padding
    (128, 96, 8, 16),  # the patched texture's own size does not matter
])
def test_a_staged_patch_survives_a_new_textures_first_upload_in_its_frame(side, other_side, rows, columns):
    completed = subprocess.run(
        [sys.executable, "-B", "-c", CHILD, json.dumps(sys.path), _dawn.__file__,
         str(side), str(other_side), str(rows), str(columns)],
        capture_output=True, text=True, timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.splitlines()[-1]) == {"frame": "patch", "later": "patch"}
