"""Candidate stencil feature against actual GL, not a broken-wrapper admission."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_stencil_capture import CASES, assert_expected, expected_image, render, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/stencil-capture-opengl"
EVIDENCE = ROOT / "build/evidence/stencil-capture-candidate"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stencil_gl_reference_labels_external_read_and_retains_broken_wrapper_evidence():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    assert origins["oracle_scope"] == "GL stencil semantics; not upstream VisPy wrapper admission"
    assert origins["stencil_fixture_sha256"] == sha256(ROOT / "tools/fixture_stencil_capture.py")
    assert origins["stencil_capture_sha256"] == sha256(ROOT / "tools/oracle_stencil_capture.py")
    assert origins["analytic_setup_source_sha256"] == sha256(ROOT / "tools/fixture_depth_capture.py")
    assert origins["requirements_sha256"] == sha256(ROOT / "tools/oracle_requirements.txt")
    external = origins["external_readback"]
    assert external["api"] == "OpenGL.GL.glReadPixels(GL_STENCIL_INDEX)"
    assert external["version"] == "3.1.10" and "site-packages" in external["origin"]
    assert set(external["source_sha256"]) == {"GL/images.py", "raw/GL/VERSION/GL_1_0.py"}
    failures = ROOT / external["wrapper_failure_manifest"]
    assert external["wrapper_failure_manifest_sha256"] == sha256(failures)
    broken = json.loads(failures.read_text())
    for name in CASES:
        assert name not in broken["fixtures"]
        assert broken["errors"][name]["type"] == "KeyError"
        assert broken["errors"][name]["error"] == "GL_STENCIL_INDEX8"
    assert manifest["errors"] == {} and set(manifest["fixtures"]) == set(CASES)
    for name, record in manifest["fixtures"].items():
        assert record["parameters"] == specification(name, "pyqt6")
        assert record["process"]["exit_code"] == 0
        for artifact in [*(record[key] for key in ("rgba", "filtered_glir", "expanded_shaders", "capture")),
                         record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]
        assert_expected(name, np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))


def test_stencil_float_values_are_integer_units_and_crop_is_asymmetric():
    image = expected_image("stencil_float")
    assert image.shape == (6, 8, 1) and image.dtype == np.float32
    assert np.unique(image).tolist() == [3, 37, 203]
    assert np.array_equal(expected_image("stencil_crop_float"), image[2:5, 2:6])
    with pytest.raises(AssertionError, match="exact depth/stencil values"):
        assert_expected("stencil_float", image / 255)


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_candidate_public_stencil_capture_preserves_real_gl_semantics(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], "real GL stencil reference required"
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders and params == specification(name)
    actual, expected = dict(params), dict(record["parameters"])
    assert actual.pop("capture_api") == "gloo.read_pixels(mode='stencil')"
    assert expected.pop("capture_api") == "PyOpenGL.GL.glReadPixels(GL_STENCIL_INDEX)"
    assert actual.pop("explicit_gloo_finish_calls") == 0
    assert expected.pop("explicit_gloo_finish_calls") == 1
    assert actual == expected
    assert image.dtype == reference.dtype and image.shape == reference.shape
    difference = np.abs(image.astype(np.float64) - reference.astype(np.float64))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert_expected(name, image)
    assert np.array_equal(image, reference), (name, "exact GL stencil semantics", float(difference.max()))
    assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
    print("stencil GL-spec independent oracle", name, "maxabs", float(difference.max()))
