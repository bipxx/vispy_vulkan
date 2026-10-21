"""Capture using explicit upstream Qt teardown before the next render.

This entry point extends the immutable legacy oracle_capture.py protocol.
Existing references retain that script's original source hash. New captures
record this entry point and upstream_qt_lifecycle.py instead.

Example (independent installed reference, no repository Python path):
  build/oracle-opengl/Scripts/python.exe tools/oracle_capture_qt.py \
      --kind upstream --output tests/reference/opengl
  .venv/Scripts/python.exe tools/oracle_capture_qt.py \
      --kind candidate --output build/evidence/candidate
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback
from contextlib import nullcontext

from fixture_gloo import FIXTURES, assert_expected_regions, assert_numeric_landmarks, render

ROOT = Path(__file__).resolve().parents[1]
PIN = "117b054598f4758b598f4b8f48feea48c11fe7b0"
SOURCE_FILES = ("gloo/program.py", "gloo/glir.py", "gloo/texture.py",
                "gloo/buffer.py", "gloo/context.py", "gloo/wrappers.py")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def qt_teardown_scope(kind):
    if kind != "upstream":
        return nullcontext(None)
    from upstream_qt_lifecycle import upstream_qt_teardown
    return upstream_qt_teardown()


def provenance(kind):
    import vispy
    import numpy
    from PyQt6 import QtCore
    from vispy import app, gloo

    expected = "0.17.0" if kind == "upstream" else "0.17.0+vulkan.1"
    assert metadata.version("vispy") == expected, "wrong installed distribution"
    assert vispy.__version__ == expected, "wrong imported module"
    package = Path(vispy.__file__).resolve().parent
    distribution = metadata.distribution("vispy")
    source_hashes = {name: sha256(package / name) for name in SOURCE_FILES}
    if kind == "upstream":
        assert "site-packages" in str(package), "oracle must import an installed upstream package"
        assert not (package / "_dawn.pyd").exists(), "fork found in oracle environment"
        manifest = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
        for name, actual in source_hashes.items():
            assert actual == manifest["files"][name], f"upstream pin mismatch: {name}"
    canvas = app.Canvas(app="pyqt6" if kind == "upstream" else "dawn_headless",
                        size=(2, 2), show=False)
    if kind == "upstream":
        canvas.app.native.setQuitOnLastWindowClosed(False)
    canvas.set_current()
    try:
        if kind == "upstream":
            gloo.clear(color=True, depth=False, stencil=False)
            gloo.finish()
            renderer = {name: str(gloo.gl.glGetParameter(getattr(gloo.gl, enum)))
                        for name, enum in (("vendor", "GL_VENDOR"),
                                           ("renderer", "GL_RENDERER"),
                                           ("version", "GL_VERSION"))}
            assert "Dawn" not in renderer["renderer"]
        else:
            from vispy import _dawn
            renderer = _dawn.device_info()
            assert renderer["ok"], renderer["error"]
    finally:
        canvas.close()
    try:
        compiler = subprocess.run(["cmake", "--version"], capture_output=True,
                                  text=True, check=True).stdout.splitlines()[0]
    except (FileNotFoundError, subprocess.CalledProcessError):
        compiler = None
    files = sorted(distribution.files or [])
    record = next((distribution.locate_file(p) for p in files if str(p).endswith(".dist-info/RECORD")), None)
    return {
        "kind": kind, "upstream_commit": PIN if kind == "upstream" else None,
        "python": platform.python_version(), "python_executable": sys.executable,
        "platform": platform.platform(), "machine": platform.machine(),
        "vispy_origin": str(package), "vispy_version": vispy.__version__,
        "distribution_origin": str(distribution.locate_file("")),
        "distribution_record_sha256": sha256(record) if record else None,
        "source_sha256": source_hashes,
        "versions": {name: metadata.version(name) for name in
                     ("vispy", "numpy", "PyQt6", "PyQt6-Qt6", "PyQt6-sip",
                      "freetype-py", "hsluv", "kiwisolver", "packaging", "PyOpenGL")},
        "qt_runtime": QtCore.qVersion(), "numpy_origin": numpy.__file__,
        "renderer": renderer, "cmake": compiler,
        "fixture_source_sha256": sha256(ROOT / "tools/fixture_gloo.py"),
        "capture_source_sha256": sha256(Path(__file__)),
        "requirements_sha256": sha256(ROOT / "tools/oracle_requirements.txt"),
        "environment": {key: os.environ.get(key) for key in
                        ("QT_API", "QT_QPA_PLATFORM", "QT_SCALE_FACTOR", "PYTHONPATH",
                         "VISPY_PYQT5_SHARE_CONTEXT")},
        "regenerate": "uv venv build/oracle-opengl --python 3.12; "
                      "uv pip install --python build/oracle-opengl/Scripts/python.exe "
                      "-r tools/oracle_requirements.txt; "
                      "build/oracle-opengl/Scripts/python.exe tools/oracle_capture_qt.py "
                      "--kind upstream --output tests/reference/opengl",
    }


def main():
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=tuple(FIXTURES))
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--worker", choices=tuple(FIXTURES), help=argparse.SUPPRESS)
    options = parser.parse_args()
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        raise RuntimeError("Qt offscreen is not an OpenGL qualification environment")
    if options.kind == "upstream":
        import vispy
        vispy.use(gl="gl+")
    options.output.mkdir(parents=True, exist_ok=True)
    with qt_teardown_scope(options.kind) as provenance_teardown:
        capture_provenance = provenance(options.kind)
    manifest = {"schema": 1, "provenance": capture_provenance,
                "comparison": {"interior_max_abs_u8": 2,
                               "edge_max_differing_fraction": 0.001,
                               "categorical_exact": True,
                               "mask": "tools.fixture_gloo.comparison_masks"},
                "fixtures": {}, "errors": {}}
    if provenance_teardown is not None:
        manifest["upstream_qt_teardown"] = {"provenance": provenance_teardown,
            "helper_sha256": sha256(ROOT / "tools/upstream_qt_lifecycle.py")}
    for name in ([options.worker] if options.worker else options.fixtures or FIXTURES):
        if not options.worker:
            child_file = options.output / f"{name}.capture.json"
            child_file.unlink(missing_ok=True)
            result = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)),
                                     "--kind", options.kind, "--output", str(options.output),
                                     "--worker", name], capture_output=True, text=True)
            print(result.stdout, end="", flush=True)
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr, flush=True)
            if not child_file.exists():
                manifest["errors"][name] = {"error": f"capture process failed with {result.returncode}"}
            else:
                child = json.loads(child_file.read_text())
                if result.returncode == 0:
                    manifest["fixtures"].update(child["fixtures"])
                manifest["errors"].update(child["errors"])
                if name in manifest["fixtures"]:
                    manifest["fixtures"][name]["capture"] = {"file": child_file.name,
                                                              "sha256": sha256(child_file)}
            if result.returncode and name not in manifest["errors"]:
                manifest["errors"][name] = {"error": f"capture process failed with {result.returncode}"}
            write_json(options.output / "manifest.json", manifest)
            if result.returncode and not options.keep_going:
                return True
            continue
        try:
            with qt_teardown_scope(options.kind) as fixture_teardown:
                image, commands, shaders, reads = render(name, "pyqt6" if options.kind == "upstream" else "dawn_headless")
            assert reads == (2 if name == "shared_canvases" else 1)
            assert_numeric_landmarks(name, image)
            assert_expected_regions(name, image)
            image_file = options.output / f"{name}.npy"
            trace_file = options.output / f"{name}.glir.json"
            shader_file = options.output / f"{name}.shaders.json"
            np.save(image_file, image, allow_pickle=False)
            write_json(trace_file, commands)
            write_json(shader_file, shaders)
            assert commands, "filtered GLIR is required"
            if name != "clear_only_fbo":
                assert shaders, "expanded shaders are required for draw fixtures"
            fixture = FIXTURES[name]
            manifest["fixtures"][name] = {
                "operation": fixture.operation, "size": list(fixture.size),
                "shape": list(image.shape), "dtype": image.dtype.str,
                "readbacks": reads, "exact": fixture.exact,
                "requested_samples": 4 if name == "msaa4" else 0,
                "capture_method": "qt_owned_msaa_resolve" if name == "msaa4" and options.kind == "upstream" else "gloo.read_pixels",
                "edge_columns": list(fixture.edge_columns), "edge_rows": list(fixture.edge_rows),
                "rgba": {"file": image_file.name, "sha256": sha256(image_file)},
                "filtered_glir": {"file": trace_file.name, "sha256": sha256(trace_file)},
                "expanded_shaders": {"file": shader_file.name, "sha256": sha256(shader_file)},
            }
            if fixture_teardown is not None:
                manifest["fixtures"][name]["upstream_qt_teardown"] = fixture_teardown
            print(f"PASS {name}: {image.shape}, {reads} final readback(s)", flush=True)
        except Exception as exc:
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc)}
            traceback.print_exc()
            if not options.keep_going:
                write_json(options.output / (f"{name}.capture.json" if options.worker else "manifest.json"), manifest)
                raise
    write_json(options.output / (f"{options.worker}.capture.json" if options.worker else "manifest.json"), manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
