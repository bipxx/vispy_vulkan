# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap Linux observer: the derived collectors, Linux paths in the policy, and the controller's Linux dispatch.

These are CPU checks for every platform. The native Linux controls (compiling the collectors, ptrace step-over and
stop) are in test_hot_swap_linux_native.py.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys

from tools import audit_hot_swap as audit
from tools.hot_swap import policy
from tools.hot_swap.policy import assess_hot_swap, context_or_draw, correlate, renderer_roots, static_scan

CLEAN = {'runtime': [], 'test_only': [], 'errors': [], 'complete': True}
COMPLETE = dict(attribution_complete=True, native_api_complete=True, native_loads_complete=True,
                execution_succeeded=True, static=CLEAN)
COVERAGE = ('startup_and_transient_native_loads', 'native_public_gl_export_breakpoints',
            'native_entrypoint_resolution', 'process_tree')
SITE = '/env/lib/python3.12/site-packages'
LIBPYTHON = '/home/u/.local/share/uv/python/cpython-3.12.8-linux-x86_64-gnu/lib/libpython3.12.so.1.0'
# The families documented in docs/hot-swap-gates.md, as the Windows observer first implemented them.
DOCUMENTED_CONTEXT = re.compile(r'^(?:wgl(?:Create|Make|Swap|Share|Copy|Delete)|eglCreate|eglMakeCurrent|eglSwap|'
                                r'glX(?:Create|MakeCurrent|MakeContextCurrent|Swap)|OSMesa(?:Create|MakeCurrent)|'
                                r'SwapBuffers$)')
DOCUMENTED_DRAW = re.compile(r'^gl(?:Draw(?!Buffer)|MultiDraw|Clear$|ClearBuffer|ClearNamedFramebuffer|ClearTex|Begin$|'
                             r'CallLists?$|Dispatch|Blit|Accum$|Bitmap$|CopyPixels$|Rect|Eval(?:Mesh|Point)|'
                             r'ArrayElement$)')
NAMES = ('wglCreateContext', 'wglMakeCurrent', 'wglSwapBuffers', 'wglShareLists', 'wglCopyContext', 'wglDeleteContext',
         'wglGetProcAddress', 'wglGetCurrentContext', 'eglCreateContext', 'eglCreateWindowSurface', 'eglMakeCurrent',
         'eglSwapBuffers', 'eglGetDisplay', 'eglInitialize', 'eglGetProcAddress', 'glXCreateContextAttribsARB',
         'glXCreateNewContext', 'glXMakeCurrent', 'glXMakeContextCurrent', 'glXMakeCurrentReadSGI', 'glXSwapBuffers',
         'glXQueryExtension', 'glXGetProcAddressARB', 'OSMesaCreateContextExt', 'OSMesaMakeCurrent',
         'OSMesaGetCurrentContext', 'SwapBuffers', 'SwapBuffersEXT', 'glDrawArrays', 'glDrawElementsInstanced',
         'glDrawTransformFeedback', 'glDrawPixels', 'glDrawBuffer', 'glDrawBuffers', 'glDrawBuffersARB', 'glMultiDrawArrays',
         'glClear', 'glClearColor', 'glClearDepth', 'glClearStencil', 'glClearBufferfv', 'glClearNamedFramebufferfv',
         'glClearTexImage', 'glBegin', 'glBeginQuery', 'glCallList', 'glCallLists', 'glCallListsARB', 'glDispatchCompute',
         'glBlitFramebuffer', 'glAccum', 'glBitmap', 'glCopyPixels', 'glRectf', 'glEvalMesh2', 'glEvalPoint1',
         'glEvalCoord1f', 'glArrayElement', 'glArrayElementEXT', 'glGetError', 'glGetString', 'glHotSwapQueryControl')


