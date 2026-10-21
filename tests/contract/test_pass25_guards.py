"""Pass25 rejection paths must leave prior evidence and protected files intact."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pass25_guard_contract", ROOT / "tools/pass25_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    return path


def dump(root, name, record):
    return write(root, name, json.dumps(record, sort_keys=True))


def inventory(root):
    return {path.relative_to(root).as_posix(): guard.sha(path)
            for path in root.rglob("*") if path.is_file()}


def current_native_snapshot(root):
    """Compare actual current native bytes without approving any activation.

    Historical pass25 build/resume still checks the exact pass24 baseline.
    These rejection tests must also remain meaningful after a new activation.
    """
    native = root / "src/vispy"
    return {path.relative_to(root).as_posix(): guard.sha(path)
            for path in native.rglob("*") if path.is_file()
            and (path.suffix.lower() in {".pyd", ".dll", ".so", ".dylib"}
                 or path.name == "VkLayer_vispy_submit.json")}


def packet_preflight(root, supplied=None, **kwargs):
    # These fixtures explicitly approve their own synthetic immutable record;
    # the actual CLI requires the separate, operator-reviewed freeze digest.
    kwargs.setdefault("expected_frozen_sha256", guard.sha(root / guard.PATHS["evidence"] / "frozen-inputs.json"))
    return guard.preflight(root, supplied, **kwargs)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    """Small synthetic packet; the CLI tests retain the genuine immutable pins."""
    root = tmp_path / "workspace"
    root.mkdir()
    paths = {key: root / value for key, value in guard.PATHS.items()}
    history = write(root, "build/evidence/native-pass-24/retained-status.json", "old proof")
    write(root, "build/w9/source/retained.cpp", "old source")
    write(root, "build/native-pass24-sdk/retained.obj", "old ABI object")
    worker_sources = {}
    for index in range(12):
        name = f"cpp/owned{index}.cpp" if index < 9 else f"tests/shaders/owned{index}.cpp"
        path = write(paths["worker"], "source/" + name, f"tested {index}")
        worker_sources[name] = guard.sha(path)
    write(paths["worker"], "datasets/points/a.vert", "tested point shader")
    write(paths["worker"], "point-contract.exe", "tested binary")
    evidence = dump(paths["worker"], "evidence.json", {"scope": "synthetic CPU fixture", "exit": 0})
    source_list = [{"file": name, "sha256": checksum} for name, checksum in sorted(worker_sources.items())]
    source_sha = hashlib.sha256(json.dumps(source_list, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    worker_inventory = inventory(paths["worker"])
    hash_file = dump(paths["worker"], "hashes.json", {
        "source": source_list, "source_identity_sha256": source_sha,
        "files": [{"file": name, "sha256": checksum} for name, checksum in sorted(worker_inventory.items())]})
    monkeypatch.setattr(guard, "WORKER_HASH_SHA", guard.sha(hash_file))
    monkeypatch.setattr(guard, "WORKER_EVIDENCE_SHA", guard.sha(evidence))
    monkeypatch.setattr(guard, "WORKER_SOURCE_SHA", source_sha)
    activated = {}
    for name in ("_dawn.cp312-win_amd64.pyd", "_sdf_cpu.cp312-win_amd64.pyd",
                 "VkLayer_vispy_submit.dll", "VkLayer_vispy_submit.json"):
        prefix = "src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/"
        activated[name] = guard.sha(write(root, prefix + name, "protected " + name))
    activation = dump(root, guard.PATHS["activation"], {"activated": activated})
    monkeypatch.setattr(guard, "ACTIVATION_SHA", guard.sha(activation))
    executable = write(root, "prepared/python.exe", "synthetic interpreter")
    cfg = write(root, "prepared/pyvenv.cfg", "synthetic interpreter configuration")
    cmake = write(root, "prepared/cmake.exe", "synthetic CMake")
    module = write(root, "prepared/build-module.py", "synthetic build module")
    requirements = write(root, "compat/requirements.txt", "synthetic hashed dependencies")
    preparation = {
        "abi": "cp312", "interpreter_pin": "3.12.8", "planned_architecture": "x64",
        "planned_configuration": "Release", "environment": str(executable.parent),
        "cmake": {"origin": str(cmake), "sha256": guard.sha(cmake)},
        "installed_environment": {"executable": str(executable), "executable_sha256": guard.sha(executable),
            "base_executable": str(executable), "base_executable_sha256": guard.sha(executable),
            "pyvenv_cfg_sha256": guard.sha(cfg), "modules": [
                {"name": "synthetic", "origin": str(module), "sha256": guard.sha(module)}]},
        "requirements": "compat/requirements.txt", "requirements_sha256": guard.sha(requirements),
        "toolchain": {"generator_toolset": "v143,version=14.44.35207", "windows_sdk": "10.0.22621.0"}}
    preparation_file = dump(root, guard.PATHS["preparation"], preparation)
    monkeypatch.setattr(guard, "PREPARATION_SHA", guard.sha(preparation_file))
    sdk_manifest = dump(paths["sdk"], "manifest.json", {"producer": {"synthetic": True}})
    monkeypatch.setattr(guard, "SDK_SHA", guard.sha(sdk_manifest))
    # SDK policy/relocation/tamper validation has its separate real SDK contracts.
    write(root, "cmake/native_sdk.py", "def verify(*args):\n    return {'synthetic': True}\n")
    source_files = {}
    for name in ("CMakeLists.txt", "CMakePresets.json", "pyproject.toml", "uv.lock", "cmake/dependencies.lock.json"):
        source_files[name] = guard.sha(write(paths["snapshot"], name, "synthetic source " + name))
    for name in worker_sources:
        if name.startswith("cpp/"):
            shutil.copyfile(paths["worker"] / "source" / name,
                            write(paths["snapshot"], name, b""))
            source_files[name] = worker_sources[name]
    dump(paths["snapshot"], "wheel-source-manifest.json", {"snapshot": str(paths["snapshot"]),
        "source_files": source_files, "source_tree_sha256": guard.tree_digest(source_files)})
    shutil.copytree(paths["worker"] / "source", paths["harness"])
    write(paths["harness"], "datasets/point-corpus/a.vert", "tested point shader")
    shutil.copytree(paths["worker"], paths["evidence"] / "full-source-tint-proof")
    tools = {name: guard.sha(write(root, name, "synthetic frozen tool " + name)) for name in (
        "tools/pass25_guard.py", "tools/freeze_pass25_inputs.py", "tools/build_pass25_sdk.ps1")}
    harness_files = inventory(paths["harness"])
    frozen = {"schema": 2, "source_snapshot": str(paths["snapshot"]), "harness_root": str(paths["harness"]),
        "source_tree_sha256": guard.tree_digest(source_files), "harness_files": harness_files,
        "harness_tree_sha256": guard.tree_digest(harness_files), "worker_verified_sha256": worker_sources,
        "worker_source_identity_sha256": source_sha, "worker_hash_manifest_sha256": guard.WORKER_HASH_SHA,
        "worker_evidence_sha256": guard.WORKER_EVIDENCE_SHA, "activation_manifest_sha256": guard.ACTIVATION_SHA,
        "guard_tools_sha256": tools, "protected_native_before": guard.protected(root),
        "protected_native_after": guard.protected(root)}
    dump(paths["evidence"], "frozen-inputs.json", frozen)
    return root, paths, preparation, frozen, history


def reject_unchanged(root, call, match):
    before = inventory(root)
    with pytest.raises(guard.GuardError, match=match):
        call()
    assert inventory(root) == before


def test_valid_preflight_is_read_only(packet):
    root, paths, _, _, _ = packet
    before = inventory(root)
    result = packet_preflight(root)
    assert result["preflight"] == "passed_read_only"
    assert result["paths"]["evidence"] == str(paths["evidence"])
    assert inventory(root) == before


@pytest.mark.parametrize("key,value", [
    ("evidence", "build/evidence/native-pass-24"), ("snapshot", "build/w9/source"),
    ("build", "build/native-pass24-sdk"), ("harness", "build/evidence/native-pass-24/harness"),
    ("sdk", "build/native-sdk/windows-x64-release-2"), ("preparation", "compat/cp310-candidate/preparation.json")])
def test_historical_or_other_packet_paths_rejected_before_writes(packet, key, value):
    root, _, _, _, _ = packet
    reject_unchanged(root, lambda: packet_preflight(root, {key: value}), "Noncanonical")


@pytest.mark.parametrize("output", ["status.json", "configure.log", "build-script.ps1", "protected-source-binaries-before.json"])
def test_initial_outputs_cannot_be_overwritten(packet, output):
    root, paths, _, _, _ = packet
    write(paths["evidence"], output, "existing failed attempt")
    reject_unchanged(root, lambda: packet_preflight(root), "outputs already exist")


@pytest.mark.parametrize("field,value", [("source_snapshot", "build/w9/source"),
                                         ("harness_root", "build/evidence/native-pass-24/harness")])
def test_frozen_metadata_cannot_redirect_reads_to_historical_inputs(packet, field, value):
    root, paths, _, frozen, _ = packet
    frozen[field] = str(root / value)
    dump(paths["evidence"], "frozen-inputs.json", frozen)
    reject_unchanged(root, lambda: packet_preflight(root), "Noncanonical")


@pytest.mark.parametrize("relative", ["source/cpp/owned0.cpp", "point-contract.exe", "datasets/points/a.vert", "evidence.json"])
def test_full_archived_worker_proof_is_checked_before_writes(packet, relative):
    root, paths, _, _, _ = packet
    write(paths["evidence"] / "full-source-tint-proof", relative, "changed archive")
    reject_unchanged(root, lambda: packet_preflight(root), "changed|checksum")


def test_untracked_source_and_changed_matching_dataset_rejected(packet):
    root, paths, _, _, _ = packet
    extra = write(paths["snapshot"], "cpp/untracked.cpp", "untracked source")
    reject_unchanged(root, lambda: packet_preflight(root), "source inventory")
    extra.unlink()
    write(paths["harness"], "datasets/point-corpus/a.vert", "changed shader")
    reject_unchanged(root, lambda: packet_preflight(root), "checksum")


def test_protected_artifact_and_activation_manifest_checked_before_writes(packet):
    root, _, _, _, _ = packet
    write(root, "src/vispy/_dawn.cp312-win_amd64.pyd", "changed active ABI leaf")
    reject_unchanged(root, lambda: packet_preflight(root), "Activated pass24 artifact changed")


def test_current_native_snapshot_accepts_new_bytes_without_relaxing_the_pass24_pin(packet):
    root, _, _, _, _ = packet
    historical = current_native_snapshot(root)
    write(root, "src/vispy/_dawn.cp312-win_amd64.pyd", "new separately activated renderer")
    current = current_native_snapshot(root)
    assert set(current) == set(historical)
    assert current["src/vispy/_dawn.cp312-win_amd64.pyd"] != historical["src/vispy/_dawn.cp312-win_amd64.pyd"]
    reject_unchanged(root, lambda: packet_preflight(root), "Activated pass24 artifact changed")
    assert current_native_snapshot(root) == current


def test_approved_freeze_digest_rejects_consistently_rewritten_source_manifest(packet):
    root, paths, _, frozen, _ = packet
    approved = guard.sha(paths["evidence"] / "frozen-inputs.json")
    source = guard.load(paths["snapshot"] / "wheel-source-manifest.json")
    source["source_files"]["CMakeLists.txt"] = guard.sha(write(paths["snapshot"], "CMakeLists.txt", "different consistent source"))
    source["source_tree_sha256"] = guard.tree_digest(source["source_files"])
    frozen["source_tree_sha256"] = source["source_tree_sha256"]
    dump(paths["snapshot"], "wheel-source-manifest.json", source)
    dump(paths["evidence"], "frozen-inputs.json", frozen)
    reject_unchanged(root, lambda: guard.preflight(root, expected_frozen_sha256=approved), "Approved frozen-inputs identity")


def test_build_cannot_infer_approval_from_the_mutable_freeze_record(packet):
    root, _, _, _, _ = packet
    reject_unchanged(root, lambda: guard.preflight(root), "approved frozen-inputs SHA256 is required")


@pytest.mark.parametrize("relative,reason", [
    ("tools/build_pass25_sdk.ps1", "Frozen guard tool changed"),
    (guard.PATHS["sdk"] + "/manifest.json", "Unexpected SDK3 manifest"),
    (guard.PATHS["activation"], "Activated pass24 manifest changed"),
    (guard.PATHS["preparation"], "preparation identity changed")])
def test_build_policy_or_protected_identity_tampering_rejected_before_writes(packet, relative, reason):
    root, _, _, _, _ = packet
    write(root, relative, "changed identity")
    reject_unchanged(root, lambda: packet_preflight(root), reason)


def test_canonical_build_path_cannot_be_a_junction_to_a_historical_cache(packet):
    root, paths, _, _, _ = packet
    target = root / "build/native-pass24-sdk"
    historical_before = inventory(target)
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    pwsh = shutil.which("pwsh")
    assert pwsh
    command = f"New-Item -ItemType Junction -Path {quote(paths['build'])} -Target {quote(target)} | Out-Null"
    subprocess.run([pwsh, "-NoProfile", "-Command", command], check=True, capture_output=True)
    try:
        reject_unchanged(root, lambda: packet_preflight(root), "Noncanonical pass25 build")
        assert inventory(target) == historical_before
    finally:
        # Remove only the newly created test junction; never its target.
        subprocess.run([pwsh, "-NoProfile", "-Command", f"Remove-Item -LiteralPath {quote(paths['build'])}"],
                       check=True, capture_output=True)


def seed_resume(packet):
    root, paths, preparation, _, _ = packet
    identity = packet_preflight(root)["owner"]
    cache = {
        "CMAKE_HOME_DIRECTORY": str(paths["snapshot"]), "CMAKE_CACHEFILE_DIR": str(paths["build"]),
        "VISPY_NATIVE_SDK": str(paths["sdk"]), "VISPY_CONTRACT_TESTS_ROOT": str(paths["harness"] / "tests"),
        "VISPY_CONTRACT_DATASETS_ROOT": str(paths["harness"] / "datasets"),
        "Python_EXECUTABLE": preparation["installed_environment"]["executable"],
        "Python3_EXECUTABLE": preparation["installed_environment"]["executable"],
        "CMAKE_COMMAND": preparation["cmake"]["origin"], "CMAKE_GENERATOR": "Visual Studio 17 2022",
        "CMAKE_GENERATOR_PLATFORM": "x64", "CMAKE_GENERATOR_TOOLSET": preparation["toolchain"]["generator_toolset"],
        "CMAKE_SYSTEM_VERSION": preparation["toolchain"]["windows_sdk"], "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_CONFIGURATION_TYPES": "Release", "CMAKE_MSVC_RUNTIME_LIBRARY": "MultiThreadedDLL",
        "VISPY_INPLACE": "OFF", "VISPY_EXPORT_NATIVE_SDK": "OFF", "VISPY_VERIFY_DEPENDENCIES": "ON",
        "VISPY_LEGACY_MSVC_CRT_MUTEX": "ON", "VISPY_BUILD_CONTRACT_TESTS": "ON", "VISPY_CPU_CONTRACTS_ONLY": "OFF",
        "VISPY_NATIVE_SDK_MANIFEST_SHA256": guard.SDK_SHA}
    cache_file = write(paths["build"], "CMakeCache.txt", "\n".join(f"{key}:STRING={value}" for key, value in cache.items()))
    dump(paths["evidence"], "cache-owner.json", identity)
    dump(paths["evidence"], "cache-state.json", {"owner": identity, "cache_sha256": guard.sha(cache_file)})
    return identity, cache


def test_resume_requires_owned_exact_cache_and_fresh_attempt(packet):
    root, paths, _, _, _ = packet
    identity, _ = seed_resume(packet)
    before = inventory(root)
    assert packet_preflight(root, resume=True, attempt="retry-1")["owner"] == identity
    assert inventory(root) == before
    write(paths["evidence"], "attempts/retry-1/build.log", "retained retry")
    reject_unchanged(root, lambda: packet_preflight(root, resume=True, attempt="retry-1"), "already exists")
    identity["source"] = str(root / "build/w9/source")
    dump(paths["evidence"], "cache-owner.json", identity)
    reject_unchanged(root, lambda: packet_preflight(root, resume=True, attempt="retry-2"), "ownership")


@pytest.mark.parametrize("key,value", [("VISPY_INPLACE", "ON"), ("VISPY_NATIVE_SDK_MANIFEST_SHA256", "old-sdk"),
    ("CMAKE_HOME_DIRECTORY", "build/w9/source"), ("VISPY_CONTRACT_TESTS_ROOT", "build/evidence/native-pass-24/harness/tests"),
    ("VISPY_LEGACY_MSVC_CRT_MUTEX", "OFF"), ("CMAKE_GENERATOR_TOOLSET", "v142"), ("Python3_EXECUTABLE", "wrong-python.exe")])
def test_resume_rejects_wrong_cache_even_if_cache_hash_is_resealed(packet, key, value):
    root, paths, _, _, _ = packet
    identity, cache = seed_resume(packet)
    cache[key] = str(root / value) if key.endswith(("DIRECTORY", "ROOT", "EXECUTABLE")) else value
    cache_file = write(paths["build"], "CMakeCache.txt", "\n".join(f"{name}:STRING={item}" for name, item in cache.items()))
    dump(paths["evidence"], "cache-state.json", {"owner": identity, "cache_sha256": guard.sha(cache_file)})
    reject_unchanged(root, lambda: packet_preflight(root, resume=True, attempt="retry-1"), "cache setting mismatch")


def test_freeze_rejects_existing_or_historical_destinations_without_touching_history(packet):
    root, _, _, _, _ = packet
    reject_unchanged(root, lambda: guard.validate_destinations(root, {}, freeze=True), "must be new")
    reject_unchanged(root, lambda: guard.validate_destinations(root, {"evidence": "build/evidence/native-pass-24"}, freeze=True), "Noncanonical")


@pytest.mark.parametrize("flag,value", [("-Evidence", "build/evidence/native-pass-24"),
    ("-Snapshot", "build/w9/source"), ("-Build", "build/native-pass24-sdk"),
    ("-Sdk", "build/native-sdk/windows-x64-release-2")])
def test_actual_powershell_entrypoint_rejects_historical_paths_without_mutation(flag, value):
    historical = ROOT / "build/evidence/native-pass-24"
    before = inventory(historical)
    active_before = current_native_snapshot(ROOT)
    pwsh = shutil.which("pwsh")
    assert pwsh, "The qualified Windows build host requires PowerShell 7"
    result = subprocess.run([pwsh, "-NoProfile", "-File", str(ROOT / "tools/build_pass25_sdk.ps1"),
                             flag, value, "-PreflightOnly"], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="strict")
    assert result.returncode != 0
    assert "Noncanonical pass25" in result.stdout + result.stderr
    assert inventory(historical) == before
    assert current_native_snapshot(ROOT) == active_before


def test_actual_freeze_entrypoint_rejects_historical_evidence_without_mutation():
    historical = ROOT / "build/evidence/native-pass-24"
    before = inventory(historical)
    active_before = current_native_snapshot(ROOT)
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/freeze_pass25_inputs.py"),
                             "--evidence", str(historical)], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="strict")
    assert result.returncode != 0 and "Noncanonical pass25 evidence" in result.stdout + result.stderr
    assert inventory(historical) == before
    assert current_native_snapshot(ROOT) == active_before
