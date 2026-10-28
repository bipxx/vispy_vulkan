"""Real registered plugin rendering, Qt interaction and callback retirement."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from tools.fixture_napari_threedee import (
    AXES, CASES, DATA_SHAPE, SIZE, assert_landmarks, handle_world,
    phantom, projected_axis_distance, specification,
)
from tools.smooth_line_parity import smooth_line_difference

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/napari-threedee-opengl"
EVIDENCE = ROOT / "build/evidence/napari-threedee-candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_plugin_fixture_geometry_is_analytic_and_import_creates_no_qapplication():
    data = phantom()
    assert data.shape == DATA_SHAPE and data.dtype == np.float32
    assert data[3, 5, 6] == .25 and data[8, 11, 14] == 1 and data[2, 12, 17] == .5
    assert data[8, 5, 6] == 0
    for axis, spec in AXES.items():
        np.testing.assert_array_equal(handle_world(axis), np.asarray(spec["vector"]) * 10)
    assert projected_axis_distance(np.zeros(3), np.array([0, 0, 2]), [1, 0, 0], "x") == 2
    assert projected_axis_distance(np.zeros(3), np.array([0, 3, 0]), [1, 0, 0], "y") == 3
    assert projected_axis_distance(np.zeros(3), np.array([0, 0, 2]), [1, 0, 1], "x") == pytest.approx(1)
    assert len({specification(name)["input"]["sha256"] for name in CASES}) == 1
    code = """
from tools.fixture_napari_threedee import CASES, specification
import sys
assert all(specification(name)['comparison'].startswith('whole-frame exact') for name in CASES)
assert not any(name.split('.')[0] in {'PyQt6', 'PySide2', 'vispy', 'napari', 'napari_threedee'} for name in sys.modules)
"""
    child = subprocess.run([str(ROOT / ".venv/Scripts/python.exe"), "-c", code], cwd=ROOT,
                           capture_output=True, text=True)
    assert child.returncode == 0, (child.stdout, child.stderr)


def test_genuine_plugin_wheel_and_registration_proof_without_viewer_or_graphics():
    python = ROOT / "build/host-environments/napari-threedee-cpython312-pyqt6-packaged/Scripts/python.exe"
    assert python.is_file(), "required pinned real plugin environment is missing"
    code = """
import json
import sys
from PyQt6 import QtGui, QtWidgets
from tools.oracle_napari_threedee_capture import plugin_provenance
assert QtWidgets.QApplication.instance() is None
record = plugin_provenance()
assert len(record['plugin_files_sha256']) >= 100
assert QtWidgets.QApplication.instance() is None and QtGui.QOpenGLContext.currentContext() is None
assert not any(name == '_dawn' or name.endswith('._dawn') for name in sys.modules)
print(json.dumps({'plugin': record['plugin_version'], 'wheel_sha256': record['plugin_wheel_sha256'],
                  'files_checked': len(record['plugin_files_sha256']), 'widget': record['registered_layer_widget']}))
"""
    env = dict(os.environ, QT_API="pyqt6", QT_QPA_PLATFORM="offscreen")
    child = subprocess.run([str(python), "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
    assert child.returncode == 0, (child.returncode, child.stdout, child.stderr)
    record = json.loads(child.stdout)
    assert record["plugin"] == "0.0.29" and record["files_checked"] >= 100
    print("genuine plugin CPU registration, no viewer/graphics", child.stdout.strip())


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_registered_plugin_qt_workflow_matches_independent_upstream(name, tmp_path):
    path = REFERENCE / "manifest.json"
    assert path.is_file(), "required real upstream plugin capture is pending"
    manifest = json.loads(path.read_text())
    assert name in manifest["fixtures"], (name, "unresolved upstream admission", manifest["errors"].get(name))
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["plugin"]["plugin_version"] == "0.0.29"
    assert origins["plugin"]["python_hash_seed"] == "0"
    assert origins["plugin"]["fixture_source_sha256"] == digest(ROOT / "tools/fixture_napari_threedee.py")
    assert origins["plugin"]["capture_source_sha256"] == digest(ROOT / "tools/oracle_napari_threedee_capture.py")
    assert "site-packages" in origins["plugin"]["plugin_origin"]
    record = manifest["fixtures"][name]
    assert record["process"]["exit_code"] == 0
    for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
        assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
    reference = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    output = tmp_path / name
    child_env = dict(os.environ, PYTHONHASHSEED="0")
    # Every rendering/import/Qt operation runs in the explicit installed
    # candidate interpreter, as in the overlay and render-plane suites.
    candidate_python = Path(os.environ.get("VISPY_PLUGIN_CANDIDATE_PYTHON", sys.executable)).resolve(strict=True)
    child = subprocess.run([str(candidate_python), "-X", "faulthandler",
                            str(ROOT / "tools/oracle_napari_threedee_capture.py"),
                            "--kind", "candidate", "--output", str(output), "--fixtures", name],
                           env=child_env, cwd=ROOT, capture_output=True, text=True)
    assert child.returncode == 0, (name, child.returncode, child.stdout, child.stderr)
    candidate = json.loads((output / "manifest.json").read_text())["fixtures"][name]
    assert candidate["process"]["exit_code"] == 0
    params = candidate["parameters"]
    artifacts = candidate["artifacts"]
    image = np.load(output / artifacts["rgba"]["file"], allow_pickle=False)
    commands = json.loads((output / artifacts["filtered_glir"]["file"]).read_text())
    shaders = json.loads((output / artifacts["expanded_shaders"]["file"]).read_text())
    extras = {key: np.load(output / artifact["file"], allow_pickle=False) for key, artifact in artifacts.items()
              if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
    assert commands and shaders
    assert_landmarks(name, image, params, extras)
    for key in ("case", "input", "size", "camera", "origin", "radius", "handle_size", "handle_world", "picking", "comparison", "stages", "initial_projection", "final_projection"):
        assert params[key] == record["parameters"][key], (name, key)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    # Smooth-line coverage is driver-defined: interiors exact, antialiased edges bounded (decision D5).
    reason = smooth_line_difference(image, reference)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    for key, value in extras.items():
        prior = np.load(REFERENCE / record["artifacts"][key]["file"], allow_pickle=False)
        reason = smooth_line_difference(value, prior)
        assert reason is None, (name, key, reason)
    print("registered plugin public Qt workflow", name, "smooth-line parity", image.shape)
