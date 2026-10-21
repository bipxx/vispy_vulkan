"""Public-gloo review reproductions compared with an independent GL oracle."""

from pathlib import Path

import pytest

from tools.fixture_gloo import FIXTURES, assert_numeric_landmarks, render
from tools.oracle_compare import assert_reference

pytestmark = pytest.mark.gpu
ORDER_CASES = {"uniform_snapshot", "buffer_snapshot", "texture_snapshot_resize",
               "framebuffer_sample", "shared_canvases", "delete_snapshot"}
EVIDENCE = Path(__file__).resolve().parents[2] / "build/evidence/regressions"


@pytest.mark.parametrize("name", [name for name in FIXTURES if name not in ORDER_CASES])
def test_review_regression_matches_independent_opengl(name):
    image, commands, _, reads = render(name)
    assert reads == 1
    assert commands
    assert_numeric_landmarks(name, image)
    assert_reference(name, image, evidence=EVIDENCE)
    print(f"regression {name}: independent OpenGL parity")
