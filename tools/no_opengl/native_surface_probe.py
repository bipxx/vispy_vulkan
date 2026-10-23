"""Causal control: Vulkan offscreen versus a real Win32 HWND, without Qt."""
from __future__ import annotations

import argparse
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('offscreen', 'win32'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'RUNNING', 'mode': args.mode, 'stages': []}
    def stage(name):
        result['stages'].append(name)
        (args.output / 'surface.json').write_text(json.dumps(result, indent=2) + '\n')
    canvas = native = hwnd = None
    try:
        import numpy as np
        from vispy import app, gloo, _dawn as native
        result['device'] = dict(native.device_info())
        assert result['device']['backend'] == 'Vulkan' and result['device']['ok']
        assert not any(name.startswith(('PyQt', 'PySide', 'qtpy')) for name in sys.modules)
        stage('vulkan_device_without_qt')
        canvas = app.Canvas(app='dawn_headless', size=(64, 64), show=False, config={'samples': 0})
        canvas.set_current()
        canvas_id = canvas._backend._dawn_canvas_id
        stage('headless_canvas_created')
        if args.mode == 'win32':
            if sys.platform != 'win32':
                raise RuntimeError('Win32 control requires Windows')
            user, kernel = c.WinDLL('user32', use_last_error=True), c.WinDLL('kernel32', use_last_error=True)
            kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
            kernel.GetModuleHandleW.restype = w.HMODULE
            user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, c.c_int, c.c_int,
                                            c.c_int, c.c_int, w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p]
            user.CreateWindowExW.restype = w.HWND
            user.DestroyWindow.argtypes = [w.HWND]
            user.DestroyWindow.restype = w.BOOL
            hwnd = user.CreateWindowExW(0, 'STATIC', 'Vulkan native surface control', 0x10cf0000,
                                        0, 0, 96, 96, None, None, kernel.GetModuleHandleW(None), None)
            if not hwnd:
                raise c.WinError(c.get_last_error())
            stage('native_hwnd_created_without_qt')
            stage('before_set_surface_win32')
            native.set_surface_win32(canvas_id, int(hwnd), 0)
            stage('after_set_surface_win32')
        gloo.set_viewport(0, 0, 64, 64)
        gloo.clear(color=(1, 0, 0, 1))
        pixels = gloo.read_pixels((0, 0, 64, 64), alpha=True)
        assert pixels.shape == (64, 64, 4) and np.all(pixels == [255, 0, 0, 255])
        np.save(args.output / 'clear.npy', pixels)
        stage('exact_vulkan_clear_capture')
        stage('before_native_present')
        native.present(canvas_id)
        native.process_events()
        stage('after_native_present')
        result['status'] = 'PASS_SURFACE_CONTROL'
    except BaseException:
        import traceback
        result.update(status='FAILED', error=traceback.format_exc())
    finally:
        try:
            if canvas is not None:
                canvas.close()
            if hwnd:
                assert user.DestroyWindow(hwnd)
            if native is not None:
                native.process_events()
                native.shutdown()
                state = dict(native.probe())
                fields = ('pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
                          'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
                          'line_resource_pool_busy_slots', 'line_resource_pool_bytes')
                assert all(state[name] == 0 for name in fields), state
                result['after_shutdown'] = state
        except BaseException:
            import traceback
            result.update(status='FAILED_CLEANUP', cleanup_error=traceback.format_exc())
        (args.output / 'surface.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'PASS_SURFACE_CONTROL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
