"""Admit actual ABI consumer evidence separately from Qt/platform release gates."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify_evidence(proof):
    for name, expected in proof["evidence_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name


def test_each_standard_python_abi_has_an_actual_external_graphics_and_rollback_pass():
    proof = load(ROOT / "compat/native-sdk/w5-windows-clean-consumers-provenance.json")
    builds = load(ROOT / "compat/native-sdk/w5-windows-python-matrix-provenance.json")
    verify_evidence(proof)
    assert set(proof["consumers"]) == set(builds["leaves"]) == {
        "cp310", "cp311", "cp312", "cp313", "cp314"
    }
    expected_numpy = {"cp310": "1.26.4", "cp311": "2.4.6", "cp312": "2.5.3",
                      "cp313": "2.5.3", "cp314": "2.5.3"}
    for abi, record in proof["consumers"].items():
        assert record["exit_code"] == record["pytest_skipped"] == 0
        assert record["pytest_passed"] == 1
        assert record["wheel_sha256"] == builds["leaves"][abi]["wheel_sha256"]
        assert record["evidence"]["dependencies"]["numpy"] == expected_numpy[abi]
        assert record["evidence"]["device"]["ok"]
        assert not record["evidence"]["device"]["software"]
        assert record["evidence"]["device"]["backend"] == "Vulkan"
        assert record["actual_native_clear_and_text_verified"]
        assert record["compiled_font_sdf_verified"] and record["assets_notices_verified"]
        assert record["uninstall_and_hashed_upstream_restore"] == "vispy==0.17.0"
        xml = "w5-clean-wheel-consumer.xml" if abi == "cp312" else f"w5-clean-wheel-{abi}-consumer.xml"
        suite = ET.parse(ROOT / "build/evidence" / xml).getroot().find("testsuite")
        assert suite.attrib["tests"] == "1"
        assert all(suite.attrib[name] == "0" for name in ("errors", "failures", "skipped"))
    assert not proof["full_release_matrix_qualified"]
    assert not proof["public_binding_host_matrix_qualified"]


def test_real_legacy_mutex_failure_has_a_causal_cpu_control_matrix():
    proof = load(ROOT / "compat/native-sdk/msvc-legacy-crt-compatibility-proof.json")
    verify_evidence(proof)
    observed = {(item["Runtime"], item["Variant"]): item["ExitCode"] for item in proof["results"]}
    assert observed == {("old", "default"): 1, ("old", "compat"): 0,
                        ("modern", "default"): 0, ("modern", "compat"): 0}
    assert proof["matching_diagnostic_pdb"] and proof["mutex_import_matches_selected_runtime"]
    assert not proof["qt_imported"] and not proof["graphics_created"]
    assert not proof["full_vendor_compatibility_rebuild_completed"]
    directory = ROOT / "build/evidence/crt-mutex-compatibility-1"
    for name in ("old-default", "old-compat", "modern-default", "modern-compat"):
        record = load(directory / f"{name}.json")
        assert record["resolved_mutex_import_matches_selected_runtime"]
        if name == "old-default":
            assert record["phase"] == "before_mutex_lock" and "result" not in record
            assert "access violation reading 0x0000000000000000" in (directory / f"{name}.log").read_text()
        else:
            assert record["phase"] == "mutex_lock_passed" and record["result"] == 73
    default = load(directory / "default-compile-arguments.json")
    compatible = load(directory / "compat-compile-arguments.json")
    assert '/MD' in default and '/MD' in compatible
    assert '/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR' not in default
    assert '/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR' in compatible
    stack = (directory / "debugger/native-stack.log").read_text()
    assert "vispy_mutex_probe" in stack and "crt_mutex_probe.cpp:6" in stack


def test_scoped_dive_failure_keeps_both_nonzero_children_unadmitted():
    proof = load(ROOT / "compat/host-environments/dive-pyside2-candidate-w5-scoped-failure.json")
    verify_evidence(proof)
    assert proof["fixtures_admitted"] == 0 and not proof["graphics_qualified"]
    assert proof["child_exit_codes"] == {"image": 3221225477, "image_edit": 3221225477}
    assert proof["source_native_artifacts_unchanged"]
    assert "ordinary unchanged host teardown and scatter admission remain unresolved" in proof["scope"]
    callsite = load(ROOT / "build/evidence/dive-pyside2-style-candidate-w5-debug-1/import-callsite.json")
    assert callsite["called_import"] == "MSVCP140.dll:_Mtx_lock"
    assert callsite["module_sha256"] == (
        "e28144be709defdd1de05f7afd8e3536cf785ef083805121908186e6ff8e1040"
    )
