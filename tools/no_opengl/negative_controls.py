"""Run independent native controls without installing Python audit hooks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from .policy import assess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--native-auditor', type=Path)
    parser.add_argument('--native-debugger', type=Path)
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = args.output.resolve()
    fixture = args.fixture.resolve(strict=True)
    windows = sys.platform == 'win32'
    if not windows and not args.native_auditor:
        parser.error('Linux controls require --native-auditor')
    transient = root / ('opengl32.dll' if windows else 'libGL.so.1')
    shutil.copyfile(fixture, transient)
    prefix = f'import ctypes; x=ctypes.CDLL({str(fixture)!r});'
    cases = {
        'safe': prefix + 'assert x.auditSafeControl()==23',
        'resolve': prefix + 'x.auditResolveControl.argtypes=[ctypes.c_void_p];assert x.auditResolveControl(x._handle)==1',
        'call': prefix + 'assert x.auditCallControl()==17',
        'transient': f'import ctypes,_ctypes;x=ctypes.CDLL({str(transient)!r});assert x.auditSafeControl()==23;'
                     + ('_ctypes.FreeLibrary(x._handle)' if windows else '_ctypes.dlclose(x._handle)'),
    }
    cases['child_call'] = ('import subprocess,sys;subprocess.run([sys.executable,"-I","-B","-c",'
                           + repr(prefix + 'assert x.auditCallControl()==17') + '],check=True)')
    if not windows:
        cases['fork_call'] = prefix + 'import os;pid=os.fork();x.auditCallControl() if pid==0 else os.waitpid(pid,0)'
    reports = {}
    for name, code in cases.items():
        command = [str(args.python.resolve(strict=True)), '-I', '-B', '-c', code]
        if windows:
            from .windows import trace
            native = trace(command, environment=os.environ.copy(), cwd=root, log=root / (name + '.log'))
        else:
            from .linux import trace
            native = trace(command, auditor=args.native_auditor, environment=os.environ.copy(), cwd=root,
                           log=root / (name + '.log'), trace_path=root / (name + '.loader.tsv'),
                           debugger=args.native_debugger)
        events = native['events']
        api_complete = all(native['coverage'].get(key, False) for key in
                           ('native_public_gl_export_breakpoints', 'native_entrypoint_resolution', 'process_tree'))
        gates = assess(events, native_loads_complete=native['coverage']['startup_and_transient_native_loads'],
                       native_api_complete=api_complete, execution_succeeded=native['process_exit'] == 0)
        native['gates'] = gates
        (root / (name + '.json')).write_text(json.dumps(native, indent=2) + '\n')
        reports[name] = native
    def seen(case, kind):
        return any(row['kind'] == kind for row in reports[case]['events'])
    checks = {
        'safe_control_exits_zero': reports['safe']['process_exit'] == 0,
        'safe_control_has_no_gl_violation': not reports['safe']['gates']['violations'],
        'native_lookup_without_call_detected': seen('resolve', 'native_gl_binding'),
        'transient_forbidden_load_detected': reports['transient']['gates']['no_gl_loads'] == 'FAIL',
        'transient_unload_observed': any(row['kind'] == 'native_unload' and
                                        Path(row.get('path') or '').name == transient.name
                                        for row in reports['transient']['events']),
        'no_collector_errors': not any(value['errors'] for value in reports.values()),
    }
    if windows or args.native_debugger:
        checks['native_direct_call_detected'] = seen('call', 'native_gl_call')
        checks['exec_child_native_call_detected'] = seen('child_call', 'native_gl_call')
        if not windows:
            checks['fork_child_inherited_native_call_detected'] = seen('fork_call', 'native_gl_call')
    else:
        # The local-call control is linked -Bsymbolic. Its successful undetected
        # invocation demonstrates why LD_AUDIT cannot pass the execution gate.
        checks['local_call_coverage_gap_exposed'] = reports['call']['process_exit'] == 0 and not seen('call', 'native_gl_call')
        checks['local_call_never_claimed_as_pass'] = reports['call']['gates']['no_gl_execution'] == 'UNVERIFIED'
    report = {'status': 'PASS_CONTROLS' if all(checks.values()) else 'FAIL_CONTROLS',
              'checks': checks, 'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'scope': 'Collector controls only, never candidate artifact qualification.',
              'reports': {name: str(root / (name + '.json')) for name in reports}}
    (root / 'controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], root / 'controls.json')
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
