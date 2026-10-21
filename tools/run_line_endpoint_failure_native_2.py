"""Independent, guarded three-case native terminal-record control runner.

Pure preparation does not qualify hardware. Only --run starts one child after
an actual future epoch's activation/build/source context has been frozen and
rechecked. The controls intentionally submit no GPU work and do not qualify
pipeline-failure rollback, endpoint output, or rasterization.
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/native/test_line_endpoint_failure_dawn.py"
AUTHOR = "build/evidence/line-endpoint-failure-dawn-authoring-2"
PATTERN_PATH = "tools/run_line_endpoint_native_3.py"
IDENTITY_PATH = "tools/line_endpoint_process_identity.py"
PINS = {
    SOURCE: "1df7dbf123f040ade4ea42763c601e6e8b2debb21ded5de63f3cb119d73205da",
    PATTERN_PATH: "fd25396bef9e0cb49ab19c244b8e1a89b62ee8bd71aec7f336814a6e2578d05b",
    IDENTITY_PATH: "07694626c5f6e6998d6a2bbb38d275219d8bfd5936d78463a1a806b881d5c321",
    AUTHOR + "/result.json": "db3e22c597afe872ccc34a1878e3c76031ced2017fad1704a06c004dac2551fd",
    AUTHOR + "/seal.json": "09011e97f32035e16ea2ca7b07a9f83b9ded13c9291666b130fcdb88093608c9",
    "build/evidence/line-endpoint-failure-dawn-review-shaders-2/result.json": "b134350c39433a3657e89202b0a7f25df2e9f86d618b508aae0ed22d4b85612b",
}
CONTROLS = ("cancel-unpainted", "abort-paint", "destroy-owner")
GPU_IDS = tuple(SOURCE + "::test_native_rejected_unsubmitted_draw_terminal_records_drain_and_slots_recover[" + name + "]" for name in CONTROLS)
ZERO_WORK = ("pending_tickets", "pending_draws", "queued_frames", "pending_timestamp_frames", "line_resource_pool_busy_slots")
ZERO_EXECUTION = ("dawn_queue_submits", "draw_calls", "compute_passes", "line_endpoint_dispatches", "line_endpoint_rows", "timestamp_query_sets", "timestamp_resolves", "timestamp_readbacks")
NO_PRESENT = (1 << 64) - 1
ERROR = "DRAW first exceeds native nonnegative count range"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_patterns():
    # Module initialization defines stdlib-only utilities; its main is never
    # invoked, and none of its eighteen selectors or criteria are reassigned.
    for name in (PATTERN_PATH, IDENTITY_PATH):
        require(sha(ROOT / name) == PINS[name], "Pinned utility source differs: " + name)
    spec = importlib.util.spec_from_file_location("line_failure_pinned_patterns", ROOT / PATTERN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require("vispy._dawn" not in sys.modules, "Pure utilities imported native")
    return module


patterns = load_patterns()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def predicate_namespace():
    """Compile only the two held pure assertion functions, never test imports."""
    path = ROOT / SOURCE
    require(sha(path) == PINS[SOURCE], "Failure criteria source differs")
    tree = ast.parse(path.read_bytes())
    values = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    controls = ast.literal_eval(values["CONTROLS"])
    require(tuple(controls) == CONTROLS and ast.literal_eval(values["ZERO_WORK"]) == ZERO_WORK
            and ast.literal_eval(values["ZERO_EXECUTION"]) == ZERO_EXECUTION, "Held control/counter declarations differ")
    require(ast.dump(values["NO_PRESENT"], include_attributes=False) == ast.dump(ast.parse("(1 << 64) - 1", mode="eval").body, include_attributes=False), "No-present sentinel differs")
    selected = [copy.deepcopy(n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"failed_unsubmitted", "no_work"}]
    require({n.name for n in selected} == {"failed_unsubmitted", "no_work"}, "Pure terminal predicates missing")
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    namespace = {"CONTROLS": controls, "ZERO_WORK": ZERO_WORK, "ZERO_EXECUTION": ZERO_EXECUTION, "NO_PRESENT": NO_PRESENT}
    exec(compile(module, str(path) + ":pure-terminal-predicates", "exec"), namespace)
    identity = hashlib.sha256(ast.dump(module, include_attributes=False).encode()).hexdigest()
    return namespace, identity


def validate_cpu_authoring(proof, seal, process):
    require(type(proof["process_exit"]) is type(proof["child_exit"]) is int and proof["process_exit"] == proof["child_exit"] == 0, "CPU authoring did not succeed")
    require(type(proof["executed"]) is type(proof["errors"]) is type(proof["failures"]) is int
            and proof["executed"] == 29 and proof["errors"] == proof["failures"] == 0, "CPU29 proof count/failure differs")
    require(proof["GPU_used"] is False and proof["native_imported"] is False and proof["protected_unchanged"] is True, "Historical CPU authoring scope differs")
    require(proof["owned_sources_sha256"] == {SOURCE: PINS[SOURCE]}, "CPU proof source binding differs")
    cpu = proof["CPU_case_ids"]
    require(len(cpu) == len(set(cpu)) == 29 and all(n.startswith(SOURCE + "::test_cpu_") for n in cpu), "Exact CPU29 identities missing")
    require(tuple(proof["GPU_ids_unrun"]) == GPU_IDS, "Exact GPU3 authoring identities differ")
    require(type(seal["process_exit"]) is int and seal["process_exit"] == 0 and len(seal["artifacts"]) == 9, "Authoring seal differs")
    require(seal["artifacts"]["result.json"] == PINS[AUTHOR + "/result.json"] and seal["artifacts"]["source.py"] == PINS[SOURCE], "Authoring seal/source binding differs")
    require(process["selected"] == cpu and tuple(process["deselected"]) == GPU_IDS, "Historical selected/deselected identities differ")
    require(process["session_terminal"] is True and type(process["exitstatus"]) is int and process["exitstatus"] == 0, "CPU process did not terminate successfully")
    reports = process["reports"]
    phases = {(n, phase) for n in cpu for phase in ("setup", "call", "teardown")}
    require(len(reports) == 87 and {(r["id"], r["phase"]) for r in reports} == phases and all(r["outcome"] == "passed" for r in reports), "Actual CPU29 phases differ")
    return tuple(cpu)


def resolve_historical_inputs(proof):
    """Preserve old CPU protection separately from current native authority.

    A changed current leaf may resolve only to its exact retained prior image
    or source archive. No historical hash is silently updated to a new epoch.
    """
    origins = {}
    for name, value in proof["protected_inputs"].items():
        live = patterns.member(ROOT, name)
        candidates = [live]
        if name.startswith("src/vispy/") and name.endswith((".pyd", ".dll", ".json")):
            candidates.append(ROOT / "build/evidence/native-pass-31/binaries" / Path(name).name)
        if name.startswith(("cpp/", "tests/", "src/")):
            candidates.append(patterns.member(ROOT / "build/w17/source", name))
        if name in {"cpp/shader/line_evaluator.cpp", "tests/lines/line_evaluator_contract.cpp"}:
            candidates.append(patterns.member(ROOT / "build/evidence/line-evaluator-storage-access-source-only-1/after", name))
        matched = next((path for path in candidates if path.is_file() and sha(path) == value), None)
        require(matched is not None, "Historical CPU-protected bytes unavailable: " + name)
        origins[name] = {"origin": matched.relative_to(ROOT).as_posix(), "sha256": value}
    require(len(origins) == 2520, "Historical protection inventory differs")
    return origins


def held_inputs():
    hashes, _ = patterns.held_inputs()  # original eighteen source/array holds, not their execution
    hashes.update(PINS)
    patterns.rehash(hashes)
    proof, seal = read(ROOT / (AUTHOR + "/result.json")), read(ROOT / (AUTHOR + "/seal.json"))
    cpu = validate_cpu_authoring(proof, seal, read(ROOT / (AUTHOR + "/process.json")))
    for name, value in seal["artifacts"].items():
        path = patterns.member(ROOT / AUTHOR, name)
        require(sha(path) == value, "Retained authoring artifact differs")
        hashes[path.relative_to(ROOT).as_posix()] = value
    patterns.validate_xml(ROOT / (AUTHOR + "/junit.xml"), tuple(map(patterns.xml_identity, cpu)))
    review = read(ROOT / "build/evidence/line-endpoint-failure-dawn-review-shaders-2/result.json")
    require(review["status"] == "CLEAR_WITH_SCOPE" and review["process_exit"] == 0 and review["material_findings"] == [], "Failure source review is not clear")
    origins = resolve_historical_inputs(proof)
    for row in origins.values():
        require(row["origin"] not in hashes or hashes[row["origin"]] == row["sha256"], "Conflicting historical input origin")
        hashes[row["origin"]] = row["sha256"]
    _, predicate_identity = predicate_namespace()
    patterns.rehash(hashes)
    return hashes, cpu, {"result_sha256": PINS[AUTHOR + "/result.json"], "seal_sha256": PINS[AUTHOR + "/seal.json"],
                         "source_sha256": PINS[SOURCE], "pure_predicate_AST_sha256": predicate_identity,
                         "scope": "Historical CPU29 authoring/protected bytes; not current native authority",
                         "protected_input_origins": origins}


def validate_epoch(epoch):
    require(type(epoch) is int and epoch >= 32, "Actual reviewed future epoch32 or later required")
    return epoch


def validate_current_bundle(epoch, activation, handoff, manifest, frozen, status, manifest_sha, handoff_sha):
    validate_epoch(epoch)
    if "epoch" in handoff:
        require(type(handoff["epoch"]) is int and handoff["epoch"] == epoch, "Actual handoff epoch differs")
    patterns.validate_context(epoch, activation, handoff, manifest, frozen, status, manifest_sha, handoff_sha)


def collect_inputs(args):
    epoch = validate_epoch(args.epoch)
    activation_path = ROOT / f"build/evidence/native-pass-{epoch}/activation.json"
    handoff_path = ROOT / f"build/evidence/native-pass-{epoch}-build-handoff-1/result.json"
    manifest_path = Path(args.ownership_manifest).resolve()
    require(manifest_path.parent == ROOT / "compat/native-epochs" and patterns.re.fullmatch(rf"pass{epoch}-w[1-9][0-9]*-ownership\.json", manifest_path.name), "Canonical actual ownership manifest required")
    hashes, cpu, historical = held_inputs()
    def add(path, pin=None):
        path = Path(path).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), "Protected input missing/outside repository")
        value = sha(path)
        require(pin is None or value == patterns.digest(pin), "Observed current context pin differs: " + str(path))
        name = path.relative_to(ROOT).as_posix()
        require(name not in hashes or hashes[name] == value, "Conflicting current/historical origin")
        hashes[name] = value
    add(activation_path, args.expected_activation_sha256)
    add(handoff_path, args.expected_native_build_handoff_sha256)
    add(manifest_path, args.expected_ownership_manifest_sha256)
    activation, handoff, manifest = read(activation_path), read(handoff_path), read(manifest_path)
    for name, value in activation["proof_input_hashes"].items():
        add(patterns.member(activation_path.parent, name), value)
    add(activation_path.parent / "ownership-manifest.json", args.expected_ownership_manifest_sha256)
    frozen, status = read(activation_path.parent / "frozen-inputs.json"), read(activation_path.parent / "status.json")
    validate_current_bundle(epoch, activation, handoff, manifest, frozen, status, args.expected_ownership_manifest_sha256, args.expected_native_build_handoff_sha256)
    patterns.validate_xml(activation_path.parent / "ctest.xml", tuple((n, n) for n in manifest["ctest_expected_names"]))
    binaries = read(activation_path.parent / "binary-hashes.json")
    require(binaries == handoff["all_archived_binary_hashes"], "Full archived binary inventory differs")
    for name, value in binaries.items():
        add(patterns.member(activation_path.parent / "binaries", name), value)
    for key, directory in (("source_files", manifest["paths"]["snapshot"]), ("harness_files", manifest["paths"]["harness"])):
        for name, value in frozen[key].items():
            add(patterns.member(patterns.member(ROOT, directory), name), value)
    for name, value in activation["activated"].items():
        add(ROOT / ("src/vispy/visuals/text" if name.startswith("_sdf_cpu.") else "src/vispy") / name, value)
    for name, value in activation["python_inputs"].items():
        add(patterns.member(ROOT, name), value)
    for path in (ROOT / "src/vispy").rglob("*.py"):
        add(path)
    require(args.context_proof, "Explicit observed matching CPU/source review proof pins required")
    for item in args.context_proof:
        name, value = item.rsplit("=", 1)
        path = patterns.member(ROOT, name)
        add(path, value)
        patterns.validate_context_proof(read(path))
    add(Path(__file__))
    add(Path(sys.executable))
    identity = patterns.freeze_python_identity()
    patterns.rehash(hashes)
    context = {"epoch": epoch, "activation_sha256": sha(activation_path), "handoff_sha256": sha(handoff_path),
               "manifest_sha256": sha(manifest_path), "source_tree_sha256": manifest["source_tree_sha256"],
               "harness_tree_sha256": manifest["harness_tree_sha256"], "native_binary_hashes": activation["activated"],
               "source_files": len(frozen["source_files"]), "harness_files": len(frozen["harness_files"]),
               "ctest_names": manifest["ctest_expected_names"], "python_identity": identity,
               "activation_record": activation, "hardware_scope": "Zero-submit range rejection and actual terminal records only"}
    return hashes, cpu, context, historical


PLUGIN = (ROOT / IDENTITY_PATH).read_text(encoding="utf-8") + "\n" + '''import json, os, sys, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STATE={"pid":os.getpid(),"executable":sys.executable,"version":sys.version,"selected":[],"deselected":[],"reports":[],"native_origins":{}}
try:
    STATE["process_identity"]=observe_process_identity()
except BaseException:
    STATE["process_identity_error"]=traceback.format_exc()
def save():
    leaf=sys.modules.get("vispy._dawn")
    if leaf is not None: STATE["native_origins"]["vispy._dawn"]=str(Path(leaf.__file__).resolve())
    (ROOT/"process.json").write_bytes((json.dumps(STATE,indent=2,sort_keys=True)+"\\n").encode("utf-8"))
save()
def pytest_collection_finish(session):
    STATE["selected"]=[item.nodeid for item in session.items];save()
def pytest_deselected(items):
    STATE["deselected"].extend(item.nodeid for item in items);save()
def pytest_runtest_logreport(report):
    STATE["reports"].append({"nodeid":report.nodeid,"phase":report.when,"outcome":report.outcome,"longrepr":str(report.longrepr) if report.failed or report.skipped else None});save()
def pytest_sessionfinish(session,exitstatus):
    STATE["exitstatus"]=int(exitstatus);STATE["session_terminal"]=True;save()
'''


def validate_process(record, cpu, context, launched_pid):
    require(type(record.get("exitstatus")) is int and record["exitstatus"] == 0 and record.get("session_terminal") is True, "Actual child session failed/incomplete")
    identity = patterns.validate_process_identity(record, context["python_identity"], launched_pid)
    require(len(record["selected"]) == len(set(record["selected"])) == 3 and set(record["selected"]) == set(GPU_IDS), "Actual selected GPU3 identities differ")
    require(len(record["deselected"]) == len(set(record["deselected"])) == len(cpu) == 29 and set(record["deselected"]) == set(cpu), "Actual CPU29 deselections differ")
    reports = record["reports"]
    require(len(reports) == 9 and all(r["outcome"] == "passed" for r in reports), "Actual GPU3 phases failed/missing")
    for name in GPU_IDS:
        require(sorted(r["phase"] for r in reports if r["nodeid"] == name) == ["call", "setup", "teardown"], "Actual case phases missing/duplicated")
    leaf = next(n for n in context["native_binary_hashes"] if n.startswith("_dawn."))
    require(record["native_origins"] == {"vispy._dawn": str(ROOT / "src/vispy" / leaf)}, "Actual imported extension origin differs")
    return {"selected": 3, "deselected": 29, "passed_phases": 9, "process_identity": identity, "native_origins": record["native_origins"]}


def validate_case(control, data, context):
    require(control in CONTROLS, "Unknown failure control")
    actual_context = data["context"]
    require(actual_context == {"epoch": context["epoch"], "path": str(ROOT / f"build/evidence/native-pass-{context['epoch']}/activation.json"),
                               "sha256": context["activation_sha256"], "handoff_sha256": context["handoff_sha256"],
                               "activation": context["activation_record"]}, "Actual case native authority differs")
    device = data["device"]
    require(device["ok"] is True and device["software"] is False and device["backend"] in {"Vulkan", "Metal"}
            and device["adapter_type"] in {"discrete", "integrated"}, "Actual hardware device required")
    require(device["timestamp_query"] is True, "Granted actual timestamp feature required")
    require(isinstance(data["rejected-range"]["error"], str) and ERROR in data["rejected-range"]["error"], "Actual expected negative-first range error absent")
    accepted, collection, cleanup = data["accepted"], data["collection"], data["cleanup"]
    before, after = accepted["before"], accepted["after"]
    require(type(before["device_generation"]) is int and before["device_generation"] > 0, "Actual device generation absent")
    require(type(before["frame_slots"]) is int and 1 <= before["frame_slots"] <= 8, "Original frame slots invalid")
    require(all(type(before[k]) is int and before[k] == 0 for k in ZERO_WORK), "Control began with unrelated live work")
    receipt, timing = accepted["receipt"], accepted["timing"]
    token = receipt["paint_token"]
    require(type(token) is int and (token > 0 if control == "abort-paint" else token == 0), "Actual paint token/scope differs")
    namespace, _ = predicate_namespace()
    namespace["failed_unsubmitted"](receipt, timing, 101, before["device_generation"], token, control)
    namespace["no_work"](before, after)
    require(type(receipt["present_count"]) is int and receipt["present_count"] == 0
            and type(timing["device_generation"]) is int and type(timing["render_span_ns"]) is int
            and type(timing["pass_sum_ns"]) is int, "Terminal count/span types differ")
    require(collection["receipts"] == [receipt] and collection["timings"] == [timing], "Collected terminal records duplicated/differ")
    require(collection["probes"] and collection["probes"][-1] == after, "Actual terminal collection probe absent")
    for probe in collection["probes"]:
        require(all(type(probe[k]) is int and probe[k] == before[k] for k in ZERO_EXECUTION), "Collection observed submitted work")
    require(type(accepted["restored_slots"]) is int and accepted["restored_slots"] == before["frame_slots"], "Original frame slots were not restored")
    require(cleanup["receipts"] == cleanup["timings"] == [], "Cleanup retained unexpected terminal records")
    namespace["no_work"](before, cleanup["probe"])
    require(type(cleanup["probe"]["frame_slots"]) is int and cleanup["probe"]["frame_slots"] == before["frame_slots"], "Final cleanup frame slots differ")
    return {"control": control, "device": device, "status": receipt["status"], "timing_status": timing["status"],
            "device_generation": before["device_generation"], "submission_count": 0, "timestamp_passes": 0,
            "slot_restored": accepted["restored_slots"], "temporal_refusal_scope": "Unchanged executed test body asserts idle refusal before record collection; no separate raw temporal witness fabricated"}


def validate_raw(output, context):
    raw = output / "raw"
    require(raw.is_dir() and {p.name for p in raw.iterdir()} == {"pre-ticket-" + n for n in CONTROLS}, "Actual raw three-case inventory differs")
    result = []
    for control in CONTROLS:
        folder = raw / ("pre-ticket-" + control)
        names = {"context", "device", "rejected-range", "accepted", "collection", "cleanup"}
        require(folder.is_dir() and {p.name for p in folder.iterdir()} == {n + ".json" for n in names}, "Raw failure/missing/extra artifact")
        result.append(validate_case(control, {n: read(folder / (n + ".json")) for n in names}, context))
    return {"cases": result, "count": 3, "scope": "Actual hardware/native zero-submit terminal controls; no pipeline/output or GPU timestamp interval claim"}


def follow_launched_child(process, terminal):
    """Keep the same launched handle until a strict terminal wait result.

    Interrupted observations do not authorize publication while a child lives.
    No relaunch, termination, timeout release or native-cleanup inference occurs.
    """
    terminal["child_followed_to_terminal"] = False
    if process is None:
        return
    terminal["child_pid"] = process.pid
    terminal["child_follow_wait_error_count"] = 0
    terminal["child_follow_wait_errors"] = []
    while True:
        try:
            code = process.wait()
            require(type(code) is int, "Actual child wait must return its terminal integer exit")
            terminal.update(child_exit=code, child_followed_to_terminal=True)
            return
        except BaseException:
            terminal["child_follow_wait_error_count"] += 1
            if len(terminal["child_follow_wait_errors"]) < 16:
                terminal["child_follow_wait_errors"].append(traceback.format_exc()[:4096])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--expected-activation-sha256", type=patterns.digest, required=True)
    parser.add_argument("--expected-native-build-handoff-sha256", type=patterns.digest, required=True)
    parser.add_argument("--ownership-manifest", required=True)
    parser.add_argument("--expected-ownership-manifest-sha256", type=patterns.digest, required=True)
    parser.add_argument("--context-proof", action="append", default=[], metavar="REPOSITORY_PATH=SHA256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    validate_epoch(args.epoch)
    output = Path(args.output).resolve()
    require(output.parent == ROOT / "build/evidence" and output.name.startswith(f"line-endpoint-failure-native-pass{args.epoch}-"), "Fresh canonical failure evidence folder required")
    hashes, cpu, context, historical = collect_inputs(args)
    external = patterns.external_python_images(context["python_identity"])
    command = [sys.executable, "-B", "-m", "pytest", SOURCE, "-m", "gpu", "-q", "-p", "line_failure_job_plugin", "--junitxml=" + str(output / "junit.xml")]
    env = patterns.child_environment(args, output)
    pinned_env = {k: env[k] for k in sorted(env) if k.startswith(("VISPY_LINE_ENDPOINTS_", "PYTHON", "PYTEST"))}
    plan = {"schema": 1, "runner_sha256": sha(__file__), "context": context, "historical_CPU_evidence": historical,
            "protected_inputs": hashes, "GPU_ids": list(GPU_IDS), "CPU_deselected_ids": list(cpu),
            "command": command, "environment": pinned_env, "plugin_sha256": hashlib.sha256(PLUGIN.encode("utf-8")).hexdigest(),
            "external_python_images": external, "criteria_scope": "Zero-submit negative DRAW/owner terminal-record recovery; pipeline-failure/output unqualified"}
    if args.freeze:
        require(not output.exists(), "Fresh output required; prior attempts immutable")
        output.mkdir(parents=False, exist_ok=False)
        protected = patterns.archive(output / "protected", hashes)
        external_archive = patterns.archive_external_images(output / "external-python", external)
        (output / "line_failure_job_plugin.py").write_bytes(PLUGIN.encode("utf-8"))
        write_new(output / "inputs.json", {**plan, "archive": protected, "external_archive": external_archive, "GPU_used": False, "native_imported": False})
        patterns.rehash(hashes)
        patterns.rehash_external_images(external)
        print(json.dumps({"status": "frozen_unexecuted", "inputs_sha256": sha(output / "inputs.json")}), flush=True)
        return 0
    frozen = read(output / "inputs.json")
    require({k: frozen[k] for k in plan} == plan, "Frozen exact control context differs")
    require(not (output / "terminal.json").exists() and not (output / "process.json").exists() and not (output / "raw").exists(), "Job already attempted; no replay")
    patterns.validate_archive(output / "protected", hashes)
    patterns.validate_external_archive(output / "external-python", external)
    require(sha(output / "line_failure_job_plugin.py") == plan["plugin_sha256"], "Actual byte-written child plugin differs")
    child = None
    terminal = {"utc": datetime.now(timezone.utc).isoformat(), "context": context, "inputs_sha256": sha(output / "inputs.json"),
                "GPU_attempted": False, "GPU_used": None, "native_imported": None, "process_exit": 1,
                "status": "failed", "GPU_released": False, "scope": plan["criteria_scope"]}
    try:
        with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
            terminal.update(child_pid=child.pid, GPU_attempted=True)
            write_new(output / "launch.json", {"pid": child.pid, "parent_pid": os.getpid(), "command": command, "environment": pinned_env, "utc": terminal["utc"]})
            print(json.dumps({"child_pid": child.pid, "scope": "single child, no restart"}), flush=True)
            terminal["child_exit"] = child.wait()
        require(terminal["child_exit"] == 0, "Actual child failed; no hardware admission")
        terminal["process"] = validate_process(read(output / "process.json"), cpu, context, child.pid)
        terminal["xml"] = patterns.validate_xml(output / "junit.xml", tuple(map(patterns.xml_identity, GPU_IDS)))
        terminal["raw_admission"] = validate_raw(output, context)
        terminal.update(process_exit=0, status="passed", GPU_used=True, hardware_device_used=True,
                        GPU_work_submitted=False, native_imported=True)
    except BaseException:
        terminal["error"] = traceback.format_exc()
    finally:
        follow_launched_child(child, terminal)
        terminal["child_live"] = child is not None and child.poll() is None
        terminal["GPU_released"] = child is not None and not terminal["child_live"]
        process_record = None
        try:
            if (output / "process.json").exists():
                process_record = read(output / "process.json")
        except BaseException:
            terminal["process_record_error"] = traceback.format_exc()
        if process_record is not None and child is not None:
            try:
                terminal["process_identity_observation"] = patterns.validate_process_identity(process_record, context["python_identity"], child.pid)
            except BaseException:
                terminal["process_identity_error"] = traceback.format_exc()
        terminal["child_process_closure"] = patterns.child_process_closure(terminal.get("child_exit"), process_record)
        try:
            terminal["protected_after"] = patterns.rehash(hashes)
            terminal["archive_after"] = patterns.validate_archive(output / "protected", hashes)
            terminal["external_python_after"] = patterns.rehash_external_images(external)
            terminal["external_archive_after"] = patterns.validate_external_archive(output / "external-python", external)
            terminal["protected_unchanged"] = True
        except BaseException:
            terminal.update(process_exit=1, status="failed", protected_unchanged=False, protection_error=traceback.format_exc())
        terminal["artifacts"] = {p.relative_to(output).as_posix(): sha(p) for p in output.rglob("*") if p.is_file() and "protected" not in p.relative_to(output).parts}
        write_new(output / "terminal.json", terminal)
        print(json.dumps({"status": terminal["status"], "process_exit": terminal["process_exit"], "child_live": terminal["child_live"], "GPU_released": terminal["GPU_released"], "terminal_sha256": sha(output / "terminal.json")}), flush=True)
    return terminal["process_exit"]


if __name__ == "__main__":
    raise SystemExit(main())
