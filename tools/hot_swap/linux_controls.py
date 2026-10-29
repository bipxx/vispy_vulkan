# SPDX-License-Identifier: AGPL-3.0-only
"""Native controls for the hot-swap Linux observer (tools/hot_swap/linux_observer.py), without Python audit hooks.

Builds synthetic fixtures with the existing C compiler, none of them a GL implementation: a library of GL-named
exports named like a GLX vendor library (so its load is GL activity), a host library that calls and looks them up, a
driver program, and a static program. Each control runs under the derived auditor and debugger and must show:
- a GL call from the host library is recorded with that library as its caller, executed once and stepped over, and
  recorded as host activity; under renderer roots the same call is the renderer's;
- the GL library's load records the host library as its requester, and a dlsym lookup the host library as its
  referencing object;
- a context call, a draw call and a call through an export whose alias is a draw name stop the tree before executing;
- an export whose first instruction is not endbr64 fails closed: the call is recorded, an observer error stops the tree;
- 32 threads each entering a counted GL export 32 times: every entry is recorded and the export ran exactly 1024 times;
- a forked and an exec'd child are observed alike, and a static program's GL call and GL lookup are stepped over.
The compiled entry bytes are verified first. PASS_CONTROLS describes the observer, never a candidate artifact.

Usage: tools/hot_swap/linux_controls.py --output <new directory> [--native-auditor <so> --native-debugger <exe>]
Without the collectors, it builds tools/hot_swap/loader_audit_linux.c and debugger_linux.c itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.hot_swap.linux_observer import trace  # noqa: E402
from tools.hot_swap.policy import assess_hot_swap, correlate, gl_reason  # noqa: E402

GL_LIBRARY, HOST_LIBRARY = 'libGLX_hotswapcontrol.so.0', 'libhotswap_host.so'
DRIVER, STATIC = 'hot_swap_control_driver', 'hot_swap_static_control'
THREADS = CALLS = 32
ENDBR64 = 'f30f1efa'
STEPPABLE = ('glHotSwapQueryControl', 'glHotSwapLookupControl', 'glHotSwapCountedControl', 'glDrawArrays',
             'eglCreateContext', 'glHotSwapAliasControl', 'glMultiDrawArrays')
UNSTEPPABLE = ('glHotSwapUnsteppableControl',)
COVERAGE = ('startup_and_transient_native_loads', 'native_public_gl_export_breakpoints', 'native_entrypoint_resolution',
            'process_tree')
CLEAN = {'runtime': [], 'test_only': [], 'errors': [], 'complete': True}
TIMEOUT = 120
# The strict collectors' documented flags (tools/no_opengl/README.md).
COLLECTORS = {'loader_audit.so': ('loader_audit_linux.c', ['-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror']),
              'debugger_linux': ('debugger_linux.c', ['-O2', '-Wall', '-Wextra', '-Werror'])}

GL_SOURCE = r'''/* SPDX-License-Identifier: AGPL-3.0-only
 * GL-named exports for the hot-swap Linux observer controls; not a GL implementation. The bodies differ, so
 * identical-code folding cannot merge exports; only glMultiDrawArrays is an alias, on purpose. */
#define EXPORT __attribute__((visibility("default")))
static volatile int executed;
static unsigned long counted;
EXPORT int glHotSwapQueryControl(int value) { executed = 1; return value * 3 + 1; }
EXPORT int glHotSwapLookupControl(int value) { executed = 1; return value * 11 + 3; }
EXPORT int glHotSwapCountedControl(int value) { __atomic_add_fetch(&counted, 1, __ATOMIC_SEQ_CST); return value * 5 + 2; }
EXPORT __attribute__((nocf_check)) int glHotSwapUnsteppableControl(int value) { executed = 1; return value + 7; }
EXPORT int glDrawArrays(int first, int count, int instances) { executed = 1; return first + count + instances; }
EXPORT int eglCreateContext(void) { executed = 1; return 5; }
EXPORT int glHotSwapAliasControl(void) { executed = 1; return 9; }
EXPORT int glMultiDrawArrays(void) __attribute__((alias("glHotSwapAliasControl")));
EXPORT int hotSwapExecuted(void) { return executed; }
EXPORT unsigned long hotSwapCounted(void) { return __atomic_load_n(&counted, __ATOMIC_SEQ_CST); }
'''
HOST_SOURCE = r'''/* SPDX-License-Identifier: AGPL-3.0-only
 * The host library of the hot-swap Linux observer controls: it calls and looks up the GL-named exports.
 * Built -O0 -fno-optimize-sibling-calls, so each export is called from here, never tail-jumped to. */
#define _GNU_SOURCE
#include <dlfcn.h>
#define EXPORT __attribute__((visibility("default")))
int glHotSwapQueryControl(int value);
int glHotSwapCountedControl(int value);
int glHotSwapUnsteppableControl(int value);
int glDrawArrays(int first, int count, int instances);
int eglCreateContext(void);
int glHotSwapAliasControl(void);
EXPORT int hostQuery(int value) { int result = glHotSwapQueryControl(value); return result; }
EXPORT int hostCounted(int value) { int result = glHotSwapCountedControl(value); return result; }
EXPORT int hostUnsteppable(int value) { int result = glHotSwapUnsteppableControl(value); return result; }
EXPORT int hostDraw(void) { int result = glDrawArrays(1, 2, 3); return result; }
EXPORT int hostContext(void) { int result = eglCreateContext(); return result; }
EXPORT int hostAlias(void) { int result = glHotSwapAliasControl(); return result; }
/* A lookup without a call, of a name this library does not import. */
EXPORT int hostLookup(void) {
    void *module = dlopen("@GL_LIBRARY@", RTLD_NOW | RTLD_NOLOAD);
    int found = module && dlsym(module, "glHotSwapLookupControl");
    if (module) dlclose(module);
    return found;
}
'''
DRIVER_SOURCE = r'''/* SPDX-License-Identifier: AGPL-3.0-only
 * Driver of the hot-swap Linux observer controls; no GL implementation. Usage: driver MODE FIXTURE_DIRECTORY */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#define THREADS @THREADS@
#define CALLS @CALLS@
typedef int (*unary)(int);
typedef int (*nullary)(void);
typedef unsigned long (*counter)(void);
static void *host, *gl;
static void *symbol(void *module, const char *name) {
    void *value = dlsym(module, name);
    if (!value) { fprintf(stderr, "missing %s: %s\n", name, dlerror()); exit(80); }
    return value;
}
static void *worker(void *argument) {
    unary counted = (unary)symbol(host, "hostCounted");
    long index = (long)argument, failures = 0;
    for (int n = 0; n < CALLS; ++n) {
        int value = (int)index * CALLS + n;
        if (counted(value) != value * 5 + 2) ++failures;
    }
    return (void *)failures;
}
static int child_status(pid_t child) {
    int status;
    if (child < 0 || waitpid(child, &status, 0) != child) return 70;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 71;
}
int main(int argc, char **argv) {
    if (argc != 3) return 90;
    const char *mode = argv[1], *directory = argv[2];
    if (!strcmp(mode, "safe")) { puts("PASS safe"); return 0; }
    char path[4096];
    snprintf(path, sizeof(path), "%s/@HOST_LIBRARY@", directory);
    host = dlopen(path, RTLD_NOW);
    if (!host) { fprintf(stderr, "%s\n", dlerror()); return 81; }
    snprintf(path, sizeof(path), "%s/@GL_LIBRARY@", directory);
    gl = dlopen(path, RTLD_NOW | RTLD_NOLOAD);
    if (!gl) { fprintf(stderr, "%s\n", dlerror()); return 82; }
    nullary executed = (nullary)symbol(gl, "hotSwapExecuted");
    if (!strcmp(mode, "query")) {
        int result = ((unary)symbol(host, "hostQuery"))(7);
        printf("query %d executed %d\n", result, executed());
        return result == 22 && executed() == 1 ? 0 : 3;
    }
    if (!strcmp(mode, "lookup")) return ((nullary)symbol(host, "hostLookup"))() == 1 && !executed() ? 0 : 4;
    if (!strcmp(mode, "context")) { printf("EXECUTED context %d\n", ((nullary)symbol(host, "hostContext"))()); return 5; }
    if (!strcmp(mode, "draw")) { printf("EXECUTED draw %d\n", ((nullary)symbol(host, "hostDraw"))()); return 6; }
    if (!strcmp(mode, "alias")) { printf("EXECUTED alias %d\n", ((nullary)symbol(host, "hostAlias"))()); return 7; }
    if (!strcmp(mode, "unsteppable")) {
        printf("EXECUTED unsteppable %d\n", ((unary)symbol(host, "hostUnsteppable"))(1));
        return 8;
    }
    if (!strcmp(mode, "threads")) {
        pthread_t threads[THREADS];
        long failures = 0;
        for (long i = 0; i < THREADS; ++i) if (pthread_create(&threads[i], NULL, worker, (void *)i)) return 9;
        for (int i = 0; i < THREADS; ++i) {
            void *result;
            if (pthread_join(threads[i], &result)) return 10;
            failures += (long)result;
        }
        unsigned long entries = ((counter)symbol(gl, "hotSwapCounted"))();
        printf("threads entries %lu failures %ld\n", entries, failures);
        return entries == THREADS * CALLS && !failures ? 0 : 11;
    }
    if (!strcmp(mode, "fork_query")) {
        fflush(stdout);
        pid_t child = fork();
        if (!child) _exit(((unary)symbol(host, "hostQuery"))(7) == 22 && executed() == 1 ? 0 : 12);
        return child_status(child);
    }
    if (!strcmp(mode, "exec_query")) {
        fflush(stdout);
        pid_t child = fork();
        if (!child) { execl("/proc/self/exe", argv[0], "query", directory, (char *)NULL); _exit(13); }
        return child_status(child);
    }
    return 99;
}
'''
STATIC_SOURCE = r'''/* SPDX-License-Identifier: AGPL-3.0-only
 * Static-executable control of the hot-swap Linux observer; no GL implementation. Usage: static call|lookup LIBRARY */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int glHotSwapStaticControl(int value) { return value * 7 + 1; }
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    if (!strcmp(argv[1], "call")) {
        int result = glHotSwapStaticControl(3);
        printf("static call %d\n", result);
        return result == 22 ? 0 : 3;
    }
    void *module = dlopen(argv[2], RTLD_NOW);
    if (!module) return 4;
    return dlsym(module, "glHotSwapLookupControl") ? 0 : 5;
}
'''


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_compiler(compiler, arguments, log):
    command = [compiler, *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True)
    log.append({'command': command, 'exit': result.returncode, 'stderr': result.stderr[-4000:]})
    if result.returncode:
        raise RuntimeError('Compilation failed: %s\n%s' % (' '.join(command), result.stderr))


def build_collectors(compiler, directory, log):
    """Compile the derived auditor and debugger with the strict collectors' flags."""
    directory.mkdir(parents=True, exist_ok=True)
    built = []
    for name, (source, flags) in COLLECTORS.items():
        run_compiler(compiler, [*flags, '-o', directory / name, ROOT / 'tools/hot_swap' / source], log)
        built.append(directory / name)
    return tuple(built)


