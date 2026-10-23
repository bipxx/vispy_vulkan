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
