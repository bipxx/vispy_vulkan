"""CPU guards only; never import native, create Canvas or launch GPU child."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import ast

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "build/run_native_pass_30_ordinary_oversized_pending_2.py"
spec = importlib.util.spec_from_file_location("pending30_capture_runner_cpu", PATH)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def xml(path, ids):
    root = ET.Element("testsuites", tests=str(len(ids)), failures="0", errors="0", skipped="0")
    suite = ET.SubElement(root, "testsuite", tests=str(len(ids)), failures="0", errors="0", skipped="0")
    for classname, name in ids:
        ET.SubElement(suite, "testcase", classname=classname, name=name)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8")


def context():
    source = {"one.txt": "a" * 64}; harness = {"two.txt": "b" * 64}
    st = r.shared().tree_digest(source); ht = r.shared().tree_digest(harness)
    native = {name: "c" * 64 for name in r.NATIVE_NAMES}
    proofs = {name: "d" * 64 for name in r.PROOF_NAMES}
    recipe = dict(schema=1, epoch=30, source_tree_sha256=st, harness_tree_sha256=ht,
                  ownership_manifest_sha256="e" * 64, native_binary_hashes=native,
                  proof_input_hashes=proofs, source_files_count=1, harness_files_count=1)
    a = dict(epoch=30, native_source_tree_sha256=st, ownership_manifest_sha256="e" * 64,
             activated=native, proof_input_hashes=proofs)
    h = dict(status="passed_read_only_terminal_build_handoff", process_exit=0, in_place_copy=False,
             gpu_qualified=False, source_tree_sha256=st, harness_tree_sha256=ht, manifest_sha256="e" * 64,
             native_binary_hashes=native, proof_input_hashes=proofs, ctest_executed_count=16,
             ctest_expected_names=list(r.CTEST_NAMES), source_files_verified=1, harness_files_verified=1)
    m = dict(epoch=30, source_tree_sha256=st, harness_tree_sha256=ht, source_files=source,
             harness_inputs={name: {"sha256": value} for name, value in harness.items()},
             ctest_expected_names=list(r.CTEST_NAMES), paths={"snapshot": "build/w16/source",
             "harness": "build/evidence/native-pass-30/harness"})
    f = dict(epoch=30, source_tree_sha256=st, harness_tree_sha256=ht,
             ownership_manifest_sha256="e" * 64, source_files=source, harness_files=harness)
    s = dict(epoch=30, source_tree_sha256=st, status="build_and_ctest_passed")
    for value in (a, h, m, s): value["sdk_manifest_sha256"] = r.SDK_SHA
    m["sdk_tint_reader_enabled"] = s["sdk_tint_reader_enabled"] = False
    s.update(gpu_qualified=False, in_place_copy=False)
    return recipe, a, h, m, f, s


def test_fixed_ids_and_context_admit_only_disclosed_cpu_fixture():
    assert len(r.NODEIDS) == len(set(r.NODEIDS)) == 15
    assert len(r.CPU_NAMES) == len(set(r.CPU_NAMES)) == 17
    r.validate_context(*context())
    a = r.read(ROOT / r.AUTHORING_PATH)
    assert r.sha(ROOT / r.AUTHORING_PATH) == r.AUTHORING_SHA
    assert a["gpu_case_ids"] == list(r.ORIGINAL_NODEIDS) and a["cpu_cases"] == 16
    assert set(name for _, name in r._cpu_identities(ROOT / r.CAPTURE_AUTHORING_PATH.replace("authoring.json", "cpu.xml"))) == set(r.CPU_NAMES)
    assert "vispy._dawn" not in sys.modules


@pytest.mark.parametrize("index,key,value", [
    (0, "epoch", 29), (1, "epoch", 29), (3, "epoch", 29), (4, "epoch", 29), (5, "epoch", 29),
    (0, "epoch", True), (0, "schema", True), (2, "process_exit", 1), (2, "process_exit", False),
    (2, "status", "building"), (2, "in_place_copy", True), (2, "gpu_qualified", True),
    (5, "status", "building"), (0, "source_tree_sha256", "f" * 64),
    (0, "harness_tree_sha256", "f" * 64), (0, "source_files_count", 2),
    (0, "source_files_count", True), (2, "harness_files_verified", 2),
    (2, "ctest_executed_count", 15), (2, "ctest_expected_names", list(r.CTEST_NAMES[:-1])),
    (3, "ctest_expected_names", list(r.CTEST_NAMES) + [r.CTEST_NAMES[0]]),
    (3, "sdk_tint_reader_enabled", True), (5, "sdk_tint_reader_enabled", True),
    (2, "sdk_manifest_sha256", "f" * 64),
    (3, "paths", {"snapshot": "build/w15/source", "harness": "build/evidence/native-pass-30/harness"}),
])
def test_context_rejects_epoch_nonterminal_proof_inventory_and_substitution(index, key, value):
    values = deepcopy(context()); values[index][key] = value
    with pytest.raises(ValueError):
        r.validate_context(*values)


def synthetic_preflight(tmp_path, monkeypatch):
    """Valid through native verification only; no real epoch30 is fabricated."""
    recipe, a, h, m, f, s = context()
    monkeypatch.setattr(r, "ROOT", tmp_path)
    monkeypatch.setattr(r, "OUT", tmp_path / "candidate")
    monkeypatch.setattr(r, "RECIPE", tmp_path / "build/evidence/native-pass-30/ordinary-oversized-pending-capture-recipe.json")
    monkeypatch.setattr(r, "ACTIVATION", tmp_path / "build/evidence/native-pass-30/activation.json")
    monkeypatch.setattr(r, "HANDOFF", tmp_path / "build/evidence/native-pass-30-build-handoff-1/result.json")
    own = tmp_path / "build" / PATH.name; own.parent.mkdir(parents=True); own.write_bytes(PATH.read_bytes())
    monkeypatch.setattr(r, "__file__", str(own))
    shared = tmp_path / "build" / r.SHARED_PATH.name; shared.write_bytes(r.SHARED_PATH.read_bytes())
    monkeypatch.setattr(r, "SHARED_PATH", shared)
    one = tmp_path / "build/w16/source/one.txt"; one.parent.mkdir(parents=True); one.write_bytes(b"source")
    two = tmp_path / "build/evidence/native-pass-30/harness/two.txt"; two.parent.mkdir(parents=True); two.write_bytes(b"harness")
    sources, harness = {"one.txt": r.sha(one)}, {"two.txt": r.sha(two)}
    st, ht = r.shared().tree_digest(sources), r.shared().tree_digest(harness)
    for value in (recipe, h, m, f):
        value["source_tree_sha256"] = st; value["harness_tree_sha256"] = ht
    a["native_source_tree_sha256"] = st; s["source_tree_sha256"] = st
    m["source_files"] = f["source_files"] = sources
    f["harness_files"] = harness; m["harness_inputs"] = {name: {"sha256": value} for name, value in harness.items()}
    manifest = tmp_path / "compat/native-epochs/pass30-w16-ownership.json"; write(manifest, m)
    recipe["ownership_manifest_sha256"] = a["ownership_manifest_sha256"] = h["manifest_sha256"] = f["ownership_manifest_sha256"] = r.sha(manifest)
    native = {}
    for name in r.NATIVE_NAMES:
        directory = tmp_path / ("src/vispy/visuals/text" if name.startswith("_sdf") else "src/vispy")
        directory.mkdir(parents=True, exist_ok=True); file = directory / name; file.write_bytes(name.encode())
        archived = r.ACTIVATION.parent / "binaries" / name; archived.parent.mkdir(parents=True, exist_ok=True); archived.write_bytes(file.read_bytes())
        native[name] = r.sha(file)
    recipe["native_binary_hashes"] = a["activated"] = h["native_binary_hashes"] = native
    write(r.ACTIVATION.parent / "frozen-inputs.json", f)
    write(r.ACTIVATION.parent / "status.json", s)
    binaries = dict(native)
    for name in r.BUILD_BINARY_NAMES - r.NATIVE_NAMES:
        file = r.ACTIVATION.parent / "binaries" / name; file.write_bytes(name.encode()); binaries[name] = r.sha(file)
    write(r.ACTIVATION.parent / "binary-hashes.json", binaries)
    xml(r.ACTIVATION.parent / "ctest.xml", tuple((name, name) for name in r.CTEST_NAMES))
    write(r.ACTIVATION.parent / "ownership-manifest.json", m)
    proofs = {name: r.sha(r.ACTIVATION.parent / name) for name in r.PROOF_NAMES}
    recipe["proof_input_hashes"] = a["proof_input_hashes"] = h["proof_input_hashes"] = proofs
    write(r.HANDOFF, h); a["build_handoff_sha256"] = r.sha(r.HANDOFF); write(r.ACTIVATION, a)
    recipe.update(wrapper_sha256=r.sha(own), authoring_path=r.AUTHORING_PATH, authoring_sha256=r.AUTHORING_SHA,
                  authoring_terminal_sha256=r.AUTHORING_TERMINAL_SHA, working_cpu_seal_path=r.WORKING_SEAL_PATH,
                  working_cpu_seal_sha256=r.WORKING_SEAL_SHA,
                  review_inputs={r.WORKING_REVIEW_PATH: r.WORKING_REVIEW_SHA, r.PENDING_REVIEW_PATH: r.PENDING_REVIEW_SHA},
                  ownership_manifest_path="compat/native-epochs/pass30-w16-ownership.json",
                  activation_sha256=r.sha(r.ACTIVATION), build_handoff_sha256=r.sha(r.HANDOFF))
    for key, value in (("MANIFEST_SHA", r.sha(manifest)), ("SOURCE_TREE_SHA", st), ("HARNESS_TREE_SHA", ht),
                       ("FROZEN_SHA", proofs["frozen-inputs.json"]), ("SOURCE_FILES", 1), ("HARNESS_FILES", 1)):
        monkeypatch.setattr(r, key, value)
    write(r.RECIPE, recipe)
    return r.RECIPE, r.sha(r.RECIPE)


@pytest.mark.parametrize("change", ("tampered_binary", "missing_binary", "missing_handoff", "recipe_path", "recipe_hash", "criteria"))
def test_preflight_failure_happens_before_output_or_child(tmp_path, monkeypatch, change):
    path, checksum = synthetic_preflight(tmp_path, monkeypatch)
    binary = tmp_path / "src/vispy/_dawn.cp312-win_amd64.pyd"
    if change == "tampered_binary": binary.write_bytes(b"tampered")
    elif change == "missing_binary": binary.unlink()
    elif change == "missing_handoff": r.HANDOFF.unlink()
    elif change == "recipe_path": path = path.with_name("fake.json")
    elif change == "recipe_hash": checksum = "a" * 64
    elif change == "criteria":
        recipe = r.read(path); recipe["authoring_sha256"] = "a" * 64; write(path, recipe); checksum = r.sha(path)
    monkeypatch.setattr(r.subprocess, "Popen", lambda *a, **k: pytest.fail("preflight must precede child"))
    with pytest.raises((ValueError, FileNotFoundError)):
        r.freeze(path, checksum)
    assert not r.OUT.exists() and "vispy._dawn" not in sys.modules


@pytest.mark.parametrize("change", ("missing", "duplicate", "wrong", "not_gpu", "cpu_drop", "exit"))
def test_selected_ids_deselections_and_terminal_are_strict(change):
    value = dict(exitstatus=0, selected=[{"nodeid": n, "gpu": True} for n in r.NODEIDS],
                 deselected=[{"nodeid": r.TEST + "::" + n, "gpu": False} for n in r.CPU_NAMES])
    r.verify_selection(value, r.CPU_NAMES)
    if change == "missing": value["selected"].pop()
    elif change == "duplicate": value["selected"][-1] = value["selected"][0]
    elif change == "wrong": value["selected"][-1]["nodeid"] += "wrong"
    elif change == "not_gpu": value["selected"][0]["gpu"] = False
    elif change == "cpu_drop": value["deselected"].pop()
    else: value["exitstatus"] = 1
    with pytest.raises(ValueError): r.verify_selection(value, r.CPU_NAMES)


@pytest.mark.parametrize("change", ("drop", "duplicate", "skip", "failure", "error", "declared", "classname"))
def test_xml_requires_all_fifteen_executed_passes(tmp_path, change):
    path = tmp_path / "actual.xml"; xml(path, r.EXPECTED_IDS)
    r.shared().validate_xml(path, r.EXPECTED_IDS)
    tree = ET.parse(path); root = tree.getroot(); suite = root[0]
    if change == "drop": suite.remove(suite[-1]); root.set("tests", "14"); suite.set("tests", "14")
    elif change == "duplicate": suite[-1].attrib.update(suite[0].attrib)
    elif change in ("skip", "failure", "error"): ET.SubElement(suite[0], "skipped" if change == "skip" else change)
    elif change == "declared": root.set("tests", "14")
    else: suite[0].set("classname", "substitution")
    tree.write(path)
    with pytest.raises(ValueError): r.shared().validate_xml(path, r.EXPECTED_IDS)


def test_explicit_fixture_loader_ignores_cwd_pythonpath_and_tools_shadow(tmp_path, monkeypatch):
    hashes = {"tools/fixture_ordinary_oversized.py": "515a10b5aa78ecec71fb026619faecc36e4fc0c097500782988b62af6c0ff828",
              "tools/fixture_ordinary_oversized_pending.py": r.FIXTURE_SHA}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "wrong"))
    shadow = object(); monkeypatch.setitem(sys.modules, "tools", shadow)
    retired, fixture = r.load_fixtures(hashes)
    assert fixture.contract() == r.read(ROOT / r.AUTHORING_PATH)["contract"]
    assert sys.modules["tools"] is shadow and "vispy._dawn" not in sys.modules
    with pytest.raises(ValueError): r.load_fixtures({**hashes, "tools/fixture_ordinary_oversized_pending.py": "a" * 64})


def test_child_env_is_clean_and_preserves_actual_explicit_paths():
    inherited = {"PythonPath": "bad", "PYTHONHOME": "bad", "PYTHONOPTIMIZE": "1", "PYTEST_ADDOPTS": "--ignore=x", "PATH": "keep"}
    actual = r.clean_child_environment({"PYTHONPATH": "fixed project/build", "PYTHONDONTWRITEBYTECODE": "1"}, inherited)
    assert actual == {"PATH": "keep", "PYTHONPATH": "fixed project/build", "PYTHONDONTWRITEBYTECODE": "1"}


@pytest.fixture
def analytic():
    return r.load_fixtures({"tools/fixture_ordinary_oversized.py": "515a10b5aa78ecec71fb026619faecc36e4fc0c097500782988b62af6c0ff828",
                           "tools/fixture_ordinary_oversized_pending.py": r.FIXTURE_SHA})


def probe(f):
    value = {name: 0 for name in (*f.RESIDENT, *r.RESIDENT_EXTRA, *r.IDLE, "draw_calls", "dawn_queue_submits", "retired_tickets",
                                "vertex_input_oversized_entries", "vertex_input_oversized_bytes",
                                "vertex_input_current_entries", "vertex_input_cache_entries", "vertex_input_cache_bytes")}
    value.update(vertex_input_oversized_entry_limit=8, vertex_input_oversized_byte_limit=f.WORKING_BYTES)
    return value


@pytest.mark.parametrize("counter", ("draw_calls", "dawn_queue_submits", "retired_tickets", *r.IDLE))
def test_identical_pixels_cannot_hide_dropdraw_extra_submit_or_unretired_work(counter, analytic):
    _, f = analytic; before = probe(f); after = dict(before, draw_calls=1, dawn_queue_submits=1, retired_tickets=1)
    r.executed(before, after)
    after[counter] += 1
    with pytest.raises(ValueError): r.executed(before, after)


@pytest.mark.parametrize("counter", ("completion_waits", "finish_calls", "buffer_uploads", "vertex_input_conversion_builds", "portable_shader_misses", *r.RESIDENT_EXTRA))
def test_warm_cost_and_hidden_waits_cannot_be_admitted(counter, analytic):
    _, f = analytic; before = probe(f); after = dict(before); r.resident(before, after, f)
    after[counter] += 1
    with pytest.raises(ValueError): r.resident(before, after, f)


@pytest.mark.parametrize("key,value", (("vertex_input_oversized_entries", 9), ("vertex_input_oversized_bytes", 256*1024*1024+1),
                                      ("vertex_input_oversized_entry_limit", 9), ("vertex_input_current_entries", 7)))
def test_working_scoped_limits_cannot_be_silently_weakened(key, value, analytic):
    _, f = analytic; before = probe(f); r.working_bounds(before, before)
    with pytest.raises(ValueError): r.working_bounds(before, {**before, key: value})


def working_raw(folder, retired, f):
    w = f.working_plan(f.SAMPLE_LIMITS, layouts=2)
    baseline = probe(f)
    record = dict(baseline=baseline, device=f.SAMPLE_LIMITS, working_plan=asdict(w), images={}, filtered_GLIR=[])
    commands = [["SHADERS", 1, f.working_vertex_source(w), retired.FRAGMENT]]
    for index, (phase, layout) in enumerate(zip(("cold-A", "cold-B", "resident-0", "resident-1", "resident-2", "resident-3"), (0,1,0,1,0,1))):
        before = dict(baseline, draw_calls=index, dawn_queue_submits=index, retired_tickets=index,
                      vertex_input_oversized_entries=2, vertex_input_oversized_bytes=2*w.payload_bytes_per_layout)
        after = dict(before, draw_calls=index+1, dawn_queue_submits=index+1, retired_tickets=index+1)
        record[phase] = dict(layout=layout, before=before, after_retirement_before_read=after)
        expected = f.expected_working(w, layout); np.save(folder / (phase+".npy"), expected); np.save(folder / (phase+"-expected.npy"), expected)
        record["images"][phase] = {"actual": f.array_record(expected), "expected": f.array_record(expected)}
        commands.append(["DRAW", 1, "triangles", [w.base.first + layout*w.base.count, w.base.count], 1])
    record["filtered_GLIR"] = [commands]
    return record


@pytest.mark.parametrize("change", ("none", "warm_drop", "samepixel_dropdraw", "wrong_layout", "raw_pixel", "raw_hash", "shader", "trace_dropdraw"))
def test_full_raw_aba_checks_arrays_warm_counts_execution_and_trace(tmp_path, analytic, change):
    retired, f = analytic; record = working_raw(tmp_path, retired, f)
    name = r.GPU_NAMES[12]
    if change == "warm_drop": record.pop("resident-3")
    elif change == "samepixel_dropdraw": record["resident-2"]["after_retirement_before_read"]["draw_calls"] -= 1
    elif change == "wrong_layout": record["resident-0"]["layout"] = 1
    elif change == "raw_pixel":
        path = tmp_path / "resident-0.npy"; actual = np.load(path); actual[0,0,0] ^= 1; np.save(path, actual)
    elif change == "raw_hash": record["images"]["resident-0"]["actual"]["sha256"] = "a" * 64
    elif change == "shader": record["filtered_GLIR"][0][0][2] += " "
    elif change == "trace_dropdraw": record["filtered_GLIR"][0].pop()
    if change == "none":
        result = r.validate_case(tmp_path, name, record, retired, f)
        assert result["exact_images"] == result["filtered_draws"] == 6
    else:
        with pytest.raises((ValueError, KeyError)): r.validate_case(tmp_path, name, record, retired, f)


def test_flat_digest_archive_detects_mapping_and_blob_tampering(tmp_path):
    source = tmp_path / "source"; source.mkdir(); (source / "a").write_bytes(b"same"); (source / "b").write_bytes(b"same")
    hashes = {name: r.sha(source/name) for name in ("a", "b")}
    destination = tmp_path / "archive"; result = r.shared().stage_archive(source, destination, hashes)
    assert result["logical_files"] == 2 and result["unique_blobs"] == 1
    blob = next((destination/"blobs").iterdir()); blob.write_bytes(b"bad")
    with pytest.raises(ValueError): r.shared().validate_archive(destination, hashes)


@pytest.mark.parametrize("change", ("child_nonzero", "protected_changed", "archive_corrupt"))
def test_failed_run_retains_actual_child_exit_and_all_protection_errors(tmp_path, monkeypatch, capsys, change):
    # Synthetic CPU child object only: Popen never launches a real process.
    monkeypatch.setattr(r, "ROOT", tmp_path)
    monkeypatch.setattr(r, "OUT", tmp_path / "synthetic-output")
    monkeypatch.setattr(r, "ACTIVATION", tmp_path / "build/evidence/native-pass-30/activation.json")
    monkeypatch.setattr(r, "HANDOFF", tmp_path / "build/evidence/native-pass-30-build-handoff-1/result.json")
    r.OUT.mkdir(); path = tmp_path / "protected.txt"; path.write_bytes(b"immutable")
    hashes = {"protected.txt": r.sha(path)}
    archive = r.shared().stage_archive(tmp_path, r.OUT / "protected-inputs", hashes)
    recipe = dict(activation_sha256="a"*64, build_handoff_sha256="b"*64)
    a = dict(activated={"_dawn.cp312-win_amd64.pyd": "c"*64})
    identity = {"synthetic_CPU_only": True}
    monkeypatch.setattr(r, "protect_inputs", lambda *args: (recipe, a, {}, hashes, identity, r.CPU_NAMES))
    write(r.OUT / "inputs.json", dict(wrapper_sha256=r.sha(r.__file__), protected_hashes=hashes, identity=identity,
        argv=r.child_command(), environment=r.child_environment(recipe, a), expected_CPU_deselections=list(r.CPU_NAMES), protected_archive=archive))
    class CPUChild:
        pid = 999
        def wait(self):
            if change == "protected_changed": path.write_bytes(b"changed")
            if change == "archive_corrupt": next((r.OUT/"protected-inputs/blobs").iterdir()).write_bytes(b"corrupt")
            return 7
        def poll(self): return 7
    calls = []
    def fake_popen(argv, **kwargs): calls.append(argv); return CPUChild()
    monkeypatch.setattr(r.subprocess, "Popen", fake_popen)
    assert r.run(tmp_path/"synthetic-recipe.json", "d"*64) == 1
    captured = capsys.readouterr()
    assert '"child_pid": 999' in captured.out  # Synthetic CPU double only.
    terminal = r.read(r.OUT/"terminal.json")
    assert terminal["child_exit"] == 7 and terminal["child_terminal"] is True and terminal["status"].startswith("failed")
    phases = {error["phase"] for error in terminal["errors"]}
    assert {"child", "XML", "raw_hardware"} <= phases
    if change == "protected_changed": assert "protected_after" in phases and not terminal["protected_inputs_unchanged"]
    if change == "archive_corrupt": assert "protected_archive" in phases
    assert len(calls) == 1 and (r.OUT/"child-process.json").is_file()


@pytest.mark.parametrize("key,value", (("status", "success"), ("ownership_retired", False), ("submission_count", 0), ("presented", True)))
def test_lost_receipt_cannot_claim_success_or_unsubmitted_work(key, value):
    row = dict(status="device_lost", ownership_closed=True, ownership_retired=True, submission_count=1,
               presented=False, frame_scope="qt_paint", paint_token=9)
    good = dict(raw_completion_batches=[[row]], loss_terminal=row)
    r.receipts(good, success=False)
    wrong = {**row, key: value}
    with pytest.raises(ValueError): r.receipts(dict(raw_completion_batches=[[wrong]], loss_terminal=wrong), success=False)


def capture_context():
    original = r.read(ROOT / r.AUTHORING_PATH)
    supplemental = dict(original_authoring_sha256=r.AUTHORING_SHA,
        sources_sha256={r.TEST: r.CAPTURE_TEST_SHA}, gpu_case_ids=list(r.NODEIDS), cpu_cases=17,
        expected_arrays=deepcopy(original["expected_arrays"]), contract=deepcopy(original["contract"]),
        prior_failed_hardware_seen=True)
    terminal = dict(process_exit=0, GPU_used=False, authoring_sha256=r.CAPTURE_AUTHORING_SHA)
    return original, supplemental, terminal


@pytest.mark.parametrize("change", ("original_seen", "original_gpu", "original_pin", "supplement_source",
    "old_nodes", "cpu_drop", "cpu_bool", "expected_pixel", "criteria", "nonterminal", "bool_exit", "gpu", "terminal_pin"))
def test_capture_supplement_cannot_replace_criteria_or_admit_unexecuted_cpu(change):
    original, supplemental, terminal = capture_context()
    r.validate_capture_context(original, supplemental, terminal)
    if change == "original_seen": original["candidate_seen"] = True
    elif change == "original_gpu": original["GPU_used"] = True
    elif change == "original_pin": supplemental["original_authoring_sha256"] = "a" * 64
    elif change == "supplement_source": supplemental["sources_sha256"][r.TEST] = r.ORIGINAL_TEST_SHA
    elif change == "old_nodes": supplemental["gpu_case_ids"] = list(r.ORIGINAL_NODEIDS)
    elif change == "cpu_drop": supplemental["cpu_cases"] = 16
    elif change == "cpu_bool": supplemental["cpu_cases"] = True
    elif change == "expected_pixel": next(iter(supplemental["expected_arrays"].values()))["sha256"] = "a" * 64
    elif change == "criteria": supplemental["contract"]["comparison"] = "landmarks only"
    elif change == "nonterminal": terminal["process_exit"] = 1
    elif change == "bool_exit": terminal["process_exit"] = False
    elif change == "gpu": terminal["GPU_used"] = True
    else: terminal["authoring_sha256"] = "a" * 64
    with pytest.raises(ValueError): r.validate_capture_context(original, supplemental, terminal)
    assert "vispy._dawn" not in sys.modules


def test_supplemental_source_changes_only_capture_and_one_cpu_contract():
    assert r.sha(ROOT / r.ORIGINAL_TEST) == r.ORIGINAL_TEST_SHA
    assert r.sha(ROOT / r.TEST) == r.CAPTURE_TEST_SHA
    original = ast.parse((ROOT / r.ORIGINAL_TEST).read_text())
    captured = ast.parse((ROOT / r.TEST).read_text())
    def definitions(tree):
        return {node.name: ast.dump(node, include_attributes=False)
            for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    before, after = definitions(original), definitions(captured)
    assert set(after) - set(before) == {"test_cpu_full_target_capture_ignores_shifted_draw_viewport"}
    assert not set(before) - set(after)
    assert {name for name in before if before[name] != after[name]} == {"_capture"}
    assignments_before = [ast.dump(node, include_attributes=False) for node in original.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))]
    assignments_after = [ast.dump(node, include_attributes=False) for node in captured.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))]
    assert assignments_before == assignments_after  # AUTHORING is original5.
    supplement = r.read(ROOT / r.CAPTURE_AUTHORING_PATH)
    terminal = r.read(ROOT / r.CAPTURE_AUTHORING_PATH.replace("authoring.json", "terminal.json"))
    r.validate_capture_context(r.read(ROOT / r.AUTHORING_PATH), supplement, terminal)


@pytest.mark.parametrize("change", ("one_pixel", "viewport_crop"))
def test_full_array_capture_still_rejects_one_wrong_pixel_and_viewport_crop(tmp_path, analytic, change):
    _, f = analytic
    expected = np.zeros((24, 48, 4), np.uint8); expected[..., 3] = 255
    actual = expected.copy()
    np.save(tmp_path / "phase.npy", actual); np.save(tmp_path / "phase-expected.npy", expected)
    records = {"images": {"phase": {"actual": f.array_record(actual), "expected": f.array_record(expected)}}}
    r.validate_image(tmp_path, "phase", expected, records, f)
    if change == "one_pixel": actual[9, 30, 1] = 1
    else: actual = actual[3:]
    np.save(tmp_path / "phase.npy", actual)
    with pytest.raises(ValueError): r.validate_image(tmp_path, "phase", expected, records, f)


def test_missing_actual_capture_recipe_refuses_before_output_or_child(monkeypatch):
    assert not r.RECIPE.exists() and not r.OUT.exists()
    protected = {str(path): r.sha(path) for path in (ROOT / r.PARENT_RUNNER_PATH,
        ROOT / r.ORIGINAL_TEST, ROOT / r.AUTHORING_PATH, r.ACTIVATION, r.HANDOFF)}
    monkeypatch.setattr(r.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("No child may launch"))
    with pytest.raises(FileNotFoundError):
        r.freeze(r.RECIPE, "a" * 64)
    assert not r.RECIPE.exists() and not r.OUT.exists() and "vispy._dawn" not in sys.modules
    assert all(r.sha(Path(name)) == checksum for name, checksum in protected.items())
