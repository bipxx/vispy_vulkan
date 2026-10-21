"""Independent near/far line clipping, depth, index and vertex-ID gates."""

import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

from tools.fixture_line_extensions import CASES, GREEN, SIZE, assert_landmarks, landmarks, specification, render

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/line-extensions-opengl"
EVIDENCE = ROOT / "build/evidence/line-extensions-candidate"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_line_extension_inputs_and_landmarks_are_independent():
    near = specification("near_clip")["vertices"]
    far = specification("far_clip")["vertices"]
    assert near[:, 2].tolist() == [-2, 0] and far[:, 2].tolist() == [0, 2]
    perspective = specification("near_far_perspective_clip")["vertices"]
    assert perspective[:, 3].tolist() == [1, 2]
    # Solve homogeneous clip intersections from the input, before any pixels.
    lower = -(perspective[0, 2] + perspective[0, 3]) / np.diff(perspective[:, 2] + perspective[:, 3])[0]
    upper = -(perspective[0, 3] - perspective[0, 2]) / np.diff(perspective[:, 3] - perspective[:, 2])[0]
    assert np.isclose(lower, 1 / 7) and np.isclose(upper, 3 / 5)
    for dtype in ("uint8", "uint16", "uint32"):
        spec = specification("indexed_" + dtype)
        assert spec["indices"].dtype == np.dtype(dtype)
        assert spec["indices"].tolist() == [2, 0, 3, 1]
    assert specification("nonzero_first_vertex_id")["first"] == 2
    for name in CASES:
        image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
        image[..., 3] = 255
        for (x, y), color in landmarks(name):
            image[SIZE[1] - 1 - y, x] = color
        assert_landmarks(name, image)
        colored = next((xy for xy, color in landmarks(name) if color != [0, 0, 0, 255]))
        x, y = colored
        image[SIZE[1] - 1 - y, x] = [255, 255, 255, 255]
        with pytest.raises(AssertionError, match="independent clipping/depth/ID landmark"):
            assert_landmarks(name, image)


def test_line_extension_reference_has_real_sample_queries_and_hashes():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "site-packages" in provenance["vispy_origin"] and "oracle-opengl" in provenance["python_executable"]
    assert provenance["extension_fixture_sha256"] == sha256(ROOT / "tools/fixture_line_extensions.py")
    assert provenance["extension_capture_sha256"] == sha256(ROOT / "tools/oracle_line_extensions_capture.py")
    assert provenance["original_lines_manifest_sha256"] == sha256(ROOT / "tests/reference/lines-opengl/manifest.json")
    assert manifest["comparison"] == {"full_frame_exact": True, "fixed_landmarks_exact": True}
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    for path, digest in provenance["source_sha256"].items():
        assert digest == pinned["files"][path]
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        assert record["observations"]["sample_source"] == "OpenGL driver query"
        assert record["observations"]["sample_api"] == "gloo.gl.glGetParameter(GL_SAMPLES)"
        assert max(1, record["observations"]["samples_raw"]) == record["observations"]["physical_samples"] == 1
        for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]
        assert_landmarks(name, np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False))


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_native_extended_lines_match_pinned_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "upstream admission unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params, observations = render(name)
    assert commands and shaders and params == record["parameters"]
    # Candidate GL_SAMPLES is explicitly a compatibility configuration query;
    # only the independently installed OpenGL reference claims a driver query.
    assert observations["sample_source"] == "Dawn GL facade configuration query"
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert_landmarks(name, image)
    assert np.array_equal(image, reference), (name, int(difference.max()), int(np.any(difference, axis=2).sum()))
    print("line extension independent oracle", name, "maxabs", int(difference.max()))