def build_fixtures(compiler, directory, log):
    directory.mkdir(parents=True, exist_ok=True)
    sources = {'gl.c': GL_SOURCE, 'host.c': HOST_SOURCE, 'driver.c': DRIVER_SOURCE, 'static.c': STATIC_SOURCE}
    for name, text in sources.items():
        text = (text.replace('@GL_LIBRARY@', GL_LIBRARY).replace('@HOST_LIBRARY@', HOST_LIBRARY)
                .replace('@THREADS@', str(THREADS)).replace('@CALLS@', str(CALLS)))
        (directory / name).write_bytes(text.encode())
    warnings = ['-Wall', '-Wextra', '-Werror']
    run_compiler(compiler, ['-shared', '-fPIC', '-O2', '-fcf-protection=full', *warnings,
                            '-Wl,-soname,' + GL_LIBRARY, '-o', directory / GL_LIBRARY, directory / 'gl.c'], log)
    run_compiler(compiler, ['-shared', '-fPIC', '-O0', '-fno-optimize-sibling-calls', '-fcf-protection=full', *warnings,
                            '-o', directory / HOST_LIBRARY, directory / 'host.c', '-L', directory, '-l:' + GL_LIBRARY,
                            '-Wl,-rpath,$ORIGIN', '-ldl'], log)
    run_compiler(compiler, ['-O0', '-fcf-protection=full', '-pthread', *warnings, '-o', directory / DRIVER,
                            directory / 'driver.c', '-ldl'], log)
    run_compiler(compiler, ['-static', '-O0', '-fcf-protection=full', *warnings, '-o', directory / STATIC,
                            directory / 'static.c', '-ldl'], log)
    return {path.name: sha256(path) for path in sorted(directory.iterdir())}


