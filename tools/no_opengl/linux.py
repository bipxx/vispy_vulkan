"""glibc loader evidence, with unsupported process/API coverage explicit."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


def trace(command, *, auditor, environment, cwd, log, trace_path, timeout=120):
    auditor = Path(auditor).resolve(strict=True)
    trace_path = Path(trace_path).resolve()
    if trace_path.exists():
        raise ValueError('Fresh native trace required')
    environment = dict(environment, LD_AUDIT=str(auditor), LD_BIND_NOW='1',
                       VISPY_NO_GL_NATIVE_LOG=str(trace_path))
    with Path(log).open('wb') as output:
        child = subprocess.Popen(command, env=environment, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            raise
    events, errors = [], []
    for line in trace_path.read_text().splitlines() if trace_path.exists() else []:
        fields = line.split('\t', 2)
        if len(fields) != 3 or not fields[1].isdigit():
            errors.append({'error': 'Malformed native trace line', 'line': line})
            continue
        kind, pid, value = fields
        events.append({'kind': kind, 'pid': int(pid),
                       'name' if kind == 'native_gl_binding' else 'path': value})
        if kind == 'audit_error':
            errors.append({'error': value, 'pid': int(pid)})
    starts = {row['pid'] for row in events if row['kind'] == 'audit_start'}
    exits = {row['pid'] for row in events if row['kind'] == 'audit_exit'}
    if not starts or child.pid not in starts or not starts <= exits:
        errors.append({'error': 'Missing glibc collector startup or normal shutdown',
                       'root_pid': child.pid, 'started_pids': sorted(starts), 'exited_pids': sorted(exits)})
    return {'events': events, 'errors': errors, 'process_exit': code, 'root_pid': child.pid,
            'auditor_sha256': hashlib.sha256(auditor.read_bytes()).hexdigest(),
            'trace_sha256': hashlib.sha256(trace_path.read_bytes()).hexdigest() if trace_path.exists() else None,
            'coverage': {'startup_and_transient_native_loads': False,
                         'glibc_startup_and_transient_objects': not errors,
                         'native_external_gl_symbol_binding': not errors,
                         'native_public_gl_export_breakpoints': False,
                         'native_entrypoint_resolution': False, 'process_tree': False},
            'scope': 'glibc dynamic-loader objects and symbol bindings including dlsym; '
                     'direct/local calls, private symbol resolution, non-glibc children '
                     'and complete fork/exec process-tree observation are not established.'}
