# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned Glue preparation keeps host checks and original licensing intact."""

import ast
from configparser import ConfigParser
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
MANIFEST = ROOT / 'compat/host-patches/glue-vispy-viewers-1.4.0-provenance.json'


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    archive = os.environ.get('GLUE_SOURCE_ARCHIVE')
    if not archive:
        pytest.skip('set GLUE_SOURCE_ARCHIVE to pinned glue-vispy-viewers sdist')
    return PREPARE.prepare(archive, tmp_path_factory.mktemp('glue') / 'source', MANIFEST)


def test_exact_patched_source_preserves_licenses_and_removes_legacy_requirements(source):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name, hashes in manifest['files'].items():
        assert PREPARE.sha256(source / name) == hashes['after_sha256']
        if name.endswith('.py'):
            tree = ast.parse((source / name).read_text(encoding='utf-8'))
            assert not any(isinstance(node, ast.Import) and any(
                alias.name.split('.')[0] == 'OpenGL' for alias in node.names)
                for node in ast.walk(tree))
    config = ConfigParser()
    config.read(source / 'setup.cfg', encoding='utf-8')
    dependencies = config['options']['install_requires'].lower().split()
    assert 'pyopengl' not in dependencies and 'glfw' not in dependencies
    assert {'LICENSE', 'LICENSE-AGPL', 'DAWN-PATCH-LICENSING.txt'} <= set(
        config['metadata']['license_files'].split())
    assert (source / 'LICENSE').is_file()
    assert (source / 'LICENSE-AGPL').read_bytes() == (ROOT / 'LICENSE').read_bytes()


def test_unavailable_renderer_still_takes_real_host_error_path(source):
    tree = ast.parse((source / 'glue_vispy_viewers/common/qt/data_viewer.py').read_text(encoding='utf-8'))
    paint = next(node for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.name == 'paintEvent')
    calls = [node.func.attr for node in ast.walk(paint)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    assert 'context' in calls
    assert 'critical' in calls
    assert 'close' in calls
