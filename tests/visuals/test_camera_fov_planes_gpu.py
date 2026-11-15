# SPDX-License-Identifier: AGPL-3.0-only
"""GPU acceptance for SCI-03 and SCI-05 (E04): Arcball/Fly/Perspective/Turntable/Magnify FOV, planes, depth, and polygon offset."""
from __future__ import annotations

import gc

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (48, 48)


def _quad_mesh_data(half_extent, z):
    h = float(half_extent)
    z = float(z)
    verts = np.array(
        [[-h, -h, z], [h, -h, z], [-h, h, z], [h, h, z]],
        dtype=np.float32,
    )
    faces = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
    return verts, faces


def _stop_camera_timers(cam):
    for attr in ('timer', '_timer'):
        t = getattr(cam, attr, None)
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass


@pytest.mark.parametrize('camera_kind', ['turntable', 'arcball'])
def test_camera_fov_extremes_perspective_landmark_scaling_and_pose_restoration(camera_kind):
    """Verify FOV extremes (0 orthographic, 25, 60, 110 deg) landmark area law and fresh-scene equivalence."""
    from vispy import _dawn, scene
    from vispy.util.quaternion import Quaternion

    def build_scene(fov, mutated=False):
        canvas = scene.SceneCanvas(
            app='dawn_headless', size=SIZE, show=False, bgcolor='black', config={'samples': 0}
        )
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        if camera_kind == 'turntable':
            cam = scene.cameras.TurntableCamera(
                fov=fov,
                elevation=25.0 if mutated else 0.0,
                azimuth=35.0 if mutated else 0.0,
                distance=5.0,
                center=(0.0, 0.0, 0.0),
            )
            if fov == 0.0:
                cam.scale_factor = 4.0
        else:
            cam = scene.cameras.ArcballCamera(
                fov=fov,
                distance=5.0,
                center=(0.0, 0.0, 0.0),
            )
            if fov == 0.0:
                cam.scale_factor = 4.0
            if mutated:
                cam._quaternion = Quaternion.create_from_axis_angle(0.45, 0.0, 1.0, 0.0)
        view.camera = cam

        # Note: in VisPy Turntable/Arcball at elevation=0, azimuth=0, camera looks along +Y (or Z up).
        # Using a symmetric 3D cube centered at origin guarantees viewpoint-invariant projected area vs FOV!
        cube = scene.visuals.Box(
            width=1.4, height=1.4, depth=1.4, color=(1.0, 0.25, 0.0, 1.0), parent=view.scene
        )
        cube.set_gl_state(depth_test=True, blend=False, cull_face=False)
        return canvas, cam

    areas = {}
    for fov in (0.0, 25.0, 60.0, 110.0):
        canvas, cam = build_scene(fov, mutated=False)
        try:
            img = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
            fg = int(np.count_nonzero(img[..., 0] > 100))
            assert fg > 0, f'Blank projection for {camera_kind} fov={fov}'
            areas[fov] = fg
        finally:
            _stop_camera_timers(cam)
            canvas.close()
            gc.collect()
            _dawn.process_events()

    # Analytic perspective projection law: apparent projected area shrinks strictly as FOV widens (25 -> 60 -> 110).
    assert areas[25.0] > areas[60.0] > areas[110.0] >= 4

    # Fresh-scene equivalence and byte-exact restoration under camera pose + FOV mutation.
    canvas, cam = build_scene(45.0, mutated=False)
    fresh = fresh_cam = None
    try:
        before = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        cam.fov = 75.0
        if camera_kind == 'turntable':
            cam.elevation = 25.0
            cam.azimuth = 35.0
        else:
            cam._quaternion = Quaternion.create_from_axis_angle(0.45, 0.0, 1.0, 0.0)
            cam.view_changed()
        changed = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        assert np.count_nonzero(np.any(changed != before, axis=2)) > 20

        fresh, fresh_cam = build_scene(75.0, mutated=True)
        expected_changed = np.array(fresh.render(size=SIZE, alpha=True), copy=True)
        assert int(np.abs(changed.astype(np.int16) - expected_changed.astype(np.int16)).max()) <= 1
        _stop_camera_timers(fresh_cam)
        fresh.close()
        fresh = None

        # Restore original pose & FOV -> must match `before` byte-for-byte.
        cam.fov = 45.0
        if camera_kind == 'turntable':
            cam.elevation = 0.0
            cam.azimuth = 0.0
        else:
            cam._quaternion = Quaternion()
            cam.view_changed()
        restored = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_array_equal(restored, before)
    finally:
        if fresh is not None:
            _stop_camera_timers(fresh_cam)
            fresh.close()
        _stop_camera_timers(cam)
        canvas.close()
        gc.collect()
        _dawn.process_events()


