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


actor = source_module("activation33_pure_guard", ROOT / "build/activate_native_pass_33_2.py")
preparer = source_module("prepare33_pure_guard", ROOT / "build/prepare_native_pass_33_activation_2.py")


@pytest.fixture
def schema():
    # Actual32 metadata is only an IN-MEMORY schema seed. Synthetic additions
    # exercise inventory derivation; they are never written as a future proof.
    archive = ROOT / "build/evidence/native-pass-32"
    ownership = actor.load(ROOT / "compat/native-epochs/pass32-w18-ownership.json")
    frozen, status, binaries = [actor.load(archive / n) for n in ("frozen-inputs.json", "status.json", "binary-hashes.json")]
    handoff = actor.load(ROOT / "build/evidence/native-pass-32-build-handoff-1/result.json")
    for value in (ownership, frozen, status, handoff):
        value["epoch"] = 33
    ownership["snapshot_epoch"] = 19
    added = ("line_pool_inspection_contract", "line_ownership_contract")
    ownership["targets"].extend(added)
    ownership["ctest_expected_names"].extend(added)
    new_keys = ("cpp/runtime_line_ownership.hpp", "tests/lines/line_pool_inspection_contract.cpp",
                "tests/lines/line_ownership_contract.cpp")
    synthetic = {name: "0" * 64 for name in new_keys}
    ownership["packets"].append({"name": "synthetic-schema-only", "files": synthetic,
                                 "owned_files": {name: name for name in new_keys}})
    for name, checksum in synthetic.items():
        if name.startswith("cpp/"):
            ownership["source_files"][name] = checksum
        ownership["harness_inputs"][name] = {"path": name, "sha256": checksum}
    binaries.update({name + ".exe": "0" * 64 for name in added})
    counts, owners, _ = actor.manifest_inventory(ownership)
    frozen["source_files"] = dict(ownership["source_files"])
    frozen["harness_files"] = {name: row["sha256"] for name, row in ownership["harness_inputs"].items()}
    frozen["owned_files"] = owners
    ownership["protected_native"] = dict(actor.PARENT_NATIVE)
    frozen["protected_native_before"] = frozen["protected_native_after"] = dict(actor.PARENT_NATIVE)
    handoff["protected_before"] = handoff["protected_after"] = dict(actor.PARENT_NATIVE)
    handoff["active_pass32_unchanged"] = True
    for key, value in (("source_files_verified", counts["source_files"]), ("harness_files_verified", counts["harness_files"]),
            ("owned_source_files_verified", counts["owned_files"]), ("source_owner_count", counts["CPP_owners"]),
            ("harness_owner_count", counts["contract_owners"]), ("build_target_count", counts["build_targets"]),
            ("ctest_executed_count", counts["ctest_names"])):
        handoff[key] = value
    handoff["ctest_expected_names"] = list(ownership["ctest_expected_names"])
    handoff["all_archived_binary_hashes"] = dict(binaries)
    handoff["whole_cpu_packet_file_counts"] = {p["name"]: len(p["files"]) for p in ownership["packets"]}
    approval = {"ownership_manifest_sha256": handoff["manifest_sha256"], "proof_input_hashes": handoff["proof_input_hashes"],
                "native_binary_hashes": handoff["native_binary_hashes"], "source_tree_sha256": ownership["source_tree_sha256"],
                "harness_tree_sha256": ownership["harness_tree_sha256"]}
    return handoff, approval, ownership, frozen, status, binaries


def test_pure_in_memory_handoff_schema(schema):
    actor.validate_build_handoff(*schema)


