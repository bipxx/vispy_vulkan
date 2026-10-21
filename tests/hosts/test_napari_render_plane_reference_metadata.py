"""Preserve genuine public widget dependency failures as unadmitted attempts."""

import hashlib
import json
from pathlib import Path

from tools.fixture_napari_render_plane import CASES

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_numpy_2_5_plane_constructor_failures_are_preserved_not_admitted():
    base = ROOT / "tests/reference/napari-render-plane-opengl"
    manifest = json.loads((base / "manifest.json").read_text())
    assert manifest["fixtures"] == {} and set(manifest["errors"]) == set(CASES)
    origins = manifest["provenance"]
    assert origins["kind"] == "upstream" and origins["vispy_version"] == "0.17.0"
    plugin = origins["plugin"]
    assert plugin["installed"]["numpy"] == "2.5.3"
    assert plugin["registered_render_plane_widget"]["class"] == "QtRenderPlaneManipulatorWidget"
    assert plugin["plugin_wheel_sha256"] == "de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e"
    assert plugin["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_napari_render_plane.py")
    assert plugin["capture_source_sha256"] == sha256(ROOT / "tools/oracle_napari_render_plane_capture.py")
    for error in manifest["errors"].values():
        assert error["type"] == "AttributeError" and "row_stack" in error["error"]
        assert error["process"]["exit_code"] == 1
        for artifact in [error["capture"], error["process"]["stdout"], error["process"]["stderr"]]:
            assert sha256(base / artifact["file"]) == artifact["sha256"]
        stderr = (base / error["process"]["stderr"]["file"]).read_text()
        assert "add_plugin_dock_widget" in stderr and "vispy_visual_data.py" in stderr
        assert "np.row_stack" in stderr


def test_unscheduled_numpy_2_4_attempt_retains_timer_delivery_failures_and_two_admissions():
    base = ROOT / "tests/reference/napari-render-plane-numpy246-opengl"
    manifest = json.loads((base / "manifest.json").read_text())
    assert set(manifest["fixtures"]) == {"plane_handles", "plane_clipped"}
    assert set(manifest["errors"]) == {"plane_translation", "plane_rotation"}
    plugin = manifest["provenance"]["plugin"]
    assert plugin["installed"]["numpy"] == "2.4.6"
    assert plugin["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_napari_render_plane.py")
    assert plugin["capture_source_sha256"] == sha256(ROOT / "tools/oracle_napari_render_plane_capture.py")
    for name, entry in manifest["fixtures"].items():
        assert entry["process"]["exit_code"] == 0
        for artifact in [*entry["artifacts"].values(), entry["capture"], entry["process"]["stdout"], entry["process"]["stderr"]]:
            assert sha256(base / artifact["file"]) == artifact["sha256"]
    for error in manifest["errors"].values():
        assert error["process"]["exit_code"] == 1 and error["type"] == "AssertionError"
        assert "ACTUAL" in error["error"] and "DESIRED" in error["error"]
        for artifact in [error["capture"], error["process"]["stdout"], error["process"]["stderr"]]:
            assert sha256(base / artifact["file"]) == artifact["sha256"]


def test_public_timer_variant_preserves_criteria_and_real_admitted_plane_workflows():
    import ast
    import numpy as np
    from tools.fixture_napari_render_plane_scheduled import assert_landmarks

    class RemoveWaits(ast.NodeTransformer):
        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "QtTest.QTest.qWait":
                assert len(node.value.args) == 1 and node.value.args[0].value == 10
                return None
            return self.generic_visit(node)

    original = ast.parse((ROOT / "tools/fixture_napari_render_plane.py").read_text())
    scheduled = RemoveWaits().visit(ast.parse((ROOT / "tools/fixture_napari_render_plane_scheduled.py").read_text()))
    assert ast.dump(original, include_attributes=False) == ast.dump(scheduled, include_attributes=False)
    base = ROOT / "tests/reference/napari-render-plane-scheduled-opengl"
    manifest = json.loads((base / "manifest.json").read_text())
    assert set(manifest["fixtures"]) == set(CASES) and not manifest["errors"]
    plugin = manifest["provenance"]["plugin"]
    assert plugin["installed"]["numpy"] == "2.4.6"
    assert "real QTest.qWait(10)" in plugin["public_event_delivery"]
    assert plugin["fixture_source_sha256"] == sha256(ROOT / "tools/fixture_napari_render_plane_scheduled.py")
    assert plugin["capture_source_sha256"] == sha256(ROOT / "tools/oracle_napari_render_plane_scheduled_capture.py")
    for filename, digest in plugin["evidence_sha256"].items():
        assert sha256(ROOT / "compat/host-environments" / filename) == digest
    for name, record in manifest["fixtures"].items():
        assert record["process"]["exit_code"] == 0
        for artifact in [*record["artifacts"].values(), record["capture"], record["process"]["stdout"], record["process"]["stderr"]]:
            assert sha256(base / artifact["file"]) == artifact["sha256"]
        params = record["parameters"]
        assert "not proof of all signal disconnections" in params["cleanup_scope"]
        image = np.load(base / record["artifacts"]["rgba"]["file"], allow_pickle=False)
        extras = {key: np.load(base / artifact["file"], allow_pickle=False)
                  for key, artifact in record["artifacts"].items()
                  if key not in ("rgba", "filtered_glir", "expanded_shaders", "parameters")}
        assert_landmarks(name, image, params, extras)
    for name in ("plane_handles", "plane_clipped"):
        earlier = json.loads((ROOT / "tests/reference/napari-render-plane-numpy246-opengl/manifest.json").read_text())
        assert manifest["fixtures"][name]["artifacts"]["rgba"]["sha256"] == earlier["fixtures"][name]["artifacts"]["rgba"]["sha256"]
