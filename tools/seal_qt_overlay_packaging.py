"""Seal w10 CPU packaging evidence without claiming installed graphics parity."""

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "compat/native-sdk/w10-qt-overlay-packaging-provenance.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError("A sealed packaging witness must not be overwritten")
    source = ROOT / "build/w10/source"
    source_path = source / "wheel-source-manifest.json"
    manifest = json.loads(source_path.read_text())
    base_path = ROOT / "build/w9/source/wheel-source-manifest.json"
    baseline = json.loads(base_path.read_text())
    assert manifest["source_tree_sha256"] == "f4154ac712aae052090dce67294b8d715825b4c3360f6b2a9fd9c60856581c8d"
    changed = {key for key in manifest["source_files"] if manifest["source_files"][key] != baseline["source_files"][key]}
    assert changed == {"src/vispy/app/backends/_qt.py"}
    assert not manifest["live_cpp_read"]
    files = {}

    def capture(path):
        files[path.relative_to(ROOT).as_posix()] = sha(path)

    capture(source_path)
    capture(base_path)
    activation_path = ROOT / "build/evidence/native-pass-24/activation.json"
    capture(activation_path)
    activation = json.loads(activation_path.read_text())
    for relative, expected in manifest["source_files"].items():
        assert sha(source / relative) == expected, relative
    sdk_manifest = ROOT / "build/native-sdk/windows-x64-release-3/manifest.json"
    sdk_sha = "7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2"
    assert sha(sdk_manifest) == sdk_sha
    capture(sdk_manifest)
    leaves = {}
    for abi, directory in (("cp312", "w10-sdk-cp312-pass-2"), ("cp310", "w10-sdk-cp310")):
        evidence = ROOT / "build/evidence" / directory
        record = json.loads((evidence / "provenance.json").read_text())
        assert record["process_exit"] == 0 and record["status"] == "built"
        assert record["CL_MPCount"] == "3" and not record["vendor_rebuilt"] and not record["graphics_qualified"]
        assert record["protected_before"] == record["protected_after"]
        assert record["source_tree_sha256"] == manifest["source_tree_sha256"]
        assert record["sdk_manifest_sha256"] == sdk_sha
        wheel = Path(record["wheel"])
        assert sha(wheel) == record["wheel_sha256"]
        with zipfile.ZipFile(wheel) as archive:
            qt = archive.read("vispy/app/backends/_qt.py")
            assert hashlib.sha256(qt).hexdigest() == manifest["overlay"]["snapshot_sha256"]
            native_name = f"_dawn.{abi}-win_amd64.pyd"
            sdf_name = f"_sdf_cpu.{abi}-win_amd64.pyd"
            native = {member: hashlib.sha256(archive.read(member)).hexdigest()
                      for member in archive.namelist() if member.endswith((native_name, sdf_name, ".dll"))}
            assert any(member.endswith(native_name) for member in native)
            assert any(member.endswith(sdf_name) for member in native)
        leaves[abi] = {"wheel": str(wheel), "wheel_sha256": sha(wheel), "native_members": native,
                       "evidence": evidence.relative_to(ROOT).as_posix(),
                       "process_exit": 0, "graphics_qualified": False}
        for path in evidence.rglob("*"):
            if path.is_file():
                capture(path)
        capture(source / f"build/sdk-{abi}/CMakeCache.txt")
    hosts = {}
    for name, directory, lock in (
        ("glue", "glue-candidate-w10-preparation", "glue-candidate-w10-windows-cpython312.txt"),
        ("dive", "w10-dive-pyside2-cpu-preflight", "dive-pyside2-candidate-w10-windows-cpython310.txt"),
    ):
        evidence = ROOT / "build/evidence" / directory
        proof = json.loads((evidence / "provenance.json").read_text())
        assert proof["dependency_versions_unchanged"]
        assert not proof.get("graphics_qualified", proof.get("legacy_graphics_qualified", True))
        requirement_path = ROOT / "compat/host-environments" / lock
        assert sha(requirement_path) == proof["requirements_sha256"]
        hosts[name] = {"environment": proof["environment"], "requirements": requirement_path.relative_to(ROOT).as_posix(),
                       "requirements_sha256": sha(requirement_path), "evidence": evidence.relative_to(ROOT).as_posix(),
                       "wheel_sha256": proof["wheel_sha256"], "cpu_preflight": "passed",
                       "graphics_qualified": False}
        capture(requirement_path)
        for path in evidence.rglob("*"):
            if path.is_file():
                capture(path)
    # Retain the real pre-compilation PowerShell failure alongside the successful retry.
    failed = ROOT / "build/evidence/w10-sdk-cp312"
    assert json.loads((failed / "provenance.json").read_text())["process_exit"] == 1
    for path in failed.rglob("*"):
        if path.is_file():
            capture(path)
    for relative in ("tools/freeze_qt_overlay.py", "tools/build_qt_overlay_leaf.py", "tools/prepare_installed_glue.py",
                     "tools/installed_glue_cpu.py", "tools/prepare_compatible_dive.py", "tools/compatible_dive_cpu.py",
                     "tools/seal_qt_overlay_packaging.py", "tools/oracle_dive_pyside2_style_capture.py",
                     "tools/compare_dive_installed.py", "tests/reference/dive-pyside2-style-opengl/manifest.json"):
        capture(ROOT / relative)
    result = {"schema": 1, "scope": "Two actual isolated w10 ABI wheels and new unchanged-dependency host CPU preparations only",
              "source_tree_sha256": manifest["source_tree_sha256"], "baseline_source_tree_sha256": baseline["source_tree_sha256"],
              "only_overlay": manifest["overlay"], "sdk_manifest_sha256": sdk_sha,
              "protected_baseline": "native-pass-24/activation.json", "activated_native": activation["activated"],
              "leaves": leaves, "hosts": hosts, "artifact_hashes": files,
              "installed_core_graphics_and_rollback_qualified": False,
              "host_full_frame_parity_qualified": False,
              "dive_scope": "Only previously admitted image/image_edit with public test-owned style restoration after screenshots; ordinary host teardown and scatter remain unresolved",
              "remaining_gates": ["Installed Glue complete volume and fixed-frame comparisons",
                                  "Installed scoped DIVE full arrays/PNG comparisons and clean child exits",
                                  "Final-runtime clean core consumers and remaining compatible ABI/binding/platform matrix"]}
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"proof": OUTPUT.relative_to(ROOT).as_posix(), "sha256": sha(OUTPUT), "graphics_qualified": False}))


if __name__ == "__main__":
    main()
