"""GL-spec stencil oracle via external PyOpenGL read and unchanged public gloo."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_stencil_capture import CASES, assert_expected, render
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
    if args.kind == "upstream":
        import vispy
        vispy.use(gl="gl+")
    origins = provenance(args.kind)
    origins.update({
        "stencil_fixture_sha256": sha256(ROOT / "tools/fixture_stencil_capture.py"),
        "stencil_capture_sha256": sha256(Path(__file__)),
        "analytic_setup_source_sha256": sha256(ROOT / "tools/fixture_depth_capture.py"),
        "oracle_scope": "GL stencil semantics; not upstream VisPy wrapper admission",
        "regenerate": "build/oracle-opengl/Scripts/python.exe tools/oracle_stencil_capture.py "
                      "--kind upstream --output tests/reference/stencil-capture-opengl",
    })
    if args.kind == "upstream":
        import OpenGL
        package = Path(OpenGL.__file__).resolve().parent
        origins["external_readback"] = {"api": "OpenGL.GL.glReadPixels(GL_STENCIL_INDEX)",
            "origin": str(package), "version": origins["versions"]["PyOpenGL"],
            "source_sha256": {name: sha256(package / name) for name in
                               ("GL/images.py", "raw/GL/VERSION/GL_1_0.py")},
            "unchanged_upstream_wrapper": "gloo.read_pixels(mode='stencil') raises KeyError GL_STENCIL_INDEX8",
            "wrapper_failure_manifest": "tests/reference/depth-capture-opengl/manifest.json",
            "wrapper_failure_manifest_sha256": sha256(ROOT / "tests/reference/depth-capture-opengl/manifest.json")}
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": origins,
                "comparison": {"values_exact": True, "dtype_exact": True, "analytic_expected_exact": True},
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
            process = {"exit_code": child.returncode}
            for stream in ("stdout", "stderr"):
                path = args.output / f"{name}.{stream}.log"
                path.write_text(getattr(child, stream), encoding="utf-8")
                process[stream] = {"file": path.name, "sha256": sha256(path)}
            if captured.exists():
                data = json.loads(captured.read_text())
                if child.returncode == 0:
                    manifest["fixtures"].update(data["fixtures"])
                manifest["errors"].update(data["errors"])
                if name in manifest["fixtures"]:
                    manifest["fixtures"][name]["capture"] = {
                        "file": captured.name, "sha256": sha256(captured)}
                    manifest["fixtures"][name]["process"] = process
            else:
                manifest["errors"][name] = {"error": f"capture subprocess exited {child.returncode}"}
            if child.returncode and name not in manifest["errors"]:
                manifest["errors"][name] = {"error": f"capture subprocess exited {child.returncode}"}
            if name in manifest["errors"]:
                manifest["errors"][name]["process"] = process
            write_json(args.output / "manifest.json", manifest)
            continue
        artifacts = {}
        try:
            image, commands, shaders, parameters = render(
                name, "pyqt6" if args.kind == "upstream" else "dawn_headless")
            arrays = args.output / f"{name}.npy"
            trace = args.output / f"{name}.glir.json"
            source = args.output / f"{name}.shaders.json"
            np.save(arrays, image, allow_pickle=False)
            write_json(trace, commands)
            write_json(source, shaders)
            artifacts = {"rgba": {"file": arrays.name, "sha256": sha256(arrays)},
                "filtered_glir": {"file": trace.name, "sha256": sha256(trace)},
                "expanded_shaders": {"file": source.name, "sha256": sha256(source)}}
            assert commands and shaders
            assert_expected(name, image)
            assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == parameters["readbacks"]
            manifest["fixtures"][name] = {
                "parameters": parameters, "readbacks": parameters["readbacks"],
                "shape": list(image.shape), "dtype": image.dtype.str, **artifacts}
            print(f"PASS GL-spec stencil capture {name}: {image.shape}, {image.dtype}, "
                  f"{parameters['readbacks']} readbacks", flush=True)
        except Exception as exc:
            for key, suffix, attribute in (("filtered_glir", "glir.json", "fixture_commands"),
                                           ("expanded_shaders", "shaders.json", "fixture_shaders"),
                                           ("parameters", "parameters.json", "fixture_parameters")):
                if hasattr(exc, attribute):
                    path = args.output / f"{name}.{suffix}"
                    write_json(path, getattr(exc, attribute))
                    artifacts[key] = {"file": path.name, "sha256": sha256(path)}
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc),
                                        "unadmitted_artifacts": artifacts}
            traceback.print_exc()
    output = args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json")
    write_json(output, manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
