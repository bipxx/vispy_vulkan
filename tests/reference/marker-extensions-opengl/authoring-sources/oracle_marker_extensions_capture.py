"""Freeze marker criteria or capture installed upstream/candidate in children."""

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

from fixture_marker_extensions import CASES, COMPARISON, assert_landmarks, assert_trace, case_contract, render
from oracle_image_extensions_capture import cpu_origins

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/reference/marker-extensions-opengl"
LOCK = ROOT / "tools/oracle_napari_requirements.txt"
SOURCES = ("tools/fixture_marker_extensions.py", "tools/oracle_marker_extensions_capture.py",
           "tests/parity/test_marker_extensions_parity.py")
DEPENDENCIES = ("tools/fixture_gloo.py", "tools/oracle_capture.py", "tools/oracle_image_extensions_capture.py")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze_authoring(output):
    assert not (output / "manifest.json").exists(), "captured authoring is immutable"
    output.mkdir(parents=True, exist_ok=True)
    payload = {"schema": 1, "candidate_seen": False, "GPU_used": False,
        "comparison": COMPARISON, "cases": {name: case_contract(name) for name in CASES},
        "sources_sha256": {source: sha256(ROOT / source) for source in SOURCES + DEPENDENCIES},
        "installed_upstream_lock": {"file": str(LOCK.relative_to(ROOT)), "sha256": sha256(LOCK)},
        "scope": "14 small actual marker scenes; excludes 1M performance, picking and total signal retirement"}
    authoring = output / "authoring.json"
    if authoring.exists():
        assert json.loads(authoring.read_text()) == payload, "use a new attempt when authoring changes"
    write_json(authoring, payload)
    snapshots = output / "authoring-sources"
    snapshots.mkdir(exist_ok=True)
    for source in SOURCES + DEPENDENCIES:
        target = snapshots / Path(source).name
        if target.exists():
            assert sha256(target) == payload["sources_sha256"][source]
        else:
            target.write_bytes((ROOT / source).read_bytes())
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    parser.add_argument("--freeze-authoring", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.freeze_authoring:
        assert args.kind is None and args.worker is None
        freeze_authoring(args.output)
        print("FROZEN", len(CASES), "marker workflows; no graphics context or candidate")
        return 0
    assert args.kind, "--kind is required"
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("PYTHONHASHSEED", "0")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    authoring_path = (REFERENCE if args.kind == "candidate" else args.output) / "authoring.json"
    authoring = json.loads(authoring_path.read_text())
    assert authoring["cases"] == {name: case_contract(name) for name in CASES}
    for source, expected in authoring["sources_sha256"].items():
        assert sha256(ROOT / source) == expected, source
    assert sha256(LOCK) == authoring["installed_upstream_lock"]["sha256"]
    origins = cpu_origins(args.kind)
    package = Path(origins["vispy_origin"])
    pin = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    visual_files = ("visuals/markers.py", "visuals/mesh.py", "scene/canvas.py",
                    "scene/cameras/base_camera.py", "scene/cameras/panzoom.py",
                    "visuals/transforms/transform_system.py")
    origins["marker_source_sha256"] = {name: sha256(package / name) for name in visual_files}
    if args.kind == "upstream":
        for name, digest in origins["marker_source_sha256"].items():
            assert digest == pin["files"][name], name
    origins.update(marker_fixture_sha256=sha256(ROOT / SOURCES[0]),
                   marker_capture_sha256=sha256(Path(__file__)))
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": origins, "comparison": COMPARISON,
                "authoring_sha256": sha256(authoring_path), "fixtures": {}, "errors": {}, "processes": {}}
    if not args.worker:
        assert not (args.output / "manifest.json").exists(), "preserve every attempt"
        for name in args.fixtures or CASES:
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__).resolve()),
                "--kind", args.kind, "--output", str(args.output), "--worker", name],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            process = {"exit_code": child.returncode}
            for stream in ("stdout", "stderr"):
                path = args.output / f"{name}.{stream}.log"
                path.write_text(getattr(child, stream), encoding="utf-8")
                process[stream] = {"file": path.name, "sha256": sha256(path)}
            manifest["processes"][name] = process
            print(child.stdout, end="", flush=True)
            print(child.stderr, end="", file=sys.stderr, flush=True)
            capture = args.output / f"{name}.capture.json"
            data = json.loads(capture.read_text()) if capture.exists() else {"fixtures": {}, "errors": {}}
            if child.returncode == 0 and name in data["fixtures"]:
                record = data["fixtures"][name]
                record["capture"] = {"file": capture.name, "sha256": sha256(capture)}
                manifest["fixtures"][name] = record
            else:
                manifest["errors"][name] = data["errors"].get(name, {"error": f"child exited {child.returncode}; no admission"})
            write_json(args.output / "manifest.json", manifest)
        return int(bool(manifest["errors"]))
    try:
        if args.kind == "upstream":
            import vispy
            vispy.use(gl="gl+")
        from oracle_capture import provenance
        actual = provenance(args.kind)
        image, commands, shaders, params, observations = render(args.worker,
            "pyqt6" if args.kind == "upstream" else "dawn_headless")
        artifacts = {}
        for key, suffix, value in (("rgba", "npy", image), ("filtered_glir", "glir.json", commands),
                                  ("expanded_shaders", "shaders.json", shaders),
                                  ("parameters", "parameters.json", params), ("observations", "observations.json", observations)):
            path = args.output / f"{args.worker}.{suffix}"
            np.save(path, value, allow_pickle=False) if suffix == "npy" else write_json(path, value)
            artifacts[key] = {"file": path.name, "sha256": sha256(path)}
        assert_landmarks(args.worker, image)
        assert_trace(args.worker, commands, observations)
        assert commands and shaders
        if args.kind == "upstream":
            assert observations["physical_samples"] == 1 and observations["sample_source"] == "OpenGL driver GL_SAMPLES"
        manifest["fixtures"][args.worker] = {"parameters": params, "observations": observations,
            "actual_renderer_provenance": actual, "artifacts": artifacts}
        print("PASS independent marker", args.worker, "fixed landmarks, trace revisions and exact whole-frame policy", flush=True)
    except Exception as error:
        manifest["errors"][args.worker] = {"type": type(error).__name__, "error": str(error)}
        traceback.print_exc()
    write_json(args.output / f"{args.worker}.capture.json", manifest)
    return int(bool(manifest["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
