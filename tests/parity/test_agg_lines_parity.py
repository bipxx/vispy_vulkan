"""Agg line caps, joins, degenerate joins and pixel-scaled width (M09) versus an independent OpenGL capture."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_agg_lines import CASES, CRITERIA, assert_landmarks, render, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/agg-lines-opengl"
EVIDENCE = ROOT / "build/evidence/agg-lines-candidate"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_references_bind_this_fixture_and_its_exact_criteria():
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["provenance"]["fixture_source_sha256"] == digest(ROOT / "tools/fixture_agg_lines.py")
    assert manifest["comparison"]["criteria"] == CRITERIA and not manifest["errors"]
    assert set(manifest["fixtures"]) == set(CASES)


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_agg_lines_match_exact_opengl(name):
    from vispy import _dawn

    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    assert {key: params[key] for key in specification(name)} == {key: record["parameters"][key] for key in specification(name)}
    assert params["pixel_scale"] == record["parameters"]["pixel_scale"]
    assert image.shape == reference.shape, (name, image.shape, reference.shape)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert CRITERIA[name] == "exact"
    assert np.array_equal(image, reference), (name, int(difference.max()), int(np.any(difference, axis=2).sum()))
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("agg lines", name, "exact maxabs", int(difference.max()))
