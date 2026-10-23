/* SPDX-License-Identifier: AGPL-3.0-only
 * Linux x86-64 ptrace process-tree/public GL-export observer. The cooperating
 * LD_AUDIT module stops at object-open/close, before constructors/user code.
 * No GL implementation, injection library or Python hook is used by controls.
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
#include <sys/wait.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error This observer requires Linux x86-64
#endif

typedef struct { pid_t tid, owner; int live; } Task;
typedef struct { pid_t owner; uintptr_t address, bias; unsigned char original; int live; char *name, *path; } Trap;
typedef struct { pid_t owner; uintptr_t bias; int unload, done; char *path; } Image;
static Task *tasks;
static Trap *traps;
static Image *images;
static size_t task_count, trap_count;
static size_t image_count;
static FILE *output, *loader;
static int errors, terminated, root_code = 125;

static void event(const char *kind, pid_t pid, const char *format, ...) {
    fprintf(output, "%s\t%d\t", kind, (int)pid);
    va_list args; va_start(args, format); vfprintf(output, format, args); va_end(args);
    fputc('\n', output); fflush(output);
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
    tasks[task_count++] = (Task){tid, group, 1};
    event("debug_task_start", group, "tid=%d parent_tid=%d", (int)tid, (int)parent);
    Task *parent_task = task(parent);
    if (parent_task && parent_task->owner != group) {
        size_t count = trap_count;
        for (size_t i = 0; i < count; ++i) if (traps[i].live && traps[i].owner == parent_task->owner) {
            Trap copy = traps[i]; copy.owner = group;
            copy.name = strdup(copy.name); copy.path = strdup(copy.path);
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
static void image(pid_t tid, pid_t group, uintptr_t bias, const char *requested, int unload) {
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
    for (unsigned int i = 0; i < header->e_shnum; ++i) if (sections[i].sh_type == SHT_DYNSYM) {
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
            if (!gl_symbol(name)) continue;
            unsigned int type = ELF64_ST_TYPE(symbol->st_info);
            if (type != STT_FUNC) { ++errors; event("debug_error", group, "Unsupported GL export type: %s (%u)", name, type); continue; }
            uintptr_t address = bias + symbol->st_value;
            int exists = 0;
            for (size_t p = 0; p < trap_count; ++p) if (traps[p].live && traps[p].owner == group && traps[p].address == address) exists = 1;
            if (exists) continue;
            unsigned char original;
            if (!patch(tid, address, 0xcc, &original)) continue;
            if (original == 0xcc) { ++errors; event("debug_error", group, "GL export already contains trap: %s", name); continue; }
            traps = grow(traps, trap_count + 1, sizeof(*traps));
            traps[trap_count++] = (Trap){group, address, bias, original, 1, strdup(name), strdup(path)};
            event("debug_export_trap", group, "%s|%s", name, path);
        }
    }
    if (!tables) { ++errors; event("debug_error", group, "No dynamic symbol table: %s", path); }
    munmap((void *)data, size);
}
static void loader_events(pid_t tid, pid_t group) {
    /* Queue interleaved process records; each address space is instrumented
     * only while a task in that address space is at its loader stop. */
    char *line = NULL; size_t capacity = 0;
    clearerr(loader);
    while (getline(&line, &capacity, loader) >= 0) {
        char *kind = line, *pid = strchr(line, '\t'); if (!pid) { ++errors; continue; } *pid++ = 0;
        char *value = strchr(pid, '\t'); if (!value) { ++errors; continue; } *value++ = 0;
        value[strcspn(value, "\r\n")] = 0;
        if (strcmp(kind, "native_image") && strcmp(kind, "native_image_unload")) continue;
        pid_t source = (pid_t)strtol(pid, NULL, 10);
        char *end; uintptr_t bias = (uintptr_t)strtoull(value, &end, 16);
        if (*end != '|') { ++errors; continue; }
        images = grow(images, image_count + 1, sizeof(*images));
        images[image_count++] = (Image){source, bias, strcmp(kind, "native_image_unload") == 0, 0, strdup(end + 1)};
    }
    free(line);
    for (size_t i = 0; i < image_count; ++i) if (!images[i].done && images[i].owner == group) {
        image(tid, group, images[i].bias, images[i].path, images[i].unload); images[i].done = 1;
    }
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
    long options = PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE | PTRACE_O_TRACEEXEC | PTRACE_O_TRACEEXIT | PTRACE_O_EXITKILL;
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
                event("debug_exec", group, "tid=%d", (int)tid);
            }
        } else if (signal == SIGSTOP) {
            loader_events(tid, group);
        } else if (signal == SIGTRAP) {
            struct user_regs_struct registers;
            if (ptrace(PTRACE_GETREGS, tid, NULL, &registers)) error(group, "PTRACE_GETREGS");
            else {
                int hit = 0;
                for (size_t i = 0; i < trap_count; ++i) if (traps[i].live && traps[i].owner == group && traps[i].address == registers.rip - 1) {
                    event("native_gl_call", group, "%s|%s", traps[i].name, traps[i].path); hit = 1; break;
                }
                if (hit) kill_tree();
                else { ++errors; event("debug_error", group, "Unrecognized SIGTRAP tid=%d", (int)tid); deliver = signal; }
            }
        } else deliver = signal;
        if (errors && !terminated) kill_tree();
        if (ptrace(PTRACE_CONT, tid, NULL, (void *)(intptr_t)deliver) && errno != ESRCH) error(group, "PTRACE_CONT");
    }
    event("debug_complete", root, "root_code=%d errors=%d tasks=%zu", root_code, errors, task_count);
    fclose(output); fclose(loader);
    for (size_t i = 0; i < trap_count; ++i) { free(traps[i].name); free(traps[i].path); }
    for (size_t i = 0; i < image_count; ++i) free(images[i].path);
    free(images); free(traps); free(tasks);
    return errors ? 125 : root_code;
}
