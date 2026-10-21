"""Pure schema/publication controls; only temporary files receive copies."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


class BlockGraphics:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"vispy", "PyQt5", "PyQt6", "PySide2", "PySide6", "OpenGL", "napari"}:
            raise AssertionError("Graphics/native import forbidden in pure activation guards: " + fullname)


sys.meta_path.insert(0, BlockGraphics())


def source_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


actor = source_module("activation32_pure_guard", ROOT / "build/activate_native_pass_32.py")
preparer = source_module("prepare32_pure_guard", ROOT / "build/prepare_native_pass_32_activation.py")


@pytest.fixture
def schema():
    # Retained actual31 metadata is an IN-MEMORY schema seed, never a future32
    # snapshot/ACK/build/approval and never written to canonical paths.
    archive = ROOT / "build/evidence/native-pass-31"
    ownership = actor.load(ROOT / "compat/native-epochs/pass31-w17-ownership.json")
    frozen, status, binaries = [actor.load(archive / n) for n in ("frozen-inputs.json", "status.json", "binary-hashes.json")]
    handoff = actor.load(ROOT / "build/evidence/native-pass-31-build-handoff-1/result.json")
    for value in (ownership, frozen, status, handoff):
        value["epoch"] = 32
    handoff["active_pass31_unchanged"] = True
    for value in (ownership,):
        value["protected_native"] = dict(actor.PARENT_NATIVE)
    for value in (frozen,):
        value["protected_native_before"] = value["protected_native_after"] = dict(actor.PARENT_NATIVE)
    handoff["protected_before"] = handoff["protected_after"] = dict(actor.PARENT_NATIVE)
    approval = {"ownership_manifest_sha256": handoff["manifest_sha256"], "proof_input_hashes": handoff["proof_input_hashes"],
                "native_binary_hashes": handoff["native_binary_hashes"], "source_tree_sha256": ownership["source_tree_sha256"],
                "harness_tree_sha256": ownership["harness_tree_sha256"]}
    return handoff, approval, ownership, frozen, status, binaries


def test_pure_in_memory_handoff_schema(schema):
    actor.validate_build_handoff(*schema)


@pytest.mark.parametrize("field,value", [
    ("status", "live"), ("process_exit", 1), ("process_exit", False), ("epoch", 31), ("epoch", True),
    ("manifest_sha256", "0" * 64), ("proof_input_hashes", {}), ("source_files_verified", 588),
    ("source_files_verified", True), ("harness_files_verified", 1027), ("owned_source_files_verified", 27),
    ("owned_source_files_verified", True), ("source_owner_count", 18), ("harness_owner_count", 8),
    ("source_tree_sha256", "0" * 64), ("harness_tree_sha256", "0" * 64), ("ctest_executed_count", 11),
    ("ctest_executed_count", True), ("ctest_expected_names", ["wrong"] * 18), ("all_archived_binary_hashes", {}),
    ("native_binary_hashes", {}), ("protected_before", {}), ("protected_after", {}),
    ("active_pass31_unchanged", False), ("sdk_manifest_sha256", "0" * 64), ("in_place_copy", True),
    ("gpu_qualified", True), ("sdk_private_tint_reader_enabled", True), ("native_imported", True), ("GPU_used", True),
])
def test_handoff_refuses_mismatched_or_incomplete_schema(schema, field, value):
    handoff, approval, ownership, frozen, status, binaries = schema
    handoff[field] = value
    with pytest.raises((actor.ActivationError, KeyError)):
        actor.validate_build_handoff(handoff, approval, ownership, frozen, status, binaries)


def test_harness_count_is_derived_not_historical(schema):
    handoff, approval, ownership, frozen, status, binaries = schema
    ownership["harness_inputs"]["synthetic/extra"] = {"path": "synthetic", "sha256": "0" * 64}
    frozen["harness_files"]["synthetic/extra"] = "0" * 64
    handoff["harness_files_verified"] = len(ownership["harness_inputs"])
    actor.validate_build_handoff(handoff, approval, ownership, frozen, status, binaries)


@pytest.fixture
def xml(tmp_path):
    path = tmp_path / "ctest.xml"
    path.write_bytes((ROOT / "build/evidence/native-pass-31/ctest.xml").read_bytes())
    return path


def test_actual_parent18_xml_only_is_schema_control(xml):
    actor.validate_ctest(xml, sorted(actor.EXPECTED_CTEST))


@pytest.mark.parametrize("scenario", ["suite_skip", "suite_disabled", "suite_error", "suite_failure", "case_skip", "case_error",
    "case_fail", "case_disabled", "duplicate_name", "foreign_class", "missing_case", "notrun", "wrong_result",
    "attr_skip", "attr_error", "attr_fail", "attr_disabled", "nested_suite", "nested_plural_suites", "nested_case", "nested_error", "nested_skip"])
def test_xml_refuses_incomplete_execution(xml, scenario):
    suite = ET.parse(xml).getroot()
    case = suite.findall("testcase")[0]
    if scenario.startswith("suite_"):
        suite.set({"skip": "skipped", "error": "errors", "failure": "failures", "disabled": "disabled"}[scenario[6:]], "1")
    elif scenario in ("case_skip", "case_error", "case_fail", "case_disabled"):
        ET.SubElement(case, {"case_skip": "skipped", "case_error": "error", "case_fail": "failure", "case_disabled": "disabled"}[scenario])
    elif scenario == "duplicate_name": case.set("name", suite.findall("testcase")[1].attrib["name"])
    elif scenario == "foreign_class": case.set("classname", "foreign")
    elif scenario == "missing_case": suite.remove(case)
    elif scenario == "notrun": case.set("status", "notrun")
    elif scenario == "wrong_result": case.set("result", "failed")
    elif scenario.startswith("attr_"):
        case.set({"skip": "skipped", "error": "errors", "fail": "failures", "disabled": "disabled"}[scenario[5:]], "1")
    elif scenario == "nested_suite": ET.SubElement(suite, "testsuite", tests="0")
    elif scenario == "nested_plural_suites": ET.SubElement(case, "testsuites")
    elif scenario == "nested_case": ET.SubElement(case, "testcase", name="extra", status="run")
    elif scenario in ("nested_error", "nested_skip"):
        ET.SubElement(ET.SubElement(case, "details"), "error" if scenario == "nested_error" else "skipped")
    ET.ElementTree(suite).write(xml)
    with pytest.raises(actor.ActivationError):
        actor.validate_ctest(xml, sorted(actor.EXPECTED_CTEST))


@pytest.mark.parametrize("bad", [None, True, "F" * 64, "0" * 63, "0" * 65, "g" * 64])
def test_digest_refuses_unobserved_untyped_value(bad):
    with pytest.raises(actor.ActivationError): actor.digest(bad)


def test_actual_transaction_functions_are_reused_verbatim():
    for name in ("activate_transaction", "commit_record", "archive_inputs", "safe_member"):
        assert getattr(actor, name) is getattr(actor.baseline, name)
    assert actor.sha(actor.TRANSACTION_SOURCE) == actor.TRANSACTION_SHA


def test_prepare_checks_helper_digest_before_import():
    with pytest.raises(ValueError): preparer.load_activation("0" * 64)


@pytest.mark.parametrize("scenario", ["preflight_early", "preflight_late", "serialization", "existing_record", "existing_pending",
                                          "record_appears_during_preflight", "fsync", "atomic_link"])
def test_approval_publication_refuses_before_or_during_commit(tmp_path, scenario):
    approval = tmp_path / "activation-approval.json"
    pending = approval.with_name(approval.name + ".pending")
    record = {"reviewed": "temporary schema protocol"}
    seen = []
    def preflight(value):
        assert not approval.exists() and not pending.exists()
        seen.append("complete preflight entered")
        if scenario in ("preflight_early", "preflight_late"):
            if scenario == "preflight_late":
                (tmp_path / "all-inputs-checked").write_bytes(b"temporary control")
            raise actor.ActivationError("injected last preflight check fails")
        if scenario == "record_appears_during_preflight": approval.write_bytes(b"foreign historical record")
        seen.append("complete preflight returned")
    if scenario == "serialization": record["unsupported"] = object()
    if scenario == "existing_record": approval.write_bytes(b"historical record")
    if scenario == "existing_pending": pending.write_bytes(b"historical pending")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    with patch.object(actor, "APPROVAL", approval), patch.object(actor, "preflight_record", preflight):
        with patch.object(actor.baseline.os, "fsync", side_effect=OSError("injected durable flush failure")) if scenario == "fsync" else patch.object(actor, "SDK_SHA", actor.SDK_SHA), \
             patch.object(actor.baseline.os, "link", side_effect=OSError("injected atomic link failure")) if scenario == "atomic_link" else patch.object(actor, "SDK_SHA", actor.SDK_SHA):
            with pytest.raises((actor.ActivationError, OSError, TypeError)):
                preparer.publish_approval(actor, record)
    if scenario in ("existing_record", "existing_pending"):
        assert {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()} == before
        assert not seen
    elif scenario == "record_appears_during_preflight":
        assert approval.read_bytes() == b"foreign historical record" and not pending.exists()
    else:
        assert not approval.exists() and not pending.exists()


def test_complete_preflight_and_utf8_publication_precede_return(tmp_path):
    approval = tmp_path / "activation-approval.json"
    seen = []
    record = {"scope": "temporary µ schema"}
    def checked(value):
        assert not approval.exists()
        assert value == record
        seen.append("complete")
    with patch.object(actor, "APPROVAL", approval), patch.object(actor, "preflight_record", checked):
        checksum = preparer.publish_approval(actor, record)
    assert seen == ["complete"] and approval.read_bytes() == actor.encode_json(record)
    assert checksum == hashlib.sha256(approval.read_bytes()).hexdigest()


@pytest.mark.parametrize("bad_name", ["../outside", "C:/outside", "src/vispy/_dawn.cp312-win_amd64.pyd"])
def test_qualification_context_rejects_escaping_or_changing_native(tmp_path, bad_name):
    path = tmp_path / "context.json"
    path.write_text(json.dumps({"schema": 1, "scope": "temporary", "input_hashes": {bad_name: "0" * 64}}))
    with patch.object(actor, "ROOT", tmp_path):
        with pytest.raises(actor.ActivationError): actor.qualification_inputs(path, actor.sha(path))


def test_explicit_qualification_context_bytes_and_scope(tmp_path):
    (tmp_path / "source.py").write_bytes(b"held temporary provenance")
    path = tmp_path / "context.json"
    context = {"schema": 1, "scope": "temporary source/proof context only", "input_hashes": {"source.py": actor.sha(tmp_path / "source.py")}}
    path.write_bytes(actor.encode_json(context))
    with patch.object(actor, "ROOT", tmp_path):
        assert actor.qualification_inputs(path, actor.sha(path)) == context
        (tmp_path / "source.py").write_bytes(b"changed")
        with pytest.raises(actor.ActivationError): actor.qualification_inputs(path, actor.sha(path))


def test_native_and_approval_entrypoints_require_explicit_pins():
    with pytest.raises(SystemExit): actor.main([])
    with pytest.raises(SystemExit): preparer.main([])
    assert not actor.APPROVAL.exists()
    assert not (actor.ARCHIVE / "activation.json").exists()


def test_actual_unprepared32_entrypoint_refuses_without_writes():
    with pytest.raises((FileNotFoundError, actor.ActivationError)):
        actor.preflight("0" * 64)
    assert not actor.APPROVAL.exists()
    assert not any((actor.ARCHIVE / name).exists() for name in
                   ("activation.json", "activation-before", "activation-staging", "activation-inputs"))
