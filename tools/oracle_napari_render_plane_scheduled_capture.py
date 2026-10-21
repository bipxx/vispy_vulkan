"""Capture the genuine registered plugin in isolated unchanged host processes."""

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
import zipfile

import numpy as np

if __package__:
    from .fixture_napari_render_plane_scheduled import CASES, assert_landmarks, render
else:
    from fixture_napari_render_plane_scheduled import CASES, assert_landmarks, render

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

COMMIT = "7bd485085186ebe1907f8de931aa7a93e0d58a83"
TAG = "42be31adce55bed767dd5f835c32d08c329f3e35"
WHEEL_SHA = "de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e"
WHEEL = ROOT / "build/host-wheels/napari-threedee-v0.0.29-qualification-1/napari_threedee-0.0.29-py3-none-any.whl"
PROOFS = (
    "napari-threedee-packaging-provenance.json", "napari-threedee-registration.json",
    "napari-threedee-wheel-content.json", "napari-threedee-generated-version.py",
    "napari-threedee-pinned-manifest.yaml", "napari-threedee-pinned-pyproject.toml",
    "napari-threedee-windows-cpython312-pyqt6.txt", "build-tools-windows-cpython312.txt",
    "napari-threedee-package-build-windows-cpython312.txt", "napari-threedee-package-wheel-windows-cpython312.txt",
    "napari-threedee-upstream-numpy246-windows-cpython312-pyqt6.txt",
    "napari-threedee-candidate-numpy246-windows-cpython312-pyqt6.txt",
    "napari-threedee-numpy246-paired-provenance-w5.json",
)


