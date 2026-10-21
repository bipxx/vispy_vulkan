"""Preserve public plugin authoring attempts and their honest admissions."""

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_initial_plugin_attempt_preserves_upstream_bounds_failures():
    base = ROOT / "tests/reference/napari-threedee-opengl"
    manifest = json.loads((base / "manifest.json").read_text())
    assert not manifest["fixtures"] and len(manifest["errors"]) == 5
    plugin = manifest["provenance"]["plugin"]
    assert plugin["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_napari_threedee.py")
    assert plugin["capture_source_sha256"] == sha256(ROOT / "tools/oracle_napari_threedee_capture.py")
    for record in manifest["errors"].values():
        assert record["process"]["exit_code"] == 1
        assert "NoneType" in record["error"]
        for artifact in [record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(base / artifact["file"]) == artifact["sha256"]
        stderr = (base / record["process"]["stderr"]["file"]).read_text()
        assert "viewer.dims.ndisplay = 2" in stderr and "markers.py" in stderr and "_compute_bounds" in stderr


def test_initialized_plugin_retirement_pass_is_scoped_and_failures_are_not_admitted():
    from tools.fixture_napari_threedee_initialized import assert_landmarks

    base = ROOT / "tests/reference/napari-threedee-initialized-opengl"
    manifest = json.loads((base / "manifest.json").read_text())
    assert set(manifest["fixtures"]) == {"retirement"}
    assert set(manifest["errors"]) == {"handles", "selection", "translation", "miss"}
    plugin = manifest["provenance"]["plugin"]
    assert "mandatory post-activation 2D/3D transitions retained" in plugin["public_initialization"]
    assert plugin["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_napari_threedee_initialized.py")
    assert plugin["capture_source_sha256"] == sha256(ROOT / "tools/oracle_napari_threedee_initialized_capture.py")
    record = manifest["fixtures"]["retirement"]
    assert record["process"]["exit_code"] == 0
    for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
        assert sha256(base / artifact["file"]) == artifact["sha256"]
    image = np.load(base / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    assert_landmarks("retirement", image, record["parameters"], {})
    stages = record["parameters"]["stages"]
    assert next(stage for stage in stages if stage["stage"] == "activated")["owned_callbacks"] == [True, True]
    assert next(stage for stage in stages if stage["stage"] == "two_dimensional")["owned_callbacks"] == [False, False]
    assert stages[-1]["stage"] == "layer_removed" and stages[-1]["owned_callbacks"] == [False, False]
    for error in manifest["errors"].values():
        assert error["process"]["exit_code"] == 1 and error["type"] == "AssertionError"
        assert "array([0, 0, 0])" in error["error"]


def test_visible_overlay_plugin_references_keep_real_events_state_and_exact_pixels():
    from tools.fixture_napari_threedee_overlay import CASES, assert_landmarks, specification

    base = ROOT / "tests/reference/napari-threedee-overlay-opengl"
    manifest = json.loads((base / "manifest.json").read_text())
    assert set(manifest["fixtures"]) == set(CASES) and not manifest["errors"]
    assert manifest["comparison"] == {
        "full_frame_exact": True, "fixed_cpu_projection_landmarks": True,
        "actual_qt_events": True, "picking": "installed CPU ray/sphere callbacks",
    }
    plugin = manifest["provenance"]["plugin"]
    assert plugin["plugin_wheel_sha256"] == "de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e"
    assert plugin["python_hash_seed"] == "0" and len(plugin["plugin_files_sha256"]) == 116
    assert "opaque depth occlusion remains preserved and is valid renderer behavior" in plugin["public_volume_blending"]
    assert plugin["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_napari_threedee_overlay.py")
    assert plugin["capture_source_sha256"] == sha256(ROOT / "tools/oracle_napari_threedee_overlay_capture.py")
    for filename, expected in plugin["evidence_sha256"].items():
        assert sha256(ROOT / "compat/host-environments" / filename) == expected
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(base / artifact["file"]) == artifact["sha256"]
        params = record["parameters"]
        assert params["volume_blending"] == "translucent_no_depth"
        for key, value in specification(name).items():
            assert params[key] == value, (name, key)
        image = np.load(base / record["artifacts"]["rgba"]["file"], allow_pickle=False)
        extras = {key: np.load(base / artifact["file"], allow_pickle=False) for key, artifact in record["artifacts"].items()
                  if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
        assert_landmarks(name, image, params, extras)
    handles = manifest["fixtures"]["handles"]["artifacts"]["rgba"]["sha256"]
    assert handles == manifest["fixtures"]["miss"]["artifacts"]["rgba"]["sha256"]
    assert handles != manifest["fixtures"]["selection"]["artifacts"]["rgba"]["sha256"]
    assert handles != manifest["fixtures"]["translation"]["artifacts"]["rgba"]["sha256"]
