"""Separate unchanged DIVE/PySide2 attempt; a missing oracle is not a pass."""

import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
try:
    import tomllib
except ImportError:  # CPython3.10
    import tomli as tomllib

import numpy as np
import pytest

from tools.fixture_dive_pyside2 import CASES, assert_landmarks, inputs, qimage_rgba, render

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/dive-pyside2-opengl"
EVIDENCE = ROOT / "build/evidence/dive-pyside2-candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dive_pyside2_preparation_preserves_source_and_old_failed_attempt():
    proof = json.loads((ROOT / "compat/host-environments/dive-pyside2-environment.json").read_text())
    pin = tomllib.loads((ROOT / "compat/hosts.lock.toml").read_text())["dive"]
    assert proof["commit"] == pin["commit"]
    assert proof["package_tree_sha256"] == pin["package_tree_sha256"]
    assert proof["qualification"] == "cpu_api_and_import_only"
    assert proof["rendering_qualified"] is False
    for field in ("requirements", "requirements_input", "source_inventory", "import_inventory",
                  "splitter_probe", "primary_binding_metadata"):
        assert digest(ROOT / proof[field]) == proof[field + "_sha256"]
    imports = json.loads((ROOT / proof["import_inventory"]).read_text())
    assert not imports["errors"] and len(imports["modules"]) == 3
    assert imports["selected_backend"] == "PySide2"
    assert not imports["qapplication_created"] and not imports["current_opengl_context"]
    assert not imports["dawn_modules"] and not imports["other_qt_bindings"]
    assert imports["public_widget_export"]["qwidget_subclass"]
    assert imports["public_widget_export"]["constructed"] is False
    installed = {item["name"].lower(): item["version"] for item in imports["distributions"]}
    assert installed["numpy"] == "1.26.4" and installed["pandas"] == "1.5.3"
    assert installed["pyside2"] == installed["shiboken2"] == "5.15.2.1"
    assert installed["vispy"] == "0.17.0"
    legacy = proof["legacy_pyqt5_failures"]
    assert digest(ROOT / legacy["reference_manifest"]) == legacy["reference_manifest_sha256"]
    old = json.loads((ROOT / legacy["reference_manifest"]).read_text())
    assert set(old["errors"]) == set(CASES) and not old["fixtures"]


def test_qimage_public_constbits_preserves_stride_channels_and_ownership():
    from PySide2 import QtGui, QtWidgets

    assert QtWidgets.QApplication.instance() is None
    rows = np.full((2, 20), 165, np.uint8)
    pixels = np.array([[[11, 22, 33, 255], [44, 55, 66, 128], [77, 88, 99, 63]],
                       [[199, 188, 177, 31], [166, 155, 144, 15], [133, 122, 111, 7]]], np.uint8)
    rows[:, :12] = pixels.reshape(2, 12)
    storage = rows.tobytes()
    image = QtGui.QImage(storage, 3, 2, 20, QtGui.QImage.Format_RGBA8888)
    assert image.bytesPerLine() == 20
    captured = qimage_rgba(image)
    np.testing.assert_array_equal(captured, pixels)
    image.fill(QtGui.QColor(0, 0, 0, 255))
    np.testing.assert_array_equal(captured, pixels)
    argb = QtGui.QImage(2, 1, QtGui.QImage.Format_ARGB32)
    argb.setPixelColor(0, 0, QtGui.QColor(12, 34, 56, 78))
    argb.setPixelColor(1, 0, QtGui.QColor(87, 65, 43, 21))
    np.testing.assert_array_equal(qimage_rgba(argb), [[[12, 34, 56, 78], [87, 65, 43, 21]]])
    assert QtWidgets.QApplication.instance() is None
    assert not any(name == "_dawn" or name.endswith("._dawn") for name in sys.modules)


def test_qimage_null_is_a_failure():
    from PySide2 import QtGui

    with pytest.raises(ValueError, match="null screenshot"):
        qimage_rgba(QtGui.QImage())


def test_pyside2_uses_the_same_fixed_analytic_inputs():
    assert inputs("scatter")["x"].tolist() == [-1, 1, -.5]
    assert inputs("scatter_edit", True)["x"].tolist() == [-1, 1, .5]
    assert inputs("image")["values"][3, 2] == 1
    assert inputs("image_edit", True)["values"][3, 2] == 0
    assert inputs("image_edit", True)["values"][3, 5] == 1


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_dive_pyside2_public_exports_match_independent_upstream(name):
    manifest_path = REFERENCE / "manifest.json"
    assert manifest_path.is_file(), "PySide2 upstream graphics capture has not been admitted"
    reference = json.loads(manifest_path.read_text())
    assert not reference["errors"] and set(reference["fixtures"]) == set(CASES)
    origins = reference["provenance"]
    assert origins["kind"] == "upstream" and origins["binding"] == "PySide2"
    assert origins["python"] == "3.10.16" and origins["vispy_version"] == "0.17.0"
    assert origins["fixture_source_sha256"] == digest(ROOT / "tools/fixture_dive_pyside2.py")
    assert origins["shared_fixture_source_sha256"] == digest(ROOT / "tools/fixture_dive.py")
    assert metadata.version("vispy") == "0.17.0+vulkan.1", "requires the independently installed CPython310 candidate"
    record = reference["fixtures"][name]
    assert record["process"]["exit_code"] == 0
    for artifact in record["artifacts"].values():
        assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
    expected = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    actual, commands, shaders, params, extras = render(name)
    assert commands and shaders
    assert_landmarks(name, actual, params, before=extras.get("before"))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    output = EVIDENCE / f"{name}.rgba.npy"
    assert not output.exists(), "candidate evidence from an earlier attempt must be preserved"
    np.save(output, actual, allow_pickle=False)
    assert actual.shape == expected.shape
    delta = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
    assert np.array_equal(actual, expected), (name, "full frame equality", int(delta.max()), int(np.count_nonzero(delta)))
    if name.endswith("_edit"):
        before = np.load(REFERENCE / record["artifacts"]["before"]["file"], allow_pickle=False)
        np.testing.assert_array_equal(extras["before"], before)
