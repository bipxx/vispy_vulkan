# SPDX-License-Identifier: AGPL-3.0-only
"""Current-wheel (`0.17.0+vulkan.2`) downstream scientific host renewal contracts (`HOST-01..06`).

CPU contract tests run unconditionally with zero scratch allocation and enforce:
- strict claim separation between stock hot-swap (`HOST-01`, `PASS_HOT_SWAP_GATES`)
  and patched strict no-OpenGL (`HOST-02`/`HOST-03`, `PASS_ALL_NO_OPENGL_GATES`);
- frozen `compat/no-opengl-matrix.json` and `compat/no-opengl-napari-0.10.0.json`
  optional-row preservation (`r1 == "open"`);
- `DIVE` (`HOST-04`) PySide2-legacy exclusion and Qt6 `QAction` blocker evidence;
- `Glue` (`HOST-06` / `SCI-05` `H03`) FRB `invalidate_cache`-before-update
  reconciliation alongside the preserved historical failure record;
- `phylib` and `Visbrain` (`HOST-06`) import-only vs rendered-smoke non-conflation;
- schema and hash/exit/gauge invariants on
  `compat/api-acceptance/host01-06-current-wheels-v1.json`.

GPU/wheel tests (`@pytest.mark.gpu`, `@pytest.mark.wheel`) execute isolated
child probes against an installed `0.17.0+vulkan.2` wheel when configured via
`VISPY_RENEWAL_WHEEL`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[2]
DISPOSITIONS_DOC = ROOT / "docs/host-workflow-dispositions.md"
ACCEPTANCE_RECEIPT = ROOT / "compat/api-acceptance/host01-06-current-wheels-v1.json"
H03_DISPOSITION = ROOT / "compat/api-acceptance/h03-upstream-disposition-v1.json"
NO_OPENGL_MATRIX = ROOT / "compat/no-opengl-matrix.json"
NAPARI_010_RECORD = ROOT / "compat/no-opengl-napari-0.10.0.json"
HOST_CHANGES = ROOT / "compat/host-changes.json"
HOSTS_LOCK = ROOT / "compat/hosts.lock.toml"

WINDOWS_CURRENT_WHEEL_SHA256 = "9919a280a5de2c4bec45837078cb1d405e7169933ddcfb0758aa7d6a82722d39"
LINUX_CURRENT_WHEEL_SHA256 = "e600b29e5259b896cc9d0fe36bbb5760260946aef53c013f8fc74e2fd0153007"
MESA_PATCHED_SHA256 = "9c5c41b3a7b9d759b0960c868f10375281798ad084150716d6d122c8789b9e12"
PHYLIB_PACKAGE_TREE_SHA256 = "3db4814e19aa3a6f9e477a7ae7a5472d1d86237b566088ecf521cbfb2e3c2a98"

LIVE_GAUGES = (
    "pending_tickets",
    "queued_frames",
    "live_buffer_bytes",
    "live_cpu_buffer_bytes",
    "live_texture_bytes",
    "canvas_texture_bytes",
    "transient_buffer_bytes",
    "line_resource_pool_busy_slots",
    "line_resource_pool_bytes",
    "host_import_pinned_bytes",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_host_renewal_receipt(payload: dict) -> None:
    """Validate `host01-06-current-wheels-v1.json` invariants (fail-closed)."""
    if payload.get("schema") != 1:
        raise ValueError("schema must equal 1")
    if payload.get("acceptance_id") != "host01-06-current-wheels-v1":
        raise ValueError("unexpected acceptance_id")
    if payload.get("runtime_version") != "0.17.0+vulkan.2":
        raise ValueError("runtime_version must be 0.17.0+vulkan.2")

    separation = payload.get("claim_separation") or {}
    if separation.get("stock_hot_swap_verdict") != "PASS_HOT_SWAP_GATES":
        raise ValueError("stock hot-swap verdict must be PASS_HOT_SWAP_GATES")
    if separation.get("patched_strict_no_opengl_verdict") != "PASS_ALL_NO_OPENGL_GATES":
        raise ValueError("patched strict verdict must be PASS_ALL_NO_OPENGL_GATES")
    if separation.get("stock_hot_swap_qualifies_strict_no_opengl") is not False:
        raise ValueError("stock hot-swap must never claim strict no-OpenGL qualification")
    if separation.get("artifact_admitted_to_no_opengl_matrix") is not False:
        raise ValueError("detached host renewal must not claim silent matrix promotion")
    if separation.get("no_opengl_matrix_modified") is not False:
        raise ValueError("compat/no-opengl-matrix.json must remain unmodified by W2-6")

    platforms = payload.get("platforms") or {}
    expected_platforms = {
        "windows": ("gap-w2-6-windows-978", WINDOWS_CURRENT_WHEEL_SHA256),
        "wsl": ("gap-w2-6-wsl-979", LINUX_CURRENT_WHEEL_SHA256),
    }
    if set(platforms) != set(expected_platforms):
        raise ValueError(f"platforms must be {sorted(expected_platforms)}")

    for platform_key, (expected_run_id, expected_wheel_sha) in expected_platforms.items():
        entry = platforms[platform_key]
        if entry.get("run_id") != expected_run_id:
            raise ValueError(f"{platform_key} run_id mismatch")
        if entry.get("wheel_sha256") != expected_wheel_sha:
            raise ValueError(f"{platform_key} wheel_sha256 mismatch")
        if entry.get("wheel_members_verified") != 537:
            raise ValueError(f"{platform_key} wheel_members_verified must be 537")
        if entry.get("scratch_cleaned") is not True or entry.get("scratch_absent_verified") is not True:
            raise ValueError(f"{platform_key} scratch cleanup verification missing")
        if platform_key == "wsl":
            if entry.get("mesa_lvp_sha256") != MESA_PATCHED_SHA256:
                raise ValueError("wsl must bind pinned patched Mesa 9c5c41b3...")
            if entry.get("xvfb_owned_and_waited") is not True or entry.get("wsl_exe_waited") is not True:
                raise ValueError("wsl must directly await owned Xvfb and wsl.exe exits")

        strict_runs = entry.get("patched_strict_no_opengl") or {}
        if set(strict_runs) != {"napari_0_10_0", "napari_threedee_0_0_29", "glue_1_4_0"}:
            raise ValueError(f"{platform_key} missing required patched strict scenarios")
        for name, item in strict_runs.items():
            if item.get("status") != "PASS_ALL_NO_OPENGL_GATES":
                raise ValueError(f"{platform_key} strict {name} did not PASS_ALL_NO_OPENGL_GATES")
            if item.get("process_exit") != 0 or item.get("child_waited") is not True:
                raise ValueError(f"{platform_key} strict {name} missing clean waited exit")
            if item.get("gates") != {
                "no_gl_execution": "PASS",
                "no_gl_loads": "PASS",
                "no_gl_install_link_requirement": "PASS",
            }:
                raise ValueError(f"{platform_key} strict {name} gates incomplete")
            if item.get("native_cleanup_performed") is not True:
                raise ValueError(f"{platform_key} strict {name} missing native_cleanup_performed")
            gauges = item.get("after_shutdown") or {}
            if any(gauges.get(k) != 0 for k in LIVE_GAUGES):
                raise ValueError(f"{platform_key} strict {name} non-zero shutdown gauge")

        hot_swap_runs = entry.get("stock_hot_swap") or {}
        if set(hot_swap_runs) != {"stock_napari_0_10_0", "stock_glue_1_4_0"}:
            raise ValueError(f"{platform_key} missing required stock hot-swap scenarios")
        for name, item in hot_swap_runs.items():
            if item.get("status") != "PASS_HOT_SWAP_GATES":
                raise ValueError(f"{platform_key} hot-swap {name} did not PASS_HOT_SWAP_GATES")
            if item.get("scope") != "hot-swap profile only; never a strict no-OpenGL qualification":
                raise ValueError(f"{platform_key} hot-swap {name} scope mismatch")
            if item.get("process_exit") != 0 or item.get("child_waited") is not True:
                raise ValueError(f"{platform_key} hot-swap {name} missing clean waited exit")
            if item.get("gates") != {"renderer_gl": "PASS", "no_gl_context_or_draw": "PASS"}:
                raise ValueError(f"{platform_key} hot-swap {name} gates mismatch")
            if item.get("renderer_gl_events") != 0 or item.get("unattributed_gl_events") != 0:
                raise ValueError(f"{platform_key} hot-swap {name} had renderer/unattributed GL events")
            if int(item.get("host_gl_events", 0)) <= 0:
                raise ValueError(f"{platform_key} stock hot-swap {name} expected host-attributed GL imports/loads")

        h03 = entry.get("glue_h03_reconciliation") or {}
        if (
            h03.get("process_exit") != 0
            or h03.get("child_waited") is not True
            or h03.get("stale_without_invalidation_reproduced") is not True
            or h03.get("distinct_with_invalidation_before_update") is not True
            or any((h03.get("after_shutdown") or {}).get(k) != 0 for k in LIVE_GAUGES)
        ):
            raise ValueError(f"{platform_key} glue_h03_reconciliation incomplete")

        phylib = entry.get("phylib_capability") or {}
        if (
            phylib.get("process_exit") != 0
            or phylib.get("child_waited") is not True
            or phylib.get("scope") != "import_only_cpu_co_resident_with_current_wheel"
            or phylib.get("rendering_qualified") is not False
            or phylib.get("modules_imported_count") != 12
            or phylib.get("package_tree_sha256") != PHYLIB_PACKAGE_TREE_SHA256
        ):
            raise ValueError(f"{platform_key} phylib_capability invalid")

        visbrain = entry.get("visbrain_boundary") or {}
        if (
            visbrain.get("host_admission_status") != "NOT_ADMITTED"
            or visbrain.get("rendering_qualified_for_visbrain_host") is not False
            or visbrain.get("unmodified_cp312_import_blocked") is not True
            or visbrain.get("primitive_equivalent_scope")
            != "vispy_primitive_equivalent_only_not_visbrain_host_admission"
            or visbrain.get("primitive_smoke_process_exit") != 0
            or any((visbrain.get("primitive_after_shutdown") or {}).get(k) != 0 for k in LIVE_GAUGES)
        ):
            raise ValueError(f"{platform_key} visbrain_boundary invalid")

    hosts = payload.get("host_items") or {}
    if set(hosts) != {"HOST-01", "HOST-02", "HOST-03", "HOST-04", "HOST-05", "HOST-06"}:
        raise ValueError("host_items must cover HOST-01..HOST-06")
    if hosts["HOST-04"].get("status") != "NOT_ADMITTED_PYSIDE2_LEGACY_EXCLUDED":
        raise ValueError("HOST-04 must record PySide2-legacy exclusion")
    if hosts["HOST-03"].get("windows_threedee_r1") != "open":
        raise ValueError("HOST-03 must keep windows threedee r1 open")


def test_disposition_doc_and_claim_separation_contract():
    assert DISPOSITIONS_DOC.is_file(), "docs/host-workflow-dispositions.md must exist"
    raw = DISPOSITIONS_DOC.read_bytes()
    assert b"\r\n" not in raw, "docs/host-workflow-dispositions.md must use LF-only line endings"
    text = raw.decode("utf-8")

    for required_token in (
        "HOST-01",
        "HOST-02",
        "HOST-03",
        "HOST-04",
        "HOST-05",
        "HOST-06",
        "H03",
        "PASS_HOT_SWAP_GATES",
        "PASS_ALL_NO_OPENGL_GATES",
        "hot-swap profile only; never a strict no-OpenGL qualification",
        "PySide2-legacy excluded unless ported to PyQt6/PySide6",
        "PASS_H03_HISTORICAL_UPSTREAM_DISPOSITION_ONLY",
        "rendering_qualified: false",
        "vispy_primitive_equivalent_only_not_visbrain_host_admission",
        WINDOWS_CURRENT_WHEEL_SHA256[:12],
        LINUX_CURRENT_WHEEL_SHA256[:12],
    ):
        assert required_token in text, f"missing required disposition token: {required_token}"


def test_hot_swap_policy_never_qualifies_strict_no_opengl_and_napari_010_guard():
    sys.path.insert(0, str(ROOT))
    try:
        from tools import audit_hot_swap, no_opengl_host_probe
    finally:
        sys.path.pop(0)

    assert audit_hot_swap.SCOPE == "hot-swap profile only; never a strict no-OpenGL qualification"
    assert no_opengl_host_probe.NAPARI_VERSIONS == ("0.10.0",)

    matrix = _read_json(NO_OPENGL_MATRIX)
    napari_rec = _read_json(NAPARI_010_RECORD)
    changes = _read_json(HOST_CHANGES)

    optional_host_rows = [
        row for row in matrix["rows"] if row.get("application") in ("napari", "napari-threedee", "glue-vispy-viewers")
    ]
    assert len(optional_host_rows) == 6
    assert all(row.get("mandatory") is False for row in optional_host_rows)

    win_td = next(row for row in napari_rec["rows"] if row["id"] == "windows-vulkan-napari-threedee-pyqt6")
    assert win_td["r1"] == "open"

    registered_patches = {(entry["host"], entry["version"]) for entry in changes["patches"]}
    for expected_patch in (
        ("napari", "0.10.0"),
        ("qtpy", "2.4.3"),
        ("glue-qt", "0.4.2"),
        ("glue-vispy-viewers", "1.4.0"),
    ):
        assert expected_patch in registered_patches


def test_dive_host04_pyside2_exclusion_and_qt6_blocker_contract():
    matrix = _read_json(NO_OPENGL_MATRIX)
    dive_row = next(row for row in matrix["rows"] if row["id"] == "dive-admission")
    assert dive_row["status"] == "NOT_ADMITTED"
    assert dive_row["mandatory"] is False

    inv = _read_json(ROOT / "compat/host-environments/dive-pyside6-investigation.json")
    assert inv["qtpy_scan"]["matches"] == []
    assert inv["probe_exit_code"] == 1
    assert "QAction" in inv["probe_exit_reason"]
    assert "QActionGroup" in inv["probe_exit_reason"]
    assert inv["graphics_qualification"] == "unresolved"

    scoped = _read_json(ROOT / "compat/host-environments/dive-pyside2-candidate-w10-scoped-parity.json")
    assert scoped["ordinary_host_teardown_qualified"] is False
    assert scoped["scatter_qualified"] is False
    assert scoped["installed_core_rollback_qualified"] is False
    assert "dive-opengl" in scoped["prior_failures_preserved"]


def test_glue_h03_invalidation_before_update_reconciliation_contract():
    manifest = _read_json(ROOT / "tests/reference/glue-opengl/manifest.json")
    assert "volume_edit" in manifest["errors"]
    assert manifest["errors"]["volume_edit"]["type"] == "AssertionError"
    for passing_case in ("scatter", "scatter_axes", "scatter_edit", "volume"):
        assert passing_case in manifest["fixtures"]

    disposition = _read_json(H03_DISPOSITION)
    assert disposition["status"] == "PASS_H03_HISTORICAL_UPSTREAM_DISPOSITION_ONLY"
    assert "FRB invalidation-before-update" in disposition["scope"]
    assert disposition["fixture_id"] == "H03"
    assert disposition["original_failure_preserved"] is True
    assert disposition["corrected_upstream_admitted"] is True
    assert disposition["validated_sources"]["tests/reference/glue-opengl/manifest.json"] == _sha256(
        ROOT / "tests/reference/glue-opengl/manifest.json"
    )

    ext_source = (ROOT / "tools/fixture_glue_extensions.py").read_text(encoding="utf-8")
    assert "from glue.core.fixed_resolution_buffer import invalidate_cache" in ext_source
    assert "invalidate_cache(data)" in ext_source


def test_phylib_and_visbrain_capability_vs_rendered_smoke_contract():
    lock = tomllib.loads(HOSTS_LOCK.read_text(encoding="utf-8"))
    assert lock["phylib"]["gpu"] is False
    assert lock["phylib"]["package_tree_sha256"] == PHYLIB_PACKAGE_TREE_SHA256

    for inv_rel in (
        "compat/host-environments/phylib.import-inventory.json",
        "compat/host-environments/phylib-linux.import-inventory.json",
    ):
        inv = _read_json(ROOT / inv_rel)
        assert inv["qualification"] == "import_inventory_only"
        assert inv["rendering_qualified"] is False
        assert inv["loaded_vispy_modules"] == []
        assert inv["loaded_qt_modules"] == []
        assert len(inv["modules"]) == 12
        assert inv["package_tree_sha256"] == PHYLIB_PACKAGE_TREE_SHA256

    matrix = _read_json(NO_OPENGL_MATRIX)
    vb_row = next(row for row in matrix["rows"] if row["id"] == "visbrain-admission")
    assert vb_row["status"] == "NOT_ADMITTED"

    vb_inv = _read_json(ROOT / "compat/host-environments/visbrain.import-inventory.json")
    assert vb_inv["qualification"] == "import_inventory_only"
    assert vb_inv["rendering_qualified"] is False
    assert "PyQt5.QtOpenGL" in vb_inv["loaded_qt_modules"]

    vb_fail = _read_json(ROOT / "compat/host-environments/visbrain.import-failure-1.json")
    assert any("pkg_resources" in err.get("traceback", "") for err in vb_fail.get("errors", []))


def test_receipt_validator_rejects_conflated_or_incomplete_claims():
    zero_gauges = {k: 0 for k in LIVE_GAUGES}
    strict_entry = {
        "status": "PASS_ALL_NO_OPENGL_GATES",
        "process_exit": 0,
        "child_waited": True,
        "gates": {
            "no_gl_execution": "PASS",
            "no_gl_loads": "PASS",
            "no_gl_install_link_requirement": "PASS",
        },
        "native_cleanup_performed": True,
        "after_shutdown": dict(zero_gauges),
    }
    hotswap_entry = {
        "status": "PASS_HOT_SWAP_GATES",
        "scope": "hot-swap profile only; never a strict no-OpenGL qualification",
        "process_exit": 0,
        "child_waited": True,
        "gates": {"renderer_gl": "PASS", "no_gl_context_or_draw": "PASS"},
        "renderer_gl_events": 0,
        "unattributed_gl_events": 0,
        "host_gl_events": 11,
    }
    plat_template = {
        "wheel_members_verified": 537,
        "scratch_cleaned": True,
        "scratch_absent_verified": True,
        "patched_strict_no_opengl": {
            "napari_0_10_0": copy.deepcopy(strict_entry),
            "napari_threedee_0_0_29": copy.deepcopy(strict_entry),
            "glue_1_4_0": copy.deepcopy(strict_entry),
        },
        "stock_hot_swap": {
            "stock_napari_0_10_0": copy.deepcopy(hotswap_entry),
            "stock_glue_1_4_0": copy.deepcopy(hotswap_entry),
        },
        "glue_h03_reconciliation": {
            "process_exit": 0,
            "child_waited": True,
            "stale_without_invalidation_reproduced": True,
            "distinct_with_invalidation_before_update": True,
            "after_shutdown": dict(zero_gauges),
        },
        "phylib_capability": {
            "process_exit": 0,
            "child_waited": True,
            "scope": "import_only_cpu_co_resident_with_current_wheel",
            "rendering_qualified": False,
            "modules_imported_count": 12,
            "package_tree_sha256": PHYLIB_PACKAGE_TREE_SHA256,
        },
        "visbrain_boundary": {
            "host_admission_status": "NOT_ADMITTED",
            "rendering_qualified_for_visbrain_host": False,
            "unmodified_cp312_import_blocked": True,
            "primitive_equivalent_scope": "vispy_primitive_equivalent_only_not_visbrain_host_admission",
            "primitive_smoke_process_exit": 0,
            "primitive_after_shutdown": dict(zero_gauges),
        },
    }
    sample = {
        "schema": 1,
        "acceptance_id": "host01-06-current-wheels-v1",
        "runtime_version": "0.17.0+vulkan.2",
        "claim_separation": {
            "stock_hot_swap_verdict": "PASS_HOT_SWAP_GATES",
            "patched_strict_no_opengl_verdict": "PASS_ALL_NO_OPENGL_GATES",
            "stock_hot_swap_qualifies_strict_no_opengl": False,
            "artifact_admitted_to_no_opengl_matrix": False,
            "no_opengl_matrix_modified": False,
        },
        "platforms": {
            "windows": {
                **copy.deepcopy(plat_template),
                "run_id": "gap-w2-6-windows-978",
                "wheel_sha256": WINDOWS_CURRENT_WHEEL_SHA256,
            },
            "wsl": {
                **copy.deepcopy(plat_template),
                "run_id": "gap-w2-6-wsl-979",
                "wheel_sha256": LINUX_CURRENT_WHEEL_SHA256,
                "mesa_lvp_sha256": MESA_PATCHED_SHA256,
                "xvfb_owned_and_waited": True,
                "wsl_exe_waited": True,
            },
        },
        "host_items": {
            "HOST-01": {"status": "RENEWED_HOT_SWAP_CURRENT_WHEELS"},
            "HOST-02": {"status": "RENEWED_NAPARI_0_10_0_CURRENT_WHEELS"},
            "HOST-03": {"status": "DETACHED_STRICT_OBSERVATION_CURRENT_WHEELS", "windows_threedee_r1": "open"},
            "HOST-04": {"status": "NOT_ADMITTED_PYSIDE2_LEGACY_EXCLUDED"},
            "HOST-05": {"status": "RENEWED_NAPARI_THREEDEE_0_0_29_CURRENT_WHEELS"},
            "HOST-06": {"status": "RECONCILED_GLUE_H03_PHYLIB_IMPORT_ONLY_VISBRAIN_BOUNDARY"},
        },
    }
    validate_host_renewal_receipt(sample)

    conflated = copy.deepcopy(sample)
    conflated["claim_separation"]["stock_hot_swap_qualifies_strict_no_opengl"] = True
    with pytest.raises(ValueError, match="never claim strict"):
        validate_host_renewal_receipt(conflated)

    promoted = copy.deepcopy(sample)
    promoted["platforms"]["windows"]["phylib_capability"]["rendering_qualified"] = True
    with pytest.raises(ValueError, match="phylib_capability"):
        validate_host_renewal_receipt(promoted)

    leaked = copy.deepcopy(sample)
    leaked["platforms"]["wsl"]["patched_strict_no_opengl"]["glue_1_4_0"]["after_shutdown"]["live_buffer_bytes"] = 1
    with pytest.raises(ValueError, match="non-zero shutdown gauge"):
        validate_host_renewal_receipt(leaked)

    if ACCEPTANCE_RECEIPT.is_file():
        raw = ACCEPTANCE_RECEIPT.read_bytes()
        assert b"\r\n" not in raw, "host01-06-current-wheels-v1.json must be LF-only"
        validate_host_renewal_receipt(json.loads(raw.decode("utf-8")))


@pytest.mark.gpu
@pytest.mark.wheel
def test_current_wheel_glue_h03_invalidation_and_rendered_workflows(tmp_path):
    wheel_env = os.environ.get("VISPY_RENEWAL_WHEEL")
    glue_python = os.environ.get("VISPY_RENEWAL_GLUE_PYTHON")
    if not wheel_env or not glue_python:
        pytest.skip("set VISPY_RENEWAL_WHEEL and VISPY_RENEWAL_GLUE_PYTHON for installed Glue H03 renewal")

    wheel = Path(wheel_env).resolve(strict=True)
    py_exe = Path(glue_python).absolute()
    assert py_exe.exists(), f"missing Glue interpreter: {py_exe}"
    allow_software = os.environ.get("VISPY_RENEWAL_ALLOW_SOFTWARE") == "1"
    out_file = tmp_path / "glue_h03_result.json"

    probe_code = """
