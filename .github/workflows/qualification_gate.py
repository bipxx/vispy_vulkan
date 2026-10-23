"""CI evidence and admission gates. Missing work is an error, never a skip."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(options):
    packages = {distribution.metadata["Name"]: distribution.version for distribution in metadata.distributions()}
    commands = {}
    for command in (["uv", "--version"], ["cmake", "--version"], ["git", "rev-parse", "HEAD"]):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        commands[command[0]] = {"code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    result = {
        "python": sys.version, "python_executable": sys.executable,
        "python_executable_sha256": digest(sys.executable),
        "base_python_executable": sys._base_executable,
        "base_python_executable_sha256": digest(sys._base_executable),
        "platform": platform.platform(), "machine": platform.machine(),
        "packages": packages, "commands": commands,
        "input_sha256": {str(path): digest(path) for path in
                         (Path("uv.lock"), Path("pyproject.toml"), Path("cmake/dependencies.lock.json"))},
        "environment": {key: os.environ.get(key) for key in
                        ("QT_API", "QT_QPA_PLATFORM", "QT_SCALE_FACTOR", "DISPLAY", "VK_DRIVER_FILES",
                         "MACOSX_DEPLOYMENT_TARGET", "ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH")},
        "fork_origin": None,
    }
    if not options.without_package:
        import vispy
        result["fork_origin"] = vispy.__file__
        result["fork_version"] = vispy.__version__
    if options.gpu:
        assert not options.without_package
        from vispy import _dawn
        info = _dawn.device_info()
        result["device"] = info
        result["native_origin"] = _dawn.__file__
        result["native_sha256"] = digest(_dawn.__file__)
        result["probe"] = _dawn.probe()
        write(options.output, result)
        assert info["ok"], info
        assert info["backend"] == options.backend, info
        assert info["software"] is options.software, info
        if not options.software:
            assert info["adapter_type"] != "cpu", info
        assert Path(vispy.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), vispy.__file__
    write(options.output, result)


def validate_platform(options):
    expected = {"windows": ("Windows", {"AMD64", "x86_64"}),
                "linux-x11": ("Linux", {"x86_64", "AMD64"}),
                "macos13-arm64": ("Darwin", {"arm64"}),
                "macos13-x86_64": ("Darwin", {"x86_64"})}
    system, architectures = expected[options.platform]
    assert platform.system() == system and platform.machine() in architectures, platform.platform()
    if system == "Windows":
        assert sys.getwindowsversion().product_type == 1, "A Windows 10/11 desktop is required; a hosted Server CPU job cannot substitute"
    if system == "Darwin":
        assert platform.mac_ver()[0].split(".")[0] == "13", "This job proves the macOS 13 minimum, so a newer OS cannot substitute"
    if system == "Linux":
        assert os.environ.get("DISPLAY"), "A real X11 desktop is required"
        assert os.environ.get("QT_QPA_PLATFORM") == "xcb", "Native Wayland and offscreen do not qualify X11"
    assert os.environ.get("QT_QPA_PLATFORM") not in ("offscreen", "minimal"), "Qt requires the actual desktop platform"
    module = {"pyqt5": "PyQt5", "pyqt6": "PyQt6", "pyside6": "PySide6"}[options.binding]
    importlib.import_module(module)
    installed = {binding for binding in ("PyQt5", "PyQt6", "PySide6") if importlib.util.find_spec(binding) is not None}
    assert installed == {module}, f"Bindings must use separate environments: {installed}"


def admission(options):
    # Each manifest names independently qualified upstream fixtures and its own
    # hashed environment. Release jobs must not invent compatibility from imports.
    path = Path("compat/qualifications") / options.host / options.platform / options.python / options.binding / "admission.json"
    assert path.is_file(), f"Unresolved host admission: create and verify {path} on upstream first"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["upstream_vispy_version"] == "0.17.0"
    requirements = Path(manifest["requirements_file"])
    assert digest(requirements) == manifest["requirements_sha256"]
    assert "--hash=sha256:" in requirements.read_text(encoding="utf-8")
    if options.host == "phylib":
        assert manifest["rendering"] is False and manifest["scope"] == "import-only"
        repository_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repository_root))
        from tools.phylib_import_cell import inventory, validate_observation
        import_path = Path(manifest["import_inventory"])
        assert digest(import_path) == manifest["import_inventory_sha256"]
        validate_observation(json.loads(import_path.read_bytes()), inventory.read_hosts()["phylib"])
    else:
        assert manifest["upstream_fixture_status"] == "passed"
        assert manifest["fixture_files"] and all(Path(file).is_file() for file in manifest["fixture_files"])
        assert manifest["reference_manifest"] and Path(manifest["reference_manifest"]).is_file()
        reference_path = Path(manifest["reference_manifest"])
        assert digest(reference_path) == manifest["reference_manifest_sha256"]
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        assert not reference["errors"]
        assert reference["provenance"]["kind"] == "upstream"
        assert reference["provenance"]["vispy_version"] == "0.17.0"
        assert manifest["upstream_cases"] and set(manifest["upstream_cases"]) <= set(reference["fixtures"])
        for case in manifest["upstream_cases"]:
            for role in ("rgba", "filtered_glir", "expanded_shaders"):
                artifact = reference["fixtures"][case][role]
                assert digest(reference_path.parent / artifact["file"]) == artifact["sha256"]
        for file in manifest["fixture_files"]:
            assert digest(file) == manifest["fixture_sources_sha256"][file]
        if options.host == "visbrain":
            assert manifest["upstream_sdist_sha256"] == "1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6"
            assert digest(manifest["upstream_sdist"]) == manifest["upstream_sdist_sha256"]
    write(options.output, {"admission_path": str(path), "admission_sha256": digest(path), "admission": manifest})


def oracle_requirements(options):
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    upstream = json.loads(Path(".github/workflows/upstream-vispy-0.17.0.json").read_text())
    requirements = []
    for line in Path("tools/oracle_requirements.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        if name.lower() == "vispy":
            assert version == upstream["version"] == "0.17.0"
            hashes = [file["sha256"] for file in upstream["files"]]
        else:
            normalized = name.lower().replace("_", "-")
            package = next(package for package in lock["package"] if package["name"] == normalized and package["version"] == version)
            hashes = [wheel["hash"].split(":", 1)[1] for wheel in package["wheels"]]
        assert hashes, line
        requirements.append(line + " " + " ".join("--hash=sha256:" + value for value in hashes))
    path = Path(options.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(requirements) + "\n", encoding="utf-8")


def software_stack(options):
    path = Path(os.environ.get("VISPY_SOFTWARE_STACK_MANIFEST", "compat/qualifications/software-vulkan/stack.json"))
    assert path.is_file(), f"Pin software Vulkan and OpenGL libraries in {path} before qualification"
    manifest = json.loads(path.read_text())
    assert manifest["vulkan"] and manifest["opengl"]
    for file in manifest["vulkan"] + manifest["opengl"]:
        assert digest(file["path"]) == file["sha256"], file
    assert Path(os.environ["VK_DRIVER_FILES"]).is_file()
    write(options.output, {"stack": manifest, "manifest_sha256": digest(path)})


def compare_pair(options):
    import numpy as np
    sys.path.insert(0, str(Path.cwd()))
    from tools.fixture_gloo import FIXTURES, comparison_masks
    reference_path = Path(options.reference)
    candidate_path = Path(options.candidate)
    reference = json.loads((reference_path / "manifest.json").read_text())
    candidate = json.loads((candidate_path / "manifest.json").read_text())
    assert not reference["errors"] and not candidate["errors"]
    assert reference["provenance"]["kind"] == "upstream"
    assert reference["provenance"]["vispy_version"] == "0.17.0"
    assert candidate["provenance"]["kind"] == "candidate"
    assert set(reference["fixtures"]) == set(candidate["fixtures"]) == set(FIXTURES)
    results, failures = {}, []
    for name in FIXTURES:
        original = np.load(reference_path / reference["fixtures"][name]["rgba"]["file"], allow_pickle=False)
        image = np.load(candidate_path / candidate["fixtures"][name]["rgba"]["file"], allow_pickle=False)
        assert image.shape == original.shape and image.dtype == original.dtype == np.uint8
        difference = np.abs(image.astype(np.int16) - original.astype(np.int16))
        interior, edge = comparison_masks(name, image.shape)
        exact = FIXTURES[name].exact
        interior_error = int(difference[interior].max()) if interior.any() else 0
        edge_different = int(np.count_nonzero(np.any(difference != 0, axis=2) & edge))
        passed = np.array_equal(image, original) if exact else interior_error <= 2 and edge_different <= np.count_nonzero(edge) * .001
        results[name] = {"passed": bool(passed), "exact": exact, "interior_max_abs_u8": interior_error, "edge_different_pixels": edge_different}
        if not passed:
            failures.append(name)
    write(options.output, {"comparison": {"interior_max_abs_u8": 2, "edge_max_differing_fraction": .001, "categorical_exact": True}, "fixtures": results, "failures": failures})
    assert not failures, f"Independent same-stack oracle mismatches: {failures}"


def run_pytest(options):
    repository_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repository_root))
    import pytest

    class Evidence:
        def __init__(self):
            self.nodeids = []
            self.reports = []

        def pytest_collection_finish(self, session):
            self.nodeids = [item.nodeid for item in session.items]

        def pytest_runtest_logreport(self, report):
            self.reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome})

    evidence = Evidence()
    arguments = options.pytest_args
    if arguments and arguments[0] == "--":
        arguments = arguments[1:]
    code = pytest.main(arguments, plugins=[evidence])
    write(options.output, {"exit_code": int(code), "collected": evidence.nodeids, "reports": evidence.reports})
    assert code == 0, f"pytest failed with exit code {code}"
    assert evidence.nodeids, "An empty qualification suite is not evidence"
    skipped = [report for report in evidence.reports if report["outcome"] == "skipped"]
    assert not skipped, f"Missing coverage cannot pass qualification: {skipped}"
    passed = {report["nodeid"] for report in evidence.reports if report["when"] == "call" and report["outcome"] == "passed"}
    assert passed == set(evidence.nodeids), "Every collected qualification case must execute and pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture_parser = commands.add_parser("capture")
    capture_parser.add_argument("--gpu", action="store_true")
    capture_parser.add_argument("--software", action="store_true")
    capture_parser.add_argument("--without-package", action="store_true")
    capture_parser.add_argument("--backend", choices=["Vulkan", "Metal"])
    capture_parser.add_argument("--output", required=True)
    platform_parser = commands.add_parser("platform")
    platform_parser.add_argument("--platform", required=True)
    platform_parser.add_argument("--binding", choices=["pyqt5", "pyqt6", "pyside6"], required=True)
    admission_parser = commands.add_parser("admission")
    for name in ("host", "platform", "python", "binding", "output"):
        admission_parser.add_argument("--" + name, required=True)
    oracle_parser = commands.add_parser("oracle-requirements")
    oracle_parser.add_argument("--output", required=True)
    software_parser = commands.add_parser("software-stack")
    software_parser.add_argument("--output", required=True)
    comparison_parser = commands.add_parser("compare-pair")
    for name in ("reference", "candidate", "output"):
        comparison_parser.add_argument("--" + name, required=True)
    pytest_parser = commands.add_parser("pytest")
    pytest_parser.add_argument("--output", required=True)
    pytest_parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    {"capture": capture, "platform": validate_platform, "admission": admission,
     "oracle-requirements": oracle_requirements, "software-stack": software_stack,
     "compare-pair": compare_pair, "pytest": run_pytest}[options.command](options)


if __name__ == "__main__":
    main()
