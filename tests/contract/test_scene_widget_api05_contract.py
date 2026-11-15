# SPDX-License-Identifier: AGPL-3.0-only
"""Pure-CPU API-05 contracts for scene.visuals (37 aliases), ViewBox, Grid, and cameras."""
from __future__ import annotations

import numpy as np
import pytest

from vispy import scene, visuals
from vispy.scene import cameras as scene_cameras
from vispy.scene.cameras.perspective import PerspectiveCamera
from vispy.scene.node import Node
from vispy.scene.visuals import VisualNode, create_visual_node
from vispy.scene.widgets import Grid, ViewBox, Widget
from vispy.util.quaternion import Quaternion
from vispy.visuals.filters import Clipper

EXPECTED_37_SCENE_VISUALS = {
    'Arrow',
    'Axis',
    'Box',
    'ColorBar',
    'ComplexImage',
    'Compound',
    'Cube',
    'Ellipse',
    'Graph',
    'GridLines',
    'GridMesh',
    'Histogram',
    'Image',
    'InfiniteLine',
    'InstancedMesh',
    'Isocurve',
    'Isoline',
    'Isosurface',
    'Line',
    'LinePlot',
    'LinearRegion',
    'Markers',
    'Mesh',
    'MeshNormals',
    'Plane',
    'Polygon',
    'Rectangle',
    'RegularPolygon',
    'ScrollingLines',
    'Spectrogram',
    'Sphere',
    'SurfacePlot',
    'Text',
    'Tube',
    'Volume',
    'Windbarb',
    'XYZAxis',
}


class _CPUTimerStub:
    """Pure-CPU Timer stand-in so FlyCamera/MagnifyCamera contracts never open a GUI backend."""

    def __init__(self, interval='auto', connect=None, iterations=-1, start=False, app=None):
        self.interval = (1.0 / 60.0) if interval == 'auto' else float(interval)
        self.connect_cb = connect
        self.max_iterations = iterations
        self.running = bool(start)

    def start(self, interval=None, iterations=None):
        if interval is not None:
            self.interval = float(interval)
        self.running = True

    def stop(self):
        self.running = False


def test_all_37_scene_visuals_wrapper_aliases_and_visual_node_contracts():
    assert len(EXPECTED_37_SCENE_VISUALS) == 37
    exported = set(scene.visuals.__all__)
    assert exported == (EXPECTED_37_SCENE_VISUALS | {'VisualNode'})
    assert not hasattr(scene.visuals, 'Visual')

    for alias in sorted(EXPECTED_37_SCENE_VISUALS):
        cls = getattr(scene.visuals, alias)
        underlying = getattr(visuals, alias + 'Visual')
        assert isinstance(cls, type)
        assert issubclass(cls, VisualNode)
        assert issubclass(cls, Node)
        assert issubclass(cls, underlying)
        assert cls.__name__ == alias
        assert cls.__doc__ is not None
        assert f'visuals.{alias}Visual' in cls.__doc__
        assert 'parent : Node' in cls.__doc__
        assert 'name : string' in cls.__doc__

    class NotVisualName(visuals.BaseVisual):
        pass

    class NotBaseVisualSubclass:
        pass

    with pytest.raises(RuntimeError, match='must end with Visual'):
        create_visual_node(NotVisualName)
    with pytest.raises(RuntimeError, match='must end with Visual'):
        create_visual_node(NotBaseVisualSubclass)

    root = Node(name='root')
    verts = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 3.0, 1.0]], dtype=np.float32)
    faces = np.array([[0, 1, 2]], dtype=np.uint32)
    mesh = scene.visuals.Mesh(vertices=verts, faces=faces, shading=None, parent=root, name='tri')
    assert mesh.parent is root
    assert mesh.name == 'tri'
    assert mesh._visual_superclass is visuals.MeshVisual
    assert mesh.interactive is False
    mesh.interactive = True
    assert mesh.interactive is True

    mesh.opacity = 0.35
    assert np.isclose(mesh._opacity_filter.alpha, 0.35)

    assert mesh.picking is False
    assert mesh._picking_filter.enabled is False
    mesh.picking = True
    assert mesh.picking is True
    assert mesh._picking_filter.enabled is True
    assert mesh._vshare.gl_state['blend'] is False
    mesh.picking = False
    assert mesh.picking is False
    assert mesh._picking_filter.enabled is False

    owner = Node(name='clipper_owner')
    clip1 = Clipper(bounds=(0, 0, 10, 10))
    clip2 = Clipper(bounds=(2, 2, 8, 8))
    mesh._set_clipper(owner, clip1)
    assert mesh._clippers[owner] is clip1
    mesh._set_clipper(owner, clip2)
    assert mesh._clippers[owner] is clip2
    mesh._set_clipper(owner, None)
    assert owner not in mesh._clippers