def elf(undefined=(), defined=()):
    """A minimal little-endian ELF64 shared object with a dynamic symbol table and no program headers."""
    names = [*undefined, *defined]
    strings, offsets = b'\0', {}
    for name in names:
        offsets[name] = len(strings)
        strings += name.encode() + b'\0'
    symbols = bytes(24)
    for name in undefined:
        symbols += struct.pack('<IBBHQQ', offsets[name], 0x12, 0, 0, 0, 0)  # global function, SHN_UNDEF
    for name in defined:
        symbols += struct.pack('<IBBHQQ', offsets[name], 0x12, 0, 1, 0x1000, 8)
    strings_at = 64
    symbols_at = strings_at + len(strings) + (-(strings_at + len(strings)) % 8)
    sections_at = symbols_at + len(symbols)
    header = b'\x7fELF\x02\x01\x01' + bytes(9) + struct.pack('<HHIQQQIHHHHHH', 3, 62, 1, 0, 0, sections_at, 0, 64, 56, 0,
                                                             64, 3, 0)
    sections = bytes(64) + struct.pack('<IIQQQQIIQQ', 0, 3, 0, 0, strings_at, len(strings), 0, 0, 1, 0)
    sections += struct.pack('<IIQQQQIIQQ', 0, 11, 0, 0, symbols_at, len(symbols), 1, 1, 8, 24)
    data = bytearray(sections_at + len(sections))
    data[:64] = header
    data[strings_at:strings_at + len(strings)] = strings
    data[symbols_at:symbols_at + len(symbols)] = symbols
    data[sections_at:] = sections
    return bytes(data)


def test_the_linux_collectors_are_the_strict_ones_with_the_documented_changes():
    from tools.hot_swap.derive_linux_observer import FILES
    assert [derived.name for _, derived, _ in FILES] == ['loader_audit_linux.c', 'debugger_linux.c', 'linux_observer.py']
    for strict, derived, derive in FILES:
        assert strict.parent.name == 'no_opengl' and derived.parent.name == 'hot_swap'
        assert derive(strict.read_bytes()) == derived.read_bytes(), derived.name


def test_the_context_and_draw_tables_are_the_documented_families():
    tables = (*policy.CONTEXT_PREFIXES, *policy.CONTEXT_NAMES, *policy.DRAW_PREFIXES, *policy.DRAW_NAMES,
              *policy.NOT_DRAW_PREFIXES)
    corpus = set()
    for name in (*tables, *NAMES):
        corpus |= {name, name + 'ARB', name + 's', name + 'Buffer', name[:-1], name.lower(), name.upper()}
    for name in sorted(corpus):
        assert context_or_draw(name) == bool(DOCUMENTED_CONTEXT.match(name) or DOCUMENTED_DRAW.match(name)), name
    # The Linux observer copies these tables into C, so they must be plain identifiers.
    assert all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) for name in tables)


def test_a_posix_vispy_origin_gives_posix_renderer_roots():
    assert renderer_roots(SITE + '/vispy/__init__.py') == [SITE + '/vispy', SITE + '/vispy.libs']
    assert renderer_roots('/src/vispy_vulkan/src/vispy') == ['/src/vispy_vulkan/src/vispy', '/src/vispy_vulkan/src/vispy.libs']
    windows = r'C:\env\Lib\site-packages'
    assert renderer_roots(windows + r'\vispy\__init__.py') == [windows + r'\vispy', windows + r'\vispy.libs']


