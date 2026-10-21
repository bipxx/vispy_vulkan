"""Check the compatible installed leaf with Qt's exact old CRT, without graphics."""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    wheel, output = args.wheel.resolve(strict=True), args.output.resolve()
    os.environ["QT_API"] = "pyside2"
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # Match the failed public fixture's binding-first DLL load order.
    from PySide2 import QtCore, QtGui, QtWidgets
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint
    handle = kernel.GetModuleHandleW("MSVCP140.dll")
    if not handle:
        raise RuntimeError("Qt did not load its expected MSVC runtime")
    filename = ctypes.create_unicode_buffer(32768)
    if not kernel.GetModuleFileNameW(handle, filename, len(filename)):
        raise ctypes.WinError(ctypes.get_last_error())
    runtime = Path(filename.value)
    digest = hashlib.sha256(runtime.read_bytes()).hexdigest()
    assert runtime.is_relative_to(Path(sys.prefix).resolve())
    assert digest == "f87819ae8c6f7c90d3237a1abb9809e8cba9dcd0c80ac3f0969a5e68ef652ca4"
    assert QtWidgets.QApplication.instance() is None
    assert QtGui.QOpenGLContext.currentContext() is None
    sys.argv = ["cp310_candidate_cpu.py", "--wheel", str(wheel), "--output", str(output), "--dive"]
    probe = Path(__file__).with_name("cp310_candidate_cpu.py")
    try:
        runpy.run_path(str(probe), run_name="__main__")
    except SystemExit as result:
        if result.code not in (None, 0):
            raise
    from vispy import _dawn
    # The frozen shutdown path locks Engine::mu but does not request a device.
    # This exercises the formerly failing native std::mutex under the old CRT.
    _dawn.shutdown()
    _dawn.shutdown()
    assert kernel.GetModuleHandleW("MSVCP140.dll") == handle
    assert QtWidgets.QApplication.instance() is None
    assert QtGui.QOpenGLContext.currentContext() is None
    record = json.loads(output.read_text(encoding="utf-8"))
    record.update({"qualification": "compatible_cp310_old_crt_sdf_host_import_and_shutdown_cpu_only",
                   "loaded_msvc_runtime": str(runtime), "loaded_msvc_runtime_sha256": digest,
                   "qt_imported_before_native": True, "native_shutdown_mutex_verified": True,
                   "qapplication_created": False, "legacy_graphics_qualified": False,
                   "compatibility_probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "qt_core_origin": QtCore.__file__})
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"old_crt_native_mutex": "passed", "sdf": "passed", "host_import": "passed",
                      "graphics_qualified": False}))


if __name__ == "__main__":
    main()