def export_entries(path, names):
    """The first four bytes, as hex, of each named dynamic export of an ELF64 image, read through its load segments."""
    data = Path(path).read_bytes()
    phoff, shoff = struct.unpack_from('<QQ', data, 32)
    phentsize, phnum, shentsize, shnum = struct.unpack_from('<HHHH', data, 54)
    loads = [struct.unpack_from('<IIQQQQQQ', data, phoff + index * phentsize) for index in range(phnum)]
    loads = [(vaddr, size, offset) for kind, _, offset, vaddr, _, size, _, _ in loads if kind == 1]
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + index * shentsize) for index in range(shnum)]
    found = {}
    for _, kind, _, _, offset, size, link, _, _, entry in sections:
        if kind != 11:  # SHT_DYNSYM
            continue
        strings = sections[link][4]
        for index in range(1, size // entry):
            name_at, _, _, shndx, value, _ = struct.unpack_from('<IBBHQQ', data, offset + index * entry)
            name = data[strings + name_at:data.index(b'\0', strings + name_at)].decode()
            if name in names and shndx:
                at = next(value - vaddr + start for vaddr, length, start in loads if vaddr <= value < vaddr + length)
                found[name] = data[at:at + 4].hex()
    return found


def controls(fixtures):
    driver = [str(fixtures / DRIVER)]
    modes = ('safe', 'query', 'lookup', 'context', 'draw', 'alias', 'unsteppable', 'threads', 'fork_query', 'exec_query')
    return [*((mode, [*driver, mode, str(fixtures)]) for mode in modes),
            ('static_call', [str(fixtures / STATIC), 'call', str(fixtures / GL_LIBRARY)]),
            ('static_lookup', [str(fixtures / STATIC), 'lookup', str(fixtures / GL_LIBRARY)])]


def leaf(module):
    return Path((module or {}).get('path') or '').name


def calls(report, name):
    return [e for e in report['events'] if e['kind'] == 'native_gl_call' and name in e.get('aliases', [e.get('name')])]


def complete(report):
    return not report['errors'] and all(report['coverage'].get(key) for key in COVERAGE)


def clean(report):
    return report['process_exit'] == 0 and complete(report)


def gates(report, roots=()):
    return assess_hot_swap(correlate(report['events'], [], roots), attribution_complete=True,
                           native_api_complete=all(report['coverage'].get(key) for key in COVERAGE[1:]),
                           native_loads_complete=bool(report['coverage'].get(COVERAGE[0])),
                           execution_succeeded=report['process_exit'] == 0, static=CLEAN)


def root_pid(report):
    return next((e['pid'] for e in report['events'] if e['kind'] == 'debug_task_start'), None)


def evaluate(reports, logs, entries, fixtures):
    def stopped(name, export):
        report, found = reports[name], calls(reports[name], export)
        return (len(found) == 1 and leaf(found[0]['direct_caller']) == HOST_LIBRARY and complete(report)
                and report['process_exit'] == 128 + 9 and 'EXECUTED' not in logs[name]
                and gates(report)['no_gl_context_or_draw'] == 'FAIL')

    query, threads, unsteppable = reports['query'], reports['threads'], reports['unsteppable']
    counted = calls(threads, 'glHotSwapCountedControl')
    blocked = calls(unsteppable, 'glHotSwapUnsteppableControl')
    host_gates = gates(query)
    return {
        'entry_bytes_endbr64_where_expected': sorted(entries) == sorted((*STEPPABLE, *UNSTEPPABLE))
        and all(entries[name] == ENDBR64 for name in STEPPABLE) and all(entries[name] != ENDBR64 for name in UNSTEPPABLE),
        'safe_control_clean_without_gl': clean(reports['safe']) and not any(map(gl_reason, reports['safe']['events'])),
        'host_call_recorded_with_host_caller': [leaf(e['direct_caller']) for e in calls(query, 'glHotSwapQueryControl')]
        == [HOST_LIBRARY],
        'host_call_stepped_over_and_executed_once': clean(query) and 'query 22 executed 1' in logs['query'],
        'gl_library_load_requested_by_host': any(
            e['kind'] == 'native_load' and Path(e['path']).name == GL_LIBRARY and leaf(e.get('loader_caller')) == HOST_LIBRARY
            for e in query['events']),
        'host_library_load_requested_by_driver': any(
            e['kind'] == 'native_load' and Path(e['path']).name == HOST_LIBRARY and leaf(e.get('loader_caller')) == DRIVER
            for e in query['events']),
        'host_gl_activity_recorded_not_failed': host_gates['renderer_gl'] == host_gates['no_gl_context_or_draw'] == 'PASS'
        and bool(host_gates['host_gl_events']) and not host_gates['unattributed_gl_events'],
        'renderer_roots_make_the_same_call_the_renderers': gates(query, [str(fixtures)])['renderer_gl'] == 'FAIL',
        'lookup_referenced_by_host_without_call': clean(reports['lookup']) and any(
            e['kind'] == 'native_gl_binding' and e['name'] == 'glHotSwapLookupControl'
            and leaf(e['direct_caller']) == HOST_LIBRARY for e in reports['lookup']['events'])
        and not calls(reports['lookup'], 'glHotSwapLookupControl'),
        'context_call_stops_before_execution': stopped('context', 'eglCreateContext'),
        'draw_call_stops_before_execution': stopped('draw', 'glDrawArrays'),
        'draw_alias_stops_before_execution': stopped('alias', 'glHotSwapAliasControl')
        and all('glMultiDrawArrays' in e['aliases'] for e in calls(reports['alias'], 'glHotSwapAliasControl')),
        'export_without_endbr64_fails_closed': len(blocked) == 1 and leaf(blocked[0]['direct_caller']) == HOST_LIBRARY
        and 'EXECUTED' not in logs['unsteppable'] and unsteppable['process_exit'] != 0 and not complete(unsteppable)
        and any('endbr64' in str(error.get('error')) for error in unsteppable['errors'])
        and gates(unsteppable)['no_gl_context_or_draw'] == 'UNVERIFIED',
        'threads_every_entry_recorded_and_executed_once': clean(threads)
        and f'threads entries {THREADS * CALLS} failures 0' in logs['threads'] and len(counted) == THREADS * CALLS
        and all(leaf(e['direct_caller']) == HOST_LIBRARY for e in counted),
        'threads_all_tasks_observed': sum(e['kind'] == 'debug_task_start' and e['pid'] == root_pid(threads)
                                          for e in threads['events']) >= THREADS + 1,
        'fork_child_call_recorded': clean(reports['fork_query']) and any(
            e['pid'] != root_pid(reports['fork_query']) and leaf(e['direct_caller']) == HOST_LIBRARY
            for e in calls(reports['fork_query'], 'glHotSwapQueryControl')),
        'exec_child_call_recorded': clean(reports['exec_query']) and any(
            e['pid'] != root_pid(reports['exec_query']) and e['pid'] in {
                x['pid'] for x in reports['exec_query']['events'] if x['kind'] == 'debug_exec'}
            for e in calls(reports['exec_query'], 'glHotSwapQueryControl')),
        'static_call_stepped_over': clean(reports['static_call']) and 'static call 22' in logs['static_call']
        and [leaf(e['direct_caller']) for e in calls(reports['static_call'], 'glHotSwapStaticControl')] == [STATIC],
        'static_lookup_recorded_and_stepped': clean(reports['static_lookup']) and any(
            e['kind'] == 'native_gl_binding' and e['name'] == 'glHotSwapLookupControl'
            and leaf(e['direct_caller']) == STATIC for e in reports['static_lookup']['events']),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='a new directory')
    parser.add_argument('--native-auditor', type=Path)
    parser.add_argument('--native-debugger', type=Path)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args(argv)
    if not sys.platform.startswith('linux'):
        parser.error('The native controls need Linux x86-64')
    if bool(args.native_auditor) != bool(args.native_debugger):
        parser.error('Give both collectors, or neither to build them')
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    compiler = shutil.which(args.cc) or args.cc
    commands = []
    if args.native_auditor:
        auditor, debugger = args.native_auditor.resolve(strict=True), args.native_debugger.resolve(strict=True)
    else:
        auditor, debugger = build_collectors(compiler, output / 'collectors', commands)
    identity = {'auditor_sha256': sha256(auditor), 'debugger_sha256': sha256(debugger),
                'sources_sha256': {name: sha256(ROOT / 'tools/hot_swap' / name)
                                   for name in ('loader_audit_linux.c', 'debugger_linux.c', 'linux_observer.py',
                                                'linux_controls.py', 'policy.py')}}
    fixtures = output / 'fixtures'
    fixture_hashes = build_fixtures(compiler, fixtures, commands)
    entries = export_entries(fixtures / GL_LIBRARY, (*STEPPABLE, *UNSTEPPABLE))
    environment = {key: value for key, value in os.environ.items() if key not in ('LD_AUDIT', 'LD_PRELOAD')}
    reports, logs = {}, {}
    for name, command in controls(fixtures):
        reports[name] = trace(command, auditor=auditor, environment=environment, cwd=output, log=output / f'{name}.log',
                              trace_path=output / f'{name}.loader.tsv', timeout=TIMEOUT, debugger=debugger)
        logs[name] = (output / f'{name}.log').read_text(encoding='utf-8', errors='replace')
        (output / f'{name}.json').write_text(json.dumps(reports[name], indent=2) + '\n', encoding='utf-8')
    checks = evaluate(reports, logs, entries, fixtures)
    checks['collector_identity_stable'] = identity['auditor_sha256'] == sha256(auditor) and (
        identity['debugger_sha256'] == sha256(debugger))
    report = {'status': 'PASS_CONTROLS' if all(checks.values()) else 'FAIL_CONTROLS', 'checks': checks,
              'collectors': identity, 'compiler': compiler, 'commands': commands, 'fixtures_sha256': fixture_hashes,
              'entry_bytes': entries, 'process_exits': {name: value['process_exit'] for name, value in reports.items()},
              'scope': 'Hot-swap Linux observer controls only, never a candidate artifact.',
              'reports_sha256': {name: sha256(output / f'{name}.json') for name in reports}}
    (output / 'controls.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], output / 'controls.json')
    return 0 if report['status'] == 'PASS_CONTROLS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
