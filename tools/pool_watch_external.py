# SPDX-License-Identifier: AGPL-3.0-only
"""R1 instrumentation, from outside the watched processes (D20): record when one loses its default thread pool.

tools/pool_watch.py watches from a thread inside the process. In CPython 3.12 a scheduled garbage collection runs in
whichever thread next executes bytecode, so that thread can run other threads' finalizers: it crashed three of three
Tk test runs (run b19-readback-257). This watcher runs in its own process. It opens each watched process with
PROCESS_QUERY_INFORMATION | SYNCHRONIZE and reads its handle table (NtQueryInformationProcess,
ProcessHandleInformation), which takes microseconds; it opens, duplicates or closes no handle in a watched process,
and nothing runs inside one.

In launch mode the command starts suspended, is assigned to a new job object without limits, and is resumed, so the
job lists every process the command creates: launchers such as a virtual environment's python.exe start the real
interpreter as a child. Failed process opening, job setup or resume terminates and waits for the owned child;
launch never falls back to an untracked process tree. (Enumerating all processes instead costs 35-45 ms per look
on this desktop.) Each new job
member is adopted and recorded with its parent and executable name. Attach mode (--pid) watches that process only.
For each process the watcher finds the lowest TpWorkerFactory handle (the default pool's, as tools/pool_watch.py does)
and re-reads the table every --interval seconds. When that handle value is gone or names another object type, it
appends one JSON event with the time since launch or attach, the process, the handle, what the value now names
('closed' or a type name) and the remaining worker factories, and keeps watching. A process that never had a worker
factory is recorded as such. In launch mode the watcher keeps watching until every job member has exited, then
records the root's exit, with the watcher's own CPU time, and exits with the root's code. The type of each index is
learnt from the watcher's own handles; an index it holds no handle of is recorded as a number. A close followed by
reuse for another worker factory between two reads is not seen.
Usage (Windows):
  pool_watch_external.py --output events.jsonl [--interval 0.005] -- <command>...   launch and watch
  pool_watch_external.py --output events.jsonl --pid <pid>                          watch a running process
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
import time

PROCESS_HANDLE_INFORMATION = 51
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
STATUS_PROCESS_IS_TERMINATING = 0xC000010A
HEADER_BYTES = 16
# PROCESS_HANDLE_TABLE_ENTRY_INFO on x64: HandleValue, HandleCount, PointerCount, GrantedAccess, ObjectTypeIndex,
# HandleAttributes, Reserved.
ENTRY = struct.Struct('<QQQIIII')


def decode(raw):
    """(handle value, object type index) of every entry of a PROCESS_HANDLE_SNAPSHOT_INFORMATION buffer.

    The entries are read as 64-bit little-endian words, five per entry: the handle value is the first, and the type
    index is the high half of the fourth (after GrantedAccess). Slicing keeps the per-read cost out of Python loops."""
    count = int.from_bytes(raw[:8], 'little')
    end = HEADER_BYTES + count * ENTRY.size
    if end > len(raw):
        raise ValueError('handle snapshot holds %d entries but only %d bytes' % (count, len(raw)))
    words = memoryview(bytes(raw[HEADER_BYTES:end])).cast('Q')
    return list(zip(words[0::5].tolist(), [word >> 32 for word in words[3::5].tolist()]))


def factories(entries, factory_type):
    return sorted(handle for handle, kind in entries if kind == factory_type)


def check(entries, watched, factory_type, names):
    """What the watched handle value names now: None while it is still a worker factory."""
    kind = dict(entries).get(watched)
    if kind is None:
        return 'closed'
    if kind == factory_type:
        return None
    return names.get(kind, kind)


class Windows:
    """The few native calls the watcher needs; nothing here touches a watched process's handles."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.wintypes = ctypes, wintypes
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.ntdll = ctypes.WinDLL('ntdll')
        k, n = self.kernel32, self.ntdll
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                                ctypes.c_void_p]
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
        n.NtResumeProcess.argtypes = [wintypes.HANDLE]
        n.NtResumeProcess.restype = ctypes.c_long
        n.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_ulong, ctypes.c_void_p, wintypes.ULONG,
                                                ctypes.POINTER(wintypes.ULONG)]
        n.NtQueryInformationProcess.restype = ctypes.c_long
        n.NtQueryObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                                    ctypes.POINTER(wintypes.ULONG)]
        n.NtQueryObject.restype = ctypes.c_long
        self.buffer = ctypes.create_string_buffer(1 << 16)
        self.returned = wintypes.ULONG()
        self.job, self.job_buffer = None, ctypes.create_string_buffer(8 + 8 * 4096)

    def launch(self, command):
        """Start the command suspended, assign it to a new job object, and resume it; return the Popen."""
        child = subprocess.Popen(command, creationflags=0x00000004)  # CREATE_SUSPENDED
        process, job = None, None
        try:
            # SET_QUOTA|TERMINATE|SUSPEND_RESUME: establish tracking before the child runs.
            process = self.kernel32.OpenProcess(0x0100 | 0x0001 | 0x0800, False, child.pid)
            if not process:
                raise OSError('cannot open the launched process %d (error %d)' %
                              (child.pid, self.ctypes.get_last_error()))
            job = self.kernel32.CreateJobObjectW(None, None)
            if not job:
                raise OSError('CreateJobObjectW failed (error %d)' % self.ctypes.get_last_error())
            if not self.kernel32.AssignProcessToJobObject(job, process):
                raise OSError('AssignProcessToJobObject failed (error %d)' % self.ctypes.get_last_error())
            status = self.ntdll.NtResumeProcess(process)
            if status < 0:
                raise OSError('NtResumeProcess failed: 0x%08x' % (status & 0xFFFFFFFF))
            self.job, job = job, None
            return child
        except BaseException:
            try:
                child.kill()
            finally:
                child.wait()
            raise
        finally:
            if process:
                self.kernel32.CloseHandle(process)
            if job:
                self.kernel32.CloseHandle(job)

    def members(self):
        """Pids of every process in the job (JobObjectBasicProcessIdList), or [] without a job."""
        if self.job is None:
            return []
        if not self.kernel32.QueryInformationJobObject(self.job, 3, self.job_buffer, len(self.job_buffer), None):
            return []
        listed = int.from_bytes(self.job_buffer.raw[4:8], 'little')
        words = memoryview(self.job_buffer.raw[8:8 + 8 * listed]).cast('Q')
        return words.tolist()

    def open(self, pid):
        """A handle to the process, or None when it is already gone."""
        return self.kernel32.OpenProcess(0x0400 | 0x00100000, False, pid) or None  # QUERY_INFORMATION | SYNCHRONIZE

    def close(self, process):
        self.kernel32.CloseHandle(process)

    def describe(self, process):
        """(parent pid, executable name) of an opened process."""
        basic = (self.ctypes.c_uint64 * 6)()  # PROCESS_BASIC_INFORMATION; the parent is its last field
        parent = None
        if self.ntdll.NtQueryInformationProcess(process, 0, basic, self.ctypes.sizeof(basic), None) >= 0:
            parent = basic[5]
        name, size = self.ctypes.create_unicode_buffer(1024), self.wintypes.DWORD(1024)
        if not self.kernel32.QueryFullProcessImageNameW(process, 0, name, self.ctypes.byref(size)):
            return parent, None
        return parent, os.path.basename(name.value)

    def snapshot(self, process):
        """The process's (handle, type) entries, or None once it is terminating."""
        while True:
            status = self.ntdll.NtQueryInformationProcess(process, PROCESS_HANDLE_INFORMATION, self.buffer,
                                                          len(self.buffer), self.ctypes.byref(self.returned))
            status &= 0xFFFFFFFF
            if status != STATUS_INFO_LENGTH_MISMATCH:
                break
            self.buffer = self.ctypes.create_string_buffer(max(2 * len(self.buffer), self.returned.value + 4096))
        if status == STATUS_PROCESS_IS_TERMINATING:
            return None
        if status:
            raise OSError('NtQueryInformationProcess(ProcessHandleInformation) failed: 0x%08x' % status)
        return decode(self.ctypes.string_at(self.buffer, max(self.returned.value, HEADER_BYTES)))

    def exited(self, process):
        return self.kernel32.WaitForSingleObject(process, 0) == 0

    def type_names(self):
        """Type index -> name, from this process's own handles (NtQueryObject on its own handles only)."""
        names, buffer = {}, self.ctypes.create_string_buffer(1024)
        for handle, kind in self.snapshot(self.ctypes.c_void_p(-1)):  # the current-process pseudo-handle
            if kind in names:
                continue
            if self.ntdll.NtQueryObject(self.wintypes.HANDLE(handle), 2, buffer, 1024, None) >= 0:
                length = self.ctypes.c_ushort.from_buffer(buffer, 0).value
                names[kind] = self.ctypes.wstring_at(self.ctypes.c_void_p.from_buffer(buffer, 8).value, length // 2)
        return names


def watch(api, root, record, interval, began):
    """Watch the root process and every later job member until all have exited; return the losses recorded."""
    seconds = lambda: round(time.perf_counter() - began, 4)
    names = api.type_names()
    factory_type = next((index for index, name in names.items() if name == 'TpWorkerFactory'), None)
    if factory_type is None:
        record(event='no_own_worker_factory', pid=root, seconds=seconds())
        return 0
    targets, family, losses = {}, set(), 0

    def adopt(pid, root_process=False):
        family.add(pid)
        process = api.open(pid)
        if process is None:
            record(event='not_found', pid=pid, seconds=seconds())
            return
        targets[pid] = {'process': process, 'watched': None, 'found': False}
        if not root_process:
            parent, name = api.describe(process)
            record(event='adopted', pid=pid, parent=parent, name=name, seconds=seconds())

    adopt(root, root_process=True)
    while targets:
        for pid in api.members():
            if pid not in family:
                adopt(pid)
        for pid, target in list(targets.items()):
            entries = api.snapshot(target['process'])
            if entries is None or api.exited(target['process']):  # a read during or after exit says nothing
                if not target['found']:
                    record(event='no_worker_factory', pid=pid, seconds=seconds())
                api.close(target['process'])
                del targets[pid]
                continue
            if target['watched'] is None:
                found = factories(entries, factory_type)
                if found:
                    target['watched'], target['found'] = found[0], True
                    record(event='watching', pid=pid, seconds=seconds(), handle=found[0], factories=found,
                           factory_type=factory_type)
                continue
            now = check(entries, target['watched'], factory_type, names)
            if now is not None:
                losses += 1
                record(event='default_pool_lost', pid=pid, seconds=seconds(), handle=target['watched'], now=now,
                       factories=factories(entries, factory_type))
                target['watched'] = None  # a later lowest factory is reported as the next one watched
        if targets:
            time.sleep(interval)
    return losses


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', required=True)
    parser.add_argument('--interval', type=float, default=0.005)
    parser.add_argument('--pid', type=int)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if bool(command) == (args.pid is not None):
        parser.error('give a command after -- or --pid, not both')
    if command and os.path.exists(command[0]):  # CreateProcess does not resolve a relative path written with '/'
        command = [os.path.abspath(command[0]), *command[1:]]

    def record(**fields):
        with open(args.output, 'a', encoding='utf-8') as output:
            output.write(json.dumps(fields) + '\n')

    began = time.perf_counter()
    if sys.platform != 'win32':
        child = subprocess.Popen(command) if command else None
        record(event='unsupported_platform', platform=sys.platform, pid=child.pid if child else args.pid)
        return child.wait() if child else 0
    api = Windows()
    child = api.launch(command) if command else None
    watch(api, child.pid if child else args.pid, record, args.interval, began)
    if child is None:
        return 0
    code = child.wait()
    record(event='target_exit', pid=child.pid, seconds=round(time.perf_counter() - began, 4), returncode=code,
           child_waited=True, watcher_cpu_seconds=round(time.process_time(), 3))
    return code


if __name__ == '__main__':
    sys.exit(main())
