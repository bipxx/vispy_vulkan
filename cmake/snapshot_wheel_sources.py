"""Freeze project inputs while sharing checksum-verified immutable dependencies.

The destination must be new. Native build products and Python caches are not
source inputs. Dependency trees remain shared and must pass the dependency
verifier both before and after the wheel build.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def link_directory(source: Path, destination: Path) -> None:
    if os.name == "nt":
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "New-Item -ItemType Junction -Path " + quote(destination)
             + " -Target " + quote(source) + " | Out-Null"],
            check=True,
        )
    else:
        destination.symlink_to(source, target_is_directory=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--runtime-snapshot", type=Path,
                        help="Use exact cpp/src from an existing immutable milestone instead of the live checkout")
    parser.add_argument("--expected-runtime-sha256",
                        help="Trusted source_tree_sha256 of the selected runtime milestone")
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        parser.error("The snapshot destination must not already exist")
    runtime = None
    runtime_manifest = None
    if args.runtime_snapshot:
        runtime = args.runtime_snapshot.resolve(strict=True)
        runtime_manifest = json.loads((runtime / "wheel-source-manifest.json").read_text(encoding="utf-8"))
        if not args.expected_runtime_sha256 or runtime_manifest["source_tree_sha256"] != args.expected_runtime_sha256:
            parser.error("The frozen runtime milestone does not match its trusted source digest")
    elif args.expected_runtime_sha256:
        parser.error("A runtime snapshot is required with its trusted digest")
    destination.mkdir(parents=True)
    inputs: dict[str, str] = {}
    ignored = {"__pycache__", ".pytest_cache", ".git"}
    for relative in (
        "CMakeLists.txt", "CMakePresets.json", "pyproject.toml", "uv.lock", "README.md",
        "LICENSE", "LICENSE-BSD", "LICENSING.md", "compat/runtime-package.json",
        "cmake", "cpp", "src", "third_party/licenses",
    ):
        base = runtime if runtime is not None and relative in {"cpp", "src"} else ROOT
        source = base / relative
        files = [source] if source.is_file() else sorted(source.rglob("*"))
        for file in files:
            if not file.is_file() or any(part in ignored for part in file.relative_to(source if source.is_dir() else ROOT).parts):
                continue
            if file.suffix.lower() in {".pyd", ".dll", ".so", ".pyc", ".pyo"}:
                continue
            path = file.relative_to(base)
            if path.as_posix() == "src/vispy/VkLayer_vispy_submit.json":
                continue
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            # Hash precisely the bytes written, even if source work resumes.
            data = file.read_bytes()
            if base == runtime and hashlib.sha256(data).hexdigest() != runtime_manifest["source_files"].get(path.as_posix()):
                raise ValueError(f"Frozen runtime file changed or is untracked: {path}")
            target.write_bytes(data)
            inputs[path.as_posix()] = hashlib.sha256(data).hexdigest()
    if runtime is not None:
        expected = {key: value for key, value in runtime_manifest["source_files"].items()
                    if key.startswith(("cpp/", "src/"))}
        observed = {key: value for key, value in inputs.items() if key.startswith(("cpp/", "src/"))}
        if expected != observed:
            raise ValueError("Frozen runtime inventory changed while capturing the leaf snapshot")
    for relative in ("third_party/dawn", "third_party/parity"):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        link_directory(ROOT / relative, target)
    digest = hashlib.sha256()
    for relative, checksum in sorted(inputs.items()):
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(checksum))
    manifest = {
        "schema": 1,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "original_checkout": str(ROOT),
        "snapshot": str(destination),
        "source_tree_sha256": digest.hexdigest(),
        "source_files": inputs,
        "shared_immutable_dependencies": json.loads((destination / "cmake/dependencies.lock.json").read_text())["dependencies"],
        "dependency_verification_required": "before and after the wheel build",
    }
    if runtime is not None:
        manifest["runtime_milestone"] = {
            "snapshot": str(runtime), "source_tree_sha256": runtime_manifest["source_tree_sha256"],
            "manifest_sha256": hashlib.sha256((runtime / "wheel-source-manifest.json").read_bytes()).hexdigest(),
            "content": "exact frozen cpp/src; current reviewed packaging inputs",
        }
    (destination / "wheel-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("snapshot", "source_tree_sha256", "captured_utc")}))
    print(f"Copied {len(inputs)} project source files; native/Python sources are now isolated")


if __name__ == "__main__":
    main()
