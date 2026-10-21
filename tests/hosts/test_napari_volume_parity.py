"""Categorical scientific volumes through unmodified napari's real Viewer."""

import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_napari_volume import CASES, assert_landmarks, render

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/napari-volume-opengl"
EVIDENCE = ROOT / "build/evidence/napari-volume-candidate"


@pytest.mark.parametrize("name", CASES)
def test_napari_categorical_volume_matches_independent_opengl(name):
    import napari
    import numba
    from napari._qt.qt_event_loop import get_qapp

    assert napari.__version__ == "0.9.2"
    assert numba.__version__ == "0.68.0"
    get_qapp().setQuitOnLastWindowClosed(False)
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert image.shape == reference.shape == (96, 96, 4)
    assert commands and shaders
    expected = dict(record["parameters"])
    actual = dict(params)
    assert "QOpenGLWidget" in expected.pop("native_mro")
    assert "QOpenGLWidget" not in actual.pop("native_mro")
    assert actual == expected
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.parameters.json").write_text(json.dumps(params, indent=2))
    assert np.array_equal(image, reference), (name, "exact categorical image mismatch", int(difference.max()))
    assert_landmarks(name, image)
    print("napari categorical volume independent oracle", name, "maxabs", int(difference.max()))
