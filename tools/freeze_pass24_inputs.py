"""Freeze pass24 source and matching CPU harnesses before releasing peer edits."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))


def main():
    snapshot = ROOT / "build/w9/source"
    evidence = ROOT / "build/evidence/native-pass-24"
    if snapshot.exists() or evidence.exists():
        raise ValueError("Pass24 snapshot and evidence must be new")
    point = ROOT / "build/point-identity-cpu"
    worker = load(point / "hashes.json")
    verified = {}
    for record in worker:
        name = record["file"].replace("\\", "/")
        path = ROOT / name if name.startswith(("cpp/", "tests/")) else point / name
        assert sha(path) == record["sha256"], f"Worker archive/live bytes differ: {name}"
        verified[name] = record["sha256"]
    evidence.mkdir(parents=True)
    subprocess.run([sys.executable, str(ROOT / "cmake/snapshot_wheel_sources.py"), str(snapshot)], check=True)
    manifest = load(snapshot / "wheel-source-manifest.json")
    for name, digest in verified.items():
        if name.startswith("cpp/"):
            assert manifest["source_files"][name] == digest, name
    harness = evidence / "harness"
    inputs = {}
    # Some unmodified contracts include ../../cpp/... relative to their source
    # location. Copy exact frozen project headers/sources into that layout.
    for name, digest in manifest["source_files"].items():
        if name.startswith("cpp/"):
            target = harness / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = (snapshot / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest, name
            target.write_bytes(data)
            inputs[name] = digest
    for path in sorted((ROOT / "tests").rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix not in {".cpp", ".hpp", ".h"} and not path.is_relative_to(ROOT / "tests/shaders/corpus"):
            continue
        name = path.relative_to(ROOT).as_posix()
        target = harness / name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if name in verified:
            assert digest == verified[name], name
        target.write_bytes(data)
        inputs[name] = digest
    for corpus, source in (("point-corpus", point / "point-corpus"), ("text-corpus", point / "text-corpus"),
                           ("volume-corpus", point / "volume-corpus"), ("marker-corpus", ROOT / "build/marker-corpus")):
        for path in sorted(source.rglob("*")):
            if path.is_file():
                name = "datasets/" + corpus + "/" + path.relative_to(source).as_posix()
                target = harness / name
                target.parent.mkdir(parents=True, exist_ok=True)
                data = path.read_bytes()
                target.write_bytes(data)
                inputs[name] = hashlib.sha256(data).hexdigest()
    shutil.copytree(point, evidence / "full-source-tint-proof")
    for name, digest in verified.items():
        if name.startswith(("cpp/", "tests/")):
            assert sha(ROOT / name) == digest, f"Peer changed input while freezing: {name}"
    digest = hashlib.sha256()
    for name, checksum in sorted(inputs.items()):
        digest.update(name.encode() + b"\0" + bytes.fromhex(checksum))
    record = {"qualification": "frozen_source_and_matched_cpu_inputs_only", "source_snapshot": str(snapshot),
              "source_tree_sha256": manifest["source_tree_sha256"], "worker_verified_sha256": verified,
              "worker_hash_manifest_sha256": sha(point / "hashes.json"), "harness_files": inputs,
              "harness_tree_sha256": digest.hexdigest(), "harness_root": str(harness),
              "sdk_tint_reader_enabled": False, "sdk_tint_reason": "SDK exports public headers and targets; private Tint headers/dawn_utils_config are intentionally absent",
              "separate_full_source_tint_proof": "full-source-tint-proof/evidence.json", "gpu_qualified": False}
    (evidence / "frozen-inputs.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"source_tree_sha256": record["source_tree_sha256"], "harness_tree_sha256": record["harness_tree_sha256"],
                      "harness_files": len(inputs), "verified_worker_files": len(verified)}))


if __name__ == "__main__":
    main()
