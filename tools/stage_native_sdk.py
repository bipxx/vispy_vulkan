"""Install the opt-in SDK component without compiling or reconfiguring the producer."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_sdk", ROOT / "cmake/native_sdk.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


def read_cache(path: Path) -> dict:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"[^#/:][^:]*:[^=]+=", line):
            key, value = line.split("=", 1)
            result[key.split(":", 1)[0]] = value
    return result


def protected_binaries(source: Path) -> dict:
    return {path.relative_to(source).as_posix(): sdk.sha256(path)
            for path in sorted((source / "src/vispy").rglob("*"))
            if path.is_file() and path.suffix in {".pyd", ".dll"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build = args.build.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        parser.error("Refusing to replace an existing SDK directory")
    cache = read_cache(build / "CMakeCache.txt")
    if cache.get("VISPY_EXPORT_NATIVE_SDK") != "ON" or cache.get("VISPY_NATIVE_SDK"):
        parser.error("Producer must already be configured with export ON and no imported SDK")
    if cache.get("VISPY_VERIFY_DEPENDENCIES") != "ON":
        parser.error("SDK producer must verify the immutable source pins")
    source = Path(cache["CMAKE_HOME_DIRECTORY"])
    source_manifest_path = source / "wheel-source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8")) if source_manifest_path.exists() else None
    if source_manifest:
        for name, digest in source_manifest["source_files"].items():
            if sdk.sha256(source / name) != digest:
                raise sdk.SDKError(f"Frozen producer source changed: {name}")
    before = protected_binaries(source)
    workspace_before = protected_binaries(ROOT)
    settings_path = build / "native-sdk/producer-Release.json"
    producer = json.loads(settings_path.read_text(encoding="utf-8"))
    if producer["system"] != "Windows":
        parser.error("SDK staging currently supports the observed Windows producer only")
    ns = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
    project = ET.parse(build / "_dawn.vcxproj").getroot()
    observed_sdk = project.find("m:PropertyGroup/m:WindowsTargetPlatformVersion", ns).text
    if observed_sdk != producer["windows_sdk"]:
        parser.error("Generated project SDK differs from producer metadata")
    # Validate actual compiler CRT settings for independently compiled archive inputs.
    projects = [build / "dawn/src/dawn/native/webgpu_dawn.vcxproj",
                build / "glslang/glslang/glslang.vcxproj",
                build / "glslang/glslang/glslang-default-resource-limits.vcxproj",
                build / "dawn/third_party/spirv-tools/source/SPIRV-Tools-static.vcxproj",
                build / "dawn/third_party/spirv-tools/source/opt/SPIRV-Tools-opt.vcxproj"]
    for path in projects:
        tree = ET.parse(path).getroot()
        groups = [group for group in tree.findall("m:ItemDefinitionGroup", ns)
                  if "'Release|x64'" in group.attrib.get("Condition", "")]
        if len(groups) != 1 or groups[0].find("m:ClCompile/m:RuntimeLibrary", ns).text != "MultiThreadedDLL":
            parser.error(f"Archive producer CRT is incompatible: {path}")
    compiler_digest = sdk.sha256(Path(producer["compiler"]))
    cpp_policies = {path.relative_to(build).as_posix(): sdk.project_mutex_policy(path, producer["msvc_mutex_policy"])
                    for path in sorted(build.rglob("*.vcxproj"))
                    if "CMakeFiles" not in path.relative_to(build).parts}
    if set(producer["archive_origins"]) != sdk.ARCHIVES:
        parser.error("Producer archive identity set differs from the five vendor targets")
    archive_before = {name: sdk.sha256(Path(path)) for name, path in producer["archive_origins"].items()}
    generated_root = Path(producer["generated_header_origin"])
    headers_before = sdk.inventory(generated_root)
    subprocess.run([cache["CMAKE_COMMAND"], "--install", str(build), "--config", "Release",
                    "--component", "VispyNativeSDK", "--prefix", str(output)], check=True)
    if json.loads((output / "share/VispyNativeSDK/producer.json").read_text(encoding="utf-8")) != producer:
        raise sdk.SDKError("Producer metadata changed during staging")
    archive_after = {name: sdk.sha256(Path(path)) for name, path in producer["archive_origins"].items()}
    if archive_before != archive_after or headers_before != sdk.inventory(generated_root):
        raise sdk.SDKError("Producer archives/generated headers changed during staging")
    for name, digest in archive_before.items():
        if sdk.sha256(output / "lib" / name) != digest:
            raise sdk.SDKError(f"Installed archive differs from its producer: {name}")
    for name, digest in headers_before.items():
        if sdk.sha256(output / "include" / name) != digest:
            raise sdk.SDKError(f"Installed generated header differs from its producer: {name}")
    record = {"format_version": 2, "qualification": "vendor_artifact_reuse_only",
              "native_graphics_qualified": False, "python_abi_objects_reused": False,
              "producer": producer, "compiler_sha256": compiler_digest,
              "producer_cache_sha256": sdk.sha256(build / "CMakeCache.txt"),
              "producer_archive_sha256": archive_before,
              "producer_generated_header_sha256": headers_before,
              "producer_project_sha256": {path.relative_to(build).as_posix(): sdk.sha256(path)
                                          for path in projects},
              "producer_cpp_project_policies": cpp_policies,
              "staging_script_sha256": sdk.sha256(Path(__file__)),
              "compiler_policy_verifier_sha256": sdk.sha256(ROOT / "cmake/native_sdk.py"),
              "producer_source_manifest_sha256": sdk.sha256(source_manifest_path) if source_manifest else None,
              "producer_source_tree_sha256": source_manifest["source_tree_sha256"] if source_manifest else None,
              "dependency_lock_sha256": sdk.sha256(output / "share/VispyNativeSDK/dependencies.lock.json"),
              "files": sdk.inventory(output)}
    after = protected_binaries(source)
    record["protected_native_binaries_before"] = before
    record["protected_native_binaries_after"] = after
    if before != after:
        raise sdk.SDKError("Source native artifacts changed during SDK staging")
    workspace_after = protected_binaries(ROOT)
    record["protected_workspace_native_binaries_before"] = workspace_before
    record["protected_workspace_native_binaries_after"] = workspace_after
    if workspace_before != workspace_after:
        raise sdk.SDKError("Workspace native artifacts changed during SDK staging")
    manifest = output / "manifest.json"
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_digest = sdk.sha256(manifest)
    sdk.verify(output, manifest_digest, ROOT / "cmake/dependencies.lock.json", producer)
    print(json.dumps({"sdk": str(output), "manifest_sha256": manifest_digest,
                      "files": len(record["files"]), "archives": 5, "compiled": False,
                      "wheel_qualified": False}))


if __name__ == "__main__":
    main()
