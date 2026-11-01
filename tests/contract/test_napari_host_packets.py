# SPDX-License-Identifier: AGPL-3.0-only
"""D30: reference packets per napari version, and the pin that the successor fixtures drop."""
import ast
import json

import pytest

from tools import napari_host_packets as packets_module
from tools.napari_host_packets import (ROOT, evidence_dir, installed_packet, is_napari_pin, packet_dir, packets,
                                       unpinned_source)


def make_packet(root, base, version, recorded=None):
    directory = root / f'{base}-napari-{version}'
    directory.mkdir(parents=True)
    manifest = {'schema': 1, 'provenance': {'napari_version': recorded or version}, 'fixtures': {}, 'errors': {}}
    (directory / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return directory


def test_packet_dir_names_the_napari_version(tmp_path):
    assert packet_dir('napari-opengl', '0.10.0', root=tmp_path) == tmp_path / 'napari-opengl-napari-0.10.0'
    assert packet_dir('napari-opengl', '0.10.0') == ROOT / 'tests/reference/napari-opengl-napari-0.10.0'


def test_packets_returns_every_version_and_checks_provenance(tmp_path):
    newer = make_packet(tmp_path, 'napari-opengl', '0.11.0')
    current = make_packet(tmp_path, 'napari-opengl', '0.10.0')
    assert packets('napari-opengl', root=tmp_path) == {'0.10.0': current, '0.11.0': newer}
    assert list(packets('napari-opengl', root=tmp_path)) == ['0.10.0', '0.11.0']
    make_packet(tmp_path, 'napari-volume-opengl', '0.10.0', recorded='0.9.2')
    with pytest.raises(AssertionError, match=r'0\.10\.0.*0\.9\.2'):
        packets('napari-volume-opengl', root=tmp_path)


def test_packets_keeps_bases_apart(tmp_path):
    make_packet(tmp_path, 'napari-volume-opengl', '0.10.0')
    make_packet(tmp_path, 'napari-layer-controls-opengl', '0.10.0')
    assert packets('napari-opengl', root=tmp_path) == {}
    assert list(packets('napari-volume-opengl', root=tmp_path)) == ['0.10.0']


def test_installed_packet_requires_the_exact_version(tmp_path, monkeypatch):
    current = make_packet(tmp_path, 'napari-opengl', '0.10.0')
    assert installed_packet('napari-opengl', '0.10.0', root=tmp_path) == current
    with pytest.raises(AssertionError, match=r'napari 0\.10\.1.*oracle_napari_successor_capture\.py'):
        installed_packet('napari-opengl', '0.10.1', root=tmp_path)
    make_packet(tmp_path, 'napari-volume-opengl', '0.10.0', recorded='0.9.2')
    with pytest.raises(AssertionError, match=r'0\.9\.2'):
        installed_packet('napari-volume-opengl', '0.10.0', root=tmp_path)
    versions = {'napari': '0.10.0'}
    monkeypatch.setattr(packets_module.metadata, 'version', versions.__getitem__)
    assert installed_packet('napari-opengl', root=tmp_path) == current


@pytest.mark.parametrize('source, expected', [
    ('assert metadata.version("napari") == "0.9.2"', True),
    ("assert metadata.version('napari') == '0.9.2', 'required pinned napari dependency'", True),
    ('assert napari.__version__ == "0.9.2"', True),
    ('assert metadata.version("QtPy") == "2.4.3"', False),
    ('assert metadata.version("napari") == expected', False),
    ('assert metadata.version("napari") != "0.9.2"', False),
    ('assert napari.__version__ == "0.9.2" and numba.__version__ == "0.68.0"', False),
    ('if ready:\n    assert metadata.version("napari") == "0.9.2"', False),
    ('version = metadata.version("napari")', False),
])
def test_is_napari_pin_matches_only_napari_pins(source, expected):
    assert is_napari_pin(ast.parse(source).body[0]) is expected


def pinned(name):
    """A sample render."""
    assert metadata.version('napari') == '0.9.2', 'required pinned napari dependency'  # noqa: F821
    if name:
        assert metadata.version('napari') == '0.9.2'  # noqa: F821
    return name


def unpinned(name):
    """A sample render."""
    if name:
        assert metadata.version('napari') == '0.9.2'  # noqa: F821
    return name


def test_unpinned_source_removes_only_top_level_pins():
    assert unpinned_source(pinned) == unpinned_source(unpinned).replace('def unpinned', 'def pinned')
    assert "assert metadata.version('napari') == '0.9.2'" in unpinned_source(pinned)
    assert 'required pinned napari dependency' not in unpinned_source(pinned)


def test_evidence_dir_honours_the_override(tmp_path, monkeypatch):
    monkeypatch.delenv('VISPY_NAPARI_EVIDENCE', raising=False)
    assert evidence_dir('napari-volume-successor-candidate', '0.10.0') == (
        ROOT / 'build/evidence/napari-volume-successor-candidate/0.10.0')
    monkeypatch.setenv('VISPY_NAPARI_EVIDENCE', str(tmp_path))
    assert evidence_dir('napari-volume-successor-candidate', '0.10.0') == (
        tmp_path / 'napari-volume-successor-candidate/0.10.0')


def test_lock_mismatches_names_every_unsatisfied_requirement(tmp_path, monkeypatch):
    lock = tmp_path / 'host.txt'
    lock.write_text('# a uv lock\nnapari==0.11.0 \\\n    --hash=sha256:' + '0' * 64 + '\n'
                    'numpy==2.4.6 ; python_full_version >= "3.11"\n'
                    'numpy==2.2.6 ; python_full_version < "3.11"\n'
                    'qtpy==2.4.3\nvispy==0.17.0 \\\n    --hash=sha256:' + '1' * 64 + '\n', encoding='utf-8')
    versions = {'napari': '0.10.0', 'numpy': '2.4.6', 'vispy': '0.17.0+vulkan.1'}

    def version(name):
        if name not in versions:
            raise packets_module.metadata.PackageNotFoundError(name)
        return versions[name]

    monkeypatch.setattr(packets_module.metadata, 'version', version)
    # The renderer is skipped (a candidate replaces it); markers that do not apply are skipped.
    assert packets_module.lock_mismatches(lock) == [('napari', '0.10.0', '==0.11.0'), ('qtpy', None, '==2.4.3')]
    versions.update(napari='0.11.0', qtpy='2.4.3')
    assert packets_module.lock_mismatches(lock) == []


__all__ = [name for name in dir() if name.startswith('test_')]
