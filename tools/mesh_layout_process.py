# SPDX-License-Identifier: AGPL-3.0-only
"""Consumer process termination and loaded native-image provenance observations."""
import ctypes
import hashlib
import os
from pathlib import Path
import sys


def normalized_path(path):
    text=str(path)
    if os.name=='nt' and text.startswith('\\\\?\\'):
        text=text[4:]
        if text.startswith('UNC\\'):text='\\\\'+text[4:]
    return os.path.normcase(os.path.abspath(os.path.normpath(text)))


def _kernel():
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.argtypes=[];kernel.GetCurrentProcess.restype=w.HANDLE
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
    kernel.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
    kernel.GetProcessTimes.restype=w.BOOL
    kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.WaitForSingleObject.restype=w.DWORD
    return kernel,w


def _creation_time(kernel,w,handle):
    values=[w.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle,*(ctypes.byref(v) for v in values)):
        raise ctypes.WinError(ctypes.get_last_error())
    return (int(values[0].dwHighDateTime)<<32)|int(values[0].dwLowDateTime)


def process_stamp():
    creation=None
    if os.name=='nt':
        kernel,w=_kernel();creation=_creation_time(kernel,w,kernel.GetCurrentProcess())
    return dict(pid=os.getpid(),parent_pid=os.getppid(),windows_creation_time=creation)


def worker_terminal(worker,launched_pid):
    """A direct wait, or one Windows launcher hop with creation-time observation."""
    stamp=worker['process_stamp']
    assert stamp['pid']==worker['pid'] and type(stamp['pid']) is int and stamp['pid']>0
    if worker['pid']==launched_pid:return dict(terminal=True,mode='direct_process_wait')
    assert os.name=='nt' and stamp['parent_pid']==launched_pid, 'No observed single Windows launcher edge'
    kernel,w=_kernel()
    handle=kernel.OpenProcess(0x00100000|0x1000,False,worker['pid'])
    if not handle:
        error=ctypes.get_last_error()
        if error==87:return dict(terminal=True,mode='windows_worker_already_absent',error=error)
        raise ctypes.WinError(error)
    try:
        creation=_creation_time(kernel,w,handle)
        assert type(stamp['windows_creation_time']) is int and stamp['windows_creation_time']>0
        if creation!=stamp['windows_creation_time']:
            return dict(terminal=True,mode='original_worker_pid_reused',observed_creation_time=creation)
        waited=int(kernel.WaitForSingleObject(handle,10000))
        if waited not in (0,258):raise ctypes.WinError(ctypes.get_last_error())
        return dict(terminal=waited==0,mode='windows_creation_bound_worker_wait',wait_result=waited)
    finally:
        if not kernel.CloseHandle(handle):raise ctypes.WinError(ctypes.get_last_error())


def _native_paths():
    if os.name=='nt':
        from ctypes import wintypes as w
        kernel,_=_kernel();handle=kernel.GetCurrentProcess()
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        psapi.EnumProcessModulesEx.argtypes=[w.HANDLE,ctypes.POINTER(w.HMODULE),w.DWORD,ctypes.POINTER(w.DWORD),w.DWORD]
        psapi.EnumProcessModulesEx.restype=w.BOOL
        psapi.GetModuleFileNameExW.argtypes=[w.HANDLE,w.HMODULE,w.LPWSTR,w.DWORD]
        psapi.GetModuleFileNameExW.restype=w.DWORD
        count=1024
        while True:
            modules=(w.HMODULE*count)();needed=w.DWORD()
            if not psapi.EnumProcessModulesEx(handle,modules,ctypes.sizeof(modules),ctypes.byref(needed),3):
                raise ctypes.WinError(ctypes.get_last_error())
            if needed.value<=ctypes.sizeof(modules):break
            count=(needed.value+ctypes.sizeof(w.HMODULE)-1)//ctypes.sizeof(w.HMODULE)
        paths=[]
        for module in modules[:needed.value//ctypes.sizeof(w.HMODULE)]:
            text=ctypes.create_unicode_buffer(32768)
            written=psapi.GetModuleFileNameExW(handle,module,text,len(text))
            if not written or written>=len(text):raise ctypes.WinError(ctypes.get_last_error())
            paths.append(text.value)
        return paths
    if sys.platform=='darwin':
        library=ctypes.CDLL(None)
        library._dyld_image_count.argtypes=[];library._dyld_image_count.restype=ctypes.c_uint32
        library._dyld_get_image_name.argtypes=[ctypes.c_uint32];library._dyld_get_image_name.restype=ctypes.c_char_p
        paths=[]
        for index in range(library._dyld_image_count()):
            name=library._dyld_get_image_name(index)
            if not name:raise RuntimeError('dyld image inventory changed during observation')
            paths.append(os.fsdecode(name))
        return paths
    if sys.platform.startswith('linux'):
        paths=[]
        for line in Path('/proc/self/maps').read_text().splitlines():
            fields=line.split(maxsplit=5)
            if len(fields)==6 and 'x' in fields[1] and fields[5].startswith('/'):
                paths.append(fields[5].replace('\\040',' '))
        return paths
    raise RuntimeError('Native module inventory is not implemented on this platform')


def native_modules(excluded_roots):
    roots=[Path(normalized_path(root)) for root in excluded_roots]
    result=[]
    for name in sorted({normalized_path(path) for path in _native_paths()}):
        record=dict(path=name,sha256=None,excluded_root=any(Path(name).is_relative_to(root) for root in roots))
        # Reject repository images by path before opening any excluded payload.
        if not record['excluded_root']:
            try:
                digest=hashlib.sha256()
                with Path(name).open('rb') as stream:
                    for part in iter(lambda:stream.read(1024*1024),b''):digest.update(part)
                record['sha256']=digest.hexdigest()
            except OSError as error:record['hash_error']=str(error)
        result.append(record)
    assert result, 'Native module inventory is empty'
    return result


def assert_wheel_module_origins(records,package,package_hashes,required_modules):
    package=Path(normalized_path(package))
    expected={normalized_path(package/Path(name).relative_to('vispy')):digest for name,digest in package_hashes.items()}
    observed={record['path']:record for record in records}
    assert {normalized_path(path) for path in required_modules}<=set(observed), 'Compiled module absent from native inventory'
    for record in records:
        assert not record['excluded_root'], f'Repository native image loaded: {record["path"]}'
        path=Path(record['path'])
        if path.is_relative_to(package) or 'vispy_submit' in path.name.lower():
            assert record['path'] in expected, f'Native VisPy image is not a supplied-wheel member: {path}'
            assert record['sha256']==expected[record['path']], f'Loaded wheel image bytes differ: {path}'
