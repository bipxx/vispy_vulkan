/* SPDX-License-Identifier: AGPL-3.0-only
 * Independent static-ELF controls; no OpenGL implementation.
 * cc -static -O0 -o static_negative_probe static_negative_probe.c -ldl
 */
#include <dlfcn.h>
#include <string.h>

int glNoOpenGLStaticNegativeControl(void) { return 29; }
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    if (!strcmp(argv[1], "call")) return glNoOpenGLStaticNegativeControl() == 29 ? 0 : 3;
    void *module = dlopen(argv[2], RTLD_NOW);
    if (!module) return 4;
    if (!strcmp(argv[1], "resolve")) return dlsym(module, "glNoOpenGLNegativeControl") ? 0 : 5;
    return dlsym(module, "auditSafeControl") ? 0 : 6;
}
