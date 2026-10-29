# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap observer: Linux x86-64 loads, symbol bindings and GL calls, with callers.

Derived by tools/hot_swap/derive_linux_observer.py from tools/no_opengl/linux.py
(sha256 e106dab04f4947b9007edd7833423bf40796aa2783dd9f4d3573d34431e3c775), which stays unchanged for the strict profile. It runs the derived
tools/hot_swap/loader_audit_linux.c and debugger_linux.c. Differences: records carry wall-clock time;
loads carry the object that requested them (loader_caller), GL bindings their referencing object
and GL calls the module holding their return address (direct_caller), and GL calls their export's
other names (aliases). Malformed records are errors; the coverage rules are the strict observer's.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess

# Value fields per record kind; any other kind has one. A record is its kind, pid, values and wall-clock time.
LOADER_FIELDS = {'native_load': 2, 'native_gl_binding': 3}
DEBUGGER_FIELDS = {'native_gl_call': 5, 'native_gl_binding': 3}


def record(line, fields, paths=None):
    """One collector record as an event, or None if malformed. A single value is the event's path for the kinds in
    paths (every kind when None); callers are {'path': None} when unknown."""
    parts = line.split('\t')
    if len(parts) < 4 or not parts[1].isdigit():
        return None
    kind, values = parts[0], parts[2:-1]
    try:
        wall = float(parts[-1])
    except ValueError:
        return None
    if not math.isfinite(wall) or wall <= 0 or len(values) != fields.get(kind, 1):
        return None
    row = {'kind': kind, 'pid': int(parts[1]), 'wall': wall, 'detail': '\t'.join(values)}
    if kind == 'native_gl_call':
        name, aliases, path, caller, address = values
        row.update(name=name, aliases=aliases.split(','), path=path,
                   direct_caller={'path': caller or None, 'address': address})
    elif kind == 'native_gl_binding':
        row.update(name=values[0], direct_caller={'path': values[1] or None}, path=values[2])
    elif kind == 'native_load' and len(values) == 2:
        row.update(path=values[0], loader_caller={'path': values[1] or None})
    elif paths is None or kind in paths:
        row['path'] = values[0]
    return row


