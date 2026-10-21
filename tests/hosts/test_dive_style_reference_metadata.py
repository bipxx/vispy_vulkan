"""Scoped DIVE render references do not admit ordinary host teardown."""

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/dive-pyside2-style-opengl"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check(base, artifact):
    path = base / artifact["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    return path


def test_restored_style_reference_scope_and_original_failures_are_preserved():
    manifest = _read(REFERENCE / "manifest.json")
    assert set(manifest["fixtures"]) == {"image", "image_edit"}
    assert set(manifest["errors"]) == {"scatter", "scatter_edit"}
    assert "ordinary unchanged host teardown and scatter admission remain unresolved" in manifest["scope"]
    assert manifest["comparison"] == {
        "full_frame_exact": True, "landmarks_exact": True,
        "landmark_domain": "analytic input through host CPU scene transform",
    }
    for name, expected in manifest["preserved_failed_manifests"].items():
        path = ROOT / f"tests/reference/{name}/manifest.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        old = _read(path)
        assert not old["fixtures"] and len(old["errors"]) == 4
        assert all(item["process"]["exit_code"] != 0 for item in old["errors"].values())
    assert hashlib.sha256((ROOT / "tools/oracle_dive_pyside2_style_capture.py").read_bytes()).hexdigest() == manifest["style_runner_sha256"]
    assert hashlib.sha256((ROOT / "tools/oracle_dive_pyside2_cleanup_capture.py").read_bytes()).hexdigest() == manifest["cleanup_runner_sha256"]
    for name, record in {**manifest["fixtures"], **manifest["errors"]}.items():
        assert record["process"]["exit_code"] == (0 if name.startswith("image") else 1)
        for stream in ("stdout", "stderr"):
            _check(REFERENCE, record["process"][stream])
        for key in ("capture", "cleanup", "style_restoration"):
            path = _check(REFERENCE, record[key])
            data = _read(path)
            if key == "cleanup":
                assert data["qapplication_destroyed"] and data["top_level_after"] == []
            elif key == "style_restoration":
                assert data["scope"] == manifest["scope"]
                assert data["phase"] == "DIVEWidget DeferredDelete after the fixture screenshot phase"
                assert len(data["actions"]) == 1
                action = data["actions"][0]
                assert action["receiver"] == "DIVEWidget"
                assert action["previous_owner"] == "SliderStyle"
                assert action["style_name_before"] == action["style_name_after"] == "fusion"
                assert action["public_apis"] == ["QObject.setParent(None)", "QApplication.setStyle('Fusion')"]
        if name.startswith("scatter"):
            assert "_marker_funcs" in record["error"]


def test_style_restoration_changes_only_cleanup_and_keeps_old_rendered_arrays():
    from tools.fixture_dive_pyside2 import assert_landmarks

    manifest = _read(REFERENCE / "manifest.json")
    previous = ROOT / "tests/reference/dive-pyside2-cleanup-opengl"
    old = _read(previous / "manifest.json")
    for name, record in manifest["fixtures"].items():
        before = np.load(_check(REFERENCE, record["artifacts"]["before"])) if "before" in record["artifacts"] else None
        assert_landmarks(name, np.load(_check(REFERENCE, record["artifacts"]["rgba"])), record["parameters"], before=before)
        for key, artifact in record["artifacts"].items():
            _check(REFERENCE, artifact)
            if key in ("rgba", "before", "png", "before_png"):
                earlier = old["errors"][name]["unadmitted_record"]["artifacts"][key]
                assert artifact["sha256"] == earlier["sha256"]
                assert (REFERENCE / artifact["file"]).read_bytes() == _check(previous, earlier).read_bytes()
