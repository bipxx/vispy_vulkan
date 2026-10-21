"""Seal observed compatible SDK/build/consumer results without upgrading failures."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_sdk", ROOT / "cmake/native_sdk.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


def load(path):
    data = path.read_bytes()
    return json.loads(data.decode("utf-16" if data[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Qualification provenance must be new")
    source = ROOT / "build/w8b/source"
    source_manifest = load(source / "wheel-source-manifest.json")
    assert source_manifest["source_tree_sha256"] == "01c3e80263277f24392f028cde7dc9576072cabdabf4e9329d02449ddb9f8fc4"
    for name, digest in source_manifest["source_files"].items():
        assert sdk.sha256(source / name) == digest, name
    prefix = ROOT / "build/native-sdk/windows-x64-release-3"
    digest = "7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2"
    manifest = load(prefix / "manifest.json")
    sdk.verify(prefix, digest, source / "cmake/dependencies.lock.json", manifest["producer"])
    producer = ROOT / "build/evidence/w8b-compatible-producer-2"
    assert load(producer / "status.json")["status"] == "built"
    assert load(producer / "protected-source-binaries-before.json") == load(producer / "protected-source-binaries-after.json")
    assert "Verified 10 immutable dependency source trees" in (producer / "dependencies-after.log").read_text(encoding="utf-8-sig")
    leaves = {}
    evidence = {prefix / "manifest.json", source / "wheel-source-manifest.json",
                ROOT / "build/evidence/w8b-compatible-sdk-stage.log",
                ROOT / "build/evidence/native-sdk-compatibility-policy-4.log",
                ROOT / "build/evidence/native-sdk-compatibility-policy-4.xml"}
    evidence.update(path for path in producer.rglob("*") if path.is_file())
    for abi in ("cp312", "cp310"):
        leaf = ROOT / f"build/evidence/w8b-sdk-{abi}"
        wheel = next((leaf / "wheels").glob("*.whl"))
        assert load(leaf / "protected-source-binaries-before.json") == load(leaf / "protected-source-binaries-after.json")
        build = source / f"build/sdk-{abi}"
        projects = {path.relative_to(build).as_posix(): sdk.project_mutex_policy(path, manifest["producer"]["msvc_mutex_policy"])
                    for path in sorted(build.rglob("*.vcxproj")) if "CMakeFiles" not in path.relative_to(build).parts}
        with zipfile.ZipFile(wheel) as archive:
            natives = {name: hashlib.sha256(archive.read(name)).hexdigest()
                       for name in archive.namelist() if name.endswith((".pyd", ".dll"))}
        assert len(natives) == 3
        leaves[abi] = {"wheel": wheel.relative_to(ROOT).as_posix(), "wheel_sha256": sdk.sha256(wheel),
                       "wheel_native_sha256": natives, "build_exit_code": 0, "source_native_artifacts_unchanged": True,
                       "consumer_cache_sha256": sdk.sha256(build / "CMakeCache.txt"), "cpp_projects": projects}
        evidence.update(path for path in leaf.rglob("*") if path.is_file())
        evidence.add(ROOT / f"build/evidence/w8b-sdk-{abi}-build.log")
    consumer_log = ROOT / "build/evidence/w8b-clean-wheel-cp312-consumer.log"
    consumer_xml = ROOT / "build/evidence/w8b-clean-wheel-cp312-consumer.xml"
    suite = ET.parse(consumer_xml).getroot().find("testsuite")
    assert suite.attrib["tests"] == "1" and all(suite.attrib[key] == "0" for key in ("errors", "failures", "skipped"))
    text = consumer_log.read_text(encoding="utf-8-sig")
    assert "wheel uninstall and upstream reinstall 0.17.0" in text
    consumer = json.loads(next(line.removeprefix("wheel consumer evidence ") for line in text.splitlines()
                               if line.startswith("wheel consumer evidence ")))
    assert consumer["device"]["ok"] and not consumer["device"]["software"]
    assert consumer["device"]["backend"] == "Vulkan"
    before = ROOT / "build/evidence/w8b-cp312-consumer-native-before.json"
    after = ROOT / "build/evidence/w8b-cp312-consumer-native-after.json"
    assert load(before) == load(after)
    evidence.update((consumer_log, consumer_xml, before, after))
    cpu_dir = ROOT / "build/evidence/w8b-dive-pyside2-cpu-preflight"
    cpu = load(cpu_dir / "cpu.json")
    assert cpu["native_shutdown_mutex_verified"] and cpu["font_and_compiled_sdf_verified"]
    assert not cpu["graphics_device_created"] and not cpu["qapplication_created"]
    assert cpu["loaded_msvc_runtime_sha256"] == "f87819ae8c6f7c90d3237a1abb9809e8cba9dcd0c80ac3f0969a5e68ef652ca4"
    evidence.update(path for path in cpu_dir.rglob("*") if path.is_file())
    candidate_dir = ROOT / "build/evidence/dive-pyside2-style-candidate-w8b-pass-1"
    comparison = load(candidate_dir / "comparison.json")
    assert comparison["legacy_init_render_and_clean_exit_verified"]
    assert not comparison["scoped_pixel_parity_qualified"]
    evidence.update(path for path in candidate_dir.rglob("*") if path.is_file())
    evidence.update((ROOT / "build/evidence/dive-pyside2-style-candidate-w8b-pass-1.log",
                     ROOT / "build/evidence/dive-pyside2-style-candidate-w8b-comparison.log",
                     ROOT / "build/evidence/w8b-dive-candidate-native-before.json",
                     ROOT / "build/evidence/w8b-dive-candidate-native-after.json",
                     ROOT / "compat/host-environments/dive-pyside2-candidate-w8b-windows-cpython310.txt"))
    assert load(ROOT / "build/evidence/w8b-dive-candidate-native-before.json") == load(ROOT / "build/evidence/w8b-dive-candidate-native-after.json")
    evidence.update(ROOT / name for name in ("tools/stage_native_sdk.py", "tools/verify_native_producer.py",
                                           "tools/prepare_compatible_dive.py", "tools/compatible_dive_cpu.py",
                                           "tools/compare_dive_installed.py", "tools/seal_compatible_sdk.py"))
    record = {"qualification": "compatible_windows_vendor_rebuild_cp312_core_and_cp310_scoped_legacy_result",
              "source_snapshot": "build/w8b/source", "source_tree_sha256": source_manifest["source_tree_sha256"],
              "runtime_milestone": source_manifest["runtime_milestone"], "sdk": prefix.relative_to(ROOT).as_posix(),
              "sdk_manifest_sha256": digest, "sdk_format": 2, "compiler_policy": manifest["producer"]["msvc_mutex_policy"],
              "full_vendor_compatibility_rebuild_completed": True, "old_default_archives_reused": False,
              "source_native_artifacts_unchanged": True, "python_abi_objects_reused": False, "leaves": leaves,
              "cp312_clean_core_consumer": {"exit_code": 0, "passed": 1, "skipped": 0, "evidence": consumer,
                                           "native_text_sdf_assets_notices_and_rollback_verified": True},
              "cp310_old_crt_cpu_preflight": {"passed": True, "native_shutdown_mutex_verified": True,
                                              "loaded_runtime_sha256": cpu["loaded_msvc_runtime_sha256"]},
              "cp310_legacy_init_render_clean_exit_verified": True, "cp310_scoped_dive_pixel_parity_qualified": False,
              "cp310_scoped_dive_comparison": comparison["results"], "ordinary_dive_host_qualified": False,
              "compatible_five_abi_matrix_qualified": False, "full_binding_host_platform_matrix_qualified": False,
              "original_w5_artifacts_preserved": True,
              "remaining": ["Exact scoped DIVE screenshot alpha/RGB parity", "Ordinary unchanged DIVE teardown/scatter admission",
                            "Compatible CP310 clean core/rollback and CP311/313/314 builds/consumers", "Final runtime source and installed public Qt/host/plugin matrix",
                            "Linux/macOS architecture-specific build and hardware consumers"],
              "evidence_sha256": {path.relative_to(ROOT).as_posix(): sdk.sha256(path) for path in sorted(evidence)}}
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"provenance": str(args.output), "sha256": sdk.sha256(args.output),
                      "cp312_core_consumer": "passed", "cp310_legacy_init": "passed", "cp310_scoped_pixel_parity": "failed"}))


if __name__ == "__main__":
    main()