def test_linux_native_callers_attribute_the_renderer_and_hosts():
    roots = renderer_roots(SITE + '/vispy/__init__.py')
    for caller in (SITE + '/vispy/_dawn.cpython-312-x86_64-linux-gnu.so', SITE + '/vispy.libs/libwebgpu_dawn-1a2b3c4d.so',
                   '/other/site-packages/vispy.libs/libvulkan-5e6f.so.1'):
        call = {'kind': 'native_gl_call', 'name': 'glGetError', 'direct_caller': {'path': caller}}
        assert correlate([call], [], roots)[0]['attribution'] == 'renderer', caller
    plugin = {'path': SITE + '/PyQt6/Qt6/plugins/platforms/libqxcb.so'}
    native = [{'kind': 'native_gl_call', 'name': 'glXQueryExtension', 'direct_caller': plugin},
              {'kind': 'native_gl_binding', 'name': 'eglGetDisplay', 'direct_caller': {'path': SITE + '/PyQt6/Qt6/lib/libQt6Gui.so.6'}},
              # glvnd's libGL requests its own dispatch and GLX libraries.
              {'kind': 'native_load', 'path': '/usr/lib/x86_64-linux-gnu/libGLX.so.0',
               'loader_caller': {'path': '/usr/lib/x86_64-linux-gnu/libGL.so.1'}}]
    assert [e['attribution'] for e in correlate(native, [], roots)] == ['host', 'host', 'host']


def test_libpython_and_the_python_executable_act_for_python_code():
    roots = renderer_roots(SITE + '/vispy/__init__.py')
    for caller in (LIBPYTHON, '/usr/bin/python3.12', SITE + '/../../lib-dynload/_ctypes.cpython-312-x86_64-linux-gnu.so'):
        call = {'kind': 'native_gl_call', 'name': 'glXGetProcAddressARB', 'direct_caller': {'path': caller}, 'wall': 10.0}
        assert correlate([call], [], roots)[0]['attribution'] == 'unattributed', caller  # ctypes calls raise no event
        binding = {'kind': 'native_gl_binding', 'name': 'glGetString', 'direct_caller': {'path': caller}, 'wall': 10.0}
        lookup = [{'kind': 'ctypes_symbol', 'name': 'glGetString', 'attribution': 'renderer', 'wall': 9.9}]
        assert correlate([binding], lookup, roots)[0]['attribution'] == 'renderer', caller
        load = {'kind': 'native_load', 'path': '/usr/lib/x86_64-linux-gnu/libGL.so.1', 'loader_caller': {'path': caller},
                'wall': 10.1}
        request = [{'kind': 'ctypes_load_request', 'path': 'libGL.so.1', 'attribution': 'host', 'wall': 10.0}]
        assert correlate([load], request, roots)[0]['attribution'] == 'host', caller


def test_linux_qt_gl_libraries_are_explained_by_qt_imports():
    roots = renderer_roots(SITE + '/vispy/__init__.py')
    imports = [{'kind': 'python_import', 'name': 'PyQt6.QtOpenGL', 'attribution': 'host', 'wall': 10.0}]
    module = {'kind': 'native_load', 'path': SITE + '/PyQt6/QtOpenGL.abi3.so', 'loader_caller': {'path': LIBPYTHON},
              'wall': 10.1}
    library = {'kind': 'native_load', 'path': SITE + '/PyQt6/Qt6/lib/libQt6OpenGL.so.6', 'loader_caller': {'path': None},
               'wall': 10.1}
    widgets = {**library, 'path': SITE + '/PyQt6/Qt6/lib/libQt6OpenGLWidgets.so.6'}
    assert [e['attribution'] for e in correlate([module, library, widgets], imports, roots)] == ['host'] * 3
    renderer = [{**imports[0], 'attribution': 'renderer'}]
    assert correlate([library], renderer, roots)[0]['attribution'] == 'renderer'
    egl = {**library, 'path': '/usr/lib/x86_64-linux-gnu/libEGL.so.1'}
    assert correlate([egl], imports, roots)[0]['attribution'] == 'unattributed'  # only Qt's own GL libraries


