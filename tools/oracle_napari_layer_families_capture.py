# SPDX-License-Identifier: AGPL-3.0-only
"""Independent installed napari/OpenGL reference capture of the W4 layer-family fixtures, one isolated process per case.

Run with the upstream oracle environment (napari 0.9.2, upstream vispy 0.17.0, PyQt6):
    build/oracle-napari/Scripts/python.exe tools/oracle_napari_layer_families_capture.py --kind upstream \
        --output tests/reference/napari-layer-families-opengl
"""
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_napari_layer_families import CASES, CRITERIA, assert_landmarks, render
from oracle_capture import ROOT, provenance, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    if args.kind == "upstream":
        import vispy
        vispy.use(gl="gl+")
    origins = provenance(args.kind)
    import napari
    assert napari.__version__ == "0.9.2"
    origins.update({"napari_origin": napari.__file__, "napari_version": napari.__version__,
                    "fixture_source_sha256": sha256(ROOT / "tools/fixture_napari_layer_families.py"),
                    "capture_source_sha256": sha256(Path(__file__)),
                    "installed": {dist.metadata["Name"]: dist.version for dist in metadata.distributions()}})
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": origins, "comparison": {"criteria": CRITERIA,
                "smooth_line": "tools.smooth_line_parity.smooth_line_difference"}, "fixtures": {}, "errors": {}}
    for name in ([args.worker] if args.worker else CASES):
        if not args.worker:
            captured = args.output / f"{name}.capture.json"
            assert not captured.exists(), "fresh output required"
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)), "--kind", args.kind,
                                    "--output", str(args.output), "--worker", name], capture_output=True, text=True)
            (args.output / f"{name}.stdout.log").write_text(child.stdout, encoding="utf-8")
            (args.output / f"{name}.stderr.log").write_text(child.stderr, encoding="utf-8")
            if captured.exists():
                data = json.loads(captured.read_text())
                if child.returncode == 0:
                    manifest["fixtures"].update(data["fixtures"])
                manifest["errors"].update(data["errors"])
                if name in manifest["fixtures"]:
                    manifest["fixtures"][name]["capture"] = {"file": captured.name, "sha256": sha256(captured)}
                    manifest["fixtures"][name]["process"] = {"exit_code": child.returncode}
            if child.returncode and name not in manifest["errors"]:
                manifest["errors"][name] = {"error": f"capture subprocess exited {child.returncode}"}
            print(name, "exit", child.returncode, flush=True)
            continue
        try:
            image, commands, shaders, params = render(name)
            assert_landmarks(name, image)
            assert commands and shaders
            arrays, trace, source = (args.output / f"{name}{suffix}" for suffix in (".npy", ".glir.json", ".shaders.json"))
            np.save(arrays, image, allow_pickle=False)
            write_json(trace, commands)
            write_json(source, shaders)
            manifest["fixtures"][name] = {"parameters": params, "shape": list(image.shape), "criterion": CRITERIA[name],
                                          "rgba": {"file": arrays.name, "sha256": sha256(arrays)},
                                          "filtered_glir": {"file": trace.name, "sha256": sha256(trace)},
                                          "expanded_shaders": {"file": source.name, "sha256": sha256(source)}}
        except Exception as exc:
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc)}
            traceback.print_exc()
    write_json(args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json"), manifest)
    return 1 if manifest["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
