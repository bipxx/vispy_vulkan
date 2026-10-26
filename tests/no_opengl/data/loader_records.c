/* SPDX-License-Identifier: AGPL-3.0-only
 * Exercise the production incremental reader with actual libc file streams.
 * No ptrace or rendering is performed: the known VDSO record needs no traps.
 */
#define main observer_program_main
#include "debugger_linux.c"
#undef main
#ifdef ORIGINAL_LOADER_READER
/* Local historical comparison only; normal tests use production finalization. */
static void finish_loader_events(pid_t root) { loader_events(root, root); }
#endif

static int append(int fd, const char *data, size_t size) {
    return write(fd, data, size) == (ssize_t)size;
}
int main(int argc, char **argv) {
    if (argc != 3) return 90;
    const char *record = "native_image\t7\t0x0|linux-vdso.so.1\n";
    size_t size = strlen(record), cut = (size_t)strtoul(argv[2], NULL, 10);
    int fd = memfd_create("loader-record-control", MFD_CLOEXEC);
    int out = memfd_create("loader-record-diagnostics", MFD_CLOEXEC);
    if (fd < 0 || out < 0) return 91;
    char proc[80]; snprintf(proc, sizeof(proc), "/proc/self/fd/%d", fd);
    loader = fopen(proc, "r"); output = fdopen(out, "w+");
    if (!loader || !output) return 92;
    if (!strcmp(argv[1], "split")) {
        if (!cut || cut >= size || !append(fd, record, cut)) return 93;
        loader_events(7, 7);
        if (errors || image_count || ftello(loader) != 0) return 41;
        if (!append(fd, record + cut, size - cut)) return 94;
        loader_events(7, 7);
        if (errors || image_count != 1 || !images[0].done) return 42;
    } else if (!strcmp(argv[1], "malformed")) {
        const char *bad[] = {"native_image\n", "native_image\t7\n", "native_image\t7\t0x0\n"};
        if (cut >= 3 || !append(fd, bad[cut], strlen(bad[cut]))) return 95;
        loader_events(7, 7);
        if (errors != 1 || image_count) return 43;
    } else if (!strcmp(argv[1], "tail")) {
        if (!append(fd, record, size - 1)) return 96;
        loader_events(7, 7);
        if (errors || image_count) return 44;
        finish_loader_events(7);
        if (errors != 1 || image_count) return 45;
    } else return 97;
    printf("PASS %s %zu\n", argv[1], cut);
    fclose(loader); fclose(output); close(fd);
    for (size_t i = 0; i < image_count; ++i) free(images[i].path);
    free(images); return 0;
}
