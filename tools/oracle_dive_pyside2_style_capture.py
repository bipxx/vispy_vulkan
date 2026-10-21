"""DIVE render references with explicitly scoped public style restoration.

This qualifies rendering and export only. It cannot qualify ordinary unchanged
DIVE application teardown: the pinned host transfers QApplication's borrowed
style to its slider proxy. A public DeferredDelete filter restores test-owned
style ownership only when the fixture deletes DIVEWidget after its screenshot
phase. The original host, fixture, failures and pixel criteria remain intact.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

if __package__:
    from . import oracle_dive_pyside2_cleanup_capture as lifecycle
else:
    import oracle_dive_pyside2_cleanup_capture as lifecycle

ROOT, CASES = lifecycle.ROOT, lifecycle.CASES
sha256, write_json = lifecycle.sha256, lifecycle.write_json
SCOPE = "DIVE rendering/export with public test-owned style restoration during fixture cleanup; ordinary unchanged host teardown and scatter admission remain unresolved"


def install_style_restoration(qt, receiver_name="DIVEWidget"):
    """Restore QApplication's style before a deleting widget proxy owns it."""
    from PySide2 import QtCore, QtWidgets

    record = {"scope": SCOPE, "phase": "DIVEWidget DeferredDelete after the fixture screenshot phase",
              "qt_source": "https://raw.githubusercontent.com/qt/qtbase/v5.15.2/src/widgets/styles/qproxystyle.cpp",
              "actions": []}

    class RestoreApplicationStyle(QtCore.QObject):
        def __init__(self):
            super().__init__(qt)
            self.retained_styles = []

        def eventFilter(self, receiver, event):
            if event.type() == QtCore.QEvent.DeferredDelete and type(receiver).__name__ == receiver_name:
                style = qt.style()
                owner = style.parent()
                if isinstance(owner, QtWidgets.QProxyStyle):
                    name = style.objectName()
                    assert name == "fusion", (name, "fixture requires its fixed Fusion style")
                    style.setParent(None)
                    replacement = qt.setStyle("Fusion")
                    self.retained_styles.append(replacement)
                    assert qt.style().objectName() == name
                    record["actions"].append({"receiver": type(receiver).__name__,
                                               "style_name_before": name, "style_name_after": qt.style().objectName(),
                                               "previous_owner": type(owner).__name__,
                                               "public_apis": ["QObject.setParent(None)", "QApplication.setStyle('Fusion')"]})
            return False

    guard = RestoreApplicationStyle()
    qt.installEventFilter(guard)
    return guard, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("upstream", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", nargs="+", choices=CASES)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ.setdefault("QT_API", "pyside2")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("VISPY_PYSIDE2_SHARE_CONTEXT", "true")
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    if not args.worker and args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Each explicitly scoped DIVE attempt needs a fresh output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.worker:
        import vispy
        from vispy import app
        vispy.use(app="pyside2", **({"gl": "gl+"} if args.kind == "upstream" else {}))
        qt = app.use_app("PySide2").native
        qt.setQuitOnLastWindowClosed(False)
        guard, restoration = install_style_restoration(qt)
        old_argv = sys.argv
        sys.argv = [str(ROOT / "tools/oracle_dive_pyside2_cleanup_capture.py"), "--kind", args.kind,
                    "--output", str(args.output), "--worker", args.worker]
        try:
            result = lifecycle.main()
        finally:
            sys.argv = old_argv
            write_json(args.output / f"{args.worker}.style-restoration.json", restoration)
        assert len(restoration["actions"]) == 1, restoration
        return result
    manifest = {"schema": 1, "provenance": None, "scope": SCOPE,
                "comparison": {"full_frame_exact": True, "landmarks_exact": True,
                               "landmark_domain": "analytic input through host CPU scene transform"},
                "style_runner_sha256": sha256(Path(__file__)),
                "cleanup_runner_sha256": sha256(ROOT / "tools/oracle_dive_pyside2_cleanup_capture.py"),
                "preserved_failed_manifests": {
                    name: sha256(ROOT / f"tests/reference/{name}/manifest.json")
                    for name in ("dive-opengl", "dive-pyside2-opengl", "dive-pyside2-cleanup-opengl")},
                "fixtures": {}, "errors": {}}
    for name in args.fixtures or CASES:
        captured = args.output / f"{name}.capture.json"
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
        artifacts = {}
        for key, suffix in (("capture", "capture"), ("cleanup", "cleanup"), ("style_restoration", "style-restoration")):
            path = args.output / f"{name}.{suffix}.json"
            if path.exists():
                artifacts[key] = {"file": path.name, "sha256": sha256(path)}
        if child.returncode == 0 and name in data["fixtures"] and len(artifacts) == 3:
            record = data["fixtures"][name]
            record.update(process=process, **artifacts)
            manifest["fixtures"][name] = record
        else:
            error = data["errors"].get(name, {"error": f"capture child exited {child.returncode}"})
            if name in data["fixtures"]:
                error["unadmitted_record"] = data["fixtures"][name]
            error.update(process=process, **artifacts)
            manifest["errors"][name] = error
        write_json(args.output / "manifest.json", manifest)
    return bool(manifest["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
