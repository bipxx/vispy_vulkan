"""Actual point source identity, instance/divisor and pending-update gates."""

import hashlib
import json
import os
from pathlib import Path
import numpy as np
import pytest

from tools.fixture_point_identity import (CASES, LARGE_ID, assert_expected,
                                         assert_trace, expected_image, parameters,
                                         point_operations, render, specification)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/point-identity-opengl"
EVIDENCE = Path(os.environ.get("VISPY_POINT_IDENTITY_EVIDENCE", ROOT / "build/evidence/point-identity-candidate"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_point_inputs_reject_rank_identity_and_preserve_divisor_ranges():
    for dtype in ("uint8", "uint16", "uint32"):
        spec = specification("indexed_" + dtype)
        assert spec["indices"].dtype == np.dtype(dtype)
        assert spec["indices"].tolist() == [6, 1, 4, 1]
        # Green source-ID1 is drawn twice; IDs4/6 each shade once.
        image = expected_image("indexed_" + dtype)
        assert image[23 - 8, 8].tolist() == [0, 112, 0, 255]
        assert image[23 - 4, 16].tolist() == [64, 0, 0, 255]
        assert image[23 - 4, 24].tolist() == [0, 0, 64, 255]
    assert LARGE_ID > 2 ** 24 and int(np.float32(LARGE_ID)) != LARGE_ID
    large = specification("large_uint32_constant_geometry")
    assert large["data"] is None and large["inactive_count_input_required"]
    assert large["indices"].tolist() == [LARGE_ID]
    for divisor in (1, 2):
        spec = specification("instanced_divisor" + str(divisor))
        assert len(spec["offsets"]) * divisor == 4
        assert len(point_operations(spec["case"])) == 8
        assert spec["data"].dtype.fields["a_base"][1] == 4
        assert spec["data"].dtype.fields["a_tint"][1] == 16
        assert spec["data"].dtype.itemsize == 28
    first = specification("nonzero_first_queue")
    assert first["first"] == 3 and first["count"] == 3
    assert "not public Program.draw" in first["api_scope"]
    for name in CASES:
        assert parameters(name)["case"] == name
        image = expected_image(name)
        assert_expected(name, image)
        image[0, 0] = [255, 255, 255, 255]
        with pytest.raises(AssertionError, match="fixed analytic point pixels"):
            assert_expected(name, image)


def test_point_reference_origins_criteria_driver_state_and_hashes():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "site-packages" in provenance["vispy_origin"] and "oracle-opengl" in provenance["python_executable"]
    assert provenance["point_fixture_sha256"] == sha256(ROOT / "tools/fixture_point_identity.py")
    assert provenance["point_capture_sha256"] == sha256(ROOT / "tools/oracle_point_identity_capture.py")
    assert manifest["comparison"] == {"full_frame_exact": True, "analytic_pixels_exact": True}
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    for path, digest in provenance["source_sha256"].items():
        assert digest == pinned["files"][path]
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        assert record["parameters"] == parameters(name)
        observed = record["observations"]
        assert observed["sample_source"] == "OpenGL driver"
        assert observed["physical_samples"] == max(1, observed["samples_raw"]) == 1
        assert observed["gl_version"].startswith("4.6")
        assert not observed["point_smooth"] and observed["program_point_size_after_draw"]
        if name == "large_uint32_constant_geometry":
            assert observed["count_attribute_location"] == -1
        for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(REFERENCE / artifact["file"]) == artifact["sha256"]
        assert_expected(name, np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False))
        assert_trace(name, json.loads((REFERENCE / record["artifacts"]["filtered_glir"]["file"]).read_text()))


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_point_identity_and_instances_match_fixed_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert name in manifest["fixtures"], (name, "upstream admission unresolved", manifest["errors"].get(name))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params, observations = render(name)
    assert commands and shaders and params == record["parameters"]
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.observations.json").write_text(json.dumps(observations, indent=2, sort_keys=True) + "\n")
    assert observations["sample_source"] == "Dawn facade configuration"
    assert observations["device_info"]["ok"]
    assert_expected(name, image)
    assert_trace(name, commands)
    assert np.array_equal(image, reference), (name, int(difference.max()), int(np.any(difference, axis=2).sum()))
    print("point identity exact independent oracle", name, "maxabs", int(difference.max()))
