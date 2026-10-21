"""Six order proofs; no readback between dependent commands."""

from pathlib import Path

import pytest

from tools.fixture_gloo import render
from tools.oracle_compare import assert_reference

pytestmark = pytest.mark.gpu
EVIDENCE = Path(__file__).resolve().parents[2] / "build/evidence/order-proofs"


@pytest.mark.parametrize("name", [
    "uniform_snapshot", "buffer_snapshot", "texture_snapshot_resize",
    "framebuffer_sample", "shared_canvases", "delete_snapshot",
])
def test_deferred_order_proof(name):
    image, commands, shaders, reads = render(name)
    assert reads == (2 if name == "shared_canvases" else 1)
    assert commands and shaders
    draw_count = sum(command[0] == "DRAW" for command in commands)
    assert draw_count >= (1 if name == "delete_snapshot" else 2)
    assert_reference(name, image, evidence=EVIDENCE)
    print(f"order proof {name}: {draw_count} draws, {reads} final readback(s), OpenGL parity")
