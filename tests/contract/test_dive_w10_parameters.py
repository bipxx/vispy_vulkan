"""A visually equal screenshot must not admit changed public fixture inputs."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("dive_w10_comparison", ROOT / "tools/compare_dive_w10.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def test_only_expected_native_widget_change_is_allowed():
    upstream = {"native_mro": ["QOpenGLWidget", "QWidget"], "canvas_size": [618, 392], "inputs": [{"sha256": "fixed"}]}
    candidate = {**upstream, "native_mro": ["QWidget"]}
    assert comparison.parameters_match(upstream, candidate)
    assert not comparison.parameters_match(upstream, {**candidate, "canvas_size": [619, 392]})
    assert not comparison.parameters_match(upstream, {**candidate, "inputs": [{"sha256": "changed"}]})
    assert not comparison.parameters_match(upstream, {"native_mro": ["QWidget"], "canvas_size": [618, 392]})


def test_native_widget_contract_cannot_be_omitted_or_use_upstream_gl():
    upstream = {"native_mro": ["QOpenGLWidget", "QWidget"], "state": "fixed"}
    assert not comparison.parameters_match(upstream, upstream)
    assert not comparison.parameters_match(upstream, {"state": "fixed"})
    assert not comparison.parameters_match(upstream, {"native_mro": ["QObject"], "state": "fixed"})