def test_fly_and_perspective_camera_near_far_occlusion_and_polygon_offset_stability():
    """Verify FlyCamera 3D pose landmarks and PerspectiveCamera coplanar polygon_offset depth stability."""
    from vispy import _dawn, gloo, scene
    from vispy.util.quaternion import Quaternion

    canvas = scene.SceneCanvas(
        app='dawn_headless', size=SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    fly_cam = None
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        fly_cam = scene.cameras.FlyCamera(fov=60.0)
        view.camera = fly_cam
        # Assign pose AFTER view.camera attachment (FlyCamera._set_range resets center & rotation1 on attach).
        fly_cam.center = (0.0, 0.0, 5.0)
        fly_cam.rotation1 = Quaternion()
        fly_cam.rotation2 = Quaternion()
        fly_cam.scale_factor = 1.0
        fly_cam.view_changed()

        # Near red box at z=+2.0 (3 units ahead) occludes larger far blue box at z=-1.0 (6 units ahead) along -Z.
        near_box = scene.visuals.Box(
            width=0.8, height=0.8, depth=0.8, color=(1.0, 0.0, 0.0, 1.0), parent=view.scene
        )
        near_box.transform = scene.transforms.STTransform(translate=(0.0, 0.0, 2.0))
        near_box.set_gl_state(depth_test=True, blend=False, cull_face=False)

        far_box = scene.visuals.Box(
            width=3.0, height=3.0, depth=0.4, color=(0.0, 0.0, 1.0, 1.0), parent=view.scene
        )
        far_box.transform = scene.transforms.STTransform(translate=(0.0, 0.0, -1.0))
        far_box.set_gl_state(depth_test=True, blend=False, cull_face=False)

        img_centered = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        # Center pixel hits near red box; outer ring hits far blue box.
        np.testing.assert_allclose(img_centered[24, 24], [255, 0, 0, 255], atol=2)
        assert int(np.count_nonzero(img_centered[..., 2] > 200)) > 40

        # Yaw FlyCamera around +Y away from -Z sightline and restore; verify pose changes and restores cleanly.
        orig_rot = Quaternion(fly_cam.rotation1.w, fly_cam.rotation1.x, fly_cam.rotation1.y, fly_cam.rotation1.z)
        fly_cam.rotation1 = Quaternion.create_from_axis_angle(0.45, 0.0, 1.0, 0.0) * orig_rot
        fly_cam.view_changed()
        img_yawed = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        assert np.count_nonzero(np.any(img_yawed != img_centered, axis=2)) > 20

        fly_cam.rotation1 = orig_rot
        fly_cam.view_changed()
        img_restored = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_array_equal(img_restored, img_centered)
    finally:
        _stop_camera_timers(fly_cam)
        canvas.close()
        gc.collect()
        _dawn.process_events()

    # Coplanar decal stability with TurntableCamera + polygon_offset_fill (-2, -2 vs +2, +2).
    canvas2 = scene.SceneCanvas(
        app='dawn_headless', size=SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    try:
        canvas2.set_current()
        view2 = canvas2.central_widget.add_view(border_width=0)
        view2.camera = scene.cameras.TurntableCamera(
            fov=50.0, elevation=90.0, azimuth=0.0, distance=4.0, center=(0.0, 0.0, 0.0)
        )
        v_base, f_base = _quad_mesh_data(1.2, z=0.0)
        v_decal, f_decal = _quad_mesh_data(0.6, z=0.0)

        base_mesh = scene.visuals.Mesh(
            vertices=v_base, faces=f_base, color=(0.0, 0.0, 1.0, 1.0), shading=None, parent=view2.scene
        )
        base_mesh.order = 0
        base_mesh.set_gl_state(depth_test=True, depth_func='lequal', blend=False, cull_face=False)

        decal_mesh = scene.visuals.Mesh(
            vertices=v_decal, faces=f_decal, color=(0.0, 1.0, 0.0, 1.0), shading=None, parent=view2.scene
        )
        decal_mesh.order = 1
        decal_mesh.set_gl_state(
            depth_test=True,
            depth_func='lequal',
            polygon_offset_fill=True,
            polygon_offset=(-2.0, -2.0),
            blend=False,
            cull_face=False,
        )

        # Push decal toward camera (-2, -2): center must be 100% green without z-fighting.
        gloo.set_polygon_offset(-2.0, -2.0)
        img_front = np.array(canvas2.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_allclose(img_front[24, 24], [0, 255, 0, 255], atol=2)

        # Push decal behind coplanar base (+2, +2) with depth_func='less': center must stay 100% blue!
        decal_mesh.set_gl_state(
            depth_test=True,
            depth_func='less',
            polygon_offset_fill=True,
            polygon_offset=(2.0, 2.0),
            blend=False,
            cull_face=False,
        )
        gloo.set_polygon_offset(2.0, 2.0)
        img_back = np.array(canvas2.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_allclose(img_back[24, 24], [0, 0, 255, 255], atol=2)
    finally:
        canvas2.close()
        gc.collect()
        _dawn.process_events()


@pytest.mark.parametrize('is_1d', [False, True])
def test_magnify_and_magnify1d_camera_lens_landmarks_and_restoration(is_1d):
    """Verify MagnifyCamera and Magnify1DCamera expand central feature within lens radii and restore cleanly."""
    from vispy import _dawn, scene

    canvas = scene.SceneCanvas(
        app='dawn_headless', size=SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    cam = None
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        cam_cls = scene.cameras.Magnify1DCamera if is_1d else scene.cameras.MagnifyCamera
        cam = cam_cls(rect=(0, 0, 48, 48), aspect=1.0, mag=1.0, radii=(8.0, 18.0))
        cam.mag.center = (24.0, 24.0)
        view.camera = cam

        # Small central red square [21..27, 21..27] + outer corner blue reference square [2..8, 2..8].
        center_sq = scene.visuals.Mesh(
            vertices=np.array([[21, 21, 0], [27, 21, 0], [21, 27, 0], [27, 27, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(1.0, 0.0, 0.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        center_sq.set_gl_state(blend=False, depth_test=False, cull_face=False)

        corner_sq = scene.visuals.Mesh(
            vertices=np.array([[2, 2, 0], [8, 2, 0], [2, 8, 0], [8, 8, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(0.0, 0.0, 1.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        corner_sq.set_gl_state(blend=False, depth_test=False, cull_face=False)

        unmagnified = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        red_before = int(np.count_nonzero(unmagnified[..., 0] > 200))
        blue_before = int(np.count_nonzero(unmagnified[..., 2] > 200))
        assert red_before > 0 and blue_before > 0

        cam.mag.mag = 3.0
        cam.view_changed()
        magnified = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        red_after = int(np.count_nonzero(magnified[..., 0] > 200))
        blue_after = int(np.count_nonzero(magnified[..., 2] > 200))
        # Central red feature inside lens radius grows substantially; exterior blue corner outside radii=18 is unchanged!
        assert red_after > red_before * (2 if is_1d else 3)
        assert blue_after == blue_before

        cam.mag.mag = 1.0
        cam.view_changed()
        restored = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_array_equal(restored, unmagnified)
    finally:
        _stop_camera_timers(cam)
        canvas.close()
        gc.collect()
        _dawn.process_events()