import gc, json, os, sys
from pathlib import Path
import numpy as np

root = Path(sys.argv[1]).resolve()
wheel = Path(sys.argv[2]).resolve()
out_file = Path(sys.argv[3]).resolve()
allow_software = sys.argv[4] == "1"

sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tools"))
import no_opengl_host_probe as hp
from tools import fixture_glue_extensions as fge

os.environ.setdefault("QT_API", "pyqt6")
import vispy
from vispy import _dawn, app, io

payload_check = hp.verify_installed_payload(wheel, Path(vispy.__file__).parent)
assert vispy.__version__ == "0.17.0+vulkan.2", vispy.__version__
assert Path(_dawn.__file__).resolve().parent == Path(vispy.__file__).resolve().parent

info = dict(_dawn.device_info())
assert info["ok"] and info["backend"] == "Vulkan", info
if not allow_software:
    assert not info["software"], info

qapp = app.use_app("pyqt6")
qapp.native.setQuitOnLastWindowClosed(False)

# 1. Reproduce original H03 stale FRB behavior when invalidate_cache(data) is omitted
from glue.config import settings
from glue.core import Data, DataCollection
from glue_qt.app.application import GlueApplication
from glue_vispy_viewers.volume.qt.volume_viewer import VispyVolumeViewer
from glue.viewers.volume3d.viewer_state import VolumeViewerState3D