@pytest.mark.parametrize("field,value", [
    ("status", "live"), ("process_exit", 1), ("process_exit", False), ("epoch", 32), ("epoch", True),
    ("manifest_sha256", "0" * 64), ("proof_input_hashes", {}), ("source_files_verified", 588),
    ("source_files_verified", True), ("harness_files_verified", 1027), ("owned_source_files_verified", 28),
    ("owned_source_files_verified", True), ("source_owner_count", 19), ("harness_owner_count", 9),
    ("source_tree_sha256", "0" * 64), ("harness_tree_sha256", "0" * 64), ("ctest_executed_count", 11),
    ("ctest_executed_count", True), ("build_target_count", 16), ("whole_cpu_packet_file_counts", {}), ("ctest_expected_names", ["wrong"] * 20), ("all_archived_binary_hashes", {}),
    ("native_binary_hashes", {}), ("protected_before", {}), ("protected_after", {}),
    ("active_pass32_unchanged", False), ("sdk_manifest_sha256", "0" * 64), ("in_place_copy", True),
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


def test_source_and_owner_counts_are_derived(schema):
    handoff, approval, ownership, frozen, status, binaries = schema
    name = "cpp/synthetic_additional_owner.hpp"
    ownership["source_files"][name] = frozen["source_files"][name] = "0" * 64
    ownership["harness_inputs"][name] = {"path": name, "sha256": "0" * 64}
    frozen["harness_files"][name] = "0" * 64
    ownership["packets"][-1]["files"][name] = "0" * 64
    ownership["packets"][-1]["owned_files"][name] = name
    frozen["owned_files"][name] = "0" * 64
    counts, _, _ = actor.manifest_inventory(ownership)
    handoff.update(source_files_verified=counts["source_files"], harness_files_verified=counts["harness_files"],
                   owned_source_files_verified=counts["owned_files"], source_owner_count=counts["CPP_owners"],
                   whole_cpu_packet_file_counts={p["name"]: len(p["files"]) for p in ownership["packets"]})
    actor.validate_build_handoff(*schema)


@pytest.mark.parametrize("scenario", ["overlap", "duplicate_target", "duplicate_test", "missing_inventory"])
def test_manifest_inventory_refuses_incomplete_or_overlapping_schema(schema, scenario):
    ownership = schema[2]
    if scenario == "overlap":
        packet = ownership["packets"][-1]
        name = next(iter(ownership["packets"][0]["owned_files"]))
        packet["files"][name] = "0" * 64
        packet["owned_files"][name] = name
    elif scenario == "duplicate_target":
        ownership["targets"].append(ownership["targets"][0])
    elif scenario == "duplicate_test":
        ownership["ctest_expected_names"].append(ownership["ctest_expected_names"][0])
    else:
        ownership["source_files"] = {}
    with pytest.raises(actor.ActivationError):
        actor.manifest_inventory(ownership)


@pytest.fixture
def xml(tmp_path):
    # Parser control only, not a claim that future33 executed these CTests.
    path = tmp_path / "ctest.xml"
    suite = ET.Element("testsuite", tests=str(len(actor.EXPECTED_CTEST)), failures="0", errors="0", skipped="0", disabled="0")
    for name in sorted(actor.EXPECTED_CTEST):
        ET.SubElement(suite, "testcase", classname=name, name=name, status="run", result="completed")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
    return path


def test_full_derived_xml_is_only_a_schema_control(xml):
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


def test_actual_unprepared33_entrypoint_refuses_without_writes():
    with pytest.raises((FileNotFoundError, actor.ActivationError)):
        actor.preflight("0" * 64)
    assert not actor.APPROVAL.exists()
    assert not any((actor.ARCHIVE / name).exists() for name in
                   ("activation.json", "activation-before", "activation-staging", "activation-inputs"))



@pytest.fixture
def process_observations():
    # Real retained metadata only; this pure function does not run preflight,
    # producers, tools, imports of native modules, or the native transaction.
    process = actor.load(actor.BUILD_PROCESS / "result.json")
    handoff = actor.load(actor.HANDOFF)
    command = actor.load(actor.BUILD_PROCESS / "command.json")
    checksum = actor.sha(actor.BUILD_PROCESS / "supervisor.py")
    return process, handoff, command, checksum


def test_actual_nonzero_internal_observations_are_retained(process_observations):
    process, handoff, command, checksum = process_observations
    original = copy.deepcopy((process, handoff, command))
    result = actor.validate_process_observations(process, handoff, command, checksum)
    expected = [row for row in process["observed_descendants"]
                if row["terminal_observed"] and row["process_exit"] != 0]
    assert len(expected) == 6
    assert result["sampled_nonzero_terminal_records"] == expected
    assert all(row["pid"] != process["launched_pid"] for row in expected)
    assert result["authoritative_producer_exit"] == result["authoritative_child_exit"] == 0
    assert (process, handoff, command) == original


@pytest.mark.parametrize("field,bad", [
    ("process_exit", 1), ("process_exit", False), ("process_exit", None),
    ("child_exit", 1), ("child_exit", False), ("child_exit", None),
])
def test_authoritative_producer_or_child_failure_refused(process_observations, field, bad):
    process, handoff, command, checksum = process_observations
    changed = copy.deepcopy(process)
    changed[field] = bad
    with pytest.raises(actor.ActivationError, match="authoritative"):
        actor.validate_process_observations(changed, handoff, command, checksum)


@pytest.mark.parametrize("row", [
    {"pid": 123, "terminal_observed": True, "process_exit": False},
    {"pid": 123, "terminal_observed": True, "process_exit": None},
    {"pid": 123, "terminal_observed": True, "process_exit": "0"},
    {"pid": 123, "terminal_observed": "true", "process_exit": 0},
    {"pid": 123, "process_exit": 0},
])
def test_malformed_sampled_terminal_refused(process_observations, row):
    process, handoff, command, checksum = process_observations
    changed, joined = copy.deepcopy(process), copy.deepcopy(handoff)
    changed["observed_descendants"].append(row)
    joined["observed_process_records"] = copy.deepcopy(changed["observed_descendants"])
    with pytest.raises(actor.ActivationError, match="Sampled|sampled"):
        actor.validate_process_observations(changed, joined, command, checksum)


def test_observed_root_launcher_failure_refused(process_observations):
    process, handoff, command, checksum = process_observations
    changed, joined = copy.deepcopy(process), copy.deepcopy(handoff)
    row = next(value for value in changed["observed_descendants"] if value["pid"] == changed["launched_pid"])
    row["process_exit"] = 1
    joined["observed_process_records"] = copy.deepcopy(changed["observed_descendants"])
    with pytest.raises(actor.ActivationError, match="root build launcher"):
        actor.validate_process_observations(changed, joined, command, checksum)
