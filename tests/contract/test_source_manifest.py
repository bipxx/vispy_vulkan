"""Fork identity: distribution, version base, and parity-tree file hashes."""

import hashlib
import json
from pathlib import Path

import vispy
from vispy.app import Canvas
from vispy.gloo import Program
from vispy.scene import SceneCanvas
from vispy.visuals import ImageVisual
from vispy.visuals.shaders import Function

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "compat" / "upstream_manifest.json").read_text(encoding="utf-8"))
DEVIATIONS = {
    line.strip()
    for line in (ROOT / "compat" / "deviations.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
}
PARITY = ROOT / "third_party" / "parity" / "vispy" / "vispy"


def test_version_and_public_objects():
    assert vispy.__version__ == "0.17.0+vulkan.1"
    assert vispy.__version__.split("+", 1)[0] == "0.17.0"
    assert Program.__module__ == "vispy.gloo.program"
    assert Canvas.__module__ == "vispy.app.canvas"
    assert SceneCanvas.__module__ == "vispy.scene.canvas"
    assert ImageVisual.__module__ == "vispy.visuals.image"
    assert Function.__module__ == "vispy.visuals.shaders.function"
    print("distribution vispy")
    print("version 0.17.0+vulkan.1")
    print("import vispy ok", vispy.__version__)


def test_unchanged_files_match_parity_checkout():
    package = ROOT / "src" / "vispy"
    mismatches = []
    for rel, digest in MANIFEST["files"].items():
        local = package / rel
        assert local.is_file(), rel
        local_digest = hashlib.sha256(local.read_bytes()).hexdigest()
        parity = PARITY / rel
        if rel in DEVIATIONS:
            continue
        if local_digest != digest or not parity.is_file() or hashlib.sha256(parity.read_bytes()).hexdigest() != digest:
            mismatches.append(rel)
    assert mismatches == []
    for rel in DEVIATIONS:
        if rel not in MANIFEST["files"]:
            assert (package / rel).is_file()
            continue
        local = package / rel
        parity = PARITY / rel
        assert hashlib.sha256(local.read_bytes()).hexdigest() != hashlib.sha256(parity.read_bytes()).hexdigest()
