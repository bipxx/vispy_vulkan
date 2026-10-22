# SPDX-License-Identifier: AGPL-3.0-only
"""Quality and residency of the actual 24 large-volume benchmark workloads.

Uses benchmark_frames.build_scene directly, including its exact data generator,
camera, public update function and quality probe frames. Capture waits are
deliberate; this module does not measure interactive performance.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import numpy as np

try:
    from . import benchmark_frames as benchmark
    from .fixture_large_image import rect_bounds, assert_framebuffer_draws, residency_result, RESIDENT_ZERO
    from .fixture_gloo import freeze
except ImportError:
    import benchmark_frames as benchmark
    from fixture_large_image import rect_bounds, assert_framebuffer_draws, residency_result, RESIDENT_ZERO
    from fixture_gloo import freeze

CASES = tuple(name for name, workload in benchmark.CATALOG.items() if workload.family == 'volume')
STAGES = ('initial', 'repeat', 'probe7', 'probe73')
PROBES = (None, None, 7, 73)
UPDATE_ZERO = tuple(key for key in RESIDENT_ZERO if key not in
                    ('texture_uploads', 'texture_upload_bytes', 'texture_conversion_ns'))


def record_commands(batch, commands, shaders):
    """Same lossless array records, without a 512-MiB hashing bytes copy."""
    for row in batch:
        recorded = []
        for value in row:
            if isinstance(value, np.ndarray):
                data = np.ascontiguousarray(value)
                recorded.append(dict(array=dict(dtype=data.dtype.str, shape=list(data.shape),
                    sha256=hashlib.sha256(memoryview(data).cast('B')).hexdigest(), bytes=data.nbytes)))
            else:
                recorded.append(freeze(value))
        commands.append(recorded)
        if row[0] == 'DATA' and isinstance(row[3], str):
            shaders[str(row[1])] = row[3]


def assert_owned_clear(commands, owned):
    bound = cleared = False
    draws = 0
    for row in commands:
        if row[0] == 'CURRENT':
            bound = cleared = False
        elif row[0] == 'FRAMEBUFFER':
            bound = row[1] == owned and row[2] is True
        elif row[0] == 'FUNC' and row[1] == 'glClear':
            assert bound, 'Clear missed the owned quality framebuffer'
            cleared = (int(row[2]) & 0x4100) == 0x4100
        elif row[0] == 'DRAW':
            assert bound and cleared, 'Owned color+depth clear must precede every draw'
            draws += 1
    assert draws > 0


def change_discrimination(initial_original, probe_original, initial_candidate, probe_candidate):
    """A small update cannot pass merely by remaining inside the byte tolerance."""
    original_delta = np.abs(probe_original.astype(np.int16)-initial_original.astype(np.int16))
    original_changed = np.any(original_delta != 0, axis=-1)
    candidate_changed = np.any(probe_candidate != initial_candidate, axis=-1)
    total = int(np.count_nonzero(original_changed))
    overlap = int(np.count_nonzero(original_changed & candidate_changed))
    candidate_total = int(np.count_nonzero(candidate_changed))
    return dict(passed=total > 0 and overlap*2 >= total,
                original_changed_pixels=total, candidate_changed_pixels=candidate_total,
                overlapping_changed_pixels=overlap, original_max_abs_change=int(original_delta.max()),
                required_original_changed_fraction=.5,
                status='pixel-discriminating' if total else 'upload-witnessed, not pixel-discriminating')


def case_contract(name):
    if name not in CASES:
        raise ValueError('A registered large-volume benchmark workload is required')
    workload = benchmark.CATALOG[name]
    return dict(case=name, workload=asdict(workload),
                workload_sha256=benchmark.value_sha256(asdict(workload)),
                stages=list(STAGES), probe_frames=list(PROBES),
                texture_format='r32f', cmap=workload.colormap,
                camera=dict(azimuth=30, elevation=20, distance=workload.shape[0]*2.5,
                            fov=45, center=[workload.shape[0]/2]*3),
                comparison=dict(full_rgba=True, excluded_pixels=0,
                                max_abs_channel_error=2, edge_mask=None,
                                criteria='benchmark_frames.compare_quality defaults, unchanged'),
                performance_qualified=False)


def compare_frames(original, candidate):
    # The existing benchmark whole-frame criterion is fixed before execution;
    # no masks, crops, tone correction or changed rendering controls are used.
    return benchmark.compare_quality(original, candidate)


def assert_nonblank(name, image):
    spec = case_contract(name)
    w, h = spec['workload']['viewport']
    assert image.shape == (h, w, 4) and image.dtype == np.uint8
    assert np.any(image[..., :3]), 'A blank large-volume frame cannot pass'
    assert np.any(image[..., 0] != image[0, 0, 0]), 'Constant output cannot pass'
    assert image[2, 2].tolist() == [0, 0, 0, 255], 'Outside-volume background must remain opaque black'


def render(name, kind, capture):
    """Stream all frames and raw GLIR/counters to disk before admission.

    Both roles use the benchmark's actual PyQt6 scene factory. A single owned
    RGBA8/depth target survives every capture; reactivation does not allocate.
    """
    spec = case_contract(name)
    if kind not in ('upstream', 'candidate'):
        raise ValueError('Explicit installed-wheel role required')
    from vispy import scene, gloo
    dawn = None
    if kind == 'candidate':
        from vispy import _dawn as dawn
    commands, shaders = [], {}
    owned = {}

    def on_canvas(canvas):
        owned['canvas'] = canvas
        owned['original_parser'] = canvas.context.shared.parser.parse
        def log(batch):
            record_commands(batch, commands, shaders)
            return owned['original_parser'](batch)
        canvas.context.shared.parser.parse = log
        # The shared factory has already completed its surface preparation;
        # no volume data exists yet, so the first upload remains observable.
        assert tuple(canvas.physical_size) == benchmark.CATALOG[name].viewport, 'Physical viewport preflight failed before source allocation'

    canvas = None
    pushed = False
    try:
        workload = benchmark.CATALOG[name]
        canvas, update, data_hash = benchmark.build_scene(workload, kind, False, on_canvas=on_canvas)
        assert tuple(canvas.physical_size) == workload.viewport, 'Actual physical viewport must match the benchmark'
        views = [node for node in canvas.central_widget.children if isinstance(node, scene.widgets.ViewBox)]
        assert len(views) == 1
        view = views[0]
        volumes = [node for node in view.scene.children if isinstance(node, scene.visuals.Volume)]
        assert len(volumes) == 1
        volume = volumes[0]
        w, h = workload.viewport
        color = gloo.Texture2D(shape=(h, w, 4), format='rgba', internalformat='rgba8')
        depth = gloo.RenderBuffer((h, w))
        framebuffer = gloo.FrameBuffer(color=color, depth=depth)
        canvas.push_fbo(framebuffer, (0, 0), canvas.size)
        pushed = True
        canvas.transforms.configure(viewport=(0, 0, w, h), fbo_size=(w, h),
                                    fbo_rect=(0, 0, *canvas.physical_size))
        corners = canvas.transforms.get_transform('canvas', 'framebuffer').map([[0, 0], list(canvas.size)])
        np.testing.assert_allclose(corners[:, :2], [[0, h], [w, 0]], rtol=0, atol=1e-9)
        stages = {}
        for stage, frame in zip(STAGES, PROBES):
            first = len(commands)
            before = dict(dawn.probe()) if dawn else None
            requested_bytes = update(frame) if frame is not None else 0
            framebuffer.activate()
            gloo.clear(color=(0, 0, 0, 1), depth=True, stencil=False)
            canvas.draw_visual(canvas.scene)
            rgba = np.array(framebuffer.read(alpha=True), copy=True)
            after = dict(dawn.probe()) if dawn else None
            delta = ({key: after[key]-value for key, value in before.items()
                      if type(value) is int and type(after.get(key)) is int} if dawn else None)
            row = dict(probe_frame=frame, requested_update_bytes=requested_bytes,
                       source_texture_id=volume._texture.id, target_texture_id=color.id,
                       geometry_ids=[volume._vertices.id, volume._index_buffer.id],
                       framebuffer_id=framebuffer.id, command_start=first, command_stop=len(commands),
                       commands=commands[first:], shaders=dict(shaders),
                       camera_state=dict(
                           **{key: float(getattr(view.camera, key)) for key in ('azimuth', 'elevation', 'distance', 'fov', 'scale_factor')},
                           center=[float(v) for v in view.camera.center], up=view.camera.up),
                       counter_before=before, counter_after=after, counter_delta=delta)
            capture(stage, rgba, row)
            stages[stage] = {key: value for key, value in row.items() if key not in ('commands', 'shaders')}
            del rgba
        from vispy.visuals.volume import VolumeVisual
        return commands, shaders, dict(spec, data_sha256=data_hash,
            actual_canvas_size=list(canvas.size), actual_physical_size=list(canvas.physical_size),
            canvas_to_framebuffer_corners=corners.tolist(), actual_view_rect=rect_bounds(view.rect),
            actual_inner_rect=rect_bounds(view.inner_rect), source_texture_shape=list(volume._texture.shape),
            actual_volume_controls=dict(method=volume.method, interpolation=volume.interpolation,
                threshold=float(volume.threshold), gamma=float(volume.gamma),
                relative_step_size=float(volume.relative_step_size),
                clim=[float(v) for v in volume.clim], texture_format=volume._texture.internalformat,
                colormap_samples=volume.cmap.map(np.array([0,.25,.5,.75,1],np.float32)).tolist()),
            exposed_methods=sorted(VolumeVisual._rendering_methods),
            exposed_raycasting_modes=sorted(VolumeVisual._raycasting_modes), stages_observed=stages)
    finally:
        # Keep the canvas owner even if the shared factory raises after its hook.
        canvas = owned.get('canvas', canvas)
        if canvas is not None:
            try:
                if pushed:
                    canvas.pop_fbo()
            finally:
                canvas.context.shared.parser.parse = owned['original_parser']
                canvas.close()
