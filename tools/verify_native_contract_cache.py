"""Attest an SDK leaf/contract cache without private Tint-reader compilation."""

import argparse
import importlib.util
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_sdk", ROOT / "cmake/native_sdk.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build, prefix = args.build.resolve(strict=True), args.sdk.resolve(strict=True)
    cache = {}
    for line in (build / "CMakeCache.txt").read_text(encoding="utf-8-sig").splitlines():
        if re.match(r"[^#/:][^:]*:[^=]+=", line):
            key, value = line.split("=", 1)
            cache[key.split(":", 1)[0]] = value
    assert Path(cache["VISPY_NATIVE_SDK"]).resolve() == prefix
    digest = "7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2"
    assert cache["VISPY_NATIVE_SDK_MANIFEST_SHA256"] == sdk.sha256(prefix / "manifest.json") == digest
    assert cache["VISPY_INPLACE"] == "OFF" and cache["VISPY_EXPORT_NATIVE_SDK"] == "OFF"
    assert cache["VISPY_BUILD_CONTRACT_TESTS"] == cache["VISPY_LEGACY_MSVC_CRT_MUTEX"] == cache["VISPY_VERIFY_DEPENDENCIES"] == "ON"
    projects = {path.relative_to(build).as_posix(): sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")
                for path in sorted(build.rglob("*.vcxproj")) if "CMakeFiles" not in path.relative_to(build).parts}
    for name in ("shader_contract", "point_contract"):
        assert "VISPY_TEST_TINT_READER" not in (build / (name + ".vcxproj")).read_text(encoding="utf-8-sig"), name
    assert not (build / "dawn").exists() and not (build / "glslang").exists()
    record = {"qualification": "sdk_leaf_and_cpu_contract_generated_policy_only", "sdk_manifest_sha256": digest,
              "cache_sha256": sdk.sha256(build / "CMakeCache.txt"), "cpp_projects": projects,
              "cpp_items": sum(value["cpp_items"] for value in projects.values()),
              "vendor_build_graph_added": False, "sdk_tint_reader_enabled": False,
              "test_root": cache["VISPY_CONTRACT_TESTS_ROOT"], "dataset_root": cache["VISPY_CONTRACT_DATASETS_ROOT"]}
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"cpp_items": record["cpp_items"], "sdk_tint_reader": False, "vendor_build_graph": False}))


if __name__ == "__main__":
    main()