def test_a_linux_renderer_scan_covers_vispy_libs_and_elf_symbol_imports(tmp_path):
    package = tmp_path / 'site-packages' / 'vispy'
    libs = package.parent / 'vispy.libs'
    package.mkdir(parents=True)
    libs.mkdir()
    (package / '__init__.py').write_text('')
    (package / '_dawn.cpython-312-x86_64-linux-gnu.so').write_bytes(elf(undefined=['vkCreateInstance', 'malloc']))
    (libs / 'libwebgpu_dawn-1a2b3c4d.so').write_bytes(elf(undefined=['glGetString', 'free', 'eglGetDisplay'],
                                                          defined=['wgpuCreateInstance', 'glDefinedHere']))
    (libs / 'libvulkan-5e6f.so.1.3').write_bytes(elf())
    scan = static_scan(package)
    assert scan['complete'] and scan['binaries'] == 3, scan
    found = [(Path(r['file']).name, r['gl_symbols']) for r in scan['runtime']]
    assert found == [('libwebgpu_dawn-1a2b3c4d.so', ['glGetString', 'eglGetDisplay'])]
    assert assess_hot_swap([], **{**COMPLETE, 'static': scan})['renderer_gl'] == 'UNVERIFIED'


def test_an_unreadable_elf_symbol_table_makes_the_scan_incomplete(tmp_path):
    package = tmp_path / 'vispy'
    package.mkdir()
    (package / '__init__.py').write_text('')
    whole = elf(undefined=['glGetString'])
    (package / '_dawn.cpython-312-x86_64-linux-gnu.so').write_bytes(whole[:-10])  # the section table is cut short
    scan = static_scan(package)
    assert not scan['complete'] and scan['errors'], scan


def test_linux_collector_records_carry_wall_time_callers_and_aliases():
    from tools.hot_swap.linux_observer import DEBUGGER_FIELDS, LOADER_FIELDS, record
    debugger = ('native_load', 'native_unload')
    load = record('native_load\t42\t/usr/lib/libEGL.so.1\t/opt/host/libhost.so\t1730000000.5', LOADER_FIELDS)
    assert load == {'kind': 'native_load', 'pid': 42, 'wall': 1730000000.5,
                    'detail': '/usr/lib/libEGL.so.1\t/opt/host/libhost.so', 'path': '/usr/lib/libEGL.so.1',
                    'loader_caller': {'path': '/opt/host/libhost.so'}}
    assert record('native_load\t42\tlinux-vdso.so.1\t\t1730000000.5', LOADER_FIELDS)['loader_caller'] == {'path': None}
    binding = record('native_gl_binding\t42\tglGetString\t/opt/host/libhost.so\t/usr/lib/libGL.so.1\t1730000000.5',
                     LOADER_FIELDS)
    assert (binding['name'], binding['direct_caller'], binding['path']) == (
        'glGetString', {'path': '/opt/host/libhost.so'}, '/usr/lib/libGL.so.1')
    assert record('native_image\t42\t0x7f00|/usr/lib/libGL.so.1\t1730000000.5', LOADER_FIELDS)['path'] == (
        '0x7f00|/usr/lib/libGL.so.1')
    call = record('native_gl_call\t42\tglHotSwapAliasControl\tglHotSwapAliasControl,glMultiDrawArrays\t/x/libGLX_a.so.0\t'
                  '/opt/host/libhost.so\t0x7f12\t1730000000.5', DEBUGGER_FIELDS, debugger)
    assert (call['name'], call['aliases'], call['path'], call['direct_caller']) == (
        'glHotSwapAliasControl', ['glHotSwapAliasControl', 'glMultiDrawArrays'], '/x/libGLX_a.so.0',
        {'path': '/opt/host/libhost.so', 'address': '0x7f12'})
    assert assess_hot_swap([{**call, 'attribution': 'host'}], **COMPLETE)['no_gl_context_or_draw'] == 'FAIL'
    task = record('debug_task_start\t42\ttid=42 parent_tid=0\t1730000000.5', DEBUGGER_FIELDS, debugger)
    assert task == {'kind': 'debug_task_start', 'pid': 42, 'wall': 1730000000.5, 'detail': 'tid=42 parent_tid=0'}
    mapped = record('native_load\t42\t/static/libx.so\t1730000000.5', DEBUGGER_FIELDS, debugger)
    assert mapped['path'] == '/static/libx.so' and 'loader_caller' not in mapped
    for line, fields in (('native_load\t42\t/x.so\t1730000000.5', LOADER_FIELDS),  # no requester field
                         ('native_load\tpid\t/x.so\t\t1730000000.5', LOADER_FIELDS),
                         ('audit_start\t42\tglibc LD_AUDIT', LOADER_FIELDS),  # no wall-clock time
                         ('audit_start\t42\tglibc LD_AUDIT\tnan', LOADER_FIELDS),
                         ('audit_start\t42\tglibc LD_AUDIT\t0', LOADER_FIELDS),
                         ('native_gl_call\t42\tglFoo\t/x.so\t1730000000.5', DEBUGGER_FIELDS)):
        assert record(line, fields) is None, line


