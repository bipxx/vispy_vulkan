# SPDX-License-Identifier: AGPL-3.0-only
"""The pinned Glue Qt QWidget startup must not select a global GL renderer."""

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'prepare_napari_no_opengl', ROOT / 'tools/prepare_napari_no_opengl.py')
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)
MANIFEST = ROOT / 'compat/host-patches/glue-qt-0.4.2-provenance.json'


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    archive = os.environ.get('GLUE_QT_SOURCE_ARCHIVE')
    if not archive:
        pytest.skip('set GLUE_QT_SOURCE_ARCHIVE to pinned glue-qt sdist')
    return PREPARE.prepare(archive, tmp_path_factory.mktemp('glue-qt') / 'source', MANIFEST)


def test_exact_source_retains_widget_startup_and_original_license(source):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name, hashes in manifest['files'].items():
        assert PREPARE.sha256(source / name) == hashes['after_sha256']
    text = (source / 'glue_qt/utils/app.py').read_text(encoding='utf-8')
    tree = ast.parse(text)
    imported = [alias.name for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) for alias in node.names]
    assert 'QtQuick' not in imported
    assert not any(isinstance(node, ast.Attribute) and node.attr == 'setGraphicsApi'
                   for node in ast.walk(tree))
    assert 'QtWidgets.QApplication' in text
    assert 'setWindowIcon' in text and 'setFont' in text
    assert 'setQuitOnLastWindowClosed' in text
    assert (source / 'LICENSE').is_file()
    assert (source / 'LICENSE-AGPL').read_bytes() == (ROOT / 'LICENSE').read_bytes()


def test_actual_selected_profile_can_create_glue_qapplication_without_quick(tmp_path):
    python = os.environ.get('GLUE_QT_PROFILE_PYTHON')
    if not python:
        pytest.skip('set GLUE_QT_PROFILE_PYTHON to a fresh installed host profile')
    code = '''import sys,importlib.abc
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name=='OpenGL' or name.startswith('OpenGL.') or 'QtOpenGL' in name or name.endswith('.QtQuick'):
            raise RuntimeError('unexpected GUI runtime import: '+name)
sys.meta_path.insert(0,Deny())
from glue.config import settings
settings.FONT_SIZE=12
from glue_qt.utils.app import get_qapp
from qtpy.QtWidgets import QApplication,QWidget
assert QApplication.instance() is None
application=get_qapp()
assert application is QApplication.instance() and get_qapp() is application
widget=QWidget();widget.show();application.processEvents();widget.close()
assert not any('QtQuick' in name or 'QtOpenGL' in name for name in sys.modules)
print('actual Glue QApplication initialized with QWidget profile')
'''
    result = subprocess.run([python, '-I', '-B', '-c', code], cwd=tmp_path,
                            env=dict(os.environ, QT_API='pyqt6'),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
