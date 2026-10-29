/* SPDX-License-Identifier: AGPL-3.0-only
 * Hot-swap observer: Linux x86-64 ptrace process tree and public GL-export calls, with callers.
 * Derived by tools/hot_swap/derive_linux_observer.py from tools/no_opengl/debugger_linux.c
 * (sha256 3de2b562eb75c254a4034c278cdec752588cec44cc725fc1100ff3c33791c857), which stays unchanged for the strict profile.
 * Differences: a GL call records its caller, the module holding the return address at [rsp].
 * Context, make-current, swap and draw calls (tools/hot_swap/policy.py), under any of the
 * export's names, are recorded and stop the tree before executing. Other calls are recorded and
 * stepped over past the export's leading endbr64 with the trap kept armed; an export without one
 * fails closed. A static process's GL lookup is recorded and single-stepped like other lookups.
 * Every record ends with wall-clock time; the loader's records carry it as their last field.
 */
#define _GNU_SOURCE
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/user.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error This observer requires Linux x86-64
#endif

typedef struct { pid_t tid, owner; int live, static_exec; uintptr_t stepping; } Task;
typedef struct { pid_t owner; uintptr_t address, bias; unsigned char original; int live, resolver; char *name, *path; int stop, endbr; char *aliases; } Trap;
typedef struct { pid_t owner; uintptr_t bias; int unload, done; char *path; } Image;
static Task *tasks;
static Trap *traps;
static Image *images;
static size_t task_count, trap_count;
static size_t image_count;
static FILE *output, *loader;
static int errors, terminated, root_code = 125;
static const char *auditor_path, *loader_path;

static void event(const char *kind, pid_t pid, const char *format, ...) {
    fprintf(output, "%s\t%d\t", kind, (int)pid);
    va_list args; va_start(args, format); vfprintf(output, format, args); va_end(args);
    struct timespec now;
    if (clock_gettime(CLOCK_REALTIME, &now)) { now.tv_sec = 0; now.tv_nsec = 0; }
    fprintf(output, "\t%lld.%09ld\n", (long long)now.tv_sec, now.tv_nsec); fflush(output);
}
static void error(pid_t pid, const char *operation) {
    ++errors; event("debug_error", pid, "%s: %s", operation, strerror(errno));
}
static void *grow(void *old, size_t count, size_t size) {
    void *value = realloc(old, count * size);
    if (!value) { perror("realloc"); exit(125); }
    return value;
}
static pid_t owner(pid_t tid) {
    char path[80], line[256]; snprintf(path, sizeof(path), "/proc/%d/status", (int)tid);
    FILE *stream = fopen(path, "r");
    if (stream) {
        while (fgets(line, sizeof(line), stream)) {
            int value;
            if (sscanf(line, "Tgid: %d", &value) == 1) { fclose(stream); return value; }
        }
        fclose(stream);
    }
    error(tid, "read task Tgid"); return tid;
}
static Task *task(pid_t tid) {
    for (size_t i = task_count; i; --i) if (tasks[i - 1].tid == tid && tasks[i - 1].live) return &tasks[i - 1];
    return NULL;
}
static void add_task(pid_t tid, pid_t parent) {
    if (task(tid)) return;
    pid_t group = owner(tid);
    tasks = grow(tasks, task_count + 1, sizeof(*tasks));
    Task *parent_state = task(parent);
    int static_exec = parent_state ? parent_state->static_exec : 0;
    tasks[task_count++] = (Task){tid, group, 1, static_exec, 0};
    event("debug_task_start", group, "tid=%d parent_tid=%d", (int)tid, (int)parent);
    Task *parent_task = task(parent);
    if (parent_task && parent_task->owner != group) {
        size_t count = trap_count;
        for (size_t i = 0; i < count; ++i) if (traps[i].live && traps[i].owner == parent_task->owner) {
            Trap copy = traps[i]; copy.owner = group;
            copy.name = strdup(copy.name); copy.path = strdup(copy.path); copy.aliases = strdup(copy.aliases);
            traps = grow(traps, trap_count + 1, sizeof(*traps)); traps[trap_count++] = copy;
        }
    }
}
static int gl_symbol(const char *name) {
    return (name[0] == 'g' && name[1] == 'l' && name[2] >= 'A' && name[2] <= 'Z') ||
           (strncmp(name, "glX", 3) == 0 && name[3] >= 'A' && name[3] <= 'Z') ||
           (strncmp(name, "egl", 3) == 0 && name[3] >= 'A' && name[3] <= 'Z') ||
           (strncmp(name, "wgl", 3) == 0 && name[3] >= 'A' && name[3] <= 'Z') ||
           (strncmp(name, "OSMesa", 6) == 0 && name[6] >= 'A' && name[6] <= 'Z');
}
/* Context, make-current, swap and draw names: tools/hot_swap/policy.py's tables, copied by
 * tools/hot_swap/derive_linux_observer.py. A name starting with a prefix or equal to a name. */
