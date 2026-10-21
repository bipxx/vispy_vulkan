"""Compiled and source CPU text helpers preserve upstream atlas texels."""

import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from vispy.visuals.text import _sdf_cpu


ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).parent / "data"
REFERENCE = json.loads((DATA / "sdf_upstream.json").read_text(encoding="utf-8"))


def test_cpu_reference_provenance():
    assert REFERENCE["vispy_version"] == "0.17.0"
    assert REFERENCE["arrays_sha256"] == hashlib.sha256((DATA / "sdf_upstream.npz").read_bytes()).hexdigest()
    assert REFERENCE["capture_script_sha256"] == hashlib.sha256((Path(__file__).parent / "capture_sdf_reference.py").read_bytes()).hexdigest()
    assert REFERENCE["font_sha256"] == hashlib.sha256((ROOT / "src/vispy/util/fonts/data/OpenSans-Regular.ttf").read_bytes()).hexdigest()


@pytest.mark.parametrize("case", REFERENCE["cases"])
@pytest.mark.parametrize("implementation", ["compiled", "source"])
def test_sdf_matches_upstream_in_place(case, implementation):
    helper = _sdf_cpu
    if implementation == "compiled":
        assert any(str(helper.__file__).endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES), "The editable installation must contain compiled _sdf_cpu"
    else:
        spec = importlib.util.spec_from_file_location("vispy_sdf_source", ROOT / "src/vispy/visuals/text/_sdf_cpu.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
    with np.load(DATA / "sdf_upstream.npz") as reference:
        pixels = reference[case + "_input"].copy()
        original = pixels.copy()
        h, w = pixels.shape
        result = helper._calc_distance_field(pixels, w, h, REFERENCE["spread"])
        assert result is None
        assert not np.array_equal(pixels, original)
        np.testing.assert_array_equal(pixels, reference[case + "_expected"])
        np.testing.assert_array_equal(pixels[[0, -1]], original[[0, -1]])
        np.testing.assert_array_equal(pixels[:, [0, -1]], original[:, [0, -1]])


def test_source_fallback_mutates_strided_views():
    spec = importlib.util.spec_from_file_location("vispy_sdf_source", ROOT / "src/vispy/visuals/text/_sdf_cpu.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    with np.load(DATA / "sdf_upstream.npz") as reference:
        pixels = reference["rectangle_input"]
        backing = np.zeros((pixels.shape[0], pixels.shape[1] * 2), np.float32)
        view = backing[:, ::2]
        view[:] = pixels
        helper._calc_distance_field(view, view.shape[1], view.shape[0], REFERENCE["spread"])
        np.testing.assert_array_equal(view, reference["rectangle_expected"])
        assert np.count_nonzero(backing[:, 1::2]) == 0
