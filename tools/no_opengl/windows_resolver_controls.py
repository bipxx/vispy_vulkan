"""Prove concurrent resolver observation preserves native entry semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from .dependencies import inspect_binary
from .windows import trace


def entry_bytes(path):
    image = inspect_binary(path)
    rva = next(row['rva'] for row in image['exports'] if row['name'] == 'GetProcAddress')
    data = path.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    start = pe + 24 + struct.unpack_from('<H', data, pe + 20)[0]
    for index in range(sections):
        size, address, raw_size, offset = struct.unpack_from('<IIII', data, start + index * 40 + 8)
        if address <= rva < address + min(size, raw_size):
            return data[offset + rva - address:offset + rva - address + 7]
    raise ValueError('Control entry is outside raw executable sections')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Native Windows controls require Windows')
    control = args.control.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    checks, cases = {}, {}
    instruction = entry_bytes(control)
    # LOCK INC [RIP+disp32]: the intercepted first instruction has an observable
    # effect. Native exact count 1024 proves deferred entries are not replayed.
    checks['entry_instruction_is_atomic_increment'] = instruction[:3] == b'\xf0\xff\x05'
    deferred = 0
    for mode in ('safe', 'lookup', 'call'):
        environment = dict(os.environ, VISPY_RESOLVER_RACE_AFTER=mode)
        baseline = subprocess.run([str(control)], env=environment, capture_output=True, text=True,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        checks[mode + '_ordinary_exact_count_arguments_returns'] = (
            baseline.returncode == 0 and baseline.stdout == 'ordinary_resolvers_completed\n')
        observed = trace([str(control)], environment=environment, cwd=output,
                         log=output / (mode + '.log'), timeout=60)
        (output / (mode + '.json')).write_text(json.dumps(observed, indent=2) + '\n')
        events = observed['events']
        count = sum(row['kind'] == 'native_resolver_step_deferred' for row in events)
        deferred += count
        checks[mode + '_observer_errors_empty'] = not observed['errors']
        checks[mode + '_concurrent_exact_count_arguments_returns'] = (
            (output / (mode + '.log')).read_text() == 'ordinary_resolvers_completed\n')
        if mode == 'safe':
            checks['safe_threads_finish_without_held_peer'] = observed['process_exit'] == 0
        else:
            kind = 'native_gl_binding' if mode == 'lookup' else 'native_gl_call'
            checks[mode + '_gl_still_detected'] = observed['process_exit'] == 86 and any(
                row['kind'] == kind for row in events)
        cases[mode] = {'baseline_exit': baseline.returncode, 'observed_exit': observed['process_exit'],
                       'deferred_events': count}
        print(mode, observed['process_exit'], count, flush=True)
    checks['queued_resolver_deferral_actually_exercised'] = deferred > 0
    report = {'schema': 1, 'status': 'PASS_RESOLVER_CONCURRENCY_CONTROLS' if all(checks.values()) else 'FAIL_RESOLVER_CONCURRENCY_CONTROLS',
              'checks': checks, 'cases': cases, 'entry_instruction_hex': instruction.hex(),
              'control_source_sha256': hashlib.sha256(Path(__file__).with_name('resolver_race_probe_windows.c').read_bytes()).hexdigest(),
              'control_binary_sha256': hashlib.sha256(control.read_bytes()).hexdigest(),
              'scope': '32 native threads; 1024 counted intercepted entries plus 1024 real ordinary lookups; exact argument/return checks; GL lookup/direct-call controls after ordinary completion.'}
    (output / 'controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], flush=True)
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
