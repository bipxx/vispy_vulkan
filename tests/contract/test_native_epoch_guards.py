"""Future native epochs cannot overwrite history or borrow another ABI cache."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("native_epoch_contract", ROOT / "tools/native_epoch.py")
epoch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(epoch)


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    return path


def dump(root, name, value):
    return write(root, name, json.dumps(value, sort_keys=True))


def retained(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def seal(root, record):
    path = dump(root, "compat/native-epochs/ownership.json", record)
    return path.relative_to(root).as_posix(), epoch.sha(path)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    write(root, "build/evidence/native-pass-24/status.json", "historical proof")
    write(root, "build/evidence/native-pass-25/status.json", "historical proof")
    write(root, "build/w11/source/cpp/old.cpp", "historical source")
    write(root, "build/native-pass25-sdk/old.obj", "historical ABI object")
    activated = {}
    for name in ("_dawn.cp312-win_amd64.pyd", "_sdf_cpu.cp312-win_amd64.pyd", "VkLayer_vispy_submit.dll", "VkLayer_vispy_submit.json"):
        prefix = "src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/"
        activated[name] = epoch.sha(write(root, prefix + name, "active pass25 " + name))
    activation = dump(root, "build/evidence/native-pass-25/activation.json", {"activated": activated})
    executable = write(root, "prepared/python.exe", "prepared interpreter")
    cfg = write(root, "prepared/pyvenv.cfg", "prepared configuration")
    cmake = write(root, "prepared/cmake.exe", "prepared CMake")
    ctest = write(root, "prepared/ctest.exe", "prepared CTest")
    requirements = write(root, "compat/build-requirements.txt", "hash locked requirements")
    prepared = {"abi": "cp312", "interpreter_pin": "3.12.8", "free_threaded": False,
                "planned_architecture": "x64", "planned_configuration": "Release", "environment": str(executable.parent),
                "expected_native_module": "_dawn.cp312-win_amd64.pyd", "expected_sdf_module": "_sdf_cpu.cp312-win_amd64.pyd",
                "installed_environment": {"executable": str(executable), "executable_sha256": epoch.sha(executable),
                    "base_executable": str(executable), "base_executable_sha256": epoch.sha(executable),
                    "pyvenv_cfg_sha256": epoch.sha(cfg), "python": "3.12.8", "pointer_bytes": 8, "modules": []},
                "requirements": "compat/build-requirements.txt", "requirements_sha256": epoch.sha(requirements),
                "cmake": {"origin": str(cmake), "sha256": epoch.sha(cmake)},
                "toolchain": {"generator_toolset": "v143,version=14.44.35207", "windows_sdk": "10.0.22621.0"}}
    prep_path = dump(root, "compat/preparation.json", prepared)
    sdk_path = dump(root, "build/native-sdk/windows-x64-release-3/manifest.json", {"producer": {
        "msvc_mutex_policy": "msvc-stl-init-in-situ-v1", "cxx_flags": "/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR",
        "release_flags": "/O2 /Ob2 /DNDEBUG"}})
    # SDK byte/configuration policy and source-tree checks have independent real
    # contracts; these fixtures exercise ownership/path/cache orchestration.
    write(root, "cmake/native_sdk.py", "def verify(*args):\n    return {}\n")
    monkeypatch.setattr(epoch, "check_dependencies", lambda *args: None)
    for name in ("CMakeLists.txt", "CMakePresets.json", "pyproject.toml", "uv.lock", "cmake/dependencies.lock.json",
                 "cmake/verify_dependencies.py", "cpp/runtime.cpp", "src/vispy/__init__.py"):
        write(root, name, "sealed project " + name)
    packets, harness = [], {}
    for owner, native, contract in (("ordinary", "cpp/runtime_point.hpp", "tests/markers/point_contract.cpp"),
                                    ("texture", "cpp/runtime_texture.hpp", "tests/textures/texture_contract.cpp")):
        archive = "build/" + owner + "-cpu"
        owned = {}
        for name in (native, contract):
            data = "tested " + owner + " " + name
            write(root, name, data)
            archive_name = "source/" + name
            write(root, archive + "/" + archive_name, data)
            owned[name] = archive_name
        dump(root, archive + "/result.json", {"compile_exit": 0, "run_exit": 0})
        write(root, archive + "/tested.exe", "CPU proof executable")
        write(root, archive + "/dataset/input.vert", "matched input shader")
        files = epoch.inventory(root / archive)
        packets.append({"name": owner, "sealed": True, "archive": archive, "files": files,
                        "files_tree_sha256": epoch.tree_digest(files), "owned_files": owned,
                        "source_tree_sha256": epoch.tree_digest({name: files[origin] for name, origin in owned.items()}),
                        "proof_file": "result.json", "proof_assertions": {"compile_exit": 0, "run_exit": 0}})
        for name, origin in owned.items():
            harness[name] = {"path": archive + "/" + origin, "sha256": files[origin]}
        harness["datasets/" + owner + "/input.vert"] = {"path": archive + "/dataset/input.vert", "sha256": files["dataset/input.vert"]}
    harness["cpp/runtime.cpp"] = {"path": "cpp/runtime.cpp", "sha256": epoch.sha(root / "cpp/runtime.cpp")}
    tools = {name: epoch.sha(write(root, name, (ROOT / name).read_bytes())) for name in epoch.TOOLS}
    record = {"schema": 1, "sealed": True, "epoch": 26, "snapshot_epoch": 12,
              "paths": {"snapshot": "build/w12/source", "evidence": "build/evidence/native-pass-26",
                  "harness": "build/evidence/native-pass-26/harness", "build": "build/native-pass26-sdk",
                  "sdk": "build/native-sdk/windows-x64-release-3", "preparation": "compat/preparation.json",
                  "activation": "build/evidence/native-pass-25/activation.json"},
              "activation_manifest_sha256": epoch.sha(activation), "protected_native": epoch.native_inventory(root),
              "preparation_sha256": epoch.sha(prep_path), "ctest_sha256": epoch.sha(ctest),
              "sdk_manifest_sha256": epoch.sha(sdk_path), "source_files": epoch.project_inventory(root),
              "harness_inputs": harness, "packets": packets, "tool_files": tools,
              "targets": sorted(epoch.REQUIRED_TARGETS), "ctest_expected_names": ["point_contract", "texture_contract"],
              "sdk_tint_reader_enabled": False}
    return root, record, prepared


def reject_unchanged(root, call, match):
    before = retained(root)
    with pytest.raises(epoch.EpochError, match=match):
        call()
    assert retained(root) == before


def freeze_fixture(root, record, monkeypatch):
    monkeypatch.setattr(epoch, "link_dependencies", lambda *args: None)
    manifest, approved = seal(root, record)
    result = epoch.freeze(root, manifest, approved)
    return manifest, approved, result["frozen_inputs_sha256"]


def test_prefreeze_is_read_only_and_requires_both_sealed_owners(packet):
    root, record, _ = packet
    manifest, approved = seal(root, record)
    before = retained(root)
    result = epoch.freeze(root, manifest, approved, preflight_only=True)
    assert result["preflight"] == "passed_read_only"
    assert result["epoch"] == 26
    assert retained(root) == before
    record["packets"][1]["sealed"] = False
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "unsealed")


@pytest.mark.parametrize("key,value", [("snapshot", "build/w11/source"), ("evidence", "build/evidence/native-pass-25"),
                                        ("harness", "build/evidence/native-pass-25/harness"), ("build", "build/native-pass25-sdk")])
def test_historical_paths_rejected_before_writes(packet, key, value):
    root, record, _ = packet
    record["paths"][key] = value
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "Noncanonical")


@pytest.mark.parametrize("field,value", [("epoch", 25), ("snapshot_epoch", 11)])
def test_historical_namespace_cannot_be_redeclared(packet, field, value):
    root, record, _ = packet
    record[field] = value
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "Historical")


@pytest.mark.parametrize("key", ["snapshot", "evidence", "build"])
def test_existing_initial_destinations_are_never_reused(packet, key):
    root, record, _ = packet
    write(root, record["paths"][key] + "/retained.bin", "existing failed attempt")
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "must be new")


def test_deleted_lower_epoch_cannot_repurpose_historical_namespace(packet):
    root, record, _ = packet
    write(root, "build/w13/source/retained.cpp", "newer source")
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "must advance")


@pytest.mark.parametrize("relative", ["cpp/runtime_point.hpp", "cpp/runtime_texture.hpp", "tests/markers/point_contract.cpp",
                                     "build/ordinary-cpu/tested.exe", "build/texture-cpu/dataset/input.vert",
                                     "src/vispy/_dawn.cp312-win_amd64.pyd", "build/evidence/native-pass-25/activation.json",
                                     "prepared/ctest.exe", "tools/build_native_epoch.py"])
def test_changed_sealed_inputs_are_rejected_without_outputs(packet, relative):
    root, record, _ = packet
    manifest, approved = seal(root, record)
    write(root, relative, "changed sealed bytes")
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "changed|differs")


def test_external_manifest_pin_rejects_consistent_rewrite(packet):
    root, record, _ = packet
    manifest, approved = seal(root, record)
    write(root, "cpp/runtime.cpp", "rewritten source")
    record["source_files"]["cpp/runtime.cpp"] = epoch.sha(root / "cpp/runtime.cpp")
    seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "Approved ownership manifest changed")


def test_harness_source_must_match_project_and_cpu_packets(packet):
    root, record, _ = packet
    record["harness_inputs"]["cpp/runtime_point.hpp"] = record["harness_inputs"]["cpp/runtime_texture.hpp"]
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "Matching native harness source")


def test_failed_cpu_exit_cannot_be_declared_as_a_successful_packet(packet):
    root, record, _ = packet
    packet_record = record["packets"][1]
    proof = dump(root, packet_record["archive"] + "/result.json", {"compile_exit": 0, "run_exit": 1})
    packet_record["files"]["result.json"] = epoch.sha(proof)
    packet_record["files_tree_sha256"] = epoch.tree_digest(packet_record["files"])
    packet_record["proof_assertions"]["run_exit"] = 1
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "successful exit")


def test_vendor_build_target_is_rejected(packet):
    root, record, _ = packet
    record["targets"].append("webgpu_dawn")
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "vendor targets")


@pytest.mark.parametrize("name", ["CL", "_CL_", "CFLAGS", "CXXFLAGS", "CMAKE_TOOLCHAIN_FILE"])
def test_unrecorded_ambient_compiler_overrides_are_rejected(packet, monkeypatch, name):
    root, record, _ = packet
    manifest, approved = seal(root, record)
    monkeypatch.setenv(name, "/U_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR")
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "Ambient build flags")


def test_future_destination_junction_cannot_redirect_to_history(packet):
    root, record, _ = packet
    target = root / "build/native-pass25-sdk"
    alias = root / record["paths"]["build"]
    if os.name == "nt":
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        process = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                  "New-Item -ItemType Junction -Path " + quote(alias) + " -Target " + quote(target) + " | Out-Null"],
                                 capture_output=True, check=False)
        assert process.returncode == 0
    else:
        alias.symlink_to(target, target_is_directory=True)
    manifest, approved = seal(root, record)
    reject_unchanged(root, lambda: epoch.freeze(root, manifest, approved), "filesystem alias|reparse")


def test_isolated_synthetic_freeze_archives_all_proofs_and_build_preflight_ignores_new_live_epoch(packet, monkeypatch):
    root, record, _ = packet
    manifest, approved, frozen = freeze_fixture(root, record, monkeypatch)
    write(root, "cpp/runtime_point.hpp", "later live source epoch")
    before = retained(root)
    result = epoch.build(root, manifest, approved, frozen, preflight_only=True)
    assert result["owner"]["epoch"] == 26
    assert result["protected_native"] == record["protected_native"]
    assert retained(root) == before
    for item in record["packets"]:
        epoch.verify_inventory(root / record["paths"]["evidence"] / "sealed-packets" / item["name"], item["files"])
    epoch.verify_inventory(root / record["paths"]["evidence"] / "guard-tools", record["tool_files"])


def test_archived_guard_bytes_are_pinned_before_build(packet, monkeypatch):
    root, record, _ = packet
    manifest, approved, frozen = freeze_fixture(root, record, monkeypatch)
    write(root, record["paths"]["evidence"] + "/guard-tools/tools/native_epoch.py", "changed historical guard")
    reject_unchanged(root, lambda: epoch.build(root, manifest, approved, frozen), "Sealed file changed")


@pytest.mark.parametrize("name", ["status.json", "configure.log", "initial-attempt.json"])
def test_initial_build_cannot_overwrite_attempt_outputs(packet, monkeypatch, name):
    root, record, _ = packet
    manifest, approved, frozen = freeze_fixture(root, record, monkeypatch)
    write(root, record["paths"]["evidence"] + "/" + name, "prior failed attempt")
    reject_unchanged(root, lambda: epoch.build(root, manifest, approved, frozen), "outputs already exist")


def configured_fixture(root, record, prepared, monkeypatch):
    manifest, approved, frozen = freeze_fixture(root, record, monkeypatch)
    checked = epoch.preflight_build(root, manifest, approved, frozen)
    paths, owner = checked["paths"], checked["owner"]
    dump(root, record["paths"]["evidence"] + "/cache-owner.json", owner)
    values, files = epoch.cache_settings(paths, prepared, record)
    data = "\n".join(f"{name}:STRING={value}" for name, value in {**values, **files}.items()) + "\n"
    cache = write(root, record["paths"]["build"] + "/CMakeCache.txt", data)
    dump(root, record["paths"]["evidence"] + "/cache-state.json", {"owner": owner, "cache_sha256": epoch.sha(cache)})
    return manifest, approved, frozen, paths, owner


def test_resume_requires_exact_cache_and_fresh_attempt(packet, monkeypatch):
    root, record, prepared = packet
    manifest, approved, frozen, paths, _ = configured_fixture(root, record, prepared, monkeypatch)
    before = retained(root)
    result = epoch.build(root, manifest, approved, frozen, resume=True, attempt="retry-1", preflight_only=True)
    assert result["attempt_root"].endswith("attempts\\retry-1") or result["attempt_root"].endswith("attempts/retry-1")
    assert retained(root) == before
    write(root, record["paths"]["evidence"] + "/attempts/retry-1/build.log", "retained retry")
    reject_unchanged(root, lambda: epoch.build(root, manifest, approved, frozen, resume=True, attempt="retry-1"), "already exists")


@pytest.mark.parametrize("setting,value", [("VISPY_INPLACE", "ON"), ("VISPY_LEGACY_MSVC_CRT_MUTEX", "OFF"),
                                         ("VISPY_VERIFY_DEPENDENCIES", "OFF"), ("Python_EXECUTABLE", "historical/python.exe"),
                                         ("VISPY_CONTRACT_TESTS_ROOT", "build/evidence/native-pass-25/harness/tests"),
                                         ("CMAKE_CXX_FLAGS", "/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR /D_ITERATOR_DEBUG_LEVEL=2"),
                                         ("CMAKE_CXX_FLAGS_RELEASE", "/Od /DNDEBUG")])
def test_resealed_wrong_cache_policy_or_origin_is_still_rejected(packet, monkeypatch, setting, value):
    root, record, prepared = packet
    manifest, approved, frozen, paths, owner = configured_fixture(root, record, prepared, monkeypatch)
    cache = paths["build"] / "CMakeCache.txt"
    lines = [f"{setting}:STRING={value}" if line.startswith(setting + ":") else line for line in cache.read_text().splitlines()]
    cache.write_text("\n".join(lines) + "\n")
    dump(root, record["paths"]["evidence"] + "/cache-state.json", {"owner": owner, "cache_sha256": epoch.sha(cache)})
    reject_unchanged(root, lambda: epoch.build(root, manifest, approved, frozen, resume=True, attempt="retry"), "cache setting|cache path")


def test_resume_rejects_another_epoch_owner_and_concurrent_build(packet, monkeypatch):
    root, record, prepared = packet
    manifest, approved, frozen, paths, owner = configured_fixture(root, record, prepared, monkeypatch)
    owner["epoch"] = 25
    dump(root, record["paths"]["evidence"] + "/cache-owner.json", owner)
    reject_unchanged(root, lambda: epoch.build(root, manifest, approved, frozen, resume=True, attempt="retry"), "ownership differs")
    write(root, record["paths"]["evidence"] + "/active-build.json", "another live build")
    reject_unchanged(root, lambda: epoch.build(root, manifest, approved, frozen, resume=True, attempt="retry"), "already owns")


def fake_builder(root, record, prepared, monkeypatch, *, mutate_protected=False):
    """Exercise output/ownership policy with fake commands, never a compiler."""
    calls = []
    paths = epoch.paths_for(root, record)
    monkeypatch.setattr(epoch, "attest_projects", lambda *args: {"synthetic_test": True})

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["CL_MPCount"] == "3"
        if "-S" in command:
            values, files = epoch.cache_settings(paths, prepared, record)
            write(root, record["paths"]["build"] + "/CMakeCache.txt",
                  "\n".join(f"{key}:STRING={value}" for key, value in {**values, **files}.items()))
        elif "--build" in command:
            for name in (prepared["expected_native_module"], prepared["expected_sdf_module"], "VkLayer_vispy_submit.dll", "point_contract.exe"):
                write(root, record["paths"]["build"] + "/Release/" + name, "synthetic native output")
            write(root, record["paths"]["build"] + "/generated/VkLayer_vispy_submit.json", "synthetic manifest")
            if mutate_protected:
                write(root, "src/vispy/_dawn.cp312-win_amd64.pyd", "unexpected native mutation")
        elif "--output-junit" in command:
            output = Path(command[command.index("--output-junit") + 1])
            output.write_text('<testsuite tests="2" failures="0" skipped="0">'
                              '<testcase name="point_contract" status="run"/>'
                              '<testcase name="texture_contract" status="run"/></testsuite>')
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(epoch.subprocess, "run", run)
    return calls


def test_build_scopes_job_flags_and_records_success_only_after_protected_checks(packet, monkeypatch):
    root, record, prepared = packet
    manifest, approved, frozen = freeze_fixture(root, record, monkeypatch)
    monkeypatch.setenv("CL_MPCount", "99")
    calls = fake_builder(root, record, prepared, monkeypatch)
    before = epoch.native_inventory(root)
    result = epoch.build(root, manifest, approved, frozen)
    assert result["status"] == "build_and_ctest_passed"
    assert os.environ["CL_MPCount"] == "99"
    assert epoch.native_inventory(root) == before
    assert any("/p:CL_MPCount=3" in command for command in calls)
    assert not (root / record["paths"]["evidence"] / "active-build.json").exists()
    status = epoch.load(root / record["paths"]["evidence"] / "status.json")
    assert status["in_place_copy"] is False and status["gpu_qualified"] is False


def test_protected_mutation_prevents_a_success_record_and_retains_failure_artifacts(packet, monkeypatch):
    root, record, prepared = packet
    manifest, approved, frozen = freeze_fixture(root, record, monkeypatch)
    fake_builder(root, record, prepared, monkeypatch, mutate_protected=True)
    with pytest.raises(epoch.EpochError, match="Protected source native bytes"):
        epoch.build(root, manifest, approved, frozen)
    out = root / record["paths"]["evidence"]
    assert (out / "build.log").is_file()
    assert (out / "protected-source-binaries-after.json").is_file()
    assert not (out / "status.json").exists()
    assert not (out / "active-build.json").exists()


@pytest.mark.parametrize("case", ["missing", "skipped", "failed", "duplicate"])
def test_ctest_green_requires_exact_executed_inventory(tmp_path, case):
    children = '<testcase name="point_contract" status="run"/>'
    if case == "skipped":
        children += '<testcase name="texture_contract"><skipped/></testcase>'
    elif case == "failed":
        children += '<testcase name="texture_contract"><failure/></testcase>'
    elif case == "duplicate":
        children += '<testcase name="point_contract" status="run"/>'
    path = write(tmp_path, "ctest.xml", '<testsuite>' + children + '</testsuite>')
    with pytest.raises(epoch.EpochError, match="CTest"):
        epoch.check_ctest(path, ["point_contract", "texture_contract"])


@pytest.mark.parametrize("tool", ["freeze_native_epoch.py", "build_native_epoch.py"])
def test_actual_entrypoints_without_explicit_ownership_cannot_mutate_history(tool):
    history = ROOT / "build/evidence/native-pass-25"
    before = retained(history)
    native_before = epoch.native_inventory(ROOT)
    process = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / tool)],
                             capture_output=True, encoding="utf-8", errors="replace", check=False)
    assert process.returncode == 2
    assert "--ownership-manifest" in process.stderr
    assert retained(history) == before
    assert epoch.native_inventory(ROOT) == native_before


def test_actual_freeze_rejects_old_pass25_manifest_without_mutation():
    before = retained(ROOT / "build/evidence/native-pass-25")
    native_before = epoch.native_inventory(ROOT)
    path = ROOT / "build/evidence/native-pass-25/frozen-inputs.json"
    process = subprocess.run([sys.executable, "-B", str(ROOT / "tools/freeze_native_epoch.py"),
                              "--ownership-manifest", path.relative_to(ROOT).as_posix(), "--ownership-sha256", epoch.sha(path)],
                             capture_output=True, encoding="utf-8", errors="replace", check=False)
    assert process.returncode == 2
    assert "sealed schema1" in process.stderr
    assert retained(ROOT / "build/evidence/native-pass-25") == before
    assert epoch.native_inventory(ROOT) == native_before
