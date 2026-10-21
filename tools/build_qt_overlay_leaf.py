"""Build an isolated w10 SDK3 ABI leaf and protect the activated pass24 files."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "build/w10/source"
SDK = ROOT / "build/native-sdk/windows-x64-release-3"
SDK_SHA = "7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abi", choices=("cp312", "cp310"), required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    evidence = args.evidence.resolve() if args.evidence else ROOT / f"build/evidence/w10-sdk-{args.abi}"
    if evidence.exists():
        parser.error("This ABI evidence directory must be new")
    evidence.mkdir(parents=True)
    manifest = json.loads((SNAPSHOT / "wheel-source-manifest.json").read_text())
    activation_path = ROOT / "build/evidence/native-pass-24/activation.json"
    activation = json.loads(activation_path.read_text())

    def protect():
        result = {}
        for name, expected in activation["activated"].items():
            relative = ("src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/") + name
            result[relative] = sha(ROOT / relative)
            assert result[relative] == expected, (relative, "activated pass24 artifact changed")
        return result

    def source_check():
        for name, expected in manifest["source_files"].items():
            assert sha(SNAPSHOT / name) == expected, (name, "w10 source changed")

    source_check()
    before = protect()
    env = dict(os.environ, CL_MPCount="3")
    # The historic leaf tool remains immutable; only this subprocess receives the cap.
    command = ["pwsh.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "tools/build_sdk_leaf.ps1"), "-Preparation",
               str(ROOT / f"compat/{args.abi}-candidate/preparation.json"), "-Snapshot", str(SNAPSHOT),
               "-Evidence", str(evidence / "leaf"), "-Sdk", str(SDK), "-SdkManifestSha256", SDK_SHA]
    record = {"abi": args.abi, "command": command, "CL_MPCount": "3",
              "source_tree_sha256": manifest["source_tree_sha256"], "sdk_manifest_sha256": SDK_SHA,
              "activation_manifest_sha256": sha(activation_path), "protected_before": before,
              "build_tool_sha256": sha(ROOT / "tools/build_sdk_leaf.ps1"),
              "orchestrator_sha256": sha(Path(__file__))}
    (evidence / "command.json").write_text(json.dumps(record, indent=2) + "\n")
    try:
        with (evidence / "build.log").open("w", encoding="utf-8") as log:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        record["process_exit"] = process.returncode
        assert process.returncode == 0, "Leaf build failed; evidence retained"
        build = SNAPSHOT / f"build/sdk-{args.abi}"
        cache = {}
        for line in (build / "CMakeCache.txt").read_text(encoding="utf-8-sig").splitlines():
            if line and not line.startswith(("#", "//")) and ":" in line and "=" in line:
                key, value = line.split("=", 1)
                cache[key.split(":", 1)[0]] = value
        assert cache["VISPY_INPLACE"] == "OFF"
        assert cache["VISPY_LEGACY_MSVC_CRT_MUTEX"] == cache["VISPY_VERIFY_DEPENDENCIES"] == "ON"
        assert cache["VISPY_NATIVE_SDK_MANIFEST_SHA256"] == SDK_SHA == sha(SDK / "manifest.json")
        assert not (build / "dawn").exists() and not (build / "glslang").exists()
        spec = importlib.util.spec_from_file_location("native_sdk", SNAPSHOT / "cmake/native_sdk.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        record["cpp_policy"] = {path.relative_to(build).as_posix(): helper.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")
                                for path in sorted(build.rglob("*.vcxproj")) if "CMakeFiles" not in path.relative_to(build).parts}
        wheels = list((evidence / "leaf/wheels").glob("*.whl"))
        assert len(wheels) == 1
        record.update(wheel=str(wheels[0]), wheel_sha256=sha(wheels[0]),
                      vendor_rebuilt=False, graphics_qualified=False, status="built")
        with (evidence / "dependency-after.log").open("w", encoding="utf-8") as log:
            subprocess.run([str(ROOT / ".venv/Scripts/python.exe"), str(SNAPSHOT / "cmake/verify_dependencies.py")],
                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    finally:
        source_check()
        record["protected_after"] = protect()
        assert record["protected_after"] == before
        (evidence / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"abi": args.abi, "wheel_sha256": record["wheel_sha256"], "status": record["status"]}))


if __name__ == "__main__":
    main()
