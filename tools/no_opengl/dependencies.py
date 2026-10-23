"""Read PE normal/delay imports and ELF dynamic dependencies without loading them."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
import struct
import sys

from .policy import is_gl_entrypoint, library_reason


class BinaryError(ValueError):
    pass


@lru_cache(maxsize=None)
def windows_api_set_host(name: str) -> Path | None:
    """Ask the OS loader for an API-set host without running DLL initialization.

    This runs in the dependency-audit process, never in the candidate observer.
    A successful resolution is recorded as a real file and audited recursively.
    """
    if sys.platform != "win32" or not name.casefold().startswith(("api-", "ext-")):
        return None
    import ctypes
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [w.LPCWSTR, w.HANDLE, w.DWORD]
    kernel.LoadLibraryExW.restype = w.HMODULE
    kernel.GetModuleFileNameW.argtypes = [w.HMODULE, w.LPWSTR, w.DWORD]
    kernel.GetModuleFileNameW.restype = w.DWORD
    kernel.FreeLibrary.argtypes = [w.HMODULE]
    kernel.FreeLibrary.restype = w.BOOL
    # DONT_RESOLVE_DLL_REFERENCES | LOAD_LIBRARY_SEARCH_SYSTEM32: inspect the
    # selected host's path, without calling an export or executing DllMain.
    handle = kernel.LoadLibraryExW(name, None, 0x00000001 | 0x00000800)
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
        return Path(buffer.value).resolve(strict=True) if 0 < length < len(buffer) else None
    finally:
        kernel.FreeLibrary(handle)


def _cstring(data, offset):
    if not 0 <= offset < len(data):
        raise BinaryError("String offset outside binary")
    end = data.find(b"\0", offset)
    if end < 0:
        raise BinaryError("Unterminated binary string")
    return data[offset:end].decode("ascii", "strict")


def pe_image(data: bytes) -> dict:
    if data[:2] != b"MZ" or len(data) < 64:
        raise BinaryError("Not a PE image")
    offset = struct.unpack_from("<I", data, 60)[0]
    if data[offset:offset + 4] != b"PE\0\0":
        raise BinaryError("Invalid PE signature")
    machine, sections, _, _, _, optional_size, _ = struct.unpack_from("<HHIIIHH", data, offset + 4)
    optional = offset + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic == 0x20b:
        pointer, directory = 8, optional + 112
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    elif magic == 0x10b:
        pointer, directory = 4, optional + 96
        image_base = struct.unpack_from("<I", data, optional + 28)[0]
    else:
        raise BinaryError("Unknown PE optional header")
    directory_count = struct.unpack_from("<I", data, directory - 4)[0]
    headers_size = struct.unpack_from("<I", data, optional + 60)[0]
    table = optional + optional_size
    ranges = []
    for index in range(sections):
        start = table + index * 40
        virtual_size, address, raw_size, raw_offset = struct.unpack_from("<IIII", data, start + 8)
        ranges.append((address, max(virtual_size, raw_size), raw_offset, raw_size))
    def rva(value):
        if value < headers_size and value < len(data):
            return value
        for address, extent, raw_offset, raw_size in ranges:
            if address <= value < address + extent:
                relative = value - address
                if relative >= raw_size or raw_offset + relative >= len(data):
                    raise BinaryError("PE RVA has no file-backed bytes")
                return raw_offset + relative
        raise BinaryError("PE RVA outside sections")
    def entry(index):
        if index >= directory_count:
            return 0, 0
        return struct.unpack_from("<II", data, directory + 8 * index)
    def thunks(value):
        if not value:
            return []
        position = rva(value)
        result = []
        fmt = "<Q" if pointer == 8 else "<I"
        for _ in range(len(data) // pointer):
            item = struct.unpack_from(fmt, data, position)[0]
            if not item:
                return result
            result.append("#" + str(item & 0xffff) if item >> (pointer * 8 - 1) else _cstring(data, rva(item) + 2))
            position += pointer
        raise BinaryError("Unterminated import table")
    imports = []
    value, size = entry(1)
    if value:
        position = rva(value)
        for _ in range(max(1, size // 20)):
            lookup, stamp, forwarder, name, first = struct.unpack_from("<IIIII", data, position)
            if not any((lookup, stamp, forwarder, name, first)):
                break
            imports.append({"name": _cstring(data, rva(name)), "delay": False, "symbols": thunks(lookup or first)})
            position += 20
    value, size = entry(13)
    if value:
        position = rva(value)
        for _ in range(max(1, size // 32)):
            attrs, name, handle, iat, lookup, bound, unload, stamp = struct.unpack_from("<IIIIIIII", data, position)
            if not any((attrs, name, handle, iat, lookup, bound, unload, stamp)):
                break
            convert = (lambda x: x) if attrs & 1 else (lambda x: x - image_base if x else 0)
            imports.append({"name": _cstring(data, rva(convert(name))), "delay": True, "symbols": thunks(convert(lookup or iat))})
            position += 32
    exports = []
    value, size = entry(0)
    if value:
        position = rva(value)
        _, _, _, _, _, ordinal_base, functions, names, functions_rva, names_rva, ordinals_rva = struct.unpack_from("<IIHHIIIIIII", data, position)
        for index in range(names):
            name = _cstring(data, rva(struct.unpack_from("<I", data, rva(names_rva) + index * 4)[0]))
            ordinal = struct.unpack_from("<H", data, rva(ordinals_rva) + index * 2)[0]
            if ordinal >= functions:
                raise BinaryError("PE export ordinal outside function table")
            address = struct.unpack_from("<I", data, rva(functions_rva) + ordinal * 4)[0]
            forwarded = value <= address < value + size
            exports.append({"name": name, "ordinal": ordinal_base + ordinal, "rva": address,
                            "forwarder": _cstring(data, rva(address)) if forwarded else None})
    return {"format": "PE", "machine": machine, "pointer_bytes": pointer, "imports": imports, "exports": exports}


def elf_image(data: bytes) -> dict:
    if data[:4] != b"\x7fELF" or data[4:6] not in (b"\x02\x01", b"\x01\x01"):
        raise BinaryError("Only little-endian ELF32/ELF64 is supported")
    wide = data[4] == 2
    if wide:
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phsize, phnum = struct.unpack_from("<HH", data, 54)
    else:
        phoff = struct.unpack_from("<I", data, 28)[0]
        phsize, phnum = struct.unpack_from("<HH", data, 42)
    loads, dynamic = [], None
    for index in range(phnum):
        pos = phoff + index * phsize
        if wide:
            kind, flags, offset, address, physical, file_size, memory_size, alignment = struct.unpack_from("<IIQQQQQQ", data, pos)
        else:
            kind, offset, address, physical, file_size, memory_size, flags, alignment = struct.unpack_from("<IIIIIIII", data, pos)
        if kind == 1:
            loads.append((address, file_size, offset))
        elif kind == 2:
            dynamic = (offset, file_size)
    tags = []
    if dynamic:
        for pos in range(dynamic[0], sum(dynamic), 16 if wide else 8):
            tag, value = struct.unpack_from("<qQ" if wide else "<iI", data, pos)
            if not tag:
                break
            tags.append((tag, value))
    string_address = next((value for tag, value in tags if tag == 5), None)
    strings = None
    if string_address is not None:
        strings = next((offset + string_address - address for address, size, offset in loads if address <= string_address < address + size), None)
        if strings is None:
            raise BinaryError("ELF string table outside file-backed load segments")
    needed = [{"name": _cstring(data, strings + value), "delay": False, "symbols": []}
              for tag, value in tags if tag == 1]
    paths = [_cstring(data, strings + value) for tag, value in tags if tag in (15, 29)]
    return {"format": "ELF", "machine": struct.unpack_from("<H", data, 18)[0],
            "pointer_bytes": 8 if wide else 4, "imports": needed, "runpaths": paths, "exports": []}


def inspect_binary(path: Path) -> dict:
    data = Path(path).read_bytes()
    result = pe_image(data) if data[:2] == b"MZ" else elf_image(data)
    return {"path": str(Path(path).resolve()), "sha256": hashlib.sha256(data).hexdigest(), **result}


def dependency_closure(roots: list[Path], search_dirs: list[Path]) -> dict:
    """Resolve only declared search directories and each binary's own directory.

    Unresolved dependencies are explicit; system/API-set names are not silently
    treated as proof of complete closure. No inspected binary is executed.
    """
    directories = [Path(p).resolve(strict=True) for p in search_dirs]
    indexes, api_sets = {}, {}
    def locate(name, parent, runpaths):
        paths = [parent, *(Path(value.replace("$ORIGIN", str(parent))) for text in runpaths for value in text.split(":")), *directories]
        for directory in paths:
            if not directory.is_absolute() or not directory.is_dir():
                continue
            key = str(directory)
            if key not in indexes:
                indexes[key] = {p.name.casefold(): p for p in directory.iterdir() if p.is_file()}
            if name.casefold() in indexes[key]:
                return indexes[key][name.casefold()].resolve()
        host = windows_api_set_host(name)
        if host:
            api_sets[name] = str(host)
            return host
        return None
    queue = [Path(p).resolve(strict=True) for p in roots]
    visited, binaries, edges, unresolved, violations = set(), [], [], [], []
    while queue:
        path = queue.pop(0)
        if str(path) in visited:
            continue
        visited.add(str(path))
        try:
            binary = inspect_binary(path)
        except (BinaryError, OSError, struct.error, UnicodeError) as error:
            unresolved.append({"path": str(path), "error": str(error)})
            continue
        binaries.append(binary)
        reason = library_reason(path.name)
        if reason:
            violations.append({"kind": "library", "path": str(path), "reason": reason})
        for item in binary["imports"]:
            target = locate(item["name"], path.parent, binary.get("runpaths", []))
            edge = {"parent": str(path), **item, "resolved": str(target) if target else None}
            edges.append(edge)
            reason = library_reason(item["name"])
            gl_symbols = [name for name in item["symbols"] if is_gl_entrypoint(name)]
            if reason or gl_symbols:
                violations.append({**edge, "kind": "dependency", "reason": reason or "OpenGL API import", "gl_symbols": gl_symbols})
            if target:
                queue.append(target)
            else:
                unresolved.append(edge)
    return {"gate": "FAIL" if violations else ("UNVERIFIED" if unresolved else "PASS"),
            "binaries": binaries, "edges": edges, "unresolved": unresolved, "violations": violations,
            "windows_api_set_hosts": api_sets,
            "coverage": {"required_dependencies": True, "PE_delay_imports": True, "dynamic_plugin_discovery": False,
                         "environment_without_gl_packages": False},
            "scope": "Declared root binary closure only; runtime plugin discovery and no-GL installed environment remain separate gates."}
