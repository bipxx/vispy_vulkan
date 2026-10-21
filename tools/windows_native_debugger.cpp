#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <dbghelp.h>

#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::wstring hex(DWORD64 value) {
    std::wostringstream out;
    out << L"0x" << std::hex << std::setw(16) << std::setfill(L'0') << value;
    return out.str();
}
std::wstring win_error(DWORD error = GetLastError()) {
    wchar_t* buffer = nullptr;
    FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
                   FORMAT_MESSAGE_IGNORE_INSERTS, nullptr, error, 0,
                   reinterpret_cast<wchar_t*>(&buffer), 0, nullptr);
    std::wstring result = std::to_wstring(error) + L": " + (buffer ? buffer : L"unknown Windows error");
    if (buffer) LocalFree(buffer);
    while (!result.empty() && (result.back() == L'\r' || result.back() == L'\n')) result.pop_back();
    return result;
}
std::string utf8(const std::wstring& value) {
    if (value.empty()) return {};
    const int size = WideCharToMultiByte(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    std::string result(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), result.data(), size, nullptr, nullptr);
    return result;
}
struct Log {
    std::ofstream file;
    ULONGLONG start = GetTickCount64();
    explicit Log(const std::filesystem::path& path) {
        if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
        file.open(path, std::ios::binary | std::ios::trunc);
        if (!file) throw std::runtime_error("cannot open debugger log");
    }
    void put(const std::wstring& value) {
        const auto line = utf8(L"[" + std::to_wstring(GetTickCount64() - start) + L" ms] " + value + L"\n");
        file.write(line.data(), static_cast<std::streamsize>(line.size()));
        file.flush();
        std::fwrite(line.data(), 1, line.size(), stdout);
        std::fflush(stdout);
    }
};
struct Handle {
    HANDLE value = nullptr;
    explicit Handle(HANDLE handle = nullptr) : value(handle) {}
    ~Handle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};

