# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of test_napari_threedee_overlay_parity.py: the registered napari-threedee layer manipulator's
public Qt workflows versus the installed napari's OpenGL packet.

The comparison is the retained test's (decision D5). tests/contract/test_napari_successor_references.py binds every
packet to the successor fixture, the retained fixture, the plugin capture and the oracle's host lock.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from tools.fixture_napari_threedee_overlay_successor import CASES, assert_landmarks
from tools.napari_host_packets import evidence_dir, installed_packet
from tools.smooth_line_parity import smooth_line_difference

ROOT = Path(__file__).resolve().parents[2]
BASE = "napari-threedee-overlay-opengl"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_python():
    return Path(os.environ.get("VISPY_PLUGIN_CANDIDATE_PYTHON", sys.executable)).resolve(strict=True)


def test_genuine_plugin_wheel_and_registration_proof_without_viewer_or_graphics():
    code = """
import json
import sys
sys.path.insert(0, 'tools')
from PyQt6 import QtGui, QtWidgets
import oracle_napari_plugin_successor_capture as capture
assert QtWidgets.QApplication.instance() is None
record = capture.plugin_provenance('overlay', None)
assert len(record['plugin_files_sha256']) >= 100
assert QtWidgets.QApplication.instance() is None and QtGui.QOpenGLContext.currentContext() is None
assert not any(name == '_dawn' or name.endswith('._dawn') for name in sys.modules)
print(json.dumps({'plugin': record['plugin_version'], 'napari': record['napari_version'],
                  'files_checked': len(record['plugin_files_sha256']), 'widget': record['registered_layer_widget']}))
"""
    env = dict(os.environ, QT_API="pyqt6", QT_QPA_PLATFORM="offscreen")
    child = subprocess.run([str(candidate_python()), "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
    assert child.returncode == 0, (child.returncode, child.stdout, child.stderr)
    record = json.loads(child.stdout)
    assert record["plugin"] == "0.0.29" and record["files_checked"] >= 100
    print("genuine plugin CPU registration, no viewer/graphics", child.stdout.strip())


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_registered_plugin_qt_workflow_matches_independent_upstream(name, tmp_path):
    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert name in manifest["fixtures"], (name, "unresolved upstream admission", manifest["errors"].get(name))
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    plugin = origins["plugin"]
    assert plugin["suite"] == "overlay" and plugin["plugin_version"] == "0.0.29" and plugin["python_hash_seed"] == "0"
    assert "site-packages" in plugin["plugin_origin"]
    record = manifest["fixtures"][name]
    assert record["process"]["exit_code"] == 0
    for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
        assert digest(packet / artifact["file"]) == artifact["sha256"]
    reference = np.load(packet / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    output = tmp_path / name
    child_env = dict(os.environ, PYTHONHASHSEED="0")
    # Every rendering/import/Qt operation runs in the explicit installed candidate interpreter.
    python = candidate_python()
    child = subprocess.run([str(python), "-X", "faulthandler",
                            str(ROOT / "tools/oracle_napari_plugin_successor_native_probe.py"),
                            "--suite", "overlay", "--output", str(output), "--fixture", name],
                           env=child_env, cwd=ROOT, capture_output=True, text=True)
    # Keep complete diagnostics even when a Qt/native callback aborts before
    # the worker can create a render manifest.
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
    assert candidate["process"]["exit_code"] == 0
    proof_artifact = candidate["native_proof"]
    assert digest(output / proof_artifact["file"]) == proof_artifact["sha256"]
    proof = json.loads((output / proof_artifact["file"]).read_text(encoding="utf-8"))
    assert proof["worker_result"] == 0 and proof["candidate_version"] == "0.17.0+vulkan.1"
    assert proof["probe"]["draw_calls"] > 0 and proof["probe"]["pipeline_misses"] > 0
    assert proof["probe"]["dawn_queue_submits"] > 0
    params = candidate["parameters"]
    artifacts = candidate["artifacts"]
    image = np.load(output / artifacts["rgba"]["file"], allow_pickle=False)
    commands = json.loads((output / artifacts["filtered_glir"]["file"]).read_text(encoding="utf-8"))
    shaders = json.loads((output / artifacts["expanded_shaders"]["file"]).read_text(encoding="utf-8"))
    extras = {key: np.load(output / artifact["file"], allow_pickle=False) for key, artifact in artifacts.items()
              if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
    assert commands and shaders
    assert_landmarks(name, image, params, extras)
    for key in ("case", "input", "size", "camera", "volume_blending", "origin", "radius", "handle_size", "handle_world", "picking", "comparison", "stages", "initial_projection", "final_projection"):
        assert params[key] == record["parameters"][key], (name, key)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence = evidence_dir("napari-threedee-overlay-successor-candidate", origins["napari_version"])
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    # Smooth-line coverage is driver-defined: interiors exact, antialiased edges bounded.
    reason = smooth_line_difference(image, reference)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    for key, value in extras.items():
        prior = np.load(packet / record["artifacts"][key]["file"], allow_pickle=False)
        reason = smooth_line_difference(value, prior)
        assert reason is None, (name, key, reason)
    print("registered plugin public Qt workflow", name, "smooth-line parity", image.shape,
          "differing", int(np.any(difference, axis=2).sum()), "max", int(difference.max()))
    print("actual installed candidate pipeline", proof["native_origin"], proof["native_sha256"], proof["device_info"], proof["probe"])
