"""Actual native Qt capture, raw blend alpha, redraw and QImage ownership."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_qt_framebuffer_alpha import CASES, parameters, render

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/qt-framebuffer-alpha-borderless-opengl"
EVIDENCE = Path(os.environ.get("VISPY_QT_ALPHA_EVIDENCE",
                             ROOT / "build/evidence/qt-framebuffer-alpha-candidate"))


def test_alpha_reference_is_independent_and_preserves_fixed_semantics():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert manifest["kind"] == "upstream" and not manifest["errors"]
    assert set(manifest["fixtures"]) == set(CASES)
    assert manifest["fixture_sha256"] == hashlib.sha256((ROOT / "tools/fixture_qt_framebuffer_alpha.py").read_bytes()).hexdigest()
    assert manifest["capture_sha256"] == hashlib.sha256((ROOT / "tools/oracle_qt_framebuffer_alpha_capture.py").read_bytes()).hexdigest()
    for name, record in manifest["fixtures"].items():
        assert record["parameters"] == parameters(name)
        assert record["provenance"]["kind"] == "upstream"
        assert "site-packages" in record["provenance"]["vispy_origin"]
        assert record["process"]["exit_code"] == 0
        for artifact in record["artifacts"].values():
            assert hashlib.sha256((REFERENCE / artifact["file"]).read_bytes()).hexdigest() == artifact["sha256"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_native_qt_alpha_redraw_and_owned_images_match_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    record = manifest["fixtures"][name]
    arrays, params, observed = render(name)
    from vispy import _dawn
    device = _dawn.device_info()
    assert device["ok"] and device["backend"] == "Vulkan" and not device["software"]
    observed["device_info"] = device
    assert params == record["parameters"]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / f"{name}.observations.json").write_text(json.dumps(observed, indent=2) + "\n")
    for key, candidate in arrays.items():
        reference = np.load(REFERENCE / record["artifacts"][key]["file"], allow_pickle=False)
        np.save(EVIDENCE / f"{name}.{key}.npy", candidate, allow_pickle=False)
        difference = np.abs(candidate.astype(np.int16) - reference.astype(np.int16))
        np.save(EVIDENCE / f"{name}.{key}.difference.npy", difference, allow_pickle=False)
        assert np.array_equal(candidate, reference), (name, key, int(difference.max()), int(np.any(difference, axis=2).sum()))
    assert observed["qimage_has_alpha"] == record["observations"]["qimage_has_alpha"]
    assert observed["dpr"] == record["observations"]["dpr"]
