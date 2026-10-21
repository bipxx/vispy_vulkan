"""Prepare a new Glue lock/environment, changing only the installed VisPy wheel."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


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
        parser.error("Environment, lock and evidence must all be new")
    baseline = ROOT / "tools/oracle_glue_requirements.txt"
    text = baseline.read_text(encoding="utf-8")
    pattern = r"(?m)^vispy==0\.17\.0 \\\n(?:    --hash=sha256:[a-f0-9]+(?: \\)?\n)+"
    replacement = "vispy @ " + wheel.as_uri() + " --hash=sha256:" + sha(wheel) + "\n"
    changed, count = re.subn(pattern, replacement, text)
    assert count == 1, "Expected one exact upstream VisPy hash block"
    assert re.sub(pattern, "VISPY_WHEEL\n", text) == changed.replace(replacement, "VISPY_WHEEL\n")
    requirements.parent.mkdir(parents=True, exist_ok=True)
    requirements.write_text(changed, encoding="utf-8")
    evidence.mkdir(parents=True)
    prepared = json.loads((ROOT / "compat/cp312-candidate/preparation.json").read_text())
    interpreter = Path(prepared["environment"]) / "Scripts/python.exe"
    commands = []
    uv = shutil.which("uv")
    assert uv

    def run(command, logname, *, cwd=ROOT):
        with (evidence / logname).open("w", encoding="utf-8") as log:
            process = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                     env=dict(os.environ, QT_API="pyqt6", QT_QPA_PLATFORM="offscreen"))
        commands.append({"argv": command, "cwd": str(cwd), "exit_code": process.returncode,
                         "log": logname, "log_sha256": sha(evidence / logname)})
        assert process.returncode == 0, (logname, "CPU preparation failed; evidence retained")

    baseline_python = ROOT / "build/host-environments/glue-cpython312-pyqt6-candidate-w5/Scripts/python.exe"
    before = json.loads(subprocess.check_output([uv, "pip", "list", "--python", str(baseline_python), "--format", "json"]))
    before = {row["name"].lower().replace("_", "-"): row["version"] for row in before}
    record = {"scope": "CPU preparation only; installed host graphics comparisons pending",
              "environment": str(environment), "requirements": str(requirements),
              "requirements_sha256": sha(requirements), "baseline_requirements_sha256": sha(baseline),
              "wheel": str(wheel), "wheel_sha256": sha(wheel), "commands": commands,
              "dependency_versions_unchanged": False, "graphics_qualified": False,
              "preparation_tool_sha256": sha(Path(__file__))}
    try:
        run([uv, "venv", str(environment), "--python", str(interpreter)], "venv.log")
        python = environment / "Scripts/python.exe"
        run([uv, "pip", "install", "--python", str(python), "--require-hashes", "--only-binary", ":all:",
             "-r", str(requirements)], "install.log")
        run([uv, "pip", "check", "--python", str(python)], "dependency-check.log")
        with tempfile.TemporaryDirectory(prefix="vispy-glue-cpu-") as external:
            run([str(python), "-I", str(ROOT / "tools/installed_glue_cpu.py"), "--wheel", str(wheel),
                 "--output", str(evidence / "cpu.json")], "cpu.log", cwd=Path(external))
        cpu = json.loads((evidence / "cpu.json").read_text())
        assert cpu["distributions"] == before, "Installed versions differ from the original candidate host"
        record.update(dependency_versions_unchanged=True, status="prepared", cpu_sha256=sha(evidence / "cpu.json"),
                      installed_package_files_verified=len(cpu["wheel_package_files"]))
    finally:
        (evidence / "provenance.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"environment": str(environment), "cpu_preflight": "passed", "graphics_qualified": False}))


if __name__ == "__main__":
    main()
