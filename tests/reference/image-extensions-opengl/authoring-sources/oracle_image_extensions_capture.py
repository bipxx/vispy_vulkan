"""Frozen image/label authoring or isolated installed OpenGL/candidate capture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from fixture_image_extensions import CASES, COMPARISON, assert_landmarks, case_contract, render

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/reference/image-extensions-opengl"
LOCK = ROOT / "tools/oracle_napari_requirements.txt"
SOURCES = ("tools/fixture_image_extensions.py", "tools/oracle_image_extensions_capture.py",
           "tests/parity/test_image_extensions_parity.py")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze_authoring(output):
    output.mkdir(parents=True, exist_ok=True)
    assert not (output / "manifest.json").exists(), "captured criteria must never be rewritten"
    payload = {"schema": 1, "candidate_seen": False, "GPU_used": False,
        "comparison": COMPARISON, "cases": {name: case_contract(name) for name in CASES},
        "sources_sha256": {f: sha256(ROOT / f) for f in SOURCES},
        "installed_upstream_lock": {"file": str(LOCK.relative_to(ROOT)), "sha256": sha256(LOCK)},
        "scope": "13public workflows; remap is observed from real uploads, multiscale uses one selected host texture, original level content/revisit frames are distinct cases"}
    authoring = output / "authoring.json"
    if authoring.exists():
        assert json.loads(authoring.read_text(encoding="utf-8")) == payload, "freeze changed; preserve the original attempt and use a new output directory"
    write_json(authoring, payload)
    snapshot = output / "authoring-sources"
    snapshot.mkdir(exist_ok=True)
    for source in SOURCES:
        target = snapshot / Path(source).name
        if target.exists():
            assert sha256(target) == payload["sources_sha256"][source]
        else:
            target.write_bytes((ROOT / source).read_bytes())
    return payload


def cpu_origins(kind):
    expected = "0.17.0" if kind == "upstream" else "0.17.0+vulkan.1"
    assert metadata.version("vispy") == expected
    assert metadata.version("napari") == "0.9.2"
    assert metadata.version("numba") == "0.68.0"
    # Assert each pinned runtime distribution except the deliberately replaced
    # renderer. Reading metadata imports no Qt widget and creates no device.
    from packaging.requirements import Requirement
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith((" ", "#")):
            continue
        requirement = Requirement(line.split(" --hash=", 1)[0].rstrip("\\").strip())
        if requirement.marker and not requirement.marker.evaluate():
            continue
        if requirement.name.lower() != "vispy":
            assert metadata.version(requirement.name) in requirement.specifier, (
                requirement.name, metadata.version(requirement.name), str(requirement.specifier))
    dist = metadata.distribution("vispy")
    package = Path(dist.locate_file("vispy")).resolve()
    if kind == "upstream":
        assert "site-packages" in str(package)
        assert not list(package.glob("_dawn*")), "upstream origin contains the fork"
        pin = json.loads((ROOT / "compat/upstream_manifest.json").read_text(encoding="utf-8"))
        for source in ("gloo/program.py", "gloo/glir.py", "gloo/texture.py", "gloo/buffer.py",
                       "gloo/context.py", "gloo/wrappers.py"):
            assert sha256(package / source) == pin["files"][source]
    host = Path(metadata.distribution("napari").locate_file("napari")).resolve()
    observed = {"kind": kind, "python_executable": sys.executable,
        "vispy_origin": str(package), "napari_origin": str(host),
        "installed_versions": {d.metadata["Name"]: d.version for d in metadata.distributions()},
        "host_lock_sha256": sha256(LOCK), "fixture_sha256": sha256(ROOT / SOURCES[0]),
        "capture_sha256": sha256(Path(__file__)),
        "host_source_sha256": {name: sha256(host / name) for name in (
            "layers/image/image.py", "layers/labels/labels.py", "layers/_scalar_field/scalar_field.py",
            "_vispy/layers/labels.py", "_vispy/layers/base.py", "_vispy/utils/gl.py",
            "utils/colormaps/colormap.py")},
        "visual_source_sha256": {name: sha256(package / name) for name in (
            "visuals/image.py", "visuals/_scalable_textures.py")},
        "native_artifacts": {p.name: sha256(p) for p in package.glob("_dawn*.pyd")},
        "environment": {key: os.environ.get(key) for key in
            ("QT_API", "QT_SCALE_FACTOR", "QT_QPA_PLATFORM", "PYTHONHASHSEED", "PYTHONPATH")}}
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    parser.add_argument("--freeze-authoring", action="store_true", help="CPU-only; create immutable pre-candidate data/criteria/source witnesses")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.freeze_authoring:
        assert args.kind is None and args.worker is None
        payload = freeze_authoring(args.output)
        print("FROZEN", len(payload["cases"]), "public workflows; no graphics context or candidate")
        return 0
    parser.error("--kind is required for capture") if not args.kind else None
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("PYTHONHASHSEED", "0")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen", "actual OpenGL/Qt qualification requires a real surface"
    authoring_file = args.output / "authoring.json"
    if args.kind == "candidate":
        authoring_file = REFERENCE / "authoring.json"
    assert authoring_file.is_file(), "freeze independent criteria before capture"
    authoring = json.loads(authoring_file.read_text(encoding="utf-8"))
    assert authoring["cases"] == {name: case_contract(name) for name in CASES}
    for source, expected in authoring["sources_sha256"].items():
        assert sha256(ROOT / source) == expected, source
    assert sha256(LOCK) == authoring["installed_upstream_lock"]["sha256"]
    origins = cpu_origins(args.kind)
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.worker:
        assert not (args.output / "manifest.json").exists(), "preserve every capture attempt"
    manifest = {"schema": 1, "provenance": origins, "comparison": COMPARISON,
                "authoring_sha256": sha256(authoring_file), "fixtures": {}, "errors": {}, "processes": {}}
    if not args.worker:
        for name in args.fixtures or CASES:
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__).resolve()),
                "--kind", args.kind, "--output", str(args.output), "--worker", name],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            stdout, stderr = args.output / f"{name}.stdout.log", args.output / f"{name}.stderr.log"
            stdout.write_text(child.stdout, encoding="utf-8")
            stderr.write_text(child.stderr, encoding="utf-8")
            print(child.stdout, end="", flush=True)
            print(child.stderr, end="", file=sys.stderr, flush=True)
            manifest["processes"][name] = {"exit_code": child.returncode,
                "stdout": {"file": stdout.name, "sha256": sha256(stdout)},
                "stderr": {"file": stderr.name, "sha256": sha256(stderr)}}
            capture = args.output / f"{name}.capture.json"
            if capture.is_file():
                data = json.loads(capture.read_text(encoding="utf-8"))
                manifest["errors"].update(data["errors"])
                if child.returncode == 0:
                    manifest["fixtures"].update(data["fixtures"])
                    if name in manifest["fixtures"]:
                        manifest["fixtures"][name]["capture"] = {"file": capture.name, "sha256": sha256(capture)}
            if child.returncode or name not in manifest["fixtures"]:
                manifest["errors"].setdefault(name, {"error": f"capture child exited {child.returncode}; no admission"})
            write_json(args.output / "manifest.json", manifest)
        return int(bool(manifest["errors"]))
    try:
        if args.kind == "upstream":
            import vispy
            vispy.use(gl="gl+")
        from oracle_capture import provenance
        actual = provenance(args.kind)
        image, commands, shaders, params = render(args.worker,
            backend="pyqt6" if args.kind == "upstream" else "dawn_headless")
        array_file, trace_file, shader_file, params_file = [args.output / f"{args.worker}.{suffix}"
            for suffix in ("npy", "glir.json", "shaders.json", "parameters.json")]
        # Preserve raw pixels and commands even when analytic admission fails.
        np.save(array_file, image, allow_pickle=False)
        write_json(trace_file, commands)
        write_json(shader_file, shaders)
        write_json(params_file, params)
        assert_landmarks(args.worker, image)
        assert commands and shaders
        manifest["fixtures"][args.worker] = {"parameters": params, "shape": list(image.shape),
            "actual_renderer_provenance": actual,
            "rgba": {"file": array_file.name, "sha256": sha256(array_file)},
            "filtered_glir": {"file": trace_file.name, "sha256": sha256(trace_file)},
            "expanded_shaders": {"file": shader_file.name, "sha256": sha256(shader_file)},
            "parameters_file": {"file": params_file.name, "sha256": sha256(params_file)}}
        print("PASS", args.kind, args.worker, image.shape, "fixed analytic landmarks; exact comparison policy", flush=True)
    except Exception as exc:
        manifest["errors"][args.worker] = {"type": type(exc).__name__, "error": str(exc)}
        traceback.print_exc()
    write_json(args.output / f"{args.worker}.capture.json", manifest)
    return int(bool(manifest["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
