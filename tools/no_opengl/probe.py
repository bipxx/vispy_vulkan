"""Fresh-process candidate probe. Native observation belongs to the controller."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from no_opengl.policy import import_reason, is_gl_entrypoint, library_reason


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', choices=('import', 'headless', 'qt', 'script'), default='import')
    parser.add_argument('--binding', choices=('pyqt5', 'pyqt6', 'pyside6'))
    parser.add_argument('--policy', choices=('observe', 'deny'), default='deny')
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--dependency-path', type=Path, action='append', default=[])
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--script', type=Path)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    report = {'status': 'FAILED', 'pid': os.getpid(), 'parent_pid': os.getppid(), 'scenario': args.scenario,
              'binding': args.binding, 'policy': args.policy, 'python': sys.version, 'executable': sys.executable,
              'events': [], 'snapshots': [], 'source_mode': bool(args.source_root)}
    native = canvas = None
    began = time.monotonic()
    def event(kind, **values):
        report['events'].append({'kind': kind, 'pid': os.getpid(), 'elapsed_s': time.monotonic() - began, **values})
    def hook(name, values):
        reason = None
        if name == 'import':
            module = values[0]
            reason = import_reason(module)
            if reason:
                event('python_import', name=module)
        elif name == 'ctypes.dlopen':
            library = str(values[0]) if values[0] is not None else ''
            event('ctypes_load_request', path=library)
            reason = library_reason(library)
        elif name in ('ctypes.dlsym', 'ctypes.dlsym/handle'):
            symbol = str(values[1])
            if is_gl_entrypoint(symbol):
                event('ctypes_symbol', name=symbol)
                reason = 'OpenGL entry-point lookup'
        if reason and args.policy == 'deny':
            raise RuntimeError('No-OpenGL policy blocked: ' + reason)
    try:
        assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
        if args.source_root:
            # Source probes must not accidentally import the editable installation.
            if any(type(f).__name__ == 'ScikitBuildRedirectingFinder' for f in sys.meta_path):
                raise RuntimeError('Use base Python -I plus --dependency-path; an editable finder is active')
            for path in args.dependency_path:
                sys.path.append(str(path.resolve(strict=True)))
            sys.path.insert(0, str(args.source_root.resolve(strict=True) / 'src'))
        elif args.dependency_path:
            raise RuntimeError('--dependency-path is only valid for explicitly labelled source probes')
        sys.addaudithook(hook)
        from mesh_layout_process import _native_paths
        def snapshot(phase):
            report['snapshots'].append({'phase': phase, 'paths': _native_paths()})
        snapshot('before_vispy')
        if args.scenario == 'script':
            if args.script is None:
                raise ValueError('--script is required for script scenario')
            sys.argv = [str(args.script), *([x for x in args.arguments if x != '--'])]
            try:
                runpy.run_path(str(args.script.resolve(strict=True)), run_name='__main__')
            except SystemExit as exit_status:
                if exit_status.code not in (None, 0):
                    raise
        else:
            import vispy
            from vispy import gloo, scene
            report['vispy_origin'] = str(Path(vispy.__file__).resolve())
            report['module_origins'] = {name: getattr(sys.modules[name], '__file__', None)
                                        for name in sorted(sys.modules) if name.startswith('vispy')}
            if args.source_root:
                assert Path(vispy.__file__).resolve().is_relative_to(args.source_root.resolve())
            snapshot('after_vispy_import')
            if args.binding:
                from vispy import app
                app.use_app(args.binding)
                snapshot('after_qt_import')
            if args.scenario in ('headless', 'qt'):
                import numpy as np
                from vispy import _dawn as native, app
                info = dict(native.device_info())
                assert info['ok'] and info['backend'] == 'Vulkan', info
                report['device'] = info
                canvas = app.Canvas(app=args.binding if args.scenario == 'qt' else 'dawn_headless',
                                    size=(32, 24), show=args.scenario == 'qt', config={'samples': 0})
                canvas.events.draw.ignore_callback_errors = False
                if args.scenario == 'qt':
                    for _ in range(6):
                        app.process_events()
                canvas.set_current()
                gloo.set_viewport(0, 0, 32, 24)
                gloo.clear(color=(1, 0, 0, 1))
                pixels = gloo.read_pixels((0, 0, 32, 24), alpha=True)
                assert pixels.shape == (24, 32, 4) and np.all(pixels == [255, 0, 0, 255])
                np.save(args.output.with_suffix('.rgba.npy'), pixels)
                snapshot('after_clear_capture')
                canvas.close()
                canvas = None
                if args.scenario == 'qt':
                    app.process_events()
            report['status'] = 'PASS_SCENARIO'
        if args.scenario == 'script':
            report['status'] = 'PASS_SCENARIO'
        if args.wheel:
            # Apply the same installed-artifact check to host scripts. A host
            # which never imports the candidate cannot qualify its artifact.
            import vispy
            from vispy import _dawn
            package = Path(vispy.__file__).resolve().parent
            assert package.is_relative_to(Path(sys.prefix).resolve())
            assert Path(_dawn.__file__).resolve().parent == package
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cmake'))
            from runtime_package import wheel_package_hashes
            members = wheel_package_hashes(args.wheel)
            with zipfile.ZipFile(args.wheel) as archive:
                for name in members:
                    assert (package / Path(name).relative_to('vispy')).read_bytes() == archive.read(name), name
            report.update(wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                          wheel_members_verified=len(members), vispy_origin=str(Path(vispy.__file__).resolve()),
                          native_origin=str(Path(_dawn.__file__).resolve()))
        snapshot('after_scenario')
    except BaseException:
        report['error'] = traceback.format_exc()
    finally:
        try:
            if canvas is not None:
                canvas.close()
            if native is not None:
                import gc
                gc.collect()
                native.process_events()
                native.shutdown()
                state = dict(native.probe())
                gauges = ('pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
                          'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
                          'line_resource_pool_busy_slots', 'line_resource_pool_bytes')
                assert all(state[key] == 0 for key in gauges), state
                report.update(after_shutdown=state, zero_live_gauges=list(gauges))
        except BaseException:
            report.update(status='FAILED_CLEANUP', cleanup_error=traceback.format_exc())
        report['forbidden_modules_present'] = [name for name in sys.modules if import_reason(name)]
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if report['status'] == 'PASS_SCENARIO' else 1


if __name__ == '__main__':
    raise SystemExit(main())
