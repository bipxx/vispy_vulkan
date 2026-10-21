"""Seal the two actual installed scoped DIVE parity proofs separately from CPU prep."""

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "compat/host-environments/dive-pyside2-candidate-w10-scoped-parity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError("A sealed actual parity proof must be new")
    preparation_path = ROOT / "compat/native-sdk/w10-qt-overlay-packaging-provenance.json"
    preparation = json.loads(preparation_path.read_text())
    capture_root = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-pass-1"
    qualification_root = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-qualification"
    comparison_path = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-comparison.json"
    comparison = json.loads(comparison_path.read_text())
    status = json.loads((qualification_root / "status.json").read_text())
    assert status["status"] == "passed" and status["capture_process_exit"] == status["comparison_process_exit"] == 0
    assert status["protected_before"] == status["protected_after"]
    assert comparison["qualified"] and comparison["fixed_public_parameters_qualified"]
    assert not comparison["ordinary_host_teardown_qualified"] and not comparison["scatter_qualified"]
    manifest = json.loads((capture_root / "manifest.json").read_text())
    assert set(manifest["fixtures"]) == {"image", "image_edit"} and not manifest["errors"]
    environment = Path(preparation["hosts"]["dive"]["environment"])
    wheel = Path(preparation["leaves"]["cp310"]["wheel"])
    assert sha(wheel) == status["wheel_sha256"] == preparation["leaves"]["cp310"]["wheel_sha256"]
    package = environment / "Lib/site-packages/vispy"
    installed = {}
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.startswith("vispy/") and not member.endswith("/"):
                expected = hashlib.sha256(archive.read(member)).hexdigest()
                assert sha(package / member.removeprefix("vispy/")) == expected, member
                installed[member] = expected
    files = {}

    def capture(path):
        files[path.relative_to(ROOT).as_posix()] = sha(path)

    capture(preparation_path)
    capture(wheel)
    capture(comparison_path)
    reference = ROOT / "tests/reference/dive-pyside2-style-opengl"
    for directory in (reference, capture_root, qualification_root,
                      ROOT / "build/evidence/dive-pyside2-style-candidate-w10-preparation"):
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                capture(path)
    qt_sha = preparation["only_overlay"]["snapshot_sha256"]
    children = {}
    for name, row in manifest["fixtures"].items():
        assert row["process"]["exit_code"] == 0
        cleanup = json.loads((capture_root / row["cleanup"]["file"]).read_text())
        integrity = cleanup["installed_vispy_record_integrity"]
        assert integrity["files_checked"] == len(installed) == 545
        assert integrity["selected"]["vispy/app/backends/_qt.py"]["sha256"] == qt_sha
        assert cleanup["qapplication_destroyed"] and not cleanup["top_level_after"]
        raw = json.loads((capture_root / row["capture"]["file"]).read_text())
        origin = Path(raw["provenance"]["vispy_origin"])
        assert origin.resolve() == package.resolve()
        assert raw["provenance"]["binding"] == "PySide2"
        assert raw["provenance"]["host_package_tree_sha256"] == "545fef99d793c155a9e04441b41d54ce3a3964e5ace1005e5f90ee50353cd026"
        renderer = raw["provenance"]["renderer"]
        assert renderer["ok"] and renderer["backend"] == "Vulkan" and not renderer["software"]
        checked = comparison["results"][name]
        assert checked["full_frame_exact"] and checked["public_parameters_exact"]
        assert all(frame["pixels_differing"] == frame["max_abs"] == 0 for frame in checked["frames"].values())
        assert all(checked["png_bytes_exact"].values())
        children[name] = {"process_exit": 0, "renderer": renderer, "vispy_origin": str(origin),
                          "capture_dependency_metadata_sha256": raw["provenance"]["requirements_sha256"],
                          "actual_candidate_requirements_sha256": preparation["hosts"]["dive"]["requirements_sha256"],
                          "frames": checked["frames"], "png_bytes_exact": checked["png_bytes_exact"],
                          "public_parameters_exact": True, "qapplication_destroyed": True}
    for relative in ("tools/compare_dive_w10.py", "tools/run_dive_w10_qualification.py",
                     "tools/seal_dive_w10_parity.py", "tools/oracle_dive_pyside2_style_capture.py",
                     "tools/oracle_dive_pyside2_cleanup_capture.py", "tools/fixture_dive_pyside2.py",
                     "compat/host-environments/dive-pyside2-candidate-w10-windows-cpython310.txt"):
        capture(ROOT / relative)
    proof = {"schema": 1, "scope": comparison["scope"], "source_tree_sha256": preparation["source_tree_sha256"],
             "wheel_sha256": sha(wheel), "qt_overlay_sha256": qt_sha, "environment": str(environment),
             "children": children, "scoped_image_export_parity_qualified": True,
             "ordinary_host_teardown_qualified": False, "scatter_qualified": False,
             "installed_core_rollback_qualified": False,
             "dependency_metadata_note": "The unchanged capture tool retains its original upstream dependency-lock hash; actual unchanged-version candidate lock and exact installed wheel are separately recorded and verified",
             "protected_native_before": status["protected_before"], "protected_native_after": status["protected_after"],
             "installed_wheel_package_files": installed, "artifact_hashes": files,
             "comparison": comparison_path.relative_to(ROOT).as_posix(),
             "prior_failures_preserved": ["dive-opengl", "dive-pyside2-opengl", "dive-pyside2-cleanup-opengl",
                                          "dive-pyside2-style-candidate-w5-pass-1", "dive-pyside2-style-candidate-w8b-pass-1"]}
    OUTPUT.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"proof": OUTPUT.relative_to(ROOT).as_posix(), "sha256": sha(OUTPUT),
                      "scoped_image_export_parity": "passed", "ordinary_host_teardown_qualified": False}))


if __name__ == "__main__":
    main()