def test_viewbox_camera_selectors_reuse_bounds_and_validation():
    vb = ViewBox(name='main_vb', size=(200, 100))
    assert vb.interactive is True
    assert vb.scene.clip_children is True
    assert isinstance(vb.camera, scene_cameras.BaseCamera)
    assert vb.is_in_scene(vb.camera)

    vb.camera = 'panzoom'
    pz = vb.camera
    assert isinstance(pz, scene_cameras.PanZoomCamera)
    assert vb.is_in_scene(pz)

    vb.camera = 'turntable'
    tt = vb.camera
    assert isinstance(tt, scene_cameras.TurntableCamera)
    assert vb.is_in_scene(tt)

    vb.camera = 'arcball'
    ab = vb.camera
    assert isinstance(ab, scene_cameras.ArcballCamera)

    # Switching back by string reuses the existing camera already attached to vb.scene.
    vb.camera = 'panzoom'
    assert vb.camera is pz

    verts = np.array([[-2.0, 1.0, -0.5], [4.0, 5.0, 3.5], [0.0, 2.0, 1.0]], dtype=np.float32)
    faces = np.array([[0, 1, 2]], dtype=np.uint32)
    mesh = scene.visuals.Mesh(vertices=verts, faces=faces, shading=None, parent=vb.scene)
    orphan = Node()
    assert vb.is_in_scene(mesh) is True
    assert vb.is_in_scene(orphan) is False

    bounds_all = vb.get_scene_bounds()
    assert np.allclose(bounds_all[0], (-2.0, 4.0))
    assert np.allclose(bounds_all[1], (1.0, 5.0))
    assert np.allclose(bounds_all[2], (-0.5, 3.5))
    assert np.allclose(vb.get_scene_bounds(dim=1), (1.0, 5.0))

    with pytest.raises(TypeError, match='must be None, str, or Camera'):
        ViewBox(camera=object())
    with pytest.raises(ValueError, match='Not a camera object'):
        vb.camera = object()


def test_grid_proportional_solver_indexing_and_collision_contracts():
    grid = Grid(spacing=4, size=(124, 84))
    v00 = grid[0, 0]
    v01 = grid[0, 1]
    v1_span = grid[1, 0:2]

    assert isinstance(v00, ViewBox)
    assert isinstance(v01, ViewBox)
    assert isinstance(v1_span, ViewBox)
    assert grid.grid_size == (2, 2)
    assert grid[0, 0] is v00
    assert grid[0, 1] is v01
    assert grid[1, 0:2] is v1_span

    with pytest.raises(ValueError, match='collision'):
        _ = grid[1, 0]
    with pytest.raises(ValueError, match='step must be one or None'):
        _ = grid[0:2:2, 0]
    with pytest.raises(ValueError, match='Incorrect index'):
        _ = grid[0, 0, 0]
    with pytest.raises(ValueError, match='indices must be slices or integers'):
        _ = grid['bad', 0]
    with pytest.raises(ValueError, match='cannot send kwargs if widget is given'):
        grid.add_widget(Widget(), row=2, col=0, bgcolor='black')

    grid._update_child_widget_dim()
    assert np.allclose(v00.pos, (0, 0))
    assert np.allclose(v00.size, (60, 40))
    assert np.allclose(v01.pos, (64, 0))
    assert np.allclose(v01.size, (60, 40))
    assert np.allclose(v1_span.pos, (0, 44))
    assert np.allclose(v1_span.size, (124, 40))

    grid.next_row()
    v20 = grid.add_view(camera='panzoom')
    assert isinstance(v20, ViewBox)
    assert grid.grid_size == (3, 2)
    grid.remove_widget(v20)
    assert grid.grid_size == (2, 2)
    assert all(entry[-1] is not v20 for entry in grid._grid_widgets.values())


