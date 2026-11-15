# SPDX-License-Identifier: AGPL-3.0-only
"""GPU acceptance for SCI-04, SCI-05, and PERF-01: bounded VolumeVisual modes, 3D texture memory, and queue telemetry."""
from __future__ import annotations

import gc
import json
import os
from pathlib import Path
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
VOL_SHAPE = (16, 16, 16)
CANVAS_SIZE = (32, 32)


def _synthetic_volume():
    """Analytic (16, 16, 16) float32 volume with medium shell (0.40, r<=6.5) and bright core (0.95, r<=2.2)."""
    zz, yy, xx = np.mgrid[0:16, 0:16, 0:16].astype(np.float32)
    dist = np.sqrt((zz - 7.5) ** 2 + (yy - 7.5) ** 2 + (xx - 7.5) ** 2)
    vol = np.zeros(VOL_SHAPE, dtype=np.float32)
    vol[dist <= 6.5] = 0.40
    vol[dist <= 2.2] = 0.95
    return vol


@pytest.mark.parametrize('texture_format', [None, 'auto'])
@pytest.mark.parametrize('interpolation', ['linear', 'nearest'])
def test_volume_bounded_modes_mip_attenuated_iso_translucent_oracle(texture_format, interpolation):
    """Verify VolumeVisual mip, attenuated_mip, iso, translucent, clim/threshold/plane updates, and 3D formats."""
    from vispy import _dawn, scene
    from vispy.color import Colormap

    vol_data = _synthetic_volume()
    canvas = scene.SceneCanvas(
        app='dawn_headless', size=CANVAS_SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.TurntableCamera(
            fov=0.0, elevation=0.0, azimuth=0.0, scale_factor=20.0, center=(8.0, 8.0, 8.0)
        )

        volume = scene.visuals.Volume(
            vol_data,
            clim=(0.0, 1.0),
            method='mip',
            threshold=0.5,
            attenuation=0.0,
            relative_step_size=0.8,
            cmap='grays',
            interpolation=interpolation,
            texture_format=texture_format,
            parent=view.scene,
        )

        # 1. MIP mode: center ray pierces bright 0.95 core -> bright center, black corner.
        img_mip = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        center_mip = int(img_mip[16, 16, 0])
        assert center_mip >= 200, f'Expected bright MIP core, got {center_mip}'
        np.testing.assert_array_equal(img_mip[1, 1, :3], [0, 0, 0])

        # Widening clim to (0.0, 2.0) halves normalized core intensity monotonically; set_data restores exact CPU/GPU scale.
        volume.clim = (0.0, 2.0)
        img_mip_wide_clim = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        center_wide = int(img_mip_wide_clim[16, 16, 0])
        assert 80 <= center_wide < center_mip - 40
        volume.set_data(vol_data, clim=(0.0, 1.0))

        # 2. Attenuated MIP: attenuation=0 matches unattenuated MIP; attenuation=0.5 dims deep core behind r<=6.5 shell.
        volume.method = 'attenuated_mip'
        volume.attenuation = 0.0
        img_att0 = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        volume.attenuation = 0.5
        img_att_half = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        assert int(img_att0[16, 16, 0]) >= 200
        assert 40 < int(img_att_half[16, 16, 0]) < int(img_att0[16, 16, 0]) - 35

        # 3. Isosurface mode: threshold=0.65 hits 0.95 core above 0.40 shell; threshold=0.99 yields empty black center.
        volume.method = 'iso'
        volume.threshold = 0.65
        img_iso_hit = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        assert int(img_iso_hit[16, 16, :3].max()) >= 40
        volume.threshold = 0.99
        img_iso_miss = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        assert int(img_iso_miss[16, 16, :3].max()) == 0

        # 4. Translucent mode (requires alpha-ramp colormap so 0-voxels have alpha=0) + plane raycasting slice control.
        volume.cmap = Colormap([(0.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0, 0.8)])
        volume.method = 'translucent'
        img_trans = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        assert int(img_trans[16, 16, 0]) > int(img_trans[1, 1, 0]) == 0
        volume.cmap = 'grays'

        volume.method = 'mip'
        volume.raycasting_mode = 'plane'
        volume.plane_normal = (0.0, 1.0, 0.0)
        volume.plane_thickness = 2.0
        volume.plane_position = (7.5, 7.5, 7.5)
        img_plane_core = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        volume.plane_position = (7.5, 0.5, 7.5)
        img_plane_edge = np.array(canvas.render(size=CANVAS_SIZE, alpha=True), copy=True)
        assert int(img_plane_core[16, 16, 0]) > int(img_plane_edge[16, 16, 0])
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


def test_sci05_volume_queued_data_revisions_and_bounded_3d_texture_memory():
    """Verify queued Volume.set_data revisions before readback and bounded 3D texture memory retirement."""
    from vispy import _dawn, gloo, scene

    vol_a = _synthetic_volume()
    vol_b = np.zeros(VOL_SHAPE, dtype=np.float32)
    vol_b[10:15, 2:7, 2:7] = 1.0  # Shifted off-center bright block

    canvas = scene.SceneCanvas(
        app='dawn_headless', size=CANVAS_SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    attachments, depth_attachments, targets = [], [], []
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.TurntableCamera(
            fov=0.0, elevation=90.0, azimuth=0.0, scale_factor=20.0, center=(8.0, 8.0, 8.0)
        )
        volume = scene.visuals.Volume(
            vol_a, clim=(0.0, 1.0), method='mip', texture_format='auto', parent=view.scene
        )

        attachments = [gloo.RenderBuffer(CANVAS_SIZE[::-1], format='color') for _ in range(2)]
        depth_attachments = [gloo.RenderBuffer(CANVAS_SIZE[::-1], format='depth') for _ in range(2)]
        targets = [gloo.FrameBuffer(color=c, depth=d) for c, d in zip(attachments, depth_attachments)]

        def draw_fbo(fbo):
            canvas.push_fbo(fbo, (0, 0), CANVAS_SIZE)
            try:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            return _dawn.probe()['pending_draws']

        p0 = draw_fbo(targets[0])
        volume.set_data(vol_b, clim=(0.0, 1.0))
        p1 = draw_fbo(targets[1])
        assert 0 < p0 < p1, 'Both Volume.set_data revisions must remain queued prior to readback'

        probe_mid = _dawn.probe()
        # Bounded 16^3 float32 volume + FBOs + colormap/spatial filter LUTs must remain well below 8 MiB.
        assert 0 < probe_mid['live_texture_bytes'] < 8 * 1024 * 1024

        with targets[0]:
            frame_a = targets[0].read()
        with targets[1]:
            frame_b = targets[1].read()

        # Frame A had centered core bright; Frame B shifted bright block away from center!
        assert int(frame_a[16, 16, 0]) >= 200
        assert int(frame_b[16, 16, 0]) == 0
        assert int(frame_b[..., 0].max()) >= 200
    finally:
        for fbo in targets:
            fbo.delete()
        for rb in attachments + depth_attachments:
            rb.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()


def test_perf01_bounded_multi_visual_queue_batching_telemetry_no_optical_claim():
    """Verify multi-visual batched FBO queue equivalence and record bounded CPU/queue telemetry (no optical claim)."""
    from vispy import _dawn, gloo, scene

    canvas = scene.SceneCanvas(
        app='dawn_headless', size=CANVAS_SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    attachments, depth_attachments, targets = [], [], []
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.TurntableCamera(
            fov=45.0, elevation=20.0, azimuth=30.0, distance=24.0, center=(8.0, 8.0, 8.0)
        )

        mesh = scene.visuals.Box(
            width=4.0, height=4.0, depth=4.0, color=(0.8, 0.2, 0.1, 1.0), parent=view.scene
        )
        mesh.transform = scene.transforms.STTransform(translate=(3.0, 8.0, 8.0))
        markers = scene.visuals.Markers(method='instanced', scaling='fixed', parent=view.scene)
        markers.set_data(
            pos=np.array([[13.0, 8.0, 8.0], [8.0, 13.0, 8.0]], dtype=np.float32),
            size=5.0,
            face_color='cyan',
        )
        volume = scene.visuals.Volume(
            _synthetic_volume(), clim=(0.0, 1.0), method='mip', texture_format='auto', parent=view.scene
        )
        assert volume.parent is view.scene

        attachments = [gloo.RenderBuffer(CANVAS_SIZE[::-1], format='color') for _ in range(4)]
        depth_attachments = [gloo.RenderBuffer(CANVAS_SIZE[::-1], format='depth') for _ in range(4)]
        targets = [gloo.FrameBuffer(color=c, depth=d) for c, d in zip(attachments, depth_attachments)]
        azimuths = (15.0, 45.0, 75.0, 105.0)

        # Warm-up pipeline compilation before bounded queue/encode measurement.
        _ = canvas.render(size=CANVAS_SIZE, alpha=True)

        # Mode A: Queue all 4 multi-visual scene draws before reading back.
        t0 = time.perf_counter()
        pending_trace = []
        for fbo, az in zip(targets, azimuths):
            view.camera.azimuth = az
            canvas.push_fbo(fbo, (0, 0), CANVAS_SIZE)
            try:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            pending_trace.append(int(_dawn.probe()['pending_draws']))
        t_encode_batched = time.perf_counter() - t0
        assert pending_trace == sorted(pending_trace) and pending_trace[-1] >= 4

        batched_frames = []
        for fbo in targets:
            with fbo:
                batched_frames.append(fbo.read())
        t_total_batched = time.perf_counter() - t0

        # Mode B: Immediate draw + readback per frame -> must match batched frames pixel-for-pixel.
        t1 = time.perf_counter()
        immediate_frames = []
        for fbo, az in zip(targets, azimuths):
            view.camera.azimuth = az
            canvas.push_fbo(fbo, (0, 0), CANVAS_SIZE)
            try:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            with fbo:
                immediate_frames.append(fbo.read())
        t_total_immediate = time.perf_counter() - t1

        for f_batch, f_imm in zip(batched_frames, immediate_frames):
            np.testing.assert_array_equal(f_batch, f_imm)
            assert int(np.count_nonzero(f_batch[..., :3])) > 10

        probe_after = _dawn.probe()
        assert probe_after['pending_draws'] == 0
        telemetry = {
            'frames_compared': 4,
            'pending_draws_trace': pending_trace,
            'batched_encode_seconds': round(t_encode_batched, 6),
            'batched_total_seconds': round(t_total_batched, 6),
            'immediate_total_seconds': round(t_total_immediate, 6),
            'live_buffer_bytes': int(probe_after['live_buffer_bytes']),
            'live_texture_bytes': int(probe_after['live_texture_bytes']),
            'optical_display_timing_claimed': False,
        }
        assert telemetry['batched_encode_seconds'] >= 0.0
        if out_path := os.environ.get('VISPY_W2_4_PERF_TELEMETRY'):
            p = Path(out_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((json.dumps(telemetry, indent=2) + '\n').encode('utf-8'))
    finally:
        for fbo in targets:
            fbo.delete()
        for rb in attachments + depth_attachments:
            rb.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()
