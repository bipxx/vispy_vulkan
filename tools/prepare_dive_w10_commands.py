"""Prepare checked installed DIVE commands without creating Qt or GPU objects."""

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-preparation"
    if output.exists():
        raise FileExistsError("Preparation evidence must be new")
    sealed_path = ROOT / "compat/native-sdk/w10-qt-overlay-packaging-provenance.json"
    sealed = json.loads(sealed_path.read_text())
    assert sha(sealed_path) == "4ef237f5b8d0143468cb74e0f5588320042febd04651255a3e2ab0268947d040"
    for relative, expected in sealed["artifact_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    environment = Path(sealed["hosts"]["dive"]["environment"])
    wheel = Path(sealed["leaves"]["cp310"]["wheel"])
    package = environment / "Lib/site-packages/vispy"
    installed = {}
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.startswith("vispy/") and not member.endswith("/"):
                actual = sha(package / member.removeprefix("vispy/"))
                assert actual == hashlib.sha256(archive.read(member)).hexdigest(), member
                installed[member] = actual
    activation_path = ROOT / "build/evidence/native-pass-24/activation.json"
    activation = json.loads(activation_path.read_text())
    protected = {}
    for name, expected in activation["activated"].items():
        relative = ("src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/") + name
        protected[relative] = sha(ROOT / relative)
        assert protected[relative] == expected, relative
    capture = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-pass-1"
    comparison = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-comparison.json"
    assert not capture.exists() and not comparison.exists(), "Use a fresh future capture/comparison destination"
    python = environment / "Scripts/python.exe"
    commands = {
        "capture": [str(python), "-X", "faulthandler", str(ROOT / "tools/oracle_dive_pyside2_style_capture.py"),
                    "--kind", "candidate", "--output", str(capture), "--fixtures", "image", "image_edit"],
        "compare": [str(ROOT / ".venv/Scripts/python.exe"), str(ROOT / "tools/compare_dive_w10.py"),
                    "--reference", str(ROOT / "tests/reference/dive-pyside2-style-opengl"),
                    "--candidate", str(capture), "--output", str(comparison)],
    }
    record = {"qualification": "installed_dive_command_preparation_only", "cwd": str(ROOT),
              "commands": commands, "environment": {"QT_API": "pyside2", "QT_SCALE_FACTOR": "1"},
              "unset_environment": ["QT_QPA_PLATFORM", "PYTHONPATH"],
              "wheel": str(wheel), "wheel_sha256": sha(wheel), "installed_package_files": installed,
              "sealed_packaging_proof_sha256": sha(sealed_path), "activation_manifest_sha256": sha(activation_path),
              "protected_native": protected, "capture_executed": False, "graphics_qualified": False,
              "reference_manifest_sha256": sha(ROOT / "tests/reference/dive-pyside2-style-opengl/manifest.json"),
              "capture_tool_sha256": sha(ROOT / "tools/oracle_dive_pyside2_style_capture.py"),
              "comparator_sha256": sha(ROOT / "tools/compare_dive_w10.py"),
              "preparation_tool_sha256": sha(Path(__file__)),
              "acceptance": "Two clean child exits; exact entire before/changed RGBA arrays and PNG exports; all public parameters/state identical except the known native QWidget implementation",
              "scope": sealed["dive_scope"]}
    output.mkdir(parents=True)
    (output / "command-plan.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"command_plan": str(output / "command-plan.json"), "installed_files": len(installed),
                      "capture_executed": False}))


if __name__ == "__main__":
    main()
