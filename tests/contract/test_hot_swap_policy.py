# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap gates: renderer GL activity and any GL context or draw fail; host GL activity is recorded."""
import json
import sys

import pytest

from tools import audit_hot_swap as audit
from tools.hot_swap.derive_observer import DERIVED, STRICT, derive
from tools.hot_swap.policy import assess_hot_swap, attribute, context_or_draw, correlate, renderer_roots, static_scan

CLEAN = {'runtime': [], 'test_only': [], 'errors': [], 'complete': True}
COMPLETE = dict(attribution_complete=True, native_api_complete=True, native_loads_complete=True,
                execution_succeeded=True, static=CLEAN)
ROOTS = renderer_roots(r'C:\env\Lib\site-packages\vispy\__init__.py')


def test_attribution_uses_the_innermost_frame_past_machinery_gl_modules_and_shims():
    assert attribute(['importlib._bootstrap', 'OpenGL.platform.win32', 'OpenGL.error', 'napari._vispy.canvas']) == 'host'
    assert attribute(['_frozen_importlib', 'OpenGL.GL', 'vispy.gloo.gl']) == 'renderer'
    assert attribute(['ctypes', 'OpenGL.platform', 'importlib']) == 'unattributed'
    # A binding shim forwards to the Qt GL module: whoever imported the shim is the cause.
    assert attribute(['PyQt6.QtOpenGL', 'qtpy.QtOpenGL', 'vispy.app.backends._qt']) == 'renderer'
    assert attribute(['PyQt6.QtOpenGL', 'qtpy.QtOpenGLWidgets', 'napari._qt.qt_viewer']) == 'host'
    assert attribute(['threading', 'vispy.app.timer']) == 'renderer'


def test_renderer_gl_activity_fails():
    events = [{'kind': 'python_import', 'name': 'OpenGL.GL', 'attribution': 'renderer'}]
    gates = assess_hot_swap(events, **COMPLETE)
    assert gates['renderer_gl'] == 'FAIL' and gates['no_gl_context_or_draw'] == 'PASS'


def test_host_gl_activity_is_recorded_not_failed():
    events = [{'kind': 'python_import', 'name': 'OpenGL.error', 'attribution': 'host'},
              {'kind': 'ctypes_load_request', 'path': 'opengl32', 'attribution': 'host'},
              {'kind': 'native_load', 'path': r'C:\Windows\System32\opengl32.dll', 'attribution': 'host'}]
    gates = assess_hot_swap(events, **COMPLETE)
    assert gates['renderer_gl'] == 'PASS' and len(gates['host_gl_events']) == 3


def test_any_context_or_draw_call_fails_under_any_export_name():
    for name in ('wglCreateContext', 'wglMakeCurrent', 'wglSwapBuffers', 'glDrawArrays', 'glClear', 'eglMakeCurrent',
                 'glBegin', 'glDispatchCompute', 'glBlitFramebuffer', 'glMultiDrawElements', 'glClearBufferfv',
                 'OSMesaCreateContextExt', 'OSMesaMakeCurrent', 'glEvalMesh2', 'glEvalPoint1', 'glArrayElement',
                 'glDrawPixels', 'glDrawElementsInstanced', 'glDrawTransformFeedback'):
        call = {'kind': 'native_gl_call', 'name': name, 'attribution': 'host'}
        assert assess_hot_swap([call], **COMPLETE)['no_gl_context_or_draw'] == 'FAIL', name
    alias = {'kind': 'native_gl_call', 'name': 'glQueryAlias', 'aliases': ['glQueryAlias', 'glDrawArrays'],
             'attribution': 'host'}
    assert assess_hot_swap([alias], **COMPLETE)['no_gl_context_or_draw'] == 'FAIL'
    for name in ('wglGetProcAddress', 'wglGetCurrentContext', 'glGetError', 'glGetString', 'glBeginQuery',
                 'glClearColor', 'glClearDepth', 'glClearStencil', 'glDrawBuffer', 'glDrawBuffers',
                 'glDrawBuffersARB', 'OSMesaGetCurrentContext'):
        assert not context_or_draw(name), name


def test_incomplete_coverage_static_references_or_unattributed_activity_are_unverified():
    unattributed = [{'kind': 'native_load', 'path': 'opengl32.dll', 'attribution': 'unattributed'}]
    assert assess_hot_swap(unattributed, **COMPLETE)['renderer_gl'] == 'UNVERIFIED'
    for flag in ('attribution_complete', 'native_api_complete', 'native_loads_complete', 'execution_succeeded'):
        assert assess_hot_swap([], **{**COMPLETE, flag: False})['renderer_gl'] == 'UNVERIFIED', flag
    referenced = {**CLEAN, 'runtime': [{'file': 'gloo/glir.py', 'line': 1, 'reference': 'OpenGL.GL'}]}
    assert assess_hot_swap([], **{**COMPLETE, 'static': referenced})['renderer_gl'] == 'UNVERIFIED'
    assert assess_hot_swap([], **{**COMPLETE, 'static': {**CLEAN, 'complete': False}})['renderer_gl'] == 'UNVERIFIED'
    assert assess_hot_swap([], **{**COMPLETE, 'native_api_complete': False})['no_gl_context_or_draw'] == 'UNVERIFIED'


