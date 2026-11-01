# SPDX-License-Identifier: AGPL-3.0-only
"""D30: the successor capture writes one fresh packet per napari version and never admits a failed worker's record."""
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
TOOL = ROOT / 'tools/oracle_napari_successor_capture.py'


def load(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location('successor_capture_regression', TOOL)
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    return capture


def run_tool(*arguments):
    return subprocess.run([sys.executable, '-B', str(TOOL), *arguments], cwd=ROOT, capture_output=True, text=True)


def test_successor_capture_suites_name_each_retained_and_successor_module(monkeypatch):
    capture = load(monkeypatch)
    assert set(capture.SUITES) == {'scientific', 'layer_controls', 'layer_families', 'vector_layers', 'volume'}
    for name, suite in capture.SUITES.items():
        assert (ROOT / 'tests/reference' / suite.base / 'manifest.json').is_file(), name  # the retained packet
        assert (ROOT / suite.retained).is_file() and (ROOT / f'tools/{suite.module}.py').is_file(), name
        assert suite.module == Path(suite.retained).stem + '_successor', name
    assert capture.SUITES['scientific'].record == 'exact' and capture.SUITES['volume'].record is None
    assert {capture.SUITES[name].record for name in ('layer_controls', 'layer_families', 'vector_layers')} == {'criterion'}


def test_successor_capture_refuses_an_existing_packet(tmp_path):
    (tmp_path / 'translucent.capture.json').write_text('{}', encoding='utf-8')
    child = run_tool('--suite', 'volume', '--kind', 'candidate', '--output', str(tmp_path))
    assert child.returncode != 0 and 'fresh output required' in child.stderr, (child.stdout, child.stderr)
    assert sorted(path.name for path in tmp_path.iterdir()) == ['translucent.capture.json']


def test_successor_upstream_capture_requires_a_host_lock(tmp_path):
    child = run_tool('--suite', 'volume', '--kind', 'upstream', '--output', str(tmp_path / 'packet'))
    assert child.returncode == 2 and '--host-lock' in child.stderr, (child.stdout, child.stderr)
    assert not (tmp_path / 'packet').exists()


@pytest.mark.parametrize('worker_writes_a_record', [False, True])
def test_successor_worker_failure_cannot_admit_a_partial_record(tmp_path, monkeypatch, worker_writes_a_record):
    capture = load(monkeypatch)
    monkeypatch.setattr(capture, 'provenance', lambda kind: {})
    # CI installs no napari: everything the parent reads about it comes through napari_identity.
    monkeypatch.setattr(capture, 'napari_identity', lambda: ('0.10.0', str(tmp_path / 'napari/__init__.py')))
    monkeypatch.setattr(capture, 'host_provenance', lambda *args: {'napari_version': args[1]})
    monkeypatch.setattr(capture.metadata, 'version', lambda name: pytest.fail(f'read {name} metadata directly'))
    output = tmp_path / 'packet'

    def failed_worker(command, **kwargs):
        name = command[command.index('--worker') + 1]
        if worker_writes_a_record:
            record = {'fixtures': {name: {'untrusted': True}}, 'errors': {}}
            (output / f'{name}.capture.json').write_text(json.dumps(record), encoding='utf-8')
        return SimpleNamespace(returncode=1, stdout='', stderr='')

    monkeypatch.setattr(capture.subprocess, 'run', failed_worker)
    monkeypatch.setattr(capture.sys, 'argv', ['capture', '--suite', 'volume', '--kind', 'candidate',
                                              '--output', str(output)])
    assert capture.main() == 1
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['fixtures'] == {}
    assert set(manifest['errors']) == set(capture.successor('volume').CASES)


def test_successor_host_provenance_records_any_napari_version(tmp_path, monkeypatch):
    capture = load(monkeypatch)
    package = tmp_path / 'site-packages/napari'
    for name in capture.SUITES['volume'].host_sources:
        (package / name).parent.mkdir(parents=True, exist_ok=True)
        (package / name).write_text(name, encoding='utf-8')
    lock = tmp_path / 'host.txt'
    lock.write_text('napari==0.11.0\n', encoding='utf-8')
    record = capture.host_provenance('volume', '0.11.0', str(package / '__init__.py'), lock)
    assert record['suite'] == 'volume' and record['napari_version'] == '0.11.0'
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()  # noqa: E731
    assert record['fixture_source_sha256'] == digest(ROOT / 'tools/fixture_napari_volume_successor.py')
    assert record['retained_fixture_source_sha256'] == digest(ROOT / 'tools/fixture_napari_volume.py')
    assert record['capture_source_sha256'] == digest(TOOL)
    assert record['host_lock'] == {'file': lock.resolve().as_posix(), 'sha256': digest(lock), 'snapshot': 'host-lock.txt'}
    inside = capture.host_provenance('volume', '0.11.0', str(package / '__init__.py'), ROOT / 'pyproject.toml')
    assert inside['host_lock'] == {'file': 'pyproject.toml', 'sha256': digest(ROOT / 'pyproject.toml'),
                                   'snapshot': 'host-lock.txt'}
    assert record['host_source_sha256'] == {name: digest(package / name) for name in capture.SUITES['volume'].host_sources}
    assert 'numpy' in {name.lower() for name in record['installed']}
    plain = capture.host_provenance('layer_controls', '0.10.0', str(package / '__init__.py'), None)
    assert plain['host_lock'] is None and 'host_source_sha256' not in plain


def guarded_run(*arguments):
    # Offscreen Qt makes the tool fail before any canvas, should a refusal ever stop working.
    return subprocess.run([sys.executable, '-B', str(TOOL), *arguments], cwd=ROOT, capture_output=True, text=True,
                          env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))


