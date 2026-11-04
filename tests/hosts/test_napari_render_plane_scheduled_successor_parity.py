# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of test_napari_render_plane_scheduled_parity.py: the registered napari-threedee render-plane
manipulator's scheduled Qt workflows versus the installed napari's OpenGL packet.

The comparison is the retained test's (decision D19; D8 revised under it). tests/contract/
test_napari_successor_references.py binds every packet to the successor fixture, the retained fixture, the plugin
capture and the oracle's host lock.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from tools.fixture_napari_render_plane_scheduled_successor import CASES, assert_landmarks
from tools.napari_host_packets import evidence_dir, installed_packet
from tools.positioned_line_comparison import positioned_line_difference

ROOT = Path(__file__).resolve().parents[2]
BASE = "napari-render-plane-scheduled-opengl"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_python():
    return Path(os.environ.get("VISPY_PLUGIN_CANDIDATE_PYTHON", sys.executable)).resolve(strict=True)


def test_registered_plane_widget_and_camera_api_preflight_creates_no_graphics():
    code = """
import json
import sys
sys.path.insert(0, 'tools')
from PyQt6 import QtGui, QtWidgets
from napari.components import Camera
import oracle_napari_plugin_successor_capture as capture
from fixture_napari_render_plane_scheduled_successor import CAMERA, CASES, specification
record = capture.plugin_provenance('scheduled', None)
assert record['registered_render_plane_widget']['class'] == 'QtRenderPlaneManipulatorWidget'
assert Camera(angles=CAMERA['angles']).up_direction[0] > .2
assert QtWidgets.QApplication.instance() is None and QtGui.QOpenGLContext.currentContext() is None
assert not any(name == '_dawn' or name.endswith('._dawn') for name in sys.modules)
print(json.dumps({'widget': record['registered_render_plane_widget'], 'wheel_sha256':record['plugin_wheel_sha256'],
                  'napari': record['napari_version'], 'cases':list(CASES),
                  'source_hashes':{name:specification(name)['input']['sha256'] for name in CASES}}))
"""
    child = subprocess.run([str(candidate_python()), "-c", code], cwd=ROOT,
                           env=dict(os.environ, QT_API="pyqt6", QT_QPA_PLATFORM="offscreen"), capture_output=True, text=True)
    assert child.returncode == 0, (child.returncode, child.stdout, child.stderr)
    print("real registered plane widget CPU preflight, no graphics", child.stdout.strip())


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_registered_render_plane_qt_workflow_matches_upstream(name, tmp_path):
    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert name in manifest["fixtures"], (name, "unresolved upstream admission", manifest["errors"].get(name))
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    plugin = origins["plugin"]
    assert plugin["suite"] == "scheduled" and plugin["installed"]["numpy"] == "2.4.6"
    assert plugin["python_hash_seed"] == "0"
    reference = manifest["fixtures"][name]
    assert reference["process"]["exit_code"] == 0
    for artifact in [*reference["artifacts"].values(), reference["capture"], reference["process"]["stdout"], reference["process"]["stderr"]]:
        assert digest(packet / artifact["file"]) == artifact["sha256"]
    output = tmp_path / name
    python = candidate_python()
    child = subprocess.run([str(python), "-X", "faulthandler", str(ROOT / "tools/oracle_napari_plugin_successor_native_probe.py"),
                            "--suite", "scheduled", "--fixture", name, "--output", str(output)],
                           cwd=ROOT, env=dict(os.environ, PYTHONHASHSEED="0"), capture_output=True, text=True)
    process = {"candidate_python": str(python), "exit_code": child.returncode, "streams": {}}
    for stream in ("stdout", "stderr"):
        diagnostic = tmp_path / f"{name}.{stream}.log"
        diagnostic.write_text(getattr(child, stream), encoding="utf-8")
        process["streams"][stream] = {"file": diagnostic.name, "sha256": digest(diagnostic)}
    (tmp_path / f"{name}.process.json").write_text(json.dumps(process, indent=2) + "\n")
    assert child.returncode == 0, (name, child.returncode, child.stdout, child.stderr)
    produced = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert produced["provenance"]["napari_version"] == origins["napari_version"], "candidate runs another napari"
    candidate = produced["fixtures"][name]
    assert produced["provenance"]["plugin"]["installed"]["numpy"] == "2.4.6", "paired runtime pin differs"
    params, artifacts = candidate["parameters"], candidate["artifacts"]
    proof = json.loads((output / candidate["native_proof"]["file"]).read_text(encoding="utf-8"))
    assert proof["probe"]["draw_calls"] > 0 and proof["probe"]["pipeline_misses"] > 0
    assert proof["device_info"]["ok"] and proof["candidate_version"] == "0.17.0+vulkan.1"
    image = np.load(output / artifacts["rgba"]["file"], allow_pickle=False)
    expected = np.load(packet / reference["artifacts"]["rgba"]["file"], allow_pickle=False)
    extras = {key: np.load(output / artifact["file"], allow_pickle=False) for key, artifact in artifacts.items()
              if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
    assert_landmarks(name, image, params, extras)
    for key in ("case", "input", "camera", "plane_position", "plane_normal", "plane_thickness", "clip_plane", "stages", "landmarks"):
        assert params[key] == reference["parameters"][key], (name, key)
    difference = np.abs(image.astype(np.int16) - expected.astype(np.int16))
    evidence = evidence_dir("napari-render-plane-scheduled-successor-candidate", origins["napari_version"])
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    # The manipulator's smooth 3D strokes are judged by position, not exact intensity (D19; D8 revised under it):
    # D5's smooth-line rule, plus pixels beyond its edge bound where both frames draw the stroke.
    reason = positioned_line_difference(image, expected)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    for key, value in extras.items():
        prior = np.load(packet / reference["artifacts"][key]["file"], allow_pickle=False)
        reason = positioned_line_difference(value, prior)
        assert reason is None, (name, key, reason)
