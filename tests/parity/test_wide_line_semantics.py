"""Independent invocation and homogeneous-clipping line admissions."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_wide_line_semantics import (
    CASES, SIZE, assert_landmarks, center_fraction, contract, render, shaders,
    specification, vertices,
)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/wide-line-semantics-opengl-1"


@pytest.mark.parametrize("name", CASES)
def test_cpu_wide_line_semantics_inputs_are_frozen(name):
    spec = specification(name)
    assert spec["line_width"] == 3. and spec["readbacks"] == 1
    assert not spec["intermediate_finish"] and not contract()["candidate_seen"]
    assert vertices(name).dtype == np.float32 and vertices(name).shape == (2, 4)
    assert spec["line_smooth"] == name.endswith("_smooth")
    vertex, fragment = shaders(name)
    assert spec["qualifier"] + " out vec4" in vertex
    assert spec["qualifier"] + " in vec4" in fragment
    if name.startswith("private_state"):
        assert vertex.count("evaluate_endpoint(a_position)") == 1
        assert "float private_state = 0.;" in vertex
    else:
        np.testing.assert_allclose(vertices(name)[:, 0], [-2., 6.], atol=0, rtol=0)
        np.testing.assert_allclose(vertices(name)[:, 3], [1., 3.], atol=0, rtol=0)


def test_cpu_clip_parameters_and_qualifier_crossings_are_independent():
    a, b = vertices("clipped_noperspective_aliased").astype(np.float64)
    for t, boundary, q in ((.1, -1., .25), (.5, 1., .75)):
        point = (1 - t) * a + t * b
        assert point[0] / point[3] == pytest.approx(boundary)
        assert t * b[3] / point[3] == pytest.approx(q)
    assert center_fraction("clipped_noperspective_aliased", 15) < .5
    assert center_fraction("clipped_noperspective_aliased", 16) > .5
    assert center_fraction("clipped_perspective_aliased", 31) < .5
    assert center_fraction("clipped_perspective_aliased", 32) > .5


def test_cpu_shared_private_state_and_wrong_qualifier_have_rejection_witnesses():
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    image[SIZE[1] - 1 - np.arange(5, 8)[:, None], np.arange(4, 29)[None, :], 1] = 255
    assert_landmarks("private_state_aliased", image)
    wrong = image.copy()
    wrong[..., 2] = wrong[..., 1]
    with pytest.raises(AssertionError):
        assert_landmarks("private_state_aliased", wrong)
    for qualifier in ("noperspective", "perspective"):
        gradient = np.zeros_like(image)
        gradient[..., 3] = 255
        q = np.asarray([center_fraction(f"clipped_{qualifier}_aliased", x) for x in range(SIZE[0])])
        gradient[SIZE[1] - 1 - 12, :, 0] = np.rint((1. - q) * 255).astype(np.uint8)
        gradient[SIZE[1] - 1 - 12, :, 2] = np.rint(q * 255).astype(np.uint8)
        assert_landmarks(f"clipped_{qualifier}_aliased", gradient)
        other = "perspective" if qualifier == "noperspective" else "noperspective"
        with pytest.raises(AssertionError):
            assert_landmarks(f"clipped_{other}_aliased", gradient)


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_native_wide_line_endpoint_and_clip_semantics_matches_reference(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    assert not manifest["errors"] and not manifest["candidate_seen"]
    record = manifest["fixtures"][name]
    assert record["process"]["exit_code"] == 0 and record["parameters"] == specification(name)
    path = REFERENCE / record["rgba"]["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["rgba"]["sha256"]
    image, commands, expanded, spec, observed = render(name)
    assert commands and expanded and spec == record["parameters"]
    assert_landmarks(name, image)
    np.testing.assert_array_equal(image, np.load(path, allow_pickle=False))
