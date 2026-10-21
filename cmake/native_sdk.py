"""Verify an immutable, ABI-independent Windows vendor SDK before CMake import."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ARCHIVES = {"webgpu_dawn.lib", "glslang.lib", "glslang-default-resource-limits.lib",
            "SPIRV-Tools.lib", "SPIRV-Tools-opt.lib"}
SETTINGS = ("system", "architecture", "pointer_bytes", "configuration", "runtime",
            "cmake_version", "compiler_version", "windows_sdk", "cxx_flags", "release_flags",
            "msvc_mutex_policy")

MUTEX_DEFINITION = "_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR"
MUTEX_POLICIES = {"msvc-stl-init-in-situ-v1": True, "msvc-stl-constexpr-v1": False}


def mutex_macro_defined(definitions: str, flags: str, undefinitions: str = "") -> bool:
    """Read exact MSVC macro switches; an explicit undefinition is unqualified."""
    def macro_name(value: str) -> str:
        return value.replace('"', '').strip().split("=", 1)[0]

    defined = any(macro_name(value) == MUTEX_DEFINITION for value in definitions.split(";"))
    undefined = any(macro_name(value) == MUTEX_DEFINITION for value in undefinitions.split(";"))
    tokens = re.findall(r'(?:[^\s"]|"[^"]*")+', flags)
    for index, raw in enumerate(tokens):
        token = raw.replace('"', '')
        if len(token) < 2 or token[:2] not in {"/D", "-D", "/U", "-U"}:
            continue
        value = token[2:]
        if not value and index + 1 < len(tokens):
            value = tokens[index + 1]
        if macro_name(value) == MUTEX_DEFINITION:
            defined |= token[1] == "D"
            undefined |= token[1] == "U"
    if undefined:
        raise SDKError("Explicit MSVC mutex macro undefinition is incompatible with SDK policy")
    return defined


def project_mutex_policy(path: Path, expected: str) -> dict:
    """Verify the real Release compiler definitions for every C++ item."""
    if expected not in MUTEX_POLICIES:
        raise SDKError("Unrecognized MSVC mutex compiler policy")
    ns = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
    tree = ET.parse(path).getroot()
    items = [item for item in tree.findall("m:ItemGroup/m:ClCompile", ns)
             if Path(item.attrib.get("Include", "")).suffix.lower() in {".cpp", ".cc", ".cxx"}]
    if not items:
        return {"cpp_items": 0, "policy": expected}
    groups = [group for group in tree.findall("m:ItemDefinitionGroup", ns)
              if "'Release|x64'" in group.attrib.get("Condition", "")]
    if len(groups) != 1:
        raise SDKError(f"Expected one Release/x64 compiler group: {path}")
    common = groups[0].find("m:ClCompile", ns)
    if common is None:
        raise SDKError(f"Missing Release/x64 ClCompile settings: {path}")
    properties = dict.fromkeys(("PreprocessorDefinitions", "AdditionalOptions", "UndefinePreprocessorDefinitions"), "")
    properties.update({node.tag.rsplit("}", 1)[-1]: node.text or "" for node in common
                       if node.tag.rsplit("}", 1)[-1] in properties})
    for item in items:
        effective = dict(properties)
        for node in item:
            name = node.tag.rsplit("}", 1)[-1]
            if name in properties and (not node.attrib.get("Condition") or "'Release|x64'" in node.attrib["Condition"]):
                effective[name] = (node.text or "").replace("%(" + name + ")", properties[name])
        defined = mutex_macro_defined(effective["PreprocessorDefinitions"], effective["AdditionalOptions"],
                                      effective["UndefinePreprocessorDefinitions"])
        if defined != MUTEX_POLICIES[expected]:
            raise SDKError(f"C++ compiler mutex policy mismatch in {path}: {item.attrib['Include']}")
    return {"cpp_items": len(items), "policy": expected, "project_sha256": sha256(path)}


class SDKError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(prefix: Path) -> dict[str, str]:
    result = {}
    for path in sorted(prefix.rglob("*")):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise SDKError(f"SDK links are not immutable copied artifacts: {path}")
        if path.is_file() and path != prefix / "manifest.json":
            result[path.relative_to(prefix).as_posix()] = sha256(path)
    return result


def normalized_arch(value: str) -> str:
    return {"amd64": "x86_64", "x64": "x86_64"}.get(value.lower(), value.lower())


def verify(prefix: Path, expected_digest: str, dependency_lock: Path,
           consumer: dict) -> dict:
    prefix = prefix.resolve(strict=True)
    manifest_path = prefix / "manifest.json"
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise SDKError("An exact trusted SDK manifest SHA-256 is required")
    if sha256(manifest_path) != expected_digest:
        raise SDKError("SDK manifest checksum mismatch")
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    if record.get("format_version") != 2 or record.get("qualification") != "vendor_artifact_reuse_only":
        raise SDKError("Unsupported SDK format or qualification")
    actual = inventory(prefix)
    if actual != record["files"]:
        changed = sorted(set(actual) ^ set(record["files"]) |
                         {key for key in actual.keys() & record["files"].keys()
                          if actual[key] != record["files"][key]})
        raise SDKError("SDK inventory/checksum mismatch: " + ", ".join(changed[:8]))
    if sha256(dependency_lock) != record["dependency_lock_sha256"]:
        raise SDKError("SDK vendor source pins differ from the frozen consumer")
    sdk_lock = prefix / "share/VispyNativeSDK/dependencies.lock.json"
    if sha256(sdk_lock) != record["dependency_lock_sha256"]:
        raise SDKError("SDK embedded dependency lock mismatch")
    archives = {Path(path).name for path in actual if path.endswith(".lib")}
    if archives != ARCHIVES or sum(path.endswith(".lib") for path in actual) != 5:
        raise SDKError("SDK must contain exactly the five vendor archives")
    if any(Path(path).suffix.lower() in {".pyd", ".dll", ".obj"} for path in actual):
        raise SDKError("SDK contains an ABI leaf or an unexpected shared/object artifact")
    for path in actual:
        if path.endswith(".cmake"):
            text = (prefix / path).read_text(encoding="utf-8")
            if re.search(r"(?<![A-Za-z0-9_])[A-Za-z]:[/\\]", text) or "nanobind" in text.lower() or "python3" in text.lower():
                raise SDKError(f"SDK export contains an external build/ABI dependency: {path}")
    producer = record["producer"]
    embedded = json.loads((prefix / "share/VispyNativeSDK/producer.json").read_text(encoding="utf-8"))
    if producer != embedded:
        raise SDKError("SDK producer settings differ from installed metadata")
    if producer["system"] != "Windows" or normalized_arch(producer["architecture"]) != "x86_64":
        raise SDKError("SDK reuse currently supports Windows x86_64 only")
    if producer["configuration"] != "Release" or producer["runtime"] != "MultiThreadedDLL":
        raise SDKError("SDK requires Release with the DLL CRT")
    if producer.get("dawn_backend_vulkan") != "ON" or producer.get("dawn_backend_null") != "OFF" \
            or producer.get("dawn_backend_metal") != "OFF" or producer.get("dawn_monolithic") != "STATIC":
        raise SDKError("SDK requires the pinned static Vulkan renderer configuration")
    policy = producer.get("msvc_mutex_policy")
    if policy not in MUTEX_POLICIES or mutex_macro_defined("", producer["cxx_flags"] + " " + producer["release_flags"]) != MUTEX_POLICIES[policy]:
        raise SDKError("SDK mutex compiler policy disagrees with its compiler flags")
    projects = record.get("producer_cpp_project_policies", {})
    if not projects or not any(value.get("cpp_items", 0) for value in projects.values()):
        raise SDKError("SDK lacks observed vendor C++ compiler policy evidence")
    if any(value["policy"] != policy for value in projects.values()):
        raise SDKError("SDK archive C++ compiler policy evidence is incompatible")
    for key in SETTINGS:
        expected, observed = producer[key], consumer[key]
        if key == "architecture":
            expected, observed = normalized_arch(expected), normalized_arch(observed)
        if expected != observed:
            raise SDKError(f"SDK {key} mismatch: producer={expected!r}, consumer={observed!r}")
    if sha256(Path(consumer["compiler"])) != record["compiler_sha256"]:
        raise SDKError("SDK compiler binary mismatch")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify"])
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--dependency-lock", type=Path, required=True)
    for key in SETTINGS + ("compiler",):
        parser.add_argument("--" + key.replace("_", "-"), type=int if key == "pointer_bytes" else str, required=True)
    args = parser.parse_args()
    consumer = {key: getattr(args, key) for key in SETTINGS + ("compiler",)}
    record = verify(args.sdk, args.manifest_sha256, args.dependency_lock, consumer)
    print(f"Verified immutable SDK: {len(record['files'])} files, five vendor archives; ABI leaves remain separate")


if __name__ == "__main__":
    main()