old_bg, old_fg = settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR
settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR = "black", "white"
app_stale = None
try:
    axis = np.linspace(-1, 1, 32, dtype=np.float32)
    z, y, x = np.meshgrid(axis, axis, axis, indexing="ij")
    data0 = Data(label="stale check", intensity=((x / .7) ** 2 + (y / .55) ** 2 + (z / .4) ** 2 <= 1).astype(np.float32))
    app_stale = GlueApplication(DataCollection([data0]))
    v0 = app_stale.new_data_viewer(VispyVolumeViewer, state=VolumeViewerState3D(resolution=32, downsample=False))
    assert v0.add_data(data0)
    st0 = v0.state
    st0.visible_axes = False
    st0.perspective_view = False
    ly0 = st0.layers[0]
    ly0.alpha = 1
    ly0.color_mode = "Fixed"
    ly0.color = "#00ff00"
    ly0.attribute = data0.id["intensity"]
    ly0.v_min, ly0.v_max = 0, 1
    st0.set_limits(-.5, 31.5, -.5, 31.5, -.5, 31.5)
    c0 = v0._vispy_widget.canvas
    c0.native.setFixedSize(128, 128)
    app_stale.show()
    v0.show()
    qapp.process_events()
    c0.size = (128, 128)
    c0.central_widget.size = (128, 128)
    cam0 = v0._vispy_widget.view.camera
    cam0.azimuth, cam0.elevation = 0, 0
    cam0.center, cam0.scale_factor = (0, 0, 0), 2.5
    c0.app.process_events()
    _ = np.array(c0.render(size=(128, 128), alpha=True), copy=True)
    # Now mutate without invalidate_cache(data0): FRB stays cached at center (64, 64)!
    upd = np.zeros((32, 32, 32), np.float32)
    upd[10:22, 8:24, 18:26] = 1
    data0.update_components({data0.id["intensity"]: upd})
    ly0.color = "#0000ff"
    c0.app.process_events()
    stale_img = np.array(c0.render(size=(128, 128), alpha=True), copy=True)
    stale_center_pixel = stale_img[64, 64].tolist()
    without_invalidation_stale = (stale_center_pixel == [0, 0, 255, 255])
