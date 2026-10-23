"""Exercise color renderbuffers and a flat 2D marker cloud on an installed wheel.

This is a functional rendering/reuse check, not an OpenGL parity or performance
benchmark. Run with the consumer environment's Python and a fresh output path.
"""

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import traceback
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mesh_layout_process import (
    assert_wheel_module_origins,
    native_modules,
    process_stamp,
)


ROOT = Path(__file__).resolve().parents[1]
WARM_COUNTERS = (
    'shader_normalizations', 'shader_parse_calls', 'shader_link_calls',
    'shader_module_creations', 'render_pipeline_creations',
    'compute_pipeline_creations', 'buffer_uploads', 'geometry_upload_bytes',
    'point_conversion_builds', 'point_conversion_bytes',
    'vertex_input_conversion_builds', 'vertex_input_conversion_bytes',
    'texture_uploads', 'texture_upload_bytes',
)
LIVE_GAUGES = (
    'pending_tickets', 'queued_frames', 'live_buffer_bytes',
    'live_cpu_buffer_bytes', 'live_texture_bytes', 'canvas_texture_bytes',
    'transient_buffer_bytes', 'line_resource_pool_busy_slots',
    'line_resource_pool_bytes',
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=1_000_000)
    args = parser.parse_args()
    require(args.count > 0, 'A positive marker count is required')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = {
        'status': 'FAILED_PRESERVED', 'pid': process_stamp()['pid'],
        'process_stamp': process_stamp(), 'count': args.count,
        'scope': 'installed-wheel functional markers; no parity or timing claim',
        'cases': [],
    }
    native = canvas = None
    try:
        require(sys.flags.isolated and sys.flags.dont_write_bytecode,
                'Run the installed consumer with Python -I -B')
        import numpy as np
        import vispy
        from vispy import _dawn as native, app, gloo, scene
        from vispy.visuals.text import _sdf_cpu

        package = Path(vispy.__file__).resolve().parent
        require(package.is_relative_to(Path(sys.prefix).resolve()) and
                not package.is_relative_to(ROOT), 'An external installed wheel is required')
        with zipfile.ZipFile(args.wheel) as archive:
            hashes = {name: hashlib.sha256(archive.read(name)).hexdigest()
                      for name in archive.namelist()
                      if name.startswith('vispy/') and not name.endswith('/')}
        for name, expected in hashes.items():
            path = package / Path(name).relative_to('vispy')
            require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                    'Installed package differs from the wheel: ' + name)
        result.update(device=dict(native.device_info()), package=str(package),
                      installed_members_verified=len(hashes),
                      wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest())
        result['renderbuffers'] = []
        canvas = app.Canvas(app='dawn_headless', size=(8, 8), show=False,
                            config={'samples': 0})
        canvas.set_current()
        for format_name, format_value in (('color', 'color'), ('rgba8-enum', 0x8058)):
            color = gloo.RenderBuffer((8, 8), format=format_value)
            fbo = gloo.FrameBuffer(color=color)
            start = dict(native.probe())
            with fbo:
                initial = fbo.read(alpha=True)
                np.save(output / (format_name + '-uninitialized.npy'), initial)
                require(initial.shape == (8, 8, 4) and not np.any(initial),
                        format_name + ': new storage must read as zero')
                gloo.clear(color=(1, 0, 0, 1))
                cleared = fbo.read(alpha=True)
                np.save(output / (format_name + '-cleared.npy'), cleared)
                require(np.all(cleared == [255, 0, 0, 255]),
                        format_name + ': clear did not reach the attachment')
            color.resize((4, 4))
            with fbo:
                resized = fbo.read(alpha=True)
                np.save(output / (format_name + '-resized.npy'), resized)
                require(resized.shape == (4, 4, 4) and not np.any(resized),
                        format_name + ': resized storage must read as zero')
                gloo.clear(color=(0, 0, 1, 1))
                color.resize((6, 6))
                pending_resize = fbo.read(alpha=True)
                np.save(output / (format_name + '-pending-resize.npy'), pending_resize)
                require(pending_resize.shape == (6, 6, 4) and not np.any(pending_resize),
                        format_name + ': queued clear leaked into the replacement allocation')
            end = dict(native.probe())
            result['latest_renderbuffer'] = {
                'format': format_name, 'before': start, 'after': end,
                'texture_uploads': end['texture_uploads'] - start['texture_uploads'],
                'texture_upload_bytes': end['texture_upload_bytes'] - start['texture_upload_bytes'],
            }
            require(end['texture_uploads'] == start['texture_uploads'] and
                    end['texture_upload_bytes'] == start['texture_upload_bytes'],
                    format_name + ': storage allocation performed a CPU texture upload')
            result['renderbuffers'].append({'format': format_name,
                                            'before': start, 'after': end,
                                            'initial_clear_resize_verified': True})
            fbo.delete()
            color.delete()
        canvas.close()
        canvas = None
        side = int(np.ceil(np.sqrt(args.count)))
        indices = np.arange(args.count, dtype=np.uint32)
        positions = np.zeros((args.count, 3), dtype=np.float32)
        positions[:, 0] = (indices % side + 0.5) * (1.6 / side) - 0.8
        positions[:, 1] = (indices // side + 0.5) * (1.6 / side) - 0.8
        result['positions_sha256'] = hashlib.sha256(positions.tobytes()).hexdigest()
        minimum_colored_pixels = min(1_000, args.count // 8)
        result['depth_test'] = False  # Flat 2D cloud: blend overlapping equal-depth markers.
        for method in ('points', 'instanced'):
            canvas = scene.SceneCanvas(app='dawn_headless', size=(128, 128),
                                       show=False, bgcolor='black', config={'samples': 0})
            view = canvas.central_widget.add_view()
            view.camera = scene.PanZoomCamera(rect=(-1, -1, 2, 2))
            marker = scene.visuals.Markers(method=method, parent=view.scene)
            marker.set_gl_state(depth_test=False)
            marker.set_data(positions, size=1, edge_width=0, face_color='red')
            first = canvas.render(alpha=True)
            np.save(output / (method + '-initial.npy'), first)
            result['latest_frame'] = {
                'method': method, 'channel_max': first.max(axis=(0, 1)).tolist(),
                'nonzero_rgb': int(np.count_nonzero(first[:, :, :3])),
                'red_pixels_above_32': int(np.count_nonzero(first[:, :, 0] > 32)),
                'probe': dict(native.probe()),
            }
            require(first.shape == (128, 128, 4), 'Unexpected marker frame shape')
            require(np.count_nonzero(first[:, :, 0] > 32) > minimum_colored_pixels,
                    method + ': the large marker grid did not render')
            before = dict(native.probe())
            for _ in range(2):
                warm = canvas.render(alpha=True)
                require(np.array_equal(first, warm), method + ': unchanged rendering changed')
            after = dict(native.probe())
            deltas = {name: after[name] - before[name] for name in WARM_COUNTERS}
            result['latest_warm'] = {'method': method, 'before': before,
                                     'after': after, 'deltas': deltas}
            require(all(value == 0 for value in deltas.values()),
                    method + ': resident rendering repeated compiler/conversion/upload work: ' + str(deltas))
            marker.set_data(positions, size=1, edge_width=0, face_color='lime')
            updated = canvas.render(alpha=True)
            require(np.count_nonzero(updated[:, :, 1] > 32) > minimum_colored_pixels and
                    np.count_nonzero(updated[:, :, 0] > 32) == 0,
                    method + ': marker color update did not reach the frame')
            require(not np.array_equal(first, updated), method + ': the update left the image unchanged')
            np.save(output / (method + '-updated.npy'), updated)
            result['cases'].append({'method': method, 'count': args.count,
                                    'warm_counter_deltas': deltas,
                                    'before_warm': before, 'after_warm': after,
                                    'initial_red_pixels': int(np.count_nonzero(first[:, :, 0] > 32)),
                                    'updated_green_pixels': int(np.count_nonzero(updated[:, :, 1] > 32))})
            marker.parent = None
            canvas.close()
            canvas = None
            del marker, view
            gc.collect()
        records = native_modules([ROOT, ROOT.parent / 'vispy_vulkan-publication'])
        layer = package / ('VkLayer_vispy_submit.dll' if sys.platform == 'win32'
                           else 'VkLayer_vispy_submit.so')
        assert_wheel_module_origins(records, package, hashes,
                                    [native.__file__, _sdf_cpu.__file__, layer])
        result.update(native_modules=records, native_origins_verified=True,
                      status='PASS_INSTALLED_LARGE_MARKER_FUNCTIONAL_SMOKE')
    except BaseException:
        result['error'] = traceback.format_exc()
    finally:
        try:
            if canvas is not None:
                canvas.close()
            if native is not None:
                gc.collect()
                native.process_events()
                native.shutdown()
                result['after_shutdown'] = dict(native.probe())
                require(all(result['after_shutdown'][name] == 0 for name in LIVE_GAUGES),
                        'Live resource gauges remain after shutdown')
                result['zero_live_gauges_verified'] = list(LIVE_GAUGES)
        except BaseException:
            result['status'] = 'FAILED_CLEANUP_PRESERVED'
            result['cleanup_error'] = traceback.format_exc()
        (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result['status'], flush=True)
    return 0 if result['status'] == 'PASS_INSTALLED_LARGE_MARKER_FUNCTIONAL_SMOKE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
