"""Actual three-pixel/smooth GL coverage, interpolation and pending state."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_wide_lines import CASES, DOUBLE_QUARTER_GREEN, SIZE, assert_landmarks, clip_positions, landmarks, render, specification
from tools.wide_lines_comparison import CANONICAL_SHARED_FIXTURE_SHA256, CAPTURED_SHARED_FIXTURE_SHA256, wide_line_difference

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/wide-lines-opengl"
EVIDENCE = ROOT / "build/evidence/wide-lines-candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_wide_line_analytic_inputs_and_coverage_criteria_are_fixed_before_capture():
    for name in CASES:
        spec = specification(name)
        assert spec["line_width"] == 3 and spec["readbacks"] == 1 and not spec["intermediate_finish"]
        assert spec["line_smooth"] == (not name.endswith("aliased"))
        assert "no masks" in spec["comparison"]
        assert spec["vertices_sha256"] == hashlib.sha256(clip_positions(spec["points"], -.5 if name == "depth_occlusion_smooth" else 0., spec["weights"]).tobytes()).hexdigest()
    assert specification("diagonal_smooth_forward")["points"] == specification("diagonal_smooth_reverse")["points"][::-1]
    assert specification("ordered_width_smooth")["ordered_widths"] == [3., 1.]
    assert ([15, 7], DOUBLE_QUARTER_GREEN) in landmarks("strip_alpha_smooth")
    # A width-one substitute cannot pass the independent three-row interiors.
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    image[SIZE[1] - 1 - 6, 4:29] = [0, 255, 0, 255]
    with pytest.raises(AssertionError, match="fixed wide-line landmark"):
        assert_landmarks("horizontal_aliased", image)


def test_wide_line_reference_keeps_actual_driver_advertisement_and_exit_qualification():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert "site-packages" in origins["vispy_origin"] and "oracle-opengl" in origins["python_executable"]
    assert origins["renderer"]["version"].startswith("4.")
    # Decision D16: captured with the shared fixture before its reviewed replacement (only the depth clear added).
    assert origins["wide_fixture_sha256"] == CAPTURED_SHARED_FIXTURE_SHA256
    assert digest(ROOT / "tools/fixture_wide_lines.py") == CANONICAL_SHARED_FIXTURE_SHA256
    assert origins["wide_capture_sha256"] == digest(ROOT / "tools/oracle_wide_lines_capture.py")
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    assert manifest["comparison"] == {"full_frame_exact": True, "fixed_landmarks_exact": True}
    for name, record in manifest["fixtures"].items():
        assert record["parameters"] == specification(name) and record["process"]["exit_code"] == 0
        observed = json.loads((REFERENCE / record["observations"]["file"]).read_text())
        assert observed["physical_samples"] == 1 and observed["samples_raw"] in (0, 1)
        assert observed["sample_query_kind"] == "actual OpenGL target"
        assert observed["state_query_kind"] == "actual OpenGL driver after final readback"
        assert observed["line_width"] == (1 if name == "ordered_width_smooth" else 3)
        assert observed["line_smooth_enabled"] == specification(name)["line_smooth"]
        assert observed["smooth_line_width_range"][1] >= 3
        for entry in [*(record[key] for key in ("rgba", "filtered_glir", "expanded_shaders", "observations", "capture")), record["process"]["stdout"], record["process"]["stderr"]]:
            assert digest(REFERENCE / entry["file"]) == entry["sha256"]
        assert_landmarks(name, np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))
    for failure in manifest["errors"].values():
        assert failure["process"]["exit_code"] != 0
        for entry in [*failure["unadmitted_artifacts"].values(), failure["process"]["stdout"], failure["process"]["stderr"]]:
            assert digest(REFERENCE / entry["file"]) == entry["sha256"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_native_wide_smooth_line_matches_independent_exact_driver(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "upstream admission unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    image, commands, shaders, params, observed = render(name)
    assert commands and shaders and params == record["parameters"]
    assert observed["physical_samples"] == 1
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert_landmarks(name, image)
    # Decision D15: smooth cases drop only the smooth-line frame cap, with exact alpha; aliased cases stay exact.
    reason = wide_line_difference(specification(name)["line_smooth"], image, reference)
    assert reason is None, (name, reason, int(difference.max()), int(np.any(difference, axis=2).sum()))
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
