# SPDX-License-Identifier: AGPL-3.0-only
"""In-memory synthetic wheels prove archive joins, never native admission."""
import base64
from copy import deepcopy
import csv
import hashlib
import io
import json
import struct
import zipfile

import pytest

from tools import qualification_artifact as qa


def sample(platform='win32'):
    manifest = {'schema': 1, 'profile': 'dawn-no-opengl-runtime', 'files': ['__init__.py'],
                'excluded_files': [], 'compatibility_aliases': [],
                'notice_files': ['LICENSE', 'LICENSE-BSD', 'LICENSING.md', 'vispy-LICENSE.txt'],
                'generated_manifest_member': qa.runtime_package.MEMBER}
    manifest_data = json.dumps(manifest).encode()
    pure = {'vispy/__init__.py': b'# Synthetic source\n', qa.runtime_package.MEMBER: manifest_data}
    notices = {'vispy/_licenses/' + name: ('original ' + name).encode() for name in manifest['notice_files']}
    licenses = {qa.DIST + '/licenses/' + name: notices['vispy/_licenses/' + name]
                for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md')}
    suffix = '.cp312-win_amd64.pyd' if platform == 'win32' else '.cpython-312-x86_64-linux-gnu.so'
    names = qa.runtime_package.expected_members(manifest, suffix=suffix, platform=platform) - set(pure) - set(notices)
    binary = bytearray(512)
    if platform == 'win32':
        binary[:2] = b'MZ'
        struct.pack_into('<I', binary, 60, 64)
        binary[64:68] = b'PE\0\0'
        struct.pack_into('<HHIIIHH', binary, 68, 0x8664, 0, 0, 0, 0, 240, 0)
        struct.pack_into('<H', binary, 88, 0x20b)
    else:
        binary[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', binary, 18, 62)
    native = {name: b'{}' if name.endswith('.json') else bytes(binary) for name in names}
    tag = 'cp312-cp312-' + ('win_amd64' if platform == 'win32' else 'linux_x86_64')
    entries = {**pure, **notices, **licenses, **native,
               qa.DIST + '/METADATA': b'Name: vispy\nVersion: 0.17.0+vulkan.1\nLicense-Expression: AGPL-3.0-only\nDescription-Content-Type: text/markdown\n\n',
               qa.DIST + '/WHEEL': ('Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: ' + tag + '\n\n').encode()}
    inputs = {'manifest_data': manifest_data, 'pure_hashes': {n: qa.sha(d) for n, d in pure.items()},
              'notices': notices, 'distribution_licenses': licenses,
              'native_hashes': {n: qa.sha(d) for n, d in native.items()},
              'suffix': suffix, 'platform': platform, 'tag': tag}
    return entries, inputs


def wheel_bytes(entries, change_record=None):
    entries = dict(entries)
    rows = []
    for name, data in sorted(entries.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        rows.append([name, 'sha256=' + digest, str(len(data))])
    rows.append([qa.DIST + '/RECORD', '', ''])
    if change_record:
        change_record(rows)
    record = io.StringIO(newline='')
    csv.writer(record).writerows(rows)
    entries[qa.DIST + '/RECORD'] = record.getvalue().encode()
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        for name, data in entries.items(): archive.writestr(name, data)
    return result.getvalue()


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_complete_synthetic_archive_never_admits_native_or_installed_origin(platform):
    entries, inputs = sample(platform)
    result = qa.audit_archive(wheel_bytes(entries), **inputs)
    assert result['status'] == 'PASS_EXACT_ARCHIVE_PREREQUISITE'
    assert not result['artifact_admitted'] and not result['producer_admitted']
    assert not result['installed_origin_verified']
    assert result['package_hashes'] == {**inputs['pure_hashes'], **inputs['native_hashes'],
                                       **{n: qa.sha(d) for n, d in inputs['notices'].items()}}


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_correctly_hashed_wrong_native_architecture_still_rejects(platform):
    entries, inputs = sample(platform)
    name = next(n for n in inputs['native_hashes'] if not n.endswith('.json'))
    data = bytearray(entries[name])
    struct.pack_into('<H', data, 68 if platform == 'win32' else 18, 0xAA64 if platform == 'win32' else 183)
    entries[name] = bytes(data)
    inputs['native_hashes'][name] = qa.sha(entries[name])
    with pytest.raises(qa.InventoryError, match='architecture differs'):
        qa.audit_archive(wheel_bytes(entries), **inputs)


@pytest.mark.parametrize('change', ['source', 'native', 'notice', 'license', 'missing-license',
                                   'metadata-license', 'duplicate-metadata', 'abi', 'purelib',
                                   'extra-package', 'extra-distribution', 'path', 'manifest',
                                   'missing-native-origin', 'missing-source-origin', 'missing-notice-origin'])
def test_resealed_wheel_does_not_hide_wrong_source_or_origin(change):
    entries, inputs = sample()
    if change == 'source': entries['vispy/__init__.py'] += b'wrong'
    elif change == 'native': entries['vispy/_dawn.cp312-win_amd64.pyd'] += b'wrong'
    elif change == 'notice': entries['vispy/_licenses/vispy-LICENSE.txt'] = b'wrong BSD'
    elif change == 'license': entries[qa.DIST + '/licenses/LICENSE-BSD'] = b'wrong BSD'
    elif change == 'missing-license':
        del entries[qa.DIST + '/licenses/LICENSE-BSD']; del inputs['distribution_licenses'][qa.DIST + '/licenses/LICENSE-BSD']
    elif change == 'metadata-license':
        entries[qa.DIST + '/METADATA'] = entries[qa.DIST + '/METADATA'].replace(b'AGPL-3.0-only', b'BSD-3-Clause')
    elif change == 'duplicate-metadata': entries[qa.DIST + '/METADATA'] = b'Name: vispy\n' + entries[qa.DIST + '/METADATA']
    elif change == 'abi': entries[qa.DIST + '/WHEEL'] = entries[qa.DIST + '/WHEEL'].replace(b'cp312', b'cp311')
    elif change == 'purelib': entries[qa.DIST + '/WHEEL'] = entries[qa.DIST + '/WHEEL'].replace(b'false', b'true')
    elif change == 'extra-package': entries['vispy/unexpected.py'] = b'extra'
    elif change == 'extra-distribution': entries['unselected.data/payload'] = b'extra'
    elif change == 'path': entries['../outside'] = b'extra'
    elif change == 'manifest': entries[qa.runtime_package.MEMBER] += b' '
    elif change == 'missing-native-origin': inputs['native_hashes'].pop(next(iter(inputs['native_hashes'])))
    elif change == 'missing-source-origin': inputs['pure_hashes'].pop('vispy/__init__.py')
    elif change == 'missing-notice-origin': inputs['notices'].pop('vispy/_licenses/vispy-LICENSE.txt')
    # RECORD is regenerated, so these exercise semantic joins, not old hashes.
    with pytest.raises((qa.InventoryError, ValueError)):
        qa.audit_archive(wheel_bytes(entries), **inputs)


@pytest.mark.parametrize('change', ['hash', 'size', 'missing', 'duplicate', 'self-hash', 'malformed'])
def test_record_controls(change):
    entries, inputs = sample()

    def mutate(rows):
        if change == 'hash': rows[0][1] = 'sha256=' + 'A' * 43
        elif change == 'size': rows[0][2] = '9999'
        elif change == 'missing': rows.pop(0)
        elif change == 'duplicate': rows.append(deepcopy(rows[0]))
        elif change == 'self-hash': rows[-1][1] = 'sha256=' + 'A' * 43
        else: rows[0].pop()

    with pytest.raises(qa.InventoryError):
        qa.audit_archive(wheel_bytes(entries, mutate), **inputs)


def test_real_source_notice_inputs_keep_original_and_agpl_copies():
    notices = qa.source_notices(qa.ROOT)
    copies = qa.source_distribution_licenses(qa.ROOT)
    for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md'):
        assert notices['vispy/_licenses/' + name] == (qa.ROOT / name).read_bytes()
        assert copies[qa.DIST + '/licenses/' + name] == notices['vispy/_licenses/' + name]
    assert notices['vispy/_licenses/vispy-LICENSE.txt'] == notices['vispy/_licenses/LICENSE-BSD']


@pytest.mark.parametrize('field', ['windows_sdk_sha256', 'windows_compiler_sha256', 'linux_scope', 'metal_scope'])
def test_producer_policy_cannot_relabel_experimental_origins(monkeypatch, field):
    policy = deepcopy(qa.validate_policy())
    policy[field] = '0' * 64 if field.endswith('sha256') else 'admitted'
    read = qa.read_json
    monkeypatch.setattr(qa, 'read_json', lambda path: policy if path == qa.ROOT / qa.POLICY else read(path))
    with pytest.raises(qa.InventoryError): qa.validate_policy()


def test_unapproved_sdk_is_rejected_before_verifier_or_file_access(monkeypatch):
    reference = {'path': 'unit-only.json', 'sha256': '0' * 64}
    record = {'schema': 1, 'kind': 'vendor-sdk-reuse', 'manifest': reference,
              'dependency_lock': reference, 'consumer': reference}
    monkeypatch.setattr(qa.native_sdk, 'verify', lambda *a: pytest.fail('unapproved SDK reached verifier'))
    with pytest.raises(qa.InventoryError, match='not an allowed vendor origin'):
        qa.validate_sdk(record)


def test_sdk_delegation_only_reports_vendor_reuse(monkeypatch):
    # Synthetic verifier result, explicitly no native leaf/artifact approval.
    manifest = qa.ROOT / 'unit-sdk/manifest.json'
    lock = qa.ROOT / 'unit-lock.json'
    settings = {name: 'unit-only' for name in qa.native_sdk.SETTINGS + ('compiler',)}
    refs = {'manifest': {'path': 'unit-sdk/manifest.json', 'sha256': qa.SDK_SHA},
            'dependency_lock': {'path': 'unit-lock.json', 'sha256': '0' * 64},
            'consumer': {'path': 'unit-consumer.json', 'sha256': '0' * 64}}
    monkeypatch.setattr(qa, 'file_ref', lambda root, ref: root / ref['path'])
    read = qa.read_json
    monkeypatch.setattr(qa, 'read_json', lambda path: settings if path == qa.ROOT / refs['consumer']['path'] else read(path))
    calls = []

    def verified(prefix, checksum, dependency, consumer):
        calls.append((prefix, checksum, dependency, consumer))
        return {'compiler_sha256': qa.COMPILER_SHA,
                'compiler_policy_verifier_sha256': qa.sha((qa.ROOT / 'cmake/native_sdk.py').read_bytes())}

    monkeypatch.setattr(qa.native_sdk, 'verify', verified)
    result = qa.validate_sdk({'schema': 1, 'kind': 'vendor-sdk-reuse', **refs})
    assert calls == [(manifest.parent, qa.SDK_SHA, lock, settings)]
    assert not result['native_leaf_admitted'] and not result['artifact_admitted']


def test_policy_cli_is_read_only_and_cannot_admit(capsys):
    before = (qa.ROOT / qa.POLICY).read_bytes()
    assert qa.main([]) == 0
    assert (qa.ROOT / qa.POLICY).read_bytes() == before
    assert '"artifact_admitted": false' in capsys.readouterr().out


@pytest.mark.parametrize('name,blocked', [('build/work/another-run/native.pyd', True),
                                        ('build/artifacts/hash/native.pyd', False)])
def test_archive_references_cannot_borrow_disposable_scratch(monkeypatch, name, blocked):
    path = qa.ROOT / name
    monkeypatch.setattr(qa, 'file_ref', lambda *args: path)
    if blocked:
        with pytest.raises(qa.InventoryError, match='managed scratch'):
            qa.retained_file(qa.ROOT, {})
    else:
        assert qa.retained_file(qa.ROOT, {}) == path
