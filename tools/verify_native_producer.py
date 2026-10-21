"""Attest actual generated C++ project policy before an isolated vendor build."""

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_sdk", ROOT / "cmake/native_sdk.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build = args.build.resolve(strict=True)
    producer_path = build / "native-sdk/producer-Release.json"
    producer = json.loads(producer_path.read_text(encoding="utf-8"))
    if producer["msvc_mutex_policy"] != "msvc-stl-init-in-situ-v1":
        raise sdk.SDKError("Compatible producer must enable in-situ mutex initialization")
    if not sdk.mutex_macro_defined("", producer["cxx_flags"] + " " + producer["release_flags"]):
        raise sdk.SDKError("Compatible producer compiler flags do not define its policy")
    projects = {path.relative_to(build).as_posix(): sdk.project_mutex_policy(path, producer["msvc_mutex_policy"])
                for path in sorted(build.rglob("*.vcxproj"))
                if "CMakeFiles" not in path.relative_to(build).parts}
    count = sum(value["cpp_items"] for value in projects.values())
    if not count:
        raise sdk.SDKError("No generated C++ source items were observed")
    record = {"producer": producer, "producer_metadata_sha256": sdk.sha256(producer_path),
              "verifier_sha256": sdk.sha256(ROOT / "cmake/native_sdk.py"),
              "cpp_items": count, "projects": projects, "compiled": False}
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Verified mutex policy in {count} C++ source items across {len(projects)} generated projects")


if __name__ == "__main__":
    main()
