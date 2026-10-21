"""Capture new clipping/depth/vertex-ID lines in the pinned OpenGL environment."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import numpy as np

from fixture_line_extensions import CASES, assert_landmarks, render
from oracle_capture import ROOT, provenance, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    if args.kind == "upstream":
        import vispy
        vispy.use(gl="gl+")
    if not args.worker and args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Each qualification attempt requires a fresh output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    origins = provenance(args.kind)
    origins.update({"extension_fixture_sha256": sha256(ROOT / "tools/fixture_line_extensions.py"),
                    "extension_capture_sha256": sha256(Path(__file__)),
                    "original_lines_manifest_sha256": sha256(ROOT / "tests/reference/lines-opengl/manifest.json")})
    manifest = {"schema": 1, "provenance": origins,
                "comparison": {"full_frame_exact": True, "fixed_landmarks_exact": True},
                "fixtures": {}, "errors": {}}
    for name in ([args.worker] if args.worker else args.fixtures or CASES):
        if not args.worker:
            captured = args.output / f"{name}.capture.json"
            assert not captured.exists()
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)),
                                    "--kind", args.kind, "--output", str(args.output), "--worker", name],
                                   capture_output=True, text=True)
            print(child.stdout, end="", flush=True)
            print(child.stderr, end="", file=sys.stderr, flush=True)
            process = {"exit_code": child.returncode}
            for stream in ("stdout", "stderr"):
                path = args.output / f"{name}.{stream}.log"
                path.write_text(getattr(child, stream), encoding="utf-8")
                process[stream] = {"file": path.name, "sha256": sha256(path)}
            data = json.loads(captured.read_text()) if captured.exists() else {"fixtures": {}, "errors": {}}
            if child.returncode == 0 and name in data["fixtures"]:
                record = data["fixtures"][name]
                record.update(process=process, capture={"file": captured.name, "sha256": sha256(captured)})
                manifest["fixtures"][name] = record
            else:
                error = data["errors"].get(name, {"error": f"capture child exited {child.returncode}"})
                if name in data["fixtures"]:
                    error["unadmitted_record"] = data["fixtures"][name]
                if captured.exists():
                    error["capture"] = {"file": captured.name, "sha256": sha256(captured)}
                error["process"] = process
                manifest["errors"][name] = error
            write_json(args.output / "manifest.json", manifest)
            continue
        artifacts = {}
        try:
            image, commands, shaders, parameters, observations = render(name, "pyqt6" if args.kind == "upstream" else "dawn_headless")
            for key, suffix, value in (("rgba", "npy", image), ("filtered_glir", "glir.json", commands),
                                        ("expanded_shaders", "shaders.json", shaders)):
                path = args.output / f"{name}.{suffix}"
                np.save(path, value, allow_pickle=False) if suffix == "npy" else write_json(path, value)
                artifacts[key] = {"file": path.name, "sha256": sha256(path)}
            assert commands and shaders
            assert_landmarks(name, image)
            assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
            if args.kind == "upstream":
                assert observations["sample_source"] == "OpenGL driver query"
            assert observations["physical_samples"] == 1
            manifest["fixtures"][name] = {"parameters": parameters, "observations": observations,
                                           "shape": list(image.shape), "artifacts": artifacts}
            print(f"PASS independent line extension {name}; actual samples={observations['samples_raw']}", flush=True)
        except Exception as error:
            for key, suffix, attribute in (("filtered_glir", "glir.json", "fixture_commands"),
                                           ("expanded_shaders", "shaders.json", "fixture_shaders")):
                if hasattr(error, attribute):
                    path = args.output / f"{name}.{suffix}"
                    write_json(path, getattr(error, attribute))
                    artifacts[key] = {"file": path.name, "sha256": sha256(path)}
            manifest["errors"][name] = {"type": type(error).__name__, "error": str(error), "unadmitted_artifacts": artifacts}
            traceback.print_exc()
    write_json(args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json"), manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
