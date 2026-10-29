# SPDX-License-Identifier: AGPL-3.0-only
"""R1 instrumentation: record the moment this process loses its default thread pool (Windows only).

The 2026-10-28 napari startup stalls had lost the default thread pool's worker factory handle (runs
napari-startup-stall-recurrence-209 and com-stall-harness-213): code that did not own the handle closed it, and the
value was reused. Who closes it is unknown, so the plan instruments launches and waits for a recurrence.

start(path) finds the lowest TpWorkerFactory handle (the default pool's) and re-checks its object type from a daemon
thread every few milliseconds. When it is no longer a TpWorkerFactory, the watcher appends one JSON event to path
with the time since start, the handle's new type, the worker factory handles that remain, and every Python thread's
stack, then stops. A watcher that finds no factory, or runs off Windows, records that and stops. It only queries
object types: it never closes, duplicates or changes a handle. Enable it in a diagnostic launch with the environment
variable VISPY_POOL_WATCH=<events.jsonl> and `import tools.pool_watch` (for example from a run's sitecustomize).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback

INTERVAL = 0.005
_started = None


def _handle_type(value):
    import ctypes
    from ctypes import wintypes

    buffer = ctypes.create_string_buffer(1024)
    status = _ntdll().NtQueryObject(wintypes.HANDLE(value), 2, buffer, 1024, None)  # ObjectTypeInformation
    if status < 0:
        return 'status 0x%08x' % (status & 0xFFFFFFFF)
    length = ctypes.c_ushort.from_buffer(buffer, 0).value
    return ctypes.wstring_at(ctypes.c_void_p.from_buffer(buffer, 8).value, length // 2)


def _ntdll():
    import ctypes
    from ctypes import wintypes

    ntdll = ctypes.WinDLL('ntdll')
    ntdll.NtQueryObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                                    ctypes.POINTER(wintypes.ULONG)]
    ntdll.NtQueryObject.restype = ctypes.c_long
    return ntdll


def factories(limit=8192):
    """Handle values of this process's worker factories (read-only)."""
    return [value for value in range(4, limit, 4) if _handle_type(value) == 'TpWorkerFactory']


def _record(path, **fields):
    fields.update(pid=os.getpid(), seconds=round(time.perf_counter() - _started, 4), argv=sys.argv[:3])
    with open(path, 'a', encoding='utf-8') as output:
        output.write(json.dumps(fields) + '\n')


def _stacks():
    names = {thread.ident: thread.name for thread in threading.enumerate()}
    return {f'{names.get(ident, "?")} ({ident})': traceback.format_stack(frame)
            for ident, frame in sys._current_frames().items()}


def _watch(path, handle):
    while True:
        time.sleep(INTERVAL)
        kind = _handle_type(handle)
        if kind != 'TpWorkerFactory':
            _record(path, event='default_pool_lost', handle=handle, now=kind, factories=factories(),
                    stacks=_stacks())
            return


def start(path):
    """Start watching once per process; return the watched handle, or None when there is nothing to watch."""
    global _started
    if _started is not None:
        return None
    _started = time.perf_counter()
    if sys.platform != 'win32':
        _record(path, event='unsupported_platform', platform=sys.platform)
        return None
    found = factories()
    if not found:
        _record(path, event='no_worker_factory')
        return None
    _record(path, event='watching', handle=found[0], factories=found)
    threading.Thread(target=_watch, args=(path, found[0]), name='pool-watch', daemon=True).start()
    return found[0]


if os.environ.get('VISPY_POOL_WATCH'):
    start(os.environ['VISPY_POOL_WATCH'])