def trace(command, *, auditor, environment, cwd, log, trace_path, timeout=120, debugger=None):
    auditor = Path(auditor).resolve(strict=True)
    trace_path = Path(trace_path).resolve()
    if trace_path.exists():
        raise ValueError('Fresh native trace required')
    environment = dict(environment, VISPY_NO_GL_NATIVE_LOG=str(trace_path))
    debugger_path = trace_path.with_suffix('.debugger.tsv')
    if debugger:
        debugger = Path(debugger).resolve(strict=True)
        if debugger_path.exists():
            raise ValueError('Fresh debugger trace required')
        environment.update(VISPY_NO_GL_AUDITOR=str(auditor))
        environment.pop('LD_AUDIT', None)
        environment.pop('VISPY_NO_GL_PTRACE_HANDSHAKE', None)
        command = [str(debugger), str(debugger_path), str(trace_path), '--', *command]
    else:
        environment.update(LD_AUDIT=str(auditor), LD_BIND_NOW='1')
    with Path(log).open('wb') as output:
        child = subprocess.Popen(command, env=environment, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            raise
    events, errors = [], []
    for line in trace_path.read_text(encoding='utf-8', errors='replace').splitlines() if trace_path.exists() else []:
        row = record(line, LOADER_FIELDS)
        if row is None:
            errors.append({'error': 'Malformed native trace line', 'line': line})
            continue
        kind, pid, value = row['kind'], row['pid'], row['detail']
        events.append(row)
        if kind == 'audit_error':
            errors.append({'error': value, 'pid': int(pid)})
    starts = {row['pid'] for row in events if row['kind'] == 'audit_start'}
    exits = {row['pid'] for row in events if row['kind'] == 'audit_exit'}
    if not debugger and (not starts or child.pid not in starts or (code == 0 and not starts <= exits)):
        errors.append({'error': 'Missing glibc collector startup or normal shutdown',
                       'root_pid': child.pid, 'started_pids': sorted(starts), 'exited_pids': sorted(exits)})
    coverage = {'startup_and_transient_native_loads': False,
                'glibc_startup_and_transient_objects': not errors,
                'native_external_gl_symbol_binding': not errors,
                'native_public_gl_export_breakpoints': False,
                'native_entrypoint_resolution': False, 'process_tree': False,
                'private_or_statically_linked_gl_implementations': False}
    if debugger:
        begun, ended, execs, audit_starts, complete = set(), set(), {}, {}, False
        static_execs = []
        for row in events:
            if row['kind'] == 'audit_start':
                audit_starts[row['pid']] = audit_starts.get(row['pid'], 0) + 1
        for line in debugger_path.read_text(encoding='utf-8', errors='replace').splitlines() if debugger_path.exists() else []:
            row = record(line, DEBUGGER_FIELDS, ('native_load', 'native_unload'))
            if row is None:
                errors.append({'error': 'Malformed debugger trace', 'line': line})
                continue
            kind, pid, value = row['kind'], row['pid'], row['detail']
            if kind == 'debug_error':
                errors.append({'error': value, 'pid': pid})
            if kind in ('debug_task_start', 'debug_task_exit'):
                tid = value.split()[0].removeprefix('tid=')
                (begun if kind == 'debug_task_start' else ended).add((pid, tid))
            if kind == 'debug_exec':
                row['path'], _, row['interpreter'] = value.partition('|')
                if row['interpreter']:
                    execs[pid] = execs.get(pid, 0) + 1
                else:
                    static_execs.append({'pid': pid, 'path': row['path']})
            if kind == 'debug_complete':
                complete = 'errors=0 ' in value
            events.append(row)
        tree = bool(begun) and begun == ended and complete
        collectors = bool(execs or static_execs) and all(audit_starts.get(pid, 0) >= count for pid, count in execs.items())
        if not tree or not collectors:
            errors.append({'error': 'Incomplete debugger tree or exec collector coverage',
                           'started_tasks': sorted(begun), 'exited_tasks': sorted(ended),
                           'execs': execs, 'auditor_starts': audit_starts})
        full = tree and collectors and not errors
        coverage.update(startup_and_transient_native_loads=full,
                        native_public_gl_export_breakpoints=full,
                        native_entrypoint_resolution=full, process_tree=tree,
                        ptrace_loader_handshake=full)
        coverage['static_exec_executable_mappings_and_public_exports'] = full
    return {'events': events, 'errors': errors, 'process_exit': code, 'root_pid': child.pid,
            'auditor_sha256': hashlib.sha256(auditor.read_bytes()).hexdigest(),
            'trace_sha256': hashlib.sha256(trace_path.read_bytes()).hexdigest() if trace_path.exists() else None,
            'debugger_sha256': hashlib.sha256(debugger.read_bytes()).hexdigest() if debugger else None,
            'coverage': coverage,
            'scope': ('Linux x86-64 ptrace process tree, pre-constructor loader handshake, '
                      'ELF public GL-export call traps: context, make-current, swap and draw calls stop the '
                      'tree, other calls are recorded with their caller and stepped over past a leading endbr64; '
                      'glibc symbol bindings including dlsym, with their referencing object; loads with the '
                      'object that requested them; '
                      'dynamic exec collector variables restored before loader entry; static execs use '
                      'mapping syscall stops and ELF public-export inspection. Private/static non-exported '
                      'implementations and manual export parsing excluded.'
                      if debugger else 'glibc dynamic-loader objects and symbol bindings including dlsym; '
                      'direct/local calls, private symbol resolution, non-glibc children '
                      'and complete fork/exec process-tree observation are not established.')}
