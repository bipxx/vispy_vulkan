"""Candidate-only native pipeline proof around the frozen public plugin runner."""

import argparse
import importlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys

import oracle_napari_threedee_overlay_capture as frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow", choices=("layer", "render-plane", "render-plane-scheduled"), default="layer")
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args()
    runner = frozen if args.workflow == "layer" else importlib.import_module(
        "oracle_napari_render_plane_scheduled_capture" if args.workflow == "render-plane-scheduled"
        else "oracle_napari_render_plane_capture")
    assert args.fixture in runner.CASES
    assert not args.output.exists(), "each candidate process needs a fresh artifact directory"
    args.output.mkdir(parents=True)
    old = sys.argv
    sys.argv = [str(Path(runner.__file__)), "--kind", "candidate",
                "--output", str(args.output), "--worker", args.fixture]
    try:
        result = runner.main()
    finally:
        sys.argv = old
    from vispy import _dawn
    native = Path(_dawn.__file__).resolve()
    info, probe = _dawn.device_info(), _dawn.probe()
    proof = {"kind": "actual installed candidate pipeline execution", "fixture": args.fixture,
             "native_origin": str(native), "native_sha256": frozen.sha256(native),
             "candidate_version": metadata.version("vispy"),
             "frozen_capture_sha256": frozen.sha256(Path(runner.__file__)),
             "device_info": info, "probe": probe, "worker_result": int(result)}
    path = args.output / "native-proof.json"
    frozen.write_json(path, proof)
    capture = args.output / f"{args.fixture}.capture.json"
    data = json.loads(capture.read_text())
    for record in data["fixtures"].values():
        record["process"] = {"exit_code": int(result)}
        record["native_proof"] = {"file": path.name, "sha256": frozen.sha256(path)}
    frozen.write_json(args.output / "manifest.json", data)
    if not result:
        assert info["ok"] and probe["draw_calls"] > 0
        assert probe["dawn_queue_submits"] > 0 and probe["pipeline_misses"] > 0
    print(json.dumps({"fixture": args.fixture, "worker_result": int(result),
                      "native_sha256": proof["native_sha256"], "device": info,
                      "draw_calls": probe["draw_calls"], "pipeline_misses": probe["pipeline_misses"],
                      "queue_submits": probe["dawn_queue_submits"]}), flush=True)
    return bool(result)


if __name__ == "__main__":
    raise SystemExit(main())
