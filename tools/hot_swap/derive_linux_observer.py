# SPDX-License-Identifier: AGPL-3.0-only
"""Derive the hot-swap Linux observer from the strict one in tools/no_opengl/, which stays unchanged.

The strict pair is a glibc LD_AUDIT module (loader_audit_linux.c) and a ptrace debugger (debugger_linux.c), run by
linux.py; the auditor alone cannot pass (tools/no_opengl/README.md). Each change is an exact replacement that must
match once:
1. Auditor: every record ends with wall-clock time. A load records the object that requested it, from la_objsearch's
   LA_SER_ORIG call (the Linux counterpart of the Windows observer's loader_caller). A GL binding, including dlsym,
   records its referencing and defining objects (the counterpart of direct_caller).
2. Debugger: a GL call records its caller, the module holding the return address at [rsp] on the export trap. Context,
   make-current, swap and draw calls (a C copy of tools/hot_swap/policy.py's tables, under any of the export's names)
   are recorded and still stop the tree before executing. Other calls are recorded and stepped over by moving rip past
   the export's leading endbr64, with the trap kept armed, so no thread is single-stepped. An export whose first
   instruction is not endbr64 fails closed: the call is recorded, an observer error stops the tree. A static
   process's GL lookup is recorded and single-stepped like its other lookups. Every record ends with wall-clock time.
3. linux.py: parses the new records (wall time, callers, aliases) into events; the coverage rules are unchanged.
Supporting changes are commented where they are made. Run this module to regenerate the derived files;
tests/contract/test_hot_swap_linux_observer.py checks that the committed files equal the derivation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.hot_swap.policy import (CONTEXT_NAMES, CONTEXT_PREFIXES, DRAW_NAMES, DRAW_PREFIXES,  # noqa: E402
                                   NOT_DRAW_PREFIXES)

STRICT, DERIVED = ROOT / 'tools/no_opengl', ROOT / 'tools/hot_swap'
AUDITOR, DEBUGGER, OBSERVER = [], [], []


def c_strings(values):
    """A NULL-terminated C string array initializer; the policy tables hold plain identifiers only."""
    assert all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', value) for value in values), values
    return '{' + ', '.join('"%s"' % value for value in values) + ', NULL}'


# 1. The auditor.
AUDITOR.append(('''/* SPDX-License-Identifier: AGPL-3.0-only
 * glibc runtime-linker audit module. Logs loader events before Python starts,
 * including transient dlopen/dlclose and externally bound GL entry points.
 * Build: cc -shared -fPIC -O2 -o loader_audit.so loader_audit_linux.c
 */''', '''/* SPDX-License-Identifier: AGPL-3.0-only
 * Hot-swap loader audit module: glibc LD_AUDIT loads, unloads and GL bindings, with callers.
 * Derived by tools/hot_swap/derive_linux_observer.py from tools/no_opengl/loader_audit_linux.c
 * (sha256 {origin}), which stays unchanged for the strict profile.
 * Differences: every record ends with wall-clock time; a load records the object that requested
 * it (la_objsearch, LA_SER_ORIG); a GL binding records its referencing and defining objects.
 * Build: cc -shared -fPIC -O2 -o loader_audit.so loader_audit_linux.c
 */'''))
AUDITOR.append(('#include <signal.h>\n', '#include <signal.h>\n#include <time.h>\n'))
# The requester of the next load: the loader holds its lock from an LA_SER_ORIG search to the object's open, and
# opens nothing else in between. A name that is already loaded is matched before any search, so no open follows it.
AUDITOR.append(('static int debugger_handshake = 0;\n', '''static int debugger_handshake = 0;
static char main_path[4096];
static char pending_requester[4096], pending_name[4096];
static int pending_search = 0;

static size_t decimal(char *text, unsigned long long number, int width) {
    char reverse[24];
    size_t digits = 0, used = 0;
    do { reverse[digits++] = (char)('0' + number % 10); number /= 10; } while (number || (int)digits < width);
    while (digits) text[used++] = reverse[--digits];
    text[used] = 0;
    return used;
}
'''))
AUDITOR.append(('''static void emit(const char *kind, const char *value) {
    char line[8192];''', '''static void emit_fields(const char *kind, const char *const *values, size_t count) {
    char line[8192];'''))
AUDITOR.append(('''    const char *parts[5] = {kind, "\\t", pid, "\\t", value ? value : ""};
    for (int part = 0; part < 5; ++part)
        for (const char *p = parts[part]; *p && length < sizeof(line) - 2; ++p)
            line[length++] = (*p == '\\n' || *p == '\\r' || (*p == '\\t' && part != 1 && part != 3)) ? '?' : *p;
    line[length++] = '\\n';''', '''    /* kind, pid, the values and wall-clock time, tab-separated; a field's own tabs and line breaks become '?'.
     * A record that does not fit marks the trace incomplete instead of being cut silently. */
    char wall[48];
    struct timespec now;
    if (clock_gettime(CLOCK_REALTIME, &now)) { now.tv_sec = 0; now.tv_nsec = 0; trace_failed = 1; }
    size_t used = decimal(wall, (unsigned long long)now.tv_sec, 1);
    wall[used++] = '.';
    decimal(wall + used, (unsigned long long)now.tv_nsec, 9);
    const char *parts[8] = {kind, pid};
    size_t total = 2;
    for (size_t i = 0; i < count && total < 7; ++i) parts[total++] = values[i] ? values[i] : "";
    parts[total++] = wall;
    for (size_t part = 0; part < total; ++part) {
        if (part) {
            if (length < sizeof(line) - 1) line[length++] = '\\t'; else trace_failed = 1;
        }
        for (const char *p = parts[part]; *p; ++p) {
            if (length >= sizeof(line) - 1) { trace_failed = 1; break; }
            line[length++] = (*p == '\\n' || *p == '\\r' || *p == '\\t') ? '?' : *p;
        }
    }
    line[length++] = '\\n';'''))
AUDITOR.append(('unsigned int la_version(unsigned int version) {', '''static void emit(const char *kind, const char *value) {
    emit_fields(kind, &value, 1);
}

unsigned int la_version(unsigned int version) {'''))
AUDITOR.append(('''    debugger_handshake = handshake && strcmp(handshake, "1") == 0;
''', '''    debugger_handshake = handshake && strcmp(handshake, "1") == 0;
    ssize_t main_length = readlink("/proc/self/exe", main_path, sizeof(main_path) - 1);
    main_path[main_length > 0 ? main_length : 0] = 0;
'''))
AUDITOR.append(('unsigned int la_objopen(struct link_map *map, Lmid_t namespace_id, uintptr_t *cookie) {', '''/* An object's path from its audit cookie (its link map); the main program's empty name is its executable. */
static const char *object_path(uintptr_t cookie) {
    struct link_map *map = (struct link_map *)cookie;
    if (!map) return "";
    return map->l_name && *map->l_name ? map->l_name : main_path;
}
static void copy_text(char *target, size_t size, const char *source) {
    size_t used = 0;
    for (; source && source[used] && used + 1 < size; ++used) target[used] = source[used];
    target[used] = 0;
    if (source && source[used]) trace_failed = 1;
}
static const char *leaf(const char *path) {
    const char *slash = strrchr(path, '/');
    return slash ? slash + 1 : path;
}
char *la_objsearch(const char *name, uintptr_t *cookie, unsigned int flag) {
    if (flag == LA_SER_ORIG) {
        copy_text(pending_requester, sizeof(pending_requester), object_path(*cookie));
        copy_text(pending_name, sizeof(pending_name), name);
        pending_search = 1;
    }
    return (char *)name;
}
/* The requester of a newly opened object: the pending search for the same file name, else unknown. Objects opened
 * without a search (the program, the loader and the vDSO) have none. */
static const char *requester(struct link_map *map) {
    if (!pending_search) return "";
    pending_search = 0;
    return strcmp(leaf(map->l_name), leaf(pending_name)) ? "" : pending_requester;
}

unsigned int la_objopen(struct link_map *map, Lmid_t namespace_id, uintptr_t *cookie) {'''))
AUDITOR.append(('''    emit("native_load", map->l_name);
''', '''    const char *load[2] = {map->l_name, requester(map)};
    emit_fields("native_load", load, 2);
'''))
AUDITOR.append(('''    (void)index; (void)reference; (void)definition; (void)flags;
    if (gl_symbol(name)) emit("native_gl_binding", name);''', '''    (void)index; (void)flags;
    if (gl_symbol(name)) {
        const char *binding[3] = {name, object_path(*reference), object_path(*definition)};
        emit_fields("native_gl_binding", binding, 3);
    }'''))

# 2. The debugger.
DEBUGGER.append(('''/* SPDX-License-Identifier: AGPL-3.0-only
 * Linux x86-64 ptrace process-tree/public GL-export observer. The cooperating
 * LD_AUDIT module stops at object-open/close, before constructors/user code.
 * No GL implementation, injection library or Python hook is used by controls.
 */''', '''/* SPDX-License-Identifier: AGPL-3.0-only
 * Hot-swap observer: Linux x86-64 ptrace process tree and public GL-export calls, with callers.
 * Derived by tools/hot_swap/derive_linux_observer.py from tools/no_opengl/debugger_linux.c
 * (sha256 {origin}), which stays unchanged for the strict profile.
 * Differences: a GL call records its caller, the module holding the return address at [rsp].
 * Context, make-current, swap and draw calls (tools/hot_swap/policy.py), under any of the
 * export's names, are recorded and stop the tree before executing. Other calls are recorded and
 * stepped over past the export's leading endbr64 with the trap kept armed; an export without one
 * fails closed. A static process's GL lookup is recorded and single-stepped like other lookups.
 * Every record ends with wall-clock time; the loader's records carry it as their last field.
 */'''))
DEBUGGER.append(('#include <sys/wait.h>\n#include <unistd.h>\n', '#include <sys/wait.h>\n#include <time.h>\n#include <unistd.h>\n'))
DEBUGGER.append(('typedef struct { pid_t owner; uintptr_t address, bias; unsigned char original; int live, resolver; char *name, *path; } Trap;',
                 'typedef struct { pid_t owner; uintptr_t address, bias; unsigned char original; int live, resolver; char *name, *path; int stop, endbr; char *aliases; } Trap;'))
DEBUGGER.append(("""    fputc('\\n', output); fflush(output);
}""", """    struct timespec now;
    if (clock_gettime(CLOCK_REALTIME, &now)) { now.tv_sec = 0; now.tv_nsec = 0; }
    fprintf(output, "\\t%lld.%09ld\\n", (long long)now.tv_sec, now.tv_nsec); fflush(output);
}"""))
DEBUGGER.append(('            copy.name = strdup(copy.name); copy.path = strdup(copy.path);',
                 '            copy.name = strdup(copy.name); copy.path = strdup(copy.path); copy.aliases = strdup(copy.aliases);'))
DEBUGGER.append(('static int patch(pid_t tid, uintptr_t address, unsigned char byte, unsigned char *old) {', '''/* Context, make-current, swap and draw names: tools/hot_swap/policy.py's tables, copied by
 * tools/hot_swap/derive_linux_observer.py. A name starting with a prefix or equal to a name. */
static const char *const context_prefixes[] = @CONTEXT_PREFIXES@;
static const char *const context_names[] = @CONTEXT_NAMES@;
static const char *const draw_prefixes[] = @DRAW_PREFIXES@;
static const char *const draw_names[] = @DRAW_NAMES@;
static const char *const not_draw_prefixes[] = @NOT_DRAW_PREFIXES@;
static int listed(const char *name, const char *const *list, int prefix) {
    for (; *list; ++list) if (prefix ? !strncmp(name, *list, strlen(*list)) : !strcmp(name, *list)) return 1;
    return 0;
}
static int context_or_draw(const char *name) {
    return listed(name, context_names, 0) || listed(name, context_prefixes, 1) || listed(name, draw_names, 0) ||
           (listed(name, draw_prefixes, 1) && !listed(name, not_draw_prefixes, 1));
}
/* 1 when an export's first instruction is endbr64 (f3 0f 1e fa), 0 when not, -1 on a read error. Moving rip past it
 * steps over the trap that replaced its first byte: without indirect branch tracking, endbr64 has no effect. */
static int leading_endbr64(pid_t tid, uintptr_t address) {
    static const unsigned char endbr64[4] = {0xf3, 0x0f, 0x1e, 0xfa};
    for (size_t n = 0; n < sizeof(endbr64); ++n) {
        uintptr_t aligned = (address + n) & ~(uintptr_t)(sizeof(long) - 1);
        errno = 0; long word = ptrace(PTRACE_PEEKTEXT, tid, (void *)aligned, NULL);
        if (word == -1 && errno) { error(tid, "PTRACE_PEEKTEXT endbr64"); return -1; }
        if ((unsigned char)((unsigned long)word >> ((address + n - aligned) * 8)) != endbr64[n]) return 0;
    }
    return 1;
}
/* Another export name at a trapped address: a call stops when any of its names is a context or draw name. A name
 * listed twice (several symbol versions) is kept once. */
static void add_alias(Trap *trap, const char *name) {
    size_t length = strlen(name);
    for (const char *p = trap->aliases; p && *p;) {
        const char *end = strchr(p, ',');
        size_t size = end ? (size_t)(end - p) : strlen(p);
        if (size == length && !strncmp(p, name, length)) return;
        p += end ? size + 1 : size;
    }
    char *aliases;
    if (asprintf(&aliases, "%s,%s", trap->aliases, name) < 0) {
        ++errors; event("debug_error", trap->owner, "GL export alias allocation: %s", name); return;
    }
    free(trap->aliases); trap->aliases = aliases;
    trap->stop |= context_or_draw(name);
}
static int patch(pid_t tid, uintptr_t address, unsigned char byte, unsigned char *old) {'''
                 .replace('@CONTEXT_PREFIXES@', c_strings(CONTEXT_PREFIXES)).replace('@CONTEXT_NAMES@', c_strings(CONTEXT_NAMES))
                 .replace('@DRAW_PREFIXES@', c_strings(DRAW_PREFIXES)).replace('@DRAW_NAMES@', c_strings(DRAW_NAMES))
                 .replace('@NOT_DRAW_PREFIXES@', c_strings(NOT_DRAW_PREFIXES))))
DEBUGGER.append(('            for (size_t p = 0; p < trap_count; ++p) if (traps[p].live && traps[p].owner == group && traps[p].address == address) exists = 1;',
                 '''            for (size_t p = 0; p < trap_count; ++p) if (traps[p].live && traps[p].owner == group && traps[p].address == address) {
                exists = 1;
                if (!resolver && !traps[p].resolver) add_alias(&traps[p], name);
            }'''))
DEBUGGER.append(('''            unsigned char original;
            if (!patch(tid, address, 0xcc, &original)) continue;''', '''            unsigned char original;
            int endbr = resolver ? 0 : leading_endbr64(tid, address);
            if (endbr < 0 || !patch(tid, address, 0xcc, &original)) continue;'''))
DEBUGGER.append(('            traps[trap_count++] = (Trap){group, address, bias, original, 1, resolver, strdup(name), strdup(path)};',
                 '''            traps[trap_count++] = (Trap){group, address, bias, original, 1, resolver, strdup(name), strdup(path),
                                         !resolver && context_or_draw(name), endbr, strdup(name)};'''))
# Loader records end with wall-clock time (and a load's requester): an image record's value stops at its first tab.
DEBUGGER.append(('        value[strcspn(value, "\\r\\n")] = 0;', '        value[strcspn(value, "\\t\\r\\n")] = 0;'))
DEBUGGER.append(('static int poke_bytes(pid_t tid, uintptr_t address, const void *data, size_t size) {', '''/* The module holding the return address at [rsp]: at an export's first instruction, its caller. An address outside
 * every file-backed mapping (for example generated code) leaves the path empty: an unknown caller. A tail call names
 * the caller's caller. */
static void caller_module(pid_t tid, pid_t group, uintptr_t rsp, char *path, size_t size, uintptr_t *address) {
    unsigned long word; char proc[80], *line = NULL; size_t capacity = 0;
    *path = 0;
    if (!peek_word(tid, rsp, &word)) return;
    *address = (uintptr_t)word;
    snprintf(proc, sizeof(proc), "/proc/%d/maps", (int)tid);
    FILE *stream = fopen(proc, "r");
    if (!stream) { error(group, "open caller maps"); return; }
    while (getline(&line, &capacity, stream) >= 0) {
        unsigned long start, end; int consumed = 0;
        if (sscanf(line, "%lx-%lx %*s %*s %*s %*s %n", &start, &end, &consumed) != 2 || !consumed) {
            ++errors; event("debug_error", group, "Unreadable caller mapping in %s", proc); break;
        }
        if (word < start || word >= end) continue;
        char *name = line + consumed; name[strcspn(name, "\\r\\n")] = 0;
        if (*name == '/') snprintf(path, size, "%s", name);
        break;
    }
    free(line); fclose(stream);
}
static int poke_bytes(pid_t tid, uintptr_t address, const void *data, size_t size) {'''))
DEBUGGER.append(('''                        if (gl_symbol(symbol)) { event("native_gl_binding", group, "%s", symbol); kill_tree(); }
                        else {''', '''                        if (gl_symbol(symbol)) {
                            char caller[8192]; uintptr_t return_address = 0;
                            caller_module(tid, group, registers.rsp, caller, sizeof(caller), &return_address);
                            event("native_gl_binding", group, "%s\\t%s\\t", symbol, caller);
                        }
                        {'''))
DEBUGGER.append(('''                    } else { event("native_gl_call", group, "%s|%s", traps[i].name, traps[i].path); kill_tree(); }''',
                 '''                    } else {
                        char caller[8192]; uintptr_t return_address = 0;
                        caller_module(tid, group, registers.rsp, caller, sizeof(caller), &return_address);
                        event("native_gl_call", group, "%s\\t%s\\t%s\\t%s\\t0x%lx", traps[i].name, traps[i].aliases, traps[i].path,
                              caller, (unsigned long)return_address);
                        if (traps[i].stop) kill_tree();
                        else if (!traps[i].endbr) {
                            ++errors; event("debug_error", group, "GL export does not begin with endbr64, cannot step over: %s|%s",
                                            traps[i].name, traps[i].path);
                        } else {
                            registers.rip = traps[i].address + 4;
                            if (ptrace(PTRACE_SETREGS, tid, NULL, &registers)) error(group, "PTRACE_SETREGS GL step-over");
                        }
                    }'''))
DEBUGGER.append(('    for (size_t i = 0; i < trap_count; ++i) { free(traps[i].name); free(traps[i].path); }',
                 '    for (size_t i = 0; i < trap_count; ++i) { free(traps[i].name); free(traps[i].path); free(traps[i].aliases); }'))

# 3. The Python runner and parser.
OBSERVER.append(('''"""glibc loader evidence, with unsupported process/API coverage explicit."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
''', '''# SPDX-License-Identifier: AGPL-3.0-only
"""Hot-swap observer: Linux x86-64 loads, symbol bindings and GL calls, with callers.

Derived by tools/hot_swap/derive_linux_observer.py from tools/no_opengl/linux.py
(sha256 {origin}), which stays unchanged for the strict profile. It runs the derived
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
    parts = line.split('\\t')
    if len(parts) < 4 or not parts[1].isdigit():
        return None
    kind, values = parts[0], parts[2:-1]
    try:
        wall = float(parts[-1])
    except ValueError:
        return None
    if not math.isfinite(wall) or wall <= 0 or len(values) != fields.get(kind, 1):
        return None
    row = {'kind': kind, 'pid': int(parts[1]), 'wall': wall, 'detail': '\\t'.join(values)}
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
'''))
OBSERVER.append(('''    for line in trace_path.read_text().splitlines() if trace_path.exists() else []:
        fields = line.split('\\t', 2)
        if len(fields) != 3 or not fields[1].isdigit():
            errors.append({'error': 'Malformed native trace line', 'line': line})
            continue
        kind, pid, value = fields
        events.append({'kind': kind, 'pid': int(pid),
                       'name' if kind == 'native_gl_binding' else 'path': value})''',
                 '''    for line in trace_path.read_text(encoding='utf-8', errors='replace').splitlines() if trace_path.exists() else []:
        row = record(line, LOADER_FIELDS)
        if row is None:
            errors.append({'error': 'Malformed native trace line', 'line': line})
            continue
        kind, pid, value = row['kind'], row['pid'], row['detail']
        events.append(row)'''))
OBSERVER.append(('''                'native_entrypoint_resolution': False, 'process_tree': False}''',
                 '''                'native_entrypoint_resolution': False, 'process_tree': False,
                'private_or_statically_linked_gl_implementations': False}'''))
OBSERVER.append(('''        for line in debugger_path.read_text().splitlines() if debugger_path.exists() else []:
            fields = line.split('\\t', 2)
            if len(fields) != 3 or not fields[1].isdigit():
                errors.append({'error': 'Malformed debugger trace', 'line': line})
                continue
            kind, pid, value = fields
            pid = int(pid)
            row = {'kind': kind, 'pid': pid, 'detail': value}
            if kind == 'native_gl_call':
                row['name'], _, row['path'] = value.partition('|')
            elif kind == 'native_gl_binding':
                row['name'] = value
            elif kind in ('native_load', 'native_unload'):
                row['path'] = value''', '''        for line in debugger_path.read_text(encoding='utf-8', errors='replace').splitlines() if debugger_path.exists() else []:
            row = record(line, DEBUGGER_FIELDS, ('native_load', 'native_unload'))
            if row is None:
                errors.append({'error': 'Malformed debugger trace', 'line': line})
                continue
            kind, pid, value = row['kind'], row['pid'], row['detail']'''))
OBSERVER.append(('''                      'ELF public GL-export call traps and glibc symbol bindings including dlsym; \'''',
                 '''                      'ELF public GL-export call traps: context, make-current, swap and draw calls stop the '
                      'tree, other calls are recorded with their caller and stepped over past a leading endbr64; '
                      'glibc symbol bindings including dlsym, with their referencing object; loads with the '
                      'object that requested them; \''''))


def derive(source, replacements):
    """The derived text for a strict source's bytes."""
    data, origin = source.decode('utf-8'), hashlib.sha256(source).hexdigest()
    for old, new in replacements:
        assert data.count(old) == 1, old[:80]
        data = data.replace(old, new.replace('{origin}', origin))
    return data.encode('utf-8')


def derive_auditor(source):
    return derive(source, AUDITOR)


def derive_debugger(source):
    return derive(source, DEBUGGER)


def derive_observer(source):
    return derive(source, OBSERVER)


# (strict source, derived file, derivation)
FILES = ((STRICT / 'loader_audit_linux.c', DERIVED / 'loader_audit_linux.c', derive_auditor),
         (STRICT / 'debugger_linux.c', DERIVED / 'debugger_linux.c', derive_debugger),
         (STRICT / 'linux.py', DERIVED / 'linux_observer.py', derive_observer))


if __name__ == '__main__':
    for strict, derived, derivation in FILES:
        derived.write_bytes(derivation(strict.read_bytes()))
        print('derived', derived.relative_to(ROOT).as_posix(), 'from', strict.relative_to(ROOT).as_posix(),
              hashlib.sha256(strict.read_bytes()).hexdigest())
