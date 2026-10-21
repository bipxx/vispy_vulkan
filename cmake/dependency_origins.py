"""Verify explicit immutable dependency origins and attach them to a fresh snapshot.

The caller supplies a pinned context, capture packet, independent admission and
the exact new dependency lock. This module never chooses a producer or rewrites
a lock. Baseline native-epoch helpers remain unchanged until integration review.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess


class OriginError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise OriginError(message)


def checksum(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "Invalid SHA256")
    return value


def relative(value):
    require(type(value) is str and value and not any(c in value for c in "\\:\0*?[]"),
            "Unsafe relative origin path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and not ({".", ".."} & set(path.parts)), "Noncanonical origin path")
    return path


def no_alias(path):
    attrs = getattr(path.lstat(), "st_file_attributes", 0)
    require(not path.is_symlink() and not attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0),
            "Immutable origin uses a filesystem alias: " + str(path))


def member(workspace, name):
    workspace = Path(workspace).absolute()
    target = workspace.joinpath(*relative(name).parts)
    require(target.resolve() == target, "Origin uses a filesystem alias")
    for path in (target, *target.parents):
        if path.exists() or path.is_symlink():
            no_alias(path)
        if path == workspace:
            break
    return target


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, "Duplicate JSON key")
        result[name] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(OriginError("Nonfinite JSON")))


def reference(workspace, row):
    require(type(row) is dict and set(row) == {"path", "sha256"}, "Invalid pinned reference")
    path = member(workspace, row["path"])
    require(path.is_file() and sha(path) == checksum(row["sha256"]), "Changed pinned origin input")
    return path, load(path)


def inventory(root):
    root = Path(root)
    require(root.is_dir(), "Missing physical origin tree")
    no_alias(root)
    files = []
    for parent, directories, names in os.walk(root):
        for name in [*directories, *names]:
            no_alias(Path(parent) / name)
        files.extend(Path(parent) / name for name in names)
    files.sort(key=lambda path: path.relative_to(root).as_posix())
    with ThreadPoolExecutor(max_workers=8) as executor:
        return {path.relative_to(root).as_posix(): digest
                for path, digest in zip(files, executor.map(sha, files))}


def tree_digest(files):
    require(type(files) is dict and files, "Missing immutable source inventory")
    digest = hashlib.sha256()
    for name, value in sorted(files.items()):
        relative(name)
        digest.update(name.encode("utf-8") + b"\0" + bytes.fromhex(checksum(value)))
    return digest.hexdigest()


def packet(workspace, row):
    require(type(row) is dict and set(row) == {"path", "sha256", "seal_path", "seal_sha256"},
            "Invalid whole-packet reference")
    path, result = reference(workspace, {key: row[key] for key in ("path", "sha256")})
    seal_path, seal = reference(workspace, {"path": row["seal_path"], "sha256": row["seal_sha256"]})
    require(path.name == "result.json" and seal_path == path.parent / "seal.json", "Packet roots differ")
    actual = inventory(path.parent)
    require(type(seal.get("artifact_hashes")) is dict
            and actual == seal["artifact_hashes"] | {"seal.json": row["seal_sha256"]}, "Whole packet differs")
    return result, seal, {str((path.parent / name).relative_to(workspace)).replace("\\", "/"): value
                          for name, value in actual.items()}


def verify_origins(workspace, *, context, capture, admission, dependency_lock):
    """Return verified mappings; all reads finish before snapshot mutation."""
    workspace = Path(workspace).absolute()
    context_path, record = reference(workspace, context)
    lock_path = Path(dependency_lock).absolute()
    require(lock_path.is_file() and sha(lock_path) == record["dependency_lock"]["sha256"],
            "Project and origin dependency locks differ")
    _, lock = reference(workspace, record["dependency_lock"])
    require(record["schema"] == 1 and record["scope"] == "explicit_immutable_dependency_origins"
            and lock["schema"] == 1 and lock["digest_algorithm"] ==
            "sha256(sorted relative path + NUL + file SHA256 bytes)", "Origin/lock schema differs")
    require(all(record.get(key) is False for key in
                ("dependency_lock_promoted", "SDK_staged", "native_imported", "device_created", "GPU_used")),
            "Captured origin scope differs")
    captured, seal, required = packet(workspace, capture)
    require(context_path.parent == member(workspace, capture["path"]).parent,
            "Context is outside its capture packet")
    require(captured["status"] == "passed_origin_capture" and type(captured["process_exit"]) is int
            and captured["process_exit"] == 0 and captured["error"] is None
            and captured["origin_context_sha256"] == context["sha256"]
            and captured["new_lock_sha256"] == record["dependency_lock"]["sha256"],
            "Origin capture did not pass")
    require(captured["scope"] == "patched_dependency_origin_capture_only"
            and captured["source_copy_only"] is True
            and all(captured[key] is False for key in
                    ("child_launched", "compiled", "tests_run", "dependency_lock_promoted", "SDK_staged",
                     "native_imported", "device_created", "GPU_used")), "Capture scope differs")
    require(captured["protected_native_before"] == captured["protected_native_after"],
            "Origin capture changed protected native bytes")
    physical = member(workspace, seal["physical_root"])
    complete = inventory(physical)
    require(complete == seal["physical_file_hashes"] == captured["complete_physical_files"]
            and captured["physical_root"] == seal["physical_root"], "Physical capture inventory differs")
    required.update({(physical / name).relative_to(workspace).as_posix(): value
                     for name, value in complete.items()})
    _, policy = reference(workspace, record["source_exclusion_policy"])
    require(policy["schema"] == 1 and policy["scope"] == "explicit_source_output_exclusion_policy"
            and policy["directory_name_exclusions"] == []
            and policy["source_bearing_build_directories_retained"] is True
            and policy["output_products_captured_as_source"] is False, "Origin exclusion policy differs")
    required[record["source_exclusion_policy"]["path"]] = record["source_exclusion_policy"]["sha256"]
    dependencies = lock["dependencies"]
    origins = record["origins"]
    require(type(dependencies) is list and type(origins) is list and dependencies and origins,
            "Missing dependency mappings")
    names = [row["name"] for row in dependencies]
    logical_names = [row["path"] for row in dependencies]
    require(len(names) == len(set(names)) and len(logical_names) == len(set(logical_names))
            and len(origins) == len(dependencies), "Duplicate/missing dependency mapping")
    require({row["name"] for row in origins} == set(names), "Origin dependency identities differ")
    _, upstream = reference(workspace, record["upstream_lock"])
    upstream_rows = {row["name"]: row for row in upstream["dependencies"]}
    require(len(upstream_rows) == len(upstream["dependencies"]) and set(upstream_rows) == set(names)
            and upstream["digest_algorithm"] == lock["digest_algorithm"], "Upstream identities differ")
    required[record["upstream_lock"]["path"]] = record["upstream_lock"]["sha256"]
    mapped = {}
    for origin in origins:
        dependency = next(row for row in dependencies if row["name"] == origin["name"])
        logical = origin["logical_root"]
        relative(logical)
        require(logical.startswith("third_party/") and logical == dependency["path"]
                and logical not in mapped and dependency["exclude_directory_names"] == [],
                "Logical root or digest policy differs")
        require(dependency["path"] == upstream_rows[dependency["name"]]["path"]
                and dependency["revision"] == upstream_rows[dependency["name"]]["revision"],
                "Upstream logical identity was rewritten")
        root = member(workspace, origin["physical_root"])
        require(root.is_relative_to(physical) and root != physical, "Origin is outside physical capture")
        _, manifest = reference(workspace, origin["physical_manifest"])
        files = manifest["files"]
        require(manifest["schema"] == 1 and manifest["scope"] == "immutable_qualified_dependency_file_inventory"
                and manifest["physical_root"] == origin["physical_root"]
                and manifest["upstream_revision"] == origin["upstream_revision"] == dependency["revision"]
                and type(dependency["file_count"]) is int and len(files) == dependency["file_count"]
                and tree_digest(files) == manifest["tree_sha256"] == origin["tree_sha256"] == dependency["tree_sha256"]
                and origin["source_exclusion_policy"] == record["source_exclusion_policy"],
                "Dependency lineage/inventory differs")
        require(not any(name.endswith((".pyc", ".pyo")) for name in files), "Origin contains Python bytecode")
        prefix = root.relative_to(physical).as_posix() + "/"
        require({name[len(prefix):]: value for name, value in complete.items() if name.startswith(prefix)} == files,
                "Dependency source view differs from capture")
        required[origin["physical_manifest"]["path"]] = origin["physical_manifest"]["sha256"]
        mapped[logical] = {"physical_root": root, "files": files, "name": origin["name"]}
    for parent, parent_row in mapped.items():
        for child, child_row in mapped.items():
            if child.startswith(parent + "/"):
                suffix = child[len(parent) + 1:]
                require(child_row["physical_root"] == parent_row["physical_root"] / suffix,
                        "Nested origin has a conflicting physical identity")
                require({name[len(suffix) + 1:]: value for name, value in parent_row["files"].items()
                         if name.startswith(suffix + "/")} == child_row["files"], "Nested source views differ")
    admitted, _, _ = packet(workspace, admission)
    require(admitted["status"] == "CLEAR_WITH_SCOPE" and admitted["scope"] == "explicit_immutable_dependency_origins"
            and type(admitted["process_exit"]) is int and admitted["process_exit"] == 0
            and admitted["material_findings"] == []
            and all(admitted[key] is False for key in ("native_imported", "device_created", "GPU_used")),
            "Independent origin admission did not clear")
    required[context["path"]] = context["sha256"]
    required[record["dependency_lock"]["path"]] = record["dependency_lock"]["sha256"]
    scope = admitted["verified_scope"]
    require(scope["dependency_lock"] == record["dependency_lock"] and scope["origin_context"] == context
            and scope["complete_physical_source_and_dependency_inventory_admitted"] is True,
            "Independent admitted origin role differs")
    require(type(admitted["checked_inputs"]) is dict and all(admitted["checked_inputs"].get(name) == value
            for name, value in required.items()), "Independent admission omits exact captured inputs")
    for name, value in admitted["checked_inputs"].items():
        require(sha(member(workspace, name)) == checksum(value), "Admitted origin input changed")
    return mapped


def verify_snapshot(snapshot, mappings):
    snapshot = Path(snapshot).absolute()
    for logical, row in mappings.items():
        target = snapshot.joinpath(*relative(logical).parts)
        require(target.is_dir() and target.resolve() == row["physical_root"], "Snapshot origin identity differs")
        if not any(logical.startswith(parent + "/") for parent in mappings if parent != logical):
            require(inventory(row["physical_root"]) == row["files"], "Snapshot physical source changed")
    return True


def link_snapshot(snapshot, mappings):
    """Create only minimal approved roots in a new snapshot; retain failed output."""
    snapshot = Path(snapshot).absolute()
    no_alias(snapshot)
    roots = {name: row for name, row in mappings.items()
             if not any(name.startswith(parent + "/") for parent in mappings if parent != name)}
    targets = [(snapshot.joinpath(*relative(name).parts), row["physical_root"]) for name, row in sorted(roots.items())]
    for target, source in targets:
        require(not target.exists() and not target.is_symlink(), "Snapshot origin destination already exists")
        require(target.is_relative_to(snapshot), "Snapshot destination escapes")
        member(snapshot, target.relative_to(snapshot).as_posix())
        require(inventory(source) == roots[target.relative_to(snapshot).as_posix()]["files"],
                "Physical origin changed before linking")
    for target, source in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            script = "New-Item -ItemType Junction -Path " + quote(target) + " -Target " + quote(source) + " | Out-Null"
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], check=True)
        else:
            target.symlink_to(source, target_is_directory=True)
    return verify_snapshot(snapshot, mappings)
