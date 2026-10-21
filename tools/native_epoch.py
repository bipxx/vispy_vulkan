"""Explicit, sealed ownership guards for new Windows SDK native build epochs.

This is deliberately independent of the historical pass25 entrypoints. No
epoch, source, evidence, cache, protected activation or approved digest is
inferred from defaults. Read-only preflight completes before any output write.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {"tools/native_epoch.py", "tools/freeze_native_epoch.py", "tools/build_native_epoch.py"}
SOURCE_ROOTS = ("CMakeLists.txt", "CMakePresets.json", "pyproject.toml", "uv.lock",
                "LICENSE", "LICENSE-BSD", "LICENSING.md",
                "cmake", "cpp", "src", "third_party/licenses")
FROZEN_ITEMS = {"frozen-inputs.json", "ownership-manifest.json", "harness", "sealed-packets", "guard-tools"}
REQUIRED_TARGETS = {"_dawn", "_sdf_cpu", "VkLayer_vispy_submit", "shader_contract", "point_contract",
                    "artifact_contract", "texture_contract", "state_contract", "readback_contract",
                    "timestamp_contract", "native_contract", "vk_layer_contract"}


class EpochError(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise EpochError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def checksum(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "An explicit SHA256 is required")
    return value


def tree_digest(files):
    digest = hashlib.sha256()
    for name, value in sorted(files.items()):
        digest.update(name.encode("utf-8") + b"\0" + bytes.fromhex(checksum(value)))
    return digest.hexdigest()


def member(base, name):
    """Use lexical workspace paths; reject aliases including Windows junctions."""
    require(isinstance(name, str) and name != "", "A relative path is required")
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and name == relative.as_posix()
            and not ({"..", "."} & set(relative.parts)) and "\\" not in name and ":" not in name,
            f"Unsafe relative path: {name}")
    base = Path(base).absolute()
    target = base.joinpath(*relative.parts)
    require(target.resolve() == target, f"Path uses a filesystem alias: {target}")
    for path in (target, *target.parents):
        if path.exists() or path.is_symlink():
            attrs = getattr(path.lstat(), "st_file_attributes", 0)
            require(not path.is_symlink() and not attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0),
                    f"Path uses a reparse point: {path}")
        if path == base:
            break
    return target


def inventory(base):
    return {path.relative_to(base).as_posix(): sha(member(base, path.relative_to(base).as_posix()))
            for path in Path(base).rglob("*") if path.is_file()}


def reject_tree_aliases(base):
    for path in (Path(base), *Path(base).rglob("*")):
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
        require(not path.is_symlink() and not attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0),
                f"Evidence/cache uses a filesystem alias: {path}")


def verify_inventory(base, files):
    require(isinstance(files, dict) and files, f"A sealed inventory is required: {base}")
    reject_tree_aliases(base)
    for name, value in files.items():
        require(sha(member(base, name)) == checksum(value), f"Sealed file changed: {base}/{name}")
    require(inventory(base) == files, f"Sealed inventory changed: {base}")


def project_inventory(root):
    result = {}
    for name in SOURCE_ROOTS:
        base = member(root, name)
        files = [base] if base.is_file() else sorted(base.rglob("*"))
        for path in files:
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in path.parts):
                continue
            if path.suffix.lower() in {".pyd", ".dll", ".so", ".dylib", ".pyc", ".pyo"}:
                continue
            if relative == "src/vispy/VkLayer_vispy_submit.json":
                continue
            result[relative] = sha(member(root, relative))
    return result


def native_inventory(root):
    base = member(root, "src/vispy")
    return {path.relative_to(root).as_posix(): sha(member(root, path.relative_to(root).as_posix()))
            for path in base.rglob("*") if path.is_file() and (
                path.suffix.lower() in {".pyd", ".dll", ".so", ".dylib"}
                or path.name == "VkLayer_vispy_submit.json")}


def check_protected(root, record, paths):
    require(sha(paths["activation"]) == checksum(record["activation_manifest_sha256"]),
            "Protected activation manifest changed")
    activated = load(paths["activation"])["activated"]
    require(len(activated) == 4, "Four activated native artifacts are required")
    mapped = {}
    for name, value in activated.items():
        require("/" not in name and "\\" not in name, "Activation artifact must be a basename")
        prefix = "src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/"
        mapped[prefix + name] = checksum(value)
    protected = record["protected_native"]
    require(all(protected.get(name) == value for name, value in mapped.items()), "Protected baseline disagrees with activation")
    require(native_inventory(root) == protected, "Protected native inventory or bytes changed")
    return protected


def check_preparation(root, record, path):
    require(sha(path) == checksum(record["preparation_sha256"]), "Build preparation changed")
    prepared = load(path)
    require(prepared["abi"] == "cp312" and prepared["planned_architecture"] == "x64"
            and prepared["planned_configuration"] == "Release" and not prepared["free_threaded"],
            "This entrypoint requires the standard CP312 Windows x64 Release preparation")
    installed = prepared["installed_environment"]
    require(installed["python"] == prepared["interpreter_pin"] and installed["pointer_bytes"] == 8,
            "Prepared interpreter identity is inconsistent")
    for origin, digest in ((installed["executable"], installed["executable_sha256"]),
                           (installed["base_executable"], installed["base_executable_sha256"]),
                           (Path(prepared["environment"]) / "pyvenv.cfg", installed["pyvenv_cfg_sha256"]),
                           (prepared["cmake"]["origin"], prepared["cmake"]["sha256"]),
                           (Path(prepared["cmake"]["origin"]).with_name("ctest.exe"), record["ctest_sha256"]),
                           (member(root, prepared["requirements"]), prepared["requirements_sha256"])):
        require(sha(origin) == checksum(digest), f"Prepared build tool or lock changed: {origin}")
    for item in installed["modules"]:
        require(sha(item["origin"]) == checksum(item["sha256"]), f"Prepared module changed: {item['name']}")
    return prepared


def sdk_module(root):
    path = member(root, "cmake/native_sdk.py")
    spec = importlib.util.spec_from_file_location("native_epoch_sdk", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def check_sdk(root, record, prefix, dependency_lock):
    require(sha(prefix / "manifest.json") == checksum(record["sdk_manifest_sha256"]), "Sealed SDK manifest changed")
    sdk_record = load(prefix / "manifest.json")
    require(sdk_record["producer"]["msvc_mutex_policy"] == "msvc-stl-init-in-situ-v1", "A compatible-CRT SDK is required")
    sdk_module(root).verify(prefix, record["sdk_manifest_sha256"], dependency_lock, sdk_record["producer"])


def origin_settings(record):
    if "dependency_origins" not in record:
        return None
    origins = record["dependency_origins"]
    require(type(origins) is dict and set(origins) ==
            {"schema", "authority_workspace", "module_sha256", "context", "capture", "admission"}
            and type(origins["schema"]) is int and origins["schema"] == 1,
            "Explicit dependency-origin settings differ")
    workspace = origins["authority_workspace"]
    require(type(workspace) is str and Path(workspace).is_absolute()
            and Path(workspace).resolve() == Path(workspace).absolute(), "Origin authority workspace must be canonical and absolute")
    checksum(origins["module_sha256"])
    require(record["source_files"].get("cmake/dependency_origins.py") == origins["module_sha256"],
            "Origin module is absent from exact project source ownership")
    for name in ("context", "capture", "admission"):
        row = origins[name]
        keys = {"path", "sha256"} if name == "context" else {"path", "sha256", "seal_path", "seal_sha256"}
        require(type(row) is dict and set(row) == keys, "Explicit origin reference differs")
        member(workspace, row["path"])
        checksum(row["sha256"])
        if name != "context":
            member(workspace, row["seal_path"])
            checksum(row["seal_sha256"])
    return origins


def origin_module(root, record):
    origins = origin_settings(record)
    require(origins is not None, "Explicit dependency origins are required")
    path = member(root, "cmake/dependency_origins.py")
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == origins["module_sha256"], "Owned origin module changed")
    spec = importlib.util.spec_from_file_location("native_epoch_dependency_origins", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def dependency_lock_for(root, record):
    """Select a new lock only from the exact approved origin authority, never promote it."""
    origins = origin_settings(record)
    upstream = member(root, "cmake/dependencies.lock.json")
    if origins is None:
        return upstream
    module = origin_module(root, record)
    workspace = origins["authority_workspace"]
    context_path, context = module.reference(workspace, origins["context"])
    require(context["schema"] == 1 and context["scope"] == "explicit_immutable_dependency_origins"
            and context["upstream_lock"]["path"] == "cmake/dependencies.lock.json"
            and sha(upstream) == context["upstream_lock"]["sha256"]
            and all(context[key] is False for key in
                    ("dependency_lock_promoted", "SDK_staged", "native_imported", "device_created", "GPU_used")),
            "Approved origin context or preserved upstream lock differs")
    module.reference(workspace, context["upstream_lock"])
    lock_path, lock = module.reference(workspace, context["dependency_lock"])
    require(lock_path != upstream and context["dependency_lock"]["sha256"] != context["upstream_lock"]["sha256"]
            and lock["schema"] == 1 and lock["digest_algorithm"] == "sha256(sorted relative path + NUL + file SHA256 bytes)",
            "Explicit distinct captured new lock required")
    captured, _, required = module.packet(workspace, origins["capture"])
    admitted, _, _ = module.packet(workspace, origins["admission"])
    require(context_path.parent == module.member(workspace, origins["capture"]["path"]).parent
            and captured["status"] == "passed_origin_capture" and captured["scope"] == "patched_dependency_origin_capture_only"
            and type(captured["process_exit"]) is int and captured["process_exit"] == 0 and captured["error"] is None
            and captured["source_copy_only"] is True and captured["origin_context_sha256"] == origins["context"]["sha256"]
            and captured["new_lock_sha256"] == context["dependency_lock"]["sha256"]
            and captured["protected_native_before"] == captured["protected_native_after"]
            and all(captured[key] is False for key in ("child_launched", "compiled", "tests_run", "dependency_lock_promoted",
                    "SDK_staged", "native_imported", "device_created", "GPU_used")), "Actual approved capture/new lock differs")
    require(admitted["status"] == "CLEAR_WITH_SCOPE" and admitted["scope"] == "explicit_immutable_dependency_origins"
            and type(admitted["process_exit"]) is int and admitted["process_exit"] == 0 and admitted["material_findings"] == []
            and all(admitted[key] is False for key in ("native_imported", "device_created", "GPU_used")),
            "Actual independent origin admission required for lock selection")
    facts = admitted["verified_scope"]
    require(facts["origin_context"] == origins["context"] and facts["dependency_lock"] == context["dependency_lock"]
            and facts["complete_physical_source_and_dependency_inventory_admitted"] is True,
            "Actual admitted context/new-lock roles differ")
    for row in (origins["context"], context["dependency_lock"], context["upstream_lock"]):
        require(row["path"] not in required or required[row["path"]] == row["sha256"], "Origin lock proof identity collision")
        required[row["path"]] = row["sha256"]
    require(type(admitted["checked_inputs"]) is dict and all(admitted["checked_inputs"].get(name) == pin for name, pin in required.items()),
            "Independent origin admission omits bound capture/context/new-lock inputs")
    return lock_path


def origin_arguments(record, *, require_mappings=True):
    origins = origin_settings(record)
    if origins is None:
        return []
    values = {"workspace": origins["authority_workspace"], "module-sha256": origins["module_sha256"]}
    for name in ("context", "capture", "admission"):
        row = origins[name]
        values[name] = row["path"]
        values[name + "-sha256"] = row["sha256"]
        if name != "context":
            values[name + "-seal"] = row["seal_path"]
            values[name + "-seal-sha256"] = row["seal_sha256"]
    result = [value for name, value in values.items() for value in ("--origin-" + name, value)]
    if not require_mappings:
        result.append("--origin-preflight-only")
    return result


def dependency_command(root, prepared, record=None, *, require_mappings=True):
    command = [prepared["installed_environment"]["executable"], "-B", str(member(root, "cmake/verify_dependencies.py"))]
    if record is not None and origin_settings(record) is not None:
        require(sha(member(root, "cmake/verify_dependencies.py")) ==
                record["source_files"].get("cmake/verify_dependencies.py"), "Owned dependency verifier changed")
        require(sha(member(root, "cmake/dependency_origins.py")) == record["dependency_origins"]["module_sha256"],
                "Owned origin module changed")
        command += ["--dependency-lock", str(dependency_lock_for(root, record))]
        command += origin_arguments(record, require_mappings=require_mappings)
    return command


def check_dependencies(root, prepared, record=None, *, require_mappings=True):
    command = dependency_command(root, prepared, record, require_mappings=require_mappings)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    require(result.returncode == 0, "Immutable dependency source verification failed before writes: "
            + result.stdout.decode("utf-8", errors="replace"))


def paths_for(root, record):
    epoch, source_epoch = record["epoch"], record["snapshot_epoch"]
    require(type(epoch) is int and epoch >= 26 and type(source_epoch) is int and source_epoch >= 12,
            "Historical pass25/w11 and earlier epochs are forbidden")
    expected = {"snapshot": f"build/w{source_epoch}/source", "evidence": f"build/evidence/native-pass-{epoch}",
                "harness": f"build/evidence/native-pass-{epoch}/harness", "build": f"build/native-pass{epoch}-sdk"}
    require(set(record["paths"]) == set(expected) | {"sdk", "preparation", "activation"}, "Unexpected path inventory")
    require(all(record["paths"][key] == name for key, name in expected.items()), "Noncanonical epoch destinations")
    match = re.fullmatch(r"build/evidence/native-pass-([0-9]+)/activation.json", record["paths"]["activation"])
    require(match and 25 <= int(match[1]) < epoch, "Protected activation must be an earlier qualified epoch")
    return {key: member(root, name) for key, name in record["paths"].items()}


def check_packet(archive, packet):
    require(re.fullmatch(r"[a-z][a-z0-9-]{0,47}", packet["name"]), "Unsafe packet name")
    require(packet["sealed"] is True, f"CPU ownership packet is unsealed: {packet['name']}")
    require(tree_digest(packet["files"]) == checksum(packet["files_tree_sha256"]), "CPU archive tree identity differs")
    verify_inventory(archive, packet["files"])
    proof = load(member(archive, packet["proof_file"]))
    require(packet["proof_file"] in packet["files"] and packet["proof_assertions"], "CPU result assertions are required")
    exits = [value for key, value in packet["proof_assertions"].items() if "exit" in key]
    require(exits and all(type(value) is int and value == 0 for value in exits), "CPU packet requires explicit successful exit assertions")
    for key, expected in packet["proof_assertions"].items():
        current = proof
        for field in key.split("."):
            current = current[int(field)] if isinstance(current, list) else current[field]
        require(type(current) is type(expected) and current == expected, f"CPU proof assertion failed: {packet['name']}:{key}")
    owned = {name: packet["files"][origin] for name, origin in packet["owned_files"].items()}
    require(owned and tree_digest(owned) == checksum(packet["source_tree_sha256"]), "Owned source tree identity differs")
    for name, origin in packet["owned_files"].items():
        member(archive, origin)
        require(name.startswith(("cpp/", "tests/")) and name.endswith((".cpp", ".hpp", ".h", ".mm")),
                f"Unexpected native ownership source: {name}")
    return owned


def approved_manifest(root, manifest_path, approved_sha):
    checksum(approved_sha)
    path = member(root, manifest_path)
    require(sha(path) == approved_sha, "Approved ownership manifest changed")
    record = load(path)
    require(record["schema"] == 1 and record["sealed"] is True, "Ownership manifest must be sealed schema1")
    for name in ("CL", "_CL_", "CFLAGS", "CXXFLAGS", "CMAKE_TOOLCHAIN_FILE"):
        require(not os.environ.get(name, "").strip(), f"Ambient build flags are not sealed: {name}")
    paths = paths_for(root, record)
    require(set(record["tool_files"]) == TOOLS, "Entrypoint tool inventory differs")
    for name, value in record["tool_files"].items():
        require(sha(member(root, name)) == checksum(value), f"Approved entrypoint changed: {name}")
    targets = record["targets"]
    require(len(targets) == len(set(targets)) and REQUIRED_TARGETS <= set(targets)
            and all(name in REQUIRED_TARGETS or re.fullmatch(r"[a-z][a-z0-9_]*_contract", name) for name in targets),
            "Native leaf and contract targets must be explicit; vendor targets are forbidden")
    names = record["ctest_expected_names"]
    require(names and len(names) == len(set(names)) and all(isinstance(name, str) and name for name in names),
            "An exact nonempty CTest inventory is required")
    require(record["sdk_tint_reader_enabled"] is False, "SDK exports cannot enable private Tint-reader contracts")
    return path, record, paths


def preflight_freeze(root, manifest_path, approved_sha):
    path, record, paths = approved_manifest(root, manifest_path, approved_sha)
    require(not any(paths[key].exists() for key in ("snapshot", "evidence", "build")), "Initial epoch destinations must be new")
    # Even a deleted historical directory cannot be repurposed as a lower epoch.
    for directory, pattern, number in (("build", r"w([0-9]+)", record["snapshot_epoch"]),
                                       ("build/evidence", r"native-pass-([0-9]+)", record["epoch"]),
                                       ("build", r"native-pass([0-9]+)-sdk", record["epoch"])):
        base = member(root, directory)
        for child in base.iterdir() if base.is_dir() else ():
            match = re.fullmatch(pattern, child.name)
            require(not match or int(match[1]) < number, "Epoch must advance beyond all existing source/evidence/cache epochs")
    require(project_inventory(root) == record["source_files"], "Live source inventory differs from the sealed ownership manifest")
    before = check_protected(root, record, paths)
    prepared = check_preparation(root, record, paths["preparation"])
    require(record["packets"] and len({item["name"] for item in record["packets"]}) == len(record["packets"]),
            "Distinct sealed CPU ownership packets are required")
    owned = {}
    for packet in record["packets"]:
        archive = member(root, packet["archive"])
        for name, value in check_packet(archive, packet).items():
            require(name not in owned, f"Overlapping CPU source ownership: {name}")
            owned[name] = value
            require(sha(member(root, name)) == value, f"Live CPU-owned source changed: {name}")
            target = record["source_files"] if name.startswith("cpp/") else {
                name: item["sha256"] for name, item in record["harness_inputs"].items()}
            require(target.get(name) == value, f"Owned source absent from matching snapshot/harness: {name}")
    require(record["harness_inputs"], "Matching external CPU harness is required")
    for name, item in record["harness_inputs"].items():
        member(paths["harness"], name)
        require(name.startswith(("cpp/", "tests/", "datasets/")), "Unexpected harness member")
        require(sha(member(root, item["path"])) == checksum(item["sha256"]), f"Sealed harness input changed: {name}")
    for name, value in record["source_files"].items():
        if name.startswith("cpp/"):
            require(record["harness_inputs"].get(name, {}).get("sha256") == value, f"Matching native harness source missing: {name}")
    check_sdk(root, record, paths["sdk"], dependency_lock_for(root, record))
    check_dependencies(root, prepared, record, require_mappings=False)
    return {"manifest": path, "record": record, "paths": paths, "prepared": prepared,
            "protected": before, "owned_files": owned, "preflight": "passed_read_only"}


def write_json_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def link_dependencies(root, snapshot, record=None):
    if record is not None and origin_settings(record) is not None:
        module = origin_module(root, record)
        origins = record["dependency_origins"]
        mappings = module.verify_origins(origins["authority_workspace"], context=origins["context"],
                                         capture=origins["capture"], admission=origins["admission"],
                                         dependency_lock=dependency_lock_for(root, record))
        module.link_snapshot(snapshot, mappings)
        require(sha(member(snapshot, "cmake/dependencies.lock.json")) ==
                sha(member(root, "cmake/dependencies.lock.json")), "Snapshot origin lock changed")
        return
    for name in ("third_party/dawn", "third_party/parity"):
        source = member(root, name)
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                            "New-Item -ItemType Junction -Path " + quote(target) + " -Target " + quote(source)
                            + " | Out-Null"], check=True)
        else:
            target.symlink_to(source, target_is_directory=True)


def freeze(root, manifest_path, approved_sha, *, preflight_only=False):
    checked = preflight_freeze(root, manifest_path, approved_sha)
    if preflight_only:
        return summary(checked)
    record, paths = checked["record"], checked["paths"]
    # Exclusive creation: partial failures are retained, never silently reused.
    paths["evidence"].mkdir(parents=True, exist_ok=False)
    paths["snapshot"].mkdir(parents=True, exist_ok=False)
    for name, value in record["source_files"].items():
        data = member(root, name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == value, f"Source changed during capture: {name}")
        target = member(paths["snapshot"], name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    source_record = {"schema": 1, "original_checkout": str(Path(root).resolve()), "snapshot": str(paths["snapshot"]),
                     "source_files": record["source_files"], "source_tree_sha256": tree_digest(record["source_files"]),
                     "ownership_manifest_sha256": approved_sha,
                     "dependency_verification_required": "before and after the native build"}
    if origin_settings(record) is not None:
        source_record["dependency_origins"] = record["dependency_origins"]
    write_json_new(paths["snapshot"] / "wheel-source-manifest.json", source_record)
    paths["harness"].mkdir()
    harness = {}
    for name, item in record["harness_inputs"].items():
        data = member(root, item["path"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item["sha256"], f"Harness input changed during capture: {name}")
        target = member(paths["harness"], name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        harness[name] = item["sha256"]
    archive_root = paths["evidence"] / "sealed-packets"
    archive_root.mkdir()
    for packet in record["packets"]:
        shutil.copytree(member(root, packet["archive"]), archive_root / packet["name"])
        check_packet(archive_root / packet["name"], packet)
    shutil.copyfile(checked["manifest"], paths["evidence"] / "ownership-manifest.json")
    guard_root = paths["evidence"] / "guard-tools"
    guard_root.mkdir()
    for name, value in record["tool_files"].items():
        target = member(guard_root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(member(root, name), target)
    verify_inventory(guard_root, record["tool_files"])
    require(project_inventory(root) == record["source_files"], "Live source changed during capture")
    require(project_inventory(paths["snapshot"]) == record["source_files"], "Snapshot inventory changed during capture")
    verify_inventory(paths["harness"], harness)
    require(sha(checked["manifest"]) == approved_sha, "Ownership manifest changed during capture")
    require(check_protected(root, record, paths) == checked["protected"], "Protected native bytes changed during capture")
    link_dependencies(root, paths["snapshot"], record)
    if origin_settings(record) is not None:
        check_dependencies(paths["snapshot"], checked["prepared"], record)
    frozen = {"schema": 1, "epoch": record["epoch"], "snapshot_epoch": record["snapshot_epoch"],
              "ownership_manifest_sha256": approved_sha, "source_files": record["source_files"],
              "source_tree_sha256": source_record["source_tree_sha256"], "harness_files": harness,
              "harness_tree_sha256": tree_digest(harness), "owned_files": checked["owned_files"],
              "protected_native_before": checked["protected"], "protected_native_after": check_protected(root, record, paths),
              "sdk_tint_reader_enabled": False, "gpu_qualified": False}
    if origin_settings(record) is not None:
        frozen["dependency_origins"] = record["dependency_origins"]
    write_json_new(paths["evidence"] / "frozen-inputs.json", frozen)
    return {**summary(checked), "source_tree_sha256": frozen["source_tree_sha256"],
            "harness_tree_sha256": frozen["harness_tree_sha256"],
            "frozen_inputs_sha256": sha(paths["evidence"] / "frozen-inputs.json")}


def cache_settings(paths, prepared, record):
    producer = load(paths["sdk"] / "manifest.json")["producer"]
    values = {"CMAKE_GENERATOR": "Visual Studio 17 2022", "CMAKE_GENERATOR_PLATFORM": "x64",
              "CMAKE_GENERATOR_TOOLSET": prepared["toolchain"]["generator_toolset"],
              "CMAKE_SYSTEM_VERSION": prepared["toolchain"]["windows_sdk"],
              "CMAKE_BUILD_TYPE": "Release", "CMAKE_CONFIGURATION_TYPES": "Release",
              "CMAKE_CXX_FLAGS": producer["cxx_flags"], "CMAKE_CXX_FLAGS_RELEASE": producer["release_flags"],
              "CMAKE_MSVC_RUNTIME_LIBRARY": "MultiThreadedDLL", "VISPY_INPLACE": "OFF",
              "VISPY_EXPORT_NATIVE_SDK": "OFF", "VISPY_VERIFY_DEPENDENCIES": "ON",
              "VISPY_LEGACY_MSVC_CRT_MUTEX": "ON", "VISPY_BUILD_CONTRACT_TESTS": "ON",
              "VISPY_CPU_CONTRACTS_ONLY": "OFF", "VISPY_NATIVE_SDK_MANIFEST_SHA256": record["sdk_manifest_sha256"]}
    files = {"CMAKE_HOME_DIRECTORY": paths["snapshot"], "CMAKE_CACHEFILE_DIR": paths["build"],
             "VISPY_NATIVE_SDK": paths["sdk"], "VISPY_CONTRACT_TESTS_ROOT": paths["harness"] / "tests",
             "VISPY_CONTRACT_DATASETS_ROOT": paths["harness"] / "datasets",
             "Python_EXECUTABLE": prepared["installed_environment"]["executable"],
             "Python3_EXECUTABLE": prepared["installed_environment"]["executable"],
             "CMAKE_COMMAND": prepared["cmake"]["origin"]}
    origins = origin_settings(record)
    if origins is not None:
        files["VISPY_DEPENDENCY_LOCK"] = dependency_lock_for(paths["snapshot"], record)
        values["VISPY_DEPENDENCY_ORIGIN_MODULE_SHA256"] = origins["module_sha256"]
        files["VISPY_DEPENDENCY_ORIGIN_WORKSPACE"] = Path(origins["authority_workspace"])
        for name in ("context", "capture", "admission"):
            for field, value in origins[name].items():
                suffix = {"path": "", "sha256": "_SHA256", "seal_path": "_SEAL", "seal_sha256": "_SEAL_SHA256"}[field]
                values["VISPY_DEPENDENCY_ORIGIN_" + name.upper() + suffix] = value
    return values, files


def verify_cache(paths, prepared, record, owner=None):
    if owner is not None:
        require(load(paths["evidence"] / "cache-owner.json") == owner, "Resume cache ownership differs")
        state = load(paths["evidence"] / "cache-state.json")
        require(state["owner"] == owner and sha(paths["build"] / "CMakeCache.txt") == state["cache_sha256"],
                "Resume configured cache identity changed")
    cache = {}
    for line in (paths["build"] / "CMakeCache.txt").read_text(encoding="utf-8-sig").splitlines():
        if re.match(r"[^#/:][^:]*:[^=]+=", line):
            key, value = line.split("=", 1)
            cache[key.split(":", 1)[0]] = value
    values, files = cache_settings(paths, prepared, record)
    for name, value in values.items():
        require(cache.get(name) == value, f"Configured cache setting differs: {name}")
    for name, path in files.items():
        require(name in cache and Path(cache[name]).resolve() == Path(path).resolve(), f"Configured cache path differs: {name}")


def preflight_build(root, manifest_path, approved_sha, frozen_sha, *, resume=False, attempt="initial"):
    path, record, paths = approved_manifest(root, manifest_path, approved_sha)
    checksum(frozen_sha)
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", attempt), "Unsafe attempt label")
    require((attempt != "initial") if resume else (attempt == "initial"), "Resume needs a fresh non-initial attempt")
    require(paths["evidence"].is_dir() and paths["snapshot"].is_dir(), "A frozen source and evidence packet are required")
    reject_tree_aliases(paths["evidence"])
    if not resume:
        require(not paths["build"].exists() and {path.name for path in paths["evidence"].iterdir()} == FROZEN_ITEMS,
                "Initial build cache or outputs already exist")
    else:
        require(paths["build"].is_dir(), "Resume requires an owned configured cache")
        reject_tree_aliases(paths["build"])
    attempt_root = member(paths["evidence"], "attempts/" + attempt) if resume else paths["evidence"]
    require(not resume or not attempt_root.exists(), "Resume attempt output already exists")
    require(not (paths["evidence"] / "active-build.json").exists(), "A native build already owns this epoch")
    require(sha(paths["evidence"] / "ownership-manifest.json") == approved_sha, "Archived ownership manifest changed")
    verify_inventory(paths["evidence"] / "guard-tools", record["tool_files"])
    frozen_path = paths["evidence"] / "frozen-inputs.json"
    require(sha(frozen_path) == frozen_sha, "Approved frozen-inputs identity changed")
    frozen = load(frozen_path)
    require(frozen["schema"] == 1 and frozen["epoch"] == record["epoch"] and frozen["snapshot_epoch"] == record["snapshot_epoch"]
            and frozen["ownership_manifest_sha256"] == approved_sha, "Frozen epoch identity differs")
    require(frozen["source_files"] == record["source_files"] and frozen["source_tree_sha256"] == tree_digest(record["source_files"]),
            "Frozen source identity differs")
    require(project_inventory(paths["snapshot"]) == record["source_files"], "Frozen project source inventory changed")
    source_record = load(paths["snapshot"] / "wheel-source-manifest.json")
    require(source_record["snapshot"] == str(paths["snapshot"]) and source_record["source_files"] == record["source_files"]
            and source_record["source_tree_sha256"] == frozen["source_tree_sha256"]
            and source_record["ownership_manifest_sha256"] == approved_sha, "Snapshot manifest differs")
    harness = {name: item["sha256"] for name, item in record["harness_inputs"].items()}
    require(frozen["harness_files"] == harness and frozen["harness_tree_sha256"] == tree_digest(harness), "Frozen harness identity differs")
    verify_inventory(paths["harness"], harness)
    require({path.name for path in (paths["evidence"] / "sealed-packets").iterdir()} == {item["name"] for item in record["packets"]},
            "Sealed CPU archive inventory differs")
    owned = {}
    for packet in record["packets"]:
        for name, value in check_packet(paths["evidence"] / "sealed-packets" / packet["name"], packet).items():
            require(name not in owned, f"Overlapping CPU source ownership: {name}")
            owned[name] = value
            base = paths["snapshot"] if name.startswith("cpp/") else paths["harness"]
            require(sha(member(base, name)) == value and harness.get(name) == value, f"Frozen CPU-owned source differs: {name}")
    require(frozen["owned_files"] == owned, "Frozen CPU ownership differs")
    for name, value in record["source_files"].items():
        if name.startswith("cpp/"):
            require(harness.get(name) == value, f"Frozen CPP/harness identity differs: {name}")
    before = check_protected(root, record, paths)
    require(frozen["protected_native_before"] == frozen["protected_native_after"] == before, "Frozen protected baseline differs")
    require(frozen["sdk_tint_reader_enabled"] is False and frozen["gpu_qualified"] is False, "Frozen qualification scope differs")
    prepared = check_preparation(root, record, paths["preparation"])
    check_sdk(paths["snapshot"], record, paths["sdk"], dependency_lock_for(paths["snapshot"], record))
    require(frozen.get("dependency_origins") == origin_settings(record)
            and source_record.get("dependency_origins") == origin_settings(record), "Frozen origin authority differs")
    check_dependencies(paths["snapshot"], prepared, record)
    owner = {"schema": 1, "epoch": record["epoch"], "snapshot_epoch": record["snapshot_epoch"],
             "paths": record["paths"], "ownership_manifest_sha256": approved_sha, "frozen_inputs_sha256": frozen_sha,
             "source_tree_sha256": frozen["source_tree_sha256"], "harness_tree_sha256": frozen["harness_tree_sha256"],
             "sdk_manifest_sha256": record["sdk_manifest_sha256"], "preparation_sha256": record["preparation_sha256"],
             "activation_manifest_sha256": record["activation_manifest_sha256"], "tool_files": record["tool_files"]}
    if origin_settings(record) is not None:
        owner["dependency_origins"] = record["dependency_origins"]
    if resume:
        verify_cache(paths, prepared, record, owner)
    return {"manifest": path, "record": record, "paths": paths, "prepared": prepared, "frozen": frozen,
            "protected": before, "owner": owner, "attempt_root": attempt_root, "preflight": "passed_read_only"}


def summary(checked):
    result = {"preflight": checked["preflight"], "epoch": checked["record"]["epoch"],
              "paths": {key: str(value) for key, value in checked["paths"].items()}, "protected_native": checked["protected"]}
    if origin_settings(checked["record"]) is not None:
        result["dependency_origins"] = checked["record"]["dependency_origins"]
    if "owner" in checked:
        result.update(owner=checked["owner"], attempt_root=str(checked["attempt_root"]))
    return result


def attest_projects(root, checked):
    paths = checked["paths"]
    sdk = sdk_module(paths["snapshot"])
    projects = {path.relative_to(paths["build"]).as_posix(): sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")
                for path in sorted(paths["build"].rglob("*.vcxproj")) if "CMakeFiles" not in path.relative_to(paths["build"]).parts}
    require(projects, "No generated C++ compiler policies were attested")
    for target in ("shader_contract", "point_contract"):
        require("VISPY_TEST_TINT_READER" not in (paths["build"] / (target + ".vcxproj")).read_text(encoding="utf-8-sig"),
                "SDK contract attempted to use private Tint headers")
    require(not any((paths["build"] / name).exists() for name in ("dawn", "glslang")), "SDK build added a vendor build graph")
    return {"sdk_manifest_sha256": checked["record"]["sdk_manifest_sha256"], "cpp_projects": projects,
            "sdk_tint_reader_enabled": False, "vendor_build_graph_added": False}


def check_ctest(path, expected):
    document = ET.parse(path).getroot()
    tests = list(document.iter("testcase"))
    names = [test.get("name") for test in tests]
    require(len(names) == len(set(names)) and set(names) == set(expected), "CTest inventory differs from the approved contract list")
    require(all(not any(test.find(name) is not None for name in ("failure", "error", "skipped"))
                and test.get("status", "run") == "run" for test in tests), "CTest has failed, skipped or unexecuted contracts")
    for suite in document.iter("testsuite"):
        require(all(int(suite.get(key, "0")) == 0 for key in ("failures", "errors", "skipped", "disabled")),
                "CTest suite reports incomplete qualification")


def build(root, manifest_path, approved_sha, frozen_sha, *, resume=False, attempt="initial", preflight_only=False):
    checked = preflight_build(root, manifest_path, approved_sha, frozen_sha, resume=resume, attempt=attempt)
    if preflight_only:
        return summary(checked)
    paths, record, prepared = checked["paths"], checked["record"], checked["prepared"]
    lock = paths["evidence"] / "active-build.json"
    write_json_new(lock, checked["owner"])  # exclusive cross-attempt build ownership
    out = checked["attempt_root"]
    attempt_claimed = False
    try:
        if resume:
            out.mkdir(parents=True, exist_ok=False)
        else:
            write_json_new(out / "initial-attempt.json", checked["owner"])
            write_json_new(out / "cache-owner.json", checked["owner"])
        attempt_claimed = True
        write_json_new(out / "preflight.json", summary(checked))
        write_json_new(out / "protected-source-binaries-before.json", checked["protected"])
        env = {**os.environ, "CL_MPCount": "3", "PYTHONDONTWRITEBYTECODE": "1"}
        cmake, python = prepared["cmake"]["origin"], prepared["installed_environment"]["executable"]

        def run(name, command):
            write_json_new(out / (name + "-command.json"), {"argv": command, "CL_MPCount": "3"})
            with (out / (name + ".log")).open("xb") as stream:
                result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, env=env, check=False)
            require(result.returncode == 0, f"Native {name} failed; immutable attempt evidence retained")

        values, files = cache_settings(paths, prepared, record)
        configure = [cmake, "-S", str(paths["snapshot"]), "-B", str(paths["build"]), "-G", values["CMAKE_GENERATOR"],
                     "-A", values["CMAKE_GENERATOR_PLATFORM"], "-T", values["CMAKE_GENERATOR_TOOLSET"]]
        configure += [f"-D{name}={value}" for name, value in {**values, **files}.items()
                      if name not in {"CMAKE_GENERATOR", "CMAKE_GENERATOR_PLATFORM", "CMAKE_GENERATOR_TOOLSET",
                                      "CMAKE_HOME_DIRECTORY", "CMAKE_CACHEFILE_DIR", "CMAKE_COMMAND"}]
        if not resume:
            run("configure", configure)
        verify_cache(paths, prepared, record)
        write_json_new(out / "generated-cpp-policy.json", attest_projects(root, checked))
        state = {"owner": checked["owner"], "cache_sha256": sha(paths["build"] / "CMakeCache.txt")}
        (paths["evidence"] / "cache-state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run("build", [cmake, "--build", str(paths["build"]), "--config", "Release", "--parallel", "3", "--target",
                      *record["targets"], "--", "/p:CL_MPCount=3"])
        run("ctest", [str(Path(cmake).with_name("ctest.exe")), "--test-dir", str(paths["build"]), "-C", "Release",
                      "--output-on-failure", "--output-junit", str(out / "ctest.xml")])
        check_ctest(out / "ctest.xml", record["ctest_expected_names"])
        require(project_inventory(paths["snapshot"]) == record["source_files"], "Frozen source changed during build")
        require(sha(checked["manifest"]) == approved_sha, "Approved ownership manifest changed during build")
        verify_inventory(paths["harness"], checked["frozen"]["harness_files"])
        verify_cache(paths, prepared, record)
        write_json_new(out / "generated-cpp-policy-after.json", attest_projects(root, checked))
        check_sdk(paths["snapshot"], record, paths["sdk"], dependency_lock_for(paths["snapshot"], record))
        run("dependencies-after", dependency_command(paths["snapshot"], prepared, record))
        archives = out / "binaries"
        archives.mkdir()
        files_to_copy = [path for path in (paths["build"] / "Release").iterdir() if path.is_file()
                         and path.suffix.lower() in {".pyd", ".dll", ".exe", ".pdb"}]
        files_to_copy += [paths["build"] / "generated/VkLayer_vispy_submit.json"]
        hashes = {}
        for path in files_to_copy:
            require(path.name not in hashes, "Duplicate native output basename")
            shutil.copyfile(path, archives / path.name)
            hashes[path.name] = sha(archives / path.name)
        require({prepared["expected_native_module"], prepared["expected_sdf_module"], "VkLayer_vispy_submit.dll",
                 "VkLayer_vispy_submit.json"} <= set(hashes), "Required native output archive is incomplete")
        shutil.copyfile(paths["build"] / "CMakeCache.txt", out / "CMakeCache.txt")
        write_json_new(out / "binary-hashes.json", hashes)
    finally:
        if attempt_claimed and (paths["build"] / "CMakeCache.txt").is_file():
            state = {"owner": checked["owner"], "cache_sha256": sha(paths["build"] / "CMakeCache.txt")}
            (paths["evidence"] / "cache-state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        after = native_inventory(root)
        if attempt_claimed:
            write_json_new(out / "protected-source-binaries-after.json", after)
        lock.unlink()
        require(after == checked["protected"], "Protected source native bytes changed during build")
        check_protected(root, record, paths)
    write_json_new(out / "status.json", {"status": "build_and_ctest_passed", "epoch": record["epoch"],
                   "source_tree_sha256": checked["frozen"]["source_tree_sha256"], "sdk_manifest_sha256": record["sdk_manifest_sha256"],
                   "in_place_copy": False, "gpu_qualified": False, "sdk_tint_reader_enabled": False})
    return {**summary(checked), "status": "build_and_ctest_passed", "in_place_copy": False, "gpu_qualified": False}
