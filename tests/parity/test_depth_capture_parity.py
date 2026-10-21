"""Depth24/stencil8 capture semantics; unresolved pinned wrappers cannot pass."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_depth_capture import CASES, assert_expected, expected_image, render, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/depth-capture-opengl"
EVIDENCE = ROOT / "build/evidence/depth-capture-candidate"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_depth_stencil_analytic_contract_has_asymmetric_exact_values_and_no_color_channels():
    depth = expected_image("depth_float")
    assert depth.shape == (6, 8, 1) and depth.dtype == np.float32
    assert depth[3, 1, 0] == np.float32(4194304 / 16777215)
    assert depth[1, 4, 0] == np.float32(12582911 / 16777215)
    assert np.unique(expected_image("depth_u8")).tolist() == [64, 191, 255]
    assert np.array_equal(expected_image("depth_noalpha_float"), depth)
    assert np.array_equal(expected_image("depth_crop_float"), depth[2:5, 2:6])
    stencil = expected_image("stencil_float")
    assert np.unique(stencil).tolist() == [3, 37, 203]
    assert np.array_equal(stencil, expected_image("stencil_gl_float"))
    assert np.array_equal(expected_image("stencil_crop_float"), stencil[2:5, 2:6])
    with pytest.raises(AssertionError, match="exact depth/stencil values"):
        assert_expected("stencil_float", stencil / 255)
    with pytest.raises(AssertionError, match="exact depth/stencil values"):
        assert_expected("depth_float", depth[::-1])


def test_depth_stencil_reference_metadata_preserves_upstream_sources_and_failed_apis():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert "site-packages" in origins["vispy_origin"] and "oracle-opengl" in origins["python_executable"]
    assert origins["depth_fixture_sha256"] == sha256(ROOT / "tools/fixture_depth_capture.py")
    assert origins["depth_capture_sha256"] == sha256(ROOT / "tools/oracle_depth_capture.py")
    assert origins["requirements_sha256"] == sha256(ROOT / "tools/oracle_requirements.txt")
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    assert manifest["comparison"] == {"values_exact": True, "dtype_exact": True, "analytic_expected_exact": True}
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    for path, digest in origins["source_sha256"].items():
        assert digest == pinned["files"][path]
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        assert record["parameters"] == specification(name)
        for artifact in [*(record[key] for key in ("rgba", "filtered_glir", "expanded_shaders", "capture")),
                         record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]
        assert_expected(name, np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))
    for error in manifest["errors"].values():
        assert error["process"]["exit_code"] != 0
        for artifact in [*error["unadmitted_artifacts"].values(), error["process"]["stdout"], error["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_public_depth_stencil_capture_matches_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "pinned upstream admission unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders and params == record["parameters"]
    assert image.shape == reference.shape and image.dtype == reference.dtype
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    difference = np.abs(image.astype(np.float64) - reference.astype(np.float64))
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert_expected(name, image)
    assert np.array_equal(image, reference), (name, "exact packed depth/stencil capture", float(difference.max()))
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
    print("depth/stencil independent oracle", name, image.dtype, "maxabs", float(difference.max()))
