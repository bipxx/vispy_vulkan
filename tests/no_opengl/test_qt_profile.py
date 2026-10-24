"""Selected Qt package contents and notice preservation are explicit."""
import hashlib
import json
from pathlib import Path
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from no_opengl.policy import library_reason
from no_opengl.qt_profile import build


@pytest.mark.parametrize('binding,qt', [('pyqt6', 'Qt6'), ('pyqt5', 'Qt5'), ('pyside6', 'Qt6')])
def test_selected_profile_pins_original_wheels_and_retains_required_native_paths(binding, qt):
    manifest = json.loads((ROOT / ('compat/qt/windows-' + binding + '-no-opengl.json')).read_text())
    lock = tomllib.loads((ROOT / 'uv.lock').read_text())
    for item in manifest['wheels']:
        package = next(row for row in lock['package'] if row['name'] == item['name'])
        original = next(row for row in package['wheels'] if row['url'] == item['input_url'])
        assert original['hash'] == 'sha256:' + item['input_sha256']
        assert item['selected_members'] == sorted(set(item['selected_members']))
        assert set(item['original_notice_members']) <= set(item['selected_members'])
        assert not any(library_reason(name) for name in item['selected_members'] if name.endswith(('.dll', '.pyd')))
    runtime = next(item for item in manifest['wheels'] if item['name'] == manifest.get('runtime_distribution', 'pyqt6-qt6'))
    prefix = 'PySide6/' if binding == 'pyside6' else ('PyQt5/Qt5/' if binding == 'pyqt5' else 'PyQt6/Qt6/')
    assert {prefix + ('' if binding == 'pyside6' else 'bin/') + qt + 'Gui.dll',
            prefix + 'plugins/platforms/qwindows.dll'} <= set(runtime['selected_members'])
    requirements = (ROOT / ('compat/qt/windows-' + binding + '-no-opengl-requirements.txt')).read_text()
    for item in manifest['wheels']:
        assert item['name'] + '==' + item['output_version'] + ' --hash=sha256:' in requirements
    assert manifest['preferred_sources'] and all(len(item['sha256']) == 64 for item in manifest['preferred_sources'])
    if binding == 'pyside6':
        meta = next(item for item in manifest['wheels'] if item['name'] == 'pyside6')
        assert set(meta['drop_requires']) == {'PySide6_Addons', 'PySide6_PDF', 'PySide6_WebEngine'}
        assert not any(item['name'] == 'pyside6-addons' for item in manifest['wheels'])


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


def test_linux_source_profile_records_relocation_notices_and_real_feature_limits():
    manifest = json.loads((ROOT / 'compat/qt/linux-pyqt6-no-opengl.json').read_text())
    assert manifest['features']['opengl'] is manifest['features']['egl'] is False
    assert manifest['features']['xcb'] and manifest['features']['vulkan']
    assert not manifest['features']['qt_network_ssl'] and not manifest['features']['wayland']
    assert manifest['notices'] and all(len(item['sha256']) == 64 for item in manifest['notices'])
    for wheel in manifest['wheels']:
        assert len({entry['member'] for entry in wheel['files']}) == len(wheel['files'])
        assert not any(library_reason(entry['member']) for entry in wheel['files'])
        assert all(len(entry['sha256']) == 64 for entry in wheel['files'])
    binding = next(item for item in manifest['wheels'] if item['name'] == 'pyqt6')
    native = [item for item in binding['files'] if item.get('native')]
    assert {item['member'] for item in native} == {'PyQt6/Qt' + name + '.abi3.so' for name in manifest['modules']}
    assert all(item['relocated'] and item['before_relocation_sha256'] != item['sha256'] for item in native)
    runtime = next(item for item in manifest['wheels'] if item['name'] == 'pyqt6-qt6')
    assert 'PyQt6/Qt6/lib/libQt6Gui.so.6' in {item['member'] for item in runtime['files']}
    assert not any('.so.6.' in item['member'] for item in runtime['files'])
    assert manifest['runtime_apt_versions']['status'] == 'PASS'
    assert all('=' in pin for pin in manifest['runtime_apt_versions']['apt_install_pins'])


