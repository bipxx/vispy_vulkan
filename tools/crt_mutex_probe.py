"""Load an exact CRT and one diagnostic mutex DLL in a fresh CPU-only process."""

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_rva(path, symbol):
    data = path.read_bytes()
    u16 = lambda offset: struct.unpack_from("<H", data, offset)[0]
    u32 = lambda offset: struct.unpack_from("<I", data, offset)[0]
    u64 = lambda offset: struct.unpack_from("<Q", data, offset)[0]
    pe = u32(0x3C)
    optional, size = pe + 24, u16(pe + 20)
    sections = []
    for index in range(u16(pe + 6)):
        offset = optional + size + index * 40
        sections.append((u32(offset + 12), u32(offset + 8), u32(offset + 20), u32(offset + 16)))

    def offset(rva):
        for va, virtual_size, raw, raw_size in sections:
            if va <= rva < va + max(virtual_size, raw_size):
                return raw + rva - va
        raise ValueError(rva)

    def name(rva):
        start = offset(rva)
        return data[start:data.index(b"\0", start)].decode()

    descriptor = offset(u32(optional + 120))  # PE32+ import data directory.
    while u32(descriptor + 12):
        dll = name(u32(descriptor + 12))
        original = u32(descriptor) or u32(descriptor + 16)
        iat, index = u32(descriptor + 16), 0
        while value := u64(offset(original + index * 8)):
            if not value & (1 << 63) and dll.lower() == "msvcp140.dll" and name(value + 2) == symbol:
                return iat + index * 8
            index += 1
        descriptor += 20
    raise ValueError("Required CRT import is absent")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime_path, probe_path = args.runtime.resolve(strict=True), args.probe.resolve(strict=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint
    assert not kernel.GetModuleHandleW("msvcp140.dll"), "Fresh child already loaded a CRT"
    runtime = ctypes.WinDLL(str(runtime_path))
    probe = ctypes.WinDLL(str(probe_path))
    assert kernel.GetModuleHandleW("msvcp140.dll") == runtime._handle
    buffer = ctypes.create_unicode_buffer(32768)
    assert kernel.GetModuleFileNameW(runtime._handle, buffer, len(buffer))
    loaded_path = Path(buffer.value).resolve(strict=True)
    assert sha(loaded_path) == sha(runtime_path)
    mutex_import = ctypes.c_void_p.from_address(probe._handle + import_rva(probe_path, "_Mtx_lock")).value
    actual_export = ctypes.cast(runtime._Mtx_lock, ctypes.c_void_p).value
    assert mutex_import == actual_export, "Mutex call resolved a different CRT"
    record = {"qualification": "cpu_only_std_mutex_runtime_compatibility_diagnostic",
              "python": sys.executable, "runtime_requested": str(runtime_path),
              "runtime_loaded": str(loaded_path), "runtime_sha256": sha(loaded_path),
              "probe": str(probe_path), "probe_sha256": sha(probe_path),
              "resolved_mutex_import_matches_selected_runtime": True,
              "qt_imported": False, "graphics_created": False, "phase": "before_mutex_lock"}
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    function = probe.vispy_mutex_probe
    function.restype = ctypes.c_int
    function.argtypes = []
    record["result"] = function()
    assert record["result"] == 73
    record["phase"] = "mutex_lock_passed"
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
