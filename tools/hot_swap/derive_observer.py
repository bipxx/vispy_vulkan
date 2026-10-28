# SPDX-License-Identifier: AGPL-3.0-only
"""Derive tools/hot_swap/windows_observer.py from the strict observer tools/no_opengl/windows.py, which stays unchanged.

Each change is an exact replacement that must match once:
1. A GL entry-point lookup is recorded and then single-stepped like any other lookup, instead of terminating the
   process tree (host packages such as PyOpenGL resolve GL names at import).
2. A GL call records its direct caller. Context, make-current, swap and draw calls still terminate the tree (the
   hot-swap gate has failed); other calls such as wglGetCurrentContext are stepped over.
3. A GL library load records the first caller outside the system loader (ntdll, KernelBase, kernel32).
Supporting changes are commented where they are made. Run this module to regenerate the observer;
tests/contract/test_hot_swap_policy.py checks that the committed observer equals the derivation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRICT = ROOT / 'tools/no_opengl/windows.py'
DERIVED = ROOT / 'tools/hot_swap/windows_observer.py'
REPLACEMENTS = []


def sub(old, new):
    REPLACEMENTS.append((old, new))


sub('''"""Observe Windows startup/transient DLL loads, symbol lookups and GL calls.

The child is created under the Windows debugger, before its first instruction.
Each loaded image's GL exports and public native symbol resolvers receive debug
breakpoints before execution resumes. Ordinary resolver calls are single-stepped
with the other threads suspended; GL lookups terminate the negative control.
A hit is recorded and terminates the test process tree before executing GL.
Unresolved image paths, forwarded GL exports and failed breakpoint placement make
API coverage incomplete; they never become an absence claim.
"""''', '''# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap observer: Windows startup/transient DLL loads, symbol lookups and GL calls, with callers.

Derived by tools/hot_swap/derive_observer.py from tools/no_opengl/windows.py
(sha256 {origin}), which stays unchanged for the strict profile. Differences: GL lookups are recorded
and single-stepped instead of terminating; GL calls record their direct caller, and only context,
make-current, swap and draw calls terminate the tree (other calls are stepped over); GL library loads
record the first caller outside the system loader. Unresolved image paths, forwarded GL exports and
failed breakpoint placement still make API coverage incomplete; they never become an absence claim.
"""''')
sub('''from .dependencies import inspect_binary
from .policy import is_gl_entrypoint
''', '''from tools.hot_swap.policy import context_or_draw
from tools.no_opengl.dependencies import inspect_binary
from tools.no_opengl.policy import is_gl_entrypoint, library_reason
from tools.no_opengl.windows_stack import Unwinder
''')
# Review fixes: the handle-baseline control source stays in tools/no_opengl/; events carry wall-clock time so the
# controller can order them against the child's Python events.
sub('''        control_source = Path(__file__).with_name('handle_negative_probe_windows.c')''',
    '''        control_source = Path(__file__).resolve().parents[1] / 'no_opengl' / 'handle_negative_probe_windows.c\'''')
sub('''        events.append({"kind": kind, "sequence": len(events), "elapsed_s": time.monotonic() - started, **values})''',
    '''        events.append({"kind": kind, "sequence": len(events), "elapsed_s": time.monotonic() - started,
                       "wall": time.time(), **values})''')
# 1. A GL lookup is recorded, then handled like any other lookup. A deferred step re-traps the same lookup later,
#    so it is emitted only when the step is taken.
sub('''        if is_gl_entrypoint(name):
            emit('native_gl_binding', pid=pid, name=name, resolver=export['resolver'], path=export['path'],
                 direct_caller=caller(pid, registers))
            return True
        if pid in stepping:''', '''        direct = caller(pid, registers) if is_gl_entrypoint(name) else None
        result = step_over(pid, tid, address, export, registers, name)
        deferred = step_state.pop('deferred', False)
        if direct is not None and not deferred:
            emit('native_gl_binding', pid=pid, name=name, resolver=export['resolver'], path=export['path'],
                 direct_caller=direct)
        return result
    step_state = {}
    def step_over(pid, tid, address, export, registers, name):
        step_state.pop('deferred', None)
        if pid in stepping:''')
