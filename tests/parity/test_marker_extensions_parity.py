"""Required actual marker methods/depth/revisions with independent references."""

import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

from tools.fixture_marker_extensions import (CASES, COMPARISON, RGB, CMY, REV_POS,
    array_record, assert_landmarks, assert_trace, case_contract, landmarks, render, specification)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/marker-extensions-opengl"
EVIDENCE = ROOT / "build/evidence/marker-extensions-candidate"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_marker_contracts_are_frozen_before_candidate():
    authoring = json.loads((REFERENCE / "authoring.json").read_text())
    assert authoring["candidate_seen"] is False and authoring["GPU_used"] is False
    assert authoring["comparison"] == COMPARISON
    assert authoring["cases"] == {name: case_contract(name) for name in CASES}
    assert len(CASES) == 14
    for source, digest in authoring["sources_sha256"].items():
        assert sha(ROOT / source) == digest


def test_marker_revision_sentinels_change_only_declared_source_fields():
    before = specification("points_color_revision")["input"]
    after = specification("points_color_revision")["updated_input"]
    assert np.array_equal(before["pos"], after["pos"])
    assert np.array_equal(before["face_color"], RGB) and np.array_equal(after["face_color"], CMY)
    position = specification("instanced_position_revision")
    assert np.array_equal(position["input"]["face_color"], position["updated_input"]["face_color"])
    assert np.array_equal(position["updated_input"]["pos"] - REV_POS, np.tile([16, 48, 0], (3, 1)))
    assert array_record(position["input"]["pos"]) != array_record(position["updated_input"]["pos"])


def test_analytic_scaling_and_spherical_occlusion_landmarks_are_distinct():
    fringe = [(name, [entry for entry in landmarks(name) if entry["column"] in (39, 46)])
              for name in ("points_camera_fixed", "points_camera_scene", "points_camera_visual")]
    assert len({json.dumps(entries, sort_keys=True) for _, entries in fringe}) == 3
    sphere = specification("points_spherical_depth")["depth_geometry"]
    center = sphere["sphere_center_window_depth"] + sphere["sphere_center_depth_change"]
    rim = .5 - .1 * np.sqrt(1 - (19 / 20) ** 2)
    assert center < sphere["front_mesh_window_depth"] < rim
    assert all(specification(name)["readbacks"] == 1 for name in CASES)
    assert all(not specification(name)["dependent_intermediate_present_or_finish"] for name in CASES)


def test_public_marker_constructor_and_canonical_layout_without_graphics():
    from vispy.visuals import MarkersVisual

    for name in CASES:
        spec = specification(name)
        visual = MarkersVisual(method=spec["method"], scaling=spec["scaling"],
                               antialias=spec["antialias"], spherical=spec["spherical"])
        visual.set_data(**spec["input"])
        assert visual._data.dtype.names == ("a_position", "a_fg_color", "a_bg_color",
                                           "a_size", "a_edgewidth", "a_symbol")
        assert np.array_equal(visual._data["a_position"], spec["input"]["pos"])
        assert visual.scaling == spec["scaling"] and visual.spherical == spec["spherical"]
        if "updated_input" in spec:
            before = visual._data.copy()
            visual.set_data(**spec["updated_input"])
            if spec["workflow"] == "color_revision":
                for field in before.dtype.names:
                    if field != "a_bg_color":
                        assert np.array_equal(before[field], visual._data[field]), field
            else:
                for field in before.dtype.names:
                    if field != "a_position":
                        assert np.array_equal(before[field], visual._data[field]), field


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_marker_methods_depth_and_revisions_match_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert manifest["provenance"]["kind"] == "upstream"
    assert manifest["comparison"] == COMPARISON
    assert manifest["processes"][name]["exit_code"] == 0
    record = manifest["fixtures"][name]
    assert record["parameters"] == case_contract(name)
    assert record["observations"]["physical_samples"] == 1
    assert record["observations"]["sample_source"] == "OpenGL driver GL_SAMPLES"
    artifact = record["artifacts"]["rgba"]
    assert sha(REFERENCE / artifact["file"]) == artifact["sha256"]
    reference = np.load(REFERENCE / artifact["file"], allow_pickle=False)
    image, commands, shaders, params, observations = render(name)
    assert params == record["parameters"]
    assert commands and shaders and observations["readbacks"] == 1
    assert_trace(name, commands, observations)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.observations.json").write_text(json.dumps(observations, indent=2, sort_keys=True))
    assert np.array_equal(image, reference), (name, int(difference.max()), int(np.count_nonzero(np.any(difference, axis=2))))
    assert_landmarks(name, image)
    if specification(name)["prewarm_submission_without_read"]:
        before, after = observations["native_before_dependent_draws"], observations["native_after_final_read"]
        for counter in ("buffer_uploads", "texture_uploads", "pipeline_misses", "portable_shader_misses",
                        "point_conversion_builds", "point_conversion_bytes"):
            assert after[counter] == before[counter], (name, counter, before[counter], after[counter])