finally:
    if app_stale is not None:
        for group in app_stale.viewers:
            for vw in group:
                vw.close(warn=False)
        app_stale.close()
    settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR = old_bg, old_fg
    for _ in range(6):
        qapp.process_events()

# 2. Run reconciled fixture_glue_extensions with invalidate_cache(data) before update_components
img_vol, cmds_vol, shd_vol, _ = fge.render("volume")
fge.assert_landmarks("volume", img_vol)
img_edit, cmds_edit, shd_edit, params_edit = fge.render("volume_edit")
fge.assert_landmarks("volume_edit", img_edit)
assert cmds_edit and shd_edit
assert not np.array_equal(img_vol, img_edit)
assert not np.array_equal(stale_img, img_edit)

png_out = out_file.parent / "glue_h03_volume_edit.png"
io.write_png(str(png_out), img_edit)

for _ in range(8):
    qapp.process_events()
gc.collect()
_dawn.process_events()
_dawn.shutdown()
state = dict(_dawn.probe())
ctrl = {
    "without_invalidation_stale": bool(without_invalidation_stale),
    "stale_center_rgba": stale_center_pixel,
    "with_invalidation_updated": True,
    "updated_center_rgba": img_edit[64, 64].tolist(),
    "updated_box_rgba": img_edit[64, 88].tolist(),
}
assert ctrl["without_invalidation_stale"] is True, ctrl
result = {
    "status": "PASS",
    "wheel_sha256": payload_check["wheel_sha256"],
    "wheel_members_verified": payload_check["verified_files"],
    "device": info,
    "cache_control": ctrl,
    "volume_edit_export": str(png_out),
    "after_shutdown": state,
}
out_file.write_text(json.dumps(result, indent=2) + "\\n", encoding="utf-8")
"""
    script_file = tmp_path / "run_glue_h03_probe.py"
    script_file.write_text(probe_code, encoding="utf-8", newline="\n")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["VISPY_QT_PRESENTATION"] = "readback"
    for k in ("PYTHONPATH", "PYTHONHOME", "PYTHONOPTIMIZE"):
        env.pop(k, None)

    proc = subprocess.run(
        [str(py_exe), "-I", "-B", str(script_file), str(ROOT), str(wheel), str(out_file), "1" if allow_software else "0"],
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert proc.returncode == 0, f"Glue H03 probe failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
    data = _read_json(out_file)
    assert data["status"] == "PASS"
    assert data["wheel_members_verified"] == 537
    assert data["cache_control"]["without_invalidation_stale"] is True
    assert data["cache_control"]["with_invalidation_updated"] is True
    assert all(data["after_shutdown"][g] == 0 for g in LIVE_GAUGES), data["after_shutdown"]


@pytest.mark.gpu
@pytest.mark.wheel
def test_current_wheel_phylib_co_residency_and_visbrain_boundary_smoke(tmp_path):
    wheel_env = os.environ.get("VISPY_RENEWAL_WHEEL")
    phylib_python = os.environ.get("VISPY_RENEWAL_PHYLIB_PYTHON")
    qt_python = os.environ.get("VISPY_RENEWAL_QT_PYTHON")
    phylib_source = os.environ.get("VISPY_RENEWAL_PHYLIB_SOURCE")
    visbrain_source = os.environ.get("VISPY_RENEWAL_VISBRAIN_SOURCE")
    if not (wheel_env and phylib_python and qt_python and phylib_source and visbrain_source):
        pytest.skip("set VISPY_RENEWAL_WHEEL, VISPY_RENEWAL_PHYLIB_PYTHON, VISPY_RENEWAL_QT_PYTHON, and host sources")

    wheel = Path(wheel_env).resolve(strict=True)
    allow_software = os.environ.get("VISPY_RENEWAL_ALLOW_SOFTWARE") == "1"

    # 1. phylib 2.7.1 import-only + co-residency with installed current VisPy wheel
    phylib_out = tmp_path / "phylib_coresidency.json"
    phylib_script = tmp_path / "run_phylib_probe.py"
    phylib_script.write_text(
        """
