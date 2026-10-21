"""Read-only identity and ownership checks for the single pass25 build packet.

No checks in this module create directories, logs, caches or evidence. Callers
must finish preflight before recording an attempt or invoking a build tool.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    "snapshot": "build/w11/source",
    "evidence": "build/evidence/native-pass-25",
    "harness": "build/evidence/native-pass-25/harness",
    "build": "build/native-pass25-sdk",
    "sdk": "build/native-sdk/windows-x64-release-3",
    "preparation": "compat/cp312-candidate/preparation.json",
    "worker": "build/point-capacity-cpu",
    "activation": "build/evidence/native-pass-24/activation.json",
}
SDK_SHA = "7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2"
PREPARATION_SHA = "b3916829a85afff36230700d1d5d7ea262677a22dc6658e59c0551b9e9e57f52"
ACTIVATION_SHA = "2b2b6b72d834d2c13d9e61696df4f2bd5c78f0eed193956cfefad9b2f000d06f"
WORKER_HASH_SHA = "cf1fd210c594c814e89628a3f93a0e3a4e20a8fc8362cfb9aa2dd6d88d75a60f"
WORKER_EVIDENCE_SHA = "ebcd1db91b9fec9233dbaf56f0bd22e073b81504ed8625e51f61598fe6269d74"
WORKER_SOURCE_SHA = "f2dc2c0570188127de5bdfa9d6184c4fd3d59887b2304623fde0c83c8b19e05e"
FROZEN_ITEMS = {"frozen-inputs.json", "harness", "full-source-tint-proof"}


class GuardError(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise GuardError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def canonical(root, key, supplied=None):
    """Reject historical destinations and filesystem aliases before any IO write."""
    root = Path(root).resolve(strict=True)
    expected = root / PATHS[key]
    candidate = Path(supplied) if supplied is not None else expected
    if not candidate.is_absolute():
        candidate = root / candidate
    require(candidate.resolve() == expected,
            f"Noncanonical pass25 {key}: expected {expected}")
    for path in (expected, *expected.parents):
        if path == root:
            break
        if path.exists() or path.is_symlink():
            require(not path.is_symlink() and not (
                path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
                if hasattr(path.lstat(), "st_file_attributes") else False),
                f"Pass25 {key} uses a reparse point: {path}")
    return expected


def tree_digest(files):
    digest = hashlib.sha256()
    for name, checksum in sorted(files.items()):
        digest.update(name.encode() + b"\0" + bytes.fromhex(checksum))
    return digest.hexdigest()


def member(base, name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ".." not in relative.parts
            and "\\" not in name and ":" not in name,
            f"Unsafe archived relative path: {name}")
    target = Path(base).joinpath(*relative.parts)
    require(target.resolve() == target.absolute(), f"Archived file uses an alias: {name}")
    return target


def verify_inventory(base, files, *, exact=True):
    for name, expected in files.items():
        path = member(base, name)
        require(path.is_file() and sha(path) == expected, f"Archived checksum mismatch: {path}")
    if exact:
        observed = {path.relative_to(base).as_posix() for path in Path(base).rglob("*") if path.is_file()}
        require(observed == set(files), f"Archived inventory mismatch: {base}")


def verify_worker(archive):
    require(sha(archive / "hashes.json") == WORKER_HASH_SHA, "Worker hash manifest changed")
    require(sha(archive / "evidence.json") == WORKER_EVIDENCE_SHA, "Worker CPU evidence changed")
    record = load(archive / "hashes.json")
    source = record["source"]
    require(len(source) == 12 and len({item["file"] for item in source}) == 12,
            "Expected all twelve distinct tested worker sources")
    identity = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(identity == record["source_identity_sha256"] == WORKER_SOURCE_SHA,
            "Worker source identity changed")
    files = {item["file"]: item["sha256"] for item in record["files"]}
    require(len(files) == len(record["files"]), "Worker archive has duplicate paths")
    # hashes.json is the sealed inventory itself; all other proof files are listed.
    verify_inventory(archive, files, exact=False)
    observed = {path.relative_to(archive).as_posix() for path in archive.rglob("*") if path.is_file()}
    require(observed == set(files) | {"hashes.json"}, "Worker full archive inventory changed")
    owned = {item["file"]: item["sha256"] for item in source}
    verify_inventory(archive / "source", owned)
    return owned


def verify_source_inventory(snapshot, files):
    verify_inventory(snapshot, files, exact=False)
    observed = set()
    for name in ("CMakeLists.txt", "CMakePresets.json", "pyproject.toml", "uv.lock",
                 "cmake", "cpp", "src", "third_party/licenses"):
        path = snapshot / name
        if path.is_file():
            observed.add(name)
        elif path.is_dir():
            observed.update(file.relative_to(snapshot).as_posix() for file in path.rglob("*") if file.is_file())
    require(observed == set(files), "Frozen project source inventory changed")


def verify_matched_datasets(archive, harness):
    for item in load(archive / "hashes.json")["files"]:
        name = item["file"]
        if not name.startswith("datasets/"):
            continue
        relative = name.removeprefix("datasets/")
        corpus, rest = relative.split("/", 1)
        routes = {"points": "datasets/point-corpus", "markers": "datasets/marker-corpus",
                  "text": "datasets/text-corpus", "volume": "datasets/volume-corpus",
                  "corpus": "tests/shaders/corpus"}
        require(corpus in routes, f"Unrecognized sealed worker corpus: {corpus}")
        require(sha(member(harness, routes[corpus] + "/" + rest)) == item["sha256"],
                f"Matched worker dataset changed: {name}")


def protected(root):
    activation_path = canonical(root, "activation")
    require(sha(activation_path) == ACTIVATION_SHA, "Activated pass24 manifest changed")
    activation = load(activation_path)["activated"]
    require(len(activation) == 4, "Expected four activated pass24 artifacts")
    expected = {}
    for name, checksum in activation.items():
        prefix = "src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/"
        relative = prefix + name
        require(sha(member(root, relative)) == checksum, f"Activated pass24 artifact changed: {relative}")
        expected[relative] = checksum
    # Also protect any other already installed native ABI leaves.
    for path in (Path(root) / "src/vispy").rglob("*"):
        if path.is_file() and path.suffix.lower() in {".pyd", ".dll"}:
            expected[path.relative_to(root).as_posix()] = sha(path)
    return expected


def verify_preparation(root, preparation):
    require(sha(preparation) == PREPARATION_SHA, "CP312 preparation identity changed")
    record = load(preparation)
    require(record["abi"] == "cp312" and record["interpreter_pin"] == "3.12.8"
            and record["planned_architecture"] == "x64" and record["planned_configuration"] == "Release",
            "Unexpected CP312 build preparation")
    installed = record["installed_environment"]
    for path_key, digest_key in (("executable", "executable_sha256"), ("base_executable", "base_executable_sha256")):
        require(sha(installed[path_key]) == installed[digest_key], f"Prepared interpreter changed: {path_key}")
    require(sha(Path(record["environment"]) / "pyvenv.cfg") == installed["pyvenv_cfg_sha256"],
            "Prepared interpreter configuration changed")
    require(sha(record["cmake"]["origin"]) == record["cmake"]["sha256"], "Prepared CMake changed")
    require(sha(member(root, record["requirements"])) == record["requirements_sha256"], "Build dependency lock changed")
    for item in installed["modules"]:
        require(sha(item["origin"]) == item["sha256"], f"Prepared build module changed: {item['name']}")
    return record


def verify_sdk(root, sdk_path, dependency_lock):
    require(sha(sdk_path / "manifest.json") == SDK_SHA, "Unexpected SDK3 manifest")
    path = Path(root) / "cmake/native_sdk.py"
    spec = importlib.util.spec_from_file_location("pass25_native_sdk", path)
    sdk = importlib.util.module_from_spec(spec)
    # Execute the reviewed verifier without generating a project __pycache__.
    exec(compile(path.read_bytes(), str(path), "exec"), sdk.__dict__)
    sdk_record = load(sdk_path / "manifest.json")
    sdk.verify(sdk_path, SDK_SHA, dependency_lock, sdk_record["producer"])


def validate_destinations(root, supplied, *, freeze=False, resume=False, attempt="initial"):
    paths = {key: canonical(root, key, supplied.get(key)) for key in PATHS}
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", attempt) is not None,
            "Attempt label must be a plain lowercase identifier")
    require(attempt != "initial" if resume else attempt == "initial",
            "Resume requires a fresh non-initial attempt label")
    if freeze:
        require(not resume and not paths["snapshot"].exists() and not paths["evidence"].exists()
                and not paths["build"].exists(), "Pass25 freeze destinations/cache must be new")
    elif not resume:
        require(not paths["build"].exists(), "Initial pass25 cache must be new")
        require(paths["evidence"].is_dir(), "Frozen pass25 evidence is required")
        actual = {path.name for path in paths["evidence"].iterdir()}
        require(actual == FROZEN_ITEMS, "Initial pass25 outputs already exist or frozen evidence is incomplete")
    else:
        require(paths["build"].is_dir(), "Resume requires an owned configured pass25 cache")
        attempts = paths["evidence"] / "attempts"
        require(attempts.resolve() == attempts and not attempts.is_symlink(), "Resume attempts directory uses an alias")
        require(not (attempts / attempt).exists(), "Resume attempt evidence already exists")
    return paths


def verify_cache(build, identity, paths, preparation):
    owner_path = paths["evidence"] / "cache-owner.json"
    require(owner_path.is_file() and load(owner_path) == identity, "Resume cache ownership does not match this frozen packet")
    state = load(paths["evidence"] / "cache-state.json")
    cache_path = build / "CMakeCache.txt"
    require(sha(cache_path) == state["cache_sha256"] and state["owner"] == identity,
            "Resume configured cache identity changed")
    cache = {}
    for line in cache_path.read_text(encoding="utf-8-sig").splitlines():
        if line and not line.startswith(("#", "//")) and "=" in line and ":" in line.split("=", 1)[0]:
            key, value = line.split("=", 1)
            cache[key.split(":", 1)[0]] = value
    path_settings = {"CMAKE_HOME_DIRECTORY": paths["snapshot"], "CMAKE_CACHEFILE_DIR": build,
                     "VISPY_NATIVE_SDK": paths["sdk"],
                     "VISPY_CONTRACT_TESTS_ROOT": paths["harness"] / "tests",
                     "VISPY_CONTRACT_DATASETS_ROOT": paths["harness"] / "datasets",
                     "Python_EXECUTABLE": preparation["installed_environment"]["executable"],
                     "Python3_EXECUTABLE": preparation["installed_environment"]["executable"],
                     "CMAKE_COMMAND": preparation["cmake"]["origin"]}
    for key, expected in path_settings.items():
        require(key in cache and Path(cache[key]).resolve() == Path(expected).resolve(), f"Resume cache setting mismatch: {key}")
    settings = {"CMAKE_GENERATOR": "Visual Studio 17 2022", "CMAKE_GENERATOR_PLATFORM": "x64",
                "CMAKE_GENERATOR_TOOLSET": preparation["toolchain"]["generator_toolset"],
                "CMAKE_SYSTEM_VERSION": preparation["toolchain"]["windows_sdk"],
                "CMAKE_BUILD_TYPE": "Release", "CMAKE_CONFIGURATION_TYPES": "Release",
                "CMAKE_MSVC_RUNTIME_LIBRARY": "MultiThreadedDLL", "VISPY_INPLACE": "OFF",
                "VISPY_EXPORT_NATIVE_SDK": "OFF", "VISPY_VERIFY_DEPENDENCIES": "ON",
                "VISPY_LEGACY_MSVC_CRT_MUTEX": "ON", "VISPY_BUILD_CONTRACT_TESTS": "ON",
                "VISPY_CPU_CONTRACTS_ONLY": "OFF", "VISPY_NATIVE_SDK_MANIFEST_SHA256": SDK_SHA}
    for key, value in settings.items():
        require(cache.get(key) == value, f"Resume cache setting mismatch: {key}")


def preflight(root, supplied=None, *, resume=False, attempt="initial", expected_frozen_sha256=None):
    paths = validate_destinations(root, supplied or {}, resume=resume, attempt=attempt)
    frozen_path = paths["evidence"] / "frozen-inputs.json"
    require(isinstance(expected_frozen_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", expected_frozen_sha256) is not None,
            "The approved frozen-inputs SHA256 is required")
    require(sha(frozen_path) == expected_frozen_sha256, "Approved frozen-inputs identity changed")
    preparation = verify_preparation(root, paths["preparation"])
    verify_sdk(root, paths["sdk"], paths["snapshot"] / "cmake/dependencies.lock.json")
    frozen = load(frozen_path)
    require(frozen["schema"] == 2, "Expected guarded pass25 frozen inputs")
    canonical(root, "snapshot", frozen["source_snapshot"])
    canonical(root, "harness", frozen["harness_root"])
    source = load(paths["snapshot"] / "wheel-source-manifest.json")
    canonical(root, "snapshot", source["snapshot"])
    require(tree_digest(source["source_files"]) == source["source_tree_sha256"] == frozen["source_tree_sha256"],
            "Frozen source tree identity differs")
    verify_source_inventory(paths["snapshot"], source["source_files"])
    require(tree_digest(frozen["harness_files"]) == frozen["harness_tree_sha256"], "Frozen harness tree identity differs")
    verify_inventory(paths["harness"], frozen["harness_files"])
    owned = verify_worker(paths["evidence"] / "full-source-tint-proof")
    verify_matched_datasets(paths["evidence"] / "full-source-tint-proof", paths["harness"])
    require(frozen["worker_verified_sha256"] == owned and
            frozen["worker_source_identity_sha256"] == WORKER_SOURCE_SHA and
            frozen["worker_hash_manifest_sha256"] == WORKER_HASH_SHA and
            frozen["worker_evidence_sha256"] == WORKER_EVIDENCE_SHA, "Frozen worker identity differs")
    for name, checksum in owned.items():
        target = paths["snapshot"] if name.startswith("cpp/") else paths["harness"]
        require(sha(member(target, name)) == checksum, f"Tested source differs: {name}")
        require(frozen["harness_files"].get(name) == checksum, f"Matching harness source missing: {name}")
    for name, checksum in source["source_files"].items():
        if name.startswith("cpp/"):
            require(frozen["harness_files"].get(name) == checksum, f"Harness CPP differs from frozen native source: {name}")
    before = protected(root)
    require(frozen["activation_manifest_sha256"] == ACTIVATION_SHA
            and frozen["protected_native_before"] == frozen["protected_native_after"] == before,
            "Frozen protected baseline differs from activated pass24")
    tools = {"tools/pass25_guard.py", "tools/freeze_pass25_inputs.py", "tools/build_pass25_sdk.ps1"}
    require(set(frozen["guard_tools_sha256"]) == tools, "Frozen guard tool inventory differs")
    for name, checksum in frozen["guard_tools_sha256"].items():
        require(sha(member(root, name)) == checksum, f"Frozen guard tool changed: {name}")
    identity = {"schema": 1, "build": str(paths["build"]), "source": str(paths["snapshot"]),
                "harness": str(paths["harness"]), "source_tree_sha256": frozen["source_tree_sha256"],
                "harness_tree_sha256": frozen["harness_tree_sha256"], "frozen_inputs_sha256": sha(frozen_path),
                "worker_source_identity_sha256": WORKER_SOURCE_SHA, "sdk_manifest_sha256": SDK_SHA,
                "activation_manifest_sha256": ACTIVATION_SHA, "preparation_sha256": PREPARATION_SHA,
                "guard_tools_sha256": frozen["guard_tools_sha256"]}
    if resume:
        verify_cache(paths["build"], identity, paths, preparation)
    attempt_root = paths["evidence"] / "attempts" / attempt if resume else paths["evidence"]
    return {"paths": {key: str(value) for key, value in paths.items()}, "attempt_root": str(attempt_root),
            "owner": identity, "protected": before, "preflight": "passed_read_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("snapshot", "evidence", "build", "sdk", "preparation"):
        parser.add_argument("--" + key, default=PATHS[key])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--attempt", default="initial")
    parser.add_argument("--frozen-inputs-sha256")
    args = parser.parse_args()
    try:
        result = preflight(ROOT, {key: getattr(args, key) for key in PATHS if hasattr(args, key)},
                           resume=args.resume, attempt=args.attempt,
                           expected_frozen_sha256=args.frozen_inputs_sha256)
    except (GuardError, OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Pass25 preflight rejected before writes: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
