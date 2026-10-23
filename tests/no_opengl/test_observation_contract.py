"""Do not convert collector blind spots or attempted loads into absence proof."""
import json
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from no_opengl.dependencies import BinaryError, elf_image, pe_image
from no_opengl.policy import assess, import_reason, is_gl_entrypoint, library_reason


@pytest.mark.parametrize('name', ['opengl32.dll', 'libGL.so.1', 'libEGL.so.1', 'libGLX_mesa.so.0',
                                  'Qt6OpenGL.dll', 'QtOpenGL.abi3.so', 'libGLdispatch.so.0', 'libglapi.so.0',
                                  'libQt6OpenGL.so.6', 'libQt5OpenGLWidgets.so.5.15.2',
                                  'libQt6OpenGL.6.dylib', '/qt/QtOpenGLWidgets.framework/QtOpenGLWidgets',
                                  '/System/Library/Frameworks/OpenGL.framework/OpenGL'])
def test_api_specific_runtimes_are_rejected(name):
    assert library_reason(name)


@pytest.mark.parametrize('name', ['nvoglv64.dll', 'libvulkan_lvp.so', 'libglslang.so', 'libX11.so.6'])
def test_shared_vulkan_driver_and_compiler_are_not_gl_loaders(name):
    assert library_reason(name) is None


def test_facade_aliases_are_allowed_but_raw_implementations_are_not():
    assert import_reason('vispy.gloo.gl.gl2') is None
    assert import_reason('vispy.gloo.gl.glplus') is None
    assert import_reason('OpenGL.error')
    assert import_reason('PyQt6.QtOpenGLWidgets')


def test_incomplete_native_observation_never_passes():
    result = assess([], native_loads_complete=False, native_api_complete=False, execution_succeeded=True)
    assert result['no_gl_execution'] == result['no_gl_loads'] == 'UNVERIFIED'


def test_final_snapshot_cannot_replace_transient_native_load_evidence():
    events = [{'kind': 'native_load', 'path': '/tmp/libGL.so.1'},
              {'kind': 'native_unload', 'path': '/tmp/libGL.so.1'}]
    assert assess(events, native_loads_complete=False, native_api_complete=False,
                  execution_succeeded=True)['no_gl_loads'] == 'FAIL'


def test_lookup_without_call_already_fails_execution_gate():
    result = assess([{'kind': 'native_gl_binding', 'name': 'eglCreateContext'}],
                    native_loads_complete=False, native_api_complete=False, execution_succeeded=False)
    assert result['no_gl_execution'] == 'FAIL'


def test_denied_ctypes_request_is_not_falsely_reported_as_actual_load():
    result = assess([{'kind': 'ctypes_load_request', 'path': 'opengl32.dll'}],
                    native_loads_complete=True, native_api_complete=True, execution_succeeded=False)
    assert result['violations']
    assert result['no_gl_loads'] == 'UNVERIFIED'


def test_entrypoint_classifier_does_not_confuse_glslang():
    assert is_gl_entrypoint('glGetString') and is_gl_entrypoint('wglCreateContext')
    assert not is_gl_entrypoint('glslang_compile')


def test_pe_records_normal_delayed_imports_symbols_and_export_ordinals():
    # Independent minimal PE64 fixture: no executable code and no compiler needed.
    data = bytearray(0x900)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, 0x84, 0x8664, 1, 0, 0, 0, 240, 0)
    optional = 0x98
    struct.pack_into('<H', data, optional, 0x20b)
    struct.pack_into('<Q', data, optional + 24, 0x140000000)
    struct.pack_into('<I', data, optional + 108, 16)
    section = optional + 240
    struct.pack_into('<IIII', data, section + 8, 0x700, 0x1000, 0x700, 0x200)
    def directory(index, offset, size):
        struct.pack_into('<II', data, optional + 112 + index * 8, offset - 0x200 + 0x1000, size)
    def rva(offset):
        return offset - 0x200 + 0x1000
    directory(1, 0x200, 40)
    struct.pack_into('<IIIII', data, 0x200, rva(0x300), 0, 0, rva(0x280), rva(0x300))
    data[0x280:0x28d] = b'normal.dll\0\0\0'
    struct.pack_into('<QQ', data, 0x300, rva(0x330), 0)
    data[0x330:0x33d] = b'\0\0glGetError\0'
    directory(13, 0x380, 64)
    struct.pack_into('<IIIIIIII', data, 0x380, 1, rva(0x400), 0, rva(0x430), rva(0x430), 0, 0, 0)
    data[0x400:0x40c] = b'opengl32.dll'
    data[0x40c] = 0
    struct.pack_into('<QQ', data, 0x430, rva(0x460), 0)
    data[0x460:0x472] = b'\0\0wglCreateContext\0'
    directory(0, 0x500, 0x80)
    struct.pack_into('<IIHHIIIIIII', data, 0x500, 0, 0, 0, 0, 0, 7, 1, 1, rva(0x540), rva(0x548), rva(0x550))
    struct.pack_into('<I', data, 0x540, rva(0x600))
    struct.pack_into('<I', data, 0x548, rva(0x560))
    struct.pack_into('<H', data, 0x550, 0)
    data[0x560:0x56b] = b'auditSafe\0\0'
    result = pe_image(bytes(data))
    assert result['imports'] == [dict(name='normal.dll', delay=False, symbols=['glGetError']),
                                 dict(name='opengl32.dll', delay=True, symbols=['wglCreateContext'])]
    assert result['exports'][0]['ordinal'] == 7


def test_bad_binary_does_not_become_an_empty_closure():
    with pytest.raises(BinaryError):
        elf_image(b'not a binary')


def test_mandatory_application_matrix_is_explicitly_unqualified():
    matrix = json.loads((ROOT / 'compat/no-opengl-matrix.json').read_text())
    mandatory = [row for row in matrix['rows'] if row['mandatory']]
    assert len({row['id'] for row in matrix['rows']}) == len(matrix['rows'])
    for platform in ('windows-vulkan', 'wsl-linux-lavapipe-x11'):
        rows = [row for row in mandatory if row['platform'] == platform]
        assert {row['application'] for row in rows} == {'headless', 'qwidget', 'napari', 'glue-vispy-viewers', 'napari-threedee'}
        assert {row['binding'] for row in rows if row['application'] == 'qwidget'} == {'pyqt5', 'pyqt6', 'pyside6'}
    assert all(row['status'] == 'PENDING' and not row['evidence'] for row in mandatory)
