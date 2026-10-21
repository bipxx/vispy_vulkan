"""Capture installed napari categorical volume references in isolated processes."""

import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_napari_volume import CASES, assert_landmarks, render
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
    import napari
    assert napari.__version__ == "0.9.2"
    package = Path(napari.__file__).resolve().parent
    origins.update({"napari_origin": napari.__file__, "napari_version": napari.__version__,
        "host_requirements_sha256": sha256(ROOT / "tools/oracle_napari_requirements.txt"),
        "volume_fixture_sha256": sha256(ROOT / "tools/fixture_napari_volume.py"),
        "volume_capture_sha256": sha256(Path(__file__)),
        "host_source_sha256": {name: sha256(package / name) for name in
            ("_vispy/visuals/volume.py", "_vispy/layers/labels.py", "_vispy/camera.py")},
        "installed": {dist.metadata["Name"]: dist.version for dist in metadata.distributions()},
        "regenerate": "build/oracle-napari/Scripts/python.exe tools/oracle_napari_volume_capture.py "
            "--kind upstream --output tests/reference/napari-volume-opengl"})
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": origins,
        "comparison": {"categorical_exact": True, "landmark_exact": True},
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
            image, commands, shaders, params = render(name)
            assert_landmarks(name, image)
            assert commands and shaders
            arrays = args.output / f"{name}.npy"
            trace = args.output / f"{name}.glir.json"
            source = args.output / f"{name}.shaders.json"
            np.save(arrays, image, allow_pickle=False)
            write_json(trace, commands)
            write_json(source, shaders)
            manifest["fixtures"][name] = {"parameters": params, "shape": list(image.shape),
                "rgba": {"file": arrays.name, "sha256": sha256(arrays)},
                "filtered_glir": {"file": trace.name, "sha256": sha256(trace)},
                "expanded_shaders": {"file": source.name, "sha256": sha256(source)}}
            print(f"PASS napari volume {name}: {image.shape}, independent {args.kind}", flush=True)
        except Exception as exc:
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc)}
            traceback.print_exc()
    output = args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json")
    write_json(output, manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
