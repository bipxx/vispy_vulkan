"""Validate the supplied dependency sources without network fetches.

The tree digest hashes sorted POSIX relative paths, a NUL separator, and each
file's SHA256 bytes. Source files are hashed byte for byte. Generated caches
and build products are excluded explicitly in the lock, never by Git state.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "cmake" / "dependencies.lock.json"


def source_digest(path: Path, exclusions: list[str]) -> tuple[str, int]:
    # Isolated wheel sources may link to immutable dependencies. Read their
    # physical paths so Windows does not exceed MAX_PATH through a long alias.
    path = path.resolve()
    ignored = set(exclusions)
    paths = []
    for directory, subdirs, filenames in __import__("os").walk(path):
        subdirs[:] = [name for name in subdirs if name not in ignored]
        for name in filenames:
            if name in ignored or name.endswith((".pyc", ".pyo")):
                continue
            paths.append(Path(directory) / name)
    paths.sort(key=lambda file: file.relative_to(path).as_posix())
    digest = hashlib.sha256()
    # Windows file scanning has substantial per-file latency for Dawn's shader
    # corpus. Bounded parallel reads retain the same deterministic digest.
    with ThreadPoolExecutor(max_workers=8) as executor:
        checksums = executor.map(lambda file: hashlib.sha256(file.read_bytes()).digest(), paths)
        for file, checksum in zip(paths, checksums):
            digest.update(file.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(checksum)
    return digest.hexdigest(), len(paths)


def verify() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    errors = []
    for dependency in lock["dependencies"]:
        path = ROOT / dependency["path"]
        if not path.is_dir():
            errors.append(f"{dependency['name']}: missing {path}")
            continue
        digest, count = source_digest(path, dependency["exclude_directory_names"])
        if digest != dependency["tree_sha256"] or count != dependency["file_count"]:
            errors.append(f"{dependency['name']}: source checksum mismatch ({digest}, {count} files)")
    if errors:
        raise RuntimeError("Vendored sources differ from immutable pins:\n" + "\n".join(errors))
    print(f"Verified {len(lock['dependencies'])} immutable dependency source trees")


def verify_origins(args):
    # This authority is distinct from ROOT, which may be a fresh snapshot.
    workspace = Path(args.origin_workspace)
    if not workspace.is_absolute() or workspace.resolve() != workspace.absolute():
        raise RuntimeError("Origin authority workspace must be canonical and absolute")
    path = ROOT / "cmake/dependency_origins.py"
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != args.origin_module_sha256:
        raise RuntimeError("Owned dependency-origin module changed")
    spec = importlib.util.spec_from_file_location("vispy_dependency_origins", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(data, str(path), "exec"), module.__dict__)
    mappings = module.verify_origins(
        workspace,
        context={"path": args.origin_context, "sha256": args.origin_context_sha256},
        capture={"path": args.origin_capture, "sha256": args.origin_capture_sha256,
                 "seal_path": args.origin_capture_seal, "seal_sha256": args.origin_capture_seal_sha256},
        admission={"path": args.origin_admission, "sha256": args.origin_admission_sha256,
                   "seal_path": args.origin_admission_seal, "seal_sha256": args.origin_admission_seal_sha256},
        dependency_lock=args.dependency_lock)
    if not args.origin_preflight_only:
        module.verify_snapshot(ROOT, mappings)
    print(f"Verified {len(mappings)} explicit immutable dependency source origins")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    names = ("workspace", "module-sha256", "context", "context-sha256", "capture", "capture-sha256",
             "capture-seal", "capture-seal-sha256", "admission", "admission-sha256",
             "admission-seal", "admission-seal-sha256")
    for name in names:
        parser.add_argument("--origin-" + name)
    parser.add_argument("--origin-preflight-only", action="store_true")
    parser.add_argument("--dependency-lock", type=Path)
    args = parser.parse_args()
    values = [getattr(args, "origin_" + name.replace("-", "_")) for name in names]
    if any(value is not None for value in values) or args.origin_preflight_only:
        if not all(type(value) is str and value for value in values) or args.dependency_lock is None:
            parser.error("Explicit origin mode requires every origin argument and its bound dependency lock")
        verify_origins(args)
    else:
        if args.dependency_lock is not None:
            parser.error("A separate dependency lock requires explicit origin authority")
        verify()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
