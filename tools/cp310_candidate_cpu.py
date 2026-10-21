"""Verify installed CP310 NumPy1.26 ABI, font/SDF and optional DIVE imports, CPU only."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--external", action="store_true")
    parser.add_argument("--dive", action="store_true")
    args = parser.parse_args()
    wheel, output = args.wheel.resolve(strict=True), args.output.resolve()
    prefix = Path(sys.prefix).resolve()
    assert platform.python_version() == "3.10.16"
    if args.external:
        assert not prefix.is_relative_to(ROOT)
    assert not any(Path(path).resolve().is_relative_to(ROOT / "src") for path in sys.path if path)
    os.environ["QT_API"] = "pyside2"
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import numpy as np
    import vispy
    from vispy import _dawn
    from vispy.util.fonts import _load_glyph
    from vispy.visuals.text import _sdf_cpu

    assert np.__version__ == "1.26.4"
    assert metadata.version("vispy") == vispy.__version__ == "0.17.0+vulkan.1"
    dist = metadata.distribution("vispy")
    verified = []
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith("/") or name.endswith(".dist-info/RECORD"):
                continue
            installed = Path(dist.locate_file(name)).resolve()
            assert installed.is_relative_to(prefix) and installed.read_bytes() == archive.read(name), name
            verified.append(name)
    origins = {}
    for module in (np, vispy, _dawn, _sdf_cpu):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(prefix)
        origins[module.__name__] = {"origin": str(path), "sha256": sha(path)}
    assert _dawn.__file__.endswith(".cp310-win_amd64.pyd")
    assert _sdf_cpu.__file__.endswith(".cp310-win_amd64.pyd")
    package = Path(vispy.__file__).parent
    notices = package / "_licenses"
    for name, expected in json.loads((notices / "manifest.json").read_text()).items():
        assert sha(notices / name) == expected, name
    glyphs = {}
    _load_glyph(dict(face="OpenSans", size=32, bold=False, italic=False), "R", glyphs)
    field = np.pad(glyphs["R"]["bitmap"].astype(np.float32) / 255, 8)
    before = field.copy()
    assert _sdf_cpu._calc_distance_field(field, field.shape[1], field.shape[0], 8) is None
    assert np.isfinite(field).all() and not np.array_equal(field, before)
    record = {"qualification": "installed_cp310_numpy126_sdf_and_imports_cpu_only",
              "python": platform.python_version(), "environment": str(prefix),
              "external_to_checkout": not prefix.is_relative_to(ROOT), "numpy": np.__version__,
              "wheel": str(wheel), "wheel_sha256": sha(wheel), "tool_sha256": sha(Path(__file__)),
              "wheel_files_verified": verified, "module_origins": origins,
              "font_and_compiled_sdf_verified": True, "assets_notices_verified": True,
              "graphics_context_created": False, "graphics_device_created": False,
              "graphics_qualified": False, "rollback_qualified": False}
    if args.dive:
        import DIVE
        from PySide2 import QtGui, QtWidgets
        sys.path.insert(0, str(ROOT / "tools"))
        from host_inventory import source_inventory
        inventory = source_inventory(Path(DIVE.__file__).parent)
        assert inventory["sha256"] == "545fef99d793c155a9e04441b41d54ce3a3964e5ace1005e5f90ee50353cd026"
        assert issubclass(DIVE.DIVEWidget, QtWidgets.QWidget)
        assert QtWidgets.QApplication.instance() is None
        assert QtGui.QOpenGLContext.currentContext() is None
        assert hasattr(QtWidgets, "QAction") and hasattr(QtWidgets, "QActionGroup")
        names = {item.metadata["Name"].lower(): item.version for item in metadata.distributions()}
        assert {name for name in names if name in {"pyqt5", "pyqt6", "pyside2", "pyside6"}} == {"pyside2"}
        record["dive"] = {"origin": DIVE.__file__, "package_tree_sha256": inventory["sha256"],
                          "public_widget": "DIVE.DIVEWidget", "widget_constructed": False,
                          "binding": "PySide2", "binding_version": names["pyside2"]}
    record["distributions"] = [{"name": item.metadata["Name"], "version": item.version}
                               for item in sorted(metadata.distributions(), key=lambda x: x.metadata["Name"])]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"python": record["python"], "numpy": record["numpy"],
                      "sdf": "passed", "dive_import": args.dive, "graphics_qualified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