// CommandLineToArgvW/MSVC-compatible quoting, including empty arguments and
// backslashes before a quote or the closing quote. No command shell is used.
std::wstring quote(const std::wstring& argument) {
    std::wstring result = L"\"";
    size_t slashes = 0;
    for (wchar_t character : argument) {
        if (character == L'\\') { ++slashes; continue; }
        result.append(character == L'"' ? slashes * 2 + 1 : slashes, L'\\');
        result += character;
        slashes = 0;
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}
std::wstring file_name(HANDLE file) {
    if (!file || file == INVALID_HANDLE_VALUE) return {};
    std::vector<wchar_t> buffer(1024);
    for (;;) {
        const DWORD size = GetFinalPathNameByHandleW(file, buffer.data(), static_cast<DWORD>(buffer.size()), FILE_NAME_NORMALIZED);
        if (!size) return {};
        if (size < buffer.size()) {
            std::wstring path(buffer.data(), size);
            // DbgHelp's symbol/PDB lookup does not consistently accept the
            // extended Win32 namespace returned by GetFinalPathNameByHandle.
            if (path.rfind(L"\\\\?\\UNC\\", 0) == 0) path = L"\\\\" + path.substr(8);
            else if (path.rfind(L"\\\\?\\", 0) == 0) path.erase(0, 4);
            return path;
        }
        buffer.resize(static_cast<size_t>(size) + 1);
    }
}
std::wstring process_name(HANDLE process) {
    std::vector<wchar_t> buffer(32768);
    DWORD size = static_cast<DWORD>(buffer.size());
    return QueryFullProcessImageNameW(process, 0, buffer.data(), &size) ? std::wstring(buffer.data(), size) : L"";
}

struct Debugger {
    Handle owned_process;
    HANDLE process;
    DWORD pid;
    Log& log;
    bool symbols = false;
    std::map<DWORD64, std::wstring> modules;
    std::set<DWORD> threads;
    Debugger(HANDLE process_handle, DWORD process_id, Log& output, const std::wstring& symbol_path)
        : owned_process(process_handle), process(process_handle), pid(process_id), log(output) {
        SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_LOAD_LINES |
                      SYMOPT_FAIL_CRITICAL_ERRORS | SYMOPT_NO_PROMPTS);
        symbols = SymInitializeW(process, symbol_path.empty() ? nullptr : symbol_path.c_str(), FALSE) != FALSE;
        if (!symbols) log.put(L"SymInitialize failed: " + win_error());
    }
    ~Debugger() { if (symbols) SymCleanup(process); }
    void load(HANDLE file, void* address, const std::wstring& fallback = L"") {
        const DWORD64 base = reinterpret_cast<DWORD64>(address);
        std::wstring path = file_name(file);
        if (path.empty()) path = fallback;
        modules[base] = path.empty() ? L"<path unavailable>" : path;
        if (symbols) {
            DWORD image_size = 0;
            IMAGE_DOS_HEADER dos{};
            if (ReadProcessMemory(process, address, &dos, sizeof(dos), nullptr) && dos.e_magic == IMAGE_DOS_SIGNATURE && dos.e_lfanew > 0) {
                const DWORD64 size_address = base + dos.e_lfanew + offsetof(IMAGE_NT_HEADERS64, OptionalHeader) + offsetof(IMAGE_OPTIONAL_HEADER64, SizeOfImage);
                ReadProcessMemory(process, reinterpret_cast<void*>(size_address), &image_size, sizeof(image_size), nullptr);
            }
            SetLastError(ERROR_SUCCESS);
            const auto loaded = SymLoadModuleExW(process, file, path.empty() ? nullptr : path.c_str(), nullptr, base, image_size, nullptr, 0);
            if (!loaded && GetLastError() != ERROR_SUCCESS)
                log.put(L"SymLoadModule " + modules[base] + L" failed: " + win_error());
        }
        if (file && file != INVALID_HANDLE_VALUE) CloseHandle(file);
    }
    std::wstring frame_name(DWORD64 address) {
        std::wstring result = hex(address);
        auto module = modules.upper_bound(address);
        if (module != modules.begin()) {
            --module;
            result += L" " + module->second + L"+" + hex(address - module->first);
        }
        if (!symbols) return result;
        alignas(SYMBOL_INFOW) unsigned char bytes[sizeof(SYMBOL_INFOW) + MAX_SYM_NAME * sizeof(wchar_t)]{};
        auto* symbol = reinterpret_cast<SYMBOL_INFOW*>(bytes);
        symbol->SizeOfStruct = sizeof(SYMBOL_INFOW);
        symbol->MaxNameLen = MAX_SYM_NAME;
        DWORD64 displacement = 0;
        if (SymFromAddrW(process, address, &displacement, symbol))
            result += L" " + std::wstring(symbol->Name, symbol->NameLen) + L"+" + hex(displacement);
        IMAGEHLP_LINEW64 line{};
        line.SizeOfStruct = sizeof(line);
        DWORD line_displacement = 0;
        if (SymGetLineFromAddrW64(process, address, &line_displacement, &line))
            result += L" " + std::wstring(line.FileName) + L":" + std::to_wstring(line.LineNumber);
        return result;
    }
    bool stack(DWORD thread_id, CONTEXT* captured = nullptr) {
        Handle thread(OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, thread_id));
        if (!thread.value) { log.put(L"OpenThread " + std::to_wstring(thread_id) + L" failed: " + win_error()); return false; }
        CONTEXT context{};
        context.ContextFlags = CONTEXT_FULL;
        if (!GetThreadContext(thread.value, &context)) {
            log.put(L"GetThreadContext " + std::to_wstring(thread_id) + L" failed: " + win_error()); return false;
        }
        if (captured) *captured = context;
        STACKFRAME64 frame{};
#if defined(_M_X64)
        const DWORD machine = IMAGE_FILE_MACHINE_AMD64;
        frame.AddrPC.Offset = context.Rip;
        frame.AddrStack.Offset = context.Rsp;
        frame.AddrFrame.Offset = context.Rbp;
        log.put(L"thread " + std::to_wstring(thread_id) + L" RIP=" + hex(context.Rip) + L" RSP=" + hex(context.Rsp) + L" RBP=" + hex(context.Rbp));
        log.put(L"RAX=" + hex(context.Rax) + L" RBX=" + hex(context.Rbx) + L" RCX=" + hex(context.Rcx) + L" RDX=" + hex(context.Rdx));
        log.put(L"RSI=" + hex(context.Rsi) + L" RDI=" + hex(context.Rdi) + L" R8=" + hex(context.R8) + L" R9=" + hex(context.R9));
#elif defined(_M_IX86)
        const DWORD machine = IMAGE_FILE_MACHINE_I386;
        frame.AddrPC.Offset = context.Eip;
        frame.AddrStack.Offset = context.Esp;
        frame.AddrFrame.Offset = context.Ebp;
        log.put(L"thread " + std::to_wstring(thread_id) + L" EIP=" + hex(context.Eip) + L" ESP=" + hex(context.Esp));
#else
#error Native debugger currently requires an x64 or x86 Windows host build.
#endif
        frame.AddrPC.Mode = frame.AddrStack.Mode = frame.AddrFrame.Mode = AddrModeFlat;
        log.put(L"  #0 " + frame_name(frame.AddrPC.Offset));
        int printed = 1;
        for (int depth = 1; depth < 96; ++depth) {
            const DWORD64 previous_pc = frame.AddrPC.Offset, previous_stack = frame.AddrStack.Offset;
            if (!StackWalk64(machine, process, thread.value, &frame, &context, nullptr,
                             SymFunctionTableAccess64, SymGetModuleBase64, nullptr)) break;
            if (!frame.AddrPC.Offset) break;
            // The first StackWalk call can return the seeded current frame.
            // Allow that initialization before testing forward progress.
            if (frame.AddrPC.Offset == previous_pc && frame.AddrStack.Offset == previous_stack) {
                if (depth == 1) continue;
                break;
            }
            log.put(L"  #" + std::to_wstring(printed++) + L" " + frame_name(frame.AddrPC.Offset));
        }
        return true;
    }
    void exception(const DEBUG_EVENT& event, const std::filesystem::path& dump_path, bool all_threads) {
        const auto& record = event.u.Exception.ExceptionRecord;
        log.put(std::wstring(event.u.Exception.dwFirstChance ? L"FIRST-CHANCE" : L"SECOND-CHANCE") + L" exception code=" + hex(record.ExceptionCode) + L" address=" + hex(reinterpret_cast<DWORD64>(record.ExceptionAddress)) + L" pid=" + std::to_wstring(pid) + L" thread=" + std::to_wstring(event.dwThreadId));
        if (record.ExceptionCode == EXCEPTION_ACCESS_VIOLATION && record.NumberParameters >= 2) {
            const auto mode = record.ExceptionInformation[0];
            log.put(std::wstring(L"access ") + (mode == 0 ? L"read" : mode == 1 ? L"write" : mode == 8 ? L"execute" : L"unknown") + L" address=" + hex(record.ExceptionInformation[1]));
        }
        CONTEXT context{};
        const bool captured = stack(event.dwThreadId, &context);
        if (all_threads) for (DWORD thread : threads) if (thread != event.dwThreadId) stack(thread);
        log.put(L"loaded modules:");
        for (const auto& [base, path] : modules) log.put(L"  " + hex(base) + L" " + path);
        if (dump_path.empty()) return;
        if (!dump_path.parent_path().empty()) std::filesystem::create_directories(dump_path.parent_path());
        Handle file(CreateFileW(dump_path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr));
        if (file.value == INVALID_HANDLE_VALUE) { log.put(L"cannot create minidump: " + win_error()); return; }
        EXCEPTION_RECORD local_record = record;
        local_record.ExceptionRecord = nullptr;
        EXCEPTION_POINTERS pointers{&local_record, &context};
        MINIDUMP_EXCEPTION_INFORMATION exception_info{event.dwThreadId, &pointers, FALSE};
        const auto flags = static_cast<MINIDUMP_TYPE>(MiniDumpNormal | MiniDumpWithThreadInfo | MiniDumpWithUnloadedModules | MiniDumpWithIndirectlyReferencedMemory);
        if (MiniDumpWriteDump(process, pid, file.value, flags, captured ? &exception_info : nullptr, nullptr, nullptr))
            log.put(L"minidump " + dump_path.wstring());
        else log.put(L"MiniDumpWriteDump failed: " + win_error());
    }
};
}  // namespace

