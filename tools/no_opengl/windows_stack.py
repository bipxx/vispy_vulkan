"""Read-only x64 unwind frames using Windows' local PE unwind information."""
from __future__ import annotations


class Unwinder:
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        class Address(c.Structure):
            _fields_ = [('offset', c.c_uint64), ('segment', w.WORD), ('mode', w.DWORD)]
        class KernelHelp(c.Structure):
            _fields_ = [('thread', c.c_uint64), ('callback_stack', w.DWORD), ('callback_store', w.DWORD),
                        ('next_callback', w.DWORD), ('frame_pointer', w.DWORD),
                        ('call_user', c.c_uint64), ('callback_dispatcher', c.c_uint64), ('system_start', c.c_uint64),
                        ('exception_dispatcher', c.c_uint64), ('stack_base', c.c_uint64), ('stack_limit', c.c_uint64),
                        ('build', w.DWORD), ('retpoline_table_size', w.DWORD), ('retpoline_table', c.c_uint64),
                        ('retpoline_offset', w.DWORD), ('retpoline_size', w.DWORD), ('reserved', c.c_uint64 * 2)]
        class Frame(c.Structure):
            _fields_ = [('pc', Address), ('return_address', Address), ('frame', Address), ('stack', Address),
                        ('store', Address), ('function', c.c_void_p), ('parameters', c.c_uint64 * 4),
                        ('far', w.BOOL), ('virtual', w.BOOL), ('reserved', c.c_uint64 * 3), ('kernel', KernelHelp)]
        self.Frame = Frame
        self.api = c.WinDLL('dbghelp', use_last_error=True)
        self.api.SymSetOptions.argtypes = [w.DWORD]
        self.api.SymSetOptions.restype = w.DWORD
        self.api.SymInitializeW.argtypes = [w.HANDLE, w.LPCWSTR, w.BOOL]
        self.api.SymInitializeW.restype = w.BOOL
        self.api.SymCleanup.argtypes = [w.HANDLE]
        self.api.SymCleanup.restype = w.BOOL
        self.api.SymFunctionTableAccess64.argtypes = [w.HANDLE, c.c_uint64]
        self.api.SymFunctionTableAccess64.restype = c.c_void_p
        self.api.SymGetModuleBase64.argtypes = [w.HANDLE, c.c_uint64]
        self.api.SymGetModuleBase64.restype = c.c_uint64
        self.api.StackWalk64.argtypes = [w.DWORD, w.HANDLE, w.HANDLE, c.POINTER(Frame), c.c_void_p,
                                         c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p]
        self.api.StackWalk64.restype = w.BOOL
        # Local public PE metadata only; never use symbol servers or prompts.
        self.api.SymSetOptions(0x4 | 0x200 | 0x1000 | 0x4000 | 0x10000 | 0x80000)
        self.processes = set()

    def frames(self, process, thread, context, limit=16):
        c = self.c
        if process not in self.processes:
            if not self.api.SymInitializeW(process, '', True):
                raise c.WinError(c.get_last_error())
            self.processes.add(process)
        frame = self.Frame()
        frame.pc.offset = c.c_uint64.from_address(context + 248).value
        frame.frame.offset = c.c_uint64.from_address(context + 160).value
        frame.stack.offset = c.c_uint64.from_address(context + 152).value
        frame.pc.mode = frame.frame.mode = frame.stack.mode = 3  # AddrModeFlat.
        result = []
        for _ in range(limit):
            if not self.api.StackWalk64(0x8664, process, thread, c.byref(frame), context, None,
                                       c.cast(self.api.SymFunctionTableAccess64, c.c_void_p),
                                       c.cast(self.api.SymGetModuleBase64, c.c_void_p), None):
                break
            if not frame.pc.offset or (result and result[-1]['address'] == frame.pc.offset):
                break
            base = self.api.SymGetModuleBase64(process, frame.pc.offset)
            entry = self.api.SymFunctionTableAccess64(process, frame.pc.offset)
            begin = c.c_uint32.from_address(entry).value if entry else None
            result.append({'address': frame.pc.offset, 'module_base': base,
                           'function_begin': base + begin if base and begin is not None else None})
        return result

    def close(self, process):
        if process in self.processes:
            self.api.SymCleanup(process)
            self.processes.remove(process)
