"""A successful scenario cannot mask a later installed-artifact failure."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _failure_reports(report):
    """Keep the actual controller/worker cause in CI's retained pytest report."""
    details = {}
    keys = ('status', 'process_exit', 'worker_status', 'error', 'cleanup_error',
            'workflow', 'gates', 'forbidden_modules_present')
    for path in (report, report.with_suffix('.worker.json')):
        if path.is_file():
            value = json.loads(path.read_text())
            details[path.name] = {key: value[key] for key in keys if key in value}
    log = report.with_suffix('.process.log')
    if log.is_file():
        details['process_log_tail'] = log.read_bytes()[-8192:].decode('utf-8', errors='replace')
    return json.dumps(details, indent=2)


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
                             '--binding', 'pyqt6', '--gates', 'imports', '--output', str(report),
                             '--workflow-id', 'tk-state', '--covered-feature', 'app.canvas', '--', '--literal', '--', 'value'],
                            capture_output=True, text=True)
    value = json.loads(report.read_text())
    worker = json.loads(Path(value['worker_report']).read_text())
    assert worker['status'] == 'PASS_SCENARIO' and worker['binding'] == 'pyqt6', _failure_reports(report)
    assert value['process_exit'] == 0 and not worker.get('error') and not worker.get('cleanup_error')
    # This CPU test checks CLI binding/argument plumbing, not platform admission.
    # A Python host can preload a GL framework before the script (macOS does).
    # Preserve that native failure; never turn it into an import-only pass.
    violations = value['gates']['violations']
    if violations:
        assert all(item['kind'] == 'native_load' for item in violations), _failure_reports(report)
        assert value['gates']['no_gl_loads'] == 'FAIL'
        assert value['status'] == 'FAIL' and result.returncode == 1, _failure_reports(report)
    else:
        assert value['status'] == 'PASS_IMPORT_GATE_ONLY' and result.returncode == 0, _failure_reports(report)
    assert value['workflow'] == worker['workflow']
    assert value['workflow']['id'] == 'tk-state' and value['workflow']['features'] == ['app.canvas']
    assert value['workflow']['arguments'] == ['--literal', '--', 'value']
    assert value['workflow']['script_sha256'] == hashlib.sha256(script.read_bytes()).hexdigest()
    assert value['worker_report_sha256'] == hashlib.sha256(Path(value['worker_report']).read_bytes()).hexdigest()


def test_probe_records_actual_script_arguments_without_dropping_literal_boundaries(tmp_path):
    marker = tmp_path / 'argv.json'
    script = tmp_path / 'scenario.py'
    script.write_text('import sys, json\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\n')
    report = tmp_path / 'worker.json'
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools/no_opengl/probe.py'),
                             '--scenario', 'script', '--script', str(script), '--workflow-id', 'tk-state',
                             '--covered-feature', 'app.canvas', '--output', str(report), '--', str(marker), '--', '--literal', ''],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(marker.read_text()) == ['--', '--literal', '']
    worker = json.loads(report.read_text())
    assert worker['workflow']['arguments'] == [str(marker), '--', '--literal', '']


def test_probe_cannot_pass_when_the_observed_script_changes_during_execution(tmp_path):
    script = tmp_path / 'scenario.py'
    script.write_text('from pathlib import Path\nPath(__file__).write_text("# Changed during scenario\\n")\n')
    report = tmp_path / 'worker.json'
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools/no_opengl/probe.py'),
                             '--scenario', 'script', '--script', str(script), '--output', str(report)],
                            capture_output=True, text=True)
    assert result.returncode == 1
    worker = json.loads(report.read_text())
    assert worker['status'] == 'FAILED_SCENARIO' and 'script changed during execution' in worker['error']
