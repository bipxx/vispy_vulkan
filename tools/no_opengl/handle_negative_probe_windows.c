/* SPDX-License-Identifier: AGPL-3.0-only
 * Independent CloseHandle fidelity controls. No CRT or GL implementation.
 */
typedef unsigned long DWord;
typedef unsigned short WChar;
typedef void *Handle;
__declspec(dllimport) int __stdcall CloseHandle(Handle);
__declspec(dllimport) Handle __stdcall CreateEventW(void *, int, int, const WChar *);
__declspec(dllimport) int __stdcall SetHandleInformation(Handle, DWord, DWord);
__declspec(dllimport) DWord __stdcall GetLastError(void);
__declspec(dllimport) void __stdcall SetLastError(DWord);
__declspec(dllimport) DWord __stdcall GetEnvironmentVariableW(const WChar *, WChar *, DWord);
__declspec(dllimport) Handle __stdcall GetStdHandle(DWord);
__declspec(dllimport) int __stdcall WriteFile(Handle, const void *, DWord, DWord *, void *);
__declspec(dllimport) Handle __stdcall LoadLibraryW(const WChar *);
__declspec(dllimport) void *__stdcall GetProcAddress(Handle, const char *);
__declspec(dllimport) void __stdcall ExitProcess(DWord);
__declspec(dllimport) void __stdcall RaiseException(DWord, DWord, DWord, const unsigned __int64 *);

static char *number(char *out, DWord value) {
    char reverse[16]; unsigned int used = 0;
    do { reverse[used++] = (char)('0' + value % 10); value /= 10; } while (value);
    while (used) *out++ = reverse[--used];
    return out;
}
static char *text(char *out, const char *value) { while (*value) *out++ = *value++; return out; }

void __stdcall control_main(void) {
    WChar mode[32], after[32], path[512];
    char line[128], *end = line;
    DWord written;
    mode[0] = after[0] = path[0] = 0;
    GetEnvironmentVariableW(L"VISPY_HANDLE_CONTROL_MODE", mode, 32);
    GetEnvironmentVariableW(L"VISPY_HANDLE_CONTROL_AFTER", after, 32);
    int protected_handle = mode[0] == 'p';
    Handle handle = protected_handle ? CreateEventW(0, 0, 0, 0) : (Handle)(unsigned __int64)0xBADF00D;
    if (protected_handle && (!handle || !SetHandleInformation(handle, 2, 2))) ExitProcess(10);
    SetLastError(0);
    int closed = CloseHandle(handle);
    DWord error = GetLastError();
    end = text(end, "{\"closed\":"); end = number(end, (DWord)closed);
    end = text(end, ",\"error\":"); end = number(end, error); end = text(end, "}\n");
    WriteFile(GetStdHandle((DWord)-11), line, (DWord)(end - line), &written, 0);
    if (protected_handle) { SetHandleInformation(handle, 2, 0); CloseHandle(handle); }
    if (closed || error != 6) ExitProcess(11);
    if (after[0] == 'u') RaiseException(0xc0000008UL, 0, 0, 0);
    if (after[0] == 'l' || after[0] == 'c') {
        DWord length = GetEnvironmentVariableW(L"VISPY_HANDLE_CONTROL_DLL", path, 512);
        if (!length || length >= 512) ExitProcess(12);
        Handle module = LoadLibraryW(path);
        if (!module) ExitProcess(13);
        if (after[0] == 'l') { if (!GetProcAddress(module, "glNoOpenGLNegativeControl")) ExitProcess(14); }
        else {
            int (*call)(void) = (int (*)(void))GetProcAddress(module, "auditCallControl");
            if (!call || call() != 17) ExitProcess(15);
        }
    }
    ExitProcess(0);
}
