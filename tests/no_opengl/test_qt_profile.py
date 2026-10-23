"""Selected Qt package contents and notice preservation are explicit."""
import hashlib
import json
from pathlib import Path
import sys
import tomllib
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from no_opengl.policy import library_reason
from no_opengl.qt_profile import build


def test_selected_profile_pins_original_wheels_and_retains_required_native_paths():
    manifest = json.loads((ROOT / 'compat/qt/windows-pyqt6-no-opengl.json').read_text())
    lock = tomllib.loads((ROOT / 'uv.lock').read_text())
    for item in manifest['wheels']:
        package = next(row for row in lock['package'] if row['name'] == item['name'])
        original = next(row for row in package['wheels'] if row['url'] == item['input_url'])
        assert original['hash'] == 'sha256:' + item['input_sha256']
        assert item['selected_members'] == sorted(set(item['selected_members']))
        assert set(item['original_notice_members']) <= set(item['selected_members'])
        assert not any(library_reason(name) for name in item['selected_members'] if name.endswith(('.dll', '.pyd')))
    runtime = next(item for item in manifest['wheels'] if item['name'] == 'pyqt6-qt6')
    assert {'PyQt6/Qt6/bin/Qt6Gui.dll', 'PyQt6/Qt6/plugins/platforms/qwindows.dll'} <= set(runtime['selected_members'])
    requirements = (ROOT / 'compat/qt/windows-pyqt6-no-opengl-requirements.txt').read_text()
    assert 'pyqt6==6.11.0+vispynogl.1 --hash=sha256:' in requirements
    assert 'pyqt6-qt6==6.11.2+vispynogl.1 --hash=sha256:' in requirements
    assert 'pyqt6-sip==13.13.0 --hash=sha256:' in requirements


def profile_fixture(tmp_path, *, missing_notice=False, wrong_hash=False):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    source = inputs / 'qt-1-py3-none-win_amd64.whl'
    notice, gl = 'qt-1.dist-info/LICENSE', 'PyQt6/Qt6/bin/Qt6OpenGL.dll'
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr(notice, b'original license text')
        archive.writestr(gl, b'GL-specific synthetic fixture')
    item = dict(name='pyqt6-qt6', input_filename=source.name, input_sha256='0' * 64 if wrong_hash else hashlib.sha256(source.read_bytes()).hexdigest(),
                input_version='1', output_version='1+profile', selected_members=sorted([gl] if missing_notice else [notice, gl]),
                original_notice_members=[] if missing_notice else [notice])
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(dict(schema=1, platform='win_amd64', profile='synthetic-negative', wheels=[item])))
    return manifest, inputs


@pytest.mark.parametrize('missing_notice,wrong_hash,reason', [(True, False, 'notices'), (False, True, 'Pinned'), (False, False, 'GL-specific')])
def test_profile_rejects_dropped_notice_changed_input_and_gl_native_payload(tmp_path, missing_notice, wrong_hash, reason):
    manifest, inputs = profile_fixture(tmp_path, missing_notice=missing_notice, wrong_hash=wrong_hash)
    with pytest.raises(ValueError, match=reason):
        build(manifest, inputs, tmp_path / 'output')