def plugin_provenance():
    """Verify real wheel contents and public entry point before a fixture runs."""
    import napari
    import napari_threedee
    from npe2 import PluginManager

    assert napari.__version__ == metadata.version("napari") == "0.9.2"
    assert metadata.version("napari-threedee") == "0.0.29"
    assert sha256(WHEEL) == WHEEL_SHA
    package = Path(napari_threedee.__file__).resolve().parent
    assert "site-packages" in str(package)
    distribution = metadata.distribution("napari-threedee")
    matched = {}
    with zipfile.ZipFile(WHEEL) as wheel:
        for member in wheel.namelist():
            if member.startswith("napari_threedee/") and not member.endswith("/"):
                installed = package / member.removeprefix("napari_threedee/")
                actual = installed.read_bytes()
                assert actual == wheel.read(member), ("installed plugin differs from genuine wheel", member)
                matched[member] = sha256(installed)
    entries = [(entry.name, entry.value) for entry in distribution.entry_points if entry.group == "napari.manifest"]
    assert entries == [("napari-threedee", "napari_threedee:napari.yaml")], entries
    manager = PluginManager.instance()
    manager.discover()
    manifest = manager.get_manifest("napari-threedee")
    assert manifest.name == "napari-threedee"
    widgets = {widget.display_name: widget.command for widget in manifest.contributions.widgets}
    assert widgets["render plane manipulator"] == "napari-threedee.QtRenderPlaneManipulatorWidget"
    command = manager.commands.get(widgets["render plane manipulator"])
    assert command.__module__.startswith("napari_threedee.") and command.__name__ == "QtRenderPlaneManipulatorWidget"
    return {"public_event_delivery": "real QTest.qWait(10) after each mouse move delivers the unchanged napari 5 ms throttle; no callback replacement",
            "public_initialization": "Viewer(ndisplay=2), add unchanged 3D data, ndisplay=3 before plugin construction; mandatory post-activation 2D/3D transitions retained",
            "public_volume_blending": "translucent_no_depth: distinct visible-handle workflow; opaque depth occlusion remains preserved and is valid renderer behavior",
            "plugin_name": manifest.name, "plugin_version": distribution.version,
            "plugin_origin": str(package), "plugin_commit": COMMIT, "plugin_tag_object": TAG,
            "plugin_wheel": str(WHEEL), "plugin_wheel_sha256": WHEEL_SHA,
            "plugin_files_sha256": matched, "plugin_entry_points": entries,
            "registered_render_plane_widget": {"command": widgets["render plane manipulator"], "module": command.__module__, "class": command.__name__},
            "napari_origin": napari.__file__, "napari_version": napari.__version__,
            "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
            "evidence_sha256": {name: sha256(ROOT / "compat/host-environments" / name) for name in PROOFS},
            "fixture_source_sha256": sha256(ROOT / "tools/fixture_napari_render_plane_scheduled.py"),
            "capture_source_sha256": sha256(Path(__file__)),
            "installed": {dist.metadata["Name"]: dist.version for dist in metadata.distributions()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ.setdefault("QT_API", "pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYQT5_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen", "offscreen Qt does not qualify this renderer"
    if not args.worker and args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Every plugin admission attempt requires a fresh directory")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "provenance": None,
                "comparison": {"full_frame_exact": True, "fixed_cpu_projection_landmarks": True,
                               "actual_qt_events": True, "picking": "installed CPU ray/sphere callbacks"},
                "fixtures": {}, "errors": {}}
    if args.worker:
        try:
            assert os.environ.get("PYTHONHASHSEED") == "0", "capture workers require deterministic interpreter hash seed"
            from oracle_capture import provenance
            import vispy
            if args.kind == "upstream":
                vispy.use(gl="gl+")
            origins = provenance(args.kind)
            origins["plugin"] = plugin_provenance()
            manifest["provenance"] = origins
            # Hold the QApplication strongly until this child process exits.
            # Fixture-owned viewers/widgets are closed through public Qt APIs.
            from vispy import app
            qt = app.use_app("pyqt6").native
            qt.setQuitOnLastWindowClosed(False)
            image, commands, shaders, params, extras = render(args.worker)
            assert_landmarks(args.worker, image, params, extras)
            assert commands and shaders
            artifacts = {}
            for key, value, extension in (
                ("rgba", image, ".npy"), ("filtered_glir", commands, ".glir.json"),
                ("expanded_shaders", shaders, ".shaders.json"), ("parameters", params, ".parameters.json"),
                *((key, value, ".npy") for key, value in extras.items()),
            ):
                path = args.output / f"{args.worker}.{key}{extension}"
                if extension == ".npy":
                    np.save(path, value, allow_pickle=False)
                else:
                    write_json(path, value)
                artifacts[key] = {"file": path.name, "sha256": sha256(path)}
            manifest["fixtures"][args.worker] = {"shape": list(image.shape), "parameters": params, "artifacts": artifacts}
            print(f"PASS registered plugin {args.worker}: {image.shape}, independent {args.kind}", flush=True)
        except Exception as exc:
            manifest["errors"][args.worker] = {"type": type(exc).__name__, "error": str(exc)}
            traceback.print_exc()
        write_json(args.output / f"{args.worker}.capture.json", manifest)
        return bool(manifest["errors"])
    for name in args.fixtures or CASES:
        capture = args.output / f"{name}.capture.json"
        # The unchanged plugin builds AxisSet from a Python set. Fix its axis
        # iteration order before interpreter start, for both oracle and fork.
        child_env = dict(os.environ, PYTHONHASHSEED="0")
        child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)),
                                "--kind", args.kind, "--output", str(args.output), "--worker", name],
                               env=child_env, capture_output=True, text=True)
        print(child.stdout, end="", flush=True)
        print(child.stderr, end="", file=sys.stderr, flush=True)
        process = {"exit_code": child.returncode}
        for stream in ("stdout", "stderr"):
            path = args.output / f"{name}.{stream}.log"
            path.write_text(getattr(child, stream), encoding="utf-8")
            process[stream] = {"file": path.name, "sha256": sha256(path)}
        data = json.loads(capture.read_text()) if capture.exists() else {"fixtures": {}, "errors": {}}
        if manifest["provenance"] is None:
            manifest["provenance"] = data.get("provenance")
        if child.returncode == 0 and name in data["fixtures"]:
            record = data["fixtures"][name]
            record.update(process=process, capture={"file": capture.name, "sha256": sha256(capture)})
            manifest["fixtures"][name] = record
        else:
            error = data["errors"].get(name, {"error": f"capture child exited {child.returncode}"})
            if name in data["fixtures"]:
                error["unadmitted_record"] = data["fixtures"][name]
            error["process"] = process
            if capture.exists():
                error["capture"] = {"file": capture.name, "sha256": sha256(capture)}
            manifest["errors"][name] = error
        write_json(args.output / "manifest.json", manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