def test_a_host_query_call_is_recorded_but_a_renderer_call_fails():
    query = {'kind': 'native_gl_call', 'name': 'wglGetCurrentContext', 'attribution': 'host'}
    gates = assess_hot_swap([query], **COMPLETE)
    assert gates['no_gl_context_or_draw'] == 'PASS' and gates['renderer_gl'] == 'PASS' and gates['host_gl_events']
    gates = assess_hot_swap([{**query, 'name': 'glGetError', 'attribution': 'renderer'}], **COMPLETE)
    assert gates['renderer_gl'] == 'FAIL' and gates['no_gl_context_or_draw'] == 'PASS'


def test_the_native_caller_attributes_first_for_any_renderer_install_layout():
    qt = {'path': r'C:\env\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll'}
    for path in (r'C:\env\Lib\site-packages\vispy\_dawn.cp312-win_amd64.pyd',
                 r'C:\env\Lib\site-packages\vispy.libs\webgpu_dawn.dll'):
        binding = {'kind': 'native_gl_binding', 'name': 'glGetError', 'direct_caller': {'path': path}}
        assert correlate([binding], [], ROOTS)[0]['attribution'] == 'renderer', path
    editable = renderer_roots(r'C:\src\vispy_vulkan\src\vispy\__init__.py')
    binding = {'kind': 'native_gl_binding', 'name': 'glGetError',
               'direct_caller': {'path': r'C:\src\vispy_vulkan\src\vispy\_dawn.pyd'}}
    assert correlate([binding], [], editable)[0]['attribution'] == 'renderer'
    native = [{'kind': 'native_gl_call', 'name': 'wglGetCurrentContext', 'direct_caller': qt},
              {'kind': 'native_load', 'path': r'C:\Windows\System32\opengl32.dll', 'loader_caller': qt}]
    assert [e['attribution'] for e in correlate(native, [], ROOTS)] == ['host', 'host']


def test_gl_calls_through_python_cannot_be_attributed():
    for caller in (r'C:\python\DLLs\libffi-8.dll', r'C:\python\DLLs\_ctypes.pyd', None):
        call = {'kind': 'native_gl_call', 'name': 'wglGetProcAddress', 'direct_caller': {'path': caller}, 'wall': 10.0}
        lookup = [{'kind': 'ctypes_symbol', 'name': 'wglGetProcAddress', 'attribution': 'host', 'wall': 9.9}]
        assert correlate([call], lookup, ROOTS)[0]['attribution'] == 'unattributed', caller


def test_python_explanations_must_precede_the_native_event_closely():
    host_load = [{'kind': 'ctypes_load_request', 'path': 'opengl32', 'attribution': 'host', 'wall': 10.0}]
    load = {'kind': 'native_load', 'path': r'C:\Windows\System32\opengl32.dll',
            'loader_caller': {'path': r'C:\python\DLLs\_ctypes.pyd'}}
    assert correlate([{**load, 'wall': 10.2}], host_load, ROOTS)[0]['attribution'] == 'host'
    assert correlate([{**load, 'wall': 5.0}], host_load, ROOTS)[0]['attribution'] == 'unattributed'  # load before
    assert correlate([{**load, 'wall': 60.0}], host_load, ROOTS)[0]['attribution'] == 'unattributed'  # long after
    unknown = {'kind': 'native_load', 'path': r'C:\Windows\System32\opengl32.dll', 'loader_caller': {'path': None},
               'wall': 10.2}
    assert correlate([unknown], [], ROOTS)[0]['attribution'] == 'unattributed'


def test_qt_imports_explain_only_qt_gl_files():
    imports = [{'kind': 'python_import', 'name': 'PyQt6.QtOpenGL', 'attribution': 'host', 'wall': 10.0}]
    python = {'path': r'C:\python\python312.dll'}
    qt = {'kind': 'native_load', 'path': r'C:\env\PyQt6\QtOpenGL.pyd', 'loader_caller': python, 'wall': 10.1}
    qt_dll = {'kind': 'native_load', 'path': r'C:\env\PyQt6\Qt6\bin\Qt6OpenGL.dll', 'loader_caller': {'path': None},
              'wall': 10.1}
    egl = {'kind': 'native_load', 'path': r'C:\env\libEGL.dll', 'loader_caller': {'path': None}, 'wall': 10.1}
    assert [e['attribution'] for e in correlate([qt, qt_dll, egl], imports, ROOTS)] == ['host', 'host', 'unattributed']
    renderer_import = [{**imports[0], 'attribution': 'renderer'}]
    assert correlate([qt], renderer_import, ROOTS)[0]['attribution'] == 'renderer'


