# SPDX-License-Identifier: AGPL-3.0-only
"""Source archive metadata must retain complete inputs and actual export exit."""
import hashlib
import json
import shutil
import sys

import pytest

from tools import audit_linux_wheel as audit

COMMIT = '18f362e43525aad9c0434c69608b5dad9089c830'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def linux_wheel_exported_source(tmp_path, monkeypatch):
    root = (tmp_path/'source').absolute()
    names = ['CMakeLists.txt', 'CMakePresets.json', 'pyproject.toml', 'uv.lock',
             'LICENSE', 'LICENSE-BSD', 'LICENSING.md', 'README.md',
             'compat/runtime-package.json', 'cmake/native.cmake', 'cpp/runtime.cpp',
             'src/vispy/__init__.py', 'third_party/licenses/dawn-LICENSE.txt']
    for name in names:
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('retained input '+name+'\n', encoding='utf-8')
    selected = ['CMakeLists.txt', 'CMakePresets.json', 'pyproject.toml', 'uv.lock',
                'LICENSE', 'LICENSE-BSD', 'LICENSING.md', 'README.md',
                'compat/runtime-package.json', 'cmake', 'cpp', 'src', 'third_party']
    repository = tmp_path/'original-repository'
    repository.mkdir()
    receipt = tmp_path/'export.json'
    receipt.write_text(json.dumps(dict(argv=['git', '-C', str(repository), 'archive',
        '--format=tar', COMMIT, '--', *selected], actual_exit=0, child_waited=True, child_pid=42, error=None)))
    original = {name: sha(root/name) for name in names}
    export_map = tmp_path/'export-inventory.json'
    export_map.write_text(json.dumps(dict(commit=COMMIT,
        files={name: value for name,value in original.items() if not name.startswith('third_party/licenses/')})))
    monkeypatch.setattr(audit, 'git_blob_hashes', lambda repository,commit,names:
        ({name:original[name] for name in names}, dict(synthetic_cpu_fixture=True)))
    manifest = tmp_path/'source.json'
    data = dict(schema=1, kind='git-archive-source-inventory', commit=COMMIT,
                files={name: sha(root/name) for name in names},
                export_receipt=dict(path=str(receipt), sha256=sha(receipt)),
                export_inventory=dict(path=str(export_map), sha256=sha(export_map)),
                auditor_files=audit.auditor_identity())
    manifest.write_text(json.dumps(data))
    return root, manifest, receipt, data


def test_archive_source_revision_checks_all_inputs_and_export_receipt(linux_wheel_exported_source):
    root, manifest, receipt, data = linux_wheel_exported_source
    revision, proof = audit.archive_source_revision(root, manifest)
    assert revision == COMMIT
    assert proof['kind']=='verified-git-archive-inventory'
    assert proof['manifest_sha256']==sha(manifest)
    assert proof['export_receipt_sha256']==sha(receipt)
    assert proof['export_inventory_sha256']==data['export_inventory']['sha256']
    assert proof['verified_files']==len(data['files'])
    assert proof['auditor_files']==audit.auditor_identity()



@pytest.mark.parametrize('name', ['cpp/runtime.cpp', 'src/vispy/__init__.py', 'third_party/licenses/dawn-LICENSE.txt'])
def test_changed_production_or_license_input_is_rejected(linux_wheel_exported_source, name):
    root, manifest, _, _ = linux_wheel_exported_source
    (root/name).write_text('changed after export')
    with pytest.raises(AssertionError, match='Exported source changed'):
        audit.archive_source_revision(root, manifest)


@pytest.mark.parametrize('name', ['cpp/runtime.cpp', 'third_party/licenses/dawn-LICENSE.txt', 'README.md', 'compat/runtime-package.json'])
def test_incomplete_source_authority_cannot_label_an_archive(linux_wheel_exported_source, name):
    root, manifest, _, data = linux_wheel_exported_source
    del data['files'][name]
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match='omits production/package inputs|drops exported inputs'):
        audit.archive_source_revision(root, manifest)


@pytest.mark.parametrize('revision', ['main', 'a'*39, 'g'*40])
def test_only_exact_commit_ids_are_accepted(linux_wheel_exported_source, revision):
    root, manifest, _, data = linux_wheel_exported_source
    data['commit'] = revision
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match='Exact source commit required'):
        audit.archive_source_revision(root, manifest)


@pytest.mark.parametrize('field,value', [('actual_exit', 1), ('actual_exit', False),
    ('child_waited', False), ('child_pid', 0), ('error', 'export interrupted')])
def test_failed_or_unawaited_export_cannot_supply_source_revision(linux_wheel_exported_source, field, value):
    root, manifest, receipt, data = linux_wheel_exported_source
    record = json.loads(receipt.read_text())
    record[field] = value
    receipt.write_text(json.dumps(record))
    data['export_receipt']['sha256'] = sha(receipt)
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError):
        audit.archive_source_revision(root, manifest)


