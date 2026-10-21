"""Capture public DIVE exports in a pinned, independently installed Qt5 oracle."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
import traceback

import numpy as np

from fixture_dive import CASES, assert_landmarks, render
from host_inventory import source_inventory
from oracle_capture import PIN, ROOT, SOURCE_FILES, sha256, write_json

ADMISSION = ROOT / "tools/oracle_dive_admission.json"


def provenance(kind):
    import vispy
    from vispy import app, gloo
    from PyQt5 import QtCore
    app.use_app("PyQt5")
    import DIVE

    admission = json.loads(ADMISSION.read_text())
    pin = tomllib.loads((ROOT / "compat/hosts.lock.toml").read_text())["dive"]
    expected = "0.17.0" if kind == "upstream" else "0.17.0+vulkan.1"
    assert metadata.version("vispy") == vispy.__version__ == expected
    vispy_package = Path(vispy.__file__).resolve().parent
    host_package = Path(DIVE.__file__).resolve().parent
    assert "site-packages" in str(host_package), "DIVE must be the unchanged installed source copy"
    host_tree = source_inventory(host_package)
    assert host_tree["sha256"] == pin["package_tree_sha256"], "pinned DIVE package changed"
    assert sha256(ROOT / admission["requirements"]) == admission["requirements_sha256"]
    assert sha256(ROOT / pin["source_inventory"]) == pin["source_inventory_sha256"]
    assert sha256(ROOT / admission["import_inventory"]) == admission["import_inventory_sha256"]
    original_import = json.loads((ROOT / admission["import_inventory"]).read_text())
    installed = []
    for record in original_import["distributions"]:
        name = record["name"]
        version = metadata.version(name)
        assert version == (expected if name.lower() == "vispy" else record["version"]), (name, version)
        dist = metadata.distribution(name)
        record_path = next(dist.locate_file(path) for path in dist.files
                           if str(path).replace("\\", "/").endswith(".dist-info/RECORD"))
        installed.append({"name": name, "version": version,
                          "origin": str(dist.locate_file("")), "record_sha256": sha256(record_path)})
    # DIVE has no distribution metadata. Record copied package origins and
    # source hashes; never invent a package version or installed entry point.
    package_sources = {}
    archived_sources = {}
    source = ROOT / f"build/host-sources/dive-{pin['commit']}/DIVE-{pin['commit']}"
    for name, reference in admission["source_files"].items():
        path = host_package / name.removeprefix("DIVE/") if name.startswith("DIVE/") else source / name
        digest = sha256(path)
        assert digest == reference["sha256"], (name, "source pin mismatch")
        (package_sources if name.startswith("DIVE/") else archived_sources)[name] = {
            "origin": str(path), "sha256": digest, "url": reference["url"]}
    vispy_hashes = {name: sha256(vispy_package / name) for name in SOURCE_FILES}
    if kind == "upstream":
        assert "site-packages" in str(vispy_package) and not (vispy_package / "_dawn.pyd").exists()
        manifest = json.loads((ROOT / "compat/upstream_manifest.json").read_text())
        for name, actual in vispy_hashes.items():
            assert actual == manifest["files"][name], name
    canvas = app.Canvas(app="pyqt5", size=(2, 2), show=False)
    canvas.app.native.setQuitOnLastWindowClosed(False)
    canvas.set_current()
    try:
        if kind == "upstream":
            gloo.clear(color=True, depth=False, stencil=False)
            gloo.finish()
            renderer = {key: str(gloo.gl.glGetParameter(getattr(gloo.gl, enum)))
                        for key, enum in (("vendor", "GL_VENDOR"), ("renderer", "GL_RENDERER"),
                                          ("version", "GL_VERSION"))}
            assert "Dawn" not in renderer["renderer"]
        else:
            from vispy import _dawn
            renderer = _dawn.device_info()
            assert renderer["ok"], renderer["error"]
    finally:
        canvas.close()
    return {"kind": kind, "python": platform.python_version(), "python_executable": sys.executable,
            "platform": platform.platform(), "vispy_version": vispy.__version__,
            "vispy_origin": str(vispy_package), "upstream_commit": PIN if kind == "upstream" else None,
            "vispy_source_sha256": vispy_hashes, "host_commit": pin["commit"],
            "host_origin": str(host_package), "host_version_metadata": None,
            "host_package_tree_sha256": host_tree["sha256"],
            "host_package_sources": package_sources, "host_archived_sources": archived_sources,
            "source_inventory_sha256": pin["source_inventory_sha256"],
            "import_inventory_sha256": admission["import_inventory_sha256"],
            "requirements_sha256": admission["requirements_sha256"], "installed": installed,
            "qt_runtime": QtCore.qVersion(), "renderer": renderer,
            "fixture_source_sha256": sha256(ROOT / "tools/fixture_dive.py"),
            "capture_source_sha256": sha256(Path(__file__)),
            "environment": {key: os.environ.get(key) for key in
                            ("QT_API", "QT_QPA_PLATFORM", "QT_SCALE_FACTOR", "PYTHONPATH",
                             "VISPY_PYQT5_SHARE_CONTEXT")},
            "regenerate": "Use the verified unchanged DIVE source copy and hashed "
                          "compat/host-environments/dive-windows-cpython311-pyqt5.txt; "
                          "build/host-environments/dive-cpython311-pyqt5/Scripts/python.exe "
                          "tools/oracle_dive_capture.py --kind upstream --output tests/reference/dive-opengl"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ.setdefault("QT_API", "pyqt5")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    import vispy
    vispy.use(app="pyqt5", **({"gl": "gl+"} if args.kind == "upstream" else {}))
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": provenance(args.kind),
                "comparison": {"full_frame_exact": True, "landmarks_exact": True,
                               "landmark_domain": "analytic input through host CPU scene transform"},
                "fixtures": {}, "errors": {}}
    for name in ([args.worker] if args.worker else args.fixtures or CASES):
        if not args.worker:
            captured = args.output / f"{name}.capture.json"
            captured.unlink(missing_ok=True)
            child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)),
                                    "--kind", args.kind, "--output", str(args.output), "--worker", name],
                                   capture_output=True, text=True)
            print(child.stdout, end="", flush=True)
            print(child.stderr, end="", file=sys.stderr, flush=True)
            process = {"exit_code": child.returncode}
            for stream in ("stdout", "stderr"):
                log = args.output / f"{name}.{stream}.log"
                log.write_text(getattr(child, stream), encoding="utf-8")
                process[stream] = {"file": log.name, "sha256": sha256(log)}
            if captured.exists():
                data = json.loads(captured.read_text())
                if child.returncode == 0:
                    manifest["fixtures"].update(data["fixtures"])
                manifest["errors"].update(data["errors"])
                if name in manifest["fixtures"]:
                    manifest["fixtures"][name]["capture"] = {"file": captured.name, "sha256": sha256(captured)}
                    manifest["fixtures"][name]["process"] = process
            else:
                manifest["errors"][name] = {"error": f"capture process exited {child.returncode}"}
            if child.returncode and name not in manifest["errors"]:
                manifest["errors"][name] = {"error": f"capture process exited {child.returncode}"}
            if name in manifest["errors"]:
                manifest["errors"][name]["process"] = process
            write_json(args.output / "manifest.json", manifest)
            continue
        artifacts = {}
        try:
            image, commands, shaders, params, extras = render(name)
            payloads = {"rgba": ("npy", image), "filtered_glir": ("glir.json", commands),
                        "expanded_shaders": ("shaders.json", shaders), "parameters": ("parameters.json", params)}
            for key, value in extras.items():
                payloads[key] = ("png" if key.endswith("png") else "npy", value)
            for key, (suffix, value) in payloads.items():
                path = args.output / f"{name}.{key}.{suffix}"
                if suffix == "npy":
                    np.save(path, value, allow_pickle=False)
                elif suffix == "png":
                    path.write_bytes(value)
                else:
                    write_json(path, value)
                artifacts[key] = {"file": path.name, "sha256": sha256(path)}
            assert_landmarks(name, image, params, before=extras.get("before"))
            assert commands and shaders, "real scene GLIR and expanded shaders required"
            manifest["fixtures"][name] = {"parameters": params, "shape": list(image.shape), "artifacts": artifacts}
            print(f"PASS DIVE {name}: public PNG {image.shape}, independent {args.kind}", flush=True)
        except Exception as exc:
            manifest["errors"][name] = {"type": type(exc).__name__, "error": str(exc)}
            if artifacts:
                manifest["errors"][name]["unadmitted_artifacts"] = artifacts
            traceback.print_exc()
    output = args.output / (f"{args.worker}.capture.json" if args.worker else "manifest.json")
    write_json(output, manifest)
    if not args.worker and args.kind == "upstream":
        admission = json.loads(ADMISSION.read_text())
        admission["upstream_qualification"] = "unresolved" if manifest["errors"] else "partial"
        admission["bounded_fixture_qualification"] = "unresolved" if manifest["errors"] else "passed"
        admission["successful_fixtures"] = list(manifest["fixtures"])
        admission["unresolved_fixtures"] = {"arrow": "No real rendering fixture yet.", **manifest["errors"]}
        admission["reference_manifest"] = str(output.resolve().relative_to(ROOT).as_posix())
        admission["reference_manifest_sha256"] = sha256(output)
        admission["bounded_fixture_plan"] = {"cases": list(args.fixtures or CASES),
            "widget_size": [640, 480], "public_api": "DIVEWidget.take_screenshot",
            "updates": ["DIVEWidget.edit_data", "DIVEWidget.edit_artist"],
            "comparison": manifest["comparison"], "fixture_source_sha256": manifest["provenance"]["fixture_source_sha256"]}
        write_json(ADMISSION, admission)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
