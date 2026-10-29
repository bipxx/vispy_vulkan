# SPDX-License-Identifier: AGPL-3.0-only
"""napari layer families (W4) versus an independently installed OpenGL capture."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_napari_layer_families import CASES, CRITERIA, assert_landmarks, render, specification
from tools.napari_layer_families_comparison import layer_family_difference

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/napari-layer-families-opengl"
EVIDENCE = ROOT / "build/evidence/napari-layer-families-candidate"
FIXED = ("case", "size", "camera", "background", "criterion", "inputs_sha256")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_references_bind_this_fixture_and_its_fixed_criteria():
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["fixture_source_sha256"] == digest(ROOT / "tools/fixture_napari_layer_families.py")
    assert manifest["comparison"]["criteria"] == CRITERIA and not manifest["errors"]
    assert set(manifest["fixtures"]) == set(CASES)
    for name, record in manifest["fixtures"].items():
        assert {key: record["parameters"][key] for key in FIXED} == {key: specification(name)[key] for key in FIXED}
        for artifact in (record["rgba"], record["filtered_glir"], record["expanded_shaders"], record["capture"]):
            assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
        assert_landmarks(name, np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_napari_layer_family_matches_opengl(name):
    import napari
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn

    assert napari.__version__ == "0.9.2"
    get_qapp().setQuitOnLastWindowClosed(False)
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    for key in (*FIXED, "layer_types", "ndisplay"):
        assert params[key] == record["parameters"][key], (name, key)
    assert "QOpenGLWidget" not in params["native_mro"]
    assert image.shape == reference.shape, (name, image.shape, reference.shape)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    # The fixture's criteria, with decisions D11 (colorbar, histogram) and D12 (surface_shaded).
    reason = layer_family_difference(name, image, reference)
    assert reason is None, (name, reason)
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("napari layer families", name, CRITERIA[name], "maxabs", int(difference.max()))