import hashlib, importlib, json, sys
import hashlib
from pathlib import Path

root = Path(sys.argv[1]).resolve()
wheel = Path(sys.argv[2]).resolve()
phylib_pkg_parent = Path(sys.argv[3]).resolve()
out_file = Path(sys.argv[4]).resolve()

sys.path.insert(0, str(root / "tools"))
import host_inventory as hi
import no_opengl_host_probe as hp

sys.path.insert(0, str(phylib_pkg_parent))
pin = hi.read_hosts(hi.LOCK)["phylib"]
pkg_dir = phylib_pkg_parent / "phylib"
pkg_sha = hi.source_inventory(pkg_dir)["sha256"]
assert pkg_sha == pin["package_tree_sha256"], pkg_sha

imported = []
for mod_name in pin["import_probe_modules"]:
    mod = importlib.import_module(mod_name)
    imported.append(mod_name)

loaded_vispy_before = [m for m in sys.modules if m == "vispy" or m.startswith("vispy.")]
loaded_qt_before = [m for m in sys.modules if m.split(".")[0] in ("PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy")]
assert loaded_vispy_before == [], loaded_vispy_before
assert loaded_qt_before == [], loaded_qt_before

import vispy
from vispy import _dawn
payload = hp.verify_installed_payload(wheel, Path(vispy.__file__).parent)
assert vispy.__version__ == "0.17.0+vulkan.2"