sub('''            emit('native_resolver_step_deferred', pid=pid, tid=tid, active_tid=active['tid'],
                 address=address, name=name, before_rip=before_rip, retry_rip=address,
                 argument_module=reg(registers, 128), argument_name=reg(registers, 136))
            return False''', '''            emit('native_resolver_step_deferred', pid=pid, tid=tid, active_tid=active['tid'],
                 address=address, name=name, before_rip=before_rip, retry_rip=address,
                 argument_module=reg(registers, 128), argument_name=reg(registers, 136))
            step_state['deferred'] = True
            return False''')
# 3. The first caller outside the system loader, for GL library loads. It shares the strict observer's unwinder,
#    which it closes with each process: DbgHelp initialises a process handle once.
sub('''    def image_path(handle):''', '''    loader_modules = {'ntdll.dll', 'kernelbase.dll', 'kernel32.dll'}
    def loader_caller(pid, tid):
        nonlocal unwinder
        try:
            if unwinder is None:
                unwinder = Unwinder()
            storage, registers = context(tid)
            for frame in unwinder.frames(processes[pid], threads[tid][1], registers, limit=96):
                owner = module_at(pid, frame['address'])
                if owner['path'] and Path(owner['path']).name.casefold() not in loader_modules:
                    return owner
            return {'path': None, 'error': 'no caller outside the system loader within 96 frames'}
        except Exception as error:
            return {'path': None, 'error': str(error)}
    def image_path(handle):''')
sub('''                        modules[(pid, data.base)] = path
                        emit('native_load', pid=pid, path=path or '', base=data.base)
                        install(pid, data.base, path)
                    elif event.code == 7:''', '''                        modules[(pid, data.base)] = path
                        extra = {'loader_caller': loader_caller(pid, event.tid)} if path and library_reason(path) else {}
                        emit('native_load', pid=pid, path=path or '', base=data.base, **extra)
                        install(pid, data.base, path)
                    elif event.code == 7:''')
# 2. GL calls record their caller; only context, make-current, swap and draw calls terminate. A call is recorded
#    even when its caller cannot be read, so a context or draw call still fails the gate; such a call cannot be
#    stepped over, so the tree stops (fail closed).
sub('''                            else:
                                emit('native_gl_call', pid=pid, name=export['names'][0], aliases=export['names'], path=export['path'])
                            if terminate:''', '''                            else:
                                names = export['names']
                                try:
                                    storage, registers = context(event.tid)
                                    direct = caller(pid, registers)
                                except Exception as error:
                                    registers, direct = None, {'path': None, 'error': str(error)}
                                    errors.append({'pid': pid, 'gl_call': names[0], 'error': str(error)})
                                deferred = False
                                if registers is not None and not any(context_or_draw(name) for name in names):
                                    try:
                                        terminate = step_over(pid, event.tid, address, export, registers, names[0])
                                        deferred = step_state.pop('deferred', False)
                                    except Exception as error:  # fail closed: stop the tree, keep the report
                                        errors.append({'pid': pid, 'gl_call': names[0], 'error': str(error)})
                                        terminate = True
                                if not deferred:
                                    emit('native_gl_call', pid=pid, name=names[0], aliases=names, path=export['path'],
                                         direct_caller=direct)
                            if terminate:''')
# The strict observer imports Unwinder inside trace(), which makes the name local to the whole function and
# hides the module-level import from loader_caller(). Use the module-level import throughout.
sub('''                                    if unwinder is None:
                                        from .windows_stack import Unwinder
                                        unwinder = Unwinder()''', '''                                    if unwinder is None:
                                        unwinder = Unwinder()''')


def derive(source):
    """The hot-swap observer's source for the strict observer's source bytes."""
    data, origin = source.decode('utf-8'), hashlib.sha256(source).hexdigest()
    for old, new in REPLACEMENTS:
        assert data.count(old) == 1, old[:80]
        data = data.replace(old, new.replace('{origin}', origin))
    return data.encode('utf-8')


if __name__ == '__main__':
    DERIVED.write_bytes(derive(STRICT.read_bytes()))
    print('derived', DERIVED.relative_to(ROOT).as_posix(), 'from', hashlib.sha256(STRICT.read_bytes()).hexdigest())
