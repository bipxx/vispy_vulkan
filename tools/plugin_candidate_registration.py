"""Prove candidate wheel/plugin origins and public discovery without constructing a viewer.

The wheel comes from the exact pinned Git commit and real upstream tag. Public
npe2 discovery and command resolution read the installed entry point; no
synthetic manifest, widget factory execution, graphics context or device is used.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import inspect
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import tomllib
import traceback
import warnings
import zipfile

from host_inventory import source_inventory

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(record: dict, wheel: Path, vispy_wheel: Path) -> None:
    pin = tomllib.loads((ROOT / "compat/hosts.lock.toml").read_text())["napari_threedee"]
    source = ROOT / f"build/host-sources/napari_threedee-{pin['commit']}/napari-threedee-{pin['commit']}"
    assert source_inventory(source)["sha256"] == pin["source_tree_sha256"]
    record["source_commit"] = pin["commit"]
    record["source_tree_sha256"] = pin["source_tree_sha256"]
    record["wheel"] = str(wheel)
    record["wheel_sha256"] = sha256(wheel)
    with zipfile.ZipFile(wheel) as archive:
        version_bytes = archive.read("napari_threedee/_version.py")
        manifest_bytes = archive.read("napari_threedee/napari.yaml")
    os.environ["QT_API"] = "pyqt6"
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6 import QtGui, QtWidgets

    assert QtWidgets.QApplication.instance() is None
    assert QtGui.QOpenGLContext.currentContext() is None
    import napari_threedee
    import napari
    import vispy
    import npe2
    from npe2 import PluginManifest, plugin_manager

    record["modules"] = []
    for module in (napari_threedee, napari, vispy, npe2, QtGui, QtWidgets):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(Path(sys.prefix).resolve()), module.__name__
        record["modules"].append({"name": module.__name__, "origin": str(path),
                                  "sha256": sha256(path),
                                  "version": str(getattr(module, "__version__", ""))})
    assert metadata.version("napari") == "0.9.2"
    assert metadata.version("vispy") == vispy.__version__ == "0.17.0+vulkan.1"
    vispy_dist = metadata.distribution("vispy")
    record["vispy_wheel"] = str(vispy_wheel)
    record["vispy_wheel_sha256"] = sha256(vispy_wheel)
    assert record["vispy_wheel_sha256"] == "e94ab51c4d3ad37333506af3c1b99ea3ce05cccd34bb4ea682e63ad70f2c1c3c"
    with zipfile.ZipFile(vispy_wheel) as archive:
        checked_vispy = []
        for name in archive.namelist():
            if name.endswith("/") or name.endswith(".dist-info/RECORD"):
                continue
            installed_file = Path(vispy_dist.locate_file(name)).resolve()
            assert installed_file.is_relative_to(Path(sys.prefix).resolve())
            assert installed_file.read_bytes() == archive.read(name), name
            checked_vispy.append(name)
    record["vispy_wheel_files_verified"] = checked_vispy
    from vispy import _dawn
    record["native_module"] = {"origin": _dawn.__file__, "sha256": sha256(Path(_dawn.__file__))}
    assert Path(_dawn.__file__).is_relative_to(Path(sys.prefix))
    installed_names = {item.metadata["Name"].lower() for item in metadata.distributions()}
    assert not ({"pyqt5", "pyside6", "pyside2"} & installed_names), "mixed Qt bindings"
    dist = metadata.distribution("napari-threedee")
    assert dist.version == napari_threedee.__version__ == "0.0.29"
    record["version"] = dist.version
    record["distributions"] = []
    for installed in sorted(metadata.distributions(), key=lambda item: item.metadata["Name"]):
        text = installed.read_text("RECORD")
        record["distributions"].append({"name": installed.metadata["Name"], "version": installed.version,
                                         "record_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None})
    record["distribution_files"] = {}
    for name in ("METADATA", "entry_points.txt", "RECORD", "direct_url.json"):
        entry = next(path for path in dist.files if str(path).endswith(".dist-info/" + name))
        path = Path(dist.locate_file(entry)).resolve()
        record["distribution_files"][name] = {"origin": str(path), "sha256": sha256(path)}
    record["direct_url"] = json.loads(dist.read_text("direct_url.json"))
    assert record["direct_url"]["url"] == wheel.as_uri()
    archive_info = record["direct_url"]["archive_info"]
    record["direct_url_archive_sha256"] = archive_info.get("hashes", {}).get("sha256")
    if record["direct_url_archive_sha256"] is not None:
        assert record["direct_url_archive_sha256"] == record["wheel_sha256"]
    # uv's local-wheel direct_url.json may have empty archive_info. The hashed
    # installation lock and byte comparison against this wheel establish origin.
    with zipfile.ZipFile(wheel) as archive:
        checked = []
        for name in archive.namelist():
            if name.endswith("/") or name.endswith(".dist-info/RECORD"):
                continue  # Installer adds its own RECORD entries.
            path = Path(dist.locate_file(name)).resolve()
            assert path.is_relative_to(Path(sys.prefix).resolve()), name
            assert path.read_bytes() == archive.read(name), name
            checked.append(name)
        record["wheel_files_verified_against_installation"] = checked
    entry_points = list(metadata.entry_points(group="napari.manifest", name="napari-threedee"))
    assert len(entry_points) == 1
    entry = entry_points[0]
    assert entry.value == "napari_threedee:napari.yaml"
    record["entry_point"] = {"name": entry.name, "group": entry.group, "value": entry.value,
                              "distribution": entry.dist.metadata["Name"], "version": entry.dist.version}
    package = Path(napari_threedee.__file__).resolve().parent
    original_files = {item["path"]: item["sha256"] for item in source_inventory(source / "src/napari_threedee")["files"]}
    installed_files = {item["path"]: item["sha256"] for item in source_inventory(package)["files"]}
    assert set(installed_files) - set(original_files) == {"_version.py"}
    assert set(original_files) <= set(installed_files)
    assert all(installed_files[name] == digest for name, digest in original_files.items())
    assert (package / "_version.py").read_bytes() == version_bytes
    assert (package / "napari.yaml").read_bytes() == manifest_bytes
    record["installed_source_files"] = installed_files
    record["unchanged_source_file_count"] = len(original_files)
    record["generated_version"] = {"origin": str(package / "_version.py"), "sha256": sha256(package / "_version.py"),
                                     "generation": "unmodified upstream pyproject Hatch VCS build hook"}
    record["installed_manifest"] = {"origin": str(package / "napari.yaml"), "sha256": sha256(package / "napari.yaml")}
    direct = PluginManifest.from_distribution("napari-threedee")
    record["manifest"] = json.loads(direct.json())
    manager = plugin_manager.instance()
    record["discover_count"] = manager.discover(clear=True, include_npe1=False)
    discovered = plugin_manager.get_manifest("napari-threedee")
    assert discovered.name == direct.name == "napari-threedee"
    assert json.loads(discovered.json()) == record["manifest"]
    record["registered_manifest_names"] = sorted(manifest.name for manifest in plugin_manager.iter_manifests())
    assert "napari-threedee" in record["registered_manifest_names"]
    widgets = [widget for widget in plugin_manager.iter_widgets() if widget.command.startswith("napari-threedee.")]
    assert len(widgets) == len(direct.contributions.widgets) == 11
    record["widgets"] = [{"command": widget.command, "display_name": widget.display_name} for widget in widgets]
    record["resolved_commands"] = []
    for command in direct.contributions.commands:
        resolved = manager.commands.get(command.id)
        assert callable(resolved)
        module = importlib.import_module(resolved.__module__)
        path = Path(inspect.getfile(resolved)).resolve()
        assert path.is_relative_to(package), command.id
        record["resolved_commands"].append({"id": command.id, "python_name": command.python_name,
                                            "resolved_name": resolved.__module__ + ":" + resolved.__qualname__,
                                            "module_origin": module.__file__, "origin": str(path),
                                            "sha256": sha256(path), "executed": False})
    assert len(record["resolved_commands"]) == 12
    record["qapplication_created"] = QtWidgets.QApplication.instance() is not None
    record["current_opengl_context"] = QtGui.QOpenGLContext.currentContext() is not None
    record["dawn_modules"] = sorted(name for name in sys.modules if name == "_dawn" or name.endswith("._dawn"))
    record["other_qt_bindings"] = sorted(name for name in sys.modules if name.split(".")[0] in {"PyQt5", "PySide2", "PySide6"})
    assert not record["qapplication_created"] and not record["current_opengl_context"]
    # Importing the ABI leaf verifies its installed origin; this probe calls no
    # renderer entry point and constructs no native instance/device.
    assert record["dawn_modules"] == ["vispy._dawn"]
    assert not record["other_qt_bindings"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--vispy-wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    wheel, output = args.wheel.resolve(strict=True), args.output.resolve()
    vispy_wheel = args.vispy_wheel.resolve(strict=True)
    record = {"qualification": "installed_packaging_and_plugin_registration_cpu_only",
              "python": platform.python_version(), "executable": sys.executable,
              "environment": sys.prefix, "tool_sha256": sha256(Path(__file__)),
              "viewer_constructed": False, "widget_constructed": False,
              "graphics_context_created": False, "graphics_device_created": False,
              "rendering_qualified": False, "errors": []}
    with tempfile.TemporaryDirectory(prefix="napari-plugin-registration-") as directory:
        previous = Path.cwd()
        os.chdir(directory)
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                try:
                    probe(record, wheel, vispy_wheel)
                except Exception:
                    record["errors"].append(traceback.format_exc())
                record["warnings"] = [{"category": warning.category.__name__, "message": str(warning.message),
                                       "filename": warning.filename, "line": warning.lineno} for warning in captured]
        finally:
            os.chdir(previous)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"registration": "passed" if not record["errors"] else "failed",
                      "widgets": len(record.get("widgets", [])),
                      "resolved_commands": len(record.get("resolved_commands", [])),
                      "rendering_qualified": False}))
    return bool(record["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