int wmain(int argc, wchar_t** argv) {
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    // CPU-only smoke fixture. It is never used unless requested explicitly.
    if (argc == 2 && std::wstring(argv[1]) == L"--self-test-crash-child") {
        volatile int* invalid = nullptr;
        *invalid = 17;
        return 0;
    }
    try {
        std::filesystem::path log_path = L"native-debugger.log", dump_path;
        std::wstring cwd, symbol_path;
        bool all_threads = false, capture_first_chance = false, debug_children = false;
        ULONGLONG timeout_ms = 0;
        int child = 1;
        for (; child < argc && std::wstring(argv[child]) != L"--"; ++child) {
            const std::wstring option = argv[child];
            if (option == L"--all-threads") { all_threads = true; continue; }
            if (option == L"--capture-first-chance") { capture_first_chance = true; continue; }
            if (option == L"--debug-children") { debug_children = true; continue; }
            if (++child >= argc) throw std::runtime_error("debugger option lacks value");
            if (option == L"--log") log_path = argv[child];
            else if (option == L"--dump") dump_path = argv[child];
            else if (option == L"--cwd") cwd = argv[child];
            else if (option == L"--symbols") symbol_path = argv[child];
            else if (option == L"--timeout-seconds") {
                const auto seconds = std::stoull(argv[child]);
                if (seconds > 86400) throw std::runtime_error("debugger timeout exceeds one day");
                timeout_ms = seconds * 1000;
            } else throw std::runtime_error("unrecognized debugger option");
        }
        if (child >= argc || ++child >= argc) throw std::runtime_error("usage: windows_native_debugger [--log path] [--dump path] [--cwd path] [--symbols path] [--all-threads] [--timeout-seconds N] -- executable arguments");
        Log log(log_path);
        std::wstring command;
        for (int i = child; i < argc; ++i) {
            if (!command.empty()) command += L' ';
            command += quote(argv[i]);
        }
        log.put(L"launch " + command);
        STARTUPINFOW startup{};
        startup.cb = sizeof(startup);
        startup.dwFlags = STARTF_USESTDHANDLES;
        startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
        startup.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
        startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
        PROCESS_INFORMATION info{};
        if (!CreateProcessW(argv[child], command.data(), nullptr, nullptr, TRUE,
                            (debug_children ? DEBUG_PROCESS : DEBUG_ONLY_THIS_PROCESS) | CREATE_NO_WINDOW, nullptr,
                            cwd.empty() ? nullptr : cwd.c_str(), &startup, &info)) {
            log.put(L"CreateProcess failed: " + win_error()); return 2;
        }
        Handle process(info.hProcess), primary_thread(info.hThread);
        DebugSetProcessKillOnExit(TRUE);
        std::map<DWORD, std::unique_ptr<Debugger>> debuggers;
        std::set<DWORD> loader_breakpoints;
        DWORD parent_exit_code = 0, child_failure = 0;
        bool parent_exited = false;
        const ULONGLONG start = GetTickCount64();
        bool timed_out = false;
        for (;;) {
            DEBUG_EVENT event{};
            if (!WaitForDebugEvent(&event, 1000)) {
                if (GetLastError() != ERROR_SEM_TIMEOUT) {
                    log.put(L"WaitForDebugEvent failed: " + win_error());
                    TerminateProcess(process.value, 2); return 2;
                }
                if (timeout_ms && GetTickCount64() - start >= timeout_ms && !timed_out) {
                    timed_out = true;
                    log.put(L"debugger timeout; terminating child");
                    for (const auto& [pid, debugger] : debuggers) TerminateProcess(debugger->process, ERROR_TIMEOUT);
                    if (!parent_exited) TerminateProcess(process.value, ERROR_TIMEOUT);
                }
                continue;
            }
            DWORD disposition = DBG_CONTINUE;
            auto found = debuggers.find(event.dwProcessId);
            Debugger* debugger = found == debuggers.end() ? nullptr : found->second.get();
            switch (event.dwDebugEventCode) {
            case CREATE_PROCESS_DEBUG_EVENT: {
                HANDLE child_process = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_DUP_HANDLE | PROCESS_TERMINATE, FALSE, event.dwProcessId);
                if (!child_process) throw std::runtime_error("cannot open debugged process for stack capture");
                auto created = std::make_unique<Debugger>(child_process, event.dwProcessId, log, symbol_path);
                debugger = created.get();
                debugger->threads.insert(event.dwThreadId);
                debugger->load(event.u.CreateProcessInfo.hFile, event.u.CreateProcessInfo.lpBaseOfImage, process_name(child_process));
                debuggers[event.dwProcessId] = std::move(created);
                loader_breakpoints.insert(event.dwProcessId);
                log.put(L"process " + std::to_wstring(event.dwProcessId));
                break;
            }
            case CREATE_THREAD_DEBUG_EVENT: if (debugger) debugger->threads.insert(event.dwThreadId); break;
            case EXIT_THREAD_DEBUG_EVENT: if (debugger) debugger->threads.erase(event.dwThreadId); break;
            case LOAD_DLL_DEBUG_EVENT:
                if (debugger) debugger->load(event.u.LoadDll.hFile, event.u.LoadDll.lpBaseOfDll);
                else if (event.u.LoadDll.hFile) CloseHandle(event.u.LoadDll.hFile);
                break;
            case UNLOAD_DLL_DEBUG_EVENT:
                if (debugger) {
                    if (debugger->symbols) SymUnloadModule64(debugger->process, reinterpret_cast<DWORD64>(event.u.UnloadDll.lpBaseOfDll));
                    debugger->modules.erase(reinterpret_cast<DWORD64>(event.u.UnloadDll.lpBaseOfDll));
                }
                break;
            case EXCEPTION_DEBUG_EVENT:
                if (loader_breakpoints.count(event.dwProcessId) && event.u.Exception.dwFirstChance && event.u.Exception.ExceptionRecord.ExceptionCode == EXCEPTION_BREAKPOINT)
                    loader_breakpoints.erase(event.dwProcessId);
                else {
                    disposition = DBG_EXCEPTION_NOT_HANDLED;
                    if (debugger && (!event.u.Exception.dwFirstChance || (capture_first_chance && event.u.Exception.ExceptionRecord.ExceptionCode == EXCEPTION_ACCESS_VIOLATION)))
                        debugger->exception(event, dump_path, all_threads);
                }
                break;
            case EXIT_PROCESS_DEBUG_EVENT:
                log.put(L"process " + std::to_wstring(event.dwProcessId) + L" exit=" + hex(event.u.ExitProcess.dwExitCode) + L" (" + std::to_wstring(event.u.ExitProcess.dwExitCode) + L")");
                if (event.dwProcessId == info.dwProcessId) {
                    parent_exited = true;
                    parent_exit_code = event.u.ExitProcess.dwExitCode;
                }
                if (!child_failure && event.u.ExitProcess.dwExitCode) child_failure = event.u.ExitProcess.dwExitCode;
                ContinueDebugEvent(event.dwProcessId, event.dwThreadId, disposition);
                debuggers.erase(event.dwProcessId);
                loader_breakpoints.erase(event.dwProcessId);
                if (parent_exited && debuggers.empty())
                    return static_cast<int>(timed_out ? ERROR_TIMEOUT : parent_exit_code ? parent_exit_code : child_failure);
                continue;
            default: break;
            }
            if (!ContinueDebugEvent(event.dwProcessId, event.dwThreadId, disposition)) {
                log.put(L"ContinueDebugEvent failed: " + win_error());
                TerminateProcess(process.value, 2); return 2;
            }
        }
    } catch (const std::exception& error) {
        std::fprintf(stderr, "native debugger: %s\n", error.what());
        return 2;
    }
}
