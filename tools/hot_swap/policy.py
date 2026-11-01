# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap gates: renderer GL activity and any GL context or draw fail; host GL activity is recorded.

The strict no-OpenGL policy (tools/no_opengl/policy.py) is reused unchanged to recognise GL modules,
libraries and entry points. Attribution names the code that caused an event: the innermost stack frame
that is not import machinery, ctypes, the audit tools, a GL implementation or a GL binding shim.
A static scan of the installed renderer package covers GL code that the dynamic events cannot see.
"""
from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import struct

from tools.no_opengl.policy import import_reason, is_gl_entrypoint, library_reason

RENDERER = ('vispy',)
# Frames that only carry an event through: import machinery, threads, the audit tools, GL implementations and
# binding shims (qtpy.QtOpenGL only forwards to the Qt binding's GL module).
_TRANSPARENT = re.compile(r'^(?:importlib(?:\.|$)|_frozen_importlib|encodings(?:\.|$)|ctypes(?:\.|$)|runpy$|'
                          r'threading$|pkgutil$|lazy_loader(?:\.|$)|tools\.hot_swap(?:\.|$)|OpenGL(?:\.|$)|'
                          r'PyQt[56]\.QtOpenGL|PySide6\.QtOpenGL|qtpy\.QtOpenGL)')
# Executing these creates, binds or presents a GL context, or draws: a name that starts with a prefix or equals a name.
# glClearColor/Depth/Stencil and glDrawBuffer* only set state. The Linux observer's C copy is generated from these
# tables (tools/hot_swap/derive_linux_observer.py), so they stay plain identifiers.
CONTEXT_PREFIXES = ('wglCreate', 'wglMake', 'wglSwap', 'wglShare', 'wglCopy', 'wglDelete', 'eglCreate', 'eglMakeCurrent',
                    'eglSwap', 'glXCreate', 'glXMakeCurrent', 'glXMakeContextCurrent', 'glXSwap', 'OSMesaCreate',
                    'OSMesaMakeCurrent')
CONTEXT_NAMES = ('SwapBuffers',)
DRAW_PREFIXES = ('glDraw', 'glMultiDraw', 'glClearBuffer', 'glClearNamedFramebuffer', 'glClearTex', 'glDispatch', 'glBlit',
                 'glRect', 'glEvalMesh', 'glEvalPoint')
DRAW_NAMES = ('glClear', 'glBegin', 'glCallList', 'glCallLists', 'glAccum', 'glBitmap', 'glCopyPixels', 'glArrayElement')
NOT_DRAW_PREFIXES = ('glDrawBuffer',)
# Python's ctypes/FFI and its extension-module loader act for whichever Python code called them: _ctypes and libffi,
# and the interpreter, either python3*.dll and a static Linux python3.x executable, or a shared libpython3.x.so.
_PYTHON_NATIVE = ('_ctypes', 'libffi', 'python3', 'libpython3')
# Qt's own GL modules and libraries, which an import of a QtOpenGL module loads (libQt6OpenGL.so.6 on Linux).
_QT_GL = re.compile(r'^(?:lib)?(?:qtopengl|qt[56]opengl)', re.IGNORECASE)
# Shared libraries a renderer package can ship, including versioned ELF names (libfoo-1a2b.so.1.3).
_SHARED = re.compile(r'\.(?:pyd|dll|so)(?:\.\d+)*$', re.IGNORECASE)
# The static scan's pseudo-import for an ELF image's undefined dynamic symbols: ELF names no library per symbol.
ELF_SYMBOL_IMPORTS = 'undefined ELF dynamic symbols'
# A Python GL event explains a native event observed after it, within this many seconds (wall clock).
_EARLY, _LATE = 0.05, 10.0
# A Qt library dependency loads while its importing module loads: the nearest preceding Qt binding import, within this
# many seconds, explains a Qt GL library loaded with no native caller (e.g. qtpy importing PySide6.QtDataVisualization,
# whose Qt library links Qt6OpenGL.dll).
_QT_DEPENDENCY = 1.0


def first_caller(modules):
    """The first module of a stack, innermost first, that is not machinery, a GL module or a shim; else None."""
    for name in modules:
        if name and not _TRANSPARENT.match(name):
            return name
    return None


def attribute(modules):
    """'renderer', 'host' or 'unattributed' for a stack of module names, innermost first."""
    name = first_caller(modules)
    if name is None:
        return 'unattributed'
    return 'renderer' if any(name == root or name.startswith(root + '.') for root in RENDERER) else 'host'


def host_gl_sources(events):
    """Count host GL events by the top-level package of their first caller; 'native' when no Python caller exists."""
    counts = {}
    for event in events:
        name = first_caller(event.get('stack') or [])
        source = name.split('.')[0] if name else 'native'
        counts[source] = counts.get(source, 0) + 1
    return counts


def gl_library(path):
    """library_reason, also for a bare ctypes name: PyOpenGL loads 'opengl32', which Windows resolves to .dll."""
    path = str(path)
    name = path.replace('\\', '/').rsplit('/', 1)[-1]
    return library_reason(path) or (library_reason(path + '.dll') if name and '.' not in name else None)


def gl_reason(event):
    """Why an event is GL activity, or None."""
    kind = event.get('kind')
    if kind == 'python_import':
        return import_reason(event.get('name', ''))
    if kind in ('ctypes_load_request', 'native_load'):
        return gl_library(event.get('path', ''))
    if kind in ('ctypes_symbol', 'native_gl_binding') and is_gl_entrypoint(event.get('name', '')):
        return 'OpenGL entry-point resolution'
    if kind == 'native_gl_call':
        return 'OpenGL API call'
    return None


def _library(path):
    name = str(path).replace('\\', '/').rsplit('/', 1)[-1].lower()
    return re.sub(r'(?:\.(?:dll|pyd|so)(?:\.[\w.]+)?|\.cp\d+[\w-]*)+$', '', name)


def renderer_roots(vispy_origin):
    """The installed renderer's directories: the vispy package and a vendored vispy.libs beside it. The origin comes
    from the observed child: an absolute POSIX path from the Linux observer, otherwise a Windows path, parsed the same
    way on any host that assesses a report."""
    if not vispy_origin:
        return []
    package = (PurePosixPath if str(vispy_origin).startswith('/') else PureWindowsPath)(vispy_origin)
    package = package.parent if package.suffix == '.py' else package
    return [str(package), str(package.parent / 'vispy.libs')]


def _normal(path):
    return str(path).replace('/', '\\').rstrip('\\').casefold()


def _within(path, roots):
    path = _normal(path)
    return any(path.startswith(_normal(root) + '\\') for root in roots)


def correlate(native_events, python_events, roots=()):
    """Attribute the observer's native GL loads, lookups and calls.

    The native caller decides first: code under the renderer roots is the renderer, and any other known native
    module except Python's ctypes/FFI and extension-module loader is a host. A GL call through Python cannot be
    attributed (ctypes calls raise no audit event), so it stays unattributed. A load or lookup through Python,
    or with no recorded caller, takes the attribution of the Python events that explain it and were observed
    shortly before it: a ctypes load request for the same library or, for Qt's own GL modules only, an import
    of a QtOpenGL module; a ctypes lookup of the same name. A Qt GL library that no Python GL event explains takes the
    nearest preceding Qt binding import within _QT_DEPENDENCY seconds. A renderer explanation wins; unexplained events
    stay unattributed."""
    loads, symbols, qt_imports, qt_bindings = {}, {}, [], []
    for event in python_events:
        side, wall = event.get('attribution', 'unattributed'), event.get('wall')
        if event.get('kind') == 'ctypes_load_request' and gl_library(event.get('path', '')):
            loads.setdefault(_library(event['path']), []).append((wall, side))
        elif event.get('kind') == 'ctypes_symbol':
            symbols.setdefault(event.get('name'), []).append((wall, side))
        elif event.get('kind') == 'python_import' and 'QtOpenGL' in event.get('name', ''):
            qt_imports.append((wall, side))
        elif event.get('kind') == 'qt_binding_import' and wall is not None:
            qt_bindings.append((wall, side))

    def explained(candidates, wall):
        return {side for when, side in candidates
                if when is not None and wall is not None and when - _EARLY <= wall <= when + _LATE}

    def nearest_qt_import(wall):
        earlier = [(when, side) for when, side in qt_bindings if wall is not None and 0 <= wall - when <= _QT_DEPENDENCY]
        return {max(earlier)[1]} if earlier else set()

    result = []
    for event in native_events:
        if not gl_reason(event):
            result.append(event)
            continue
        caller = (event.get('direct_caller') or event.get('loader_caller') or {}).get('path') or ''
        through_python = not caller or _library(caller).startswith(_PYTHON_NATIVE)
        if caller and (_within(caller, roots) or re.search(r'[\\/]site-packages[\\/]vispy(?:\.libs)?[\\/]', caller, re.I)):
            sides = {'renderer'}
        elif not through_python:
            sides = {'host'}  # a known native host module, e.g. a Qt plugin or a graphics driver
        elif event.get('kind') == 'native_gl_call':
            sides = set()
        elif event.get('kind') == 'native_load':
            library = _library(event['path'])
            sides = explained(loads.get(library, ()), event.get('wall'))
            if _QT_GL.match(library):
                sides |= explained(qt_imports, event.get('wall')) or nearest_qt_import(event.get('wall'))
        else:
            sides = explained(symbols.get(event.get('name'), ()), event.get('wall'))
        side = 'renderer' if 'renderer' in sides else 'host' if sides and sides <= {'host'} else 'unattributed'
        result.append({**event, 'attribution': side})
    return result


def context_or_draw(name):
    """True for an executed GL call that creates, binds or presents a context, or that draws."""
    return (name in CONTEXT_NAMES or name.startswith(CONTEXT_PREFIXES) or name in DRAW_NAMES
            or (name.startswith(DRAW_PREFIXES) and not name.startswith(NOT_DRAW_PREFIXES)))


def _test_only(relative):
    parts = Path(relative).parts
    return 'tests' in parts or (len(parts) > 1 and parts[0] == 'testing')


def static_scan(package, binary_imports=None):
    """GL references in the installed renderer package: Python imports, import_module/__import__ of GL modules,
    ctypes loads of GL libraries, and GL libraries or GL entry points in native import tables (for ELF images, the
    undefined dynamic symbols). Native images are the package's and vispy.libs' .pyd, .dll and .so files, including
    versioned .so names. Test modules and vispy.testing are listed separately; they never run in a host process."""
    package = Path(package)
    runtime, test_only, errors, files, binaries = [], [], [], 0, 0
    for path in sorted(package.rglob('*.py')):
        files += 1
        relative = path.relative_to(package).as_posix()
        try:
            tree = ast.parse(path.read_bytes())
        except (SyntaxError, ValueError) as error:
            errors.append({'file': relative, 'error': str(error)})
            continue
        for node in ast.walk(tree):
            found = []
            if isinstance(node, ast.Import):
                found = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                found = [node.module, *(node.module + '.' + alias.name for alias in node.names)]
            elif (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
                  and isinstance(node.args[0].value, str)):
                function = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                if function in ('import_module', '__import__'):
                    found = [node.args[0].value]
                elif function in ('CDLL', 'WinDLL', 'OleDLL', 'PyDLL', 'LoadLibrary', 'find_library'):
                    value = node.args[0].value
                    if gl_library(value) or value.lower() in ('gl', 'egl', 'glesv2', 'osmesa', 'opengl'):
                        (test_only if _test_only(relative) else runtime).append(
                            {'file': relative, 'line': node.lineno, 'reference': f'{function}({value!r})'})
            for name in found:
                if import_reason(name) or 'QtOpenGL' in name:
                    (test_only if _test_only(relative) else runtime).append(
                        {'file': relative, 'line': node.lineno, 'reference': name})
    for path in sorted(path for root in (package, package.parent / 'vispy.libs') for path in root.rglob('*')
                       if _SHARED.search(path.name) and path.is_file()):
        binaries += 1
        try:
            imports = (binary_imports or _binary_imports)(path)
        except Exception as error:  # an unreadable binary makes the scan incomplete
            errors.append({'file': str(path), 'error': str(error)})
            continue
        for entry in imports:
            name, symbols = (entry, []) if isinstance(entry, str) else (entry.get('name', ''), entry.get('symbols', []))
            gl_symbols = [symbol for symbol in symbols if is_gl_entrypoint(symbol)]
            if library_reason(name) or gl_symbols:
                runtime.append({'file': str(path.relative_to(package.parent)), 'reference': f'imports {name}',
                                'gl_symbols': gl_symbols})
    return {'runtime': runtime, 'test_only': test_only, 'errors': errors, 'python_files': files,
            'binaries': binaries, 'complete': not errors and files > 0}


def _binary_imports(path):
    """A native image's imports. ELF's DT_NEEDED names libraries but not the symbols taken from them, so an ELF image
    also lists its undefined dynamic symbols under ELF_SYMBOL_IMPORTS."""
    from tools.no_opengl.dependencies import inspect_binary
    binary = inspect_binary(Path(path))
    imports = binary.get('imports', [])
    if binary.get('format') == 'ELF':
        imports = [*imports, {'name': ELF_SYMBOL_IMPORTS, 'symbols': elf_undefined_symbols(Path(path).read_bytes())}]
    return imports


def elf_undefined_symbols(data):
    """The undefined symbols of a little-endian ELF image's dynamic symbol tables, in table order. A malformed image, or
    a dynamically linked one without a dynamic symbol table, raises ValueError: the scan is then incomplete."""
    if data[:4] != b'\x7fELF' or data[4:6] not in (b'\x01\x01', b'\x02\x01'):
        raise ValueError('Only little-endian ELF32/ELF64 is supported')
    wide = data[4] == 2
    header, section, symbol = (('<16xHHIQQQIHHHHHH', '<IIQQQQIIQQ', '<IBBHQQ') if wide else
                               ('<16xHHIIIIIHHHHHH', '<IIIIIIIIII', '<IIIBBH'))
    _, _, _, _, phoff, shoff, _, _, phentsize, phnum, shentsize, shnum, _ = struct.unpack_from(header, data)

    def within(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('ELF table outside the image')

    within(shoff, shnum * shentsize)
    if shnum and shentsize != struct.calcsize(section):
        raise ValueError('Unexpected ELF section header size')
    sections = [struct.unpack_from(section, data, shoff + index * shentsize) for index in range(shnum)]
    names, tables = [], 0
    for _, kind, _, _, offset, size, link, _, _, entry in sections:
        if kind != 11:  # SHT_DYNSYM
            continue
        if entry != struct.calcsize(symbol) or link >= shnum:
            raise ValueError('Malformed ELF dynamic symbol table')
        within(offset, size)
        strings, string_size = sections[link][4], sections[link][5]
        within(strings, string_size)
        tables += 1
        for index in range(1, size // entry):
            fields = struct.unpack_from(symbol, data, offset + index * entry)
            name, shndx = (fields[0], fields[3]) if wide else (fields[0], fields[5])
            if shndx or not name:
                continue
            if name >= string_size:
                raise ValueError('ELF symbol name outside its string table')
            end = data.find(b'\0', strings + name, strings + string_size)
            if end < 0:
                raise ValueError('Unterminated ELF symbol name')
            names.append(data[strings + name:end].decode('utf-8', 'replace'))
    if not tables:
        within(phoff, phnum * phentsize)
        if any(struct.unpack_from('<I', data, phoff + index * phentsize)[0] == 2 for index in range(phnum)):
            raise ValueError('Dynamically linked ELF image without a dynamic symbol table')
    return names


def assess_hot_swap(events, *, attribution_complete, native_api_complete, native_loads_complete,
                    execution_succeeded, static):
    """Gates for one observed run.

    renderer_gl: FAIL when any GL import, load, lookup or call is attributed to the renderer. PASS needs complete
    attribution and native coverage, no unattributed GL activity, a successful scenario, and a complete static
    scan with no GL reference in the renderer's runtime modules (dynamic events cannot see GL that the host had
    already loaded). no_gl_context_or_draw: FAIL on any executed context or draw call, under any of its export
    names, whoever made it; PASS needs complete native API coverage and a successful scenario.
    """
    renderer, host, unattributed, context = [], [], [], []
    for event in events:
        reason = gl_reason(event)
        if reason is None:
            continue
        item = {**event, 'reason': reason}
        names = [event.get('name', ''), *event.get('aliases', [])]
        if event.get('kind') == 'native_gl_call' and any(context_or_draw(name) for name in names):
            context.append(item)
        side = event.get('attribution', 'unattributed')
        {'renderer': renderer, 'host': host}.get(side, unattributed).append(item)
    complete = attribution_complete and native_api_complete and native_loads_complete and execution_succeeded
    if renderer:
        renderer_gate = 'FAIL'
    elif unattributed or static['runtime'] or not static['complete'] or not complete:
        renderer_gate = 'UNVERIFIED'
    else:
        renderer_gate = 'PASS'
    if context:
        context_gate = 'FAIL'
    elif native_api_complete and execution_succeeded:
        context_gate = 'PASS'
    else:
        context_gate = 'UNVERIFIED'
    return {'renderer_gl': renderer_gate, 'no_gl_context_or_draw': context_gate,
            'renderer_events': renderer, 'context_events': context, 'host_gl_events': host,
            'unattributed_gl_events': unattributed, 'renderer_static_references': static['runtime'],
            'test_only_static_references': static['test_only'], 'static_scan_errors': static['errors']}
