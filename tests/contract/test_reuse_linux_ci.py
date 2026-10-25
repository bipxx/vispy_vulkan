# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded reuse transport and consumer controls; no artifact admission."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from tools import reuse_linux_ci as reuse


def archive(tmp_path, members):
    path = tmp_path/'original.zip'
    with zipfile.ZipFile(path, 'w') as stream:
        for name, data in members:
            stream.writestr(name, data)
    pin = copy.deepcopy(reuse.read(reuse.REFERENCE))
    pin.update(artifact_bytes=path.stat().st_size, artifact_sha256=reuse.digest(path),
               max_expanded_bytes=1024, recovered_members=[])
    return path, pin


def test_reference_is_closed_and_preserves_production_identity():
    pin = reuse.read(reuse.REFERENCE)
    assert reuse.reference(copy.deepcopy(pin)) == pin
    for key, value in [('schema', True), ('repository', 'other/repo'),
                       ('artifact_bytes', 0), ('production_sha256', 'x'*64)]:
        changed = {**pin, key: value}
        with pytest.raises(ValueError): reuse.reference(changed)
    with pytest.raises(ValueError): reuse.reference({**pin, 'fallback_build': True})


def test_transport_reuses_retained_bytes_without_copying(tmp_path):
    path, pin = archive(tmp_path, [('runs/original/payload.log', b'original')])
    workspace = tmp_path/'workspace'
    inventory = reuse.import_archive(path, pin, workspace)
    before = sorted(p.relative_to(workspace) for p in workspace.rglob('*') if p.is_file())
    again = reuse.import_archive(path, pin, workspace, available=inventory['members'])
    assert again == inventory
    assert before == sorted(p.relative_to(workspace) for p in workspace.rglob('*') if p.is_file())
    row = inventory['members'][0]
    (workspace/row['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        reuse.import_archive(path, pin, workspace, available=inventory['members'])


@pytest.mark.parametrize('mutation', ['digest', 'size', 'expanded'])
def test_transport_limits_fail_before_retention(tmp_path, mutation):
    path, pin = archive(tmp_path, [('payload.log', b'original')])
    if mutation == 'digest': pin['artifact_sha256'] = '0'*64
    elif mutation == 'size': pin['artifact_bytes'] += 1
    else: pin['max_expanded_bytes'] = 1
    workspace = tmp_path/'workspace'
    with pytest.raises(ValueError): reuse.import_archive(path, pin, workspace)
    assert not workspace.exists()


@pytest.mark.parametrize('members', [
    [('same', b'a'), ('same', b'b')],
    [('../payload', b'a')], [('/payload', b'a')],
])
def test_transport_rejects_ambiguous_members(tmp_path, members):
    path, pin = archive(tmp_path, members)
    with pytest.raises(ValueError): reuse.import_archive(path, pin, tmp_path/'workspace')


def test_exact_byte_recovery_keeps_original_archive_unchanged(tmp_path):
    path, pin = archive(tmp_path, [('payload', b'original')])
    original = path.read_bytes()
    pin['recovered_members'] = [dict(member='runs/original/wheels/.gitignore',
                                    sha256=hashlib.sha256(b'*').hexdigest(), data_hex='2a')]
    workspace = tmp_path/'workspace'
    inventory = reuse.import_archive(path, pin, workspace)
    assert (workspace/inventory['members'][-1]['path']).read_bytes() == b'*'
    assert path.read_bytes() == original
    pin['recovered_members'][0]['sha256'] = '0'*64
    with pytest.raises(ValueError, match='recovery'):
        reuse.import_archive(path, pin, workspace)


def test_install_reference_uses_current_retained_wheel_and_hash(tmp_path):
    wheel = tmp_path/'retained wheel.whl'; wheel.write_bytes(b'explicit synthetic wheel bytes')
    path = reuse.wheel_requirement(wheel, tmp_path)
    assert path.read_text() == 'vispy @ '+wheel.as_uri()+' --hash=sha256:'+reuse.digest(wheel)+'\n'
    assert reuse.wheel_requirement(wheel, tmp_path) == path
    wheel.write_bytes(b'changed')
    with pytest.raises(ValueError, match='differs'): reuse.wheel_requirement(wheel, tmp_path)


def test_reuse_reports_are_immutable(tmp_path):
    path = tmp_path/'result.json'
    reuse.write(path, {'admitted': False})
    reuse.write(path, {'admitted': False})
    with pytest.raises(ValueError, match='differs'): reuse.write(path, {'admitted': True})


@pytest.mark.parametrize('mutation', [None, 'native', 'harness', 'python', 'license', 'wheel'])
def test_current_input_changes_stop_reuse_before_consumer_install(tmp_path, monkeypatch, mutation):
    # This isolates input selection. Full provenance semantics are independently
    # exercised by the original-record golden and native capture rejection suite.
    from tools import qualification_native
    import sys
    sys.path.insert(0, str(reuse.ROOT/'cmake'))
    import runtime_package
    source = tmp_path/'source'; workspace = tmp_path/'workspace'
    workspace.mkdir()
    files = {'cpp/renderer.cpp': b'native', 'tests/contract.cpp': b'harness',
             'src/vispy/__init__.py': b'python', 'LICENSE': b'license'}
    for name, data in files.items():
        path = source/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))
    schema = source/reuse.native.SCHEMA; schema.parent.mkdir(parents=True); schema.write_bytes(b'{}')
    before = {name: reuse.digest(source/name) for name in files}
    save(source/'compat/candidates/tk-state-resource-1/candidate.json',
         {'runtime_inputs': {'path': 'runtime.json'}})
    save(source/'runtime.json', {'python': [{'file': {'path': 'src/vispy/__init__.py',
         'sha256': before['src/vispy/__init__.py']}}],
         'licenses': [{'path': 'LICENSE', 'sha256': before['LICENSE']}]})
    save(workspace/'state.json', {'evidence': '/original/evidence'})
    save(workspace/'before.json', before)
    save(workspace/'audit.json', {'wheel': '/original/wheel.whl'})
    (workspace/'wheel.whl').write_bytes(b'explicit synthetic wheel')
    capture = {'state': {'path': 'state.json'}, 'files': [
        {'origin': '/original/evidence/source-before.json', 'file': {'path': 'before.json'}},
        {'origin': '/original/evidence/archive.json', 'file': {'path': 'audit.json'}},
        {'origin': '/original/wheel.whl', 'file': {'path': 'wheel.whl'}}]}
    monkeypatch.setattr(reuse.native, 'capture_from_inventory', lambda *a: capture)
    monkeypatch.setattr(qualification_native, 'source_inputs', lambda *a: {
        name: before[name] for name in ('cpp/renderer.cpp', 'tests/contract.cpp')})
    monkeypatch.setattr(reuse.native, 'production_inputs', lambda *a: {})
    checks = []
    def validate(*args):
        checks.append('native')
        return {'production_sha256': 'a'*64, 'artifact_admitted': False}, {}
    monkeypatch.setattr(reuse.native, 'validate_capture', validate)
    def wheel_check(*args, **kwargs):
        checks.append('wheel')
        if mutation == 'wheel': raise ValueError('Changed shipped package')
    monkeypatch.setattr(runtime_package, 'wheel_package_hashes', wheel_check)
    changed = dict(native='cpp/renderer.cpp', harness='tests/contract.cpp',
                   python='src/vispy/__init__.py', license='LICENSE')
    if mutation in changed: (source/changed[mutation]).write_bytes(b'changed')
    if mutation:
        with pytest.raises(ValueError, match='Changed'):
            reuse.validate_inputs({}, {'production_sha256': 'a'*64}, source, workspace)
        assert checks == (['native', 'wheel'] if mutation == 'wheel' else [])
    else:
        result = reuse.validate_inputs({}, {'production_sha256': 'a'*64}, source, workspace)
        assert checks == ['native', 'wheel']
        assert result['native']['artifact_admitted'] is False



