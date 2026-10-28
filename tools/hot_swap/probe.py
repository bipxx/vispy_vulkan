# SPDX-License-Identifier: AGPL-3.0-only
"""Run one host scenario script with an attributing audit hook (child process of tools/audit_hot_swap.py).

GL imports, ctypes library loads and GL symbol lookups are recorded with the module stack that caused them
and an attribution (renderer, host or unattributed). The hook observes; it never blocks. Native loads and
GL calls are observed by the controller's debugger-based observer.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.hot_swap.policy import attribute, gl_library  # noqa: E402
from tools.no_opengl.policy import import_reason, is_gl_entrypoint  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    report = {'status': 'FAILED', 'pid': os.getpid(), 'python': sys.version, 'executable': sys.executable,
              'prefix': sys.prefix, 'events': [], 'hook_errors': []}
    began = time.monotonic()

    def stack():
        # Skip stack(), record() and hook(): start at the frame that raised the audit event.
        frame, names = sys._getframe(3), []
        while frame is not None:
            names.append(frame.f_globals.get('__name__', ''))
            frame = frame.f_back
        return names

    def record(kind, **values):
        modules = stack()
        report['events'].append({'kind': kind, 'pid': os.getpid(), 'elapsed_s': time.monotonic() - began,
                                 'wall': time.time(), 'attribution': attribute(modules), 'stack': modules[:24],
                                 **values})

    def hook(name, values):
        try:
            if name == 'import' and import_reason(values[0]):
                record('python_import', name=values[0])
            elif name == 'ctypes.dlopen' and values[0] is not None and gl_library(str(values[0])):
                record('ctypes_load_request', path=str(values[0]))
            elif name in ('ctypes.dlsym', 'ctypes.dlsym/handle') and is_gl_entrypoint(str(values[1])):
                record('ctypes_symbol', name=str(values[1]))
        except Exception:  # an observer must never change the scenario; a failure only removes coverage
            report['hook_errors'].append(traceback.format_exc())

    def write(final):
        report['attribution_complete'] = not report['hook_errors']
        report['gl_modules_present'] = sorted(name for name in sys.modules if import_reason(name))
        report['vispy_origin'] = getattr(sys.modules.get('vispy'), '__file__', None)
        report['written_at_exit'] = final
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    # Rewrite the report at interpreter exit too, so events from atexit handlers and late threads are kept.
    atexit.register(write, True)
    try:
        sys.addaudithook(hook)
        sys.argv = [str(args.script), *[a for a in args.arguments if a != '--']]
        try:
            runpy.run_path(str(args.script.resolve(strict=True)), run_name='__main__')
        except SystemExit as exit_status:
            if exit_status.code not in (None, 0):
                raise
        report['status'] = 'PASS_SCENARIO'
    except BaseException:
        report.update(status='FAILED_SCENARIO', error=traceback.format_exc())
    finally:
        write(False)
    return 0 if report['status'] == 'PASS_SCENARIO' else 1


if __name__ == '__main__':
    raise SystemExit(main())