out_file.write_text(json.dumps({
    "status": "PASS",
    "scope": "import_only_cpu_co_resident_with_current_wheel",
    "rendering_qualified": False,
    "modules_imported": imported,
    "package_tree_sha256": pkg_sha,
    "wheel_sha256": payload["wheel_sha256"],
    "wheel_members_verified": payload["verified_files"],
}, indent=2) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
        newline="\n",
    )
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k in ("PYTHONPATH", "PYTHONHOME", "PYTHONOPTIMIZE"):
        env.pop(k, None)

    p1 = subprocess.run(
        [str(Path(phylib_python).absolute()), "-I", "-B", str(phylib_script), str(ROOT), str(wheel), str(phylib_source), str(phylib_out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p1.returncode == 0, f"phylib probe failed:\n{p1.stdout}\n{p1.stderr}"
    phylib_res = _read_json(phylib_out)
    assert phylib_res["rendering_qualified"] is False
    assert len(phylib_res["modules_imported"]) == 12
    assert phylib_res["package_tree_sha256"] == PHYLIB_PACKAGE_TREE_SHA256
    assert phylib_res["wheel_members_verified"] == 537

    # 2. Visbrain 0.4.5 unmodified cp312/Qt6 boundary + VisPy primitive equivalent rendered smoke
    vb_out = tmp_path / "visbrain_boundary.json"
    vb_script = tmp_path / "run_visbrain_boundary.py"
    vb_script.write_text(
        """
import gc, json, os, sys
import hashlib
from pathlib import Path
import numpy as np

root = Path(sys.argv[1]).resolve()
wheel = Path(sys.argv[2]).resolve()
vb_src = Path(sys.argv[3]).resolve()
out_file = Path(sys.argv[4]).resolve()
allow_software = sys.argv[5] == "1"

# First verify unmodified visbrain 0.4.5 import_probe_modules + gui fail closed in clean cp312/Qt6 no-GL consumer
import importlib
sys.path.insert(0, str(vb_src))
blocked_exc = None
try:
    for _mod in ("visbrain", "visbrain.objects", "visbrain.visuals", "visbrain.gui"):
        importlib.import_module(_mod)
except BaseException as exc:
    blocked_exc = f"{type(exc).__name__}: {exc}"
finally:
    sys.excepthook = sys.__excepthook__
    sys.path.pop(0)
    for k in [m for m in list(sys.modules) if m == "visbrain" or m.startswith("visbrain.")]:
        sys.modules.pop(k, None)
assert blocked_exc is not None, "unmodified visbrain 0.4.5 modules unexpectedly imported in clean cp312/Qt6 consumer"

sys.path.insert(0, str(root / "tools"))
import no_opengl_host_probe as hp
import vispy
from vispy import _dawn, app, io, scene

payload = hp.verify_installed_payload(wheel, Path(vispy.__file__).parent)
info = dict(_dawn.device_info())
assert info["ok"] and info["backend"] == "Vulkan", info
if not allow_software:
    assert not info["software"], info

qapp = app.use_app("pyqt6")
qapp.native.setQuitOnLastWindowClosed(False)

canvas = scene.SceneCanvas(keys=None, size=(256, 256), show=True, bgcolor="black", app="pyqt6", config={"samples": 0})
try:
    view = canvas.central_widget.add_view()
    view.camera = scene.TurntableCamera(azimuth=0.0, elevation=90.0, roll=0.0, center=(0.0, 0.0, 0.0), scale_factor=4.0)
    xyz = np.array([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [-1.0, 1.0, 0.0], [1.0, 1.0, 0.0]], dtype=np.float32)
    seg = np.array([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [-1.0, -1.0, 0.0], [-1.0, 1.0, 0.0], [1.0, -1.0, 0.0], [1.0, 1.0, 0.0]], dtype=np.float32)
    markers = scene.visuals.Markers(pos=xyz, face_color="red", size=14.0, edge_width=0.0, parent=view.scene)
    lines = scene.visuals.Line(pos=seg, color="cyan", width=3.0, connect="segments", method="gl", parent=view.scene)
    for _ in range(6):
        qapp.process_events()
    frame0 = canvas.render(alpha=True).copy()
    assert frame0.shape == (256, 256, 4) and frame0.dtype == np.uint8
    assert int(np.count_nonzero(frame0[:, :, :3])) > 128

    markers.set_data(pos=xyz, face_color="lime", size=18.0, edge_width=0.0)
    lines.set_data(pos=seg, color="yellow", width=5.0, connect="segments")
    for _ in range(6):
        qapp.process_events()
    frame1 = canvas.render(alpha=True).copy()
    assert frame1.shape == (256, 256, 4) and frame1.dtype == np.uint8
    assert not np.array_equal(frame0, frame1)
    png_path = out_file.parent / "vispy_primitive_equivalent.png"
    io.write_png(str(png_path), frame1)
    assert png_path.is_file() and png_path.stat().st_size > 100
finally:
    canvas.close()
    for _ in range(6):
        qapp.process_events()

gc.collect()
_dawn.process_events()
_dawn.shutdown()
state = dict(_dawn.probe())
out_file.write_text(json.dumps({
    "host_admission_status": "NOT_ADMITTED",
    "rendering_qualified_for_visbrain_host": False,
    "unmodified_cp312_import_blocked": True,
    "unmodified_cp312_blocker": blocked_exc,
    "primitive_equivalent_scope": "vispy_primitive_equivalent_only_not_visbrain_host_admission",
    "wheel_sha256": payload["wheel_sha256"],
    "wheel_members_verified": payload["verified_files"],
    "after_shutdown": state,
}, indent=2) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
        newline="\n",
    )
    env_qt = dict(env)
    env_qt["VISPY_QT_PRESENTATION"] = "readback"
    p2 = subprocess.run(
        [
            str(Path(qt_python).absolute()),
            "-I",
            "-B",
            str(vb_script),
            str(ROOT),
            str(wheel),
            str(visbrain_source),
            str(vb_out),
            "1" if allow_software else "0",
        ],
        env=env_qt,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert p2.returncode == 0, f"visbrain boundary probe failed:\n{p2.stdout}\n{p2.stderr}"
    vb_res = _read_json(vb_out)
    assert vb_res["host_admission_status"] == "NOT_ADMITTED"
    assert vb_res["rendering_qualified_for_visbrain_host"] is False
    assert vb_res["unmodified_cp312_import_blocked"] is True
    assert vb_res["primitive_equivalent_scope"] == "vispy_primitive_equivalent_only_not_visbrain_host_admission"
    assert all(vb_res["after_shutdown"][g] == 0 for g in LIVE_GAUGES), vb_res["after_shutdown"]
