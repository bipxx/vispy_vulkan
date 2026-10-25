# SPDX-License-Identifier: AGPL-3.0-only
"""Small in-memory controls for bounded package projection, not graphics proof."""
import io
import hashlib
import json
import tarfile
from types import SimpleNamespace

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
