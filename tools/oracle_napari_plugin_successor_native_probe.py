# SPDX-License-Identifier: AGPL-3.0-only
"""Candidate-only native pipeline proof around the plugin successor capture (decisions D30 and D31).

The successor of tools/oracle_napari_threedee_native_probe.py: it runs tools/oracle_napari_plugin_successor_capture.py's
worker for one fixture in this process, then records the installed candidate's native module and Dawn probe.
"""

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import sys

import oracle_napari_plugin_successor_capture as runner


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", choices=runner.SUITES, required=True)
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args()
    assert args.fixture in runner.successor(args.suite).CASES
    assert not args.output.exists(), "each candidate process needs a fresh artifact directory"
    args.output.mkdir(parents=True)
    old = sys.argv
    sys.argv = [str(Path(runner.__file__)), "--suite", args.suite, "--kind", "candidate",
                "--output", str(args.output), "--worker", args.fixture]
    try:
        result = runner.main()
    finally:
        sys.argv = old
    from vispy import _dawn
    native = Path(_dawn.__file__).resolve()
    info, probe = _dawn.device_info(), _dawn.probe()
    proof = {"kind": "actual installed candidate pipeline execution", "suite": args.suite, "fixture": args.fixture,
             "native_origin": str(native), "native_sha256": runner.sha256(native),
             "candidate_version": metadata.version("vispy"),
             "frozen_capture_sha256": runner.sha256(Path(runner.__file__)),
             "device_info": info, "probe": probe, "worker_result": int(result)}
    path = args.output / "native-proof.json"
    runner.write_json(path, proof)
    capture = args.output / f"{args.fixture}.capture.json"
    data = json.loads(capture.read_text(encoding="utf-8"))
    for record in data["fixtures"].values():
        record["process"] = {"exit_code": int(result)}
        record["native_proof"] = {"file": path.name, "sha256": runner.sha256(path)}
    runner.write_json(args.output / "manifest.json", data)
    if not result:
        assert info["ok"] and probe["draw_calls"] > 0
        assert probe["dawn_queue_submits"] > 0 and probe["pipeline_misses"] > 0
    print(json.dumps({"suite": args.suite, "fixture": args.fixture, "worker_result": int(result),
                      "native_sha256": proof["native_sha256"], "device": info,
                      "draw_calls": probe["draw_calls"], "pipeline_misses": probe["pipeline_misses"],
                      "queue_submits": probe["dawn_queue_submits"]}), flush=True)
    return bool(result)


if __name__ == "__main__":
    raise SystemExit(main())