def test_linux_pyside_source_profile_binds_real_relocation_and_declared_build_patch():
    manifest = json.loads((ROOT / 'compat/qt/linux-pyside6-no-opengl.json').read_text())
    assert manifest['profile'] == 'linux-pyside6-source-no-opengl-v1'
    assert not manifest['features']['opengl'] and not manifest['features']['egl']
    assert not manifest['features']['qt_network_ssl']
    native = [entry for wheel in manifest['wheels'] for entry in wheel['files'] if entry.get('native')]
    assert len(native) == 50 and sum(entry['relocated'] for entry in native) == 13
    assert manifest['original_notice_count'] == 136
    assert len(manifest['notices']) == 139  # Includes the exact declared patch, manifest and original file.
    assert len(manifest['runtime_apt_versions']['apt_install_pins']) == 50
    patch = manifest['preferred_source_patches'][0]
    assert patch['original_header_retained'] and patch['original_file_license'] == 'BSD-3-Clause'
    assert not patch['feature_flags_changed'] and not patch['ssl_feature']
    assert hashlib.sha256((ROOT / patch['repository_patch']).read_bytes()).hexdigest() == patch['patch_sha256']
    binding = next(wheel for wheel in manifest['wheels'] if wheel['name'] == 'pyside6')
    assert set(binding['requires']) == {'shiboken6==6.12.0+vispynogl.1', 'pyside6-qt6==6.12.0+vispynogl.1'}
    assert not manifest['support_wheels']  # Shiboken is source-built, not replaced by a stock wheel.


def test_linux_pyqt5_keeps_official_sip_and_distinguishes_qt_from_dawn_vulkan():
    manifest = json.loads((ROOT / 'compat/qt/linux-pyqt5-no-opengl.json').read_text())
    assert not manifest['features']['opengl'] and not manifest['features']['egl']
    assert not manifest['features']['vulkan'] and manifest['features']['dawn_vulkan_renderer_independent']
    native = [entry for wheel in manifest['wheels'] for entry in wheel['files'] if entry.get('native')]
    assert len(native) == 43 and sum(entry['relocated'] for entry in native) == 10
    assert manifest['original_notice_count'] == 93 and len(manifest['notices']) == 94
    assert not manifest['preferred_source_patches']
    sip = manifest['support_wheels'][0]
    lock = tomllib.loads((ROOT / 'uv.lock').read_text())
    package = next(row for row in lock['package'] if row['name'] == 'pyqt5-sip')
    original = next(row for row in package['wheels'] if row['url'] == sip['url'])
    assert original['hash'] == 'sha256:' + sip['sha256']
    selection = manifest['portable_sip_selection']
    assert not selection['portable_modified_sip_selected']
    assert sip['native_sha256'] == selection['original_wheel_native_sha256']
    assert sip['native_sha256'] != selection['portable_modified_native_sha256']
    versions = manifest['runtime_apt_versions']
    assert len(versions['apt_install_pins']) == 47
    expected = {row['package'] + (':' + row['architecture'] if ':' not in row['package'] else '') + '=' + row['version']
                for row in versions['packages']}
    assert set(versions['apt_install_pins']) == expected


def test_source_profile_rejects_changed_input_and_path_escape(tmp_path):
    from no_opengl.qt_linux_profile import verified
    root = tmp_path / 'bundle'
    root.mkdir()
    (root / 'file').write_bytes(b'changed')
    with pytest.raises(ValueError, match='bytes differ'):
        verified(root, 'file', '0' * 64)
    with pytest.raises(ValueError, match='Noncanonical'):
        verified(root, '../outside', '0' * 64)


def test_multidistribution_profile_rewrites_only_selected_dependency_names(tmp_path):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    source = inputs / 'pyside6-6.12.0-cp310-abi3-win_amd64.whl'
    header = 'pyside6-6.12.0.dist-info'
    payload = {
        header + '/LICENSE': b'original notice',
        header + '/METADATA': b'Metadata-Version: 2.4\nName: PySide6\nVersion: 6.12.0\nRequires-Dist: PySide6_Essentials==6.12.0\nRequires-Dist: PySide6_Pdf==6.12.0.140\nRequires-Dist: PySide6_Pdf-Extra==1\n\n',
        header + '/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp310-abi3-win_amd64\n',
    }
    with zipfile.ZipFile(source, 'w') as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
    item = dict(name='pyside6', input_filename=source.name, input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                input_version='6.12.0', output_version='6.12.0+profile', selected_members=sorted(payload),
                original_notice_members=[header + '/LICENSE'], profile_member='PySide6/_profile.json',
                requires_overrides={'PySide6-Essentials': '==6.12.0+profile'}, drop_requires=['PySide6-Pdf'])
    manifest = tmp_path / 'profile.json'
    manifest.write_text(json.dumps(dict(schema=1, platform='win_amd64', profile='synthetic-selected', wheels=[item])))
    result = build(manifest, inputs, tmp_path / 'output')
    with zipfile.ZipFile(result['wheels'][0]['file']) as archive:
        text = archive.read('pyside6-6.12.0+profile.dist-info/METADATA').decode()
        assert 'Requires-Dist: PySide6-Essentials==6.12.0+profile' in text
        assert 'Requires-Dist: PySide6_Pdf==' not in text
        assert 'Requires-Dist: PySide6_Pdf-Extra==1' in text
        assert archive.read('pyside6-6.12.0+profile.dist-info/LICENSE') == b'original notice'
