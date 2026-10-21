"""Test-owned PySide2 lifecycle proof is distinct from graphics admission."""

import json
import os
from pathlib import Path
import subprocess
import hashlib

ROOT = Path(__file__).resolve().parents[2]


def test_public_qobject_cleanup_destroys_widgets_before_qapplication():
    # The isolated locked PySide2 interpreter is required, not optional. This
    # creates only ordinary QWidgets with offscreen Qt, never a GL canvas.
    python = ROOT / "build/host-environments/dive-pyside2-cpython310-upstream/Scripts/python.exe"
    assert python.is_file(), "required pinned PySide2 environment is missing"
    code = """
import json
import sys
from PySide2 import QtWidgets
from tools.oracle_dive_pyside2_cleanup_capture import cleanup_qapplication, verify_vispy_record
installed = verify_vispy_record()
assert installed['version'] == '0.17.0' and installed['files_checked'] >= 500
assert len(installed['selected']) == 3
qt = QtWidgets.QApplication([])
qt.setQuitOnLastWindowClosed(False)
first, second = QtWidgets.QWidget(), QtWidgets.QWidget()
first.show()
second.show()
result = cleanup_qapplication(qt)
assert result['top_level_before'].count('QWidget') == 2
assert result['widget_destroyed_signals'].count('QWidget') == 2
assert result['qapplication_destroyed'] and not result['top_level_after']
assert not any(name == '_dawn' or name.endswith('._dawn') for name in sys.modules)
print(json.dumps(result))
"""
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    child = subprocess.run([str(python), "-X", "faulthandler", "-c", code],
                           cwd=ROOT, env=env, capture_output=True, text=True)
    assert child.returncode == 0, (child.returncode, child.stdout, child.stderr)
    record = json.loads(child.stdout)
    assert record["qapplication_destroyed"] and record["top_level_after"] == []
    print("public QObject cleanup, no graphics", child.stdout.strip())


def test_first_pyside2_failed_attempt_retains_nonzero_exit_and_images():
    path = ROOT / "tests/reference/dive-pyside2-opengl/manifest.json"
    manifest = json.loads(path.read_text())
    assert not manifest["fixtures"] and set(manifest["errors"]) == {"scatter", "scatter_edit", "image", "image_edit"}
    for name, error in manifest["errors"].items():
        assert error["process"]["exit_code"] != 0
        for stream in ("stdout", "stderr"):
            artifact = error["process"][stream]
            assert hashlib.sha256((path.parent / artifact["file"]).read_bytes()).hexdigest() == artifact["sha256"]
        if name.startswith("image"):
            record = json.loads((path.parent / f"{name}.capture.json").read_text())["fixtures"][name]
            for artifact in record["artifacts"].values():
                assert hashlib.sha256((path.parent / artifact["file"]).read_bytes()).hexdigest() == artifact["sha256"]
    assert "_marker_funcs" in manifest["errors"]["scatter"]["error"]
