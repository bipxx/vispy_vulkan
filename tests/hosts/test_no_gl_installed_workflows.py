# SPDX-License-Identifier: AGPL-3.0-only
"""Real installed-artifact workflows; the external audit supplies noGL gates."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.gpu
@pytest.mark.wheel
@pytest.mark.parametrize('scenario', ('qwidget', 'napari', 'glue', 'threedee'))
def test_installed_artifact_host_lifecycle(scenario, tmp_path):
    # Missing wheel/environment is a failed qualification, not a skipped row.
    wheel = Path(os.environ['VISPY_HOST_PROBE_WHEEL']).resolve(strict=True)
    output = tmp_path / scenario
    prefix = 'VISPY_HOST_PROBE_' + scenario.upper()
    python = os.environ.get(prefix + '_PYTHON',
                            os.environ.get('VISPY_HOST_PROBE_PYTHON', sys.executable))
    command = [python, '-I', '-B',
               str(ROOT / 'tools/no_opengl_host_probe.py'), '--scenario', scenario,
               '--binding', os.environ.get('QT_API', 'pyqt6'),
               '--wheel', str(wheel), '--output', str(output)]
    if os.environ.get('VISPY_HOST_PROBE_ALLOW_SOFTWARE') == '1':
        command.append('--allow-software')
    if scenario != 'qwidget':
        host_wheels = os.environ.get(prefix + '_HOST_WHEELS',
                                    os.environ.get('VISPY_HOST_PROBE_HOST_WHEELS'))
        assert host_wheels, 'Exact host wheels are required for ' + scenario
        for host_wheel in host_wheels.split(os.pathsep):
            command.extend(['--host-wheel', str(Path(host_wheel).resolve(strict=True))])
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    report_file = output / 'functional.json'
    detail = report_file.read_text(encoding='utf-8') if report_file.exists() else ''
    assert result.returncode == 0, result.stdout + result.stderr + detail
    report = json.loads(detail)
    assert report['status'] == 'passed'
    assert report['frames']
    assert all(stage['status'] == 'passed' for stage in report['stages'])
    assert report['artifact']['wheel'] == str(wheel)
