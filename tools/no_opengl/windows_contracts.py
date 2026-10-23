"""Evidence for unavailable delayed imports from installed Windows OS files."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import struct
import sys
from functools import lru_cache


@lru_cache(maxsize=None)
def os_file_version(path):
    import ctypes as c
    from ctypes import wintypes as w
    api = c.WinDLL('version', use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [w.LPCWSTR, c.POINTER(w.DWORD)]
    api.GetFileVersionInfoSizeW.restype = w.DWORD
    api.GetFileVersionInfoW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p]
    api.GetFileVersionInfoW.restype = w.BOOL
    api.VerQueryValueW.argtypes = [c.c_void_p, w.LPCWSTR, c.POINTER(c.c_void_p), c.POINTER(w.UINT)]
    api.VerQueryValueW.restype = w.BOOL
    unused = w.DWORD()
    size = api.GetFileVersionInfoSizeW(str(path), c.byref(unused))
    if not size:
        return None
    data = c.create_string_buffer(size)
    if not api.GetFileVersionInfoW(str(path), 0, size, data):
        return None
    address, length = c.c_void_p(), w.UINT()
    if not api.VerQueryValueW(data, '\\VarFileInfo\\Translation', c.byref(address), c.byref(length)) or length.value < 4:
        return None
    language, codepage = struct.unpack('<HH', c.string_at(address, 4))
    result = {}
    for field in ('CompanyName', 'OriginalFilename', 'FileVersion', 'ProductName'):
        query = f'\\StringFileInfo\\{language:04x}{codepage:04x}\\{field}'
        if api.VerQueryValueW(data, query, c.byref(address), c.byref(length)):
            result[field] = c.wstring_at(address, max(0, length.value - 1))
    return result


def parse_namespace(data):
    if len(data) < 28:
        raise ValueError('Truncated API-set namespace')
    version, size, flags, count, entries, hashes, factor = struct.unpack_from('<7I', data)
    if version != 6 or size != len(data) or entries + count * 24 > size:
        raise ValueError('Unsupported API-set namespace')
    def string(offset, length):
        if offset + length > size or length % 2:
            raise ValueError('Invalid API-set string range')
        return data[offset:offset + length].decode('utf-16-le')
    result = {}
    for index in range(count):
        flags, offset, length, hashed_length, values, value_count = struct.unpack_from('<6I', data, entries + index * 24)
        name = string(offset, length).casefold() + '.dll'
        if values + value_count * 20 > size:
            raise ValueError('Invalid API-set value range')
        hosts = []
        for item in range(value_count):
            flags, alias, alias_length, host, host_length = struct.unpack_from('<5I', data, values + item * 20)
            hosts.append({'alias': string(alias, alias_length), 'host': string(host, host_length)})
        result[name] = hosts
    return result


def namespace():
    if sys.platform != 'win32':
        return None
    import ctypes as c
    if c.sizeof(c.c_void_p) != 8 or sys.getwindowsversion().major < 10:
        raise RuntimeError('API-set evidence requires Windows 10+ x64')
    nt = c.WinDLL('ntdll')
    nt.RtlGetCurrentPeb.restype = c.c_void_p
    peb = nt.RtlGetCurrentPeb()
    # Windows x64 PEB ApiSetMap offset. Reject unknown namespace versions/sizes;
    # never turn a layout/version mismatch into an absent-contract claim.
    address = c.c_void_p.from_address(peb + 0x68).value
    header = c.string_at(address, 28)
    version, size = struct.unpack_from('<II', header)
    if version != 6 or not 28 <= size <= 16 * 1024 * 1024:
        raise RuntimeError('Unsupported live API-set namespace')
    data = c.string_at(address, size)
    return {'version': version, 'sha256': hashlib.sha256(data).hexdigest(),
            'contracts': parse_namespace(data), 'os_version': str(sys.getwindowsversion())}


def absent_os_delay(edge, *, binaries, runtime_paths, api_namespace):
    """Classify an actual OS delay edge, never arbitrary candidate imports.

    Raw closure still stays unresolved. This evidence supports only the selected
    candidate installation boundary plus a successful traced functional flow.
    """
    if sys.platform != 'win32' or not edge.get('delay') or edge.get('resolved') or not api_namespace:
        return None
    parent = Path(edge['parent']).resolve()
    system = (Path(os.environ['SystemRoot']) / 'System32').resolve()
    if parent.parent != system or not parent.is_file():
        return None
    version = os_file_version(str(parent))
    if not version or version.get('CompanyName') != 'Microsoft Corporation' or not version.get('ProductName'):
        return None
    name = edge['name']
    if any(Path(path).name.casefold() == name.casefold() for path in runtime_paths):
        return None
    if (system / name).exists():
        return None
    import ctypes as c
    from ctypes import wintypes as w
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [w.LPCWSTR, w.HANDLE, w.DWORD]
    kernel.LoadLibraryExW.restype = w.HMODULE
    kernel.FreeLibrary.argtypes = [w.HMODULE]
    c.set_last_error(0)
    handle = kernel.LoadLibraryExW(name, None, 0x00000001 | 0x00000800)
    failure = c.get_last_error()
    if handle:
        kernel.FreeLibrary(handle)
        return None
    if failure != 126:
        return None
    contracts = api_namespace['contracts']
    is_contract = name.casefold().startswith(('api-', 'ext-'))
    hosts = contracts.get(name.casefold())
    absent_hosts = []
    if is_contract and hosts:
        for value in hosts:
            host = value['host']
            if not host:
                continue
            if (system / host).exists():
                return None
            c.set_last_error(0)
            target = kernel.LoadLibraryExW(host, None, 0x00000001 | 0x00000800)
            host_failure = c.get_last_error()
            if target:
                kernel.FreeLibrary(target)
                return None
            if host_failure != 126:
                return None
            absent_hosts.append({'name': host, 'system_directory_file_exists': False, 'actual_os_resolver_error': host_failure})
    matches = [item for item in binaries if Path(item['path']).resolve() == parent]
    if len(matches) != 1:
        return None
    return {**edge, 'classification': 'unavailable-delayed-Windows-platform-component',
            'parent_os_binary_sha256': matches[0]['sha256'], 'system_directory': str(system),
            'parent_os_version_resource': version,
            'actual_os_resolver_error': failure, 'api_set_contract': is_contract,
            'api_set_mapping': hosts, 'api_set_namespace_sha256': api_namespace['sha256'],
            'absent_mapped_host_evidence': absent_hosts,
            'observed_in_admitted_flow': False,
            'scope': 'Absent OS optional branch, not a candidate installation requirement; raw OS closure remains unresolved.'}
