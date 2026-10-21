"""CPU-only guards for the five unchanged current30 requalifications."""
import ast
import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"
sys.path.insert(0, str(BUILD))
import native_pass_30_requalification as guard

PAIRS = (
    ("gpu", "run_native_pass_29_gpu_1.py", "run_native_pass_30_gpu_1.py"),
    ("ordinary", "run_native_pass_29_ordinary_1.py", "run_native_pass_30_ordinary_1.py"),
    ("numeric", "run_native_pass_29_texture_numeric_1.py", "run_native_pass_30_texture_numeric_1.py"),
    ("paint", "run_native_pass_29_paint_1.py", "run_native_pass_30_paint_1.py"),
    ("oversized", "run_native_pass_29_ordinary_oversized_3.py", "run_native_pass_30_ordinary_oversized_1.py"),
)


def load(name):
    spec = importlib.util.spec_from_file_location("cpu_requal_" + name[:-3], BUILD / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def forbid_native_and_hardware(monkeypatch):
    old_create = importlib.machinery.ExtensionFileLoader.create_module
    old_exec = importlib.machinery.ExtensionFileLoader.exec_module
    def create(loader, spec):
        if loader.name.startswith(("vispy._dawn", "vispy.visuals.text._sdf_cpu")):
            raise AssertionError("CPU proof attempted native extension import")
        return old_create(loader, spec)
    def execute(loader, module):
        if loader.name.startswith(("vispy._dawn", "vispy.visuals.text._sdf_cpu")):
            raise AssertionError("CPU proof attempted native extension execution")
        return old_exec(loader, module)
    monkeypatch.setattr(importlib.machinery.ExtensionFileLoader, "create_module", create)
    monkeypatch.setattr(importlib.machinery.ExtensionFileLoader, "exec_module", execute)
    yield
    assert "vispy._dawn" not in sys.modules


@pytest.fixture(scope="module")
def context():
    epoch = guard.ACTIVATION.parent
    return [guard.read(p) for p in (guard.ACTIVATION, guard.HANDOFF, guard.MANIFEST,
                                  epoch / "frozen-inputs.json", epoch / "status.json")]


def test_actual_context_is_current30_without_native_import(context):
    guard.validate_context(*context)
    hashes = guard.protect_inputs()
    assert len(hashes) >= 584 * 2 + 1051 + 16
    assert hashes["build/evidence/native-pass-30/activation.json"] == guard.ACTIVATION_SHA


MUTATIONS = (
    (0, "epoch", 29), (0, "epoch", True),
    (1, "status", "building"), (1, "process_exit", None), (1, "process_exit", False),
    (1, "in_place_copy", True), (1, "gpu_qualified", True),
    (1, "sdk_private_tint_reader_enabled", True), (4, "sdk_tint_reader_enabled", True),
    (0, "native_source_tree_sha256", "0" * 64),
    (1, "harness_tree_sha256", "0" * 64), (2, "sdk_manifest_sha256", "0" * 64),
    (0, "ownership_manifest_sha256", "0" * 64), (0, "build_handoff_sha256", "0" * 64),
    (1, "ctest_executed_count", 15), (1, "source_files_verified", 583),
    (1, "harness_files_verified", 651), (2, "snapshot_epoch", 15),
)


@pytest.mark.parametrize("which,key,value", MUTATIONS)
def test_context_rejects_nonmatching_or_nonterminal_proof(context, which, key, value):
    values = copy.deepcopy(context)
    values[which][key] = value
    with pytest.raises(ValueError):
        guard.validate_context(*values)


@pytest.mark.parametrize("kind", ("native", "proof", "source", "harness", "ctest", "paths"))
def test_inventory_substitution_is_rejected(context, kind):
    values = copy.deepcopy(context)
    a, h, m, f, _ = values
    if kind == "native":
        a["activated"]["_dawn.cp312-win_amd64.pyd"] = "0" * 64
    elif kind == "proof":
        a["proof_input_hashes"]["ctest.xml"] = "0" * 64
    elif kind == "source":
        f["source_files"]["cpp/runtime.cpp"] = "0" * 64
    elif kind == "harness":
        name = next(iter(f["harness_files"]))
        f["harness_files"][name] = "0" * 64
    elif kind == "ctest":
        h["ctest_expected_names"][-1] = h["ctest_expected_names"][0]
    else:
        m["paths"]["snapshot"] = "build/w15/source"
    with pytest.raises(ValueError):
        guard.validate_context(*values)


@pytest.mark.parametrize("path", (guard.ACTIVATION, guard.HANDOFF, guard.MANIFEST,
    guard.ACTIVATION.parent / "ctest.xml", ROOT / "cpp/runtime.cpp",
    ROOT / "src/vispy/_dawn.cp312-win_amd64.pyd"))
def test_real_preflight_rejects_tampered_bytes_before_any_output(monkeypatch, path):
    original = guard.sha
    monkeypatch.setattr(guard, "sha", lambda p: "0" * 64 if Path(p).resolve() == path.resolve() else original(p))
    with pytest.raises(ValueError):
        guard.protect_inputs()


@pytest.mark.parametrize("bad", ("", "../x", "a/../x", "C:/x", "C:x", "\\server\\x", "/x", "a\\x", "a//x", "./x"))
def test_logical_protected_paths_cannot_alias_or_escape(tmp_path, bad):
    with pytest.raises(ValueError):
        guard.member(tmp_path, bad)


def xml_document(path, count):
    root = ET.Element("testsuites", tests=str(count), failures="0", errors="0", skipped="0")
    suite = ET.SubElement(root, "testsuite", tests=str(count), failures="0", errors="0", skipped="0")
    expected = [("held.criteria", "case-" + str(n)) for n in range(count)]
    for classname, name in expected:
        ET.SubElement(suite, "testcase", classname=classname, name=name)
    ET.ElementTree(root).write(path, encoding="utf-8")
    return root, suite, expected


@pytest.mark.parametrize("kind", ("root-failure", "root-skip", "root-count", "root-error-tag", "suite-error", "case-skip", "case-disabled", "case-failures-flag", "case-errors-flag", "nested-disabled", "case-incomplete", "duplicate", "drop", "wrong-id", "nested-suite", "nested-suites", "wrapped-case"))
def test_strict_xml_rejects_aggregate_and_concrete_omissions(tmp_path, kind):
    path = tmp_path / "result.xml"
    root, suite, expected = xml_document(path, 16)
    if kind == "root-failure": root.set("failures", "1")
    elif kind == "root-skip": root.set("skipped", "1")
    elif kind == "root-count": root.set("tests", "15")
    elif kind == "root-error-tag": ET.SubElement(root, "error")
    elif kind == "suite-error": suite.set("errors", "1")
    elif kind == "case-skip": ET.SubElement(suite[0], "skipped")
    elif kind == "case-disabled": suite[0].set("disabled", "true")
    elif kind == "case-failures-flag": suite[0].set("failures", "1")
    elif kind == "case-errors-flag": suite[0].set("errors", "1")
    elif kind == "nested-disabled": ET.SubElement(suite[0], "disabled")
    elif kind == "case-incomplete": suite[0].set("result", "incomplete")
    elif kind == "duplicate": suite[1].set("name", suite[0].get("name"))
    elif kind == "drop": suite.remove(suite[-1]); suite.set("tests", "15")
    elif kind == "wrong-id": suite[0].set("name", "different")
    elif kind == "nested-suite": ET.SubElement(suite[0], "testsuite", tests="0")
    elif kind == "nested-suites": ET.SubElement(suite[0], "testsuites")
    else: ET.SubElement(ET.SubElement(suite, "wrapper"), "testcase", classname="hidden", name="hidden")
    ET.ElementTree(root).write(path, encoding="utf-8")
    with pytest.raises(ValueError):
        guard.validate_xml(path, expected)


@pytest.mark.parametrize("kind,count", (("gpu", 109), ("ordinary", 17)))
def test_exact_original_xml_count_and_root_failure_are_preserved(tmp_path, kind, count):
    name = next(new for key, _, new in PAIRS if key == kind)
    module = load(name)
    path = tmp_path / "result.xml"
    root, _, expected = xml_document(path, count)
    validate = module.validate_pytest_xml if kind == "gpu" else module.validate_xml
    assert validate(path, expected)["executed"] == count
    root.set("failures", "1")
    ET.ElementTree(root).write(path, encoding="utf-8")
    with pytest.raises(ValueError): validate(path, expected)


@pytest.mark.parametrize("kind,old,new", PAIRS)
def test_selection_criteria_and_historical_template_identity_unchanged(kind, old, new):
    before, after = load(old), load(new)
    assert after.PARENT_TEMPLATE == BUILD / old
    assert after.PARENT_TEMPLATE_SHA == guard.sha(BUILD / old)
    assert after.ACTIVATION == guard.ACTIVATION
    if hasattr(after, "HANDOFF"): assert after.HANDOFF == guard.HANDOFF
    assert after.OUT if hasattr(after, "OUT") else after.OUTPUT
    out = after.OUT if hasattr(after, "OUT") else after.OUTPUT
    assert "pass30" in out.name or "pass-30" in out.name
    assert not out.exists()
    for key in ("SELECTED", "NODEIDS", "EXPECTED_IDS", "OWNED", "CPU_NAMES", "GPU_NAMES", "CASES", "PHASES", "AUTHORING_SHA"):
        if hasattr(before, key): assert getattr(after, key) == getattr(before, key), key


def function_ast(filename, name):
    node = next(n for n in ast.parse((BUILD / filename).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name)
    class NormalizeEpoch(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == "_exact30_guard": node.id = "_exact29_guard"
            return node
        def visit_Constant(self, node):
            if node.value == 30: return ast.copy_location(ast.Constant(29), node)
            if isinstance(node.value, str):
                node.value = node.value.replace("actual30", "actual29").replace("pass30", "pass29").replace("native30", "native29")
            return node
    return ast.dump(NormalizeEpoch().visit(node), include_attributes=False)


UNCHANGED_VALIDATORS = (
    ("ordinary", "validate_selection"), ("ordinary", "validate_artifacts"),
    ("numeric", "retained_cases_valid"), ("paint", "retained_capture_errors"),
    ("paint", "validate_paint_xml"), ("oversized", "validate_selection"),
    ("oversized", "validate_raw"),
)


@pytest.mark.parametrize("kind,function", UNCHANGED_VALIDATORS)
def test_raw_and_selection_validators_preserve_original_semantics(kind, function):
    _, before, after = next(row for row in PAIRS if row[0] == kind)
    assert function_ast(before, function) == function_ast(after, function)


@pytest.mark.parametrize("kind,old,new", PAIRS)
def test_stale_template_rejected_before_selection_native_or_output(monkeypatch, kind, old, new):
    module = load(new)
    original = guard.sha
    monkeypatch.setattr(guard, "sha", lambda p: "0" * 64 if Path(p) == BUILD / old else original(p))
    with pytest.raises(ValueError): module.current_inputs()
    out = module.OUT if hasattr(module, "OUT") else module.OUTPUT
    assert not out.exists()


@pytest.mark.parametrize("kind,old,new", PAIRS)
def test_cpu_preflight_is_explicit_and_stops_before_candidate_output(monkeypatch, capsys, kind, old, new):
    module = load(new)
    def forbidden(*args, **kwargs): raise AssertionError("CPU dry-run launched child")
    monkeypatch.setattr(module.subprocess, "run", forbidden)
    monkeypatch.setattr(module.subprocess, "Popen", forbidden)
    if kind == "gpu":
        monkeypatch.setattr(module, "guard_epoch30", lambda *a: {})
        monkeypatch.setattr(module, "preflight", lambda *a: ({}, {}, [()] * 109, {}, ROOT / "a"))
        args = ["--preflight", "--activation-sha256", guard.ACTIVATION_SHA, "--build-handoff-sha256", guard.HANDOFF_SHA]
    elif kind == "ordinary":
        monkeypatch.setattr(module, "preflight", lambda *a: ({}, [()] * 17, {}, {}, {}))
        args = ["--preflight", "--activation-sha256", guard.ACTIVATION_SHA]
    else:
        monkeypatch.setattr(module, "protected_inputs" if kind != "oversized" else "protect_inputs", lambda *a: ({}, {}) if kind != "oversized" else ({}, {}, {}, {}))
        args = ["--preflight", "--expected-activation-sha256", guard.ACTIVATION_SHA]
        if kind != "paint": args += ["--expected-native-build-handoff-sha256", guard.HANDOFF_SHA]
        if kind == "numeric": args += ["--expected-authoring-sha256", module.AUTHORING_SHA]
    monkeypatch.setattr(sys, "argv", [str(BUILD / new), *args])
    assert module.main() == 0
    assert json.loads(capsys.readouterr().out)["CPU_only"] is True
    out = module.OUT if hasattr(module, "OUT") else module.OUTPUT
    assert not out.exists()


@pytest.mark.parametrize("kind", ("paint", "numeric", "oversized"))
def test_child_provenance_failure_precedes_native_import(monkeypatch, kind):
    module = load(next(new for key, _, new in PAIRS if key == kind))
    def reject(): raise ValueError("provenance denied before native")
    monkeypatch.setattr(module, "current_inputs", reject)
    with pytest.raises(ValueError, match="provenance denied"):
        module.pytest_sessionstart(None)


def test_numeric_epoch_only_rebinding_cannot_accept_29_or_substituted_path():
    module = load("run_native_pass_30_texture_numeric_1.py")
    module._validate_numeric29_header(guard.ACTIVATION, guard.ACTIVATION_SHA, guard.ACTIVATION_SHA, {"epoch": 30})
    for path, epoch in ((ROOT / "build/evidence/native-pass-29/activation.json", 30), (guard.ACTIVATION, 29)):
        with pytest.raises(RuntimeError):
            module._validate_numeric29_header(path, guard.ACTIVATION_SHA, guard.ACTIVATION_SHA, {"epoch": epoch})


def test_numeric_xml_real_consumer_accepts_exact_twelve_and_rejects_case_error(tmp_path):
    module = load("run_native_pass_30_texture_numeric_1.py")
    path = tmp_path / "numeric.xml"
    root, suite, _ = xml_document(path, 12)
    for row, nodeid in zip(suite, module.NODEIDS):
        row.set("classname", module.TEST[:-3].replace("/", "."))
        row.set("name", nodeid.split("::", 1)[1])
    ET.ElementTree(root).write(path, encoding="utf-8")
    assert module.validate_numeric_xml(path) == {"tests": 12, "errors": 0, "failures": 0, "skipped": 0}
    suite[0].set("errors", "1")
    ET.ElementTree(root).write(path, encoding="utf-8")
    with pytest.raises(ValueError): module.validate_numeric_xml(path)


def test_flat_archive_rejects_tampering_without_nested_source_path(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a").write_bytes(b"same")
    (source / "b").write_bytes(b"same")
    hashes = {name: guard.sha(source / name) for name in ("a", "b")}
    destination = tmp_path / "archive"
    summary = guard.stage_archive(source, destination, hashes)
    assert summary["logical_files"] == 2 and summary["unique_blobs"] == 1
    (destination / "blobs" / (hashes["a"] + ".bin")).write_bytes(b"corrupt")
    with pytest.raises(ValueError): guard.validate_archive(destination, hashes)


def test_oversized_raw_fixture_loads_from_an_unrelated_working_directory(monkeypatch, tmp_path):
    module = load("run_native_pass_30_ordinary_oversized_1.py")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [str(BUILD)] + [p for p in sys.path if Path(p or ".").resolve() != ROOT])
    fixture = module.load_analytic_fixture()
    assert fixture.contract() == guard.read(module.AUTHORING)["contract"]


def test_historical_cpp_context_is_not_substituted_by_working30_sources():
    module = load("run_native_pass_30_ordinary_oversized_1.py")
    authored = guard.read(module.AUTHORING)
    name = "cpp/runtime.cpp"
    checksum = authored["CPP_context_sha256"][name]
    path = module.frozen_context_path(name, checksum, {}, {})
    assert path.is_relative_to(ROOT / "build/w15/source")
    assert guard.sha(path) == checksum and checksum != guard.sha(ROOT / name)


def test_child_environment_removes_inherited_import_and_pytest_overrides():
    env = guard.child_environment({"PATH": "safe", "PYTHONHOME": "other", "pythonpath": "other", "PYTEST_ADDOPTS": "--maxfail=1", "PYTHONOPTIMIZE": "2"}, {"PYTHONPATH": "exact"})
    assert env["PYTHONPATH"] == "exact" and env["PATH"] == "safe"
    assert not any(k.lower() in ("pythonhome", "pythonoptimize", "pytest_addopts") for k in env)
    assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"


@pytest.mark.parametrize("activation,handoff", (("0" * 64, guard.HANDOFF_SHA),
    ("1fe711e39d9c5e5537ef153a5054e37fee3da83299a2533e7221b1c2e679934e", guard.HANDOFF_SHA),
    (guard.ACTIVATION_SHA, "0" * 64),
    (guard.ACTIVATION_SHA, "8d4ffcb272d578cfae686e61f12162ba16b9428b0af8b3a4e6929f2a22372ff1")))
def test_explicit_coordinator_pins_cannot_rebind_another_epoch(activation, handoff):
    with pytest.raises(ValueError): guard.protect_inputs(activation, handoff)


@pytest.mark.parametrize("key,value", (("native_sha256", "0" * 64), ("native_origin", "C:/other/_dawn.pyd"), ("vispy_origin", "C:/other/__init__.py"), ("python", "C:/other/python.exe"), ("pytest_exit", 1)))
def test_broad_native_witness_cannot_be_presence_only(tmp_path, key, value):
    module = load("run_native_pass_30_gpu_1.py")
    row = {"native_origin": str(ROOT / "src/vispy/_dawn.cp312-win_amd64.pyd"), "native_sha256": guard.NATIVE_PINS["_dawn.cp312-win_amd64.pyd"], "vispy_origin": str(ROOT / "src/vispy/__init__.py"), "python": str(ROOT / ".venv/Scripts/python.exe"), "pytest_exit": 0, "probe": {}, "device": {"ok": True, "software": False, "backend": "Vulkan"}}
    path = tmp_path / "native.json"
    path.write_text(json.dumps(row))
    module.validate_native_witness(path)
    row[key] = value
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError): module.validate_native_witness(path)
