"""The runtime wheel has an exact, source-auditable shipping contract."""
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cmake'))
from runtime_package import expected_members, source_package_hashes, validate_manifest, wheel_package_hashes


@pytest.fixture
def package(tmp_path):
    manifest = {'schema': 1, 'profile': 'dawn-no-opengl-runtime',
                'files': ['gloo/gl/dawn.py', 'gloo/gl/gl2.py', 'gloo/gl/glplus.py'],
                'excluded_files': {'gloo/gl/es2.py': 'legacy GL loader'},
                'compatibility_aliases': ['gloo/gl/gl2.py', 'gloo/gl/glplus.py'],
                'notice_files': ['LICENSE', 'LICENSE-BSD'], 'generated_manifest_member': 'vispy/_runtime_package.json'}
    path = tmp_path / 'compat/runtime-package.json'
    path.parent.mkdir()
    path.write_text(json.dumps(manifest))
    for name in manifest['files']:
        source = tmp_path / 'src/vispy' / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('# source ' + name)
    return tmp_path, manifest


def make_wheel(root, manifest, *, extra=None, modified=None):
    path = root / 'fixture.whl'
    with zipfile.ZipFile(path, 'w') as archive:
        for name in expected_members(manifest, suffix='.cp312-win_amd64.pyd', platform='win32'):
            source = root / 'src' / name
            data = (root / 'compat/runtime-package.json').read_bytes() if name.endswith('_runtime_package.json') else (source.read_bytes() if source.exists() else b'fixture-native-or-notice')
            archive.writestr(name, b'changed' if name == modified else data)
        if extra:
            archive.writestr(extra, b'not permitted')
    return path


def test_current_exclusions_match_backend_packaging_configuration():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    manifest = validate_manifest(json.loads((ROOT / 'compat/runtime-package.json').read_text()))
    assert set(project['tool']['scikit-build']['wheel']['exclude']) == {'vispy/' + n for n in manifest['excluded_files']}
    for name in manifest['excluded_files']:
        assert (ROOT / 'src/vispy' / name).is_file(), name
    assert {'gloo/gl/dawn.py', 'gloo/gl/gl2.py', 'gloo/gl/glplus.py'} <= set(manifest['files'])


def test_exact_archive_members_and_source_bytes_pass(package):
    root, manifest = package
    wheel = make_wheel(root, manifest)
    hashes = wheel_package_hashes(wheel, root=root, suffix='.cp312-win_amd64.pyd', platform='win32')
    assert set(hashes) == expected_members(manifest, suffix='.cp312-win_amd64.pyd', platform='win32')
    assert set(source_package_hashes(root)) <= set(hashes)


def test_legacy_loader_cannot_reappear_as_unexpected_wheel_member(package):
    root, manifest = package
    wheel = make_wheel(root, manifest, extra='vispy/gloo/gl/es2.py')
    with pytest.raises(ValueError, match='unexpected'):
        wheel_package_hashes(wheel, suffix='.cp312-win_amd64.pyd', platform='win32')


def test_shipped_source_byte_change_is_not_hidden_by_the_manifest(package):
    root, manifest = package
    wheel = make_wheel(root, manifest, modified='vispy/gloo/gl/dawn.py')
    with pytest.raises(ValueError, match='Shipped source bytes differ'):
        wheel_package_hashes(wheel, root=root, suffix='.cp312-win_amd64.pyd', platform='win32')


@pytest.mark.parametrize('bad', ['../escape.py', '/absolute.py', 'a\\b.py'])
def test_noncanonical_manifest_paths_fail(package, bad):
    root, manifest = package
    manifest['excluded_files'][bad] = 'bad'
    with pytest.raises(ValueError, match='Noncanonical'):
        validate_manifest(manifest)
