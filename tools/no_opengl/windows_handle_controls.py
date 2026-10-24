"""Prove debugger CloseHandle handling matches ordinary native API behavior."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from .windows import trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows native handle controls require Windows')
    args.output.mkdir(parents=True, exist_ok=False)
    root = args.output.resolve()
    control, fixture = args.control.resolve(strict=True), args.fixture.resolve(strict=True)
    checks, cases = {}, {}
    for mode in ('invalid', 'protected'):
        environment = dict(os.environ, VISPY_HANDLE_CONTROL_MODE=mode, VISPY_HANDLE_CONTROL_AFTER='safe',
                           VISPY_HANDLE_CONTROL_DLL=str(fixture))
        baseline = subprocess.run([str(control)], env=environment, capture_output=True, text=True,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        value = json.loads(baseline.stdout)
        checks[mode + '_ordinary_false_error6'] = baseline.returncode == 0 and value == {'closed': 0, 'error': 6}
        cases[mode + '_baseline'] = {'process_exit': baseline.returncode, 'result': value, 'stderr': baseline.stderr}
        for after in ('safe', 'lookup', 'call', 'unrelated'):
            environment['VISPY_HANDLE_CONTROL_AFTER'] = after
            name = mode + '-' + after
            result = trace([str(control)], environment=environment, cwd=root, log=root / (name + '.log'),
                           timeout=60, _handle_control=True)
            (root / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
            resumed = [row for row in result['events'] if row['kind'] == 'native_debugger_closehandle_return']
            checks[name + '_os_close_source_attributed'] = bool(resumed) and not result['errors']
            if after == 'safe':
                observed = json.loads((root / (name + '.log')).read_text())
                checks[name + '_matches_ordinary_return'] = result['process_exit'] == baseline.returncode and observed == value
            elif after == 'unrelated':
                checks[name + '_exception_not_swallowed'] = result['process_exit'] == 0xc0000008 and len(resumed) == 1
            else:
                expected = 'native_gl_binding' if after == 'lookup' else 'native_gl_call'
                checks[name + '_gl_still_detected_after_close'] = result['process_exit'] == 86 and any(row['kind'] == expected for row in result['events'])
    source = Path(__file__).with_name('handle_negative_probe_windows.c')
    os_files = {(Path(os.environ['SystemRoot']) / 'System32' / name).resolve() for name in ('ntdll.dll', 'KernelBase.dll')}
    report = {'schema': 1, 'status': 'PASS_HANDLE_FIDELITY_CONTROLS' if all(checks.values()) else 'FAIL_HANDLE_FIDELITY_CONTROLS',
              'checks': checks, 'baselines': cases, 'control_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'control_binary_sha256': hashlib.sha256(control.read_bytes()).hexdigest(),
              'os_files': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(os_files)},
              'source_documentation': 'https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle',
              'scope': 'Only first-chance OS exception-dispatcher frames unwound through actual CloseHandle/NtClose are normalized. Unrelated/second-chance exceptions and all GL traps remain untouched.'}
    (root / 'controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], root / 'controls.json')
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
