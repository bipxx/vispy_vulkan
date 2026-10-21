"""Preserve the exact parent capture and terminal/protected-native witnesses."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def native():
    return {str(path.relative_to(ROOT)): sha(path) for path in (ROOT / "src/vispy").rglob("*.pyd")}


assert not (OUT / "capture-terminal.json").exists()
authoring = json.loads((OUT / "authoring.json").read_text())
for source, digest in authoring["sources_sha256"].items():
    assert sha(ROOT / source) == digest, source
before = native()
command = [sys.executable, "-X", "faulthandler", str(ROOT / "tools/oracle_marker_extensions_corrected_capture.py"),
           "--kind", "upstream", "--output", str(OUT)]
write("capture-command.json", {"argv": command, "cwd": str(ROOT), "job_source_sha256": sha(__file__),
                               "authoring_sha256": sha(OUT / "authoring.json"), "native_before": before,
                               "environment": {name: os.environ.get(name) for name in ("QT_API", "QT_SCALE_FACTOR", "PYTHONHASHSEED")},
                               "sources_before": authoring["sources_sha256"]})
with (OUT / "parent.stdout.log").open("w", encoding="utf-8") as stdout, (OUT / "parent.stderr.log").open("w", encoding="utf-8") as stderr:
    child = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
after = native()
sources_after = {source: sha(ROOT / source) for source in authoring["sources_sha256"]}
write("capture-terminal.json", {"exit_code": child.returncode, "native_after": after,
                                "native_unchanged": before == after,
                                "sources_after": sources_after, "sources_unchanged": sources_after == authoring["sources_sha256"],
                                "manifest_sha256": sha(OUT / "manifest.json") if (OUT / "manifest.json").exists() else None,
                                "parent_stdout_sha256": sha(OUT / "parent.stdout.log"),
                                "parent_stderr_sha256": sha(OUT / "parent.stderr.log")})
print("Marker capture terminal exit", child.returncode, flush=True)
assert before == after and sources_after == authoring["sources_sha256"]
raise SystemExit(child.returncode)
