# SPDX-License-Identifier: AGPL-3.0-only
"""Real archive/RECORD joins with synthetic native images; no build admission."""
import io
import zipfile

import pytest

from tools import qualification_artifact as qa
from tools.repackage_python_wheel import repackage
from test_qualification_artifact import sample, wheel_bytes


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_source_update_preserves_all_other_members_and_record_is_valid(platform):
    entries, inputs = sample(platform)
    original = wheel_bytes(entries)
    replacement = b'# Changed Python implementation\n'
    result, report = repackage(original, {'vispy/__init__.py': replacement}, **inputs)
    assert report['changed_members'] == ['vispy/__init__.py']
    assert report['artifact_admitted'] is False and report['native_rebuilt'] is False
    assert report['original_sha256'] == qa.sha(original)
    assert report['wheel_sha256'] == qa.sha(result) != qa.sha(original)
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert archive.read('vispy/__init__.py') == replacement
        for name, payload in entries.items():
            if name != 'vispy/__init__.py':
                assert archive.read(name) == payload
        qa.check_record(archive, set(archive.namelist()))
    qa.audit_archive(result, **dict(inputs, pure_hashes={
        **inputs['pure_hashes'], 'vispy/__init__.py': qa.sha(replacement)}))
    # The original source proof must reject the successor, rather than silently
    # treating the old wheel's audit as proof of newly packaged source bytes.
    with pytest.raises(ValueError, match='source/native output bytes differ'):
        qa.audit_archive(result, **inputs)


@pytest.mark.parametrize('replacements', [{}, {'vispy/__init__.py': b'# Synthetic source\n'}])
def test_unchanged_source_reuses_original_archive_bytes(replacements):
    entries, inputs = sample()
    original = wheel_bytes(entries)
    result, report = repackage(original, replacements, **inputs)
    assert result is original
    assert report['status'] == 'UNCHANGED_ORIGINAL_WHEEL_REUSED'
    assert report['changed_members'] == [] and report['artifact_admitted'] is False


@pytest.mark.parametrize('name', [
    'vispy/_dawn.cp312-win_amd64.pyd', 'vispy/_runtime_package.json',
    'vispy/_licenses/LICENSE-BSD', qa.DIST + '/METADATA', qa.DIST + '/RECORD',
    'vispy/new_module.py', '../outside.py',
])
def test_replacements_cannot_change_native_manifest_license_metadata_or_membership(name):
    entries, inputs = sample()
    with pytest.raises(ValueError, match='Only existing pure source'):
        repackage(wheel_bytes(entries), {name: b'changed'}, **inputs)


@pytest.mark.parametrize('mutation', ['native', 'license', 'record'])
def test_original_archive_corruption_is_rejected_before_repackaging(mutation):
    entries, inputs = sample('linux')
    if mutation == 'native':
        entries['vispy/_dawn.cpython-312-x86_64-linux-gnu.so'] += b'corrupt'
    elif mutation == 'license':
        entries['vispy/_licenses/LICENSE-BSD'] = b'corrupt'
    raw = wheel_bytes(entries)
    if mutation == 'record':
        raw = wheel_bytes(entries, lambda rows: rows[0].__setitem__(1, 'sha256=wrong'))
    with pytest.raises(ValueError):
        repackage(raw, {'vispy/__init__.py': b'# Fix\n'}, **inputs)


def test_replacement_must_be_frozen_bytes():
    entries, inputs = sample()
    with pytest.raises(ValueError, match='must be bytes'):
        repackage(wheel_bytes(entries), {'vispy/__init__.py': bytearray(b'changed')}, **inputs)
