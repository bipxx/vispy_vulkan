# SPDX-License-Identifier: AGPL-3.0-only
"""Real archive/RECORD joins with synthetic native images; no build admission."""
import io
import json
import zipfile

import pytest

from tools import qualification_artifact as qa
from tools.repackage_python_wheel import repackage, repackage_from_source
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


@pytest.fixture
def source_case(tmp_path):
    entries, inputs = sample('linux')
    entries[qa.DIST + '/METADATA'] += b'Synthetic original README\n'
    source = tmp_path / 'source'
    source.mkdir()
    for name, payload in entries.items():
        if name == qa.runtime_package.MEMBER:
            relative = 'compat/runtime-package.json'
        elif name in inputs['pure_hashes']:
            relative = 'src/' + name
        elif name in inputs['notices']:
            base = name.removeprefix('vispy/_licenses/')
            relative = base if base in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md') else 'third_party/licenses/' + base
        else:
            continue
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    (source / 'README.md').write_bytes(b'Synthetic original README\n')
    (source / 'pyproject.toml').write_bytes(b'license-files = ["LICENSE", "LICENSE-BSD", "LICENSING.md"]\n')
    before = {p.relative_to(source).as_posix(): qa.sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
    return source, entries, inputs, before


def test_source_package_route_changes_python_with_frozen_metadata_and_notices(source_case):
    source, entries, inputs, before = source_case
    (source / 'src/vispy/__init__.py').write_bytes(b'# Fixed Python\n')
    output, report = repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
        platform='linux', suffix=inputs['suffix'], tag=inputs['tag'])
    assert report['changed_members'] == ['vispy/__init__.py']
    assert report['original_source_hashes'] == inputs['pure_hashes']
    assert report['current_source_hashes'] == qa.runtime_package.source_package_hashes(source)
    assert report['unchanged_metadata_inputs']['README.md'] == before['README.md']
    with zipfile.ZipFile(io.BytesIO(output)) as archive:
        assert archive.read('vispy/__init__.py') == b'# Fixed Python\n'


@pytest.mark.parametrize('name', ['README.md', 'pyproject.toml', 'compat/runtime-package.json',
                                 'LICENSE-BSD', 'third_party/licenses/vispy-LICENSE.txt'])
def test_source_package_route_rejects_changed_metadata_or_notices(source_case, name):
    source, entries, inputs, before = source_case
    path = source / name
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='Changed or missing original package metadata/notice'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'])


@pytest.mark.parametrize('keep_description', [False, True])
def test_source_package_route_requires_original_pure_source_map(source_case, keep_description):
    source, entries, inputs, before = source_case
    del before['src/vispy/__init__.py']
    with pytest.raises(ValueError, match='source map lacks'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'],
            keep_original_description=keep_description)


@pytest.mark.parametrize('python_changed', [False, True])
def test_explicit_original_description_keeps_archived_metadata_notices_and_native(source_case, python_changed):
    source, entries, inputs, before = source_case
    original = wheel_bytes(entries)
    (source / 'README.md').write_bytes(b'Updated repository landing page, not wheel description\n')
    if python_changed:
        (source / 'src/vispy/__init__.py').write_bytes(b'# Updated runtime source\n')
    output, report = repackage_from_source(original, source, before, inputs['native_hashes'],
        platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)
    decision = report['preserved_original_description']
    assert decision['original_readme_source_sha256'] == before['README.md']
    assert decision['repository_readme_sha256'] == qa.sha((source / 'README.md').read_bytes())
    assert decision['repository_readme_packaged'] is False
    assert 'README.md' not in report['unchanged_metadata_inputs']
    with zipfile.ZipFile(io.BytesIO(original)) as old, zipfile.ZipFile(io.BytesIO(output)) as new:
        assert set(old.namelist()) == set(new.namelist())
        assert decision['preserved_metadata_sha256'] == qa.sha(old.read(qa.DIST + '/METADATA'))
        changed = {name for name in old.namelist() if old.read(name) != new.read(name)}
        assert changed == ({'vispy/__init__.py', qa.DIST + '/RECORD'} if python_changed else set())
        qa.check_record(new, set(new.namelist()))
    assert report['artifact_admitted'] is False
    if not python_changed:
        assert output is original


@pytest.mark.parametrize('name', ['pyproject.toml', 'compat/runtime-package.json',
                                 'LICENSE-BSD', 'third_party/licenses/vispy-LICENSE.txt'])
def test_original_description_option_cannot_waive_other_package_guards(source_case, name):
    source, entries, inputs, before = source_case
    path = source / name
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='Changed or missing original package metadata/notice'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)


@pytest.mark.parametrize('original_hash', [None, '', 'x' * 64, '0' * 63])
def test_original_description_requires_original_readme_binding(source_case, original_hash):
    source, entries, inputs, before = source_case
    before['README.md'] = original_hash
    with pytest.raises(ValueError, match='Missing original README description source binding'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)


def test_original_description_rejects_well_formed_but_wrong_original_pin(source_case):
    source, entries, inputs, before = source_case
    before['README.md'] = '0' * 64
    with pytest.raises(ValueError, match='binding differs from archived description'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)


def test_original_description_rejects_changed_archived_text_with_valid_record(source_case):
    source, entries, inputs, before = source_case
    entries[qa.DIST + '/METADATA'] += b'Changed archived description\n'
    with pytest.raises(ValueError, match='binding differs from archived description'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)


def test_original_description_requires_a_metadata_body_separator(source_case):
    source, entries, inputs, before = source_case
    entries[qa.DIST + '/METADATA'] = entries[qa.DIST + '/METADATA'].replace(b'\n\n', b'\n', 1)
    with pytest.raises(ValueError, match='lacks an archived README description'):
        repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)


@pytest.mark.parametrize('line_ending', [b'\n', b'\r\n'])
def test_original_description_checks_raw_body_without_newline_normalization(source_case, line_ending):
    source, entries, inputs, before = source_case
    header = entries[qa.DIST + '/METADATA'].split(b'\n\n', 1)[0]
    body = b'Original README' + line_ending + b'Second line' + line_ending
    entries[qa.DIST + '/METADATA'] = header + line_ending * 2 + body
    before['README.md'] = qa.sha(body)
    output, report = repackage_from_source(wheel_bytes(entries), source, before, inputs['native_hashes'],
        platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)
    assert report['preserved_original_description']['archived_description_sha256'] == qa.sha(body)
    with zipfile.ZipFile(io.BytesIO(output)) as archive:
        assert archive.read(qa.DIST + '/METADATA') == entries[qa.DIST + '/METADATA']


@pytest.mark.parametrize('mutation', ['native', 'notice', 'record'])
def test_original_description_option_still_rejects_original_archive_corruption(source_case, mutation):
    source, entries, inputs, before = source_case
    if mutation == 'native':
        name = next(n for n in inputs['native_hashes'] if not n.endswith('.json'))
        entries[name] += b'corrupt'
    elif mutation == 'notice':
        entries['vispy/_licenses/LICENSE-BSD'] += b'corrupt'
    data = wheel_bytes(entries)
    if mutation == 'record':
        data = wheel_bytes(entries, lambda rows: rows[0].__setitem__(1, 'sha256=wrong'))
    with pytest.raises(ValueError):
        repackage_from_source(data, source, before, inputs['native_hashes'],
            platform='linux', suffix=inputs['suffix'], tag=inputs['tag'], keep_original_description=True)
