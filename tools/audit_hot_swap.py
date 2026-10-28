# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap audit: run a host scenario with stock hosts and only vispy replaced, and assess the hot-swap gates.

The child runs tools/hot_swap/probe.py (attributing audit hook) under tools/hot_swap/windows_observer.py, a
derived copy of the strict debugger-based observer that records host GL lookups and queries instead of
terminating. The strict no-OpenGL audit (tools/audit_no_opengl.py, tools/no_opengl/) is not modified; a
hot-swap result never qualifies a strict row. See docs/hot-swap-gates.md.

Exit status: 0 PASS_HOT_SWAP_GATES, 1 FAIL, 2 UNVERIFIED, 3 a tool or usage error (a TOOL_ERROR report is still
written when the output path is usable).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.hot_swap.policy import assess_hot_swap, correlate, renderer_roots, static_scan  # noqa: E402

NATIVE_API = ('native_public_gl_export_breakpoints', 'native_entrypoint_resolution', 'process_tree')
EXIT = {'PASS_HOT_SWAP_GATES': 0, 'FAIL': 1, 'UNVERIFIED': 2, 'TOOL_ERROR': 3}
SCOPE = 'hot-swap profile only; never a strict no-OpenGL qualification'


def read_worker(path):
    """The child's report. A missing or unreadable one, e.g. from a child killed while writing, removes coverage."""
    if not path.exists():
        return {'status': 'MISSING_WORKER_REPORT', 'events': []}
    try:
        report = json.loads(path.read_text(encoding='utf-8'))
    except ValueError as error:
        return {'status': 'UNREADABLE_WORKER_REPORT', 'events': [], 'error': str(error)}
    if not isinstance(report, dict) or not isinstance(report.get('events'), list):
        return {'status': 'UNREADABLE_WORKER_REPORT', 'events': [], 'error': 'not a worker report'}
    return report


def origin_roots(origin):
    """Renderer roots for the imported vispy, as imported and as resolved (junctions, subst drives, short names):
    the observer reports final paths."""
    roots = renderer_roots(origin)
    for root in renderer_roots(os.path.realpath(origin)) if origin else ():
        if root not in roots:
            roots.append(root)
    return roots


def run(args):
    report_path = args.output.resolve()
    worker = report_path.with_suffix('.worker.json')
    assert not worker.exists(), 'A fresh worker report is required'
    command = [str(args.python.absolute()), '-I', '-B', str(ROOT / 'tools/hot_swap/probe.py'),
               '--output', str(worker), '--script', str(args.script.resolve(strict=True)), '--', *args.arguments]
    environment = os.environ.copy()
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE'):
        environment.pop(key, None)
    if sys.platform != 'win32':
        raise RuntimeError('The hot-swap native observer is Windows-only; Linux rows need a separate observer.')
    from tools.hot_swap.windows_observer import trace
    native = trace(command, environment=environment, cwd=report_path.parent, log=report_path.with_suffix('.process.log'),
                   timeout=args.timeout)
    child = read_worker(worker)
    succeeded = native['process_exit'] == 0 and child.get('status') == 'PASS_SCENARIO'
    roots = origin_roots(child.get('vispy_origin'))
    # The installed renderer package is scanned statically: dynamic events cannot see GL the host already loaded.
    static = (static_scan(roots[0]) if roots else
              {'runtime': [], 'test_only': [], 'errors': [{'error': 'vispy was not imported'}], 'complete': False})
    events = [*child['events'], *correlate(native['events'], child['events'], roots)]
    gates = assess_hot_swap(events, attribution_complete=bool(child.get('attribution_complete')),
                            native_api_complete=all(native['coverage'].get(name, False) for name in NATIVE_API),
                            native_loads_complete=bool(native['coverage'].get('startup_and_transient_native_loads')),
                            execution_succeeded=succeeded, static=static)
    status = ('FAIL' if 'FAIL' in (gates['renderer_gl'], gates['no_gl_context_or_draw']) else
              'PASS_HOT_SWAP_GATES' if gates['renderer_gl'] == gates['no_gl_context_or_draw'] == 'PASS' else 'UNVERIFIED')
    return {'status': status, 'scope': SCOPE,
            'process_exit': native['process_exit'], 'child_waited': bool(native['coverage'].get('process_tree')),
            'renderer_roots': roots, 'static_scan': {k: static.get(k) for k in ('python_files', 'binaries', 'complete')},
            'worker_status': child.get('status'), 'attribution_complete': bool(child.get('attribution_complete')),
            'hook_errors': child.get('hook_errors', []),
            'worker_error': child.get('error'), 'vispy_origin': child.get('vispy_origin'),
            'script': str(args.script), 'script_sha256': hashlib.sha256(args.script.read_bytes()).hexdigest(),
            'gates': gates, 'native_coverage': native['coverage'], 'native_errors': native.get('errors', []),
            'gl_modules_present': child.get('gl_modules_present'),
            'worker_report_sha256': hashlib.sha256(worker.read_bytes()).hexdigest() if worker.exists() else None}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        """A usage error is a tool error, never a verdict."""
        self.print_usage(sys.stderr)
        self.exit(EXIT['TOOL_ERROR'], f'{self.prog}: error: {message}\n')


def main():
    parser = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--python', type=Path, required=True, help='candidate interpreter with stock hosts')
    parser.add_argument('--script', type=Path, required=True, help='host scenario script to run')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.arguments = [a for a in args.arguments if a != '--']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        parser.error('A new output report path is required')
    try:
        report = run(args)
    except Exception:  # the observer or controller failed: no verdict, but keep the evidence
        report = {'status': 'TOOL_ERROR', 'scope': SCOPE, 'error': traceback.format_exc(),
                  'gates': {'renderer_gl': 'UNVERIFIED', 'no_gl_context_or_draw': 'UNVERIFIED'}}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], report['gates']['renderer_gl'], report['gates']['no_gl_context_or_draw'], args.output,
          flush=True)
    return EXIT[report['status']]


if __name__ == '__main__':
    try:
        code = main()
    except Exception:  # e.g. the report cannot be written: still a tool error, never a verdict
        traceback.print_exc()
        code = EXIT['TOOL_ERROR']
    raise SystemExit(code)
