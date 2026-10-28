"""Public plane manipulation/depth/clipping through the genuine plugin."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from tools.fixture_napari_render_plane import (
    CASES, NORMAL, POSITION, SHAPE, local_handle, phantom, rodrigues,
    rotation_from_drag, specification, assert_landmarks,
)
from tools.smooth_line_parity import smooth_line_difference

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/napari-render-plane-numpy246-opengl"
EVIDENCE = ROOT / "build/evidence/napari-render-plane-candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_plane_input_rotation_and_clip_expectations_are_fixed_before_rendering():
    data = phantom()
    assert data.shape == SHAPE and data.dtype == np.float32
    assert data[8, 5, 6] == .25 and data[8, 17, 20] == 1 and data[16, 4, 22] == .5
    np.testing.assert_array_equal(local_handle("translator", "z"), [5, 0, 0])
    np.testing.assert_allclose(local_handle("rotator", "x"), np.array([1, 1, 0]) * 4 / np.sqrt(2))
    quarter_turn = rodrigues([0, 0, 1], np.pi / 2)
    np.testing.assert_allclose(quarter_turn @ NORMAL, [0, 1, 0], atol=1e-15)
    origin = np.array(POSITION)
    rotation, angle = rotation_from_drag(origin + [4, 0, 1], origin + [0, 4, 1],
                                         np.array([0., 0., -1.]), origin, np.array([0., 0., 1.]))
    assert angle == pytest.approx(np.pi / 2)
    np.testing.assert_allclose(rotation, quarter_turn, atol=1e-15)
    assert specification("plane_clipped")["clip_plane"]["normal"] == [0., 1., 0.]
    assert all(specification(name)["comparison"].startswith("whole-frame exact") for name in CASES)


def test_registered_plane_widget_and_camera_api_preflight_creates_no_graphics():
    python = ROOT / "build/host-environments/napari-threedee-cpython312-pyqt6-packaged/Scripts/python.exe"
    assert python.is_file(), "required genuine packaged upstream environment is missing"
    code = """
import json
import sys
from PyQt6 import QtGui, QtWidgets
from napari.components import Camera
from tools.oracle_napari_render_plane_capture import plugin_provenance
from tools.fixture_napari_render_plane import CAMERA, CASES, specification
record = plugin_provenance()
assert record['registered_render_plane_widget']['class'] == 'QtRenderPlaneManipulatorWidget'
assert Camera(angles=CAMERA['angles']).up_direction[0] > .2
assert QtWidgets.QApplication.instance() is None and QtGui.QOpenGLContext.currentContext() is None
assert not any(name == '_dawn' or name.endswith('._dawn') for name in sys.modules)
print(json.dumps({'widget': record['registered_render_plane_widget'], 'wheel_sha256':record['plugin_wheel_sha256'],
                  'cases':list(CASES), 'source_hashes':{name:specification(name)['input']['sha256'] for name in CASES}}))
"""
    child = subprocess.run([str(python), "-c", code], cwd=ROOT,
                           env=dict(os.environ, QT_API="pyqt6", QT_QPA_PLATFORM="offscreen"), capture_output=True, text=True)
    assert child.returncode == 0, (child.returncode, child.stdout, child.stderr)
    print("real registered plane widget CPU preflight, no graphics", child.stdout.strip())


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_registered_render_plane_qt_workflow_matches_upstream(name, tmp_path):
    manifest_path = REFERENCE / "manifest.json"
    assert manifest_path.is_file(), "required independent plane fixture admission is pending"
    manifest = json.loads(manifest_path.read_text())
    assert name in manifest["fixtures"], (name, "unresolved upstream admission", manifest["errors"].get(name))
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["plugin"]["installed"]["numpy"] == "2.4.6"
    assert origins["plugin"]["fixture_source_sha256"] == digest(ROOT / "tools/fixture_napari_render_plane.py")
    assert origins["plugin"]["capture_source_sha256"] == digest(ROOT / "tools/oracle_napari_render_plane_capture.py")
    assert origins["plugin"]["python_hash_seed"] == "0"
    reference = manifest["fixtures"][name]
    assert reference["process"]["exit_code"] == 0
    for artifact in [*reference["artifacts"].values(), reference["capture"], reference["process"]["stdout"], reference["process"]["stderr"]]:
        assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
    output = tmp_path / name
    candidate_python = Path(os.environ.get("VISPY_PLUGIN_CANDIDATE_PYTHON", sys.executable)).resolve(strict=True)
    child = subprocess.run([str(candidate_python), "-X", "faulthandler", str(ROOT / "tools/oracle_napari_threedee_native_probe.py"),
                            "--workflow", "render-plane", "--fixture", name, "--output", str(output)],
                           cwd=ROOT, env=dict(os.environ, PYTHONHASHSEED="0"), capture_output=True, text=True)
    process = {"candidate_python": str(candidate_python), "exit_code": child.returncode, "streams": {}}
    for stream in ("stdout", "stderr"):
        diagnostic = tmp_path / f"{name}.{stream}.log"
        diagnostic.write_text(getattr(child, stream), encoding="utf-8")
        process["streams"][stream] = {"file": diagnostic.name, "sha256": digest(diagnostic)}
    (tmp_path / f"{name}.process.json").write_text(json.dumps(process, indent=2) + "\n")
    assert child.returncode == 0, (name, child.returncode, child.stdout, child.stderr)
    candidate = json.loads((output / "manifest.json").read_text())["fixtures"][name]
    candidate_origins = json.loads((output / "manifest.json").read_text())["provenance"]
    assert candidate_origins["plugin"]["installed"]["numpy"] == "2.4.6", "paired runtime pin differs"
    params, artifacts = candidate["parameters"], candidate["artifacts"]
    proof = json.loads((output / candidate["native_proof"]["file"]).read_text())
    assert proof["probe"]["draw_calls"] > 0 and proof["probe"]["pipeline_misses"] > 0
    assert proof["device_info"]["ok"] and proof["candidate_version"] == "0.17.0+vulkan.1"
    image = np.load(output / artifacts["rgba"]["file"], allow_pickle=False)
    expected = np.load(REFERENCE / reference["artifacts"]["rgba"]["file"], allow_pickle=False)
    extras = {key: np.load(output / artifact["file"], allow_pickle=False) for key, artifact in artifacts.items()
              if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
    assert_landmarks(name, image, params, extras)
    for key in ("case", "input", "camera", "plane_position", "plane_normal", "plane_thickness", "clip_plane", "stages", "landmarks"):
        assert params[key] == reference["parameters"][key], (name, key)
    difference = np.abs(image.astype(np.int16) - expected.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    # Smooth-line coverage is driver-defined: interiors exact, antialiased edges bounded (decision D5).
    reason = smooth_line_difference(image, expected)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    for key, value in extras.items():
        prior = np.load(REFERENCE / reference["artifacts"][key]["file"], allow_pickle=False)
        reason = smooth_line_difference(value, prior)
        assert reason is None, (name, key, reason)
    print("registered plane manipulator actual Qt workflow", name, "smooth-line parity", image.shape, proof)
