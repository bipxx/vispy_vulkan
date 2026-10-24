/* SPDX-License-Identifier: AGPL-3.0-only
 * Concurrent ordinary resolver calls, followed by optional GL negative control.
 * No CRT, Qt, Vulkan driver or GL runtime dependency.
 */
typedef unsigned long DWord;
typedef unsigned short WChar;
typedef void *Handle;
__declspec(dllimport) Handle __stdcall CreateEventW(void *, int, int, const WChar *);
__declspec(dllimport) Handle __stdcall CreateThread(void *, unsigned __int64, DWord (__stdcall *)(void *), void *, DWord, DWord *);
__declspec(dllimport) int __stdcall SetEvent(Handle);
__declspec(dllimport) DWord __stdcall WaitForSingleObject(Handle, DWord);
__declspec(dllimport) DWord __stdcall WaitForMultipleObjects(DWord, const Handle *, int, DWord);
__declspec(dllimport) int __stdcall CloseHandle(Handle);
__declspec(dllimport) Handle __stdcall GetModuleHandleW(const WChar *);
__declspec(dllimport) void *__stdcall GetProcAddress(Handle, const char *);
__declspec(dllimport) DWord __stdcall GetEnvironmentVariableW(const WChar *, WChar *, DWord);
__declspec(dllimport) Handle __stdcall GetStdHandle(DWord);
__declspec(dllimport) int __stdcall WriteFile(Handle, const void *, DWord, DWord *, void *);
__declspec(dllimport) void __stdcall ExitProcess(DWord);

static Handle start_event;
static Handle kernel;
static long volatile resolver_calls;
static const char token[] = "GetTickCount64";
long __cdecl _InterlockedIncrement(long volatile *);
#pragma intrinsic(_InterlockedIncrement)
/* Exported as GetProcAddress by the linker. The first instruction increments
 * the count, so replaying an executed entry instruction changes the result.
 * Exact argument identity and returned value are independently checked.
 */
__declspec(noinline) void *auditGetProcAddress(Handle module, const char *name) {
    _InterlockedIncrement(&resolver_calls);
    return module == kernel && name == token ? (void *)(unsigned __int64)0x12345678 : 0;
}
__declspec(dllexport) __declspec(noinline) void glNoOpenGLResolverRaceControl(void) { }

static DWord __stdcall worker(void *unused) {
    unsigned int repeat;
    (void)unused;
    if (WaitForSingleObject(start_event, 15000) != 0) ExitProcess(11);
    for (repeat = 0; repeat < 32; ++repeat) {
        if (!GetProcAddress(kernel, "GetTickCount64")) ExitProcess(12);
        if (auditGetProcAddress(kernel, token) != (void *)(unsigned __int64)0x12345678) ExitProcess(16);
    }
    return 0;
}

void __stdcall control_main(void) {
    Handle threads[32];
    WChar mode[32];
    unsigned int index;
    DWord written;
    kernel = GetModuleHandleW(L"kernel32.dll");
    start_event = CreateEventW(0, 1, 0, 0);
    if (!kernel || !start_event) ExitProcess(10);
    for (index = 0; index < 32; ++index) {
        threads[index] = CreateThread(0, 0, worker, 0, 0, 0);
        if (!threads[index]) ExitProcess(13);
    }
    SetEvent(start_event);
    if (WaitForMultipleObjects(32, threads, 1, 20000) != 0) ExitProcess(14);
    if (resolver_calls != 32 * 32) ExitProcess(17);
    for (index = 0; index < 32; ++index) CloseHandle(threads[index]);
    CloseHandle(start_event);
    WriteFile(GetStdHandle((DWord)-11), "ordinary_resolvers_completed\n", 29, &written, 0);
    mode[0] = 0;
    GetEnvironmentVariableW(L"VISPY_RESOLVER_RACE_AFTER", mode, 32);
    if (mode[0] == 'l') {
        if (!GetProcAddress(GetModuleHandleW(0), "glNoOpenGLResolverRaceControl")) ExitProcess(15);
    } else if (mode[0] == 'c') {
        void (*volatile call)(void) = glNoOpenGLResolverRaceControl;
        call();
    }
    ExitProcess(0);
}
