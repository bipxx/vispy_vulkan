"""Reference metadata/contracts only. This module must not initialize a GPU."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.fixture_gloo import FIXTURES, assert_expected_regions
from tools.fixture_napari import CASES as NAPARI_CASES, assert_landmarks
from tools.fixture_volume import CASES as VOLUME_CASES, METHODS, assert_landmarks as volume_landmarks
from tools.fixture_napari_volume import CASES as CATEGORICAL_CASES, assert_landmarks as categorical_landmarks
from tools.fixture_scene import CASES as SCENE_CASES, EXACT as SCENE_EXACT, assert_landmarks as scene_landmarks
from tools.fixture_scene import MARKERS, SYMBOLS
from tools.fixture_revisions import CASES as REVISION_CASES, assert_expected as revision_expected, assert_trace as revision_trace

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/opengl"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("failure", ["stale_record", "nonzero_after_record"])
def test_capture_worker_failure_cannot_admit_a_previous_or_partial_record(tmp_path, monkeypatch, failure):
    # Exercise the CLI parent path with a controlled failing worker. No VisPy
    # import, device, or real capture is used by this harness regression.
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("oracle_parent_regression", ROOT / "tools/oracle_capture.py")
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    monkeypatch.setattr(capture, "provenance", lambda kind: {})
    name = "uniform_snapshot"
    path = tmp_path / f"{name}.capture.json"
    record = {"fixtures": {name: {"untrusted": True}}, "errors": {}}
    path.write_text(json.dumps(record))

    def failed_worker(*args, **kwargs):
        assert not path.exists(), "a prior successful record must be removed before rerun"
        if failure == "nonzero_after_record":
            path.write_text(json.dumps(record))
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(capture.subprocess, "run", failed_worker)
    monkeypatch.setattr(capture.sys, "argv", ["oracle_capture.py", "--kind", "candidate",
                                            "--output", str(tmp_path), "--fixtures", name])
    assert capture.main()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["fixtures"] == {}
    assert name in manifest["errors"]


def test_inventory_names_pins_and_keeps_visbrain_and_phylib_out():
    lock = (ROOT / "compat/hosts.lock.toml").read_text(encoding="utf-8")
    reference = (ROOT / "tests/reference/inventory.json").read_text(encoding="utf-8")
    for pin in (
        "117b054598f4758b598f4b8f48feea48c11fe7b0",
        "595639295a153c84bcb127a9e07d801355440a35",
        "33509adb53909b7542069563f77fb9a80bd565a4",
        "1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6",
        "457915ba7ef9063504484769d775b3bb1ccfd74a",
        "aa575e1c020f0c5e8227bfb234fa192fa2b12924",
        "7bd485085186ebe1907f8de931aa7a93e0d58a83",
        "499e5c6ff9b37d5de70c6493fb74c251e0d35c1c",
    ):
        assert pin in lock
        assert pin in reference
    assert "rendering = false" in lock and "gpu = false" in lock
    assert "phy GUI" in lock
    assert "visbrain" not in reference.split("rendering_matrix")[1]


def test_every_oracle_has_independent_provenance_and_reproducible_artifacts():
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(FIXTURES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream"
    assert provenance["vispy_version"] == provenance["versions"]["vispy"] == "0.17.0"
    assert provenance["upstream_commit"] == "117b054598f4758b598f4b8f48feea48c11fe7b0"
    assert "site-packages" in provenance["vispy_origin"]
    assert "oracle-opengl" in provenance["python_executable"]
    assert "Dawn" not in provenance["renderer"]["renderer"]
    assert provenance["renderer"]["version"].startswith("4.")
    assert provenance["environment"]["QT_QPA_PLATFORM"] != "offscreen"
    assert provenance["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_gloo.py")
    assert provenance["capture_source_sha256"] == sha256(ROOT / "tools/oracle_capture.py")
    assert provenance["requirements_sha256"] == sha256(ROOT / "tools/oracle_requirements.txt")
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text(encoding="utf-8"))
    for path, actual in provenance["source_sha256"].items():
        assert actual == pinned["files"][path]
    assert manifest["comparison"] == {
        "interior_max_abs_u8": 2, "edge_max_differing_fraction": .001,
        "categorical_exact": True, "mask": "tools.fixture_gloo.comparison_masks",
    }
    for name, fixture in manifest["fixtures"].items():
        assert fixture["readbacks"] == (2 if name == "shared_canvases" else 1)
        assert fixture["edge_columns"] == list(FIXTURES[name].edge_columns)
        assert fixture["edge_rows"] == list(FIXTURES[name].edge_rows)
        for artifact in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            entry = fixture[artifact]
            file = REFERENCE / entry["file"]
            assert file.is_file(), file
            assert sha256(file) == entry["sha256"], file
        image = np.load(REFERENCE / fixture["rgba"]["file"], allow_pickle=False)
        assert image.shape == tuple(fixture["shape"])
        assert_expected_regions(name, image)
        trace = json.loads((REFERENCE / fixture["filtered_glir"]["file"]).read_text())
        assert any(command[0] == "CURRENT" for command in trace)
        if name != "clear_only_fbo":
            assert any(command[0] == "DRAW" for command in trace)
            shaders = json.loads((REFERENCE / fixture["expanded_shaders"]["file"]).read_text())
            assert len(shaders) >= 2 and all("void main" in text for text in shaders.values())


def test_napari_oracles_record_host_lock_and_separate_installed_upstream():
    reference = ROOT / "tests/reference/napari-opengl"
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(NAPARI_CASES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream"
    assert provenance["vispy_version"] == "0.17.0"
    assert provenance["napari_version"] == "0.9.2"
    assert "site-packages" in provenance["napari_origin"]
    assert "oracle-napari" in provenance["python_executable"]
    assert provenance["host_requirements_sha256"] == sha256(ROOT / "tools/oracle_napari_requirements.txt")
    assert provenance["host_fixture_sha256"] == sha256(ROOT / "tools/fixture_napari.py")
    assert provenance["host_capture_sha256"] == sha256(ROOT / "tools/oracle_napari_capture.py")
    assert provenance["installed"]["numba"] == "0.68.0"
    for name, fixture in manifest["fixtures"].items():
        for artifact in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            item = fixture[artifact]
            file = reference / item["file"]
            assert file.is_file() and sha256(file) == item["sha256"]
        image = np.load(reference / fixture["rgba"]["file"], allow_pickle=False)
        assert_landmarks(name, image)
        assert fixture["parameters"]["camera_rect"] == [-.5, -.5, 32, 24]
        assert fixture["parameters"]["inputs"]
        assert "QOpenGLWidget" in fixture["parameters"]["native_mro"]


def test_scalar_volume_oracles_record_actual_methods_parameters_and_sources():
    reference = ROOT / "tests/reference/volume-opengl"
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(VOLUME_CASES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream"
    assert provenance["vispy_version"] == "0.17.0"
    assert "oracle-opengl" in provenance["python_executable"]
    assert provenance["volume_fixture_sha256"] == sha256(ROOT / "tools/fixture_volume.py")
    assert provenance["volume_capture_sha256"] == sha256(ROOT / "tools/oracle_volume_capture.py")
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text(encoding="utf-8"))
    for path, actual in provenance["volume_source_sha256"].items():
        assert actual == pinned["files"][path]
    assert manifest["comparison"] == {
        "interior_max_abs_u8": 2, "edge_max_differing_fraction": .001,
        "landmark_exact": True, "mask": "tools.fixture_volume.masks",
    }
    for name, fixture in manifest["fixtures"].items():
        for artifact in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            item = fixture[artifact]
            file = reference / item["file"]
            assert file.is_file() and sha256(file) == item["sha256"]
        params = fixture["parameters"]
        assert set(params["exposed_methods"]) == set(METHODS)
        assert params["exposed_raycasting_modes"] == ["volume", "plane"]
        assert params["relative_step_size"] == .5
        assert params["shape"] == [32, 32, 32]
        assert params["dtype"] == "<f4"
        assert params["texture_format"] == "r32f"
        assert params["clim"] == [0, 1]
        volume_landmarks(name, np.load(reference / fixture["rgba"]["file"], allow_pickle=False))
        trace = json.loads((reference / fixture["filtered_glir"]["file"]).read_text())
        assert any(command[0] == "DRAW" for command in trace)
        shaders = json.loads((reference / fixture["expanded_shaders"]["file"]).read_text())
        assert any("view_ray" in text and "u_shape" in text for text in shaders.values())


def test_categorical_volume_oracles_record_sparse_ids_host_shaders_and_actual_frames():
    reference = ROOT / "tests/reference/napari-volume-opengl"
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(CATEGORICAL_CASES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream"
    assert provenance["vispy_version"] == "0.17.0" and provenance["napari_version"] == "0.9.2"
    assert "oracle-napari" in provenance["python_executable"]
    assert provenance["volume_fixture_sha256"] == sha256(ROOT / "tools/fixture_napari_volume.py")
    assert provenance["volume_capture_sha256"] == sha256(ROOT / "tools/oracle_napari_volume_capture.py")
    assert provenance["host_requirements_sha256"] == sha256(ROOT / "tools/oracle_napari_requirements.txt")
    assert provenance["installed"]["numba"] == "0.68.0"
    assert set(provenance["host_source_sha256"]) == {
        "_vispy/visuals/volume.py", "_vispy/layers/labels.py", "_vispy/camera.py"}
    assert manifest["comparison"] == {"categorical_exact": True, "landmark_exact": True}
    for name, fixture in manifest["fixtures"].items():
        for artifact in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            item = fixture[artifact]
            file = reference / item["file"]
            assert file.is_file() and sha256(file) == item["sha256"]
        params = fixture["parameters"]
        assert params["labels"] == [0, 7, 65537, 16777473]
        assert params["relative_step_size"] == .5
        assert params["inputs"][0]["shape"] == [32, 32, 32]
        assert params["inputs"][0]["dtype"] == "<i4"
        assert "QOpenGLWidget" in params["native_mro"]
        categorical_landmarks(name, np.load(reference / fixture["rgba"]["file"], allow_pickle=False))
        shaders = json.loads((reference / fixture["expanded_shaders"]["file"]).read_text())
        assert any("sample_label_color" in text and "view_ray" in text for text in shaders.values())


def test_scene_oracles_record_fixed_geometry_font_license_and_cpu_atlases():
    reference = ROOT / "tests/reference/scene-opengl"
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(SCENE_CASES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "oracle-opengl" in provenance["python_executable"]
    assert provenance["scene_fixture_sha256"] == sha256(ROOT / "tools/fixture_scene.py")
    assert provenance["scene_capture_sha256"] == sha256(ROOT / "tools/oracle_scene_capture.py")
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text(encoding="utf-8"))
    for path, actual in provenance["scene_source_sha256"].items():
        assert actual == pinned["files"][path]
    for name, fixture in manifest["fixtures"].items():
        extras = {}
        artifacts = ["rgba", "filtered_glir", "expanded_shaders", "capture"]
        if name.startswith("text_"):
            artifacts.append("cpu_atlas")
        for artifact in artifacts:
            item = fixture[artifact]
            file = reference / item["file"]
            assert file.is_file() and sha256(file) == item["sha256"]
            if artifact == "cpu_atlas":
                extras[artifact] = np.load(file, allow_pickle=False)
        assert fixture["exact"] == (name in SCENE_EXACT)
        if name.startswith("text_"):
            params = fixture["parameters"]
            assert params["font_sha256"] == pinned["files"]["util/fonts/data/OpenSans-Regular.ttf"]
            assert params["font_license"] == "Apache License, Version 2.0 (font SFNT name ID 13)"
            assert params["method"] == "cpu" and params["face"] == "OpenSans"
            assert params["dpi"] == int(name.removeprefix("text_dpi"))
            assert "Ag 15" == params["text"]
        scene_landmarks(name, np.load(reference / fixture["rgba"]["file"], allow_pickle=False), extras)


@pytest.mark.parametrize("index", range(6), ids=SYMBOLS)
def test_marker_symbol_center_change_fails_exact_scientific_landmark(index):
    # Regression for the former whole-box edge mask admitting a corrupted
    # marker interior. This is a metadata/pixel check and creates no device.
    image = np.load(ROOT / "tests/reference/scene-opengl/marker_symbols.npy", allow_pickle=False)
    scene_landmarks("marker_symbols", image, {})
    x, y = MARKERS[index].astype(int)
    image[y, x] = [255, 255, 255, 255]
    with pytest.raises(AssertionError):
        scene_landmarks("marker_symbols", image, {})


def test_texture_revision_oracles_prove_pending_draw_update_order_and_rendered_contents():
    reference = ROOT / "tests/reference/texture-revisions-opengl"
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(REVISION_CASES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "site-packages" in provenance["vispy_origin"]
    assert "oracle-opengl" in provenance["python_executable"]
    assert provenance["revision_fixture_sha256"] == sha256(ROOT / "tools/fixture_revisions.py")
    assert provenance["revision_capture_sha256"] == sha256(ROOT / "tools/oracle_revisions_capture.py")
    assert provenance["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_gloo.py")
    assert provenance["requirements_sha256"] == sha256(ROOT / "tools/oracle_requirements.txt")
    assert manifest["comparison"] == {"rgba_exact": True, "analytic_expected_exact": True}
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text(encoding="utf-8"))
    for path, actual in provenance["source_sha256"].items():
        assert actual == pinned["files"][path]
    for name, fixture in manifest["fixtures"].items():
        assert fixture["readbacks"] == fixture["parameters"]["final_readbacks"] == 1
        assert not fixture["parameters"]["intermediate_finish"]
        assert not fixture["parameters"]["intermediate_present"]
        assert fixture["parameters"]["prewarm_presents"] == (
            1 if name.startswith("sampler_wrapping_") else 0)
        for artifact in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            item = fixture[artifact]
            path = reference / item["file"]
            assert path.is_file() and sha256(path) == item["sha256"]
        revision_expected(name, np.load(reference / fixture["rgba"]["file"], allow_pickle=False))
        revision_trace(name, json.loads((reference / fixture["filtered_glir"]["file"]).read_text()))
