"""Public captures preserve float values, normalized formats and array lifetime."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_capture import CASES, assert_expected, expected_image, render, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/typed-capture-opengl"
EVIDENCE = ROOT / "build/evidence/typed-capture-candidate"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_typed_capture_analytic_contract_preserves_units_channels_crop_and_orientation():
    rgba = expected_image("rgba32f_float")
    assert rgba.dtype == np.float32 and rgba.shape == (6, 8, 4)
    assert rgba[0, 0].tolist() == [.125, -2, 15, .75]
    assert rgba[-1, 0].tolist() == [-2, 15, .125, .25]
    red = expected_image("r32f_float")
    assert red[0, 0].tolist() == [.125, 0, 0, 1]
    rg = expected_image("rg32f_float")
    assert rg[-1, 0].tolist() == [-2, 15, 0, 1]
    crop = expected_image("float_crop_rgb")
    assert crop.shape == (3, 4, 3)
    assert np.array_equal(crop[..., 1:], rgba[2:5, 2:6, 1:3])
    assert crop[0, :, 0].tolist() == [2.5, 3.5, 4.5, 5.5]
    shifted = crop.copy()
    shifted[..., 0] -= 1
    with pytest.raises(AssertionError, match="exact analytic typed capture"):
        assert_expected("float_crop_rgb", shifted, {})
    assert expected_image("rgba8_u8")[-1, 0].tolist() == [0, 64, 32, 64]
    assert expected_image("rgba16_float")[-1, 0, 1] == np.float32(16384 / 65535)
    with pytest.raises(AssertionError, match="exact analytic typed capture"):
        assert_expected("rgba32f_float", rgba / 255, {})


def test_typed_capture_reference_is_independent_and_retains_artifact_hashes():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    provenance = manifest["provenance"]
    assert manifest["errors"] == {}, "the required typed OpenGL corpus must be fully admitted"
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "site-packages" in provenance["vispy_origin"] and "oracle-opengl" in provenance["python_executable"]
    assert provenance["typed_fixture_sha256"] == sha256(ROOT / "tools/fixture_capture.py")
    assert provenance["typed_capture_sha256"] == sha256(ROOT / "tools/oracle_typed_capture.py")
    assert provenance["requirements_sha256"] == sha256(ROOT / "tools/oracle_requirements.txt")
    assert manifest["comparison"] == {"values_exact": True, "dtype_exact": True, "analytic_expected_exact": True}
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    for path, digest in provenance["source_sha256"].items():
        assert digest == pinned["files"][path]
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        keys = ["rgba", "filtered_glir", "expanded_shaders", "capture"]
        if name == "float_owned_arrays":
            keys.append("first")
        for artifact in [*(record[key] for key in keys), record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]
        params = dict(specification(name))
        params["readback_between_ownership_stages"] = params["readbacks"] == 2
        params["explicit_gloo_finish_calls"] = 0
        assert record["parameters"] == params
        image = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
        extras = {"first": np.load(REFERENCE / record["first"]["file"], allow_pickle=False)} if "first" in record else {}
        assert_expected(name, image, extras)
    for error in manifest["errors"].values():
        assert error["process"]["exit_code"] != 0
        for artifact in [*error.get("unadmitted_artifacts", {}).values(), error["process"]["stdout"], error["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_public_typed_capture_matches_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "upstream admission unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params, extras, layout = render(name)
    assert commands and shaders and params == record["parameters"]
    assert image.dtype == reference.dtype and image.shape == reference.shape
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    difference = np.abs(image.astype(np.float64) - reference.astype(np.float64))
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    if "first" in extras:
        np.save(EVIDENCE / f"{name}.first.candidate.npy", extras["first"], allow_pickle=False)
    assert_expected(name, image, extras)
    assert np.array_equal(image, reference), (name, "typed capture exact mismatch", float(difference.max()))
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == params["readbacks"]
    print("typed capture independent oracle", name, image.dtype, "maxabs", float(difference.max()), "layout", layout)
