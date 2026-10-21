"""Real scalar volume pipelines versus installed upstream OpenGL."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_volume import CASES, METHODS, assert_landmarks, masks, render

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/volume-opengl"
EVIDENCE = Path(os.environ.get("VISPY_VOLUME_EVIDENCE", ROOT / "build/evidence/volume-candidate"))


@pytest.mark.parametrize("name", CASES)
def test_scalar_volume_image_and_depth_match_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    assert params == record["parameters"]
    assert set(params["exposed_methods"]) == set(METHODS)
    assert image.shape == reference.shape == (96, 96, 4)
    assert image.dtype == reference.dtype == np.uint8
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.parameters.json").write_text(json.dumps(params, indent=2))
    interior, edge = masks(name, image.shape)
    assert difference[interior].max() <= 2, (name, int(difference[interior].max()))
    differing = np.any(difference != 0, axis=2)
    assert np.count_nonzero(differing & edge) <= np.count_nonzero(edge) * .001, (
        name, "fixed edge-band mismatch", int(np.count_nonzero(differing & edge)))
    assert_landmarks(name, image)
    print("volume independent oracle", name, "maxabs", int(difference.max()))
