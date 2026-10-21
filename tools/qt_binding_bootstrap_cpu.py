"""Verify one installed Qt/VisPy row without native VisPy imports or a GUI.

Run with the row's interpreter and -I -B. Backend selection is public bootstrap,
not QApplication/Canvas construction or graphics qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.metadata as metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class NoVisPyNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "vispy._dawn" or fullname.endswith("._sdf_cpu"):
            raise RuntimeError("CPU bootstrap prohibits VisPy native import: " + fullname)
        return None


def verify_wheel(wheel, prefix, expected_sha):
    require(sha(wheel) == expected_sha, "Exact immutable VisPy wheel required")
    verified = {}
    base = prefix / "Lib/site-packages"
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith("/") or name.endswith("/RECORD"):
                continue
            require(not Path(name).is_absolute() and ".." not in Path(name).parts,
                    "Unsafe wheel member")
            target = base / name
            require(target.is_file(), "Installed wheel member absent: " + name)
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            require(sha(target) == digest, "Installed immutable wheel member differs: " + name)
            verified[name] = digest
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", choices=("pyqt5", "pyside6"), required=True)
    parser.add_argument("--kind", choices=("upstream", "candidate-w10"), required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--expected-packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Fresh CPU bootstrap evidence required")
    record = {"schema": 1, "status": "failed", "kind": args.kind,
              "binding": args.binding, "python": sys.version, "executable": sys.executable,
              "prefix": sys.prefix, "cwd": str(Path.cwd()), "GPU_used": False,
              "native_imported": False, "application_created": False, "errors": [],
              "bootstrap_helper_sha256": sha(__file__)}
    prefix = Path(sys.prefix).resolve()
    try:
        require(sys.version_info[:3] == (3, 12, 8) and sys.platform == "win32",
                "Pinned Windows CPython3.12.8 row required")
        expected = json.loads(args.expected_packages.read_text(encoding="utf-8"))
        versions = {d.metadata["Name"].lower().replace("_", "-"): d.version
                    for d in metadata.distributions()}
        require(versions == expected, "Installed distribution versions/inventory differ")
        chosen = {"pyqt5": "PyQt5", "pyside6": "PySide6"}[args.binding]
        other = {"PyQt5", "PyQt6", "PySide2", "PySide6"} - {chosen}
        require(not any(name.lower() in versions for name in other), "Mixed Qt bindings")
        record["versions"] = versions
        record["distribution_origins"] = {
            d.metadata["Name"]: {"version": d.version,
                "metadata_origin": str(d.locate_file("")),
                "record_sha256": hashlib.sha256((d.read_text("RECORD") or "").encode()).hexdigest()}
            for d in metadata.distributions()}
        wheel_files = verify_wheel(args.wheel.resolve(), prefix, args.wheel_sha256)
        record["wheel"] = str(args.wheel.resolve())
        record["wheel_sha256"] = args.wheel_sha256
        record["installed_wheel_files_verified"] = len(wheel_files)
        record["installed_wheel_member_hashes"] = wheel_files
        os.environ["QT_API"] = args.binding
        sys.meta_path.insert(0, NoVisPyNative())
        import vispy
        from vispy import app
        application = app.use_app(args.binding, call_reuse=False)
        backend = application.backend_module
        require(args.binding in application.backend_name.lower(), "Public Qt backend selection differs")
        require(backend.available is True, "Pinned Qt backend is unavailable")
        qt = backend._qt
        require(qt.QtWidgets.QApplication.instance() is None, "Bootstrap created an application")
        require(qt.QtGui.QOpenGLContext.currentContext() is None, "Bootstrap created a context")
        package = Path(vispy.__file__).resolve().parent
        require(package == prefix / "Lib/site-packages/vispy", "Installed VisPy origin differs")
        require(vispy.__version__ == versions["vispy"], "VisPy module/distribution versions differ")
        for name in ("vispy", "vispy.app", backend.__name__, qt.__name__,
                     chosen + ".QtCore", chosen + ".QtGui", chosen + ".QtWidgets"):
            module = sys.modules[name]
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(prefix), "CPU module origin escapes isolated row: " + name)
            record.setdefault("module_origins", {})[name] = {"path": str(path), "sha256": sha(path)}
        native = package / "_dawn.cp312-win_amd64.pyd"
        record["native_file_present_but_not_imported"] = native.is_file()
        if native.is_file():
            record["native_file_sha256"] = sha(native)
        require("vispy._dawn" not in sys.modules and not any(n.endswith("._sdf_cpu") for n in sys.modules),
                "CPU bootstrap imported a VisPy native leaf")
        require(not any(n.split(".", 1)[0] in other for n in sys.modules), "Another Qt binding imported")
        record["backend_name"] = application.backend_name
        record["backend_capability"] = backend.capability
        record["Qt_API"] = os.environ["QT_API"]
        record["status"] = "CPU_BOOTSTRAP_PASSED"
        record["graphics_qualification"] = "pending; installed w10 candidate is historical, not pass29"
    except BaseException:
        record["errors"].append(traceback.format_exc())
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True); stream.write("\n")
    print(json.dumps({"status": record["status"], "kind": args.kind,
                      "binding": args.binding, "native_imported": False,
                      "GPU_used": False, "output": str(args.output), "sha256": sha(args.output)}))
    return 0 if record["status"] == "CPU_BOOTSTRAP_PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