def test_replay_preserves_equivalent_existing_receipt_bytes(tmp_path):
    path = tmp_path/'result.json'
    original = b'{\r\n  "admitted": false\r\n}\r\n'
    path.write_bytes(original)
    reuse.write(path, {'admitted': False})
    assert path.read_bytes() == original


def test_candidate_rejection_still_retains_original_transport(tmp_path, monkeypatch):
    import sys
    workspace = tmp_path/'workspace'; workspace.mkdir()
    retained = workspace/'build/artifacts/original/source-inputs.zip'
    retained.parent.mkdir(parents=True); retained.write_bytes(b'original source fixture')
    inventory = dict(run_id=123, artifact_id=456, members=[dict(member='runs/original/source-inputs.zip',
        path=retained.relative_to(workspace).as_posix(), sha256=reuse.digest(retained))])
    class Context:
        def __init__(self, *args): pass
        def scratch(self, run): return workspace/'build/work'/run
        def marker(self, *args): pass
        def check_capacity(self, *args): pass
    monkeypatch.setattr(reuse, 'Context', Context)
    monkeypatch.setattr(reuse, 'import_archive', lambda *a, **kw: inventory)
    def reject(*args): raise ValueError('Changed native input')
    monkeypatch.setattr(reuse, 'validate_inputs', reject)
    monkeypatch.setattr(sys, 'argv', ['reuse', '--workspace', str(workspace),
        '--run-id', 'unit', '--archive', 'explicit-synthetic-transport', '--metadata-only'])
    with pytest.raises(ValueError, match='Changed native input'): reuse.main()
    record = reuse.read(workspace/'build/runs/unit/reuse-transport-inputs.json')
    assert record['artifact_admitted'] is False
    assert record['retained'] == [dict(path=str(retained), sha256=reuse.digest(retained),
        roles=['evidence', 'repro', 'source', 'licenses'])]
