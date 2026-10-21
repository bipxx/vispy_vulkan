"""Historical Glue references; active all-five graphics uses test_glue_wheel_parity."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_glue import CASES, assert_landmarks

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/glue-opengl"


def test_glue_reference_admission_records_independent_sources_and_unresolved_cases():
    """Metadata only: loading this test must not initialize a GPU or Qt app."""
    admission = json.loads((ROOT / "tools/oracle_glue_admission.json").read_text())
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    provenance = manifest["provenance"]
    assert admission["version"] == provenance["glue_vispy_viewers_version"] == "1.4.0"
    assert admission["commit"] == provenance["host_commit"] == "33509adb53909b7542069563f77fb9a80bd565a4"
    assert provenance["kind"] == "upstream" and provenance["vispy_version"] == "0.17.0"
    assert "oracle-glue" in provenance["python_executable"]
    assert "site-packages" in provenance["glue_vispy_viewers_origin"]
    assert provenance["host_requirements_sha256"] == hashlib.sha256(
        (ROOT / "tools/oracle_glue_requirements.txt").read_bytes()).hexdigest()
    assert provenance["host_fixture_sha256"] == hashlib.sha256(
        (ROOT / "tools/fixture_glue.py").read_bytes()).hexdigest()
    assert provenance["host_capture_sha256"] == hashlib.sha256(
        (ROOT / "tools/oracle_glue_capture.py").read_bytes()).hexdigest()
    assert provenance["historical_windows_test_skip"]["reason"] == "Windows fatal exception: access violation"
    assert set(manifest["fixtures"]) | set(manifest["errors"]) == set(CASES)
    assert set(admission["successful_fixtures"]) == set(manifest["fixtures"])
    assert admission["unresolved_fixtures"] == manifest["errors"]
    assert admission["upstream_qualification"] == ("unresolved" if manifest["errors"] else "passed")
    for name, expected in admission["source_files"].items():
        assert provenance["host_source_sha256"][name] == expected["sha256"]
        assert admission["commit"] in expected["url"]
    for name, fixture in manifest["fixtures"].items():
        for key in ("rgba", "filtered_glir", "expanded_shaders", "capture"):
            artifact = fixture[key]
            file = REFERENCE / artifact["file"]
            assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest() == artifact["sha256"]
        assert fixture["parameters"]["host_context_available"]
        assert fixture["parameters"]["error_dialogs"] == []
        assert_landmarks(name, np.load(REFERENCE / fixture["rgba"]["file"], allow_pickle=False))
    for name, error in manifest["errors"].items():
        artifacts = error["unadmitted_artifacts"]
        assert set(artifacts) == {"npy", "glir.json", "shaders.json"}
        for artifact in artifacts.values():
            file = REFERENCE / artifact["file"]
            assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest() == artifact["sha256"]
        # The failing upstream frame is retained as evidence, never accepted
        # as the desired edited image or used to relax the candidate test.
        with pytest.raises(AssertionError):
            assert_landmarks(name, np.load(REFERENCE / artifacts["npy"]["file"], allow_pickle=False))
