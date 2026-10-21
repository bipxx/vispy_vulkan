"""Verify a hash-locked Glue candidate installation without a graphics device."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    import vispy
    from vispy import _dawn
    from vispy.visuals.text import _sdf_cpu
    import glue_vispy_viewers
    from PyQt6 import QtCore, QtGui, QtWidgets
    assert metadata.version("vispy") == vispy.__version__ == "0.17.0+vulkan.1"
    assert metadata.version("glue-vispy-viewers") == "1.4.0"
    assert QtWidgets.QApplication.instance() is None
    assert QtGui.QOpenGLContext.currentContext() is None
    prefix = Path(sys.prefix).resolve()
    package = Path(vispy.__file__).resolve().parent
    host = Path(glue_vispy_viewers.__file__).resolve().parent
    origins = {"vispy": str(package), "native": str(Path(_dawn.__file__).resolve()),
               "sdf": str(Path(_sdf_cpu.__file__).resolve()), "host": str(host),
               "qt_core": str(Path(QtCore.__file__).resolve())}
    assert all(Path(value).is_relative_to(prefix) for value in origins.values())
    assert package != ROOT / "src/vispy"
    installed = {}
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.startswith("vispy/") and not member.endswith("/"):
                target = package / member.removeprefix("vispy/")
                expected = hashlib.sha256(archive.read(member)).hexdigest()
                assert sha(target) == expected, member
                installed[member] = expected
    admission_path = ROOT / "tools/oracle_glue_admission.json"
    admission = json.loads(admission_path.read_text())
    sources = {name: sha(host / name) for name in admission["source_files"]}
    assert all(value == admission["source_files"][name]["sha256"] for name, value in sources.items())
    record = {"qualification": "installed_glue_cpu_import_and_wheel_identity_only",
              "python": sys.version, "executable": sys.executable, "origins": origins,
              "wheel": str(wheel), "wheel_sha256": sha(wheel), "wheel_package_files": installed,
              "host_source_files": sources, "host_admission_sha256": sha(admission_path),
              "distributions": {dist.metadata["Name"].lower().replace("_", "-"): dist.version
                                for dist in metadata.distributions()},
              "qapplication_created": False, "graphics_qualified": False,
              "cpu_tool_sha256": sha(Path(__file__))}
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wheel_sha256": sha(wheel), "installed_files_verified": len(installed),
                      "host_import": "passed", "graphics_qualified": False}))


if __name__ == "__main__":
    main()