def test_camera_classes_state_transforms_and_cpu_contracts(monkeypatch):
    import vispy.scene.cameras.fly as fly_mod
    import vispy.scene.cameras.magnify as mag_mod

    monkeypatch.setattr(fly_mod, 'Timer', _CPUTimerStub)
    monkeypatch.setattr(mag_mod, 'Timer', _CPUTimerStub)

    for cam_type, expected_cls in [
        (None, scene_cameras.BaseCamera),
        ('base', scene_cameras.BaseCamera),
        ('panzoom', scene_cameras.PanZoomCamera),
        ('perspective', PerspectiveCamera),
        ('turntable', scene_cameras.TurntableCamera),
        ('arcball', scene_cameras.ArcballCamera),
        ('fly', scene_cameras.FlyCamera),
    ]:
        cam = scene_cameras.make_camera(cam_type)
        assert isinstance(cam, expected_cls)

    # MagnifyCamera / Magnify1DCamera are constructed directly, not registered in make_camera().
    for direct_only in ('magnify', 'magnify1d', 'nonexistent_camera_kind'):
        with pytest.raises(KeyError):
            scene_cameras.make_camera(direct_only)

    pz = scene_cameras.PanZoomCamera(rect=(0.0, 0.0, 10.0, 20.0), aspect=1.0, flip=(True, False, False))
    pz.zoom(0.5, center=(5.0, 10.0))
    pz_state = pz.get_state()
    pz_copy = scene_cameras.PanZoomCamera()
    pz_copy.set_state(pz_state)
    assert np.allclose(pz_copy.rect.pos, pz.rect.pos)
    assert np.allclose(pz_copy.rect.size, pz.rect.size)

    persp = PerspectiveCamera(fov=55.0, scale_factor=-12.5, center=(1.0, 2.0, 3.0))
    assert np.isclose(persp.fov, 55.0)
    assert np.isclose(persp.scale_factor, 12.5)
    assert np.allclose(persp.center, (1.0, 2.0, 3.0))
    with pytest.raises(ValueError, match='0 <= fov <= 180'):
        persp.fov = -1.0
    persp.fov = 180.0
    assert np.isclose(persp.fov, 180.0)
    with pytest.raises(ValueError, match='0 <= fov <= 180'):
        persp.fov = 180.5

    tt = scene_cameras.TurntableCamera(
        fov=45.0, elevation=20.0, azimuth=30.0, roll=5.0, distance=6.0, scale_factor=6.0, center=(0.0, 0.0, 0.0)
    )
    tt.orbit(azim=15.0, elev=100.0)
    assert np.isclose(tt.azimuth, 45.0)
    assert np.isclose(tt.elevation, 90.0)
    tt_state = tt.get_state()
    tt2 = scene_cameras.TurntableCamera()
    tt2.set_state(tt_state)
    assert np.isclose(tt2.azimuth, 45.0) and np.isclose(tt2.elevation, 90.0)

    ab = scene_cameras.ArcballCamera(fov=40.0, distance=5.0, scale_factor=5.0, center=(0.0, 0.0, 0.0))
    q = Quaternion.create_from_axis_angle(0.5, 0.0, 1.0, 0.0)
    ab._quaternion = q
    ab_state = ab.get_state()
    ab2 = scene_cameras.ArcballCamera()
    ab2.set_state(ab_state)
    assert np.allclose([ab2._quaternion.w, ab2._quaternion.x, ab2._quaternion.y, ab2._quaternion.z],
                       [q.w, q.x, q.y, q.z])

    fly = scene_cameras.FlyCamera(fov=65.0)
    fly.auto_roll = False
    assert fly.auto_roll is False
    rot = Quaternion.create_from_axis_angle(0.25, 1.0, 0.0, 0.0)
    fly.rotation1 = rot
    assert np.isclose(abs(fly.rotation.norm() - 1.0), 0.0, atol=1e-6)
    assert 'W' in fly.keymap and 'S' in fly.keymap

    mag = scene_cameras.MagnifyCamera(size_factor=0.3, radius_ratio=0.8, mag=3.0, radii=(15.0, 30.0))
    mag.mag.center = (50.0, 50.0)
    pts = np.array([[50.0, 50.0, 0.0], [52.0, 50.0, 0.0], [150.0, 50.0, 0.0]], dtype=np.float32)
    mapped = mag.mag.map(pts)
    # Center stays fixed; near-center point expands away from center; exterior point outside outer radius stays unshifted.
    assert np.allclose(mapped[0, :2], [50.0, 50.0], atol=1e-4)
    assert (mapped[1, 0] - 50.0) > (pts[1, 0] - 50.0)
    assert np.allclose(mapped[2, :2], [150.0, 50.0], atol=1e-4)
    inv = mag.mag.imap(mapped)
    assert np.allclose(inv[:, :2], pts[:, :2], atol=1e-2)

    # Magnify1DCamera binds Magnify1DTransform (1D x-axis glsl_map preserving pos.y + MagnifyTransform CPU map/imap).
    from vispy.visuals.transforms.nonlinear import Magnify1DTransform, MagnifyTransform

    mag1d = scene_cameras.Magnify1DCamera(mag=2.5, radii=(10.0, 25.0))
    assert isinstance(mag1d.mag, Magnify1DTransform) and isinstance(mag1d.mag, MagnifyTransform)
    assert 'pos.x - $center.x' in mag1d.mag.glsl_map and 'pos.y, pos.z, pos.w' in mag1d.mag.glsl_map
    mag1d.mag.center = (40.0, 20.0)
    pts1d = np.array([[40.0, 20.0, 0.0], [42.0, 20.0, 0.0], [100.0, 20.0, 0.0]], dtype=np.float32)
    mapped1d = mag1d.mag.map(pts1d)
    assert np.allclose(mapped1d[0, :2], [40.0, 20.0], atol=1e-4)
    assert (mapped1d[1, 0] - 40.0) > (pts1d[1, 0] - 40.0)
    assert np.allclose(mapped1d[2, :2], [100.0, 20.0], atol=1e-4)
    assert np.allclose(mag1d.mag.imap(mapped1d)[:, :2], pts1d[:, :2], atol=1e-2)
