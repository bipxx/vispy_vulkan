# SPDX-License-Identifier: AGPL-3.0-only
"""D31: the plugin successor capture writes one fresh packet per napari version and never admits a failed worker."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/oracle_napari_plugin_successor_capture.py'


def load(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location('plugin_successor_capture_regression', TOOL)
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    return capture


def guarded_run(*arguments):
    # Offscreen Qt makes the tool fail before any canvas, should a refusal ever stop working.
    return subprocess.run([sys.executable, '-B', str(TOOL), *arguments], cwd=ROOT, capture_output=True, text=True,
                          env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))


def test_plugin_successor_capture_suites_name_their_modules_and_the_tracked_wheel(monkeypatch):
    capture = load(monkeypatch)
    assert set(capture.SUITES) == {'overlay', 'initialized', 'scheduled'}
    for name, suite in capture.SUITES.items():
        assert (ROOT / 'tests/reference' / suite.base / 'manifest.json').is_file(), name  # the retained packet
        assert (ROOT / suite.retained).is_file() and (ROOT / f'tools/{suite.module}.py').is_file(), name
        assert suite.module == Path(suite.retained).stem + '_successor', name
    assert capture.SUITES['scheduled'].widget[0] == 'render plane manipulator'
    assert {capture.SUITES[name].widget[0] for name in ('overlay', 'initialized')} == {'layer manipulator'}
    assert capture.WHEEL.is_relative_to(ROOT / 'tests/reference/napari-plugin-wheel-inputs')
    assert hashlib.sha256(capture.WHEEL.read_bytes()).hexdigest() == capture.WHEEL_SHA


def test_plugin_successor_capture_refuses_an_existing_packet(tmp_path):
    (tmp_path / 'handles.capture.json').write_text('{}', encoding='utf-8')
    child = guarded_run('--suite', 'overlay', '--kind', 'candidate', '--output', str(tmp_path))
    assert child.returncode != 0 and 'fresh output required' in child.stderr, (child.stdout, child.stderr)
    assert sorted(path.name for path in tmp_path.iterdir()) == ['handles.capture.json']


@pytest.mark.parametrize('arguments, message', [
    (('--kind', 'upstream'), '--host-lock is required for --kind upstream'),
    (('--kind', 'upstream', '--host-lock', 'missing-lock.txt'), 'is not a file'),
    (('--kind', 'candidate'), '--output is required for --kind candidate'),
])
def test_plugin_successor_capture_refuses_bad_arguments_before_any_gui(tmp_path, arguments, message):
    output = ['--output', str(tmp_path / 'packet')] if arguments[1] == 'upstream' else []
    child = guarded_run('--suite', 'scheduled', *arguments, *output)
    assert child.returncode == 2 and message in child.stderr, (child.stdout, child.stderr)
    assert not (tmp_path / 'packet').exists()


def candidate_main(capture, monkeypatch, tmp_path, lock):
    monkeypatch.setattr(capture, 'napari_identity', lambda: ('0.10.0', str(tmp_path / 'napari/__init__.py')))
    monkeypatch.setattr(capture.sys, 'argv', ['capture', '--suite', 'overlay', '--kind', 'candidate',
                                              '--host-lock', str(lock), '--output', str(tmp_path / 'packet')])
    return capture.main()


def test_plugin_successor_capture_refuses_a_lock_that_does_not_describe_the_environment(tmp_path, monkeypatch):
    capture = load(monkeypatch)
    monkeypatch.setattr(capture.subprocess, 'run', lambda *args, **kwargs: pytest.fail('a worker before the lock check'))
    monkeypatch.setattr(capture.metadata, 'version', {'napari': '0.10.0'}.__getitem__)
    lock = tmp_path / 'host.txt'
    lock.write_text('napari==0.11.0\n', encoding='utf-8')
    with pytest.raises(SystemExit, match='does not describe this environment'):
        candidate_main(capture, monkeypatch, tmp_path, lock)
    assert not (tmp_path / 'packet').exists()


@pytest.mark.parametrize('worker_writes_a_record', [False, True])
def test_plugin_successor_parent_admits_nothing_from_a_failed_worker(tmp_path, monkeypatch, worker_writes_a_record):
    capture = load(monkeypatch)
    lock = tmp_path / 'host.txt'
    lock.write_text('# no requirements\n', encoding='utf-8')
    output = tmp_path / 'packet'

    def failed_worker(command, **kwargs):
        assert kwargs['env']['PYTHONHASHSEED'] == '0' and '--host-lock' in command
        name = command[command.index('--worker') + 1]
        if worker_writes_a_record:
            record = {'provenance': {'napari_version': '0.10.0'}, 'fixtures': {name: {'untrusted': True}}, 'errors': {}}
            (output / f'{name}.capture.json').write_text(json.dumps(record), encoding='utf-8')
        return SimpleNamespace(returncode=1, stdout='', stderr='')

    monkeypatch.setattr(capture.subprocess, 'run', failed_worker)
    assert candidate_main(capture, monkeypatch, tmp_path, lock)
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['fixtures'] == {}
    assert set(manifest['errors']) == set(capture.successor('overlay').CASES)
    assert (output / 'host-lock.txt').read_bytes() == lock.read_bytes()


__all__ = [name for name in dir() if name.startswith('test_')]
