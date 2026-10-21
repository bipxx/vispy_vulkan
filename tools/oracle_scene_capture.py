"""Capture scientific scene images and CPU text atlases using installed upstream."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_scene import CASES, EXACT, assert_landmarks, render
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
    import vispy
    if args.kind == "upstream":
        vispy.use(gl="gl+")
    origins = provenance(args.kind)
    package = Path(vispy.__file__).resolve().parent
    pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
    origins["scene_source_sha256"] = {}
    for name in ("visuals/line/line.py", "visuals/mesh.py", "visuals/markers.py",
                 "visuals/text/text.py", "util/fonts/data/OpenSans-Regular.ttf"):
        actual = sha256(package / name)
        if args.kind == "upstream":
            assert actual == pinned["files"][name], name
        origins["scene_source_sha256"][name] = actual
    origins.update({"scene_fixture_sha256": sha256(ROOT / "tools/fixture_scene.py"),
        "scene_capture_sha256": sha256(Path(__file__)),
        "regenerate": "build/oracle-opengl/Scripts/python.exe tools/oracle_scene_capture.py "
            "--kind upstream --output tests/reference/scene-opengl"})
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": origins,
        "comparison": {"interior_max_abs_u8": 2, "edge_max_differing_fraction": .001,
                       "atlas_exact": True, "mask": "tools.fixture_scene.masks"},
        "fixtures": {}, "errors": {}}
    for name in ([args.worker] if args.worker else args.fixtures or CASES):
        if not args.worker:
            captured = args.output / f"{name}.capture.json"
            captured.unlink(missing_ok=True)
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)),
                "--kind", args.kind, "--output", str(args.output), "--worker", name],
                capture_output=True, text=True)
            print(child.stdout, end="", flush=True)
            print(child.stderr, end="", file=sys.stderr, flush=True)
            if captured.exists():
                data = json.loads(captured.read_text())
                if child.returncode == 0:
                    manifest["fixtures"].update(data["fixtures"])
                manifest["errors"].update(data["errors"])
                if name in manifest["fixtures"]:
                    manifest["fixtures"][name]["capture"] = {"file": captured.name, "sha256": sha256(captured)}
            else:
                manifest["errors"][name] = {"error": f"capture subprocess exited {child.returncode}"}
            if child.returncode and name not in manifest["errors"]:
                manifest["errors"][name] = {"error": f"capture subprocess exited {child.returncode}"}
            write_json(args.output / "manifest.json", manifest)
            continue
        try:
            image, commands, shaders, params, extras = render(name, "pyqt6" if args.kind == "upstream" else "dawn_headless")
            assert_landmarks(name, image, extras)
            assert commands and shaders
            arrays = args.output / f"{name}.npy"
            trace = args.output / f"{name}.glir.json"
            source = args.output / f"{name}.shaders.json"
            np.save(arrays, image, allow_pickle=False)
            write_json(trace, commands)
            write_json(source, shaders)
            record = {"parameters": params, "shape": list(image.shape), "exact": name in EXACT,
                "rgba": {"file": arrays.name, "sha256": sha256(arrays)},
                "filtered_glir": {"file": trace.name, "sha256": sha256(trace)},
                "expanded_shaders": {"file": source.name, "sha256": sha256(source)}}
            for key, array in extras.items():
                path = args.output / f"{name}.{key}.npy"
                np.save(path, array, allow_pickle=False)
                record[key] = {"file": path.name, "sha256": sha256(path)}
            manifest["fixtures"][name] = record
            print(f"PASS scene {name}: {image.shape}, independent {args.kind}", flush=True)
        except Exception as exc:
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc)}
            traceback.print_exc()
    output = args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json")
    write_json(output, manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
