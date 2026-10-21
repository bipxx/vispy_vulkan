"""Freeze the sealed point-storage runtime and matched external SDK CPU inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

# Even direct invocation must not create bytecode before destination checks.
sys.dont_write_bytecode = True
import pass25_guard as guard


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "build/point-capacity-cpu"
WORKER_HASH_SHA = guard.WORKER_HASH_SHA
WORKER_EVIDENCE_SHA = guard.WORKER_EVIDENCE_SHA
WORKER_SOURCE_SHA = guard.WORKER_SOURCE_SHA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("snapshot", "evidence", "build"):
        parser.add_argument("--" + key, default=guard.PATHS[key])
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    # All canonical paths, existing-output checks, trusted worker/archive,
    # build tools and activated artifacts are checked before the first mkdir.
    paths = guard.validate_destinations(ROOT, vars(args), freeze=True)
    snapshot, evidence = paths["snapshot"], paths["evidence"]
    guard.verify_preparation(ROOT, paths["preparation"])
    guard.verify_sdk(ROOT, paths["sdk"], ROOT / "cmake/dependencies.lock.json")
    owned = guard.verify_worker(WORKER)
    for name, expected in owned.items():
        guard.require(sha(ROOT / name) == expected, f"Live tested worker source changed: {name}")
    activation_path = paths["activation"]
    before = guard.protected(ROOT)
    if args.preflight_only:
        print(json.dumps({"preflight": "passed_read_only", "verified_worker_sources": len(owned),
                          "worker_source_identity_sha256": WORKER_SOURCE_SHA, "protected": before}))
        return
    evidence.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, "-B", str(ROOT / "cmake/snapshot_wheel_sources.py"), str(snapshot)], check=True)
    manifest = load(snapshot / "wheel-source-manifest.json")
    for name, expected in owned.items():
        if name.startswith("cpp/"):
            guard.require(manifest["source_files"][name] == expected, f"Frozen tested CPP changed: {name}")
    harness = evidence / "harness"
    inputs = {}

    def copy_input(name, data):
        target = harness / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs[name] = hashlib.sha256(data).hexdigest()

    # Preserve relative ../../cpp includes used by the unmodified contracts.
    for name, expected in manifest["source_files"].items():
        if name.startswith("cpp/"):
            data = (snapshot / name).read_bytes()
            guard.require(hashlib.sha256(data).hexdigest() == expected, f"Frozen CPP changed: {name}")
            copy_input(name, data)
    # Archive every current C++ harness; use tested worker bytes for owned files.
    for path in sorted((ROOT / "tests").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".cpp", ".hpp", ".h"}:
            name = path.relative_to(ROOT).as_posix()
            data = (WORKER / "source" / name).read_bytes() if name in owned else path.read_bytes()
            if name in owned:
                guard.require(hashlib.sha256(data).hexdigest() == owned[name], f"Worker contract changed: {name}")
            copy_input(name, data)
    for corpus, source in (("point-corpus", "points"), ("marker-corpus", "markers"),
                           ("text-corpus", "text"), ("volume-corpus", "volume")):
        original = WORKER / "datasets" / source
        guard.require(original.is_dir() and any(original.iterdir()), f"Worker dataset missing: {source}")
        for path in sorted(original.rglob("*")):
            if path.is_file():
                copy_input("datasets/" + corpus + "/" + path.relative_to(original).as_posix(), path.read_bytes())
    for path in sorted((WORKER / "datasets/corpus").rglob("*")):
        if path.is_file():
            copy_input("tests/shaders/corpus/" + path.relative_to(WORKER / "datasets/corpus").as_posix(), path.read_bytes())
    shutil.copytree(WORKER, evidence / "full-source-tint-proof")
    for name, expected in owned.items():
        guard.require(sha(ROOT / name) == expected, f"Peer changed tested source while freezing: {name}")
    for name, expected in manifest["source_files"].items():
        guard.require(sha(snapshot / name) == expected, f"Snapshot changed while freezing: {name}")
    guard.require(guard.protected(ROOT) == before, "Protected pass24 artifacts changed while freezing")
    digest = hashlib.sha256()
    for name, expected in sorted(inputs.items()):
        digest.update(name.encode() + b"\0" + bytes.fromhex(expected))
    result = {"schema": 2, "qualification": "frozen_source_and_matched_cpu_inputs_only", "source_snapshot": str(snapshot),
              "source_tree_sha256": manifest["source_tree_sha256"], "harness_root": str(harness),
              "harness_files": inputs, "harness_tree_sha256": digest.hexdigest(),
              "worker_source_identity_sha256": WORKER_SOURCE_SHA, "worker_hash_manifest_sha256": WORKER_HASH_SHA,
              "worker_evidence_sha256": WORKER_EVIDENCE_SHA, "worker_verified_sha256": owned,
              "activation_manifest_sha256": sha(activation_path), "protected_native_before": before,
              "protected_native_after": guard.protected(ROOT), "freeze_tool_sha256": sha(Path(__file__)),
              "guard_tools_sha256": {name: sha(ROOT / name) for name in (
                  "tools/pass25_guard.py", "tools/freeze_pass25_inputs.py", "tools/build_pass25_sdk.ps1")},
              "sdk_manifest_sha256": guard.SDK_SHA, "preparation_sha256": guard.PREPARATION_SHA,
              "sdk_tint_reader_enabled": False,
              "sdk_tint_reason": "Verified SDK3 exports public headers/targets; private Tint and dawn_utils_config remain intentionally absent",
              "separate_full_source_tint_proof": "full-source-tint-proof/evidence.json", "gpu_qualified": False}
    (evidence / "frozen-inputs.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source_tree_sha256": result["source_tree_sha256"], "harness_tree_sha256": result["harness_tree_sha256"],
                      "harness_files": len(inputs), "verified_worker_sources": len(owned),
                      "frozen_inputs_sha256": sha(evidence / "frozen-inputs.json")}))


if __name__ == "__main__":
    try:
        main()
    except (guard.GuardError, OSError, KeyError, ValueError) as exc:
        sys.exit(f"Pass25 freeze rejected: {exc}")
