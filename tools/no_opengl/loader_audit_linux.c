/* SPDX-License-Identifier: AGPL-3.0-only
 * glibc runtime-linker audit module. Logs loader events before Python starts,
 * including transient dlopen/dlclose and externally bound GL entry points.
 * Build: cc -shared -fPIC -O2 -o loader_audit.so loader_audit_linux.c
 */
#define _GNU_SOURCE
#include <link.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>

static int trace_fd = -1;
static int trace_failed = 0;

static void emit(const char *kind, const char *value) {
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
    const char *parts[5] = {kind, "\t", pid, "\t", value ? value : ""};
    for (int part = 0; part < 5; ++part)
        for (const char *p = parts[part]; *p && length < sizeof(line) - 2; ++p)
            line[length++] = (*p == '\n' || *p == '\r' || (*p == '\t' && part != 1 && part != 3)) ? '?' : *p;
    line[length++] = '\n';
    if (trace_fd >= 0) {
        ssize_t written = write(trace_fd, line, length);
        if (written < 0 || (size_t)written != length) trace_failed = 1;
    }
}

unsigned int la_version(unsigned int version) {
    const char *path = getenv("VISPY_NO_GL_NATIVE_LOG");
    if (path && *path) trace_fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    emit("audit_start", "glibc LD_AUDIT");
    return version < LAV_CURRENT ? version : LAV_CURRENT;
}

unsigned int la_objopen(struct link_map *map, Lmid_t namespace_id, uintptr_t *cookie) {
    (void)namespace_id;
    *cookie = (uintptr_t)map;
    emit("native_load", map->l_name);
    return LA_FLG_BINDTO | LA_FLG_BINDFROM;
}

unsigned int la_objclose(uintptr_t *cookie) {
    struct link_map *map = (struct link_map *)*cookie;
    emit("native_unload", map ? map->l_name : "");
    return 0;
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
    (void)index; (void)reference; (void)definition; (void)flags;
    if (gl_symbol(name)) emit("native_gl_binding", name);
    return symbol->st_value;
}
