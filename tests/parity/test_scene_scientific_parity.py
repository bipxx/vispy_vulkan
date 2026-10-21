"""Scientific scene pixels and font atlases versus installed upstream OpenGL."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_scene import CASES, EXACT, assert_landmarks, masks, render

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/scene-opengl"
EVIDENCE = Path(os.environ.get("VISPY_SCENE_EVIDENCE", ROOT / "build/evidence/scene-candidate"))


@pytest.mark.parametrize("name", CASES)
def test_scientific_scene_image_and_cpu_atlas_match_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params, extras = render(name)
    assert commands and shaders
    assert params == record["parameters"]
    assert image.shape == reference.shape == (96, 128, 4)
    assert image.dtype == reference.dtype == np.uint8
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    for key, array in extras.items():
        atlas = np.load(REFERENCE / record[key]["file"], allow_pickle=False)
        np.save(EVIDENCE / f"{name}.{key}.npy", array, allow_pickle=False)
        assert np.array_equal(array, atlas), (name, "exact CPU SDF atlas mismatch")
    if name in EXACT:
        assert np.array_equal(image, reference), (name, "exact scene mismatch", int(difference.max()))
    else:
        interior, edge = masks(name, image.shape)
        assert difference[interior].max() <= 2, (name, int(difference[interior].max()))
        differing = np.any(difference != 0, axis=2)
        assert np.count_nonzero(differing & edge) <= np.count_nonzero(edge) * .001, (
            name, "fixed edge-band mismatch", int(np.count_nonzero(differing & edge)))
    assert_landmarks(name, image, extras)
    print("scene independent oracle", name, "maxabs", int(difference.max()))
