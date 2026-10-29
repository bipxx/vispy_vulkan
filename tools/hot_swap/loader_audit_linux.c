/* SPDX-License-Identifier: AGPL-3.0-only
 * Hot-swap loader audit module: glibc LD_AUDIT loads, unloads and GL bindings, with callers.
 * Derived by tools/hot_swap/derive_linux_observer.py from tools/no_opengl/loader_audit_linux.c
 * (sha256 ab045f08942d3b303f99506f4e0e2e0e75779f5a4b623e4781a63a515b82154e), which stays unchanged for the strict profile.
 * Differences: every record ends with wall-clock time; a load records the object that requested
 * it (la_objsearch, LA_SER_ORIG); a GL binding records its referencing and defining objects.
 * Build: cc -shared -fPIC -O2 -o loader_audit.so loader_audit_linux.c
 */
#define _GNU_SOURCE
#include <link.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <signal.h>
#include <time.h>

static int trace_fd = -1;
static int trace_failed = 0;
static int debugger_handshake = 0;
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

static void emit_image(const char *kind, struct link_map *map);

static void emit_fields(const char *kind, const char *const *values, size_t count) {
    char line[8192];
    size_t length = 0;
    char pid[32];
    size_t digits = 0;
    unsigned long number = (unsigned long)getpid();
    do { pid[digits++] = (char)('0' + number % 10); number /= 10; } while (number);
    for (size_t i = 0; i < digits / 2; ++i) {
        char swap = pid[i]; pid[i] = pid[digits - i - 1]; pid[digits - i - 1] = swap;
    }
    pid[digits] = 0;
    /* kind, pid, the values and wall-clock time, tab-separated; a field's own tabs and line breaks become '?'.
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
            if (length < sizeof(line) - 1) line[length++] = '\t'; else trace_failed = 1;
        }
        for (const char *p = parts[part]; *p; ++p) {
            if (length >= sizeof(line) - 1) { trace_failed = 1; break; }
            line[length++] = (*p == '\n' || *p == '\r' || *p == '\t') ? '?' : *p;
        }
    }
    line[length++] = '\n';
    if (trace_fd >= 0) {
        ssize_t written = write(trace_fd, line, length);
        if (written < 0 || (size_t)written != length) trace_failed = 1;
    }
}

static void emit(const char *kind, const char *value) {
    emit_fields(kind, &value, 1);
}

unsigned int la_version(unsigned int version) {
    const char *path = getenv("VISPY_NO_GL_NATIVE_LOG");
    const char *handshake = getenv("VISPY_NO_GL_PTRACE_HANDSHAKE");
    debugger_handshake = handshake && strcmp(handshake, "1") == 0;
    ssize_t main_length = readlink("/proc/self/exe", main_path, sizeof(main_path) - 1);
    main_path[main_length > 0 ? main_length : 0] = 0;
    if (path && *path) trace_fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    emit("audit_start", "glibc LD_AUDIT");
    return version < LAV_CURRENT ? version : LAV_CURRENT;
}

/* An object's path from its audit cookie (its link map); the main program's empty name is its executable. */
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

unsigned int la_objopen(struct link_map *map, Lmid_t namespace_id, uintptr_t *cookie) {
    (void)namespace_id;
    *cookie = (uintptr_t)map;
    const char *load[2] = {map->l_name, requester(map)};
    emit_fields("native_load", load, 2);
    if (debugger_handshake) {
        emit_image("native_image", map);
        if (kill(getpid(), SIGSTOP) != 0) trace_failed = 1;
    }
    return LA_FLG_BINDTO | LA_FLG_BINDFROM;
}

unsigned int la_objclose(uintptr_t *cookie) {
    struct link_map *map = (struct link_map *)*cookie;
    emit("native_unload", map ? map->l_name : "");
    if (debugger_handshake && map) {
        emit_image("native_image_unload", map);
        if (kill(getpid(), SIGSTOP) != 0) trace_failed = 1;
    }
    return 0;
}

static void emit_image(const char *kind, struct link_map *map) {
    char value[8192], reverse[2 * sizeof(uintptr_t)];
    size_t used = 0, digits = 0;
    uintptr_t address = (uintptr_t)map->l_addr;
    do {
        reverse[digits++] = "0123456789abcdef"[address & 15];
        address >>= 4;
    } while (address);
    value[used++] = '0'; value[used++] = 'x';
    while (digits) value[used++] = reverse[--digits];
    value[used++] = '|';
    for (const char *p = map->l_name; *p && used < sizeof(value) - 1; ++p) value[used++] = *p;
    value[used] = 0;
    emit(kind, value);
}

__attribute__((destructor)) static void finish(void) {
    emit(trace_failed ? "audit_error" : "audit_exit", trace_failed ? "incomplete trace write" : "normal loader shutdown");
    if (trace_fd >= 0) close(trace_fd);
}

static int gl_symbol(const char *name) {
    return (name[0] == 'g' && name[1] == 'l' && name[2] >= 'A' && name[2] <= 'Z') ||
           (strncmp(name, "glX", 3) == 0 && name[3] >= 'A' && name[3] <= 'Z') ||
           (strncmp(name, "egl", 3) == 0 && name[3] >= 'A' && name[3] <= 'Z') ||
           (strncmp(name, "wgl", 3) == 0 && name[3] >= 'A' && name[3] <= 'Z') ||
           strncmp(name, "OSMesa", 6) == 0;
}

uintptr_t la_symbind64(Elf64_Sym *symbol, unsigned int index, uintptr_t *reference,
                     uintptr_t *definition, unsigned int *flags, const char *name) {
    (void)index; (void)flags;
    if (gl_symbol(name)) {
        const char *binding[3] = {name, object_path(*reference), object_path(*definition)};
        emit_fields("native_gl_binding", binding, 3);
    }
    return symbol->st_value;
}
