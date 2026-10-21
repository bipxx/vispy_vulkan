"""Isolated fixed point identity captures from installed VisPy/GL4.6 or Dawn."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import numpy as np

from fixture_point_identity import CASES, assert_expected, assert_trace, render
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
        # Public context request; the fixture separately verifies the driver.
        from PyQt6.QtGui import QSurfaceFormat
        surface = QSurfaceFormat()
        surface.setVersion(4, 6)
        surface.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(surface)
        import vispy
        vispy.use(gl="gl+")
    if not args.worker and args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Each qualification attempt requires a fresh output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    origins = provenance(args.kind)
    origins.update(point_fixture_sha256=sha256(ROOT / "tools/fixture_point_identity.py"),
                   point_capture_sha256=sha256(Path(__file__)),
                   requested_upstream_context="OpenGL4.6 compatibility via public QSurfaceFormat; gl+ backend",
                   authoring="full analytic pixel arrays, data, shaders and selection fixed before candidate results")
    manifest = {"schema": 1, "provenance": origins,
                "comparison": {"full_frame_exact": True, "analytic_pixels_exact": True},
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
            image, commands, shaders, params, observations = render(name, "pyqt6" if args.kind == "upstream" else "dawn_headless")
            for key, suffix, value in (("rgba", "npy", image), ("filtered_glir", "glir.json", commands),
                                        ("expanded_shaders", "shaders.json", shaders)):
                path = args.output / f"{name}.{suffix}"
                np.save(path, value, allow_pickle=False) if suffix == "npy" else write_json(path, value)
                artifacts[key] = {"file": path.name, "sha256": sha256(path)}
            assert commands and shaders
            assert_expected(name, image)
            assert_trace(name, commands)
            if args.kind == "upstream":
                assert observations["sample_source"] == "OpenGL driver"
                assert observations["gl_version"].startswith("4.6")
                assert not observations["point_smooth"] and observations["program_point_size_after_draw"]
            manifest["fixtures"][name] = {"parameters": params, "observations": observations,
                                           "shape": list(image.shape), "artifacts": artifacts}
            print(f"PASS independent point {name}; {params['api_scope']}", flush=True)
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
