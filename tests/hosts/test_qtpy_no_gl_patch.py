# SPDX-License-Identifier: AGPL-3.0-only
"""Test the pinned QtPy patch using real bindings and forbidden-import guards."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'prepare_napari_no_opengl', ROOT / 'tools/prepare_napari_no_opengl.py')
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


@pytest.fixture(scope='module')
def source_roots(tmp_path_factory):
    qtpy_archive = os.environ.get('QTPY_SOURCE_ARCHIVE')
    napari_archive = os.environ.get('NAPARI_SOURCE_ARCHIVE')
    if not qtpy_archive or not napari_archive:
        pytest.skip('set QTPY_SOURCE_ARCHIVE and NAPARI_SOURCE_ARCHIVE to pinned sdists')
    output = tmp_path_factory.mktemp('dawn-hosts')
    qtpy = PREPARE.prepare(qtpy_archive, output / 'qtpy',
                          ROOT / 'compat/host-patches/qtpy-2.4.3-provenance.json')
    napari = PREPARE.prepare(napari_archive, output / 'napari')
    return qtpy, napari


def test_qtpy_distribution_declares_both_original_and_agpl_licenses(source_roots):
    qtpy, _ = source_roots
    from configparser import ConfigParser
    config = ConfigParser()
    config.read(qtpy / 'setup.cfg', encoding='utf-8')
    declared = config['metadata']['license_files'].split()
    assert {'LICENSE.txt', 'LICENSE-AGPL', 'DAWN-PATCH-LICENSING.txt'} <= set(declared)
    assert config['metadata']['license'] == 'AGPL-3.0-only'
    assert (qtpy / 'LICENSE.txt').is_file()
    assert (qtpy / 'LICENSE-AGPL').read_bytes() == (ROOT / 'LICENSE').read_bytes()


def test_real_napari_import_chain_and_explicit_gl_export_errors(source_roots):
    qtpy, napari = source_roots
    sites = [str(Path(p).resolve()) for p in sys.path
             if p and Path(p).name == 'site-packages' and Path(p).is_dir()]
    code = '''import sys, importlib.abc, ctypes
sys.path.extend(%r)
for p in %r: sys.path.insert(0,p)
# Upstream supports source-tree imports under pytest when another napari is installed.
import pytest
attempts=[]
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name=='OpenGL' or name.startswith('OpenGL.') or 'QtOpenGL' in name:
            attempts.append(name)
            raise RuntimeError('forbidden import: '+name)
sys.meta_path.insert(0,Deny())
def audit(event,args):
    if event=='ctypes.dlopen' and args and args[0]:
        name=str(args[0]).lower()
        if any(x in name for x in ('opengl32','libgl.so','libegl','libgles','osmesa')):
            attempts.append(name)
            raise RuntimeError('forbidden ctypes load: '+name)
sys.addaudithook(audit)
from qtpy import QtGui,QtWidgets
image=QtGui.QImage(2,2,QtGui.QImage.Format.Format_RGBA8888)
image.fill(QtGui.QColor('red'))
assert image.pixelColor(0,0).red()==255
for module,name in ((QtGui,'QOpenGLContext'),(QtGui,'QOpenGLBuffer'),(QtWidgets,'QOpenGLWidget')):
    try: getattr(module,name)
    except RuntimeError as e: assert 'disabled' in str(e)
    else: raise AssertionError('GL-only export was exposed: '+name)
import napari._vispy.canvas, napari._qt.qt_event_loop
assert napari.__file__.startswith(%r)
assert sys.modules['qtpy'].__file__.startswith(%r)
assert not attempts,attempts
print('real host import chain passed; native Qt dependency gates remain separate')
''' % (sites, [str(ROOT / 'src'), str(napari / 'src'), str(qtpy)],
       str(napari), str(qtpy))
    env = dict(os.environ, QT_API='pyqt6')
    result = subprocess.run([sys._base_executable, '-I', '-B', '-c', code],
                            env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
