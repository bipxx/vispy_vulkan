"""One-pixel GL driver line coverage, endpoint ownership and interpolation."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_lines import CASES, OCTANTS, SIZE, assert_landmarks, geometry, landmarks, render

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/lines-opengl"
EVIDENCE = ROOT / "build/evidence/lines-candidate"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_line_geometry_and_half_open_landmarks_are_fixed_before_capture():
    forward, primitive = geometry("octants_forward")
    reverse, _ = geometry("octants_reverse")
    assert primitive == "lines" and forward.shape == (16, 2)
    assert np.array_equal(reverse.reshape(8, 2, 2), forward.reshape(8, 2, 2)[:, ::-1])
    assert np.array_equal(forward.reshape(8, 2, 2)[:, 1] - forward.reshape(8, 2, 2)[:, 0], OCTANTS)
    assert (list([24, 6]), [0, 0, 0, 255]) in landmarks("half_open_endpoints")
    assert ([16, 6], [0, 64, 0, 255]) in landmarks("join_orthogonal_alpha")
    assert ([16, 7], [0, 112, 0, 255]) in landmarks("two_vertex_loop_alpha")
    black = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    black[..., 3] = 255
    assert_landmarks("degenerate_equal", black)
    black[10, 10] = [0, 255, 0, 255]
    with pytest.raises(AssertionError, match="zero-length half-open"):
        assert_landmarks("degenerate_equal", black)


def test_line_reference_has_real_upstream_provenance_and_fixed_full_frame_policy():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert "site-packages" in origins["vispy_origin"] and "oracle-opengl" in origins["python_executable"]
    assert origins["line_fixture_sha256"] == sha256(ROOT / "tools/fixture_lines.py")
    assert origins["line_capture_sha256"] == sha256(ROOT / "tools/oracle_lines_capture.py")
    assert origins["requirements_sha256"] == sha256(ROOT / "tools/oracle_requirements.txt")
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    assert manifest["comparison"] == {"full_frame_exact": True, "fixed_landmarks_exact": True}
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    for path, digest in origins["source_sha256"].items():
        assert digest == pinned["files"][path]
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        params = record["parameters"]
        points, primitive = geometry(name)
        assert params["points"] == points.tolist() and params["primitive"] == primitive
        assert params["points_sha256"] == hashlib.sha256(points.tobytes()).hexdigest()
        assert params["line_width"] == params["readbacks"] == params["physical_samples"] == 1
        assert params["intermediate_finish"] is False
        for artifact in [*(record[key] for key in ("rgba", "filtered_glir", "expanded_shaders", "capture")),
                         record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]
        assert_landmarks(name, np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))
    for error in manifest["errors"].values():
        assert error["process"]["exit_code"] != 0
        for artifact in [*error["unadmitted_artifacts"].values(), error["process"]["stdout"], error["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_native_line_rasterization_matches_actual_pinned_gl_driver(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "upstream admission unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders and params == record["parameters"]
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert_landmarks(name, image)
    assert np.array_equal(image, reference), (name, "exact-driver line mismatch", int(difference.max()),
                                              int(np.any(difference != 0, axis=2).sum()))
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
    if name == "flat_provoking_color":
        from vispy import _dawn

        if _dawn.device_info()["backend"] == "Vulkan":
            assert _dawn.device_info()["last_vertex_provoking"]
            assert _dawn.probe()["last_vertex_pipelines"] > 0
    print("line independent exact-driver oracle", name, "maxabs", int(difference.max()))
