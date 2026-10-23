"""A successful scenario cannot mask a later installed-artifact failure."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('wheel_exists', [False, True])
def test_post_scenario_invalid_wheel_fails_process_and_report(tmp_path, wheel_exists):
    marker = tmp_path / 'scenario-finished.txt'
    script = tmp_path / 'scenario.py'
    script.write_text(f'from pathlib import Path\nPath({str(marker)!r}).write_text("finished")\nraise SystemExit(0)\n')
    wheel = tmp_path / 'invalid.whl'
    if wheel_exists:
        wheel.write_bytes(b'not a wheel archive')
    report = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools/no_opengl/probe.py'),
                             '--scenario', 'script', '--script', str(script), '--wheel', str(wheel),
                             '--output', str(report)], capture_output=True, text=True)
    value = json.loads(report.read_text())
    assert marker.read_text() == 'finished'
    assert result.returncode != 0
    assert value['status'] == 'FAILED_SCENARIO'
    assert ('BadZipFile' if wheel_exists else 'FileNotFoundError') in value['error']


def test_binding_option_is_an_enum_not_a_filesystem_path(tmp_path):
    script = tmp_path / 'scenario.py'
    script.write_text('pass\n')
    report = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/audit_no_opengl.py'), 'run',
                             '--python', sys.executable, '--scenario', 'script', '--script', str(script),
                             '--binding', 'pyqt6', '--gates', 'imports', '--output', str(report)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(report.read_text())
    worker = json.loads(Path(value['worker_report']).read_text())
    assert value['status'] == 'PASS_IMPORT_GATE_ONLY' and worker['binding'] == 'pyqt6'
