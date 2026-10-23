"""Observe Windows startup/transient DLL loads, symbol lookups and GL calls.

The child is created under the Windows debugger, before its first instruction.
Each loaded image's GL exports and public native symbol resolvers receive debug
breakpoints before execution resumes. Ordinary resolver calls are single-stepped
with the other threads suspended; GL lookups terminate the negative control.
A hit is recorded and terminates the test process tree before executing GL.
Unresolved image paths, forwarded GL exports and failed breakpoint placement make
API coverage incomplete; they never become an absence claim.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time
import os
import hashlib
import json

from .dependencies import inspect_binary
from .policy import is_gl_entrypoint


def trace(command, *, environment, cwd, log, timeout=120, handle_baseline=None, _handle_control=False):
    if sys.platform != "win32":
        raise RuntimeError("Windows loader observation requires Windows")
    import ctypes as c
    from ctypes import wintypes as w
    pointer = c.c_void_p
    class ExceptionRecord(c.Structure):
        _fields_ = [("code", w.DWORD), ("flags", w.DWORD), ("record", pointer), ("address", pointer),
                    ("parameter_count", w.DWORD), ("information", c.c_size_t * 15)]
    class ExceptionInfo(c.Structure):
        _fields_ = [("record", ExceptionRecord), ("first_chance", w.DWORD)]
    class CreateThread(c.Structure):
        _fields_ = [("thread", w.HANDLE), ("tls", pointer), ("start", pointer)]
    class CreateProcess(c.Structure):
        _fields_ = [("file", w.HANDLE), ("process", w.HANDLE), ("thread", w.HANDLE), ("base", pointer),
                    ("debug_offset", w.DWORD), ("debug_size", w.DWORD), ("tls", pointer), ("start", pointer),
                    ("image_name", pointer), ("unicode", w.WORD)]
    class ExitProcess(c.Structure):
        _fields_ = [("code", w.DWORD)]
    class LoadDll(c.Structure):
        _fields_ = [("file", w.HANDLE), ("base", pointer), ("debug_offset", w.DWORD), ("debug_size", w.DWORD),
                    ("image_name", pointer), ("unicode", w.WORD)]
    class UnloadDll(c.Structure):
        _fields_ = [("base", pointer)]
    class DebugData(c.Union):
        _fields_ = [("exception", ExceptionInfo), ("create_process", CreateProcess), ("create_thread", CreateThread),
                    ("exit_process", ExitProcess), ("load", LoadDll), ("unload", UnloadDll)]
    class DebugEvent(c.Structure):
        _fields_ = [("code", w.DWORD), ("pid", w.DWORD), ("tid", w.DWORD), ("data", DebugData)]
    if c.sizeof(pointer) != 8 or c.sizeof(DebugEvent) != 176:
        raise RuntimeError("This Windows observer requires a 64-bit controller")
    k = c.WinDLL("kernel32", use_last_error=True)
    k.WaitForDebugEvent.argtypes = [c.POINTER(DebugEvent), w.DWORD]
    k.WaitForDebugEvent.restype = w.BOOL
    k.ContinueDebugEvent.argtypes = [w.DWORD, w.DWORD, w.DWORD]
    k.ContinueDebugEvent.restype = w.BOOL
    k.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD]
    k.GetFinalPathNameByHandleW.restype = w.DWORD
    k.CloseHandle.argtypes = [w.HANDLE]
    k.ReadProcessMemory.argtypes = [w.HANDLE, pointer, pointer, c.c_size_t, c.POINTER(c.c_size_t)]
    k.ReadProcessMemory.restype = w.BOOL
    k.WriteProcessMemory.argtypes = [w.HANDLE, pointer, pointer, c.c_size_t, c.POINTER(c.c_size_t)]
    k.WriteProcessMemory.restype = w.BOOL
    k.FlushInstructionCache.argtypes = [w.HANDLE, pointer, c.c_size_t]
    k.FlushInstructionCache.restype = w.BOOL
    k.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
    k.TerminateProcess.restype = w.BOOL
    k.GetThreadContext.argtypes = [w.HANDLE, pointer]
    k.GetThreadContext.restype = w.BOOL
    k.SetThreadContext.argtypes = [w.HANDLE, pointer]
    k.SetThreadContext.restype = w.BOOL
    k.SuspendThread.argtypes = [w.HANDLE]
    k.SuspendThread.restype = w.DWORD
    k.ResumeThread.argtypes = [w.HANDLE]
    k.ResumeThread.restype = w.DWORD
    k.GetExitCodeThread.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
    k.GetExitCodeThread.restype = w.BOOL
    k.OpenThread.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenThread.restype = w.HANDLE
    k.DuplicateHandle.argtypes = [w.HANDLE, w.HANDLE, w.HANDLE, c.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD]
    k.DuplicateHandle.restype = w.BOOL
    nt = c.WinDLL('ntdll')
    nt.NtSuspendThread.argtypes = [w.HANDLE, c.POINTER(w.ULONG)]
    nt.NtSuspendThread.restype = c.c_long
    nt.NtResumeThread.argtypes = [w.HANDLE, c.POINTER(w.ULONG)]
    nt.NtResumeThread.restype = c.c_long
    events, processes, modules, breakpoints, errors = [], {}, {}, {}, []
    threads, stepping, resolver_hooks, ordinal_names, image_sizes = {}, {}, {}, {}, {}
    close_functions, exception_dispatchers, unwinder = {}, {}, None
    handle_proof = None
    if handle_baseline:
        baseline_path = Path(handle_baseline).resolve(strict=True)
        baseline = json.loads(baseline_path.read_text())
        if baseline.get('schema') != 1 or baseline.get('status') != 'PASS_HANDLE_FIDELITY_CONTROLS' or not baseline.get('checks') or not all(baseline['checks'].values()):
            raise ValueError('A passing native CloseHandle fidelity baseline is required')
        required_os = {(Path(os.environ['SystemRoot']) / 'System32' / name).resolve() for name in ('ntdll.dll', 'KernelBase.dll')}
        if {Path(path).resolve() for path in baseline['os_files']} != required_os:
            raise ValueError('CloseHandle baseline does not bind both actual OS implementation files')
        control_source = Path(__file__).with_name('handle_negative_probe_windows.c')
        if baseline.get('control_source_sha256') != hashlib.sha256(control_source.read_bytes()).hexdigest():
            raise ValueError('CloseHandle independent control source differs')
        for path, expected in baseline['os_files'].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
                raise ValueError('CloseHandle baseline OS bytes differ')
        handle_proof = {'file': str(baseline_path), 'sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                        'os_files': baseline['os_files']}
    observed_pids, exited_pids = set(), set()
    started = time.monotonic()
    killed = False
    def emit(kind, **values):
        events.append({"kind": kind, "sequence": len(events), "elapsed_s": time.monotonic() - started, **values})
    def retain_thread(pid, tid, debug_handle):
        # Explicitly request suspend/query rights as well as context rights.
        # Debug-event handles can have a narrower granted mask.
        handle = k.OpenThread(0x005a, False, tid)
        # Windows owns debug-event process/thread handles until their EXIT
        # event is continued. Closing one early can let its numeric value be
        # reused, then closed again by ContinueDebugEvent. Keep our own handle.
        if not handle:
            raise c.WinError(c.get_last_error())
        threads[tid] = (pid, handle)
        return handle
    def suspend(tid):
        status = nt.NtSuspendThread(threads[tid][1], None) & 0xffffffff
        if status == 0xc000004b:  # SDK ntstatus.h STATUS_THREAD_IS_TERMINATING.
            emit('native_thread_terminating', pid=threads[tid][0], tid=tid)
            return False  # The kernel guarantees this thread cannot resume user code.
        if status & 0x80000000:
            raise RuntimeError(f'NtSuspendThread({tid}): NTSTATUS {status:#010x}')
        return True
    def read(pid, address, length):
        value, count = c.create_string_buffer(length), c.c_size_t()
        if not k.ReadProcessMemory(processes[pid], address, value, length, c.byref(count)) or count.value != length:
            raise c.WinError(c.get_last_error())
        return value.raw
    def write(pid, address, value):
        count = c.c_size_t()
        if not k.WriteProcessMemory(processes[pid], address, value, len(value), c.byref(count)) or count.value != len(value):
            raise c.WinError(c.get_last_error())
        if not k.FlushInstructionCache(processes[pid], address, len(value)):
            raise c.WinError(c.get_last_error())
    def context(tid):
        # winnt.h AMD64 CONTEXT: 1232 bytes, 16-byte alignment; documented
        # CONTEXT_CONTROL | CONTEXT_INTEGER. No floating/vector state is edited.
        storage = c.create_string_buffer(1248)
        address = (c.addressof(storage) + 15) & ~15
        c.c_uint32.from_address(address + 48).value = 0x00100003
        if not k.GetThreadContext(threads[tid][1], address):
            raise RuntimeError(f'GetThreadContext({tid}): {c.WinError(c.get_last_error())}')
        return storage, address
    def reg(address, offset):
        return c.c_uint64.from_address(address + offset).value
    def module_at(pid, address):
        matches = [{'path': path, 'address': address, 'rva': address - base}
                   for (owner, base), path in modules.items() if owner == pid and path
                   and base <= address < base + image_sizes.get((pid, base), 0)]
        return matches[0] if len(matches) == 1 else {'address': address, 'path': None}
    def caller(pid, registers):
        return module_at(pid, int.from_bytes(read(pid, reg(registers, 152), 8), 'little'))
    def ansi(pid, address, length=None):
        if not address:
            return ""
        if length is not None:
            if length > 8192:
                raise RuntimeError("Resolver string exceeds observation limit")
            return read(pid, address, length).decode('ascii', errors='replace')
        value = bytearray()
        for offset in range(8192):
            character = read(pid, address + offset, 1)
            if character == b'\0':
                return value.decode('ascii', errors='replace')
            value.extend(character)
        raise RuntimeError("Unterminated resolver string")
    def resume_step(pid):
        state = stepping.pop(pid)
        write(pid, state['address'], b'\xcc')
        storage, address = context(state['tid'])
        c.c_uint32.from_address(address + 68).value &= ~0x100
        if not k.SetThreadContext(threads[state['tid']][1], address):
            raise c.WinError(c.get_last_error())
        for tid in state['suspended']:
            if tid in threads:
                status = nt.NtResumeThread(threads[tid][1], None) & 0xffffffff
                if status & 0x80000000 and status != 0xc000004b:
                    raise RuntimeError(f'NtResumeThread({tid}): NTSTATUS {status:#010x}')
    def resolver(pid, tid, address, export):
        storage, registers = context(tid)
        name = ""
        if export['resolver'] == 'GetProcAddress':
            argument = reg(registers, 136)  # RDX: name pointer or ordinal
            if argument > 0xffff:
                name = ansi(pid, argument)
            else:
                name = ordinal_names.get((pid, reg(registers, 128), argument), '')
        else:
            argument = reg(registers, 136)  # RDX: ANSI_STRING* or NULL (ordinal)
            if argument:
                descriptor = read(pid, argument, 16)
                name = ansi(pid, int.from_bytes(descriptor[8:16], 'little'),
                            int.from_bytes(descriptor[:2], 'little'))
            else:
                name = ordinal_names.get((pid, reg(registers, 128), reg(registers, 184) & 0xffff), '')
        if is_gl_entrypoint(name):
            emit('native_gl_binding', pid=pid, name=name, resolver=export['resolver'], path=export['path'],
                 direct_caller=caller(pid, registers))
            return True
        # Execute the replaced instruction once. Suspend peer threads until the
        # trap is restored, so another thread cannot pass through an open hook.
        suspended = []
        for other, (owner, handle) in threads.items():
            if owner == pid and other != tid:
                if suspend(other):
                    suspended.append(other)
        stepping[pid] = {'tid': tid, 'address': address, 'suspended': suspended}
        write(pid, address, bytes([export['original_byte']]))
        c.c_uint64.from_address(registers + 248).value = address  # RIP
        c.c_uint32.from_address(registers + 68).value |= 0x100  # EFlags.TF
        if not k.SetThreadContext(threads[tid][1], registers):
            raise RuntimeError(f'SetThreadContext({tid}): {c.WinError(c.get_last_error())}')
        return False
    def image_path(handle):
        if not handle:
            return None
        try:
            text = c.create_unicode_buffer(32768)
            size = k.GetFinalPathNameByHandleW(handle, text, len(text), 0)
            if not 0 < size < len(text):
                return None
            value = text.value
            if value.startswith('\\\\?\\UNC\\'):
                value = '\\\\' + value[8:]
            elif value.startswith('\\\\?\\'):
                value = value[4:]
            return str(Path(value).resolve(strict=True))
        finally:
            k.CloseHandle(handle)
    def install(pid, base, path):
        if not path:
            errors.append({"pid": pid, "base": base, "error": "No path for loaded image"})
            return
        try:
            image = inspect_binary(Path(path))
            image_sizes[(pid, base)] = image['image_size']
            if Path(path).parent == (Path(os.environ['SystemRoot']) / 'System32') and Path(path).name.casefold() in ('ntdll.dll', 'kernelbase.dll', 'kernel32.dll'):
                addresses = sorted({item['rva'] for item in image['exports'] if not item['forwarder']})
                for export in image['exports']:
                    if export['name'] in ('NtClose', 'ZwClose', 'CloseHandle') and not export['forwarder']:
                        close_functions[(pid, base + export['rva'])] = {'path': path, 'name': export['name']}
                    if export['name'] == 'KiRaiseUserExceptionDispatcher' and not export['forwarder']:
                        end = next((value for value in addresses if value > export['rva']), image['image_size'])
                        exception_dispatchers[pid] = {'begin': base + export['rva'], 'end': base + end, 'path': path}
            for export in image['exports']:
                ordinal_names[(pid, base, export['ordinal'])] = export['name']
                symbol_resolver = export['name'] in ('GetProcAddress', 'LdrGetProcedureAddress', 'LdrGetProcedureAddressEx')
                if not is_gl_entrypoint(export['name']) and not symbol_resolver:
                    continue
                if export['forwarder']:
                    if symbol_resolver:
                        continue  # The actual target export is hooked when its image loads.
                    errors.append({"pid": pid, "path": path, "name": export['name'], "error": "Forwarded GL export is not instrumented"})
                    continue
                address = base + export['rva']
                key = (pid, address)
                if key in breakpoints:
                    breakpoints[key]['names'].append(export['name'])
                    continue
                original, count = c.c_ubyte(), c.c_size_t()
                if not k.ReadProcessMemory(processes[pid], address, c.byref(original), 1, c.byref(count)) or count.value != 1:
                    raise c.WinError(c.get_last_error())
                trap = c.c_ubyte(0xcc)
                if not k.WriteProcessMemory(processes[pid], address, c.byref(trap), 1, c.byref(count)) or count.value != 1:
                    raise c.WinError(c.get_last_error())
                if not k.FlushInstructionCache(processes[pid], address, 1):
                    raise c.WinError(c.get_last_error())
                breakpoints[key] = {"path": path, "base": base, "names": [export['name']], "original_byte": original.value}
                if symbol_resolver:
                    breakpoints[key]['resolver'] = export['name']
                    resolver_hooks.setdefault(pid, set()).add(export['name'])
        except Exception as error:
            errors.append({"pid": pid, "path": path, "error": str(error)})
    with Path(log).open('wb') as output:
        child = subprocess.Popen([str(x) for x in command], cwd=cwd, env=environment,
                                 stdout=output, stderr=subprocess.STDOUT,
                                 creationflags=0x00000001 | subprocess.CREATE_NO_WINDOW)  # DEBUG_PROCESS
        try:
            while True:
                if time.monotonic() - started > timeout and not killed:
                    errors.append({"error": "Observer timeout"})
                    for handle in list(processes.values()):
                        k.TerminateProcess(handle, 124)
                    child.kill()
                    killed = True
                if time.monotonic() - started > timeout + 10:
                    raise TimeoutError("Debuggee tree did not stop after timeout")
                event = DebugEvent()
                if not k.WaitForDebugEvent(c.byref(event), 100):
                    error = c.get_last_error()
                    if error not in (0, 121):
                        raise c.WinError(error)
                    if observed_pids and observed_pids == exited_pids:
                        break
                    continue
                status = 0x00010002  # DBG_CONTINUE
                pid = event.pid
                try:
                    if event.code == 3:  # CREATE_PROCESS_DEBUG_EVENT
                        observed_pids.add(pid)
                        data = event.data.create_process
                        owned_process = w.HANDLE()
                        if not k.DuplicateHandle(-1, data.process, -1, c.byref(owned_process), 0, False, 2):
                            raise c.WinError(c.get_last_error())
                        processes[pid] = owned_process.value
                        if data.thread:
                            retain_thread(pid, event.tid, data.thread)
                        path = image_path(data.file)
                        modules[(pid, data.base)] = path
                        emit('native_process_start', pid=pid, path=path)
                        emit('native_load', pid=pid, path=path or '', base=data.base)
                        install(pid, data.base, path)
                    elif event.code == 2:
                        if event.data.create_thread.thread:
                            handle = retain_thread(pid, event.tid, event.data.create_thread.thread)
                            if pid in stepping:
                                if suspend(event.tid):
                                    stepping[pid]['suspended'].append(event.tid)
                    elif event.code == 4:
                        thread = threads.pop(event.tid, None)
                        if thread:
                            k.CloseHandle(thread[1])
                    elif event.code == 6:  # LOAD_DLL_DEBUG_EVENT
                        data = event.data.load
                        path = image_path(data.file)
                        modules[(pid, data.base)] = path
                        emit('native_load', pid=pid, path=path or '', base=data.base)
                        install(pid, data.base, path)
                    elif event.code == 7:
                        base = event.data.unload.base
                        image_sizes.pop((pid, base), None)
                        emit('native_unload', pid=pid, path=modules.pop((pid, base), None), base=base)
                        for key in [key for key, value in breakpoints.items() if key[0] == pid and value['base'] == base]:
                            del breakpoints[key]
                        for key in [key for key in ordinal_names if key[:2] == (pid, base)]:
                            del ordinal_names[key]
                    elif event.code == 1:
                        info = event.data.exception
                        address = info.record.address
                        if killed:
                            pass  # Only drain the process tree after deliberate termination.
                        elif info.record.code == 0x80000003 and (pid, address) in breakpoints:
                            export = breakpoints[(pid, address)]
                            terminate = True
                            if export.get('resolver'):
                                try:
                                    terminate = resolver(pid, event.tid, address, export)
                                except Exception as error:
                                    errors.append({'pid': pid, 'resolver': export['resolver'], 'error': str(error)})
                            else:
                                emit('native_gl_call', pid=pid, name=export['names'][0], aliases=export['names'], path=export['path'])
                            if terminate:
                                for handle in list(processes.values()):
                                    k.TerminateProcess(handle, 86)
                                killed = True
                        elif info.record.code == 0x80000004 and pid in stepping and stepping[pid]['tid'] == event.tid:
                            resume_step(pid)
                        elif info.record.code not in (0x80000003, 0x40010006, 0x4001000a):
                            stack, unwind_error = [], None
                            if info.record.code in (0xc0000008, 0xc0000235) and info.first_chance:
                                try:
                                    if unwinder is None:
                                        from .windows_stack import Unwinder
                                        unwinder = Unwinder()
                                    storage, registers = context(event.tid)
                                    for frame in unwinder.frames(processes[pid], threads[event.tid][1], registers):
                                        frame['module'] = module_at(pid, frame['address'])
                                        frame['close_function'] = close_functions.get((pid, frame['function_begin']))
                                        stack.append(frame)
                                except Exception as error:
                                    unwind_error = str(error)
                            emit('native_exception', pid=pid, tid=event.tid, code=hex(info.record.code),
                                 first_chance=bool(info.first_chance), location=module_at(pid, address),
                                 stack=stack, unwind_error=unwind_error)
                            dispatcher = exception_dispatchers.get(pid, {})
                            matching_close = [frame['close_function'] for frame in stack[:4] if frame['close_function']]
                            if ((handle_proof or _handle_control) and info.first_chance and info.record.code in (0xc0000008, 0xc0000235)
                                    and dispatcher.get('begin', 0) <= address < dispatcher.get('end', 0)
                                    and matching_close and not unwind_error):
                                emit('native_debugger_closehandle_return', pid=pid, code=hex(info.record.code),
                                     source=matching_close, baseline=handle_proof or 'INDEPENDENT_CONTROL_ONLY',
                                     semantics='Documented debugger-only exception; resume OS CloseHandle FALSE/ERROR_INVALID_HANDLE behavior')
                            else:
                                status = 0x80010001  # DBG_EXCEPTION_NOT_HANDLED
                    elif event.code == 5:  # EXIT_PROCESS_DEBUG_EVENT
                        emit('native_process_exit', pid=pid, exit_code=event.data.exit_process.code)
                        exited_pids.add(pid)
                        stepping.pop(pid, None)
                        for tid in [tid for tid, (owner, _) in threads.items() if owner == pid]:
                            k.CloseHandle(threads.pop(tid)[1])
                        handle = processes.pop(pid, None)
                        if handle:
                            if unwinder is not None:
                                unwinder.close(handle)
                            k.CloseHandle(handle)
                finally:
                    if not k.ContinueDebugEvent(pid, event.tid, status):
                        raise c.WinError(c.get_last_error())
                if observed_pids and observed_pids == exited_pids:
                    break
            code = child.wait(timeout=10)
        finally:
            if child.poll() is None:
                for handle in processes.values():
                    k.TerminateProcess(handle, 125)
                child.kill()
                child.wait(timeout=10)
            for handle in processes.values():
                if unwinder is not None:
                    unwinder.close(handle)
                k.CloseHandle(handle)
            for _, handle in threads.values():
                k.CloseHandle(handle)
    return {"events": events, "process_exit": code, "root_pid": child.pid,
            "coverage": {"startup_and_transient_native_loads": not errors and observed_pids == exited_pids,
                         "native_public_gl_export_breakpoints": not errors,
                         "native_entrypoint_resolution": not errors and all(
                             {'GetProcAddress', 'LdrGetProcedureAddress'}.issubset(resolver_hooks.get(pid, set()))
                             for pid in observed_pids),
                         "process_tree": observed_pids == exited_pids,
                         "private_or_statically_linked_gl_implementations": False},
            "scope": "Windows x64 OS debugger loads, public GL export traps and GetProcAddress/LdrGetProcedureAddress[Ex] lookups; no claim about private driver implementation internals or manually parsed exports.",
            "closehandle_fidelity_baseline": handle_proof,
            "errors": errors, "observed_pids": sorted(observed_pids), "exited_pids": sorted(exited_pids)}
