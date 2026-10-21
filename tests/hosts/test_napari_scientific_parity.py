"""Pinned, unmodified napari workflows versus separately installed OpenGL."""

import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_napari import CASES, EXACT, assert_landmarks, masks, render

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/napari-opengl"
EVIDENCE = ROOT / "build/evidence/napari-candidate"


@pytest.mark.parametrize("name", CASES)
def test_unmodified_napari_scientific_workflow_matches_opengl(name):
    # Required dependencies deliberately import/fail rather than skip admission.
    import napari
    import numba
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn

    assert napari.__version__ == "0.9.2"
    assert numba.__version__ == "0.68.0"
    get_qapp().setQuitOnLastWindowClosed(False)
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert image.shape == reference.shape == (96, 128, 4)
    assert commands and shaders
    assert params["inputs"] == record["parameters"]["inputs"]
    assert params["camera_rect"] == record["parameters"]["camera_rect"]
    assert "QWidget" in params["native_mro"]
    assert "QOpenGLWidget" not in params["native_mro"]
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.parameters.json").write_text(json.dumps(params, indent=2))
    if name in EXACT:
        assert np.array_equal(image, reference), (name, int(difference.max()))
    else:
        interior, edge = masks(name, image.shape)
        assert difference[interior].max() <= 2, (name, int(difference[interior].max()))
        differing = np.any(difference != 0, axis=2)
        assert np.count_nonzero(differing & edge) <= np.count_nonzero(edge) * .001
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("napari independent oracle", name, "maxabs", int(difference.max()))
