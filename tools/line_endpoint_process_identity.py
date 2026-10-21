"""Stdlib process-image observations and strict one-edge PID admission.

This source is embedded verbatim in the qualification plugin. Importing it
does not inspect a process or import a renderer.
"""
import hashlib
import os
from pathlib import Path
import re
import sys


def _identity_require(condition, message):
    if not condition:
        raise ValueError(message)


def _identity_pid(value):
    _identity_require(type(value) is int and 0 < value <= 0xFFFFFFFF, "Positive DWORD process ID required")
    return value


def _identity_path(value):
    _identity_require(isinstance(value, str) and bool(value) and Path(value).is_absolute(), "Absolute executable image path required")
    return os.path.normcase(str(Path(value).resolve()))


def _identity_image(path):
    path = Path(path).resolve()
    _identity_require(path.is_file(), "Executable image does not exist")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _identity_windows_api():
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcessId.argtypes = []
    kernel.GetCurrentProcessId.restype = wintypes.DWORD
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetModuleFileNameW.restype = wintypes.DWORD
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return ctypes, wintypes, kernel


def _identity_windows_self_image():
    ctypes, _, kernel = _identity_windows_api()
    text = ctypes.create_unicode_buffer(32768)
    size = kernel.GetModuleFileNameW(None, text, len(text))
    if not size:
        raise ctypes.WinError(ctypes.get_last_error())
    _identity_require(size < len(text), "Self executable image path truncated")
    return _identity_image(text.value), int(kernel.GetCurrentProcessId())


def observe_windows_process_image(pid):
    """Open only for query, obtain the actual image, and always close the HANDLE."""
    pid = _identity_pid(pid)
    ctypes, wintypes, kernel = _identity_windows_api()
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        text = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(text))
        if not kernel.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        _identity_require(0 < size.value < len(text), "Observed executable image path truncated")
        return _identity_image(text.value)
    finally:
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())


def observe_process_identity():
    """Collect actual OS/self/parent identity before the test imports graphics."""
    python_pid, parent_pid = _identity_pid(os.getpid()), _identity_pid(os.getppid())
    if os.name == "nt":
        self_image, actual_pid = _identity_windows_self_image()
        _identity_require(actual_pid == python_pid, "Windows OS PID and Python PID differ")
        parent_image = observe_windows_process_image(parent_pid)
    else:
        actual_pid, self_image, parent_image = python_pid, _identity_image(sys.executable), None
    return {"schema": 1, "platform": os.name, "pid": actual_pid, "python_pid": python_pid,
            "parent_pid": parent_pid, "self_image": self_image, "parent_image": parent_image,
            "sys_executable": str(Path(sys.executable).resolve()),
            "base_executable": _identity_image(sys._base_executable),
            "version": sys.version, "cache_tag": sys.implementation.cache_tag}


def freeze_python_identity():
    """Pin redirector and real ABI image independently of repository membership."""
    if os.name == "nt":
        real, pid = _identity_windows_self_image()
        _identity_require(pid == os.getpid(), "Windows freeze PID differs")
    else:
        real = _identity_image(sys.executable)
    base = _identity_image(sys._base_executable)
    if os.name == "nt":
        _identity_require(_identity_path(real["path"]) == _identity_path(base["path"]) and real["sha256"] == base["sha256"], "Windows actual image differs from Python base image")
    return {"schema": 1, "platform": os.name, "launched_interpreter": _identity_image(sys.executable),
            "real_python_image": real, "base_executable": base,
            "version": sys.version, "cache_tag": sys.implementation.cache_tag}


def _identity_match_image(observed, expected, label):
    _identity_require(type(observed) is dict and type(expected) is dict and set(observed) == set(expected) == {"path", "sha256"}, label + " image schema differs")
    for image in (observed, expected):
        _identity_require(isinstance(image["sha256"], str) and re.fullmatch("[0-9a-f]{64}", image["sha256"]) is not None, label + " image SHA256 absent")
    _identity_require(_identity_path(observed["path"]) == _identity_path(expected["path"]) and observed["sha256"] == expected["sha256"], label + " executable image identity differs")


def validate_process_identity(record, frozen, expected_pid):
    """Accept PID equality or exactly one proven Windows redirector edge."""
    expected_pid = _identity_pid(expected_pid)
    _identity_require(type(frozen) is dict and type(frozen.get("schema")) is int and frozen["schema"] == 1 and frozen.get("platform") in ("nt", "posix"), "Frozen Python identity schema/platform invalid")
    identity = record.get("process_identity")
    _identity_require(type(identity) is dict and type(identity.get("schema")) is int and identity["schema"] == 1 and not record.get("process_identity_error"), "Actual process identity observation missing or failed")
    pid, parent_pid = _identity_pid(identity["pid"]), _identity_pid(identity["parent_pid"])
    _identity_require(type(record.get("pid")) is int and type(identity.get("python_pid")) is int and record["pid"] == pid == identity["python_pid"], "Actual OS/Python/record PID differs")
    _identity_require(pid != parent_pid and identity["platform"] == frozen["platform"], "Actual parent/platform differs")
    _identity_require(identity["version"] == record["version"] == frozen["version"] and identity["cache_tag"] == frozen["cache_tag"], "Actual Python ABI version differs")
    _identity_require(_identity_path(identity["sys_executable"]) == _identity_path(record["executable"]) == _identity_path(frozen["launched_interpreter"]["path"]), "Original sys.executable differs")
    _identity_match_image(identity["self_image"], frozen["real_python_image"], "Self")
    _identity_match_image(identity["base_executable"], frozen["base_executable"], "Base Python")
    if frozen["platform"] == "nt":
        _identity_match_image(identity["parent_image"], identity["parent_image"], "Observed parent")
    else:
        _identity_require(identity["parent_image"] is None, "Non-Windows parent image is not observed")
    if pid == expected_pid:
        mode = "direct_pid"
    else:
        _identity_require(frozen["platform"] == "nt" and parent_pid == expected_pid, "PID differs without one-edge Windows delegation")
        _identity_match_image(identity["parent_image"], frozen["launched_interpreter"], "Redirector parent")
        mode = "windows_one_edge_redirector"
    return {"mode": mode, "launched_pid": expected_pid, "actual_pid": pid, "actual_parent_pid": parent_pid,
            "actual_self_image": identity["self_image"], "actual_parent_image": identity["parent_image"]}
