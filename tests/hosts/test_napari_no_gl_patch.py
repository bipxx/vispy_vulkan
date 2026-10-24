# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned source preparation; GUI and Qt native-load gates are separate."""

import ast
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'prepare_napari_no_opengl', ROOT / 'tools/prepare_napari_no_opengl.py')
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


def test_archive_mismatch_never_creates_output(tmp_path):
    archive = tmp_path / 'wrong.tar.gz'
    archive.write_bytes(b'wrong archive')
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='source archive SHA256'):
        PREPARE.prepare(archive, output)
    assert not output.exists()


@pytest.fixture(scope='module')
def patched_source(tmp_path_factory):
    archive = os.environ.get('NAPARI_SOURCE_ARCHIVE')
    if not archive:
        pytest.skip('set NAPARI_SOURCE_ARCHIVE to the pinned upstream sdist')
    return PREPARE.prepare(archive, tmp_path_factory.mktemp('napari') / 'source')


def test_exact_pinned_source_patch_and_licenses(patched_source):
    manifest = json.loads(PREPARE.MANIFEST.read_text(encoding='utf-8'))
    for name, hashes in manifest['files'].items():
        assert PREPARE.sha256(patched_source / name) == hashes['after_sha256']
        if name.endswith('.py'):
            tree = ast.parse((patched_source / name).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(alias.name.split('.')[0] != 'OpenGL' for alias in node.names)
                if isinstance(node, ast.ImportFrom):
                    assert not (node.module or '').startswith('OpenGL')
    assert (patched_source / 'LICENSE').is_file()
    assert (patched_source / 'LICENSE-AGPL').read_bytes() == (ROOT / 'LICENSE').read_bytes()
    project = (patched_source / 'pyproject.toml').read_text(encoding='utf-8')
    assert '"PyOpenGL>=3.1.10"' not in project
    assert 'license = "AGPL-3.0-only"' in project


def test_host_limits_use_dawn_queries_without_canvas(patched_source, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        'patched_napari_limits', patched_source / 'src/napari/_vispy/utils/gl.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from vispy.gloo import gl
    observed = []

    def query(name):
        observed.append(int(name))
        return {3379: 8192, 32883: 2048, 7939: 'Dawn features'}[int(name)]

    monkeypatch.setattr(gl, 'glGetParameter', query)
    assert module.get_max_texture_sizes() == (8192, 2048)
    assert module.get_gl_extensions() == 'Dawn features'
    assert observed == [3379, 32883, 7939]
    assert not hasattr(module, 'Canvas')
    module.get_max_texture_sizes.cache_clear()

    def fail(name):
        raise RuntimeError('Dawn device unavailable')

    monkeypatch.setattr(gl, 'glGetParameter', fail)
    with pytest.raises(RuntimeError, match='Dawn device unavailable'):
        module.get_max_texture_sizes()


def test_layer_cleanup_does_not_swallow_dawn_errors(patched_source):
    source = (patched_source / 'src/napari/_vispy/canvas.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    finish_calls = [node for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'finish']
    assert len(finish_calls) == 1
    assert 'contextlib.suppress' not in source
    assert 'GLError' not in source
