"""Fans preserve first, index order and winding; line loops close exactly."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_topology import CASES, assert_expected, assert_trace, render

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/topology-opengl"
EVIDENCE = ROOT / "build/evidence/topology-candidate"


def test_topology_reference_provenance_and_fixed_expected_pixels():
    """Metadata/pixels only; no device or Qt initialization."""
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert manifest["errors"] == {}
    assert set(manifest["fixtures"]) == set(CASES)
    provenance = manifest["provenance"]
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "site-packages" in provenance["vispy_origin"]
    assert "oracle-opengl" in provenance["python_executable"]
    assert provenance["upstream_commit"] == "117b054598f4758b598f4b8f48feea48c11fe7b0"
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    for source, actual in provenance["source_sha256"].items():
        assert actual == pinned["files"][source]
    assert provenance["requirements_sha256"] == hashlib.sha256(
        (ROOT / "tools/oracle_requirements.txt").read_bytes()).hexdigest()
    assert provenance["fixture_source_sha256"] == hashlib.sha256(
        (ROOT / "tools/fixture_gloo.py").read_bytes()).hexdigest()
    for key, source in (("topology_fixture_sha256", "tools/fixture_topology.py"),
                        ("topology_capture_sha256", "tools/oracle_topology_capture.py")):
        assert provenance[key] == hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
    for name, record in manifest["fixtures"].items():
        assert record["readbacks"] == record["parameters"]["final_readbacks"] == 1
        assert not record["parameters"]["intermediate_finish"]
        assert not record["parameters"]["intermediate_present"]
        for key in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            artifact = record[key]
            path = REFERENCE / artifact["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
        assert_expected(name, np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False))
        assert_trace(name, json.loads((REFERENCE / record["filtered_glir"]["file"]).read_text()))


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_triangle_fans_and_line_loop_match_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, parameters, reads = render(name)
    assert reads == record["readbacks"] == 1
    assert parameters == record["parameters"]
    assert commands and shaders
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    assert np.array_equal(image, reference), (name, int(difference.max()))
    assert_expected(name, image)
    assert_trace(name, commands)
    if name == "line_loop_closure":
        from vispy import _dawn

        if _dawn.device_info()["backend"] == "Vulkan":
            assert _dawn.device_info()["bresenham_lines"]
            assert _dawn.probe()["bresenham_line_pipelines"] > 0
    print("topology independent oracle", name, "maxabs", int(difference.max()))
