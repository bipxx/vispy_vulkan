/* SPDX-License-Identifier: AGPL-3.0-only
 * An independent native negative-control fixture, not an OpenGL implementation.
 * Distinct return values prevent identical-code folding from making the safe
 * export share an address with the GL-shaped export.
 */
#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
__declspec(dllimport) void *__stdcall GetProcAddress(void *, const char *);
#else
#define EXPORT __attribute__((visibility("default")))
#include <dlfcn.h>
#endif
EXPORT int glNoOpenGLNegativeControl(void) { return 17; }
EXPORT int auditSafeControl(void) { return 23; }
/* Called through a harmlessly named export: Python's ctypes audit sees neither
 * the native lookup nor the direct native GL-shaped function call. */
EXPORT int auditResolveControl(void *module) {
#if defined(_WIN32)
    return GetProcAddress(module, "glNoOpenGLNegativeControl") != 0;
#else
    return dlsym(module, "glNoOpenGLNegativeControl") != 0;
#endif
}
EXPORT int auditCallControl(void) { return glNoOpenGLNegativeControl(); }
