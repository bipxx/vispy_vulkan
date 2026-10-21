"""Delayed texture updates retain each draw's contents and GPU-produced pixels."""

import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_revisions import CASES, assert_expected, assert_trace, render

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/texture-revisions-opengl"
EVIDENCE = ROOT / "build/evidence/texture-revisions-candidate"


@pytest.mark.parametrize("name", CASES)
def test_sampler_and_rendered_texture_revisions_match_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, parameters, reads = render(name)
    assert reads == record["readbacks"] == 1
    assert parameters == record["parameters"]
    assert commands and shaders
    assert image.shape == reference.shape == (24, 32, 4)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert np.array_equal(image, reference), (name, int(difference.max()),
        "old draws or untouched rendered texels changed during texture revision")
    assert_expected(name, image)
    assert_trace(name, commands)
    print("texture revision independent oracle", name, "maxabs", int(difference.max()))
