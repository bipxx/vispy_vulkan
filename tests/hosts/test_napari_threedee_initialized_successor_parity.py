# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of test_napari_threedee_initialized_parity.py: the registered plugin's retirement workflow,
initialized before the plugin is constructed, versus the installed napari's OpenGL packet.

Only retirement carries over: the other four initialized cases are D6's superseded fixtures, replaced by the overlay
suite. The comparison is the retained test's (decision D5). tests/contract/test_napari_successor_references.py binds
every packet to the successor fixture, the retained fixture, the plugin capture and the oracle's host lock.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from tools.fixture_napari_threedee_initialized_successor import assert_landmarks
from tools.napari_host_packets import evidence_dir, installed_packet
from tools.smooth_line_parity import smooth_line_difference

ROOT = Path(__file__).resolve().parents[2]
BASE = "napari-threedee-initialized-opengl"
LIVE = ("retirement",)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.gpu
@pytest.mark.parametrize("name", LIVE)
def test_registered_plugin_qt_workflow_matches_independent_upstream(name, tmp_path):
    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert name in manifest["fixtures"], (name, "unresolved upstream admission", manifest["errors"].get(name))
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    plugin = origins["plugin"]
    assert plugin["suite"] == "initialized" and plugin["plugin_version"] == "0.0.29" and plugin["python_hash_seed"] == "0"
    assert "site-packages" in plugin["plugin_origin"]
    record = manifest["fixtures"][name]
    assert record["process"]["exit_code"] == 0
    for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
        assert digest(packet / artifact["file"]) == artifact["sha256"]
    reference = np.load(packet / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    output = tmp_path / name
    child_env = dict(os.environ, PYTHONHASHSEED="0")
    # Every rendering/import/Qt operation runs in the explicit installed
    # candidate interpreter, as in the overlay and render-plane suites.
    candidate_python = Path(os.environ.get("VISPY_PLUGIN_CANDIDATE_PYTHON", sys.executable)).resolve(strict=True)
    child = subprocess.run([str(candidate_python), "-X", "faulthandler",
                            str(ROOT / "tools/oracle_napari_plugin_successor_capture.py"), "--suite", "initialized",
                            "--kind", "candidate", "--output", str(output), "--fixtures", name],
                           env=child_env, cwd=ROOT, capture_output=True, text=True)
    assert child.returncode == 0, (name, child.returncode, child.stdout, child.stderr)
    produced = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert produced["provenance"]["napari_version"] == origins["napari_version"], "candidate runs another napari"
    candidate = produced["fixtures"][name]
    assert candidate["process"]["exit_code"] == 0
    params = candidate["parameters"]
    artifacts = candidate["artifacts"]
    image = np.load(output / artifacts["rgba"]["file"], allow_pickle=False)
    commands = json.loads((output / artifacts["filtered_glir"]["file"]).read_text(encoding="utf-8"))
    shaders = json.loads((output / artifacts["expanded_shaders"]["file"]).read_text(encoding="utf-8"))
    extras = {key: np.load(output / artifact["file"], allow_pickle=False) for key, artifact in artifacts.items()
              if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
    assert commands and shaders
    assert_landmarks(name, image, params, extras)
    for key in ("case", "input", "size", "camera", "origin", "radius", "handle_size", "handle_world", "picking", "comparison", "stages", "initial_projection", "final_projection"):
        assert params[key] == record["parameters"][key], (name, key)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence = evidence_dir("napari-threedee-initialized-successor-candidate", origins["napari_version"])
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    # Smooth-line coverage is driver-defined: interiors exact, antialiased edges bounded (decision D5).
    reason = smooth_line_difference(image, reference)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    for key, value in extras.items():
        prior = np.load(packet / record["artifacts"][key]["file"], allow_pickle=False)
        reason = smooth_line_difference(value, prior)
        assert reason is None, (name, key, reason)
    print("registered plugin public Qt workflow", name, "smooth-line parity", image.shape)
