"""Observe unchanged DIVE export, raw framebuffer and Qt image semantics.

This diagnostic neither changes a host fixture nor qualifies pixel parity.
Each environment runs in its own child, using the existing scoped public
style-restoration guard for the pinned DIVE cleanup behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCOPE = "Read-only DIVE framebuffer/QImage diagnostic; not reference admission or candidate qualification"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def worker(kind, output):
    import numpy as np
    from tools.fixture_dive_pyside2 import render, qimage_rgba
    from tools.oracle_dive_pyside2_style_capture import install_style_restoration
    import vispy
    from vispy import app, gloo

    vispy.use(app="pyside2", **({"gl": "gl+"} if kind == "upstream" else {}))
    application = app.use_app("PySide2")
    qt = application.native
    qt.setQuitOnLastWindowClosed(False)
    guard, restoration = install_style_restoration(qt)
    backend = application.backend_module.CanvasBackend
    original = backend.grabFramebuffer
    observations = []

    def observe(native):
        # The original backend owns redraw/readback semantics. Extra readback
        # happens afterwards and does not replace the image returned to DIVE.
        image = original(native)
        native._vispy_canvas.set_current()
        raw = gloo.read_pixels(alpha=True)
        returned = qimage_rgba(image)
        index = len(observations)
        np.save(output / f"frame-{index}.raw.npy", raw, allow_pickle=False)
        np.save(output / f"frame-{index}.qimage.npy", returned, allow_pickle=False)
        record = {
            "canvas_config": dict(native._vispy_canvas.context.config),
            "qimage_format": int(image.format()),
            "qimage_has_alpha": bool(image.hasAlphaChannel()),
            "qimage_dpr": float(image.devicePixelRatio()),
            "raw_shape": list(raw.shape),
            "raw_alpha_unique": np.unique(raw[..., 3]).tolist(),
            "qimage_alpha_unique": np.unique(returned[..., 3]).tolist(),
            "raw_qimage_differing_pixels": int(np.any(raw != returned, axis=2).sum()),
            "raw_qimage_max_channel_difference": np.abs(raw.astype(np.int16) - returned.astype(np.int16)).max(axis=(0, 1)).tolist(),
        }
        if hasattr(native, "format"):
            fmt = native.format()
            record["actual_qt_format"] = {
                "alpha_buffer_size": fmt.alphaBufferSize(),
                "has_alpha": bool(fmt.hasAlpha()),
                "samples": fmt.samples(),
                "version": list(fmt.version()),
            }
        observations.append(record)
        return image

    backend.grabFramebuffer = observe
    try:
        image, commands, shaders, parameters, extras = render("image")
        np.save(output / "export.npy", image, allow_pickle=False)
        (output / "export.png").write_bytes(extras["png"])
        write_json(output / "filtered-glir.json", commands)
        write_json(output / "shaders.json", shaders)
        write_json(output / "parameters.json", parameters)
    finally:
        backend.grabFramebuffer = original
        write_json(output / "style-restoration.json", restoration)
    assert observations, "The unchanged public DIVE export did not call grabFramebuffer"
    assert len(restoration["actions"]) == 1, restoration
    provenance = {
        "kind": kind,
        "python_executable": sys.executable,
        "vispy_origin": vispy.__file__,
        "vispy_version": vispy.__version__,
        "fixture_sha256": digest(ROOT / "tools/fixture_dive_pyside2.py"),
        "diagnostic_sha256": digest(__file__),
    }
    if kind == "candidate":
        from vispy import _dawn
        provenance.update(native_origin=_dawn.__file__, native_sha256=digest(_dawn.__file__),
                          device_info=_dawn.device_info())
    write_json(output / "diagnostic.json", {
        "scope": SCOPE, "provenance": provenance, "observations": observations,
        "status": "observed; not a qualification pass",
    })
    print(json.dumps({"kind": kind, "observations": observations}))
    # Keep the QObject guard alive until all fixture DeferredDelete work ended.
    assert guard is not None
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=("upstream", "candidate"))
    args = parser.parse_args()
    os.environ.setdefault("QT_API", "pyside2")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYSIDE2_SHARE_CONTEXT", "true")
    if args.worker:
        args.output.mkdir(parents=True, exist_ok=False)
        return worker(args.worker, args.output)
    args.output.mkdir(parents=True, exist_ok=False)
    interpreters = {
        "upstream": ROOT / "build/host-environments/dive-pyside2-cpython310-upstream/Scripts/python.exe",
        "candidate": ROOT / "build/host-environments/dive-pyside2-cpython310-candidate-w8b/Scripts/python.exe",
    }
    results = {}
    for kind, interpreter in interpreters.items():
        command = [str(interpreter), "-X", "faulthandler", str(Path(__file__).resolve()),
                   "--output", str(args.output / kind), "--worker", kind]
        try:
            child = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
            stdout, stderr = child.stdout, child.stderr
            result = {"exit_code": child.returncode, "command": command}
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b"", error.stderr or b""
            result = {"exit_code": None, "error": "diagnostic child timeout", "command": command}
        (args.output / f"{kind}.stdout.log").write_bytes(stdout)
        (args.output / f"{kind}.stderr.log").write_bytes(stderr)
        results[kind] = result
        print(json.dumps({"kind": kind, **result}), flush=True)
    write_json(args.output / "manifest.json", {"scope": SCOPE, "children": results})
    return int(any(result["exit_code"] != 0 for result in results.values()))


if __name__ == "__main__":
    # Absolute execution from an external installed environment must not add
    # root/src to sys.path, so VisPy still resolves from that environment.
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
