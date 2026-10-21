"""Guarded future-native qualification of the held basic11/lifetime7 packet.

Authoring/freezing imports no renderer. Only an explicitly requested --run
starts a single pytest child, after canonical future activation checks. The
original private-ABI tests, shaders, expected arrays and failure predicates
remain unchanged. This runner does not implement or mock an endpoint API.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "tools/fixture_line_endpoints_dawn.py": "4aa01baa6b0e705fc6b7d7a864a5bebc668fc6ee2e9639222f134ee82e310eb3",
    "tests/native/test_line_endpoints_dawn.py": "eaef1bc8a5955ac05a6a2e6df10d00195697b91f92968aa15cfcd82191d04593",
    "tests/native/test_line_endpoint_lifetime_dawn.py": "96286ed13adadfc74d7b2bcaaebf8e3dc814cb20cae7e09cbc12651fcefc6316",
}
AUTHORS = {
    "build/evidence/line-endpoints-dawn-authoring-1/authoring.json": "9f2727d2407374f8aba12f78723ad71db99ff565d2661f2b5799a5619e260884",
    "build/evidence/line-endpoint-lifetime-dawn-authoring-3/authoring.json": "8e5ffa797587d7d5d59f19e6d83eb07cf6d6404cfd9b40fd2ce4e90f1bc060ea",
}
AUTHOR_PROOFS = {
    "build/evidence/line-endpoints-dawn-authoring-1/terminal.json": "43dcdf70d52e223549c45eca1b74ff1215ce76f189d53da302be98fe72a6fcf0",
    "build/evidence/line-endpoints-dawn-authoring-1/seal.json": "1463ca82d2913c8b79d8fd779d990ff255501a008e42dca5942834dbaeb08121",
    "build/evidence/line-endpoint-lifetime-dawn-authoring-3/terminal.json": "dd416023a173ff27aa7919a12155b5f9503867a50e411b86ecc59eb7b2ad334a",
    "build/evidence/line-endpoint-lifetime-dawn-authoring-3/seal.json": "b5c934e68f26065e30d802ef92367ef428707a128f59e8e5bf110c855aac7321",
}
BASIC_CASES = ("raw_high_ids", "indexed_u8", "indexed_u16", "indexed_u32",
               "interleaved_divisors", "globals_early_return", "matrices_arrays", "logical_count65")
BASIC_FILE = "tests/native/test_line_endpoints_dawn.py"
LIFETIME_FILE = "tests/native/test_line_endpoint_lifetime_dawn.py"
BASIC_IDS = tuple(BASIC_FILE + "::test_native_admitted_original_outputs_padding_queryoff_and_owned_storage[" + name + "]" for name in BASIC_CASES) + tuple(BASIC_FILE + "::" + name for name in (
    "test_native_diagnostic_disabled_does_not_create_endpoint_work_or_records",
    "test_native_pending_abort_returns_failure_and_recovers_diagnostic_capacity",
    "test_native_retired_uncollected_shutdown_never_maps_stale_device_storage"))
LIFETIME_IDS = tuple(LIFETIME_FILE + "::" + name for name in (
    "test_native_capture_off_resident_dispatch_and_paired_render_reuse_no_hidden_costs",
    "test_native_query_on_maps_actual_endpoint_compute_scene_and_capture_pass_pairs",
    "test_native_pending_matrix_uniform_DATA_revisions_preserve_A_B_A_original_outputs",
    "test_native_cancelled_submitted_endpoint_stays_failed_until_real_Ticket_retirement",
    "test_native_cancelled_queued_endpoint_has_real_backpressure_and_no_second_dispatch",
    "test_native_actual_device_loss_rejects_submitted_capture_and_recovers_CPU_inputs_once",
    "test_native_warmed_uniform_only_change_has_isolated_positive_upload_and_exact_outputs"))
GPU_IDS = BASIC_IDS + LIFETIME_IDS
FOLDERS = set(BASIC_CASES) | {"diagnostic-disabled", "pending-abort-capacity", "retired-uncollected-shutdown",
    "capture-off-resident", "query-on-compute", "pending-matrix-revisions", "submitted-cancellation",
    "queued-cancellation", "device-loss-recovery", "isolated-changed-UBO"}
def require(ok, label):
    if not ok:
        raise ValueError(label)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None, "Explicit lowercase SHA256 required")
    return value


def integer(value, label, minimum=0):
    require(type(value) is int and value >= minimum, label)
    return value


def member(directory, name):
    require(isinstance(name, str) and bool(name), "Nonempty relative member required")
    p, w = PurePosixPath(name), PureWindowsPath(name)
    require(not p.is_absolute() and not w.drive and not w.is_absolute() and ".." not in p.parts
            and ".." not in w.parts and "\\" not in name and str(p) == name, "Unsafe protected member")
    result = (Path(directory) / name).resolve()
    require(result.is_relative_to(Path(directory).resolve()), "Protected member escapes directory")
    return result


def tree_digest(files):
    h = hashlib.sha256()
    for name, value in sorted(files.items()):
        member(ROOT, name)
        h.update(name.encode("utf-8") + b"\0" + bytes.fromhex(digest(value)))
    return h.hexdigest()


def xml_identity(node_id):
    path, name = node_id.split("::")
    return (path[:-3].replace("/", "."), name)


def validate_xml(path, expected):
    """Require actual unique direct case identities, not declared counts alone."""
    root = ET.parse(path).getroot()
    expected = tuple(expected)
    require(root.tag in ("testsuites", "testsuite") and len(set(expected)) == len(expected), "XML root/expected identities invalid")
    suites = [root] if root.tag == "testsuite" else list(root)
    require(bool(suites), "Empty XML suite list")
    for key in ("errors", "failures", "skipped", "disabled"):
        require(int(root.get(key, "0")) == 0, "XML root failure/skip/disabled")
    if root.tag == "testsuites" and "tests" in root.attrib:
        require(int(root.attrib["tests"]) == len(expected), "XML root count differs")
    require(not any(root.find(".//" + tag) is not None for tag in ("failure", "error", "skipped", "disabled")), "XML contains failure/skip/disabled")
    cases = []
    for suite in suites:
        require(suite.tag == "testsuite" and not suite.findall(".//testsuite") and not suite.findall(".//testsuites"), "XML nested/invalid suite")
        rows = suite.findall("testcase")
        require(len(rows) == len(suite.findall(".//testcase")) == int(suite.attrib["tests"]), "XML nested/wrapped/count mismatch")
        require(all(int(suite.get(k, "0")) == 0 for k in ("errors", "failures", "skipped", "disabled")), "XML suite not completely passed")
        for row in rows:
            require(row.get("status", "run") == "run" and row.get("result", "completed") in ("completed", "passed"), "XML case incomplete")
            require(all(row.get(k, "0").lower() in ("0", "false") for k in ("skipped", "disabled")), "XML case skipped/disabled")
            require(all(int(row.get(k, "0")) == 0 for k in ("failures", "errors")), "XML case failure/error flag")
            require(not any(row.find(".//" + t) is not None for t in ("testcase", "testsuite", "testsuites", "failure", "error", "skipped", "disabled")), "XML nested case/failure")
            require(bool(row.get("classname")) and bool(row.get("name")), "XML identity absent")
            cases.append((row.get("classname"), row.get("name")))
    require(len(cases) == len(expected) == len(set(cases)) and set(cases) == set(expected), "Exact XML identities differ")
    require(len(root.findall(".//testcase")) == len(cases), "XML extra descendant case")
    return {"executed": len(cases), "identities": [list(v) for v in cases], "failures": 0, "errors": 0, "skipped": 0, "disabled": 0}


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def rehash(hashes):
    actual = {name: sha(member(ROOT, name)) for name in hashes}
    require(actual == hashes, "Protected input identities changed")
    return actual


def archive(destination, hashes):
    require(not destination.exists(), "Fresh archive required")
    rows = {}
    for name, value in sorted(hashes.items()):
        source = member(ROOT, name)
        require(sha(source) == digest(value), "Archive source identity differs")
        blob = "blobs/" + value + ".bin"
        require(len(str((destination / blob).resolve())) < 248, "Flat archive Windows path too long")
        rows[name] = {"sha256": value, "blob": blob, "bytes": source.stat().st_size}
    (destination / "blobs").mkdir(parents=True, exist_ok=False)
    for name, row in rows.items():
        target = destination / row["blob"]
        if not target.exists():
            with member(ROOT, name).open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
        require(sha(target) == row["sha256"] and target.stat().st_size == row["bytes"], "Archived blob differs")
    write_new(destination / "index.json", {"schema": 1, "files": rows})
    return validate_archive(destination, hashes)


def validate_archive(destination, hashes):
    index = read(destination / "index.json")
    require(index["schema"] == 1 and set(index["files"]) == set(hashes), "Archive logical map differs")
    blobs = set()
    for name, value in hashes.items():
        row = index["files"][name]
        require(row["sha256"] == value and row["blob"] == "blobs/" + value + ".bin", "Archive mapping differs")
        path = member(destination, row["blob"])
        require(sha(path) == value and path.stat().st_size == row["bytes"], "Archive bytes differ")
        blobs.add(path.name)
    require({p.name for p in (destination / "blobs").iterdir()} == blobs, "Archive blob inventory differs")
    return {"index_sha256": sha(destination / "index.json"), "logical_files": len(hashes), "unique_blobs": len(blobs)}


def validate_context(epoch, activation, handoff, manifest, frozen, status, manifest_sha, handoff_sha):
    integer(epoch, "Future integer epoch required", 31)
    for value in (activation, manifest, frozen, status):
        require(type(value.get("epoch")) is int and value["epoch"] == epoch, "Context epoch differs")
    require(handoff["status"] == "passed_read_only_terminal_build_handoff" and type(handoff["process_exit"]) is int and handoff["process_exit"] == 0, "Actual terminal handoff required")
    require(handoff["in_place_copy"] is False and handoff["gpu_qualified"] is False and handoff["sdk_private_tint_reader_enabled"] is False, "Handoff CPU build scope differs")
    require(status["status"] == "build_and_ctest_passed" and status["in_place_copy"] is False and status["gpu_qualified"] is False and status["sdk_tint_reader_enabled"] is False and manifest["sdk_tint_reader_enabled"] is False, "Build scope differs")
    source = digest(manifest["source_tree_sha256"])
    harness = digest(manifest["harness_tree_sha256"])
    require(all(v == source for v in (activation["native_source_tree_sha256"], handoff["source_tree_sha256"], frozen["source_tree_sha256"], status["source_tree_sha256"])), "Source tree identity differs")
    require(handoff["harness_tree_sha256"] == frozen["harness_tree_sha256"] == harness, "Harness identity differs")
    require(activation["ownership_manifest_sha256"] == handoff["manifest_sha256"] == frozen["ownership_manifest_sha256"] == manifest_sha, "Ownership manifest identity differs")
    require(activation["build_handoff_sha256"] == handoff_sha, "Activation handoff binding differs")
    require(activation["sdk_manifest_sha256"] == handoff["sdk_manifest_sha256"] == manifest["sdk_manifest_sha256"] == status["sdk_manifest_sha256"], "SDK identity differs")
    require(activation["proof_input_hashes"] == handoff["proof_input_hashes"] and set(activation["proof_input_hashes"]) == {"frozen-inputs.json", "status.json", "binary-hashes.json", "ctest.xml"}, "Proof pins differ")
    native = activation["activated"]
    require(native == handoff["native_binary_hashes"] and len(native) == 4, "Native four identity differs")
    require(sum(n.startswith("_dawn.") and n.endswith(".pyd") for n in native) == 1 and sum(n.startswith("_sdf_cpu.") and n.endswith(".pyd") for n in native) == 1
            and {"VkLayer_vispy_submit.dll", "VkLayer_vispy_submit.json"} <= set(native), "Native four names differ")
    for name, value in native.items():
        member(ROOT, name)
        require("/" not in name, "Native leaf name required")
        digest(value)
    names = manifest["ctest_expected_names"]
    require(names and len(names) == len(set(names)) and set(names) == set(handoff["ctest_expected_names"]), "Exact named CTests required")
    require(type(handoff["ctest_executed_count"]) is int and handoff["ctest_executed_count"] == len(names), "CTest count differs")
    require(frozen["source_files"] == manifest["source_files"] and len(frozen["source_files"]) == handoff["source_files_verified"], "Source inventory differs")
    require(frozen["harness_files"] == {k: v["sha256"] for k, v in manifest["harness_inputs"].items()} and len(frozen["harness_files"]) == handoff["harness_files_verified"], "Harness inventory differs")
    require(tree_digest(frozen["source_files"]) == source and tree_digest(frozen["harness_files"]) == harness, "Computed inventory digest differs")
    snapshot = integer(manifest["snapshot_epoch"], "Snapshot epoch required", 1)
    require(manifest["paths"]["snapshot"] == f"build/w{snapshot}/source" and manifest["paths"]["harness"] == f"build/evidence/native-pass-{epoch}/harness"
            and manifest["paths"]["evidence"] == f"build/evidence/native-pass-{epoch}", "Canonical frozen paths differ")


def validate_context_proof(proof):
    if "process_exit" in proof:
        require(type(proof["process_exit"]) is int and proof["process_exit"] == 0, "Context proof process did not succeed")
    else:
        require(proof.get("status") == "CLEAR_WITH_SCOPE" and proof.get("material_findings") == [], "Successful reviewed context required")
    require(not proof.get("material_findings"), "Context proof has material findings")


def held_inputs():
    """Read-only verification of the two sealed authoring contexts and arrays."""
    hashes = {**SOURCES, **AUTHOR_PROOFS}
    cpu, gpu = [], []
    for name, pin in AUTHORS.items():
        path = member(ROOT, name)
        require(sha(path) == pin, "Held authoring differs")
        hashes[name] = pin
        author = read(path)
        require(author["candidate_seen"] is False and author["GPU_used"] is False and author["native_imported"] is False, "Authoring was not candidate-unseen CPU only")
        expected_sources = {k: SOURCES[k] for k in author["sources_sha256"]}
        require(author["sources_sha256"] == expected_sources, "Authoring source pins differ")
        cpu += author["CPU_case_ids"]
        gpu += author["GPU_case_ids_unrun"]
        for key, value in author["proof_inputs_sha256"].items():
            require(key not in hashes or hashes[key] == value, "Conflicting authoring proof pin")
            hashes[key] = value
        for group in ("expected_arrays", "input_arrays"):
            for key, row in author.get(group, {}).items():
                hashes[(path.parent / key).relative_to(ROOT).as_posix()] = row["file_sha256"]
        for sibling in ("terminal.json", "seal.json"):
            sibling_path = path.parent / sibling
            key = sibling_path.relative_to(ROOT).as_posix()
            require(sibling_path.is_file() and sha(sibling_path) == AUTHOR_PROOFS[key], "Held authoring terminal/seal differs")
        terminal = read(path.parent / "terminal.json")
        require(type(terminal["process_exit"]) is int and terminal["process_exit"] == 0 and terminal["GPU_used"] is False and terminal["native_imported"] is False
                and terminal["authoring_sha256"] == pin, "Authoring terminal scope/binding differs")
        seal = read(path.parent / "seal.json")
        require(seal["artifact_hashes"]["authoring.json"] == pin, "Authoring seal binding differs")
        for key, value in seal["artifact_hashes"].items():
            hashes[(path.parent / key).relative_to(ROOT).as_posix()] = value
    require(len(cpu) == len(set(cpu)) == 74 and len(gpu) == len(set(gpu)) == 18 and set(gpu) == set(GPU_IDS), "Held exact CPU/GPU identities differ")
    original_path = ROOT / "build/evidence/line-endpoints-authoring-3/authoring.json"
    original = read(original_path)
    for key, row in original["expected_and_input_arrays"].items():
        hashes[(original_path.parent / key).relative_to(ROOT).as_posix()] = row["file_sha256"]
    for key, value in original["original_shader_files"].items():
        hashes[(original_path.parent / key).relative_to(ROOT).as_posix()] = value
    reference = ROOT / "tests/reference/line-endpoints-opengl-2"
    terminal = read(reference / "terminal.json")
    require(terminal["process_exit"] == 0 and terminal["admitted"] == 8 and terminal["unresolved"] == 0, "Independent D1 admission differs")
    for name, value in terminal["artifacts"].items():
        hashes[(reference / name).relative_to(ROOT).as_posix()] = value
    rehash(hashes)
    return hashes, sorted(cpu)


def collect_inputs(args):
    epoch = integer(args.epoch, "Matching future integer epoch required", 31)
    activation_path = ROOT / f"build/evidence/native-pass-{epoch}/activation.json"
    handoff_path = ROOT / f"build/evidence/native-pass-{epoch}-build-handoff-1/result.json"
    manifest_path = Path(args.ownership_manifest).resolve()
    require(manifest_path.parent == ROOT / "compat/native-epochs" and re.fullmatch(rf"pass{epoch}-w[1-9][0-9]*-ownership\.json", manifest_path.name), "Canonical future ownership manifest required")
    hashes, cpu = held_inputs()
    def add(path, expected=None):
        path = Path(path).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), "Missing/outside protected input: " + str(path))
        value = sha(path)
        require(expected is None or value == digest(expected), "Protected pin differs: " + str(path))
        name = path.relative_to(ROOT).as_posix()
        require(name not in hashes or hashes[name] == value, "Conflicting protected identity")
        hashes[name] = value
    add(activation_path, args.expected_activation_sha256)
    add(handoff_path, args.expected_native_build_handoff_sha256)
    add(manifest_path, args.expected_ownership_manifest_sha256)
    a, h, m = read(activation_path), read(handoff_path), read(manifest_path)
    for name, value in a["proof_input_hashes"].items():
        add(member(activation_path.parent, name), value)
    add(activation_path.parent / "ownership-manifest.json", args.expected_ownership_manifest_sha256)
    f, s = read(activation_path.parent / "frozen-inputs.json"), read(activation_path.parent / "status.json")
    validate_context(epoch, a, h, m, f, s, args.expected_ownership_manifest_sha256, args.expected_native_build_handoff_sha256)
    validate_xml(activation_path.parent / "ctest.xml", tuple((n, n) for n in m["ctest_expected_names"]))
    binaries = read(activation_path.parent / "binary-hashes.json")
    require(binaries == h["all_archived_binary_hashes"] and len(binaries) >= 4, "All archived build binaries differ")
    for name, value in binaries.items(): add(member(activation_path.parent / "binaries", name), value)
    for key, directory in (("source_files", m["paths"]["snapshot"]), ("harness_files", m["paths"]["harness"])):
        for name, value in f[key].items(): add(member(member(ROOT, directory), name), value)
    # Future live C++ work is allowed; qualification authority is the frozen
    # source/harness and actual native leaves, not unbuilt later WIP source.
    for name, value in a["activated"].items():
        add(ROOT / ("src/vispy/visuals/text" if name.startswith("_sdf_cpu.") else "src/vispy") / name, value)
    for name, value in a["python_inputs"].items(): add(member(ROOT, name), value)
    for path in (ROOT / "src/vispy").rglob("*.py"): add(path)
    require(args.context_proof, "Explicit reviewed future CPU/source context pins required")
    for item in args.context_proof:
        name, value = item.rsplit("=", 1)
        path = member(ROOT, name)
        add(path, value)
        proof = read(path)
        validate_context_proof(proof)
    add(Path(__file__))
    add(Path(sys.executable))
    rehash(hashes)
    return hashes, cpu, {"epoch": epoch, "activation_sha256": sha(activation_path), "handoff_sha256": sha(handoff_path),
                        "manifest_sha256": sha(manifest_path), "source_tree_sha256": m["source_tree_sha256"],
                        "harness_tree_sha256": m["harness_tree_sha256"], "native_binary_hashes": a["activated"],
                        "ctest_names": m["ctest_expected_names"], "source_files": len(f["source_files"]), "harness_files": len(f["harness_files"])}


def child_environment(args, output):
    env = {k: v for k, v in os.environ.items() if k.upper() not in {"PYTHONPATH", "PYTHONHOME", "PYTHONOPTIMIZE", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"}}
    env.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONPATH=os.pathsep.join((str(output), str(ROOT), str(ROOT / "src"))),
               VISPY_LINE_ENDPOINTS_EPOCH=str(args.epoch),
               VISPY_LINE_ENDPOINTS_ACTIVATION=str(ROOT / f"build/evidence/native-pass-{args.epoch}/activation.json"),
               VISPY_LINE_ENDPOINTS_ACTIVATION_SHA256=args.expected_activation_sha256,
               VISPY_LINE_ENDPOINTS_HANDOFF_SHA256=args.expected_native_build_handoff_sha256,
               VISPY_LINE_ENDPOINTS_EVIDENCE=str(output / "raw"))
    return env


PLUGIN = r'''import json, os, sys, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STATE={"pid":os.getpid(),"executable":sys.executable,"version":sys.version,"selected":[],"deselected":[],"reports":[],"native_origins":{}}
def save():
    leaf=sys.modules.get("vispy._dawn")
    if leaf is not None: STATE["native_origins"]["vispy._dawn"]=str(Path(leaf.__file__).resolve())
    (ROOT/"process.json").write_text(json.dumps(STATE,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def pytest_collection_finish(session):
    STATE["selected"]=[item.nodeid for item in session.items];save()
def pytest_deselected(items):
    STATE["deselected"].extend(item.nodeid for item in items);save()
def pytest_runtest_logreport(report):
    STATE["reports"].append({"nodeid":report.nodeid,"phase":report.when,"outcome":report.outcome,"longrepr":str(report.longrepr) if report.failed or report.skipped else None});save()
def pytest_sessionfinish(session,exitstatus):
    STATE["exitstatus"]=int(exitstatus);STATE["session_terminal"]=True;save()
'''


def validate_process(path, cpu, context, expected_pid):
    record = read(path)
    require(type(record["pid"]) is int and record["pid"] > 0 and record.get("session_terminal") is True
            and type(record.get("exitstatus")) is int and record["exitstatus"] == 0, "Actual child session did not succeed")
    require(type(expected_pid) is int and record["pid"] == expected_pid, "Process record does not belong to launched child")
    selected, deselected = record["selected"], record["deselected"]
    require(len(selected) == len(set(selected)) == 18 and set(selected) == set(GPU_IDS), "Actual18 selected IDs differ")
    require(len(deselected) == len(set(deselected)) == 74 and set(deselected) == set(cpu), "Actual74 CPU deselections differ")
    reports = record["reports"]
    require(len(reports) == 54 and all(r["outcome"] == "passed" for r in reports), "Actual case phases failed/missing")
    for name in GPU_IDS:
        phases = [r["phase"] for r in reports if r["nodeid"] == name]
        require(sorted(phases) == ["call", "setup", "teardown"], "Actual case phases duplicate/missing")
    dawn = next(n for n in context["native_binary_hashes"] if n.startswith("_dawn."))
    require(record["native_origins"] == {"vispy._dawn": str(ROOT / "src/vispy" / dawn)}, "Actual native module origin differs")
    require(Path(record["executable"]).resolve() == Path(sys.executable).resolve(), "Child interpreter differs")
    return {"pid": record["pid"], "GPU_cases": 18, "CPU_deselections": 74, "actual_phases": 54, "native_origins": record["native_origins"]}


def child_process_closure(child_exit, record):
    """A normal process exit is not a native resource-cleanup observation."""
    normal = (type(child_exit) is int and child_exit == 0 and isinstance(record, dict)
              and record.get("session_terminal") is True and type(record.get("exitstatus")) is int
              and record["exitstatus"] == 0)
    return {"normal_child_process_exit_verified": normal, "native_cleanup_proven_by_exit": False,
            "native_cleanup_evidence_scope": "Unchanged held per-case resource/Ticket/data assertions; process exit alone proves no native cleanup"}


def validate_raw(output, context):
    """Independently decode retained original typed bits; never invoke native."""
    import numpy as np
    helper_path = ROOT / "tools/fixture_line_endpoints_dawn.py"
    require(sha(helper_path) == SOURCES["tools/fixture_line_endpoints_dawn.py"], "Held decoder changed")
    spec = importlib.util.spec_from_file_location("line_endpoint_retained_decoder", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    raw = output / "raw"
    require({p.name for p in raw.iterdir() if p.is_dir()} == FOLDERS, "Exact18 raw case folders differ")
    devices = []
    for folder in raw.iterdir():
        device = read(folder / "device.json")
        require(device["ok"] is True and device["software"] is False, "Actual hardware device required")
        require(device["max_compute_workgroup_size_x"] >= 64 and device["max_compute_invocations_per_workgroup"] >= 64 and device["max_storage_buffers_per_shader_stage"] >= 2, "Actual grants inadequate")
        devices.append(device)
    original = {name: helper.load_case(name) for name in BASIC_CASES}
    decoded = 0
    for name, case in original.items():
        folder = raw / name
        record = read(folder / "capture-0-metadata.json")
        record.update(data=np.load(folder / "capture-0-data.npy", allow_pickle=False), raw_data=np.load(folder / "capture-0-raw.npy", allow_pickle=False))
        helper.decode(record, case)
        decoded += 1
    lifetime_base = ROOT / "build/evidence/line-endpoint-lifetime-dawn-authoring-3"
    variants = {}
    for label in ("A", "B", "uniform-only"):
        case = dict(original["matrices_arrays"])
        case["expected"] = {key: np.load(lifetime_base / (label + "-expected-" + key + ".npy"), allow_pickle=False) for key in case["expected"]}
        variants[label] = case
    failures = 0
    for metadata_path in raw.rglob("*-metadata.json"):
        if metadata_path.parent.name in BASIC_CASES:
            continue
        payload = read(metadata_path)
        is_list = isinstance(payload, list)
        rows = payload if is_list else [payload]
        prefix = metadata_path.name[:-len("-metadata.json")]
        for i, record in enumerate(rows):
            stem = prefix + ("-" + str(i) if is_list else "")
            record.update(data=np.load(metadata_path.parent / (stem + "-data.npy"), allow_pickle=False), raw_data=np.load(metadata_path.parent / (stem + "-raw.npy"), allow_pickle=False))
            if record["status"] == "completed":
                label = "B" if prefix == "pending-revisions" and i == 1 else "uniform-only" if metadata_path.parent.name == "isolated-changed-UBO" else "A"
                helper.decode(record, variants[label])
                decoded += 1
            else:
                helper.rejected(record)
                failures += 1
    require(failures >= 134, "Actual abort/cancel/loss/shutdown failures not retained")
    require("vispy._dawn" not in sys.modules, "Parent retained admission must not import native")
    return {"decoded_capture_records": decoded, "rejected_failure_records": failures,
            "devices": devices, "scope": "Exact original typed output/canary re-admission; lifecycle/counter predicates remain the held executed tests"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--expected-activation-sha256", type=digest, required=True)
    parser.add_argument("--expected-native-build-handoff-sha256", type=digest, required=True)
    parser.add_argument("--ownership-manifest", required=True)
    parser.add_argument("--expected-ownership-manifest-sha256", type=digest, required=True)
    parser.add_argument("--context-proof", action="append", default=[], metavar="REPOSITORY_PATH=SHA256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    require(output.parent == ROOT / "build/evidence" and output.name.startswith(f"line-endpoint-native-pass{args.epoch}-"), "Fresh canonical endpoint evidence folder required")
    hashes, cpu, context = collect_inputs(args)
    command = [sys.executable, "-B", "-m", "pytest", BASIC_FILE, LIFETIME_FILE, "-m", "gpu", "-q", "-p", "line_endpoint_job_plugin", "--junitxml=" + str(output / "junit.xml")]
    env = child_environment(args, output)
    pinned_env = {k: env[k] for k in sorted(env) if k.startswith(("VISPY_LINE_ENDPOINTS_", "PYTHON", "PYTEST"))}
    plan = {"schema": 1, "runner_sha256": sha(__file__), "context": context, "protected_inputs": hashes,
            "CPU_deselected_ids": cpu, "GPU_ids": list(GPU_IDS), "command": command, "environment": pinned_env,
            "plugin_sha256": hashlib.sha256(PLUGIN.encode("utf-8")).hexdigest(), "scope": "Private typed evaluator ABI; original D1 criteria unchanged"}
    if args.freeze:
        require(not output.exists(), "Fresh output required; prior attempts remain immutable")
        output.mkdir(parents=False, exist_ok=False)
        protected = archive(output / "protected", hashes)
        (output / "line_endpoint_job_plugin.py").write_text(PLUGIN, encoding="utf-8")
        write_new(output / "inputs.json", {**plan, "archive": protected, "GPU_used": False, "native_imported": False})
        rehash(hashes)
        print(json.dumps({"status": "frozen_unexecuted", "inputs_sha256": sha(output / "inputs.json"), "archive": protected}), flush=True)
        return 0
    frozen = read(output / "inputs.json")
    require({k: frozen[k] for k in plan} == plan, "Frozen exact job context differs")
    require(not (output / "terminal.json").exists() and not (output / "process.json").exists() and not (output / "raw").exists(), "Job already attempted; preserve it and use a fresh reviewed wrapper/output")
    validate_archive(output / "protected", hashes)
    require(sha(output / "line_endpoint_job_plugin.py") == plan["plugin_sha256"], "Frozen child plugin changed")
    child = None
    terminal = {"utc": datetime.now(timezone.utc).isoformat(), "context": context, "inputs_sha256": sha(output / "inputs.json"),
                "GPU_attempted": False, "GPU_used": None, "native_imported": None, "process_exit": 1, "status": "failed", "GPU_released": False}
    try:
        with (output / "stdout.log").open("x", encoding="utf-8") as stdout, (output / "stderr.log").open("x", encoding="utf-8") as stderr:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
            terminal.update(child_pid=child.pid, GPU_attempted=True)
            write_new(output / "launch.json", {"pid": child.pid, "parent_pid": os.getpid(), "command": command, "environment": pinned_env, "utc": terminal["utc"]})
            print(json.dumps({"child_pid": child.pid, "output": str(output), "scope": "one child; no restart on observation timeout"}), flush=True)
            terminal["child_exit"] = child.wait()
        require(terminal["child_exit"] == 0, "Actual child failed; retained witnesses may be unresolved")
        terminal["process"] = validate_process(output / "process.json", cpu, context, child.pid)
        terminal["xml"] = validate_xml(output / "junit.xml", tuple(map(xml_identity, GPU_IDS)))
        terminal["raw_admission"] = validate_raw(output, context)
        terminal.update(process_exit=0, status="passed", GPU_used=True, native_imported=True)
    except BaseException:
        terminal["error"] = traceback.format_exc()
        # Missing/crashed child records cannot prove that no graphics was used.
    finally:
        terminal["child_live"] = child is not None and child.poll() is None
        terminal["GPU_released"] = child is not None and not terminal["child_live"]
        process_record = None
        try:
            if (output / "process.json").exists(): process_record = read(output / "process.json")
        except BaseException:
            terminal["process_record_error"] = traceback.format_exc()
        terminal["child_process_closure"] = child_process_closure(terminal.get("child_exit"), process_record)
        try:
            terminal["protected_after"] = rehash(hashes)
            terminal["archive_after"] = validate_archive(output / "protected", hashes)
            terminal["protected_unchanged"] = True
        except BaseException:
            terminal.update(process_exit=1, status="failed", protected_unchanged=False, protection_error=traceback.format_exc())
        terminal["artifacts"] = {p.relative_to(output).as_posix(): sha(p) for p in output.rglob("*") if p.is_file() and "protected" not in p.relative_to(output).parts}
        write_new(output / "terminal.json", terminal)
        print(json.dumps({"status": terminal["status"], "process_exit": terminal["process_exit"], "child_live": terminal["child_live"], "GPU_released": terminal["GPU_released"], "terminal_sha256": sha(output / "terminal.json")}), flush=True)
    return terminal["process_exit"]


if __name__ == "__main__":
    raise SystemExit(main())