def test_successor_candidate_capture_never_writes_into_the_packet():
    child = guarded_run('--suite', 'volume', '--kind', 'candidate')
    assert child.returncode == 2 and '--output is required for --kind candidate' in child.stderr, child.stderr


def test_successor_capture_requires_an_existing_host_lock(tmp_path):
    child = guarded_run('--suite', 'volume', '--kind', 'upstream', '--host-lock', str(tmp_path / 'missing.txt'),
                        '--output', str(tmp_path / 'packet'))
    assert child.returncode == 2 and 'is not a file' in child.stderr, child.stderr
    assert not (tmp_path / 'packet').exists()


def candidate_main(capture, monkeypatch, tmp_path, lock):
    monkeypatch.setattr(capture, 'napari_identity', lambda: ('0.10.0', str(tmp_path / 'napari/__init__.py')))
    monkeypatch.setattr(capture.sys, 'argv', ['capture', '--suite', 'layer_controls', '--kind', 'candidate',
                                              '--host-lock', str(lock), '--output', str(tmp_path / 'packet')])
    return capture.main()


def test_successor_capture_refuses_a_lock_that_does_not_describe_the_environment(tmp_path, monkeypatch):
    capture = load(monkeypatch)
    monkeypatch.setattr(capture, 'provenance', lambda kind: pytest.fail('GUI work before the lock check'))
    monkeypatch.setattr(capture.metadata, 'version', {'napari': '0.10.0'}.__getitem__)
    lock = tmp_path / 'host.txt'
    lock.write_text('napari==0.11.0\n', encoding='utf-8')
    with pytest.raises(SystemExit, match='does not describe this environment'):
        candidate_main(capture, monkeypatch, tmp_path, lock)
    assert not (tmp_path / 'packet').exists()


def test_successor_capture_snapshots_its_host_lock(tmp_path, monkeypatch):
    capture = load(monkeypatch)
    monkeypatch.setattr(capture, 'provenance', lambda kind: {})
    monkeypatch.setattr(capture.subprocess, 'run', lambda command, **kwargs: SimpleNamespace(
        returncode=1, stdout='', stderr=''))
    lock = tmp_path / 'host.txt'
    lock.write_text('# no requirements\n', encoding='utf-8')
    assert candidate_main(capture, monkeypatch, tmp_path, lock) == 1
    packet = tmp_path / 'packet'
    assert (packet / 'host-lock.txt').read_bytes() == lock.read_bytes()
    recorded = json.loads((packet / 'manifest.json').read_text(encoding='utf-8'))['provenance']['host_lock']
    assert recorded == {'file': lock.resolve().as_posix(), 'sha256': hashlib.sha256(lock.read_bytes()).hexdigest(),
                        'snapshot': 'host-lock.txt'}


def test_image_successor_freeze_snapshots_its_host_lock(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location('image_successor_freeze',
                                                  ROOT / 'tools/oracle_image_extensions_successor_capture.py')
    image = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(image)
    monkeypatch.setattr(image.metadata, 'version', {'napari': '0.10.0'}.__getitem__)
    lock = tmp_path / 'host.txt'
    lock.write_text('napari==0.10.0\n', encoding='utf-8')
    payload = image.freeze_authoring(tmp_path / 'packet', lock)
    assert payload['napari_version'] == '0.10.0'
    assert payload['installed_upstream_lock'] == {'file': lock.resolve().as_posix(),
        'sha256': hashlib.sha256(lock.read_bytes()).hexdigest(), 'snapshot': 'host-lock.txt'}
    assert (tmp_path / 'packet/host-lock.txt').read_bytes() == lock.read_bytes()
    assert sorted(path.name for path in (tmp_path / 'packet/authoring-sources').iterdir()) == sorted(
        Path(source).name for source in image.SOURCES)


@pytest.mark.parametrize('arguments, message', [
    (('--freeze-authoring',), '--host-lock is required to freeze'),
    (('--kind', 'upstream'), '--host-lock is required for --kind upstream'),
])
def test_image_successor_capture_requires_a_host_lock(tmp_path, arguments, message):
    tool = ROOT / 'tools/oracle_image_extensions_successor_capture.py'
    child = subprocess.run([sys.executable, '-B', str(tool), *arguments, '--output', str(tmp_path / 'packet')],
                           cwd=ROOT, capture_output=True, text=True)
    assert child.returncode == 2 and message in child.stderr, (child.stdout, child.stderr)
    assert not (tmp_path / 'packet').exists()


def test_image_successor_candidate_capture_never_writes_into_the_packet():
    tool = ROOT / 'tools/oracle_image_extensions_successor_capture.py'
    child = subprocess.run([sys.executable, '-B', str(tool), '--kind', 'candidate'], cwd=ROOT,
                           capture_output=True, text=True)
    assert child.returncode == 2 and '--output is required for --kind candidate' in child.stderr, child.stderr


__all__ = [name for name in dir() if name.startswith('test_')]
