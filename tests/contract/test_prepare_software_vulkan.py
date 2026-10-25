# SPDX-License-Identifier: AGPL-3.0-only
"""Small in-memory controls for bounded package projection, not graphics proof."""
import io
import hashlib
import json
import tarfile
from types import SimpleNamespace
from pathlib import Path

import pytest

from tools import prepare_software_vulkan as driver
from tools.prepare_software_vulkan import select_members


def archive(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as tar:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(data) if kind == tarfile.REGTYPE else 0
            info.linkname = '/unrelated/target' if kind == tarfile.SYMTYPE else ''
            tar.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
    stream.seek(0)
    return stream


def test_projects_only_named_bytes_without_extracting_other_paths():
    data = archive([('../../unrelated', b'ignore', tarfile.REGTYPE),
                    ('./lib.so', b'library', tarfile.REGTYPE),
                    ('./copyright', b'original notice', tarfile.REGTYPE)])
    assert select_members(data, {'./lib.so', './copyright'}) == {
        './lib.so': b'library', './copyright': b'original notice'}


@pytest.mark.parametrize('kind', [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE])
def test_selected_member_must_be_a_regular_file(kind):
    with pytest.raises(ValueError, match='nonregular'):
        select_members(archive([('./lib.so', b'', kind)]), {'./lib.so'})


def test_duplicate_selected_name_rejects_even_when_bytes_match():
    with pytest.raises(ValueError, match='duplicate'):
        select_members(archive([('./lib.so', b'one', tarfile.REGTYPE)] * 2), {'./lib.so'})


def test_missing_library_or_notice_rejects():
    with pytest.raises(ValueError, match='missing selected'):
        select_members(archive([('./lib.so', b'one', tarfile.REGTYPE)]), {'./lib.so', './copyright'})


def test_truncated_tar_rejects():
    with pytest.raises(tarfile.ReadError):
        select_members(io.BytesIO(b'not a tar archive'), {'./lib.so'})


def input_fixture(tmp_path):
    content = b'original retained source'
    sha = hashlib.sha256(content).hexdigest()
    folder = tmp_path / sha
    folder.mkdir()
    path = folder / 'source.tar.xz'
    path.write_bytes(content)
    return {'inputs': [{'name': path.name, 'sha256': sha, 'size': len(content)}]}, path


def test_matching_retained_input_is_reused(tmp_path):
    pin, path = input_fixture(tmp_path)
    assert driver.retained_inputs(pin, tmp_path) == {path.name: path}


@pytest.mark.parametrize('change', ['bytes', 'size', 'missing', 'duplicate'])
def test_all_source_inputs_must_match(tmp_path, change):
    pin, path = input_fixture(tmp_path)
    if change == 'bytes':
        path.write_bytes(b'X' * path.stat().st_size)
    elif change == 'size':
        pin['inputs'][0]['size'] += 1
    elif change == 'missing':
        path.unlink()
    else:
        pin['inputs'].append(dict(pin['inputs'][0]))
    with pytest.raises((ValueError, FileNotFoundError)):
        driver.retained_inputs(pin, tmp_path)


@pytest.mark.parametrize('case', ['wrong-owner', 'scratch-record'])
def test_registered_owner_and_durable_record_required(tmp_path, monkeypatch, case):
    scratch = tmp_path / 'build/work/example'
    scratch.mkdir(parents=True)
    (scratch / '.build-hygiene-owner.json').write_text(json.dumps({
        'schema': 1, 'run_id': 'example', 'owner': 'another' if case == 'wrong-owner' else 'root'}))
    monkeypatch.setattr(driver, 'ROOT', tmp_path)
    monkeypatch.setattr(driver, 'sys', SimpleNamespace(platform='linux'))
    output = scratch / 'record.json' if case == 'scratch-record' else tmp_path / 'record.json'
    with pytest.raises(ValueError, match='ownership|outside all scratch'):
        driver.prepare('example', 'root', output)
    assert not (scratch / 'software-vulkan').exists()


def raw_fixture(tmp_path, monkeypatch):
    """Synthetic bytes test projection only, never an ELF/device claim."""
    monkeypatch.setattr(driver, 'ROOT', tmp_path)
    monkeypatch.setattr(driver, 'sys', SimpleNamespace(platform='linux'))
    scratch = tmp_path / 'build/work/raw'
    scratch.mkdir(parents=True)
    (scratch / '.build-hygiene-owner.json').write_text(json.dumps(
        {'schema': 1, 'run_id': 'raw', 'owner': 'root'}))
    inputs = []
    for name, data, roles in [('libvulkan_lvp.so', b'synthetic library', ['evidence']),
                              ('notice.txt', b'original notice', ['licenses']),
                              ('source.tar', b'preferred source', ['source'])]:
        sha = hashlib.sha256(data).hexdigest()
        path = tmp_path / 'artifacts' / sha / name
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        inputs.append(dict(name=name, sha256=sha, size=len(data), roles=roles))
    pin = {'inputs': inputs, 'libraries': [dict(kind='retained-file',
        input='libvulkan_lvp.so', notice_input='notice.txt',
        filename='libvulkan_lvp.so', sha256=inputs[0]['sha256'])]}
    path = tmp_path / 'pin.json'
    path.write_text(json.dumps(pin))
    return pin, path, scratch


def test_retained_native_projection_preserves_bytes_notices_and_scope(tmp_path, monkeypatch):
    pin, path, scratch = raw_fixture(tmp_path, monkeypatch)
    output = tmp_path / 'observation.json'
    record = driver.prepare('raw', 'root', output, tmp_path / 'artifacts', pin_path=path)
    assert (scratch / 'software-vulkan/libvulkan_lvp.so').read_bytes() == b'synthetic library'
    assert record['libraries'][0]['sha256'] == pin['inputs'][0]['sha256']
    assert Path(record['notices'][0]['path']).read_bytes() == b'original notice'
    assert record['qualified'] is False and record['commands'] == []
    assert json.loads(output.read_bytes()) == record


@pytest.mark.parametrize('change', ['library-hash', 'notice-bytes', 'source-missing', 'kind'])
def test_retained_projection_requires_all_inputs_and_expected_output(tmp_path, monkeypatch, change):
    pin, path, _ = raw_fixture(tmp_path, monkeypatch)
    if change == 'library-hash':
        pin['libraries'][0]['sha256'] = '0' * 64
    elif change == 'kind':
        pin['libraries'][0]['kind'] = 'unknown'
    else:
        item = pin['inputs'][1 if change == 'notice-bytes' else 2]
        file = tmp_path / 'artifacts' / item['sha256'] / item['name']
        if change == 'notice-bytes':
            file.write_bytes(b'changed notice')
        else:
            file.unlink()
    path.write_text(json.dumps(pin))
    with pytest.raises((ValueError, FileNotFoundError)):
        driver.prepare('raw', 'root', tmp_path / 'observation.json',
                       tmp_path / 'artifacts', pin_path=path)


def test_explicit_workspace_still_requires_matching_owned_marker(tmp_path, monkeypatch):
    _, path, _ = raw_fixture(tmp_path, monkeypatch)
    workspace = tmp_path / 'guest'
    scratch = workspace / 'build/work/raw'
    scratch.mkdir(parents=True)
    (scratch / '.build-hygiene-owner.json').write_text(json.dumps(
        {'schema': 1, 'run_id': 'raw', 'owner': 'another'}))
    with pytest.raises(ValueError, match='ownership'):
        driver.prepare('raw', 'root', tmp_path / 'observation.json',
                       tmp_path / 'artifacts', pin_path=path, workspace=workspace)
