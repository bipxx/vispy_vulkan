"""Freeze the pass24 source with exactly one verified Qt backend overlay."""

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/w9/source"
DESTINATION = ROOT / "build/w10/source"
OVERLAY = "src/vispy/app/backends/_qt.py"
BASE_DIGEST = "a6479aacabf2f44887ece1dba9402b44565669e65fccca081be712860a8f6007"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected(activation):
    result = {}
    for name, expected in activation["activated"].items():
        relative = ("src/vispy/visuals/text/" if name.startswith("_sdf_cpu.") else "src/vispy/") + name
        result[relative] = sha(ROOT / relative)
        assert result[relative] == expected, (relative, "activated pass24 artifact changed")
    return result


def main():
    if DESTINATION.exists():
        raise FileExistsError("The w10 source destination must be new")
    activation_path = ROOT / "build/evidence/native-pass-24/activation.json"
    activation = json.loads(activation_path.read_text(encoding="utf-8"))
    before = protected(activation)
    base_manifest_path = BASE / "wheel-source-manifest.json"
    baseline = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    assert baseline["source_tree_sha256"] == BASE_DIGEST
    assert activation["native_source_tree_sha256"] == BASE_DIGEST
    overlay_bytes = (ROOT / OVERLAY).read_bytes()
    overlay_sha = hashlib.sha256(overlay_bytes).hexdigest()
    assert overlay_sha == activation["python_inputs"][OVERLAY], "Qt overlay differs from the activated proof"
    DESTINATION.mkdir(parents=True)
    inputs = {}
    for relative, expected in baseline["source_files"].items():
        data = (BASE / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected, (relative, "frozen w9 source changed")
        if relative == OVERLAY:
            data = overlay_bytes
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs[relative] = hashlib.sha256(data).hexdigest()
    changed = {name for name in inputs if inputs[name] != baseline["source_files"][name]}
    assert changed == {OVERLAY}
    spec = importlib.util.spec_from_file_location("wheel_snapshot", BASE / "cmake/snapshot_wheel_sources.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    for relative in ("third_party/dawn", "third_party/parity"):
        (DESTINATION / relative).parent.mkdir(parents=True, exist_ok=True)
        helper.link_directory((BASE / relative).resolve(strict=True), DESTINATION / relative)
    digest = hashlib.sha256()
    for relative, checksum in sorted(inputs.items()):
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(checksum))
    assert sha(ROOT / OVERLAY) == overlay_sha, "Qt source changed during its overlay capture"
    assert protected(activation) == before
    manifest = dict(baseline)
    manifest.update(captured_utc=datetime.now(timezone.utc).isoformat(), snapshot=str(DESTINATION),
                    source_tree_sha256=digest.hexdigest(), source_files=inputs,
                    runtime_milestone={"snapshot": str(BASE), "source_tree_sha256": BASE_DIGEST,
                                       "manifest_sha256": sha(base_manifest_path),
                                       "content": "exact frozen w9 project inputs plus only the verified Qt backend overlay"},
                    overlay={"file": OVERLAY, "previous_sha256": baseline["source_files"][OVERLAY],
                             "live_sha256_before": overlay_sha, "snapshot_sha256": sha(DESTINATION / OVERLAY),
                             "live_sha256_after": sha(ROOT / OVERLAY),
                             "activation_manifest_sha256": sha(activation_path)},
                    protected_native_before=before, protected_native_after=protected(activation),
                    live_cpp_read=False)
    (DESTINATION / "wheel-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_tree_sha256": digest.hexdigest(), "qt_sha256": overlay_sha,
                      "source_files": len(inputs), "live_cpp_read": False}))


if __name__ == "__main__":
    main()
