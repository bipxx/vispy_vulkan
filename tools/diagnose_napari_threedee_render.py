"""Retain failed unchanged plugin fixture locals; never admit its pixels."""

import argparse
import json
from pathlib import Path
import traceback

import numpy as np

from fixture_napari_threedee_initialized import render
from oracle_napari_threedee_initialized_capture import ROOT, plugin_provenance, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "diagnosis must preserve earlier attempts"
    args.output.mkdir(parents=True)
    import os
    assert os.environ.get("PYTHONHASHSEED") == "0"
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    import vispy
    vispy.use(gl="gl+")
    from vispy import app
    from oracle_capture import provenance
    record = {"admitted": False, "kind": "failed unchanged upstream fixture diagnostic",
              "fixture_sha256": sha256(ROOT / "tools/fixture_napari_threedee_initialized.py"),
              "tool_sha256": sha256(Path(__file__)), "plugin": plugin_provenance(),
              "provenance": provenance("upstream"), "artifacts": {}}
    qt = app.use_app("pyqt6").native
    qt.setQuitOnLastWindowClosed(False)
    try:
        render("handles")
    except Exception as error:
        record["type"] = type(error).__name__
        record["error"] = str(error)
        record["traceback"] = traceback.format_exc()
        frame = error.__traceback__
        while frame is not None:
            current = frame.tb_frame
            if current.f_code.co_name == "render" and current.f_code.co_filename.endswith("fixture_napari_threedee_initialized.py"):
                for key in ("image", "params", "commands", "shaders"):
                    value = current.f_locals[key]
                    path = args.output / (f"{key}.npy" if isinstance(value, np.ndarray) else f"{key}.json")
                    if isinstance(value, np.ndarray):
                        np.save(path, value, allow_pickle=False)
                    else:
                        write_json(path, value)
                    record["artifacts"][key] = {"file": path.name, "sha256": sha256(path)}
                break
            frame = frame.tb_next
        assert set(record["artifacts"]) == {"image", "params", "commands", "shaders"}
        write_json(args.output / "diagnostic.json", record)
        print(json.dumps({"admitted": False, "error": record["error"], "artifacts": record["artifacts"]}), flush=True)
        traceback.print_exc()
        return 1
    raise AssertionError("expected the preserved failed fixture assertion, no admission permitted")


if __name__ == "__main__":
    raise SystemExit(main())
