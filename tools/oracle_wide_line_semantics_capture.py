"""Capture only pinned upstream endpoint-isolation/clipped-line references."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_wide_line_semantics import CASES, assert_landmarks, contract, render
from oracle_capture import ROOT, provenance, sha256, write_json

AUTHORING = ROOT / "build/evidence/wide-line-semantics-authoring-1/authoring.json"


def require_authoring():
    value = json.loads(AUTHORING.read_text(encoding="utf-8"))
    assert value["contract"] == contract() and not value["candidate_seen"] and not value["GPU_used"]
    for name, expected in value["source_sha256"].items():
        assert sha256(ROOT / name) == expected, name
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    authoring = require_authoring()
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    if not args.worker:
        args.output.mkdir(parents=True, exist_ok=False)
        manifest = {"schema": 1, "kind": "upstream", "candidate_seen": False,
                    "authoring_sha256": sha256(AUTHORING),
                    "comparison": "exact entire independently captured RGBA with unchanged analytic invariants",
                    "provenance": None, "fixtures": {}, "errors": {}}
        for name in CASES:
            command = [sys.executable, "-X", "faulthandler", str(Path(__file__).resolve()),
                       "--output", str(args.output), "--worker", name]
            child = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            process = {"exit_code": child.returncode, "command": command}
            for stream in ("stdout", "stderr"):
                path = args.output / f"{name}.{stream}.log"
                path.write_text(getattr(child, stream), encoding="utf-8")
                process[stream] = {"file": path.name, "sha256": sha256(path)}
            path = args.output / f"{name}.capture.json"
            value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if manifest["provenance"] is None:
                manifest["provenance"] = value.get("provenance")
            record = value.get("fixtures", {}).get(name)
            if child.returncode == 0 and record is not None:
                record.update(process=process, capture={"file": path.name, "sha256": sha256(path)})
                manifest["fixtures"][name] = record
            else:
                manifest["errors"][name] = {"process": process, "child_error": value.get("errors", {}),
                                            "unadmitted_record": record}
            write_json(args.output / "manifest.json", manifest)
            print(name, "terminal", child.returncode, flush=True)
        return int(bool(manifest["errors"]) or len(manifest["fixtures"]) != len(CASES))
    manifest = {"schema": 1, "provenance": None, "fixtures": {}, "errors": {}}
    try:
        import vispy
        vispy.use(gl="gl+")
        origins = provenance("upstream")
        origins["line_semantics_fixture_sha256"] = sha256(ROOT / "tools/fixture_wide_line_semantics.py")
        origins["line_semantics_capture_sha256"] = sha256(Path(__file__))
        manifest["provenance"] = origins
        image, commands, shaders, spec, observations = render(args.worker, "pyqt6")
        record = {"parameters": spec, "observations": observations,
                  "authoring_sha256": sha256(AUTHORING), "shape": list(image.shape), "dtype": image.dtype.str}
        for key, value, suffix in (("rgba", image, "npy"), ("filtered_glir", commands, "glir.json"),
                                   ("expanded_shaders", shaders, "shaders.json"), ("observations", observations, "observations.json")):
            path = args.output / f"{args.worker}.{suffix}"
            if suffix == "npy":
                np.save(path, value, allow_pickle=False)
            else:
                write_json(path, value)
            record[key] = {"file": path.name, "sha256": sha256(path)}
        manifest["fixtures"][args.worker] = record
        assert commands and shaders
        assert sum(command[:2] == ["FUNC", "glFinish"] for command in commands) == 1
        assert_landmarks(args.worker, image)
    except Exception as error:
        manifest["errors"][args.worker] = {"type": type(error).__name__, "error": str(error)}
        traceback.print_exc()
    write_json(args.output / f"{args.worker}.capture.json", manifest)
    return int(bool(manifest["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
