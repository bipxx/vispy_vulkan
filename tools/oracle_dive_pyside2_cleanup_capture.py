"""A separate DIVE/PySide2 attempt with explicit test-owned QObject cleanup.

The original fixture, pins, landmark criteria and failed captures are retained
unchanged. Qt's public deferred-deletion APIs run while QApplication and Qt's
Python modules are still strongly owned. Child exit status remains mandatory.
"""

from __future__ import annotations

import argparse
import base64
import csv
import gc
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

CASES = ("scatter", "scatter_edit", "image", "image_edit")
QT_DOCUMENTATION = [
    "https://doc.qt.io/archives/qt-5.15/qobject.html#deleteLater",
    "https://doc.qt.io/archives/qt-5.15/qcoreapplication.html#sendPostedEvents",
    "https://doc.qt.io/archives/qt-5.15/qapplication.html#topLevelWidgets",
]


def verify_vispy_record():
    """Verify every installed package file, including the actual Qt backend."""
    distribution = metadata.distribution("vispy")
    path = next(distribution.locate_file(file) for file in distribution.files
                if str(file).replace("\\", "/").endswith(".dist-info/RECORD"))
    report = {"version": distribution.version, "record_origin": str(path),
              "record_sha256": sha256(path), "files_checked": 0, "selected": {}}
    for relative, digest, _size in csv.reader(path.read_text().splitlines()):
        if not digest or not relative.startswith("vispy/"):
            continue
        installed = distribution.locate_file(relative)
        algorithm, expected = digest.split("=", 1)
        actual = base64.urlsafe_b64encode(hashlib.new(algorithm, installed.read_bytes()).digest()).decode().rstrip("=")
        assert actual == expected, (relative, "installed file differs from wheel RECORD")
        report["files_checked"] += 1
        if relative in ("vispy/app/backends/_qt.py", "vispy/app/backends/_pyside2.py", "vispy/visuals/markers.py"):
            report["selected"][relative] = {"origin": str(installed), "sha256": sha256(installed)}
    assert report["files_checked"] >= 500 and len(report["selected"]) == 3
    return report


def cleanup_qapplication(qt):
    """Delete test-owned top-level QObjects before destroying QApplication."""
    from PySide2 import QtCore, QtWidgets

    assert QtWidgets.QApplication.instance() is qt
    record = {"documentation": QT_DOCUMENTATION, "top_level_before": [],
              "widget_destroyed_signals": [], "qapplication_destroyed": False,
              "phases": []}
    # A callback keeps plain data, never the QObject being destroyed.
    qt.destroyed.connect(lambda *_: record.__setitem__("qapplication_destroyed", True))
    widgets = list(qt.topLevelWidgets())
    for widget in widgets:
        name = type(widget).__name__
        record["top_level_before"].append(name)
        widget.destroyed.connect(lambda *_, label=name: record["widget_destroyed_signals"].append(label))
        if hasattr(widget, "set_animation_state"):
            widget.set_animation_state(False)
        widget.close()
        widget.deleteLater()
    record["phases"].append("close/deleteLater all remaining public topLevelWidgets")
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qt.processEvents()
    widgets.clear()
    gc.collect()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qt.processEvents()
    record["phases"].append("flush DeferredDelete and collect Python cycles while QApplication is alive")
    record["top_level_after"] = [type(widget).__name__ for widget in qt.topLevelWidgets()]
    assert not record["top_level_after"], record
    qt.quit()
    qt.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(qt, QtCore.QEvent.DeferredDelete)
    record["phases"].append("quit and deleteLater QApplication last")
    assert record["qapplication_destroyed"], record
    assert QtWidgets.QApplication.instance() is None
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker and args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Existing DIVE attempts are immutable; use a fresh output directory")
    os.environ.setdefault("QT_API", "pyside2")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYSIDE2_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    args.output.mkdir(parents=True, exist_ok=True)
    if args.worker:
        installed_record = verify_vispy_record()
        import vispy
        from vispy import app
        vispy.use(app="pyside2", **({"gl": "gl+"} if args.kind == "upstream" else {}))
        # The backend sets sharing attributes before creating QApplication.
        qt = app.use_app("PySide2").native
        qt.setQuitOnLastWindowClosed(False)
        if __package__:
            from . import oracle_dive_pyside2_capture as original
        else:
            import oracle_dive_pyside2_capture as original
        old_argv = sys.argv
        sys.argv = [str(ROOT / "tools/oracle_dive_pyside2_capture.py"), "--kind", args.kind,
                    "--output", str(args.output), "--worker", args.worker]
        try:
            code = original.main()
        finally:
            sys.argv = old_argv
            record = cleanup_qapplication(qt)
            record["installed_vispy_record_integrity"] = installed_record
            write_json(args.output / f"{args.worker}.cleanup.json", record)
            print(f"CLEANUP {args.worker}: all test-owned widgets and QApplication destroyed", flush=True)
        return code
    # Provenance comes from a real graphics child and retains all original
    # source/environment checks; this parent creates no Qt or graphics device.
    manifest = {"schema": 1, "provenance": None,
                "comparison": {"full_frame_exact": True, "landmarks_exact": True,
                               "landmark_domain": "analytic input through host CPU scene transform"},
                "cleanup_runner_sha256": sha256(Path(__file__)),
                "original_failed_manifest_sha256": sha256(ROOT / "tests/reference/dive-pyside2-opengl/manifest.json"),
                "fixtures": {}, "errors": {}}
    for name in args.fixtures or CASES:
        captured = args.output / f"{name}.capture.json"
        assert not captured.exists()
        child = subprocess.run([sys.executable, "-X", "faulthandler", str(Path(__file__)),
                                "--kind", args.kind, "--output", str(args.output), "--worker", name],
                               capture_output=True, text=True)
        print(child.stdout, end="", flush=True)
        print(child.stderr, end="", file=sys.stderr, flush=True)
        process = {"exit_code": child.returncode}
        for stream in ("stdout", "stderr"):
            path = args.output / f"{name}.{stream}.log"
            path.write_text(getattr(child, stream), encoding="utf-8")
            process[stream] = {"file": path.name, "sha256": sha256(path)}
        data = json.loads(captured.read_text()) if captured.exists() else {"fixtures": {}, "errors": {}}
        if manifest["provenance"] is None and "provenance" in data:
            manifest["provenance"] = data["provenance"]
        cleanup_path = args.output / f"{name}.cleanup.json"
        cleanup = {"file": cleanup_path.name, "sha256": sha256(cleanup_path)} if cleanup_path.exists() else None
        if child.returncode == 0 and name in data["fixtures"] and cleanup is not None:
            record = data["fixtures"][name]
            record.update(process=process, cleanup=cleanup,
                          capture={"file": captured.name, "sha256": sha256(captured)})
            manifest["fixtures"][name] = record
        else:
            error = data["errors"].get(name, {"error": f"capture child exited {child.returncode}"})
            if name in data["fixtures"]:
                error["unadmitted_record"] = data["fixtures"][name]
            if captured.exists():
                error["capture"] = {"file": captured.name, "sha256": sha256(captured)}
            if cleanup:
                error["cleanup"] = cleanup
            error["process"] = process
            manifest["errors"][name] = error
        write_json(args.output / "manifest.json", manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
