"""Actual shown Qt attribution diagnostic, without a performance claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.benchmark_frames import PythonFrameTelemetry
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import vispy
    from vispy import scene, gloo
    assert vispy.__version__ == ("0.17.0" if args.kind == "upstream" else "0.17.0+vulkan.1")
    if args.kind == "upstream":
        package = Path(vispy.__file__).resolve().parent
        pins = json.loads((ROOT / "compat/upstream_manifest.json").read_text())["files"]
        for relative in ("gloo/glir.py", "app/backends/_qt.py", "scene/canvas.py"):
            assert hashlib.sha256((package / relative).read_bytes()).hexdigest() == pins[relative], relative
        assert "site-packages" in str(package) and not list(package.glob("_dawn*"))
    canvas = scene.SceneCanvas(app="pyqt6", size=(32, 24), show=True, vsync=False)
    telemetry = None
    result = {"kind": args.kind, "package": vispy.__file__, "version": vispy.__version__,
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "collector_sha256": hashlib.sha256((ROOT / "tools/benchmark_frames.py").read_bytes()).hexdigest(),
              "scope": "12 real shown paints: Python post-swap parser ownership only; no GPU-span, throughput, visible-latency or release claim"}
    try:
        view = canvas.central_widget.add_view()
        image = scene.visuals.Image(np.ones((2, 3), np.float32), cmap="grays", clim=(0, 1), interpolation="nearest", parent=view.scene)
        view.camera = scene.PanZoomCamera(aspect=None)
        view.camera.set_range(x=(0, 3), y=(0, 2), margin=0)
        canvas.app.process_events()
        if args.kind == "candidate":
            from vispy import _dawn
            from vispy.gloo import dawn_parser
            canvas_id = canvas._backend._dawn_canvas_id
            _dawn.finish(canvas_id)
            result["device"] = _dawn.device_info()
            assert result["device"]["ok"] and not result["device"]["software"]
            telemetry = PythonFrameTelemetry(canvas, pack_module=dawn_parser)
        else:
            canvas.set_current()
            result["device"] = {name: str(gloo.gl.glGetParameter(getattr(gloo.gl, "GL_" + name))) for name in ("VENDOR", "RENDERER", "VERSION")}
            telemetry = PythonFrameTelemetry(canvas)
        result["paint_methods"] = telemetry.paint_methods
        for frame_id in range(12):
            deadline = time.monotonic() + 8
            if args.kind == "candidate":
                while not _dawn.frame_ready(canvas_id):
                    canvas.app.process_events()
                    assert time.monotonic() < deadline, "frame ring not ready"
            telemetry.begin(frame_id)
            telemetry.update(lambda value: setattr(image, "opacity", (value + 1) / 12), frame_id)
            canvas.update()
            while telemetry.current is not None:
                canvas.app.process_events()
                assert time.monotonic() < deadline, "owning paint did not end"
        result["frames"] = telemetry.frames
        result["totals"] = telemetry.snapshot()
        assert telemetry.paint_methods
        for frame in telemetry.frames.values():
            assert frame["python_draw_calls"] == frame["python_update_calls"] == frame["python_paint_calls"] == 1
            assert frame["python_paint_tail_glir_parse_calls"] >= 1 and frame["python_paint_tail_glir_parse_ns"] > 0
        assert result["totals"]["unattributed_glir_parse_calls"] == 0
        result["status"] = "passed"
    except BaseException as error:
        result["status"] = "failed"
        result["error"] = repr(error)
        raise
    finally:
        if telemetry is not None:
            result["frames"] = telemetry.frames
            result["totals"] = telemetry.snapshot()
            telemetry.close()
        canvas.close()
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"kind": args.kind, "status": result["status"], "frames": len(result["frames"])}))

if __name__ == "__main__":
    main()
