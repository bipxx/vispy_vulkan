"""Execute the prepared scoped DIVE workflow when its GPU slot is reserved."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import traceback


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan_path = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-preparation/command-plan.json"
    plan = json.loads(plan_path.read_text())
    evidence = ROOT / "build/evidence/dive-pyside2-style-candidate-w10-qualification"
    if evidence.exists():
        raise FileExistsError("Qualification evidence must be new")
    evidence.mkdir(parents=True)
    commands = plan["commands"]
    for label, key in (("tools/oracle_dive_pyside2_style_capture.py", "capture_tool_sha256"),
                       ("tools/compare_dive_w10.py", "comparator_sha256")):
        assert sha(ROOT / label) == plan[key], label

    def protect():
        result = {relative: sha(ROOT / relative) for relative in plan["protected_native"]}
        assert result == plan["protected_native"], "Activated pass24 binaries changed"
        return result

    before = protect()
    env = dict(os.environ)
    for key in plan["unset_environment"]:
        env.pop(key, None)
    env.update(plan["environment"])
    record = {"command_plan_sha256": sha(plan_path), "runner_sha256": sha(Path(__file__)),
              "wheel_sha256": plan["wheel_sha256"], "commands": commands,
              "environment": plan["environment"], "unset_environment": plan["unset_environment"],
              "protected_before": before, "scope": plan["scope"], "status": "started"}
    (evidence / "protected-before.json").write_text(json.dumps(before, indent=2) + "\n")
    try:
        with (evidence / "capture.log").open("w", encoding="utf-8") as log:
            process = subprocess.run(commands["capture"], cwd=plan["cwd"], env=env,
                                     stdout=log, stderr=subprocess.STDOUT)
        record["capture_process_exit"] = process.returncode
        record["capture_log_sha256"] = sha(evidence / "capture.log")
        print("Scoped DIVE capture exited", process.returncode, flush=True)
        # Preserve a strict comparison failure independently from capture success.
        with (evidence / "comparison.log").open("w", encoding="utf-8") as log:
            comparison = subprocess.run(commands["compare"], cwd=plan["cwd"], env=env,
                                        stdout=log, stderr=subprocess.STDOUT)
        record["comparison_process_exit"] = comparison.returncode
        record["comparison_log_sha256"] = sha(evidence / "comparison.log")
        record["status"] = "passed" if process.returncode == comparison.returncode == 0 else "failed"
        record["qualified"] = record["status"] == "passed"
    except Exception:
        record.update(status="failed", qualified=False, orchestration_error=traceback.format_exc())
        raise
    finally:
        record["protected_after"] = protect()
        (evidence / "protected-after.json").write_text(json.dumps(record["protected_after"], indent=2) + "\n")
        for operation in ("capture", "compare"):
            command = commands[operation]
            output = Path(command[command.index("--output") + 1])
            if output.is_dir():
                record[operation + "_artifacts"] = {path.relative_to(ROOT).as_posix(): sha(path)
                                                     for path in sorted(output.rglob("*")) if path.is_file()}
            elif output.is_file():
                record[operation + "_artifacts"] = {output.relative_to(ROOT).as_posix(): sha(output)}
        (evidence / "status.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": record["status"], "capture_exit": record["capture_process_exit"],
                      "comparison_exit": record["comparison_process_exit"]}))
    return int(not record["qualified"])


if __name__ == "__main__":
    raise SystemExit(main())
