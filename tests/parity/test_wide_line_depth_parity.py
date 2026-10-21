"""Fixed three-pixel depth fixture with a publicly initialized attachment."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_wide_lines import landmarks, specification as old_specification
from tools.fixture_wide_lines_depth import CASES, assert_landmarks, render, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/wide-lines-depth-opengl"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_defined_depth_variant_preserves_geometry_landmarks_and_old_failure():
    params = specification(CASES[0])
    assert params.pop("public_initial_depth_clear") == 1
    assert params.pop("explicit_depth_func") == "less"
    assert params == old_specification(CASES[0])
    assert ([16, 12], [255, 0, 0, 255]) in landmarks(CASES[0])
    old = json.loads((ROOT / "tests/reference/wide-lines-opengl/manifest.json").read_text())
    assert CASES[0] in old["errors"] and CASES[0] not in old["fixtures"]
    assert old["errors"][CASES[0]]["process"]["exit_code"] == 1
    assert "fixed wide-line landmark" in old["errors"][CASES[0]]["error"]
    assert old["provenance"]["wide_fixture_sha256"] == digest(ROOT / "tools/fixture_wide_lines.py")
    assert old["provenance"]["wide_capture_sha256"] == digest(ROOT / "tools/oracle_wide_lines_capture.py")


def test_defined_depth_reference_preserves_actual_driver_state_and_ordered_clear():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert set(manifest["fixtures"]) == set(CASES) and not manifest["errors"]
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["wide_fixture_sha256"] == digest(ROOT / "tools/fixture_wide_lines_depth.py")
    assert origins["shared_fixed_fixture_sha256"] == digest(ROOT / "tools/fixture_wide_lines.py")
    assert origins["wide_capture_sha256"] == digest(ROOT / "tools/oracle_wide_lines_depth_capture.py")
    record = manifest["fixtures"][CASES[0]]
    assert record["parameters"] == specification(CASES[0]) and record["process"]["exit_code"] == 0
    for artifact in [*(record[key] for key in ("rgba", "filtered_glir", "expanded_shaders", "observations", "capture")), record["process"]["stdout"], record["process"]["stderr"]]:
        assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
    observed = json.loads((REFERENCE / record["observations"]["file"]).read_text())
    assert observed["physical_samples"] == 1 and observed["sample_query_kind"] == "actual OpenGL target"
    assert observed["depth_func"] == 0x0201 and observed["line_width"] == 3 and observed["line_smooth_enabled"]
    trace = json.loads((REFERENCE / record["filtered_glir"]["file"]).read_text())
    first_draw = next(index for index, command in enumerate(trace) if command[0] == "DRAW")
    assert trace.index(["FUNC", "glClearDepth", 1.]) < trace.index(["FUNC", "glClear", 256]) < first_draw
    assert trace.index(["FUNC", "glDepthFunc", "less"]) < first_draw
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in trace) == 1
    assert_landmarks(CASES[0], np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))


@pytest.mark.gpu
def test_native_initialized_wide_smooth_depth_matches_exact_gl_driver():
    name = CASES[0]
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], ("depth initialization upstream admission pending", manifest["errors"])
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["wide_fixture_sha256"] == digest(ROOT / "tools/fixture_wide_lines_depth.py")
    assert origins["shared_fixed_fixture_sha256"] == digest(ROOT / "tools/fixture_wide_lines.py")
    assert origins["wide_capture_sha256"] == digest(ROOT / "tools/oracle_wide_lines_depth_capture.py")
    record = manifest["fixtures"][name]
    assert record["process"]["exit_code"] == 0 and record["parameters"] == specification(name)
    for artifact in [*(record[key] for key in ("rgba", "filtered_glir", "expanded_shaders", "observations", "capture")), record["process"]["stdout"], record["process"]["stderr"]]:
        assert digest(REFERENCE / artifact["file"]) == artifact["sha256"]
    expected = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params, observed = render(name)
    assert params == record["parameters"] and commands and shaders and observed["physical_samples"] == 1
    assert_landmarks(name, image)
    output = ROOT / "build/evidence/wide-lines-depth-candidate"
    output.mkdir(parents=True, exist_ok=True)
    np.save(output / "candidate.npy", image, allow_pickle=False)
    difference = np.abs(image.astype(np.int16) - expected.astype(np.int16))
    np.save(output / "difference.npy", difference, allow_pickle=False)
    assert np.array_equal(image, expected), (name, int(difference.max()), int(np.any(difference, axis=2).sum()))
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
    assert ["FUNC", "glClearDepth", 1.] in commands
    assert ["FUNC", "glClear", 256] in commands
    assert ["FUNC", "glDepthFunc", "less"] in commands
