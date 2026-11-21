# SPDX-License-Identifier: AGPL-3.0-only
"""Pure-CPU CI-portable contract for HOST-03 optional hosts & Wave 3 current-wheel renewals."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_NO_OPENGL_MATRIX_SHA256 = (
    "230b12f3d4ed418cde3b0313fbdea36557b02a61c80a1cf637699d7a9bc50fc4"
)
EXPECTED_NAPARI_010_MATRIX_SHA256 = (
    "a724432bb7b29de635d46eef4f694e6673ecf9ab84d12c535e1caee8d099f349"
)
EXPECTED_HOST01_06_CURRENT_SHA256 = (
    "e36a08c2006d8268a2285972f3b66e08fd23bb379f6a3d3aa209cdcdab115679"
)
EXPECTED_H03_DISPOSITION_SHA256 = (
    "33cf278d3b7dde5b06ec1a3800ec0098673920e0e1714513246c3f092ab14463"
)
EXPECTED_TK_NATIVE_INSTALLED_V1_SHA256 = (
    "a28f459d08b293bc6213982da0a515390e764fbb0ef9012a68907fb17fef6473"
)
EXPECTED_TK_NATIVE_PROTOTYPE_V1_SHA256 = (
    "36ee7eafba447153db253bee4fa7fb97e795ed00abb9aa91b46f60b494541b27"
)
EXPECTED_SECONDARY_STORE_SHA256 = (
    "b164e3fdc85863a2327b508ea60f8d3068f740cfe90f665aa52905e28bfb3ca5"
)

CURRENT_WINDOWS_WHEEL_SHA256 = (
    "9919a280a5de2c4bec45837078cb1d405e7169933ddcfb0758aa7d6a82722d39"
)
CURRENT_LINUX_WHEEL_SHA256 = (
    "e600b29e5259b896cc9d0fe36bbb5760260946aef53c013f8fc74e2fd0153007"
)
HEADLESS_MESA_LVP_SHA256 = (
    "9c5c41b3a7b9d759b0960c868f10375281798ad084150716d6d122c8789b9e12"
)
EXPECTED_SOURCE_COMMIT = "613cacfb73b1b4424dc098241c1eaf7553746c90"

TEN_ZERO_SHUTDOWN_GAUGES = {
    "pending_tickets": 0,
    "queued_frames": 0,
    "live_buffer_bytes": 0,
    "live_cpu_buffer_bytes": 0,
    "live_texture_bytes": 0,
    "canvas_texture_bytes": 0,
    "transient_buffer_bytes": 0,
    "line_resource_pool_busy_slots": 0,
    "line_resource_pool_bytes": 0,
    "host_import_pinned_bytes": 0,
}

OPTIONAL_ROW_TO_RECEIPT_KEY = {
    "windows-vulkan-napari-pyqt6": ("windows", "napari_0_10_0"),
    "windows-vulkan-glue-vispy-viewers-pyqt6": ("windows", "glue_1_4_0"),
    "windows-vulkan-napari-threedee-pyqt6": ("windows", "napari_threedee_0_0_29"),
    "wsl-linux-lavapipe-x11-napari-pyqt6": ("wsl", "napari_0_10_0"),
    "wsl-linux-lavapipe-x11-glue-vispy-viewers-pyqt6": ("wsl", "glue_1_4_0"),
    "wsl-linux-lavapipe-x11-napari-threedee-pyqt6": ("wsl", "napari_threedee_0_0_29"),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_lf_json(rel_path: str, *, require_lf: bool = True) -> tuple[dict, str]:
    path = REPO_ROOT / rel_path
    assert path.is_file(), f"Missing tracked JSON file: {rel_path}"
    raw = path.read_bytes()
    if require_lf:
        assert b"\r" not in raw, f"CRLF forbidden in tracked JSON file: {rel_path}"
    return json.loads(raw.decode("utf-8")), _sha256_bytes(raw)


def _is_hex64(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_optional_hosts_view(
    view: dict,
    matrix: dict,
    napari_010: dict,
    host_receipt: dict,
) -> None:
    _require(view.get("schema") == 1, "schema must be 1")
    _require(
        view.get("manifest_id") == "no-opengl-optional-hosts-current-v1",
        "unexpected manifest_id",
    )
    _require(view.get("runtime_version") == "0.17.0+vulkan.2", "unexpected runtime_version")
    _require(
        view.get("status") == "PASS_ADDITIVE_OPTIONAL_HOSTS_CURRENT_WHEEL_VIEW",
        "unexpected status",
    )
    _require(
        view.get("coverage_ids") == ["HOST-01", "HOST-02", "HOST-03", "HOST-04", "HOST-05", "HOST-06"],
        "unexpected coverage_ids",
    )

    store = view.get("evidence_store")
    _require(
        isinstance(store, dict)
        and store.get("path") == "compat/evidence-stores/secondary-v1.json"
        and store.get("sha256") == EXPECTED_SECONDARY_STORE_SHA256,
        "missing or invalid secondary evidence store binding",
    )

    preserved = view.get("preserved_frozen_records", {})
    _require(
        preserved.get("no_opengl_matrix", {}).get("sha256") == EXPECTED_NO_OPENGL_MATRIX_SHA256
        and preserved.get("no_opengl_matrix", {}).get("modified") is False,
        "frozen no-opengl-matrix preservation violated",
    )
    _require(
        preserved.get("no_opengl_napari_0_10_0", {}).get("sha256") == EXPECTED_NAPARI_010_MATRIX_SHA256
        and preserved.get("no_opengl_napari_0_10_0", {}).get("modified") is False
        and preserved.get("no_opengl_napari_0_10_0", {}).get("windows_threedee_r1") == "open",
        "frozen no-opengl-napari-0.10.0 or R1 preservation violated",
    )
    _require(
        preserved.get("host01_06_current_wheels_receipt", {}).get("sha256")
        == EXPECTED_HOST01_06_CURRENT_SHA256,
        "host01-06-current-wheels-v1 hash mismatch",
    )
    _require(
        preserved.get("h03_upstream_disposition", {}).get("sha256") == EXPECTED_H03_DISPOSITION_SHA256,
        "h03-upstream-disposition-v1 hash mismatch",
    )

    claims = view.get("claim_separation", {})
    _require(claims.get("additive_view_only") is True, "must be additive_view_only")
    _require(claims.get("no_opengl_matrix_modified") is False, "matrix cannot be modified")
    _require(claims.get("no_opengl_napari_0_10_0_modified") is False, "napari matrix cannot be modified")
    _require(
        claims.get("artifact_admitted_to_no_opengl_matrix") is False,
        "additive view cannot claim matrix artifact admission",
    )
    _require(
        claims.get("stock_hot_swap_qualifies_strict_no_opengl") is False,
        "stock hot-swap cannot claim strict no-OpenGL qualification",
    )

    matrix_optional = {
        row["id"]: row
        for row in matrix["rows"]
        if row.get("mandatory") is False and row.get("status") == "QUALIFIED"
    }
    _require(
        set(matrix_optional) == set(OPTIONAL_ROW_TO_RECEIPT_KEY),
        "matrix optional strict row set mismatch",
    )
    napari_rows = {row["id"]: row for row in napari_010["rows"]}
    _require(
        napari_rows["windows-vulkan-napari-threedee-pyqt6"].get("r1") == "open",
        "napari 0.10.0 Windows threedee R1 must remain open",
    )

    rows = view.get("optional_strict_rows", [])
    _require(isinstance(rows, list) and len(rows) == 6, "expected 6 optional_strict_rows")
    seen_ids = set()
    for row in rows:
        rid = row.get("id")
        _require(rid in matrix_optional and rid not in seen_ids, f"invalid or duplicate row id {rid!r}")
        seen_ids.add(rid)
        m_row = matrix_optional[rid]
        plat_key, host_key = OPTIONAL_ROW_TO_RECEIPT_KEY[rid]
        plat_receipt = host_receipt["platforms"][plat_key]
        h_rec = plat_receipt["patched_strict_no_opengl"][host_key]

        _require(row.get("mandatory") is False, f"{rid} must have mandatory=False")
        _require(row.get("platform") == m_row["platform"], f"{rid} platform mismatch")
        _require(row.get("application") == m_row["application"], f"{rid} application mismatch")
        _require(row.get("binding") == m_row["binding"], f"{rid} binding mismatch")
        _require(
            row.get("matrix_pinned_artifact_sha256") == m_row["artifact_sha256"],
            f"{rid} matrix_pinned_artifact_sha256 mismatch",
        )
        _require(
            row.get("matrix_environment_id") == m_row["environment_id"],
            f"{rid} matrix_environment_id mismatch",
        )
        expected_wheel = (
            CURRENT_WINDOWS_WHEEL_SHA256 if plat_key == "windows" else CURRENT_LINUX_WHEEL_SHA256
        )
        _require(row.get("current_wheel_sha256") == expected_wheel, f"{rid} wheel sha mismatch")
        _require(row.get("current_run_id") == plat_receipt["run_id"], f"{rid} run_id mismatch")
        _require(
            row.get("current_status") == "PASS_ALL_NO_OPENGL_GATES"
            and h_rec.get("status") == "PASS_ALL_NO_OPENGL_GATES",
            f"{rid} strict status mismatch",
        )
        _require(
            row.get("artifact_admitted_to_no_opengl_matrix") is False,
            f"{rid} cannot claim matrix admission",
        )
        _require(
            row.get("process_exit") == 0 and row.get("child_waited") is True,
            f"{rid} must have exited 0 and waited",
        )
        _require(row.get("wheel_members_verified") == 537, f"{rid} must verify 537 wheel members")
        _require(
            row.get("gates")
            == {
                "no_gl_execution": "PASS",
                "no_gl_loads": "PASS",
                "no_gl_install_link_requirement": "PASS",
            },
            f"{rid} strict gates mismatch",
        )
        _require(
            row.get("after_shutdown") == TEN_ZERO_SHUTDOWN_GAUGES
            and h_rec.get("after_shutdown") == TEN_ZERO_SHUTDOWN_GAUGES,
            f"{rid} non-zero Dawn shutdown gauges",
        )
        _require(
            isinstance(row.get("report"), str)
            and row["report"].startswith("@evidence/build/runs/")
            and row.get("report_sha256") == h_rec["report_sha256"]
            and row.get("worker_sha256") == h_rec["worker_sha256"]
            and row.get("functional_sha256") == h_rec["functional_sha256"],
            f"{rid} evidence sha mismatch against host01-06 receipt",
        )
        if rid == "windows-vulkan-napari-threedee-pyqt6":
            _require(row.get("r1") == "open", "windows-vulkan-napari-threedee-pyqt6 must keep r1 == 'open'")
            _require(
                isinstance(row.get("r1_note"), str) and "stays open" in row["r1_note"],
                "windows-vulkan-napari-threedee-pyqt6 must explain why R1 stays open",
            )

    bounded = view.get("non_admitted_and_bounded_hosts", {})
    _require(
        bounded.get("dive-admission", {}).get("status") == "NOT_ADMITTED"
        and bounded.get("dive-admission", {}).get("pyside2_legacy_excluded") is True,
        "DIVE must remain NOT_ADMITTED",
    )
    _require(
        bounded.get("visbrain-admission", {}).get("status") == "NOT_ADMITTED"
        and bounded.get("visbrain-admission", {}).get("rendering_qualified_for_visbrain_host") is False,
        "Visbrain must remain NOT_ADMITTED",
    )
    _require(
        bounded.get("phylib-import-only", {}).get("status") == "IMPORT_ONLY_CPU_CAPABILITY"
        and bounded.get("phylib-import-only", {}).get("rendering_qualified") is False
        and bounded.get("phylib-import-only", {}).get("modules_imported_count") == 12,
        "phylib must remain import-only with rendering_qualified=False",
    )
    _require(
        bounded.get("glue-h03-reconciliation", {}).get("stale_without_invalidation_reproduced") is True
        and bounded.get("glue-h03-reconciliation", {}).get("distinct_with_invalidation_before_update")
        is True,
        "glue H-03 invalidation control must be recorded",
    )

    hotswap = view.get("stock_hot_swap_profiles", {})
    _require(hotswap.get("strict_no_opengl_qualified") is False, "hot-swap cannot claim strict no-OpenGL")
    for plat_key in ("windows", "wsl"):
        for stock_key in ("stock_napari_0_10_0", "stock_glue_1_4_0"):
            entry = hotswap.get(plat_key, {}).get(stock_key, {})
            ref_entry = host_receipt["platforms"][plat_key]["stock_hot_swap"][stock_key]
            _require(entry.get("status") == "PASS_HOT_SWAP_GATES", f"{plat_key}/{stock_key} status")
            _require(entry.get("renderer_gl_events") == 0, f"{plat_key}/{stock_key} renderer_gl_events")
            _require(
                entry.get("unattributed_gl_events") == 0,
                f"{plat_key}/{stock_key} unattributed_gl_events",
            )
            _require(
                isinstance(entry.get("host_gl_events"), int) and entry["host_gl_events"] > 0,
                f"{plat_key}/{stock_key} host_gl_events",
            )
            _require(
                entry.get("report_sha256") == ref_entry["report_sha256"],
                f"{plat_key}/{stock_key} report_sha256 mismatch",
            )


def _validate_wave3_functional_manifest(
    doc: dict,
    *,
    expected_tier: str,
    expected_wheel_sha: str,
    expected_total_passed: int,
) -> None:
    _require(doc.get("schema") == 1, "schema must be 1")
    _require(doc.get("evidence_tier") == expected_tier, f"expected tier {expected_tier}")
    _require(doc.get("source_commit") == EXPECTED_SOURCE_COMMIT, "unexpected source_commit")
    _require(doc.get("scoped_admitted") is False, "scoped_admitted must be False")
    if "artifact_admitted" in doc:
        _require(doc.get("artifact_admitted") is False, "artifact_admitted must be False")
    _require(doc.get("publicly_delivered") is False, "publicly_delivered must be False")
    if "published" in doc:
        _require(doc.get("published") is False, "published must be False")

    if "platforms" in doc:
        for plat_key, wsha in (
            ("windows", CURRENT_WINDOWS_WHEEL_SHA256),
            ("wsl", CURRENT_LINUX_WHEEL_SHA256),
        ):
            p = doc["platforms"][plat_key]
            _require(p.get("wheel_sha256") == wsha, f"{plat_key} wheel sha mismatch")
            _require(p.get("source_overrides") == 0, f"{plat_key} source_overrides must be 0")
            _require(p.get("wheel_members_verified") == 537, f"{plat_key} must verify 537 members")
            _require(
                p.get("shutdown_gauges") == TEN_ZERO_SHUTDOWN_GAUGES,
                f"{plat_key} non-zero shutdown gauges",
            )
            _require(
                p.get("actual_exit") == 0 and p.get("child_waited") is True,
                f"{plat_key} child exit/wait",
            )
            _require(p.get("scratch_absent_verified") is True, f"{plat_key} scratch must be absent")
            js = p.get("junit_summary", {})
            _require(
                js.get("total") == expected_total_passed
                and js.get("passed") == expected_total_passed
                and js.get("skipped") == 0
                and js.get("failures") == 0
                and js.get("errors") == 0,
                f"{plat_key} junit_summary mismatch",
            )
            if plat_key == "wsl":
                _require(
                    p.get("xvfb_waited") is True
                    and p.get("wsl_outer_exit") == 0
                    and p.get("wsl_outer_waited") is True,
                    "wsl xvfb/outer wait failure",
                )
    else:
        _require(doc.get("wheel", {}).get("sha256") == expected_wheel_sha, "wheel sha mismatch")
        _require(doc.get("source_overrides") == 0, "source_overrides must be 0")
        _require(doc.get("installed_members_verified") == 537, "must verify 537 members")
        _require(
            doc.get("shutdown_gauges") == TEN_ZERO_SHUTDOWN_GAUGES,
            "non-zero shutdown gauges",
        )
        _require(
            doc.get("actual_exit") == 0 and doc.get("child_waited") is True,
            "child exit/wait failure",
        )
        _require(doc.get("scratch_absent_after_cleanup") is True, "scratch must be absent")
        js = doc.get("junit_summary", {})
        _require(
            js.get("total") == expected_total_passed
            and js.get("passed") == expected_total_passed
            and js.get("skipped") == 0
            and js.get("failures") == 0
            and js.get("errors") == 0,
            "junit_summary mismatch",
        )


def _collect_evidence_refs(node: object, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        if (
            set(node.keys()) >= {"path", "sha256"}
            and isinstance(node.get("path"), str)
            and node["path"].startswith("@evidence/")
        ):
            out.append((node["path"], str(node["sha256"])))
        for key, value in node.items():
            if isinstance(value, str) and value.startswith("@evidence/"):
                sibling_sha = node.get(f"{key}_sha256")
                if isinstance(sibling_sha, str):
                    out.append((value, sibling_sha))
            else:
                _collect_evidence_refs(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_evidence_refs(item, out)


def _resolve_local_secondary_store() -> Path | None:
    store_doc, store_sha = _read_lf_json(
        "compat/evidence-stores/secondary-v1.json", require_lf=False
    )
    assert store_sha == EXPECTED_SECONDARY_STORE_SHA256
    host_key = "windows" if os.name == "nt" else "posix"
    view = store_doc["hosts"][host_key]
    declared_source = Path(view["source_workspace"])
    storage = Path(view["storage_workspace"])
    try:
        if not declared_source.is_dir() or not storage.is_dir():
            return None
        if REPO_ROOT.resolve() != declared_source.resolve():
            return None
    except OSError:
        return None
    return storage


def test_w3_4a_frozen_matrix_and_historical_packet_preservation() -> None:
    matrix, matrix_sha = _read_lf_json("compat/no-opengl-matrix.json")
    assert matrix_sha == EXPECTED_NO_OPENGL_MATRIX_SHA256
    mandatory_rows = [r for r in matrix["rows"] if r.get("mandatory") is True]
    optional_rows = [r for r in matrix["rows"] if r.get("mandatory") is False]
    assert len(mandatory_rows) == 8
    assert len(optional_rows) == 8

    napari_010, napari_sha = _read_lf_json("compat/no-opengl-napari-0.10.0.json")
    assert napari_sha == EXPECTED_NAPARI_010_MATRIX_SHA256
    win_threedee = [
        r for r in napari_010["rows"] if r["id"] == "windows-vulkan-napari-threedee-pyqt6"
    ]
    assert len(win_threedee) == 1 and win_threedee[0]["r1"] == "open"

    _, host_sha = _read_lf_json("compat/api-acceptance/host01-06-current-wheels-v1.json")
    assert host_sha == EXPECTED_HOST01_06_CURRENT_SHA256

    _, h03_sha = _read_lf_json(
        "compat/api-acceptance/h03-upstream-disposition-v1.json", require_lf=False
    )
    assert h03_sha == EXPECTED_H03_DISPOSITION_SHA256

    _, tk_inst_sha = _read_lf_json(
        "compat/api-acceptance/tk-native-installed-v1.json", require_lf=False
    )
    assert tk_inst_sha == EXPECTED_TK_NATIVE_INSTALLED_V1_SHA256

    _, tk_proto_sha = _read_lf_json(
        "compat/api-acceptance/tk-native-prototype-v1.json", require_lf=False
    )
    assert tk_proto_sha == EXPECTED_TK_NATIVE_PROTOTYPE_V1_SHA256

    _, store_sha = _read_lf_json("compat/evidence-stores/secondary-v1.json", require_lf=False)
    assert store_sha == EXPECTED_SECONDARY_STORE_SHA256

    cand_files = sorted((REPO_ROOT / "compat/candidates/tk-state-resource-16").glob("*.json"))
    assert len(cand_files) >= 1
    for cf in cand_files:
        json.loads(cf.read_bytes().decode("utf-8"))

    disp_doc = REPO_ROOT / "docs/host-workflow-dispositions.md"
    assert disp_doc.is_file() and len(disp_doc.read_bytes()) > 0


def test_w3_4a_optional_hosts_current_wheel_additive_view_join() -> None:
    matrix, _ = _read_lf_json("compat/no-opengl-matrix.json")
    napari_010, _ = _read_lf_json("compat/no-opengl-napari-0.10.0.json")
    host_receipt, _ = _read_lf_json("compat/api-acceptance/host01-06-current-wheels-v1.json")
    view, _ = _read_lf_json("compat/no-opengl-optional-hosts-current-v1.json")

    _validate_optional_hosts_view(view, matrix, napari_010, host_receipt)
    assert host_receipt["host_items"]["HOST-03"]["windows_threedee_r1"] == "open"
    assert host_receipt["platforms"]["wsl"]["mesa_lvp_sha256"] == HEADLESS_MESA_LVP_SHA256
    assert host_receipt["platforms"]["wsl"]["xvfb_owned_and_waited"] is True
    assert host_receipt["platforms"]["wsl"]["wsl_exe_waited"] is True


def test_w3_4a_tk_native_current_wheels_manifest_contract() -> None:
    tk_doc, _ = _read_lf_json("compat/api-acceptance/tk-native-current-wheels-v1.json")
    _validate_wave3_functional_manifest(
        tk_doc,
        expected_tier="installed-experimental",
        expected_wheel_sha="",
        expected_total_passed=11,
    )
    assert tk_doc["coverage_ids"] == ["LIF-07", "LIF-07-NATIVE-ADMISSION"]
    assert tk_doc["default_presentation"] == "raster"
    assert tk_doc["native_admitted_mandatory_matrix"] is False
    assert tk_doc["no_opengl_matrix_modified"] is False
    assert tk_doc["claim_separation"]["default_tk_presentation"] == "raster"
    assert tk_doc["claim_separation"]["native_admitted_mandatory_matrix"] is False
    assert tk_doc["claim_separation"]["raster_default_isolation_verified"] is True
    assert tk_doc["claim_separation"]["photoimage_allocated_on_native_path"] is False
    assert tk_doc["claim_separation"]["wsl_x11_wsi_driver_separate_from_headless_mesa_9c5"] is True

    wsl_plat = tk_doc["platforms"]["wsl"]
    assert wsl_plat["driver_origin"]["used_in_run"] is True
    assert wsl_plat["separate_headless_driver_origin"]["library_sha256"] == HEADLESS_MESA_LVP_SHA256
    assert wsl_plat["separate_headless_driver_origin"]["used_in_run"] is False

    total_cases = 0
    for mod in tk_doc["test_modules"]:
        mod_path = REPO_ROOT / mod["path"]
        assert mod_path.is_file()
        assert not mod["path"].startswith("tests/contract/"), "GPU suite must not live in tests/contract/"
        raw = mod_path.read_bytes()
        assert b"\r" not in raw
        assert _sha256_bytes(raw) == mod["sha256"]
        assert mod["cases"]["skipped"] == 0 and mod["cases"]["failed"] == 0
        total_cases += mod["cases"]["passed"]
    assert total_cases == 11


def test_w3_4a_qt_multibinding_current_wheels_manifests_contract() -> None:
    win_doc, _ = _read_lf_json("compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json")
    wsl_doc, _ = _read_lf_json("compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json")

    _validate_wave3_functional_manifest(
        win_doc,
        expected_tier="installed-functional",
        expected_wheel_sha=CURRENT_WINDOWS_WHEEL_SHA256,
        expected_total_passed=12,
    )
    _validate_wave3_functional_manifest(
        wsl_doc,
        expected_tier="installed-functional",
        expected_wheel_sha=CURRENT_LINUX_WHEEL_SHA256,
        expected_total_passed=12,
    )
    assert wsl_doc["driver_artifact"]["sha256"] == HEADLESS_MESA_LVP_SHA256
    assert (
        wsl_doc["xvfb_waited"] is True
        and wsl_doc["wsl_outer_exit"] == 0
        and wsl_doc["wsl_outer_waited"] is True
    )

    for doc in (win_doc, wsl_doc):
        assert doc["coverage_ids"] == ["LIF-02", "LIF-03", "LIF-04", "LIF-06", "LIF-08"]
        assert doc["physical_multimonitor_claimed"] is False
        assert doc["physical_hid_claimed"] is False
        assert set(doc["toolkits"]) == {"pyqt5", "pyqt6", "pyside6"}
        assert set(doc["per_binding"]) == {"pyqt5", "pyqt6", "pyside6"}
        for bname, binfo in doc["per_binding"].items():
            assert binfo["actual_exit"] == 0 and binfo["child_waited"] is True
            assert binfo["source_overrides"] == 0
            assert binfo["installed_members_verified_before_after"] == 537
            assert binfo["competing_qt_modules"] == []
            assert binfo["shutdown_gauges"] == TEN_ZERO_SHUTDOWN_GAUGES
            b_junit = doc["junit_summary"]["per_binding"][bname]
            assert b_junit == {"total": 4, "passed": 4, "skipped": 0, "failures": 0, "errors": 0}
        assert len(doc["test_modules"]) == 1
        tmod = doc["test_modules"][0]
        assert tmod["path"] == "tests/qt/test_qt_multibinding_callbacks_hidpi_gpu.py"
        tpath = REPO_ROOT / tmod["path"]
        assert tpath.is_file()
        raw = tpath.read_bytes()
        assert b"\r" not in raw and _sha256_bytes(raw) == tmod["sha256"]


def test_w3_4a_api05_plot_transforms_current_wheels_manifests_contract(frozen_source_root) -> None:
    win_doc, _ = _read_lf_json("compat/api-acceptance/api05-plot-transforms-windows-v1.json")
    wsl_doc, _ = _read_lf_json("compat/api-acceptance/api05-plot-transforms-wsl-v1.json")

    _validate_wave3_functional_manifest(
        win_doc,
        expected_tier="installed-functional",
        expected_wheel_sha=CURRENT_WINDOWS_WHEEL_SHA256,
        expected_total_passed=16,
    )
    _validate_wave3_functional_manifest(
        wsl_doc,
        expected_tier="installed-functional",
        expected_wheel_sha=CURRENT_LINUX_WHEEL_SHA256,
        expected_total_passed=16,
    )
    assert win_doc["run_id"] == "gap-w3-3-api-plot-windows-989"
    assert wsl_doc["run_id"] == "gap-w3-3-api-plot-wsl-990"
    assert wsl_doc["driver_artifact"]["sha256"] == HEADLESS_MESA_LVP_SHA256
    assert (
        wsl_doc["xvfb_waited"] is True
        and wsl_doc["wsl_outer_exit"] == 0
        and wsl_doc["wsl_outer_waited"] is True
        and wsl_doc["wsl_guest_build_work"] == []
    )

    w5_tier1, _ = _read_lf_json("compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json")
    w5_mods = {m["path"]: m for m in w5_tier1["test_modules"]}
    wave3_historical_mod_hashes = {
        "tests/contract/test_subpackages_api05_contract.py": (
            "e48d6e6c53d62f2a5a4d80f148bc7ede149dfd47f7c9715327e9a9590ced2b40"
        ),
        "tests/visuals/test_plot_transforms_filters_gpu.py": (
            "e0834c97f2c5fea75cc025626bdf62628148ef209e67a0a0b6944bc6e6d8091a"
        ),
    }

    for doc in (win_doc, wsl_doc):
        assert doc["coverage_ids"] == ["API-05", "API-06"]
        assert doc["evidence_store"]["sha256"] == EXPECTED_SECONDARY_STORE_SHA256
        mods = {m["path"]: m for m in doc["test_modules"]}
        assert set(mods) == {
            "tests/contract/test_subpackages_api05_contract.py",
            "tests/visuals/test_plot_transforms_filters_gpu.py",
        }
        assert mods["tests/contract/test_subpackages_api05_contract.py"]["cases"] == {
            "passed": 12,
            "skipped": 0,
            "failed": 0,
        }
        assert mods["tests/visuals/test_plot_transforms_filters_gpu.py"]["cases"] == {
            "passed": 4,
            "skipped": 0,
            "failed": 0,
        }
        for rel_p, m_entry in mods.items():
            assert m_entry["sha256"] == wave3_historical_mod_hashes[rel_p]
            disk_p = frozen_source_root / rel_p
            assert disk_p.is_file()
            raw = disk_p.read_bytes()
            assert b"\r" not in raw and _sha256_bytes(raw) == w5_mods[rel_p]["sha256"]

    assert win_doc["collections_runtime_matrix"] == wsl_doc["collections_runtime_matrix"]
    cmat = win_doc["collections_runtime_matrix"]
    rendered = {k: v for k, v in cmat.items() if v["status"] == "rendered"}
    bounded = {k: v for k, v in cmat.items() if v["status"] == "error"}
    assert len(rendered) == 6 and len(bounded) == 3
    assert rendered["SegmentCollection_agg_shared"]["uses_shared_utype"] is True
    assert all(v["lit_pixels"] >= 50 for v in rendered.values())
    assert bounded["PointCollection_agg_local"]["error_type"] == "RuntimeError"
    assert bounded["SegmentCollection_raw_shared"]["error_type"] == "TypeError"
    assert bounded["PathCollection_raw"]["error_type"] == "TypeError"


WAVE5_EXPECTED_SOURCE_COMMIT = "3daf19be6c102764a5891ccbc29bf906e0588df1"
WAVE5_EXPECTED_SOURCE_TREE = "6c8d3bad7d86d42c623d3e20ba1bbee87273b169"
WAVE5_EXPECTED_WHEEL_SHA256S = {
    "win_amd64_cp311": "834fe5f7ab564ed9e7dd6bddb2b3a52aa7010c129fb6044ef85a0b35fdbb7e9c",
    "win_amd64_cp312": "ec8097cf151b6773916f07d8ee30d450392067827bc70bdf94ea5f09cf34210f",
    "win_amd64_cp313": "793dab792b689f8339be8cfb507397b8efa146a3801053805accef5475a96e51",
    "manylinux_2_39_x86_64_cp311": "fc8dd6cc10daa11457d86ea4b9c2eaeba5248aec23658260b644593646763dbe",
    "manylinux_2_39_x86_64_cp312": "513088c146014305eb695d12915dafe26f55316c45bf800a8363f27e4cfb5d78",
    "manylinux_2_39_x86_64_cp313": "1362eb6a567ed713834a8c69bf7297299c6266e43af980366087481a69fa7b64",
}


def _validate_wave5_tier1_and_plat02_manifests(tier1: dict, plat02: dict, source_root: Path) -> None:
    for doc, expected_id in (
        (tier1, "tier1-collections-jupyter-rfb-v1"),
        (plat02, "plat02-cp311-cp313-wheels-v1"),
    ):
        _require(doc.get("schema") == 1, f"{expected_id}: schema must be 1")
        _require(doc.get("acceptance_id") == expected_id, f"{expected_id}: unexpected acceptance_id")
        _require(doc.get("evidence_tier") == "installed-functional", f"{expected_id}: wrong evidence_tier")
        _require(doc.get("runtime_version") == "0.17.0+vulkan.2", f"{expected_id}: wrong runtime_version")
        _require(doc.get("source_commit") == WAVE5_EXPECTED_SOURCE_COMMIT, f"{expected_id}: wrong source_commit")
        _require(doc.get("source_tree") == WAVE5_EXPECTED_SOURCE_TREE, f"{expected_id}: wrong source_tree")
        _require(doc.get("scoped_admitted") is False, f"{expected_id}: scoped_admitted must be False")
        _require(doc.get("artifact_admitted") is False, f"{expected_id}: artifact_admitted must be False")
        _require(doc.get("publicly_delivered") is False, f"{expected_id}: publicly_delivered must be False")
        _require(doc.get("published") is False, f"{expected_id}: published must be False")
        _require(doc.get("plat02_closed") is False, f"{expected_id}: plat02_closed must be False")
        _require(doc.get("full_inventory_complete") is False, f"{expected_id}: full_inventory_complete must be False")
        _require(doc.get("default_sessions_unchanged") is True, f"{expected_id}: default_sessions_unchanged must be True")
        store = doc.get("evidence_store")
        _require(
            isinstance(store, dict)
            and store.get("path") == "compat/evidence-stores/secondary-v1.json"
            and store.get("sha256") == EXPECTED_SECONDARY_STORE_SHA256,
            f"{expected_id}: invalid evidence_store",
        )

    _require(plat02.get("cp310_gpu_wheels_claimed") is False, "cp310_gpu_wheels_claimed must be False")
    _require(plat02.get("cp314_gpu_wheels_claimed") is False, "cp314_gpu_wheels_claimed must be False")

    rfiles = tier1.get("runtime_files")
    _require(isinstance(rfiles, list) and len(rfiles) == 6, "tier1 runtime_files must have 6 entries")
    for rf in rfiles:
        _require(rf.get("line_endings") == "CRLF", f"runtime file {rf} must record CRLF")
        disk_p = source_root / rf["path"]
        _require(disk_p.is_file(), f"missing runtime file {rf['path']}")
        raw = disk_p.read_bytes()
        _require(
            raw.count(b"\r\n") == raw.count(b"\n") > 0
            and len(raw) == rf["bytes"]
            and _sha256_bytes(raw) == rf["sha256"],
            f"runtime file mismatch on {rf['path']}",
        )

    tmods = tier1.get("test_modules")
    _require(isinstance(tmods, list) and len(tmods) == 3, "tier1 test_modules must have 3 entries")
    for tm in tmods:
        _require(tm.get("line_endings") == "LF", f"test module {tm} must record LF")
        disk_p = source_root / tm["path"]
        _require(disk_p.is_file(), f"missing test module {tm['path']}")
        raw = disk_p.read_bytes()
        _require(
            b"\r" not in raw and len(raw) == tm["bytes"] and _sha256_bytes(raw) == tm["sha256"],
            f"test module mismatch on {tm['path']}",
        )

    cpu = tier1["source_freeze_1006"]["cpu_contracts"]
    per_mod = cpu["per_module_from_cpu_checks_log"]
    _require(
        cpu["passed"] == 85
        and cpu["failed"] == 0
        and cpu["skipped"] == 0
        and sum(per_mod.values()) == 85,
        "invalid 1006 cpu_contracts summary",
    )
    _require(
        tier1["source_freeze_1006"]["cpython_314_timerbackend_asyncio"]["status"] == "PASS",
        "cpython_314_timerbackend_asyncio must PASS",
    )

    cmat = tier1.get("collections_runtime_matrix")
    _require(isinstance(cmat, dict) and len(cmat) == 9, "collections_runtime_matrix must have 9 entries")
    for cname, centry in cmat.items():
        _require(centry.get("status") == "rendered", f"collection {cname} must be rendered")
        lp = centry.get("lit_pixels", {})
        _require(
            isinstance(lp, dict)
            and lp.get("windows_rtx4090", 0) > 0
            and lp.get("wsl_mesa", 0) > 0
            and lp.get("colab_tesla_t4", 0) > 0,
            f"collection {cname} missing positive per-host lit_pixels",
        )

    wheels = plat02.get("wheels")
    _require(
        isinstance(wheels, dict) and set(wheels) == set(WAVE5_EXPECTED_WHEEL_SHA256S),
        "plat02 wheels keys mismatch",
    )
    for wkey, expected_sha in WAVE5_EXPECTED_WHEEL_SHA256S.items():
        w = wheels[wkey]
        _require(w["wheel"]["sha256"] == expected_sha, f"{wkey}: wheel sha256 mismatch")
        _require(w["installed_members_verified"] == 537, f"{wkey}: installed_members_verified must be 537")
        _require(w["source_overrides"] == 0, f"{wkey}: source_overrides must be 0")
        _require(w["shutdown_gauges"] == TEN_ZERO_SHUTDOWN_GAUGES, f"{wkey}: non-zero shutdown_gauges")
        jrfb = w["suites"]["test_jupyter_rfb_gpu"]
        _require(
            jrfb == {"passed": 3, "skipped": 0, "failed": 0},
            f"{wkey}: test_jupyter_rfb_gpu must be 3 passed / 0 skipped",
        )
        if w["abi"] in ("cp311", "cp313"):
            ct = w["ctest"]
            _require(
                ct["total"] == 44
                and ct["passed"] == 44
                and ct["skipped"] == 0
                and ct["failures"] == 0
                and ct["errors"] == 0,
                f"{wkey}: ctest must be 44/44",
            )
        else:
            tk = w.get("tk_capture_recovery")
            _require(
                isinstance(tk, dict)
                and tk.get("tk_capture_cases")
                == {"total": 14, "passed": 14, "skipped": 0, "failures": 0, "errors": 0}
                and tk.get("direct_functional_status") == "PASS"
                and tk.get("shutdown_gauges") == TEN_ZERO_SHUTDOWN_GAUGES,
                f"{wkey}: missing 14/14 tk_capture_recovery",
            )

    colab = plat02.get("colab_tesla_t4_summary")
    _require(
        isinstance(colab, dict)
        and colab.get("gpu_model") == "NVIDIA Tesla T4"
        and colab.get("software") is False
        and colab.get("xvfb_waited") is True
        and colab.get("xvfb_exit") == 0
        and colab.get("session_stopped_in_finally") is True
        and colab.get("total_passed_cases_across_abis") == 225,
        "invalid colab_tesla_t4_summary",
    )
    for abi in ("cp311", "cp312", "cp313"):
        cabi = colab["abis"][abi]
        _require(
            cabi["source_overrides"] == 0
            and cabi["device"]["software"] is False
            and cabi["junit_summary"] == {"total": 75, "passed": 75, "skipped": 0, "failures": 0, "errors": 0}
            and cabi["shutdown_gauges"] == TEN_ZERO_SHUTDOWN_GAUGES,
            f"colab {abi}: invalid consumer receipt",
        )


def test_w5_tier1_collections_jupyter_rfb_and_plat02_wheels_manifests_contract(frozen_source_root) -> None:
    tier1, _ = _read_lf_json("compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json")
    plat02, _ = _read_lf_json("compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json")
    _validate_wave5_tier1_and_plat02_manifests(tier1, plat02, frozen_source_root)


def test_w3_4a_local_secondary_evidence_store_and_negative_fail_closed_controls(frozen_source_root) -> None:
    manifest_paths = (
        "compat/no-opengl-optional-hosts-current-v1.json",
        "compat/api-acceptance/tk-native-current-wheels-v1.json",
        "compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json",
        "compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json",
        "compat/api-acceptance/api05-plot-transforms-windows-v1.json",
        "compat/api-acceptance/api05-plot-transforms-wsl-v1.json",
        "compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json",
        "compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json",
    )
    all_refs: list[tuple[str, str]] = []
    for rel in manifest_paths:
        doc, _ = _read_lf_json(rel)
        _collect_evidence_refs(doc, all_refs)

    assert len(all_refs) >= 50
    for logical_path, expected_sha in all_refs:
        assert logical_path.startswith("@evidence/build/")
        assert ".." not in logical_path.split("/")
        assert "/build/work/" not in logical_path
        assert _is_hex64(expected_sha), f"Invalid sha256 on {logical_path}: {expected_sha!r}"

    local_store = _resolve_local_secondary_store()
    if local_store is not None:
        for logical_path, expected_sha in all_refs:
            rel_tail = logical_path[len("@evidence/") :]
            disk_file = local_store / rel_tail
            assert disk_file.is_file(), f"Missing local retained evidence file: {disk_file}"
            assert _sha256_bytes(disk_file.read_bytes()) == expected_sha, f"Hash mismatch: {disk_file}"

    # Fail-closed negative mutation controls
    matrix, _ = _read_lf_json("compat/no-opengl-matrix.json")
    napari_010, _ = _read_lf_json("compat/no-opengl-napari-0.10.0.json")
    host_receipt, _ = _read_lf_json("compat/api-acceptance/host01-06-current-wheels-v1.json")
    view, _ = _read_lf_json("compat/no-opengl-optional-hosts-current-v1.json")

    bad_r1 = copy.deepcopy(view)
    for r in bad_r1["optional_strict_rows"]:
        if r["id"] == "windows-vulkan-napari-threedee-pyqt6":
            r["r1"] = "closed"
    with pytest.raises(ValueError, match="r1"):
        _validate_optional_hosts_view(bad_r1, matrix, napari_010, host_receipt)

    bad_admit = copy.deepcopy(view)
    bad_admit["claim_separation"]["artifact_admitted_to_no_opengl_matrix"] = True
    with pytest.raises(ValueError, match="matrix artifact admission"):
        _validate_optional_hosts_view(bad_admit, matrix, napari_010, host_receipt)

    bad_hotswap = copy.deepcopy(view)
    bad_hotswap["claim_separation"]["stock_hot_swap_qualifies_strict_no_opengl"] = True
    with pytest.raises(ValueError, match="stock hot-swap"):
        _validate_optional_hosts_view(bad_hotswap, matrix, napari_010, host_receipt)

    bad_gauge = copy.deepcopy(view)
    bad_gauge["optional_strict_rows"][0]["after_shutdown"]["live_buffer_bytes"] = 64
    with pytest.raises(ValueError, match="shutdown gauges"):
        _validate_optional_hosts_view(bad_gauge, matrix, napari_010, host_receipt)

    api_win, _ = _read_lf_json("compat/api-acceptance/api05-plot-transforms-windows-v1.json")
    bad_skip = copy.deepcopy(api_win)
    bad_skip["junit_summary"]["skipped"] = 1
    with pytest.raises(ValueError, match="junit_summary"):
        _validate_wave3_functional_manifest(
            bad_skip,
            expected_tier="installed-functional",
            expected_wheel_sha=CURRENT_WINDOWS_WHEEL_SHA256,
            expected_total_passed=16,
        )

    bad_override = copy.deepcopy(api_win)
    bad_override["source_overrides"] = 1
    with pytest.raises(ValueError, match="source_overrides"):
        _validate_wave3_functional_manifest(
            bad_override,
            expected_tier="installed-functional",
            expected_wheel_sha=CURRENT_WINDOWS_WHEEL_SHA256,
            expected_total_passed=16,
        )

    w5_tier1, _ = _read_lf_json("compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json")
    w5_plat02, _ = _read_lf_json("compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json")

    bad_plat02_closed = copy.deepcopy(w5_plat02)
    bad_plat02_closed["plat02_closed"] = True
    with pytest.raises(ValueError, match="plat02_closed"):
        _validate_wave5_tier1_and_plat02_manifests(w5_tier1, bad_plat02_closed, frozen_source_root)

    bad_w5_admitted = copy.deepcopy(w5_tier1)
    bad_w5_admitted["scoped_admitted"] = True
    with pytest.raises(ValueError, match="scoped_admitted"):
        _validate_wave5_tier1_and_plat02_manifests(bad_w5_admitted, w5_plat02, frozen_source_root)

    bad_w5_cmat = copy.deepcopy(w5_tier1)
    bad_w5_cmat["collections_runtime_matrix"]["PathCollection_raw"]["status"] = "error"
    with pytest.raises(ValueError, match="PathCollection_raw"):
        _validate_wave5_tier1_and_plat02_manifests(bad_w5_cmat, w5_plat02, frozen_source_root)

    bad_w5_sw = copy.deepcopy(w5_plat02)
    bad_w5_sw["colab_tesla_t4_summary"]["software"] = True
    with pytest.raises(ValueError, match="colab_tesla_t4_summary"):
        _validate_wave5_tier1_and_plat02_manifests(w5_tier1, bad_w5_sw, frozen_source_root)


__all__ = [name for name in dir() if name.startswith("test_")]