static const char *const context_prefixes[] = {"wglCreate", "wglMake", "wglSwap", "wglShare", "wglCopy", "wglDelete", "eglCreate", "eglMakeCurrent", "eglSwap", "glXCreate", "glXMakeCurrent", "glXMakeContextCurrent", "glXSwap", "OSMesaCreate", "OSMesaMakeCurrent", NULL};
static const char *const context_names[] = {"SwapBuffers", NULL};
static const char *const draw_prefixes[] = {"glDraw", "glMultiDraw", "glClearBuffer", "glClearNamedFramebuffer", "glClearTex", "glDispatch", "glBlit", "glRect", "glEvalMesh", "glEvalPoint", NULL};
static const char *const draw_names[] = {"glClear", "glBegin", "glCallList", "glCallLists", "glAccum", "glBitmap", "glCopyPixels", "glArrayElement", NULL};
static const char *const not_draw_prefixes[] = {"glDrawBuffer", NULL};
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
static int patch(pid_t tid, uintptr_t address, unsigned char byte, unsigned char *old) {
    uintptr_t aligned = address & ~(uintptr_t)(sizeof(long) - 1);
    unsigned int shift = (unsigned int)((address - aligned) * 8);
    errno = 0; long word = ptrace(PTRACE_PEEKTEXT, tid, (void *)aligned, NULL);
    if (word == -1 && errno) { error(tid, "PTRACE_PEEKTEXT"); return 0; }
    if (old) *old = (unsigned char)((unsigned long)word >> shift);
    unsigned long changed = ((unsigned long)word & ~(0xffUL << shift)) | ((unsigned long)byte << shift);
    if (ptrace(PTRACE_POKETEXT, tid, (void *)aligned, (void *)changed) < 0) { error(tid, "PTRACE_POKETEXT"); return 0; }
    return 1;
}
static int range(size_t size, uint64_t offset, uint64_t length) {
    return offset <= size && length <= size - offset;
}
static void image(pid_t tid, pid_t group, uintptr_t bias, const char *requested, int unload, int static_main) {
    char executable[80]; const char *path = requested;
    if (!*path) { snprintf(executable, sizeof(executable), "/proc/%d/exe", (int)tid); path = executable; }
    if (strcmp(path, "linux-vdso.so.1") == 0) return; /* Kernel supplied, no GL exports. */
    if (unload) {
        for (size_t i = 0; i < trap_count; ++i) if (traps[i].live && traps[i].owner == group && traps[i].bias == bias &&
                                                  strcmp(traps[i].path, path) == 0) {
            patch(tid, traps[i].address, traps[i].original, NULL); traps[i].live = 0;
        }
        return;
    }
    int fd = open(path, O_RDONLY | O_CLOEXEC); struct stat status;
    if (fd < 0) { error(group, "open loaded ELF image"); return; }
    if (fstat(fd, &status) || status.st_size < (off_t)sizeof(Elf64_Ehdr)) { error(group, "stat loaded ELF image"); close(fd); return; }
    size_t size = (size_t)status.st_size;
    const unsigned char *data = mmap(NULL, size, PROT_READ, MAP_PRIVATE, fd, 0); close(fd);
    if (data == MAP_FAILED) { error(group, "mmap loaded ELF image"); return; }
    const Elf64_Ehdr *header = (const Elf64_Ehdr *)data;
    if (memcmp(header->e_ident, ELFMAG, SELFMAG) || header->e_ident[EI_CLASS] != ELFCLASS64 ||
        header->e_ident[EI_DATA] != ELFDATA2LSB || header->e_machine != EM_X86_64 ||
        header->e_shentsize != sizeof(Elf64_Shdr) || !header->e_shnum ||
        !range(size, header->e_shoff, (uint64_t)header->e_shnum * sizeof(Elf64_Shdr))) {
        ++errors; event("debug_error", group, "Unsupported ELF image: %s", path); munmap((void *)data, size); return;
    }
    const Elf64_Shdr *sections = (const Elf64_Shdr *)(data + header->e_shoff);
    int tables = 0;
    for (unsigned int i = 0; i < header->e_shnum; ++i) if (sections[i].sh_type == SHT_DYNSYM || (static_main && sections[i].sh_type == SHT_SYMTAB)) {
        ++tables;
        const Elf64_Shdr *symbols = &sections[i];
        if (symbols->sh_entsize != sizeof(Elf64_Sym) || symbols->sh_link >= header->e_shnum ||
            !range(size, symbols->sh_offset, symbols->sh_size)) { ++errors; continue; }
        const Elf64_Shdr *strings = &sections[symbols->sh_link];
        if (!range(size, strings->sh_offset, strings->sh_size)) { ++errors; continue; }
        const Elf64_Sym *entries = (const Elf64_Sym *)(data + symbols->sh_offset);
        for (size_t n = 0; n < symbols->sh_size / sizeof(Elf64_Sym); ++n) {
            const Elf64_Sym *symbol = &entries[n];
            if (symbol->st_shndx == SHN_UNDEF || symbol->st_name >= strings->sh_size) continue;
            const char *name = (const char *)data + strings->sh_offset + symbol->st_name;
            if (!memchr(name, 0, strings->sh_size - symbol->st_name)) { ++errors; continue; }
            int resolver = static_main && (!strcmp(name, "dlsym") || !strcmp(name, "dlvsym") || !strcmp(name, "__dlsym") || !strcmp(name, "__dlvsym"));
            if (!gl_symbol(name) && !resolver) continue;
            unsigned int type = ELF64_ST_TYPE(symbol->st_info);
            if (type != STT_FUNC) { ++errors; event("debug_error", group, "Unsupported GL export type: %s (%u)", name, type); continue; }
            uintptr_t address = bias + symbol->st_value;
            int exists = 0;
            for (size_t p = 0; p < trap_count; ++p) if (traps[p].live && traps[p].owner == group && traps[p].address == address) {
                exists = 1;
                if (!resolver && !traps[p].resolver) add_alias(&traps[p], name);
            }
            if (exists) continue;
            unsigned char original;
            int endbr = resolver ? 0 : leading_endbr64(tid, address);
            if (endbr < 0 || !patch(tid, address, 0xcc, &original)) continue;
            if (original == 0xcc) { ++errors; event("debug_error", group, "GL export already contains trap: %s", name); continue; }
            traps = grow(traps, trap_count + 1, sizeof(*traps));
            traps[trap_count++] = (Trap){group, address, bias, original, 1, resolver, strdup(name), strdup(path),
                                         !resolver && context_or_draw(name), endbr, strdup(name)};
            event("debug_export_trap", group, "%s|%s", name, path);
        }
    }
    if (!tables) {
        if (static_main) event("debug_static_no_public_exports", group, "%s", path);
        else { ++errors; event("debug_error", group, "No dynamic symbol table: %s", path); }
    }
    munmap((void *)data, size);
}
static int loader_events(pid_t tid, pid_t group) {
    /* Queue interleaved process records; each address space is instrumented
     * only while a task in that address space is at its loader stop. */
    char *line = NULL; size_t capacity = 0;
    int complete = 1;
    clearerr(loader);
    for (;;) {
        off_t start = ftello(loader);
        if (start < 0) { error(group, "tell loader record"); break; }
        ssize_t length = getline(&line, &capacity, loader);
        if (length < 0) {
            if (ferror(loader)) error(group, "read loader record");
            break;
        }
        /* Another address space can still be appending this record. getline
         * returns an unterminated prefix at temporary EOF; retain every byte
         * until a complete line is available at a later loader stop. */
        if (!length || line[length - 1] != '\n') {
            complete = 0;
            if (fseeko(loader, start, SEEK_SET)) error(group, "rewind incomplete loader record");
            event("debug_loader_record_deferred", group, "offset=%lld bytes=%zd", (long long)start, length);
            break;
        }
        char *kind = line, *pid = strchr(line, '\t');
        if (!pid) { ++errors; event("debug_error", group, "Loader record lacks PID at offset=%lld", (long long)start); continue; } *pid++ = 0;
        char *value = strchr(pid, '\t');
        if (!value) { ++errors; event("debug_error", group, "Loader record lacks value at offset=%lld", (long long)start); continue; } *value++ = 0;
        value[strcspn(value, "\t\r\n")] = 0;
        if (strcmp(kind, "native_image") && strcmp(kind, "native_image_unload")) continue;
        pid_t source = (pid_t)strtol(pid, NULL, 10);
        char *end; uintptr_t bias = (uintptr_t)strtoull(value, &end, 16);
        if (*end != '|') { ++errors; event("debug_error", group, "Loader image lacks separator at offset=%lld", (long long)start); continue; }
        images = grow(images, image_count + 1, sizeof(*images));
        images[image_count++] = (Image){source, bias, strcmp(kind, "native_image_unload") == 0, 0, strdup(end + 1)};
    }
    free(line);
    for (size_t i = 0; i < image_count; ++i) if (!images[i].done && images[i].owner == group) {
        image(tid, group, images[i].bias, images[i].path, images[i].unload, 0); images[i].done = 1;
    }
    return complete;
}
static void finish_loader_events(pid_t root) {
    if (!loader_events(root, root)) {
        ++errors; event("debug_error", root, "Unterminated loader record after process tree exit");
    }
}
static int peek_word(pid_t tid, uintptr_t address, unsigned long *word) {
    errno = 0; long value = ptrace(PTRACE_PEEKDATA, tid, (void *)address, NULL);
    if (value == -1 && errno) { error(tid, "PTRACE_PEEKDATA stack"); return 0; }
    *word = (unsigned long)value; return 1;
}
/* The module holding the return address at [rsp]: at an export's first instruction, its caller. An address outside
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
        char *name = line + consumed; name[strcspn(name, "\r\n")] = 0;
        if (*name == '/') snprintf(path, size, "%s", name);
        break;
    }
    free(line); fclose(stream);
}
static int poke_bytes(pid_t tid, uintptr_t address, const void *data, size_t size) {
    for (size_t offset = 0; offset < size; offset += sizeof(long)) {
        unsigned long word = 0;
        size_t length = size - offset < sizeof(long) ? size - offset : sizeof(long);
        memcpy(&word, (const char *)data + offset, length);
        if (ptrace(PTRACE_POKEDATA, tid, (void *)(address + offset), (void *)word)) { error(tid, "PTRACE_POKEDATA stack"); return 0; }
    }
    return 1;
}
static int read_remote_string(pid_t tid, uintptr_t address, char *text, size_t size) {
    for (size_t offset = 0; offset < size; offset += sizeof(long)) {
        unsigned long word;
        if (!peek_word(tid, address + offset, &word)) return 0;
        for (size_t n = 0; n < sizeof(long) && offset + n < size; ++n) {
            text[offset + n] = (char)(word >> (8 * n));
            if (!text[offset + n]) return 1;
        }
    }
    ++errors; event("debug_error", tid, "Environment string exceeds limit"); return 0;
}
static void restore_auditor_environment(pid_t tid) {
    struct user_regs_struct registers;
    if (ptrace(PTRACE_GETREGS, tid, NULL, &registers)) { error(tid, "PTRACE_GETREGS exec stack"); return; }
    unsigned long words[32768], rebuilt[32768]; size_t count = 0;
    if (!peek_word(tid, registers.rsp, &words[0]) || words[0] > 16384) { ++errors; return; }
    size_t env_start = (size_t)words[0] + 2, env_end = env_start;
    for (size_t i = 1; i < env_start; ++i) if (!peek_word(tid, registers.rsp + i * 8, &words[i])) return;
    for (;;) {
        if (env_end >= 32000 || !peek_word(tid, registers.rsp + env_end * 8, &words[env_end])) { ++errors; return; }
        if (!words[env_end++]) break;
    }
    count = env_end;
    for (;;) {
        if (count + 2 >= 32768 || !peek_word(tid, registers.rsp + count * 8, &words[count]) ||
            !peek_word(tid, registers.rsp + (count + 1) * 8, &words[count + 1])) { ++errors; return; }
        count += 2; if (words[count - 2] == AT_NULL) break;
    }
    if (count + 4 >= 32768) { ++errors; event("debug_error", tid, "Exec environment exceeds collector limit"); return; }
    char *settings[4];
    if (asprintf(&settings[0], "LD_AUDIT=%s", auditor_path) < 0 ||
        asprintf(&settings[1], "VISPY_NO_GL_NATIVE_LOG=%s", loader_path) < 0) { ++errors; return; }
    settings[2] = strdup("LD_BIND_NOW=1"); settings[3] = strdup("VISPY_NO_GL_PTRACE_HANDSHAKE=1");
    uintptr_t string_top = registers.rsp - 64; unsigned long pointers[4];
    for (size_t i = 0; i < 4; ++i) {
        size_t length = strlen(settings[i]) + 1;
        string_top = (string_top - length) & ~(uintptr_t)7;
        pointers[i] = string_top;
        if (!poke_bytes(tid, string_top, settings[i], length)) { for (size_t n = 0; n < 4; ++n) free(settings[n]); return; }
    }
    size_t used = env_start; memcpy(rebuilt, words, env_start * 8);
    for (size_t i = env_start; i + 1 < env_end; ++i) {
        char text[32768];
        if (!read_remote_string(tid, words[i], text, sizeof(text))) return;
        if (!strncmp(text, "LD_AUDIT=", 9) || !strncmp(text, "LD_BIND_NOW=", 12) ||
            !strncmp(text, "VISPY_NO_GL_NATIVE_LOG=", 23) || !strncmp(text, "VISPY_NO_GL_PTRACE_HANDSHAKE=", 29)) continue;
        rebuilt[used++] = words[i];
    }
    for (size_t i = 0; i < 4; ++i) { rebuilt[used++] = pointers[i]; free(settings[i]); }
    rebuilt[used++] = 0;
    memcpy(rebuilt + used, words + env_end, (count - env_end) * 8); used += count - env_end;
    uintptr_t new_stack = (string_top - used * 8) & ~(uintptr_t)15;
    if (!poke_bytes(tid, new_stack, rebuilt, used * 8)) return;
    registers.rsp = new_stack;
    if (ptrace(PTRACE_SETREGS, tid, NULL, &registers)) error(tid, "PTRACE_SETREGS exec stack");
    else event("debug_auditor_environment_restored", tid, "initial stack collector variables; application environment preserved");
}
typedef struct { pid_t owner; uintptr_t bias; int live, seen; char *path; } Mapping;
static Mapping *mapped;
static size_t mapped_count;
static void static_mappings(pid_t tid, pid_t group, const char *main_path) {
    char proc[80], *line = NULL; size_t capacity = 0;
    snprintf(proc, sizeof(proc), "/proc/%d/maps", (int)tid);
    FILE *stream = fopen(proc, "r"); if (!stream) { error(group, "open static process maps"); return; }
    for (size_t i = 0; i < mapped_count; ++i) if (mapped[i].owner == group) mapped[i].seen = 0;
    while (getline(&line, &capacity, stream) >= 0) {
        unsigned long start, end, offset; char permissions[8]; int consumed = 0;
        if (sscanf(line, "%lx-%lx %7s %lx %*s %*s %n", &start, &end, permissions, &offset, &consumed) != 4) { ++errors; continue; }
        if (!strchr(permissions, 'x')) continue;
        char *path = line + consumed; while (*path == ' ') ++path; path[strcspn(path, "\r\n")] = 0;
        if (*path != '/') continue; /* vdso/vsyscall are kernel supplied. */
        uintptr_t bias = start - offset;
        int found = 0;
        for (size_t i = 0; i < mapped_count; ++i) if (mapped[i].live && mapped[i].owner == group && !strcmp(mapped[i].path, path)) {
            mapped[i].seen = 1; found = 1; break;
        }
        if (found) continue;
        int fd = open(path, O_RDONLY | O_CLOEXEC); Elf64_Ehdr header;
        if (fd < 0 || read(fd, &header, sizeof(header)) != sizeof(header)) { if (fd >= 0) close(fd); error(group, "read static executable mapping"); continue; }
        close(fd);
        if (header.e_type == ET_EXEC) bias = 0;
        if (strcmp(path, main_path)) {
            int resolver = 0;
            for (size_t i = 0; i < trap_count; ++i) if (traps[i].owner == group && traps[i].live && traps[i].resolver) resolver = 1;
            if (!resolver) { ++errors; event("debug_error", group, "Static process mapped DSO without observable symbol resolver: %s", path); }
        }
        image(tid, group, bias, path, 0, !strcmp(path, main_path));
        mapped = grow(mapped, mapped_count + 1, sizeof(*mapped));
        mapped[mapped_count++] = (Mapping){group, bias, 1, 1, strdup(path)};
        event("native_load", group, "%s", path);
    }
    free(line); fclose(stream);
    for (size_t i = 0; i < mapped_count; ++i) if (mapped[i].live && mapped[i].owner == group && !mapped[i].seen) {
        mapped[i].live = 0; event("native_unload", group, "%s", mapped[i].path);
        for (size_t n = 0; n < trap_count; ++n) if (traps[n].owner == group && traps[n].bias == mapped[i].bias) traps[n].live = 0;
    }
}
static int exec_image(pid_t tid, pid_t group) {
    char proc[80], path[8192], interpreter[8192] = "";
    snprintf(proc, sizeof(proc), "/proc/%d/exe", (int)tid);
    ssize_t length = readlink(proc, path, sizeof(path) - 1);
    if (length < 0) { error(group, "read exec image path"); return 0; } path[length] = 0;
    int fd = open(proc, O_RDONLY | O_CLOEXEC); Elf64_Ehdr header;
    if (fd < 0 || read(fd, &header, sizeof(header)) != sizeof(header)) { if (fd >= 0) close(fd); error(group, "read exec ELF"); return 0; }
    if (memcmp(header.e_ident, ELFMAG, SELFMAG) || header.e_ident[EI_CLASS] != ELFCLASS64 || header.e_machine != EM_X86_64) {
        close(fd); ++errors; event("debug_error", group, "Unsupported exec ELF: %s", path); return 0;
    }
    for (unsigned int i = 0; i < header.e_phnum; ++i) {
        Elf64_Phdr program;
        if (pread(fd, &program, sizeof(program), (off_t)(header.e_phoff + i * header.e_phentsize)) != sizeof(program)) { ++errors; break; }
        if (program.p_type == PT_INTERP) {
            if (program.p_filesz > sizeof(interpreter) || pread(fd, interpreter, program.p_filesz, (off_t)program.p_offset) != (ssize_t)program.p_filesz) ++errors;
        }
    }
    close(fd);
    event("debug_exec", group, "%s|%s", path, interpreter);
    if (*interpreter) { restore_auditor_environment(tid); return 0; }
    event("debug_static_exec", group, "%s", path);
    static_mappings(tid, group, path);
    return 1;
}
static void kill_tree(void) {
    terminated = 1;
    for (size_t i = 0; i < task_count; ++i) if (tasks[i].live) kill(tasks[i].tid, SIGKILL);
}
int main(int argc, char **argv) {
    if (argc < 5 || strcmp(argv[3], "--")) { fprintf(stderr, "usage: debugger_linux DEBUG_LOG LOADER_LOG -- COMMAND [ARGS...]\n"); return 125; }
    output = fopen(argv[1], "wx"); loader = fopen(argv[2], "a+");
    if (!output || !loader) { perror("fresh observer logs"); return 125; }
    rewind(loader);
    auditor_path = getenv("VISPY_NO_GL_AUDITOR"); loader_path = getenv("VISPY_NO_GL_NATIVE_LOG");
    if (!auditor_path || !loader_path) { fprintf(stderr, "Collector environment is required\n"); return 125; }
    pid_t root = fork();
    if (root < 0) { perror("fork"); return 125; }
    if (!root) {
        fclose(output); fclose(loader);
        const char *auditor = getenv("VISPY_NO_GL_AUDITOR");
        if (!auditor || !*auditor || setenv("LD_AUDIT", auditor, 1) ||
            setenv("LD_BIND_NOW", "1", 1) || setenv("VISPY_NO_GL_PTRACE_HANDSHAKE", "1", 1)) _exit(125);
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL)) _exit(125);
        raise(SIGSTOP); execvp(argv[4], argv + 4); perror("execvp"); _exit(125);
    }
    int status; if (waitpid(root, &status, 0) != root || !WIFSTOPPED(status)) return 125;
    add_task(root, 0);
    long options = PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE | PTRACE_O_TRACEEXEC | PTRACE_O_TRACEEXIT | PTRACE_O_EXITKILL | PTRACE_O_TRACESYSGOOD;
    if (ptrace(PTRACE_SETOPTIONS, root, NULL, (void *)options)) { error(root, "PTRACE_SETOPTIONS"); kill_tree(); }
    ptrace(PTRACE_CONT, root, NULL, NULL);
    for (;;) {
        pid_t tid = waitpid(-1, &status, __WALL);
        if (tid < 0) { if (errno == EINTR) continue; if (errno != ECHILD) error(root, "waitpid"); break; }
        Task *current = task(tid);
        if (!current) { add_task(tid, 0); current = task(tid); }
        pid_t group = current->owner;
        if (WIFEXITED(status) || WIFSIGNALED(status)) {
            int code = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
            event("debug_task_exit", group, "tid=%d code=%d", (int)tid, code); current->live = 0;
            if (tid == root) root_code = code;
            continue;
        }
        if (!WIFSTOPPED(status)) continue;
        int signal = WSTOPSIG(status), deliver = 0; unsigned int code = (unsigned int)status >> 16;
        if (terminated) { ptrace(PTRACE_CONT, tid, NULL, NULL); continue; }
        if (signal == SIGTRAP && code) {
            if (code == PTRACE_EVENT_FORK || code == PTRACE_EVENT_VFORK || code == PTRACE_EVENT_CLONE) {
                unsigned long child;
                if (ptrace(PTRACE_GETEVENTMSG, tid, NULL, &child)) error(group, "PTRACE_GETEVENTMSG");
                else add_task((pid_t)child, tid);
            } else if (code == PTRACE_EVENT_EXEC) {
                for (size_t i = 0; i < trap_count; ++i) if (traps[i].owner == group) traps[i].live = 0;
                current->static_exec = exec_image(tid, group);
            }
        } else if (signal == (SIGTRAP | 0x80) && current->static_exec) {
            struct user_regs_struct registers;
            if (ptrace(PTRACE_GETREGS, tid, NULL, &registers)) error(group, "PTRACE_GETREGS static syscall");
            else if ((long long)registers.rax >= 0 && (registers.orig_rax == SYS_mmap || registers.orig_rax == SYS_mprotect || registers.orig_rax == SYS_munmap)) {
                char proc[80], path[8192]; snprintf(proc, sizeof(proc), "/proc/%d/exe", (int)tid);
                ssize_t size = readlink(proc, path, sizeof(path) - 1);
                if (size < 0) error(group, "read static main path");
                else { path[size] = 0; static_mappings(tid, group, path); }
            }
        } else if (signal == SIGSTOP) {
            loader_events(tid, group);
        } else if (signal == SIGTRAP) {
            struct user_regs_struct registers;
            if (ptrace(PTRACE_GETREGS, tid, NULL, &registers)) error(group, "PTRACE_GETREGS");
            else {
                int hit = 0;
                if (current->stepping) {
                    patch(tid, current->stepping, 0xcc, NULL); current->stepping = 0; hit = 1;
                }
                for (size_t i = 0; !hit && i < trap_count; ++i) if (traps[i].live && traps[i].owner == group && traps[i].address == registers.rip - 1) {
                    if (traps[i].resolver) {
                        char symbol[8192];
                        if (!read_remote_string(tid, registers.rsi, symbol, sizeof(symbol))) break;
                        if (gl_symbol(symbol)) {
                            char caller[8192]; uintptr_t return_address = 0;
                            caller_module(tid, group, registers.rsp, caller, sizeof(caller), &return_address);
                            event("native_gl_binding", group, "%s\t%s\t", symbol, caller);
                        }
                        {
                            size_t peers = 0;
                            for (size_t n = 0; n < task_count; ++n) if (tasks[n].live && tasks[n].owner == group) ++peers;
                            if (peers != 1) { ++errors; event("debug_error", group, "Multithreaded static symbol resolver single-step unsupported"); }
                            else {
                                patch(tid, traps[i].address, traps[i].original, NULL);
                                registers.rip = traps[i].address;
                                if (ptrace(PTRACE_SETREGS, tid, NULL, &registers)) error(group, "PTRACE_SETREGS resolver step");
                                current->stepping = traps[i].address;
                            }
                        }
                    } else {
                        char caller[8192]; uintptr_t return_address = 0;
                        caller_module(tid, group, registers.rsp, caller, sizeof(caller), &return_address);
                        event("native_gl_call", group, "%s\t%s\t%s\t%s\t0x%lx", traps[i].name, traps[i].aliases, traps[i].path,
                              caller, (unsigned long)return_address);
                        if (traps[i].stop) kill_tree();
                        else if (!traps[i].endbr) {
                            ++errors; event("debug_error", group, "GL export does not begin with endbr64, cannot step over: %s|%s",
                                            traps[i].name, traps[i].path);
                        } else {
                            registers.rip = traps[i].address + 4;
                            if (ptrace(PTRACE_SETREGS, tid, NULL, &registers)) error(group, "PTRACE_SETREGS GL step-over");
                        }
                    }
                    hit = 1; break;
                }
                if (!hit) { ++errors; event("debug_error", group, "Unrecognized SIGTRAP tid=%d", (int)tid); deliver = signal; }
            }
        } else deliver = signal;
        if (errors && !terminated) kill_tree();
        current = task(tid); /* A fork event can reallocate the task array. */
        enum __ptrace_request request = current && current->stepping ? PTRACE_SINGLESTEP : (current && current->static_exec ? PTRACE_SYSCALL : PTRACE_CONT);
        if (ptrace(request, tid, NULL, (void *)(intptr_t)deliver) && errno != ESRCH) error(group, "PTRACE_CONT/SYSCALL");
    }
    if (!errors && !terminated) finish_loader_events(root);
    event("debug_complete", root, "root_code=%d errors=%d tasks=%zu", root_code, errors, task_count);
    fclose(output); fclose(loader);
    for (size_t i = 0; i < trap_count; ++i) { free(traps[i].name); free(traps[i].path); free(traps[i].aliases); }
    for (size_t i = 0; i < image_count; ++i) free(images[i].path);
    for (size_t i = 0; i < mapped_count; ++i) free(mapped[i].path);
    free(mapped); free(images); free(traps); free(tasks);
    return errors ? 125 : root_code;
}
