"""Required native/CPU build inputs and notices are present and immutable."""

import hashlib
import json
from pathlib import Path
import re
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.markers import Marker, default_environment
from packaging.utils import parse_wheel_filename
from urllib.parse import unquote, urlsplit
try:
    import tomllib
except ImportError:  # CPython 3.10 qualification
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


def test_locked_pyqt5_runtime_has_wheels_for_each_target_platform():
    """A universal lock must not select Linux/macOS-only Qt for Windows."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    runtimes = [p for p in lock["package"] if p["name"] == "pyqt5-qt5"]
    for version in ("3.10.19", "3.11.14", "3.12.8", "3.13.8", "3.14.0"):
        for platform, wheel_platform in (("win32", "win_amd64"),
                                         ("linux", "manylinux2014_x86_64"),
                                         ("darwin", "macosx_10_13_x86_64")):
            environment = dict(default_environment(), sys_platform=platform,
                               python_full_version=version,
                               python_version=".".join(version.split(".")[:2]))
            selected = [p for p in runtimes if not p.get("resolution-markers") or any(
                Marker(marker).evaluate(environment) for marker in p["resolution-markers"])]
            assert len(selected) == 1, (version, platform, "one Qt runtime required")
            runtime = selected[0]
            tags = {tag for wheel in runtime.get("wheels", [])
                    for tag in parse_wheel_filename(unquote(urlsplit(wheel["url"]).path.rsplit("/", 1)[1]))[3]}
            assert any(tag.platform == wheel_platform for tag in tags), (version, platform, runtime["version"])
            assert all(wheel["hash"].startswith("sha256:") for wheel in runtime["wheels"])


def test_build_dependencies_and_host_lock():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    build_dependencies = project["build-system"]["requires"]
    for dependency in ("Cython", "numpy", "cmake", "nanobind", "scikit-build-core"):
        assert any(requirement.startswith(dependency + "==") for requirement in build_dependencies), dependency
    assert "napari==0.9.2; python_version >= '3.11'" in project["dependency-groups"]["hosts"]
    assert project["tool"]["scikit-build"]["editable"]["mode"] == "redirect"
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    napari = [package for package in lock["package"] if package["name"] == "napari"]
    assert len(napari) == 1 and napari[0]["version"] == "0.9.2"
    assert all(wheel["hash"].startswith("sha256:") for wheel in napari[0]["wheels"])


def test_numpy_build_marker_allows_python310_and311_from_primary_metadata():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    primary = json.loads((ROOT / "compat/cp310-candidate/numpy-build-compatibility.json").read_text())
    metadata = {item["version"]: item for item in primary["primary_metadata"]}
    numpy = [Requirement(text) for text in project["build-system"]["requires"]
             if Requirement(text).name.lower() == "numpy"]
    for target in ("3.10.16", "3.11.11"):
        active = [requirement for requirement in numpy if not requirement.marker
                  or requirement.marker.evaluate({"python_version": ".".join(target.split(".")[:2]),
                                                   "python_full_version": target})]
        assert len(active) == 1, (target, "exactly one build NumPy pin must apply")
        pins = [pin.version for pin in active[0].specifier if pin.operator == "=="]
        assert len(pins) == 1
        assert SpecifierSet(metadata[pins[0]]["requires_python"]).contains(target), (
            target, "selected build NumPy does not support the declared Python version")
        if target.startswith("3.10."):
            assert metadata[pins[0]]["windows_cpython310_wheels"], "build needs a primary CPython310 Windows wheel"


def test_native_source_pins_and_presets():
    lock = json.loads((ROOT / "cmake/dependencies.lock.json").read_text())
    names = {dependency["name"] for dependency in lock["dependencies"]}
    assert {"dawn", "vispy", "glslang", "spirv-tools", "spirv-headers", "vulkan-headers", "abseil-cpp"} <= names
    for dependency in lock["dependencies"]:
        assert re.fullmatch(r"[0-9a-f]{40}", dependency["revision"]), dependency
        assert re.fullmatch(r"[0-9a-f]{64}", dependency["tree_sha256"]), dependency
        assert dependency["file_count"] > 0
    presets = json.loads((ROOT / "CMakePresets.json").read_text())
    windows = next(preset for preset in presets["configurePresets"] if preset["name"] == "windows-release")
    assert windows["architecture"] == "x64"
    assert "build/" in windows["binaryDir"]
    assert windows["cacheVariables"]["VISPY_VERIFY_DEPENDENCIES"] == "ON"


def test_all_linked_native_and_font_notices_are_included():
    directory = ROOT / "third_party/licenses"
    manifest = json.loads((directory / "manifest.json").read_text())
    expected = {
        "vispy-LICENSE.txt", "dawn-LICENSE.txt", "glslang-LICENSE.txt",
        "spirv-tools-LICENSE.txt", "spirv-headers-LICENSE.txt", "abseil-LICENSE.txt",
        "vulkan-headers-LICENSE.txt", "vulkan-loader-LICENSE.txt",
        "vulkan-utility-libraries-LICENSE.txt", "webgpu-headers-LICENSE.txt",
        "nanobind-LICENSE.txt", "robin-map-LICENSE.txt", "OpenSans-Apache-2.0.txt",
    }
    assert expected <= set(manifest)
    for name, digest in manifest.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
    notice = (directory / "THIRD-PARTY-NOTICES.txt").read_text()
    assert "1.10" in notice and "2010-2011" in notice
