"""Prepare a hashed CPython 3.11 build environment; never compile or render."""

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
from packaging.utils import parse_wheel_filename


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, default=ROOT / "build/cp311-candidate/build-env")
    parser.add_argument("--evidence", type=Path, default=ROOT / "compat/cp311-candidate")
    parser.add_argument("--install", action="store_true", help="Create the new environment and install hashed wheels only")
    parser.add_argument("--native-cache", type=Path, default=ROOT / "build/cp312-cp312-win_amd64")
    args = parser.parse_args()
    environment, evidence = args.environment.resolve(), args.evidence.resolve()
    if args.install and environment.exists():
        parser.error("Refusing to replace an existing build environment")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    marker = dict(default_environment(), python_version="3.11", python_full_version="3.11.11", sys_platform="win32", platform_system="Windows", platform_machine="AMD64")
    supported = set(cpython_tags((3, 11), ["cp311"], ["win_amd64"]))
    supported.update(compatible_tags((3, 11), "cp311", ["win_amd64"]))
    wanted = {}
    for text in project["build-system"]["requires"]:
        requirement = Requirement(text)
        if requirement.marker and not requirement.marker.evaluate(marker):
            continue
        versions = [item.version for item in requirement.specifier if item.operator == "=="]
        if len(versions) != 1:
            raise ValueError(f"Build dependency must have one exact pin: {text}")
        wanted[requirement.name.lower().replace("_", "-")] = versions[0]
    pending = list(wanted)
    selected = {}
    while pending:
        name = pending.pop(0)
        if name in selected:
            continue
        candidates = [item for item in lock["package"] if item["name"] == name
                      and (name not in wanted or item["version"] == wanted[name])]
        if len(candidates) != 1:
            raise ValueError(f"Ambiguous or absent locked build dependency: {name}")
        item = candidates[0]
        wheels = [wheel for wheel in item.get("wheels", [])
                  if parse_wheel_filename(wheel["url"].split("/")[-1])[3] & supported]
        if not wheels:
            raise ValueError(f"No locked Windows CPython3.11 wheel for {name}")
        selected[name] = {"name": name, "version": item["version"], "wheels": wheels}
        for dependency in item.get("dependencies", []):
            if "marker" not in dependency or Marker(dependency["marker"]).evaluate(marker):
                pending.append(dependency["name"])
    evidence.mkdir(parents=True, exist_ok=True)
    requirements = evidence / "build-windows-cpython311.txt"
    requirements.write_text("# Build-only dependencies selected from immutable uv.lock metadata.\n" + "\n".join(
        f"{name}=={item['version']} " + " ".join("--hash=" + wheel["hash"] for wheel in item["wheels"])
        for name, item in sorted(selected.items())) + "\n")
    python = environment / "Scripts/python.exe"
    record = {"schema": 1, "qualification": "build_preparation_only", "wheel_built": False,
              "native_graphics_qualified": False, "interpreter_pin": "3.11.11", "platform": "windows-x86_64",
              "environment": str(environment), "root_lock_sha256": sha(ROOT / "uv.lock"),
              "pyproject_sha256": sha(ROOT / "pyproject.toml"), "preparation_script_sha256": sha(Path(__file__)),
              "requirements": requirements.relative_to(ROOT).as_posix(), "requirements_sha256": sha(requirements),
              "packages": list(selected.values()), "planned_generator": "Visual Studio 17 2022",
              "planned_architecture": "x64", "planned_configuration": "Release",
              "native_dependency_reuse": "Checksum-verified immutable source trees shared by snapshot junctions; prebuilt library imports are not implemented",
              "candidate_runtime_gates": ["DIVE/visbrain CPython3.11 PyQt5 environments remain separate",
                  "NumPy2.4.6 build versus NumPy1.26.4 runtime SDF/ABI consumer proof",
                  "DIVE original float setSizes failure must be resolved by a genuinely compatible binding or remain unadmitted"]}
    if args.install:
        version = subprocess.check_output(["uv", "--version"], text=True).strip()
        if not version.startswith("uv 0.12.5 "):
            raise ValueError(f"Unexpected resolver version: {version}")
        subprocess.run(["uv", "venv", str(environment), "--python", "3.11.11"], check=True)
        subprocess.run(["uv", "pip", "install", "--python", str(python), "--require-hashes",
                        "--only-binary", ":all:", "-r", str(requirements)], check=True)
    if python.exists():
        code = "import json,sys,sysconfig,importlib.metadata; print(json.dumps(dict(python=sys.version,executable=sys.executable,extension_suffix=sysconfig.get_config_var('EXT_SUFFIX'),soabi=sysconfig.get_config_var('SOABI'),packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()})))"
        record["installed_environment"] = json.loads(subprocess.check_output([str(python), "-c", code], text=True))
        assert record["installed_environment"]["extension_suffix"] == ".cp311-win_amd64.pyd"
        actual = {name.lower().replace("_", "-"): version for name, version in record["installed_environment"]["packages"].items()}
        assert actual == {name: item["version"] for name, item in selected.items()}
    compiler_file = args.native_cache / "CMakeFiles/4.4.4/CMakeCXXCompiler.cmake"
    if compiler_file.exists():
        compiler_text = compiler_file.read_text()
        extract = lambda key: re.search(r'set\(' + key + r' "([^"]*)"\)', compiler_text).group(1)
        compiler = Path(extract("CMAKE_CXX_COMPILER"))
        toolset_version = compiler.parts[compiler.parts.index("MSVC") + 1]
        record["toolchain"] = {"compiler": str(compiler), "compiler_sha256": sha(compiler),
                               "compiler_version": extract("CMAKE_CXX_COMPILER_VERSION"),
                               "generator_toolset": "v143,version=" + toolset_version,
                               "windows_sdk": "10.0.22621.0",
                               "metadata_source": str(compiler_file), "metadata_sha256": sha(compiler_file)}
    record["expected_native_module"] = "_dawn.cp311-win_amd64.pyd"
    record["expected_sdf_module"] = "_sdf_cpu.cp311-win_amd64.pyd"
    record["expected_wheel"] = "vispy-0.17.0+vulkan.1-cp311-cp311-win_amd64.whl"
    (evidence / "preparation.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"requirements": str(requirements), "packages": len(selected),
                      "environment_prepared": "installed_environment" in record, "wheel_built": False}))


if __name__ == "__main__":
    main()
