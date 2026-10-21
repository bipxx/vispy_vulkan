"""Inventory immutable host sources and imports without constructing a canvas.

Fetching and static scanning do not import the host. Import probes run only in
the explicitly selected Python environment; failures produce evidence and a
nonzero exit status. Rendering admission is a separate upstream GPU operation.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import platform
import sys
import tarfile
import tempfile
import tokenize
import traceback
import urllib.request
import warnings

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "compat/hosts.lock.toml"
HOSTS = ("dive", "napari_threedee", "phylib", "visbrain")
IGNORED = {".git", "__pycache__", ".pytest_cache"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(source: Path) -> list[Path]:
    source = source.resolve(strict=True)
    files = []
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Source inventory cannot follow a symlink: {relative}")
        if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(source).as_posix())


def source_inventory(source: Path) -> dict:
    source = source.resolve(strict=True)
    digest = hashlib.sha256()
    files = []
    for path in source_files(source):
        name = path.relative_to(source).as_posix()
        data = path.read_bytes()
        digest.update(name.encode("utf-8") + b"\0" + data)
        files.append({"path": name, "size": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    return {"algorithm": "sorted-relative-path-nul-file-bytes-sha256",
            "sha256": digest.hexdigest(), "files": files}


def extract_verified(archive: Path, destination: Path, expected_sha256: str) -> Path:
    """Reject an entire archive before extraction if its hash or paths are invalid."""
    if sha256(archive) != expected_sha256:
        raise ValueError("Pinned source archive SHA-256 mismatch")
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to replace a source directory: {destination}")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        roots = set()
        for member in members:
            name = PurePosixPath(member.name)
            if (name.is_absolute() or ".." in name.parts or not name.parts
                    or "\\" in member.name or ":" in member.name):
                raise ValueError(f"Unsafe source archive path: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported source archive member: {member.name}")
            roots.add(name.parts[0])
        if len(roots) != 1:
            raise ValueError("Expected exactly one archive root")
        destination.mkdir(parents=True)
        # Every member above is a regular file/directory with a confined path.
        bundle.extractall(destination, members=members, filter="data")
    return destination / roots.pop()


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.scope = []
        self.imports = []
        self.dynamic_imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({"file": self.path, "line": node.lineno,
                                 "module": alias.name, "names": [], "level": 0,
                                 "scope": ".".join(self.scope)})

    def visit_ImportFrom(self, node):
        self.imports.append({"file": self.path, "line": node.lineno,
                             "module": node.module or "", "level": node.level,
                             "names": [alias.name for alias in node.names],
                             "scope": ".".join(self.scope)})

    def visit_FunctionDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node):
        name = ast.unparse(node.func)
        if name in {"import_module", "__import__"} or name.endswith(".import_module"):
            self.dynamic_imports.append({"file": self.path, "line": node.lineno,
                                         "call": ast.unparse(node),
                                         "scope": ".".join(self.scope)})
        self.generic_visit(node)


def imports_namespace(record: dict, namespace: str) -> bool:
    return record["level"] == 0 and (record["module"] == namespace
                                     or record["module"].startswith(namespace + "."))


def scan(source: Path) -> dict:
    inventory = source_inventory(source)
    records, dynamic, diagnostics = [], [], []
    for file in inventory["files"]:
        if not file["path"].endswith(".py"):
            continue
        path = source / file["path"]
        with tokenize.open(path) as stream:
            content = stream.read()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tree = ast.parse(content, filename=file["path"])
        diagnostics.extend({"file": file["path"], "category": str(item.category.__name__),
                            "line": item.lineno, "message": str(item.message)} for item in caught)
        visitor = ImportVisitor(file["path"])
        visitor.visit(tree)
        records.extend(visitor.imports)
        dynamic.extend(visitor.dynamic_imports)
    return {"schema": 1, "qualification": "source_inventory_only",
            "source": inventory, "imports": records, "dynamic_imports": dynamic,
            "vispy_imports": [item for item in records if imports_namespace(item, "vispy")],
            "qt_imports": [item for item in records
                           if any(imports_namespace(item, namespace)
                                  for namespace in ("PyQt5", "PyQt6", "PySide6", "qtpy"))],
            "parse_diagnostics": diagnostics}


def read_hosts(lock: Path = LOCK) -> dict:
    with lock.open("rb") as stream:
        return tomllib.load(stream)


def fetch(host: str, destination: Path, lock: Path = LOCK) -> Path:
    pin = read_hosts(lock)[host]
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"{host}.tar.gz"
    if archive.exists():
        if sha256(archive) != pin["source_archive_sha256"]:
            raise ValueError(f"Existing archive does not match {host}'s pin")
    else:
        with urllib.request.urlopen(pin["source_archive_url"], timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != pin["source_archive_sha256"]:
            raise ValueError(f"Downloaded archive does not match {host}'s pin")
        archive.write_bytes(data)
    return extract_verified(archive, destination / host, pin["source_archive_sha256"])


def probe(host: str, lock: Path = LOCK) -> dict:
    """Import the recorded modules, never call constructors or rendering methods."""
    pin = read_hosts(lock)[host]
    result = {"schema": 1, "host": host, "qualification": "import_inventory_only",
              "rendering_qualified": False, "python": sys.version,
              "executable": sys.executable, "platform": platform.platform(),
              "inventory_tool_sha256": sha256(Path(__file__)),
              "modules": [], "errors": [], "distributions": []}
    for distribution in sorted(importlib.metadata.distributions(),
                               key=lambda item: item.metadata.get("Name", "")):
        item = {"name": distribution.metadata["Name"], "version": distribution.version}
        wheel_record = distribution.read_text("RECORD")
        if wheel_record:
            item["record_sha256"] = hashlib.sha256(wheel_record.encode("utf-8")).hexdigest()
        result["distributions"].append(item)
    before = set(sys.modules)
    if host != "phylib":
        try:
            if importlib.metadata.version("vispy") != "0.17.0":
                raise ValueError("A host import inventory requires unmodified upstream VisPy 0.17.0")
            import vispy.app
            if not Path(vispy.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):
                raise ValueError("VisPy resolved outside the selected isolated environment")
            vispy.app.use_app(pin["inventory_qt_binding"])
        except Exception:
            result["errors"].append({"module": "vispy.app", "traceback": traceback.format_exc()})
            return result
    for name in pin["import_probe_modules"]:
        try:
            module = importlib.import_module(name)
            origin = getattr(module, "__file__", None)
            item = {"name": name, "origin": origin}
            if origin and Path(origin).is_file():
                item["sha256"] = sha256(Path(origin))
                if not Path(origin).resolve().is_relative_to(Path(sys.prefix).resolve()):
                    raise ValueError(f"{name} resolved outside the selected isolated environment")
            if hasattr(module, "__version__"):
                item["version"] = str(module.__version__)
            result["modules"].append(item)
        except Exception:
            result["errors"].append({"module": name, "traceback": traceback.format_exc()})
    added = sorted(set(sys.modules) - before)
    result["loaded_vispy_modules"] = [name for name in added if name == "vispy" or name.startswith("vispy.")]
    result["loaded_qt_modules"] = [name for name in added
                                   if any(name == prefix or name.startswith(prefix + ".")
                                          for prefix in ("PyQt5", "PyQt6", "PySide6"))]
    package = sys.modules.get(pin["import_probe_modules"][0])
    if package and getattr(package, "__file__", None):
        try:
            result["package_tree_sha256"] = source_inventory(Path(package.__file__).parent)["sha256"]
            if result["package_tree_sha256"] != pin["package_tree_sha256"]:
                raise ValueError("Installed package differs from pinned source")
        except Exception:
            result["errors"].append({"module": package.__name__, "traceback": traceback.format_exc()})
    if host == "phylib" and (result["loaded_vispy_modules"] or result["loaded_qt_modules"]):
        result["errors"].append({"module": "phylib", "error": "CPU probe unexpectedly imported a renderer or Qt binding"})
    return result


def write_record(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=LOCK)
    sub = parser.add_subparsers(dest="command", required=True)
    fetching = sub.add_parser("fetch")
    fetching.add_argument("--host", choices=HOSTS, required=True)
    fetching.add_argument("--directory", type=Path, required=True)
    scanning = sub.add_parser("scan")
    scanning.add_argument("--host", choices=HOSTS, required=True)
    scanning.add_argument("--source", type=Path, required=True)
    scanning.add_argument("--output", type=Path, required=True)
    probing = sub.add_parser("probe")
    probing.add_argument("--host", choices=HOSTS, required=True)
    probing.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "fetch":
        print(fetch(args.host, args.directory, args.lock))
    elif args.command == "scan":
        record = scan(args.source)
        pin = read_hosts(args.lock)[args.host]
        record.update({"host": args.host, "pin": pin.get("commit", pin.get("peeled_commit", pin.get("version"))),
                       "declared_dependencies": pin["declared_dependencies"],
                       "inventory_tool_sha256": sha256(Path(__file__))})
        expected = pin.get("source_tree_sha256")
        if expected and record["source"]["sha256"] != expected:
            raise ValueError(f"{args.host} source tree does not match the pinned inventory")
        write_record(args.output, record)
        print(json.dumps({"host": args.host, "source_sha256": record["source"]["sha256"],
                          "files": len(record["source"]["files"]),
                          "vispy_imports": len(record["vispy_imports"])}))
    else:
        # External probes must not accidentally resolve a checkout package.
        output = args.output.resolve()
        with tempfile.TemporaryDirectory(prefix="vispy-host-probe-") as directory:
            import os
            previous = Path.cwd()
            os.chdir(directory)
            try:
                record = probe(args.host, args.lock)
            finally:
                os.chdir(previous)
        write_record(output, record)
        print(json.dumps({"host": args.host, "modules": len(record["modules"]),
                          "errors": len(record["errors"]), "rendering_qualified": False}))
        return bool(record["errors"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
