"""Install a fresh DIVE CPU candidate using unchanged dependencies and source."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    environment, requirements, evidence = (path.resolve() for path in
                                           (args.environment, args.requirements, args.evidence))
    if any(path.exists() for path in (environment, requirements, evidence)):
        parser.error("Candidate environment, lock and evidence must all be new")
    baseline = ROOT / "compat/host-environments/dive-pyside2-candidate-w5-windows-cpython310.txt"
    text = baseline.read_text(encoding="utf-8")
    replacement = "vispy @ " + wheel.as_uri() + " --hash=sha256:" + sha(wheel)
    text, count = re.subn(r"^vispy @ .+$", replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected one pinned VisPy wheel in the existing dependency lock")
    requirements.write_text(text, encoding="utf-8")
    evidence.mkdir(parents=True)
    prepared = json.loads((ROOT / "compat/cp310-candidate/preparation.json").read_text())
    interpreter = Path(prepared["environment"]) / "Scripts/python.exe"

    def run(arguments, name):
        with (evidence / name).open("w", encoding="utf-8") as log:
            subprocess.run(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)

    run(["uv", "venv", str(environment), "--python", str(interpreter)], "venv.log")
    python = environment / "Scripts/python.exe"
    run(["uv", "pip", "install", "--python", str(python), "--require-hashes", "--only-binary", ":all:",
         "-r", str(requirements)], "install.log")
    source = ROOT / "build/host-sources/dive-aa575e1c020f0c5e8227bfb234fa192fa2b12924/DIVE-aa575e1c020f0c5e8227bfb234fa192fa2b12924/DIVE"
    spec = importlib.util.spec_from_file_location("host_inventory", ROOT / "tools/host_inventory.py")
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    assert inventory.source_inventory(source)["sha256"] == "545fef99d793c155a9e04441b41d54ce3a3964e5ace1005e5f90ee50353cd026"
    destination = environment / "Lib/site-packages/DIVE"
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    assert inventory.source_inventory(destination)["sha256"] == inventory.source_inventory(source)["sha256"]
    run([str(python), "-I", str(ROOT / "tools/compatible_dive_cpu.py"), "--wheel", str(wheel),
         "--output", str(evidence / "cpu.json")], "cpu.log")
    record = json.loads((evidence / "cpu.json").read_text())
    baseline_cpu = json.loads((ROOT / "compat/host-environments/dive-pyside2-candidate-w5-cpu.json").read_text())
    assert record["distributions"] == baseline_cpu["distributions"]
    run(["uv", "pip", "check", "--python", str(python)], "dependency-check.log")
    proof = {"qualification": "compatible_dive_candidate_cpu_preflight_only", "environment": str(environment),
             "requirements": str(requirements), "requirements_sha256": sha(requirements),
             "baseline_requirements_sha256": sha(baseline), "wheel": str(wheel), "wheel_sha256": sha(wheel),
             "dependency_versions_unchanged": True, "old_environments_preserved": True,
             "dive_source_sha256": inventory.source_inventory(destination)["sha256"],
             "no_invented_distribution_metadata": True, "legacy_graphics_qualified": False,
             "native_shutdown_mutex_verified": record["native_shutdown_mutex_verified"],
             "loaded_msvc_runtime_sha256": record["loaded_msvc_runtime_sha256"],
             "evidence_sha256": {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(evidence.rglob("*")) if path.is_file()}}
    (evidence / "provenance.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"environment": str(environment), "cpu_preflight": "passed", "graphics_qualified": False}))


if __name__ == "__main__":
    main()
