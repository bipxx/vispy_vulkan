"""Capture fixed U01 public draws/U03 queue-boundary contracts in isolation."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import numpy as np

from fixture_buffer_ordering import (CASES, COMPARISON, actual_cpu_queue_transcript,
    assert_image, assert_trace, case_contract, render)
from oracle_image_extensions_capture import cpu_origins

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/reference/buffer-ordering-opengl"
LOCK = ROOT / "tools/oracle_napari_requirements.txt"
SOURCES = ("tools/fixture_buffer_ordering.py", "tools/oracle_buffer_ordering_capture.py",
           "tests/parity/test_buffer_ordering_parity.py", "tools/fixture_gloo.py",
           "tools/oracle_capture.py", "tools/oracle_image_extensions_capture.py")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def freeze_authoring(output):
    assert not (output / "manifest.json").exists(), "captured authoring is immutable"
    output.mkdir(parents=True, exist_ok=True)
    authoring = {"schema": 1, "candidate_seen": False, "GPU_used": False,
        "comparison": COMPARISON, "cases": {name: case_contract(name) for name in CASES},
        "sources_sha256": {path: sha(ROOT / path) for path in SOURCES},
        "installed_upstream_lock": {"file": str(LOCK.relative_to(ROOT)), "sha256": sha(LOCK)},
        "scope": "U01 public middle-subdata with old/new draws pending; U03 internal real GLIR boundary with unchanged filter; public Program.draw auto-flushes"}
    target = output / "authoring.json"
    if target.exists():
        assert json.loads(target.read_text()) == authoring, "freeze changes in a new attempt"
    write(target, authoring)
    snapshots = output / "authoring-sources"
    snapshots.mkdir(exist_ok=True)
    for source in SOURCES:
        target = snapshots / Path(source).name
        if target.exists():
            assert sha(target) == authoring["sources_sha256"][source]
        else:
            target.write_bytes((ROOT / source).read_bytes())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze-authoring", action="store_true")
    parser.add_argument("--cpu-transcript", action="store_true")
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.freeze_authoring:
        assert args.kind is None and not args.cpu_transcript and args.worker is None
        freeze_authoring(args.output)
        print("FROZEN two buffer contracts; no graphics context/candidate")
        return 0
    assert args.kind
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("PYTHONHASHSEED", "0")
    authoring_path = (REFERENCE if args.kind == "candidate" else args.output) / "authoring.json"
    authoring = json.loads(authoring_path.read_text())
    assert authoring["cases"] == {name: case_contract(name) for name in CASES}
    for source, digest in authoring["sources_sha256"].items():
        assert sha(ROOT / source) == digest, source
    assert sha(LOCK) == authoring["installed_upstream_lock"]["sha256"]
    origins = cpu_origins(args.kind)
    package = Path(origins["vispy_origin"])
    files = ("gloo/glir.py", "gloo/buffer.py", "gloo/program.py", "gloo/context.py")
    origins["queue_buffer_source_sha256"] = {name: sha(package / name) for name in files}
    if args.kind == "upstream":
        pin = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
        for name, digest in origins["queue_buffer_source_sha256"].items():
            assert digest == pin["files"][name], name
    args.output.mkdir(parents=True, exist_ok=True)
    if args.cpu_transcript:
        target = args.output / "upstream-cpu-filter-transcript.json"
        assert args.kind == "upstream" and not target.exists()
        write(target, {"provenance": origins, "authoring_sha256": sha(authoring_path),
            "transcript": actual_cpu_queue_transcript(), "GPU_used": False})
        print("PASS actual pinned upstream GlirQueue.flush transcript; no GPU")
        return 0
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    manifest = {"schema": 1, "provenance": origins, "comparison": COMPARISON,
        "authoring_sha256": sha(authoring_path), "fixtures": {}, "errors": {}, "processes": {}}
    if not args.worker:
        assert not (args.output / "manifest.json").exists(), "preserve every capture attempt"
        for name in CASES:
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__).resolve()),
                "--kind", args.kind, "--output", str(args.output), "--worker", name],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            process = {"exit_code": child.returncode}
            for stream in ("stdout", "stderr"):
                target = args.output / f"{name}.{stream}.log"
                target.write_text(getattr(child, stream), encoding="utf-8")
                process[stream] = {"file": target.name, "sha256": sha(target)}
            manifest["processes"][name] = process
            print(child.stdout, end="", flush=True)
            print(child.stderr, end="", file=sys.stderr, flush=True)
            target = args.output / f"{name}.capture.json"
            capture = json.loads(target.read_text()) if target.exists() else {"fixtures": {}, "errors": {}}
            if child.returncode == 0 and name in capture["fixtures"]:
                record = capture["fixtures"][name]
                record["capture"] = {"file": target.name, "sha256": sha(target)}
                manifest["fixtures"][name] = record
            else:
                manifest["errors"][name] = capture["errors"].get(name, {"error": f"child exited {child.returncode}; not admitted"})
            write(args.output / "manifest.json", manifest)
        return int(bool(manifest["errors"]))
    try:
        if args.kind == "upstream":
            import vispy
            vispy.use(gl="gl+")
        from oracle_capture import provenance
        actual = provenance(args.kind)
        image, commands, shaders, parameters, observations = render(args.worker,
            "pyqt6" if args.kind == "upstream" else "dawn_headless")
        artifacts = {}
        for key, suffix, value in (("rgba", "npy", image), ("filtered_glir", "glir.json", commands),
                ("expanded_shaders", "shaders.json", shaders), ("parameters", "parameters.json", parameters),
                ("observations", "observations.json", observations)):
            target = args.output / f"{args.worker}.{suffix}"
            np.save(target, value, allow_pickle=False) if suffix == "npy" else write(target, value)
            artifacts[key] = {"file": target.name, "sha256": sha(target)}
        assert_image(args.worker, image)
        assert_trace(args.worker, commands, observations)
        assert commands and shaders
        if args.kind == "upstream":
            assert observations["sample_source"] == "OpenGL driver GL_SAMPLES"
            assert observations["physical_samples"] == 1
        manifest["fixtures"][args.worker] = {"parameters": parameters, "observations": observations,
            "artifacts": artifacts, "actual_renderer_provenance": actual}
        print("PASS independent buffer ordering", args.worker, "exact analytic pixels and actual filtered commands", flush=True)
    except Exception as error:
        manifest["errors"][args.worker] = {"type": type(error).__name__, "error": str(error)}
        traceback.print_exc()
    write(args.output / f"{args.worker}.capture.json", manifest)
    return int(bool(manifest["errors"]))

if __name__ == "__main__":
    raise SystemExit(main())