def test_changed_export_receipt_is_not_silently_reinterpreted(linux_wheel_exported_source):
    root, manifest, receipt, _ = linux_wheel_exported_source
    receipt.write_text('{}')
    with pytest.raises(AssertionError, match='Export receipt changed'):
        audit.archive_source_revision(root, manifest)


def test_different_exported_commit_is_rejected(linux_wheel_exported_source):
    root, manifest, receipt, data = linux_wheel_exported_source
    record = json.loads(receipt.read_text())
    record['argv'][5] = 'a'*40
    receipt.write_text(json.dumps(record))
    data['export_receipt']['sha256'] = sha(receipt)
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match='Export commit/format mismatch'):
        audit.archive_source_revision(root, manifest)


def test_input_outside_the_recorded_export_selection_is_rejected(linux_wheel_exported_source):
    root, manifest, receipt, data = linux_wheel_exported_source
    record = json.loads(receipt.read_text())
    record['argv'].remove('third_party')
    receipt.write_text(json.dumps(record))
    data['export_receipt']['sha256'] = sha(receipt)
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match='not selected for export'):
        audit.archive_source_revision(root, manifest)


def test_native_build_cannot_be_labeled_as_a_different_valid_source_root(linux_wheel_exported_source, tmp_path):
    root, manifest, _, _ = linux_wheel_exported_source
    other = tmp_path/'different-build-source'
    shutil.copytree(root, other)
    (other/'cpp/runtime.cpp').write_text('different compiled native source')
    with pytest.raises(AssertionError, match='Native build source root differs'):
        audit.verified_source_revision(root, {'CMAKE_HOME_DIRECTORY': str(other)}, manifest)
    assert audit.verified_source_revision(root, {'CMAKE_HOME_DIRECTORY': str(root)}, manifest)[0] == COMMIT


def test_manifest_cannot_reseal_a_new_source_hash_after_build(linux_wheel_exported_source):
    root, manifest, _, data = linux_wheel_exported_source
    (root/'cpp/runtime.cpp').write_text('changed after build')
    data['files']['cpp/runtime.cpp'] = sha(root/'cpp/runtime.cpp')
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match='differs from pre-build export'):
        audit.archive_source_revision(root, manifest)


def test_original_commit_still_binds_even_a_resealed_export_map(linux_wheel_exported_source):
    root, manifest, _, data = linux_wheel_exported_source
    (root/'cpp/runtime.cpp').write_text('changed after build')
    value = sha(root/'cpp/runtime.cpp')
    export_map = type(root)(data['export_inventory']['path'])
    before = json.loads(export_map.read_text())
    before['files']['cpp/runtime.cpp'] = value
    export_map.write_text(json.dumps(before))
    data['export_inventory']['sha256'] = sha(export_map)
    data['files']['cpp/runtime.cpp'] = value
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match='differ from the original commit'):
        audit.archive_source_revision(root, manifest)


def test_changed_external_auditor_dependency_is_rejected(linux_wheel_exported_source, monkeypatch):
    root, manifest, _, _ = linux_wheel_exported_source
    identity = audit.auditor_identity()
    identity[next(iter(identity))] = 'a'*64
    monkeypatch.setattr(audit, 'auditor_identity', lambda: identity)
    with pytest.raises(AssertionError, match='External auditor dependencies changed'):
        audit.archive_source_revision(root, manifest)


@pytest.mark.parametrize('flag', ['--source-root', '--source-manifest'])
def test_archive_cli_options_must_be_paired(flag, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['audit_linux_wheel.py', '--wheel', 'missing.whl',
        '--build-dir', 'missing-build', '--contracts', 'missing-contracts',
        '--output', str(tmp_path/'result.json'), flag, str(tmp_path)])
    with pytest.raises(SystemExit) as stopped:
        audit.main()
    assert stopped.value.code == 2
    assert 'must be supplied together' in capsys.readouterr().err
    assert not (tmp_path/'result.json').exists()


def test_default_checkout_revision_route_remains_explicit(linux_wheel_exported_source, monkeypatch):
    root, _, _, _ = linux_wheel_exported_source
    calls = []
    def checkout(argv, **options):
        calls.append((argv, options))
        return COMMIT+'\n'
    monkeypatch.setattr(audit.subprocess, 'check_output', checkout)
    revision, proof = audit.verified_source_revision(root, {'CMAKE_HOME_DIRECTORY': str(root)})
    assert revision == COMMIT and proof['kind'] == 'git-checkout'
    assert calls == [(['git', 'rev-parse', 'HEAD'], dict(cwd=root, text=True))]


__all__ = ['linux_wheel_exported_source'] + [name for name in globals() if name.startswith('test_')]
