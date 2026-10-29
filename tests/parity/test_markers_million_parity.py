"""One million fixed-seed markers (M06) versus an independent OpenGL capture under decision D17, fixed before capture."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_markers_million import CASES, CRITERIA, assert_landmarks, render, specification
from tools.fixture_markers_million import difference as marker_difference

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/markers-million-opengl"
EVIDENCE = ROOT / "build/evidence/markers-million-candidate"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_references_bind_this_fixture_and_its_criteria():
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["provenance"]["fixture_source_sha256"] == digest(ROOT / "tools/fixture_markers_million.py")
    assert manifest["comparison"]["criteria"] == CRITERIA and not manifest["errors"]
    assert set(manifest["fixtures"]) == set(CASES)


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_million_markers_match_opengl(name):
    from vispy import _dawn

    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders and params == record["parameters"] == specification(name)
    assert image.shape == reference.shape, (name, image.shape, reference.shape)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    # Decision D17 (under D4): the fixture's documented-difference rule, fixed before capture.
    reason = marker_difference(image, reference)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("million markers", name, CRITERIA[name], "maxabs", int(difference.max()))
