"""Independent real glue Qt viewers; failed upstream cases remain unresolved."""

import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_glue import CASES, assert_landmarks, render
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
    vispy.use(app="pyqt6", **({"gl": "gl+"} if args.kind == "upstream" else {}))
    origins = provenance(args.kind)
    import glue_vispy_viewers
    import glue
    import glue_qt
    assert glue_vispy_viewers.__version__ == "1.4.0"
    package = Path(glue_vispy_viewers.__file__).resolve().parent
    admission_path = ROOT / "tools/oracle_glue_admission.json"
    admission = json.loads(admission_path.read_text())
    host_sources = {}
    for name, expected in admission["source_files"].items():
        actual = sha256(package / name)
        assert actual == expected["sha256"], (name, "unmodified pinned host source required")
        host_sources[name] = actual
    origins.update({"glue_vispy_viewers_origin": glue_vispy_viewers.__file__,
        "glue_core_origin": glue.__file__, "glue_qt_origin": glue_qt.__file__,
        "glue_vispy_viewers_version": glue_vispy_viewers.__version__,
        "host_commit": admission["commit"], "host_source_sha256": host_sources,
        "host_requirements_sha256": sha256(ROOT / "tools/oracle_glue_requirements.txt"),
        "host_fixture_sha256": sha256(ROOT / "tools/fixture_glue.py"),
        "host_capture_sha256": sha256(Path(__file__)),
        "historical_windows_test_skip": admission["historical_windows_test_skip"],
        "installed": {dist.metadata["Name"]: dist.version for dist in metadata.distributions()},
        "regenerate": "uv venv build/oracle-glue --python 3.12; "
            "uv pip install --python build/oracle-glue/Scripts/python.exe --require-hashes "
            "-r tools/oracle_glue_requirements.txt; build/oracle-glue/Scripts/python.exe "
            "tools/oracle_glue_capture.py --kind upstream --output tests/reference/glue-opengl"})
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": origins,
        "comparison": {"interior_max_abs_u8": 2, "edge_max_differing_fraction": .001,
                       "categorical_landmarks_exact": True, "full_frame_exact": True},
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
            arrays = args.output / f"{name}.npy"
            trace = args.output / f"{name}.glir.json"
            source = args.output / f"{name}.shaders.json"
            np.save(arrays, image, allow_pickle=False)
            write_json(trace, commands)
            write_json(source, shaders)
            assert_landmarks(name, image)
            assert commands and shaders
            manifest["fixtures"][name] = {"parameters": params, "shape": list(image.shape),
                "rgba": {"file": arrays.name, "sha256": sha256(arrays)},
                "filtered_glir": {"file": trace.name, "sha256": sha256(trace)},
                "expanded_shaders": {"file": source.name, "sha256": sha256(source)}}
            print(f"PASS glue {name}: {image.shape}, independent {args.kind}", flush=True)
        except Exception as exc:
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc)}
            failures = {}
            for suffix in ("npy", "glir.json", "shaders.json"):
                path = args.output / f"{name}.{suffix}"
                if path.exists():
                    failures[suffix] = {"file": path.name, "sha256": sha256(path)}
            if failures:
                manifest["errors"][name]["unadmitted_artifacts"] = failures
            traceback.print_exc()
    output = args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json")
    write_json(output, manifest)
    if not args.worker and args.kind == "upstream":
        admission["requirements_sha256"] = origins["host_requirements_sha256"]
        admission["upstream_qualification"] = "passed" if not manifest["errors"] else "unresolved"
        admission["successful_fixtures"] = list(manifest["fixtures"])
        admission["unresolved_fixtures"] = manifest["errors"]
        admission["reference_manifest"] = str(output.relative_to(ROOT)) if output.is_absolute() else str(output)
        write_json(admission_path, admission)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