def test_a_qt_gl_library_loaded_by_a_non_gl_qt_import_takes_that_import():
    # qtpy imports PySide6.QtDataVisualization, whose Qt library links Qt6OpenGL.dll (W6, PySide6).
    loaded = {'kind': 'native_load', 'path': r'C:\env\PySide6\Qt6OpenGL.dll', 'loader_caller': {'path': None},
              'wall': 10.2}
    qtpy = [{'kind': 'qt_binding_import', 'name': 'PySide6.QtCore', 'attribution': 'renderer', 'wall': 9.0},
            {'kind': 'qt_binding_import', 'name': 'PySide6.QtDataVisualization', 'attribution': 'host', 'wall': 10.1}]
    assert correlate([loaded], qtpy, ROOTS)[0]['attribution'] == 'host'  # the nearest preceding Qt import
    by_renderer = [{**qtpy[1], 'attribution': 'renderer'}]
    assert correlate([loaded], by_renderer, ROOTS)[0]['attribution'] == 'renderer'
    assert correlate([{**loaded, 'wall': 12.0}], qtpy, ROOTS)[0]['attribution'] == 'unattributed'  # too late
    opengl32 = {**loaded, 'path': r'C:\Windows\System32\opengl32.dll'}
    assert correlate([opengl32], qtpy, ROOTS)[0]['attribution'] == 'unattributed'  # only Qt's own GL libraries
    assert assess_hot_swap(qtpy, **COMPLETE)['host_gl_events'] == []  # explanations are not GL activity


def test_static_scan_finds_renderer_gl_references_but_not_test_modules(tmp_path):
    package = tmp_path / 'vispy'
    (package / 'gloo' / 'tests').mkdir(parents=True)
    (package / 'testing').mkdir()
    (package / '__init__.py').write_text('')
    (package / 'gloo' / 'glir.py').write_text('def f():\n    import OpenGL.GL as gl\n    return gl\n')
    (package / 'gloo' / 'loader.py').write_text('import ctypes\nlib = ctypes.CDLL("opengl32")\n')
    (package / 'app.py').write_text('from PyQt6 import QtOpenGLWidgets\nimport importlib\nimportlib.import_module("OpenGL.GL")\n')
    (package / 'gloo' / 'tests' / 'test_x.py').write_text('import OpenGL.GL\n')
    (package / 'testing' / '_testing.py').write_text('from OpenGL import GL\n')
    scan = static_scan(package, binary_imports=lambda path: [])
    runtime = sorted((r['file'], r['reference']) for r in scan['runtime'])
    assert ('gloo/glir.py', 'OpenGL.GL') in runtime and ('gloo/loader.py', "CDLL('opengl32')") in runtime
    assert ('app.py', 'PyQt6.QtOpenGLWidgets') in runtime and ('app.py', 'OpenGL.GL') in runtime
    assert {r['file'] for r in scan['test_only']} == {'gloo/tests/test_x.py', 'testing/_testing.py'}
    assert scan['complete']
    (package / 'native.pyd').write_bytes(b'')
    scan = static_scan(package, binary_imports=lambda path: ['opengl32.dll', 'KERNEL32.dll'])
    assert any(r['reference'] == 'imports opengl32.dll' for r in scan['runtime'])
    # A renamed GL library is still found by the GL entry points it imports.
    renamed = [{'name': 'libEGL-1a2b3c.dll', 'symbols': ['eglGetDisplay']}, {'name': 'KERNEL32.dll', 'symbols': ['GlobalAlloc']}]
    found = [r for r in static_scan(package, binary_imports=lambda path: renamed)['runtime'] if 'gl_symbols' in r]
    assert [(r['reference'], r['gl_symbols']) for r in found] == [('imports libEGL-1a2b3c.dll', ['eglGetDisplay'])]


def test_the_observer_is_the_strict_observer_with_the_documented_changes():
    assert derive(STRICT.read_bytes()) == DERIVED.read_bytes()


def test_an_unreadable_worker_report_or_a_tool_error_is_never_a_verdict(tmp_path, monkeypatch):
    assert audit.read_worker(tmp_path / 'missing.json')['status'] == 'MISSING_WORKER_REPORT'
    truncated = tmp_path / 'truncated.json'
    truncated.write_text('{"status": "PASS_SCENARIO", "events": [', encoding='utf-8')
    assert audit.read_worker(truncated)['status'] == 'UNREADABLE_WORKER_REPORT'

    def fail(args):
        raise RuntimeError('observer failed')

    monkeypatch.setattr(audit, 'run', fail)
    output = tmp_path / 'report.json'
    monkeypatch.setattr(sys, 'argv', ['audit_hot_swap.py', '--python', 'python', '--script', 's.py',
                                      '--output', str(output)])
    assert audit.main() == 3
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['status'] == 'TOOL_ERROR' and set(report['gates'].values()) == {'UNVERIFIED'}
    with pytest.raises(SystemExit) as usage:  # an existing report path is a usage error, not a verdict
        audit.main()
    assert usage.value.code == 3


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
