"""Real pinned DIVE public screenshots; metadata checks never start a GPU."""

import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import tomllib

import numpy as np
import pytest

from tools.fixture_dive import CASES, assert_landmarks, inputs, landmark_spec, render
from tools.host_inventory import source_inventory

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/dive-opengl"
EVIDENCE = ROOT / "build/evidence/dive-candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dive_inputs_and_expected_landmarks_are_fixed_before_rendering():
    for edited in (False, True):
        points = inputs("scatter", edited)
        assert points["x"].tolist() == [-1, 1, .5 if edited else -.5]
        assert points["y"].tolist() == [-1, 1, 0]
        image = inputs("image", edited)["values"]
        assert image.shape == (8, 8) and image.dtype == np.float32
        assert image.min() == 0 and image.max() == 1
        assert image[3, 2] == (0 if edited else 1)
        assert image[3, 5] == (1 if edited else 0)
        assert image[5, 7] == 1
        assert landmark_spec("scatter", edited)["left"]["world"] == [-.25, 0, 0]


@pytest.mark.parametrize("name", CASES)
def test_dive_exact_landmarks_reject_single_interior_pixel_changes(name):
    def frame(edited):
        image = np.zeros((96, 128, 4), np.uint8)
        image[..., 3] = 255
        points = landmark_spec(name, edited)
        for index, record in enumerate(points.values()):
            x, y = 32 + index * 64, 48
            record["pixel"] = [x, y]
            image[y - 1:y + 2, x - 1:x + 2] = record["rgba"]
        return image, points

    edited = name.endswith("_edit")
    image, points = frame(edited)
    before, before_points = frame(False)
    params = {"screenshot_size": [128, 96], "screenshot_api": "DIVEWidget.take_screenshot",
              "landmarks": points, "before_landmarks": before_points}
    assert_landmarks(name, image, params, before=before if edited else None)
    image[48, 32] = [1, 2, 3, 255]
    with pytest.raises(AssertionError, match="analytic 3x3 face landmark"):
        assert_landmarks(name, image, params, before=before if edited else None)


def test_dive_reference_preserves_pins_origins_public_exports_and_unresolved_scope():
    admission = json.loads((ROOT / "tools/oracle_dive_admission.json").read_text())
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    pin = tomllib.loads((ROOT / "compat/hosts.lock.toml").read_text())["dive"]
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["host_commit"] == admission["commit"] == pin["commit"]
    assert origins["host_package_tree_sha256"] == pin["package_tree_sha256"]
    assert origins["host_version_metadata"] is None
    assert "site-packages" in origins["host_origin"]
    assert "dive-cpython311-pyqt5" in origins["python_executable"]
    assert origins["requirements_sha256"] == digest(ROOT / admission["requirements"])
    assert origins["source_inventory_sha256"] == digest(ROOT / admission["source_inventory"])
    assert origins["import_inventory_sha256"] == digest(ROOT / admission["import_inventory"])
    assert origins["fixture_source_sha256"] == digest(ROOT / "tools/fixture_dive.py")
    assert origins["capture_source_sha256"] == digest(ROOT / "tools/oracle_dive_capture.py")
    assert admission["reference_manifest_sha256"] == digest(REFERENCE / "manifest.json")
    assert admission["upstream_qualification"] == ("unresolved" if manifest["errors"] else "partial")
    assert "arrow" in admission["unresolved_fixtures"], "bounded scatter/image proof is not full host admission"
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    assert set(admission["successful_fixtures"]) == set(manifest["fixtures"])
    assert admission["bounded_fixture_qualification"] == ("unresolved" if manifest["errors"] else "passed")
    assert manifest["comparison"] == {"full_frame_exact": True, "landmarks_exact": True,
                                      "landmark_domain": "analytic input through host CPU scene transform"}
    packages = {item["name"].lower(): item["version"] for item in origins["installed"]}
    assert packages["numpy"] == "1.26.4" and packages["pandas"] == "1.5.3"
    assert packages["pyqt5"] == "5.15.11"
    for name, source in admission["source_files"].items():
        records = origins["host_package_sources"] if name.startswith("DIVE/") else origins["host_archived_sources"]
        assert records[name]["sha256"] == source["sha256"]
        assert records[name]["url"] == source["url"]
        assert admission["commit"] in source["url"]
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        for artifact in (record["process"]["stdout"], record["process"]["stderr"]):
            assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
        for artifact in [*record["artifacts"].values(), record["capture"]]:
            assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
        image = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
        before = np.load(REFERENCE / record["artifacts"]["before"]["file"], allow_pickle=False) if name.endswith("_edit") else None
        assert_landmarks(name, image, record["parameters"], before=before)
    for name, error in manifest["errors"].items():
        assert admission["unresolved_fixtures"][name] == error
        assert error["process"]["exit_code"] != 0
        for artifact in (error["process"]["stdout"], error["process"]["stderr"]):
            assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
        for artifact in error.get("unadmitted_artifacts", {}).values():
            assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_real_dive_public_screenshot_matches_independent_opengl(name):
    assert metadata.version("vispy") == "0.17.0+vulkan.1", "candidate installed wheel required"
    assert metadata.version("numpy") == "1.26.4" and metadata.version("pandas") == "1.5.3"
    assert metadata.version("PyQt5") == "5.15.11"
    from vispy import app
    app.use_app("PyQt5")
    import DIVE
    pin = tomllib.loads((ROOT / "compat/hosts.lock.toml").read_text())["dive"]
    assert source_inventory(Path(DIVE.__file__).resolve().parent)["sha256"] == pin["package_tree_sha256"]
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "upstream admission remains unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params, extras = render(name)
    assert commands and shaders
    actual, expected = dict(params), dict(record["parameters"])
    assert "QOpenGLWidget" in expected.pop("native_mro")
    assert "QOpenGLWidget" not in actual.pop("native_mro")
    assert actual == expected
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.candidate.png").write_bytes(extras["png"])
    assert_landmarks(name, image, params, before=extras.get("before"))
    assert np.array_equal(image, reference), (name, "exact public screenshot mismatch", int(difference.max()))
    if name.endswith("_edit"):
        before = np.load(REFERENCE / record["artifacts"]["before"]["file"], allow_pickle=False)
        np.save(EVIDENCE / f"{name}.before.candidate.npy", extras["before"], allow_pickle=False)
        assert np.array_equal(extras["before"], before), "initial exported frame must match too"
    print("DIVE independent public PNG", name, "maxabs", int(difference.max()))
