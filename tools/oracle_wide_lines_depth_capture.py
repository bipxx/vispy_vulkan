"""Independent pinned OpenGL three-pixel/smooth-line capture in fresh children."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_wide_lines_depth import CASES, assert_landmarks, render
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
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    if not args.worker and args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("each admission attempt requires a fresh directory")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": None,
                "comparison": {"full_frame_exact": True, "fixed_landmarks_exact": True},
                "fixtures": {}, "errors": {}}
    if not args.worker:
        for name in args.fixtures or CASES:
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
            captured = args.output / f"{name}.capture.json"
            data = json.loads(captured.read_text()) if captured.exists() else {"fixtures": {}, "errors": {}}
            if manifest["provenance"] is None:
                manifest["provenance"] = data.get("provenance")
            if child.returncode == 0 and name in data["fixtures"]:
                record = data["fixtures"][name]
                record.update(process=process, capture={"file": captured.name, "sha256": sha256(captured)})
                manifest["fixtures"][name] = record
            else:
                error = data["errors"].get(name, {"error": f"capture child exited {child.returncode}"})
                error["process"] = process
                if name in data["fixtures"]:
                    error["unadmitted_record"] = data["fixtures"][name]
                if captured.exists():
                    error["capture"] = {"file": captured.name, "sha256": sha256(captured)}
                manifest["errors"][name] = error
            write_json(args.output / "manifest.json", manifest)
        return bool(manifest["errors"])

    artifacts = {}
    try:
        if args.kind == "upstream":
            import vispy
            vispy.use(gl="gl+")
        origins = provenance(args.kind)
        origins.update({"wide_fixture_sha256": sha256(ROOT / "tools/fixture_wide_lines_depth.py"),
                        "shared_fixed_fixture_sha256": sha256(ROOT / "tools/fixture_wide_lines.py"),
                        "initial_depth_policy": "explicit public clear_depth1/depth-only clear before unchanged fixed draws",
                        "wide_capture_sha256": sha256(Path(__file__)),
                        "regenerate": "build/oracle-opengl/Scripts/python.exe tools/oracle_wide_lines_depth_capture.py --kind upstream --output <fresh-output>"})
        manifest["provenance"] = origins
        image, commands, shaders, params, observations = render(args.worker, "pyqt6" if args.kind == "upstream" else "dawn_headless")
        for key, value, suffix in (("rgba", image, "npy"), ("filtered_glir", commands, "glir.json"),
                                   ("expanded_shaders", shaders, "shaders.json"), ("observations", observations, "observations.json")):
            path = args.output / f"{args.worker}.{suffix}"
            if suffix == "npy":
                np.save(path, value, allow_pickle=False)
            else:
                write_json(path, value)
            artifacts[key] = {"file": path.name, "sha256": sha256(path)}
        assert commands and shaders
        assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
        assert_landmarks(args.worker, image)
        manifest["fixtures"][args.worker] = {"parameters": params, "observations": observations,
                                             "shape": list(image.shape), "dtype": image.dtype.str, **artifacts}
        print(f"PASS wide/smooth line {args.worker}: {image.shape}, samples {observations['physical_samples']}", flush=True)
    except Exception as error:
        for key, suffix, attr in (("filtered_glir", "glir.json", "fixture_commands"),
                                 ("expanded_shaders", "shaders.json", "fixture_shaders"),
                                 ("parameters", "parameters.json", "fixture_parameters")):
            if hasattr(error, attr):
                path = args.output / f"{args.worker}.{suffix}"
                write_json(path, getattr(error, attr))
                artifacts[key] = {"file": path.name, "sha256": sha256(path)}
        manifest["errors"][args.worker] = {"type": type(error).__name__, "error": str(error), "unadmitted_artifacts": artifacts}
        traceback.print_exc()
    write_json(args.output / f"{args.worker}.capture.json", manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
