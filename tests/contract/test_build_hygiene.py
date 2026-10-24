"""Cleanup must preserve evidence and refuse unsafe filesystem changes.

These tests use disposable fake workspaces, never project build assets.
"""
# SPDX-License-Identifier: AGPL-3.0-only

import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


TOOL = Path(os.environ.get("VISPY_BUILD_HYGIENE_TEST_TOOL", "")) if os.environ.get(
    "VISPY_BUILD_HYGIENE_TEST_TOOL") else Path(__file__).resolve().parents[2] / "tools/build_hygiene.py"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def load_tool():
    spec = importlib.util.spec_from_file_location("build_hygiene_contract", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    scratch = root / "build/work/run-1"
    root.mkdir()
    retained = []
    for role in ("source", "evidence", "licenses", "repro"):
        path = root / "retained" / (role + ".txt")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes((role + " must survive").encode())
        retained.append({"path": path.relative_to(root).as_posix(),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "roles": [role]})
    manifest = {"schema": 1, "run_id": "run-1", "owner": "contract-test",
                "state": "succeeded", "process_exit": 0, "child_waited": True,
                "scratch_root": "build/work/run-1", "retained": retained}
    obj = SimpleNamespace(root=root, scratch=scratch, manifest=manifest,
                          manifest_path=root / "retained/manifest.json",
                          plan=root / "retained/cleanup-plan.json",
                          policy=root / "policy.json", registry=root / "registry.json")
    write_json(obj.policy, {"schema": 1, "max_scratch_bytes": 20 * 1024**3,
                            "min_free_bytes": 0})
    write_json(obj.registry, {"schema": 1, "protected_roots": [],
                              "blocked_roots": [], "legacy_roots": []})
    invoke(obj, "preflight", "--run-id", "run-1", "--owner", "contract-test",
           "--expected-peak-bytes", "1024", "--register")
    (scratch / "object.bin").write_bytes(b"disposable object")
    (scratch / "nested").mkdir()
    (scratch / "nested/result.tmp").write_bytes(b"disposable output")
    write_json(obj.manifest_path, obj.manifest)
    return obj


def invoke(ws, *args, expected=0, registry=True):
    command = [sys.executable, "-I", "-B", str(TOOL),
               "--workspace", str(ws.root), "--policy", str(ws.policy)]
    if registry:
        command.extend(["--registry", str(ws.registry)])
    result = subprocess.run([*command, *map(str, args)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def plan(ws, expected=0):
    write_json(ws.manifest_path, ws.manifest)
    return invoke(ws, "plan", "--manifest", ws.manifest_path,
                  "--output", ws.plan, expected=expected)


def retained_bytes(ws):
    return {row["path"]: (ws.root / row["path"]).read_bytes()
            for row in ws.manifest["retained"]}


@pytest.mark.parametrize("state,code", [("succeeded", 0), ("failed", 7), ("cancelled", 130)])
def test_cleanup_removes_only_terminal_owned_scratch(workspace, state, code):
    ws = workspace
    ws.manifest.update(state=state, process_exit=code)
    before = retained_bytes(ws)
    sibling = ws.scratch.parent / "other-run"
    sibling.mkdir()
    (sibling / "keep.bin").write_bytes(b"another owner")
    plan(ws)
    assert ws.scratch.exists(), "Planning must not delete files"
    invoke(ws, "apply", "--plan", ws.plan)
    assert not ws.scratch.exists()
    assert retained_bytes(ws) == before
    assert (sibling / "keep.bin").read_bytes() == b"another owner"
    assert ws.manifest_path.exists() and ws.plan.exists()


def test_audit_is_read_only(workspace):
    ws = workspace
    before = {p.relative_to(ws.root): p.read_bytes()
              for p in ws.root.rglob("*") if p.is_file()}
    audit = json.loads(invoke(ws, "audit").stdout)
    assert audit["status"] == "PASS_AUDIT"
    assert audit["managed_runs"][0]["disposable"] is False
    assert {p.relative_to(ws.root): p.read_bytes()
            for p in ws.root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("change", ["not-awaited", "running", "live-child", "bad-exit"])
def test_unfinished_or_live_work_is_never_cleaned(workspace, change):
    ws = workspace
    if change == "not-awaited":
        ws.manifest["child_waited"] = False
    elif change == "running":
        ws.manifest["state"] = "running"
    elif change == "live-child":
        ws.manifest["child_pid"] = os.getpid()
    else:
        ws.manifest["process_exit"] = None
    plan(ws, expected=2)
    assert (ws.scratch / "object.bin").read_bytes() == b"disposable object"


@pytest.mark.parametrize("kind", ["protected_roots", "blocked_roots"])
@pytest.mark.parametrize("relation", ["ancestor", "exact", "descendant"])
@pytest.mark.parametrize("when", ["plan", "apply"])
def test_protected_or_blocked_overlap_refuses_cleanup(workspace, kind, relation, when):
    ws = workspace
    if when == "apply":
        plan(ws)
    target = {"ancestor": "build/work", "exact": "build/work/run-1",
              "descendant": "build/work/run-1/nested"}[relation]
    registry = {"schema": 1, "protected_roots": [], "blocked_roots": [], "legacy_roots": []}
    registry[kind] = [target]
    write_json(ws.registry, registry)
    if when == "plan":
        plan(ws, expected=2)
    else:
        invoke(ws, "apply", "--plan", ws.plan, expected=2)
    assert (ws.scratch / "nested/result.tmp").exists()


@pytest.mark.parametrize("change", ["content", "added-file", "removed-file", "added-directory"])
def test_changed_scratch_refuses_apply_without_deleting_survivors(workspace, change):
    ws = workspace
    plan(ws)
    if change == "content":
        (ws.scratch / "object.bin").write_bytes(b"changed after approval")
    elif change == "added-file":
        (ws.scratch / "unexpected.bin").write_bytes(b"new work")
    elif change == "removed-file":
        (ws.scratch / "object.bin").unlink()
    else:
        (ws.scratch / "new-empty-directory").mkdir()
    before = {p.relative_to(ws.scratch): p.read_bytes()
              for p in ws.scratch.rglob("*") if p.is_file()}
    invoke(ws, "apply", "--plan", ws.plan, expected=2)
    assert {p.relative_to(ws.scratch): p.read_bytes()
            for p in ws.scratch.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("when", ["plan", "apply"])
@pytest.mark.parametrize("change", ["missing", "hash-changed"])
def test_retained_evidence_must_still_match(workspace, when, change):
    ws = workspace
    if when == "apply":
        plan(ws)
    evidence = ws.root / "retained/evidence.txt"
    if change == "missing":
        evidence.unlink()
    else:
        evidence.write_bytes(b"different evidence")
    if when == "plan":
        plan(ws, expected=2)
    else:
        invoke(ws, "apply", "--plan", ws.plan, expected=2)
    assert (ws.scratch / "object.bin").exists()


@pytest.mark.parametrize("role", ["source", "evidence", "licenses", "repro"])
def test_failed_reproduction_and_required_provenance_cannot_be_omitted(workspace, role):
    ws = workspace
    ws.manifest.update(state="failed", process_exit=1)
    ws.manifest["retained"] = [r for r in ws.manifest["retained"] if role not in r["roles"]]
    plan(ws, expected=2)
    assert ws.scratch.exists()


def test_retained_input_cannot_live_inside_deleted_scratch(workspace):
    ws = workspace
    ws.manifest["retained"][0]["path"] = "build/work/run-1/object.bin"
    ws.manifest["retained"][0]["sha256"] = hashlib.sha256(
        (ws.scratch / "object.bin").read_bytes()).hexdigest()
    plan(ws, expected=2)
    assert ws.scratch.exists()


def test_different_manifest_owner_cannot_claim_registered_run(workspace):
    ws = workspace
    ws.manifest["owner"] = "another-agent"
    plan(ws, expected=2)
    assert (ws.scratch / "object.bin").exists()


def test_manifest_changed_after_plan_cannot_authorize_deletion(workspace):
    ws = workspace
    plan(ws)
    ws.manifest["owner"] = "changed-after-plan"
    write_json(ws.manifest_path, ws.manifest)
    invoke(ws, "apply", "--plan", ws.plan, expected=2)
    assert (ws.scratch / "object.bin").exists()


@pytest.mark.parametrize("scratch_root", ["build", "build/work", "retained", "../outside"])
def test_manifest_cannot_expand_owned_scratch_boundary(workspace, scratch_root):
    ws = workspace
    ws.manifest["scratch_root"] = scratch_root
    plan(ws, expected=2)
    assert (ws.scratch / "object.bin").exists()
    assert (ws.root / "retained/evidence.txt").exists()


def test_existing_unregistered_directory_cannot_be_adopted(workspace):
    ws = workspace
    other = ws.scratch.parent / "unregistered"
    other.mkdir()
    (other / "keep.bin").write_bytes(b"unmanaged")
    invoke(ws, "preflight", "--run-id", "unregistered", "--owner", "contract-test",
           "--expected-peak-bytes", "1", "--register", expected=2)
    assert (other / "keep.bin").read_bytes() == b"unmanaged"


def test_preflight_without_registration_does_not_create_scratch(workspace):
    ws = workspace
    invoke(ws, "preflight", "--run-id", "future-run", "--owner", "contract-test",
           "--expected-peak-bytes", "1")
    assert not (ws.scratch.parent / "future-run").exists()


def test_no_force_override_can_bypass_blocked_history(workspace):
    ws = workspace
    write_json(ws.registry, {"schema": 1, "protected_roots": [],
                              "blocked_roots": ["build/work/run-1"], "legacy_roots": []})
    invoke(ws, "plan", "--manifest", ws.manifest_path, "--output", ws.plan,
           "--force", expected=2)
    assert (ws.scratch / "object.bin").exists()


@pytest.mark.parametrize("target", ["scratch-child", "scratch-root"])
@pytest.mark.parametrize("link_kind", ["junction"] if os.name == "nt" else ["symlink"])
def test_reparse_links_are_not_followed_or_deleted(workspace, tmp_path, target, link_kind):
    ws = workspace
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious.bin").write_bytes(b"outside ownership")
    link = ws.scratch / "linked" if target == "scratch-child" else ws.scratch
    if target == "scratch-root":
        (ws.scratch / ".build-hygiene-owner.json").unlink()
        (ws.scratch / "object.bin").unlink()
        (ws.scratch / "nested/result.tmp").unlink()
        (ws.scratch / "nested").rmdir()
        ws.scratch.rmdir()
    if link_kind == "junction":
        created = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                                 capture_output=True, text=True, timeout=10)
        assert created.returncode == 0, created.stdout + created.stderr
    else:
        link.symlink_to(outside, target_is_directory=True)
    plan(ws, expected=2)
    if link_kind == "junction":
        assert link.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    else:
        assert link.is_symlink()
    assert (outside / "precious.bin").read_bytes() == b"outside ownership"


def test_disk_reserve_refuses_preflight_without_large_allocation(workspace, monkeypatch, capsys):
    ws = workspace
    module = load_tool()
    write_json(ws.policy, {"schema": 1, "max_scratch_bytes": 20 * 1024**3,
                           "min_free_bytes": 10 * 1024**3})
    monkeypatch.setattr(module.shutil, "disk_usage", lambda path: SimpleNamespace(
        total=100 * 1024**3, used=91 * 1024**3, free=9 * 1024**3))
    assert module.main(["--workspace", str(ws.root), "--policy", str(ws.policy),
                        "--registry", str(ws.registry), "preflight", "--run-id", "run-1",
                        "--owner", "contract-test", "--expected-peak-bytes", "1"]) == 2
    assert (ws.scratch / "object.bin").exists()
    capsys.readouterr()


def test_preflight_rejects_peak_over_policy_budget(workspace):
    ws = workspace
    invoke(ws, "preflight", "--run-id", "run-1", "--owner", "contract-test",
           "--expected-peak-bytes", str(20 * 1024**3 + 1), expected=2)
    assert ws.scratch.exists()


@pytest.mark.parametrize("secondary_free,expected", [(149, 2), (1000, 0)],
                         ids=["secondary-reserve-refusal", "all-capacity-roots-pass"])
def test_preflight_checks_other_capacity_roots_before_registration(
        workspace, tmp_path, monkeypatch, capsys, secondary_free, expected):
    ws = workspace
    secondary = tmp_path / "separate-capacity-root"
    secondary.mkdir()
    write_json(ws.registry, {"schema": 1, "protected_roots": [], "blocked_roots": [],
                              "legacy_roots": [], "capacity_roots": [str(secondary)]})
    write_json(ws.policy, {"schema": 1, "max_scratch_bytes": 20 * 1024**3,
                           "min_free_bytes": 100})
    module = load_tool()
    checked = []

    def capacity(path):
        path = Path(path).resolve()
        checked.append(path)
        free = secondary_free if path == secondary.resolve() else 1000
        return SimpleNamespace(total=2000, used=2000 - free, free=free)

    monkeypatch.setattr(module.shutil, "disk_usage", capacity)
    assert module.main(["--workspace", str(ws.root), "--policy", str(ws.policy),
                        "--registry", str(ws.registry), "preflight", "--run-id", "new-run",
                        "--owner", "contract-test", "--expected-peak-bytes", "50",
                        "--register"]) == expected
    result = json.loads(capsys.readouterr().out)
    assert ws.root.resolve() in checked and secondary.resolve() in checked
    reports = {Path(row["path"]).resolve(): row for row in result["capacity_checks"]}
    assert reports[ws.root.resolve()]["free_bytes"] == 1000
    assert reports[secondary.resolve()]["free_bytes"] == secondary_free
    assert reports[secondary.resolve()]["min_free_bytes"] == 100
    assert reports[secondary.resolve()]["expected_peak_bytes"] == 50
    new_scratch = ws.scratch.parent / "new-run"
    if expected:
        assert not new_scratch.exists(), "Capacity refusal must precede registration writes"
    else:
        assert (new_scratch / ".build-hygiene-owner.json").is_file()
    assert (ws.scratch / "object.bin").read_bytes() == b"disposable object"


def test_registration_marker_cannot_exceed_positive_scratch_budget(workspace):
    ws = workspace
    # A separate empty managed area makes the one-byte limit a marker-overhead
    # boundary, rather than a refusal caused by a previously populated run.
    isolated = ws.root / "isolated"
    isolated.mkdir()
    ws.root = isolated
    write_json(ws.policy, {"schema": 1, "max_scratch_bytes": 1, "min_free_bytes": 0})
    invoke(ws, "preflight", "--run-id", "tiny-run", "--owner", "contract-test",
           "--expected-peak-bytes", "1", "--register", expected=2)
    assert not (isolated / "build/work/tiny-run").exists()


@pytest.mark.parametrize("metadata", ["retained-source", "terminal-manifest", "plan-output", "plan-input"])
def test_permanent_metadata_in_sibling_scratch_cannot_authorize_cleanup(workspace, metadata):
    ws = workspace
    sibling = ws.scratch.parent / "sibling-run"
    sibling.mkdir()
    if metadata == "retained-source":
        original = ws.root / ws.manifest["retained"][0]["path"]
        retained = sibling / "source.txt"
        retained.write_bytes(original.read_bytes())
        ws.manifest["retained"][0]["path"] = retained.relative_to(ws.root).as_posix()
    elif metadata == "terminal-manifest":
        ws.manifest_path = sibling / "manifest.json"
    elif metadata == "plan-output":
        ws.plan = sibling / "plan.json"
    else:
        plan(ws)
        copied = sibling / "copied-plan.json"
        copied.write_bytes(ws.plan.read_bytes())
        invoke(ws, "apply", "--plan", copied, expected=2)
    if metadata != "plan-input":
        plan(ws, expected=2)
    assert (ws.scratch / "object.bin").read_bytes() == b"disposable object"
    assert (ws.scratch / "nested/result.tmp").read_bytes() == b"disposable output"
    assert (ws.root / "retained/evidence.txt").read_bytes() == b"evidence must survive"
    assert sibling.is_dir()


def test_omitted_registry_honors_default_blocked_cleanup_history(workspace):
    ws = workspace
    default = ws.root / "build/.hygiene/registry.json"
    write_json(default, {"schema": 1, "protected_roots": [],
                         "blocked_roots": ["build/work/run-1"], "legacy_roots": ["build/.hygiene"]})
    result = invoke(ws, "plan", "--manifest", ws.manifest_path, "--output", ws.plan,
                    expected=2, registry=False)
    assert "blocked" in result.stdout.lower()
    assert (ws.scratch / "object.bin").read_bytes() == b"disposable object"
    assert (ws.scratch / "nested/result.tmp").exists()
    assert not ws.plan.exists()
