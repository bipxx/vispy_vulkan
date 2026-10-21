"""Prepare an isolated, hashed standard CPython3.12 milestone build environment only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

from packaging.markers import Marker, default_environment
from packaging.requirements import Requirement
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
PINS = {"3.12.8": (3, 12)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_binaries() -> dict[str, str]:
    return {path.relative_to(ROOT).as_posix(): sha256(path)
            for path in sorted((ROOT / "src/vispy").rglob("*"))
            if path.is_file() and path.suffix in {".pyd", ".dll", ".so", ".dylib"}}


def locked_dependencies(version: str) -> dict:
    target = PINS[version]
    abi = f"cp{target[0]}{target[1]}"
    marker = dict(default_environment(), python_version=".".join(map(str, target)),
                  python_full_version=version, implementation_version=version,
                  implementation_name="cpython", platform_python_implementation="CPython",
                  os_name="nt", sys_platform="win32", platform_system="Windows",
                  platform_machine="AMD64")
    supported = set(cpython_tags(target, [abi], ["win_amd64"]))
    supported.update(compatible_tags(target, abi, ["win_amd64"]))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    wanted = {}
    for text in project["build-system"]["requires"]:
        requirement = Requirement(text)
        if requirement.marker and not requirement.marker.evaluate(marker):
            continue
        pins = [pin.version for pin in requirement.specifier if pin.operator == "=="]
        if len(pins) != 1:
            raise ValueError(f"Build requirement must have one exact pin: {text}")
        wanted[canonicalize_name(requirement.name)] = pins[0]
    pending, selected = list(wanted), {}
    while pending:
        name = pending.pop(0)
        if name in selected:
            continue
        candidates = [package for package in lock["package"] if package["name"] == name
                      and (name not in wanted or package["version"] == wanted[name])]
        if len(candidates) != 1:
            raise ValueError(f"Absent or ambiguous locked package: {name}")
        package = candidates[0]
        wheels = [wheel for wheel in package.get("wheels", [])
                  if parse_wheel_filename(wheel["url"].split("/")[-1])[3] & supported]
        if not wheels:
            raise ValueError(f"No pinned standard {abi}/Windows wheel: {name}")
        selected[name] = {"name": name, "version": package["version"],
                          "source": package.get("source"), "wheels": wheels}
        for dependency in package.get("dependencies", []):
            if not dependency.get("marker") or Marker(dependency["marker"]).evaluate(marker):
                pending.append(dependency["name"])
    return selected


OBSERVE = r'''
import hashlib, importlib, importlib.metadata as m, json, pathlib, platform, struct, sys, sysconfig
result = dict(python=platform.python_version(), executable=sys.executable, base_prefix=sys.base_prefix,
              executable_sha256=hashlib.sha256(pathlib.Path(sys.executable).read_bytes()).hexdigest(),
              base_executable=sys._base_executable,
              base_executable_sha256=hashlib.sha256(pathlib.Path(sys._base_executable).read_bytes()).hexdigest(),
              extension_suffix=sysconfig.get_config_var('EXT_SUFFIX'), soabi=sysconfig.get_config_var('SOABI'),
              pointer_bytes=struct.calcsize('P'), py_gil_disabled=sysconfig.get_config_var('Py_GIL_DISABLED'),
              gil_enabled=sys._is_gil_enabled() if hasattr(sys, '_is_gil_enabled') else True,
              packages=[], modules=[])
for dist in sorted(m.distributions(), key=lambda d: d.metadata['Name']):
    record = dist.read_text('RECORD')
    result['packages'].append(dict(name=dist.metadata['Name'], version=dist.version,
                                  origin=str(dist.locate_file('')),
                                  record_sha256=hashlib.sha256(record.encode()).hexdigest() if record else None))
for name in ('numpy', 'Cython', 'nanobind', 'cmake', 'scikit_build_core', 'packaging', 'pathspec'):
    module = importlib.import_module(name)
    path = pathlib.Path(module.__file__).resolve()
    assert path.is_relative_to(pathlib.Path(sys.prefix).resolve()), name
    result['modules'].append(dict(name=name, origin=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
result['numpy_include'] = importlib.import_module('numpy').get_include()
result['pyvenv_cfg_sha256'] = hashlib.sha256((pathlib.Path(sys.prefix) / 'pyvenv.cfg').read_bytes()).hexdigest()
print(json.dumps(result))
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-version", choices=PINS, required=True)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--native-cache", type=Path, default=ROOT / "build/cp312-cp312-win_amd64")
    args = parser.parse_args()
    version = args.python_version
    major, minor = PINS[version]
    abi = f"cp{major}{minor}"
    environment = ROOT / f"build/{abi}-candidate/build-env"
    evidence = ROOT / f"compat/{abi}-candidate"
    if args.install and environment.exists():
        parser.error("Refusing to replace an existing build environment")
    before = protected_binaries()
    selected = locked_dependencies(version)
    evidence.mkdir(parents=True, exist_ok=True)
    requirements = evidence / f"build-windows-cpython{major}{minor}.txt"
    requirements.write_text("# Standard CPython build dependencies selected from exact uv.lock wheels.\n" + "\n".join(
        f"{name}=={package['version']} " + " ".join("--hash=" + wheel["hash"] for wheel in package["wheels"])
        for name, package in sorted(selected.items())) + "\n", encoding="utf-8")
    resolver = subprocess.check_output(["uv", "--version"], text=True).strip()
    if not resolver.startswith("uv 0.12.5 "):
        raise ValueError(f"Unexpected resolver version: {resolver}")
    python = environment / "Scripts/python.exe"
    if args.install:
        subprocess.run(["uv", "venv", str(environment), "--python", version], check=True)
        subprocess.run(["uv", "pip", "install", "--python", str(python), "--require-hashes",
                        "--only-binary", ":all:", "-r", str(requirements)], check=True)
    record = {"qualification": "build_preparation_only", "wheel_built": False,
              "native_graphics_qualified": False, "interpreter_pin": version,
              "platform": "windows-x86_64", "abi": abi, "free_threaded": False,
              "environment": str(environment), "resolver": resolver,
              "root_lock_sha256": sha256(ROOT / "uv.lock"), "pyproject_sha256": sha256(ROOT / "pyproject.toml"),
              "preparation_script_sha256": sha256(Path(__file__)),
              "requirements": requirements.relative_to(ROOT).as_posix(),
              "requirements_sha256": sha256(requirements), "packages": list(selected.values()),
              "planned_generator": "Visual Studio 17 2022", "planned_architecture": "x64",
              "planned_configuration": "Release", "root_protected_binaries_before": before,
              "expected_native_module": f"_dawn.{abi}-win_amd64.pyd",
              "expected_sdf_module": f"_sdf_cpu.{abi}-win_amd64.pyd",
              "expected_wheel": f"vispy-0.17.0+vulkan.1-{abi}-{abi}-win_amd64.whl",
              "native_dependency_reuse": "Verified source trees only; prebuilt Dawn imports are not implemented",
              "remaining_gates": ["Build from a stable frozen source snapshot in a reserved native build slot",
                                  "Installed compiled SDF/native/assets/licenses external consumer and rollback",
                                  "Standard interpreter graphics/Qt qualification in separate supported host locks"]}
    if python.exists():
        observed = json.loads(subprocess.check_output([str(python), "-c", OBSERVE], cwd=evidence, text=True))
        assert observed["python"] == version
        assert observed["extension_suffix"] == f".{abi}-win_amd64.pyd"
        assert observed["pointer_bytes"] == 8 and not observed["py_gil_disabled"] and observed["gil_enabled"]
        actual = {canonicalize_name(package["name"]): package["version"] for package in observed["packages"]}
        assert actual == {name: package["version"] for name, package in selected.items()}
        record["installed_environment"] = observed
        cmake_executable = environment / "Lib/site-packages/cmake/data/bin/cmake.exe"
        record["cmake"] = {"origin": str(cmake_executable), "sha256": sha256(cmake_executable),
                           "version": subprocess.check_output([str(cmake_executable), "--version"], text=True).splitlines()[0]}
    compiler_file = args.native_cache / "CMakeFiles/4.4.4/CMakeCXXCompiler.cmake"
    if compiler_file.exists():
        text = compiler_file.read_text()
        extract = lambda key: re.search(r'set\(' + key + r' "([^"]*)"\)', text).group(1)
        compiler = Path(extract("CMAKE_CXX_COMPILER"))
        toolset = compiler.parts[compiler.parts.index("MSVC") + 1]
        record["toolchain"] = {"compiler": str(compiler), "compiler_sha256": sha256(compiler),
                               "compiler_version": extract("CMAKE_CXX_COMPILER_VERSION"),
                               "generator_toolset": "v143,version=" + toolset,
                               "windows_sdk": "10.0.22621.0", "metadata_source": str(compiler_file),
                               "metadata_sha256": sha256(compiler_file)}
    after = protected_binaries()
    record["root_protected_binaries_after"] = after
    record["root_protected_binary_inventory_unchanged"] = before == after
    (evidence / "preparation.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"abi": abi, "environment_prepared": "installed_environment" in record,
                      "packages": len(selected), "root_protected_binaries_unchanged": before == after,
                      "wheel_built": False}))


if __name__ == "__main__":
    main()