def test_the_controller_runs_the_linux_observer_with_both_collectors(tmp_path, monkeypatch):
    import tools.hot_swap.linux_observer as observer
    seen = {}

    def trace(command, **options):
        seen.update(command=command, **options)
        worker = Path(command[command.index('--output') + 1])
        worker.write_text(json.dumps({'status': 'PASS_SCENARIO', 'events': [], 'attribution_complete': True}),
                          encoding='utf-8')
        return {'events': [], 'errors': [], 'process_exit': 0, 'coverage': dict.fromkeys(COVERAGE, True),
                'auditor_sha256': 'a' * 64, 'debugger_sha256': 'b' * 64, 'scope': 'Linux x86-64'}

    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setattr(observer, 'trace', trace)
    script = tmp_path / 'scenario.py'
    script.write_text('pass\n')
    output = tmp_path / 'report.json'
    args = argparse.Namespace(python=Path(sys.executable), script=script, output=output, arguments=[], timeout=5.0,
                              native_auditor=tmp_path / 'loader_audit.so', native_debugger=tmp_path / 'debugger_linux')
    report = audit.run(args)
    assert (seen['auditor'], seen['debugger']) == (args.native_auditor, args.native_debugger)
    assert seen['trace_path'] == output.resolve().with_suffix('.loader.tsv') and seen['cwd'] == output.resolve().parent
    assert report['gates']['no_gl_context_or_draw'] == 'PASS' and report['status'] == 'UNVERIFIED'  # vispy not imported
    assert report['native_tools'] == {'auditor_sha256': 'a' * 64, 'debugger_sha256': 'b' * 64}


def test_linux_runs_need_both_native_collectors(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    script = tmp_path / 'scenario.py'
    script.write_text('pass\n')
    common = ['audit_hot_swap.py', '--python', sys.executable, '--script', str(script), '--native-auditor', 'loader_audit.so']
    monkeypatch.setattr(sys, 'argv', [*common, '--output', str(tmp_path / 'one.json')])
    assert audit.main() == 3  # the auditor alone cannot pass: a tool error, never a verdict
    report = json.loads((tmp_path / 'one.json').read_text(encoding='utf-8'))
    assert report['status'] == 'TOOL_ERROR' and '--native-debugger' in report['error']
    monkeypatch.setattr(audit, 'run', lambda args: {'status': 'UNVERIFIED', 'gates': {
        'renderer_gl': 'UNVERIFIED', 'no_gl_context_or_draw': 'UNVERIFIED'}, 'debugger': str(args.native_debugger)})
    monkeypatch.setattr(sys, 'argv', [*common, '--native-debugger', 'debugger_linux', '--output', str(tmp_path / 'two.json')])
    assert audit.main() == 2
    assert json.loads((tmp_path / 'two.json').read_text(encoding='utf-8'))['debugger'] == 'debugger_linux'


# Only the tests are re-exported into CI's curated list (tests/contract/curated_contracts.py).
__all__ = [name for name in dir() if name.startswith('test_')]
