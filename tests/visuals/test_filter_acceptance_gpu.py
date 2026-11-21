# SPDX-License-Identifier: AGPL-3.0-only
"""Exact primitive IDs, colormap bands, and analytic mesh lighting."""
import gc

import numpy as np
import pytest

from vispy import scene
from vispy.color import Colormap
from vispy.visuals.filters import (
    FacePickingFilter, InstancedShadingFilter, MarkerPickingFilter,
    PrimitivePickingFilter, ShadingFilter, ZColormapFilter,
)


pytestmark = pytest.mark.gpu
SIZE = (64, 32)
LEFT, RIGHT, BACKGROUND = (12, 12), (12, 44), (28, 32)
VERTICES = np.array([[4, 4, 0], [24, 4, 0], [4, 24, 0],
                     [36, 4, 0], [56, 4, 0], [36, 24, 0]], np.float32)
FACES = np.array([[0, 1, 2], [3, 4, 5]], np.uint32)
WHITE = [255, 255, 255, 255]


@pytest.fixture
def filter_scene():
    from vispy import _dawn

    canvas = scene.SceneCanvas(app='dawn_headless', size=SIZE, show=False,
                               bgcolor=(0, 0, 0, 0), config={'samples': 0})
    canvas.set_current()
    try:
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, *SIZE),
                                                 flip=(False, True, False))
        yield view.scene, lambda: canvas.render(alpha=True)
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


def _mesh(parent, *, vertices=VERTICES, faces=FACES, **kwargs):
    mesh = scene.Mesh(vertices=vertices, faces=faces, shading=None, parent=parent, **kwargs)
    mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)
    return mesh


def _ids(image):
    return tuple(int.from_bytes(bytes(image[point]), 'little')
                 for point in (LEFT, RIGHT, BACKGROUND))


def test_face_picking_replacement_empty_and_detach(filter_scene):
    parent, render = filter_scene
    mesh = _mesh(parent, color='white')
    picking = FacePickingFilter()
    mesh.attach(picking)
    picking.enabled = True
    assert _ids(render()) == (1, 2, 0)
    mesh.set_data(vertices=VERTICES, faces=FACES[::-1].copy())
    assert _ids(render()) == (2, 1, 0)
    mesh.set_data(vertices=VERTICES, faces=np.empty((0, 3), np.uint32))
    assert _ids(render()) == (0, 0, 0)
    mesh.set_data(vertices=VERTICES, faces=FACES[1:])
    assert _ids(render()) == (0, 1, 0)
    picking.enabled = False
    np.testing.assert_array_equal(render()[RIGHT], WHITE)
    picking.enabled = True
    assert _ids(render()) == (0, 1, 0)
    mesh.detach(picking)
    np.testing.assert_array_equal(render()[RIGHT], WHITE)


@pytest.mark.parametrize('method', ['points', 'instanced'])
def test_marker_picking_empty_invalid_and_transparency(filter_scene, method):
    parent, render = filter_scene
    markers = scene.Markers(method=method, parent=parent)
    markers.set_gl_state(blend=False, depth_test=False)
    picking = MarkerPickingFilter(discard_transparent=True)
    markers.attach(picking)
    picking.enabled = True
    positions = np.array([[12, 12], [44, 12]], np.float32)
    markers.set_data(positions, size=12, edge_width=0, face_color='white')
    assert _ids(render()) == (1, 2, 0)
    with pytest.raises(ValueError, match='symbols'):
        markers.set_data(positions, symbol='invalid-symbol')
    assert _ids(render()) == (1, 2, 0)
    markers.set_data()
    assert _ids(render()) == (0, 0, 0)
    markers.set_data(positions[::-1].copy(), size=12, edge_width=0,
                     face_color=[(1, 1, 1, 1), (1, 0, 0, 0)])
    assert _ids(render()) == (0, 1, 0)
    picking.discard_transparent = False
    assert _ids(render()) == (2, 1, 0)
    picking.enabled = False
    np.testing.assert_array_equal(render()[RIGHT], WHITE)


def test_primitive_picking_custom_ids_dtype_retry_and_subscription(filter_scene):
    class ExplicitIDs(PrimitivePickingFilter):
        values = np.repeat(np.array([0x01020304, 0xA1B2C3D4], np.uint32), 3)
        calls = 0

        def _get_picking_ids(self):
            self.calls += 1
            return self.values

    parent, render = filter_scene
    colors = np.array([[1, 1, 1, 1], [1, 0, 0, 0]], np.float32)
    mesh = _mesh(parent, face_colors=colors)
    picking = ExplicitIDs(discard_transparent=True)
    mesh.attach(picking)
    picking.enabled = True
    assert _ids(render()) == (0x01020304, 0, 0)
    picking.discard_transparent = False
    assert _ids(render()) == (0x01020304, 0xA1B2C3D4, 0)
    picking.values = picking.values.astype(np.int64)
    with pytest.raises(ValueError, match='ids must be uint32'):
        picking.enabled = True
    picking.values = np.repeat(np.array([7, 41], np.uint32), 3)
    picking.enabled = True
    assert _ids(render()) == (7, 41, 0)
    mesh.detach(picking)
    before = picking.calls
    mesh.set_data(vertices=VERTICES, faces=FACES, color='white')
    np.testing.assert_array_equal(render()[RIGHT], WHITE)
    assert picking.calls == before


def test_zcolormap_bands_and_reattach(filter_scene):
    parent, render = filter_scene
    vertices = VERTICES.copy()
    vertices[3:, 2] = 1
    mesh = _mesh(parent, vertices=vertices, color='green')
    cmap = Colormap(['red', 'blue'])
    zfilter = ZColormapFilter(cmap, zrange=(0, 1))
    mesh.attach(zfilter)
    image = render()
    np.testing.assert_allclose(image[LEFT], [255, 0, 0, 255], atol=1)
    np.testing.assert_allclose(image[RIGHT], [0, 0, 255, 255], atol=1)
    vertices[:3, 2] = 0.5
    mesh.set_data(vertices=vertices, faces=FACES, color='green')
    np.testing.assert_allclose(render()[LEFT], [128, 0, 128, 255], atol=1)
    mesh.detach(zfilter)
    np.testing.assert_array_equal(render()[LEFT], [0, 128, 0, 255])
    # A degenerate range remains accepted at construction.
    ZColormapFilter(cmap, zrange=(1, 1))
    with pytest.raises(KeyError, match='missing-swarm-colormap'):
        ZColormapFilter('missing-swarm-colormap', zrange=(0.5, 1.5))
    np.testing.assert_array_equal(render()[LEFT], [0, 128, 0, 255])
    zfilter = ZColormapFilter(cmap, zrange=(0.5, 1.5))
    mesh.attach(zfilter)
    image = render()
    np.testing.assert_allclose(image[LEFT], [255, 0, 0, 255], atol=1)
    np.testing.assert_allclose(image[RIGHT], [128, 0, 128, 255], atol=1)

    # Both the mesh and filter now sample distinct LUTs in the same shader.
    mesh.cmap = Colormap(['lime', 'white'], interpolation='zero')
    mesh.clim = (0, 1)
    mesh.set_data(vertices=vertices, faces=FACES,
                  vertex_values=np.repeat([0, 1], 3).astype(np.float32))
    image = render()
    np.testing.assert_allclose(image[LEFT], [255, 0, 0, 255], atol=1)
    np.testing.assert_allclose(image[RIGHT], [128, 0, 128, 255], atol=1)
    mesh.detach(zfilter)
    image = render()
    np.testing.assert_array_equal(image[LEFT], [0, 255, 0, 255])
    np.testing.assert_array_equal(image[RIGHT], WHITE)


def test_shading_filter_lambert_invalid_mode_and_restore(filter_scene):
    parent, render = filter_scene
    mesh = _mesh(parent, color='white')
    # The triangles are clockwise in the render coordinate system (y up).
    shading = ShadingFilter(shading='smooth', light_dir=(0, 0, 1),
                            ambient_light=(1, 1, 1, 0.25),
                            diffuse_light=(1, 1, 1, 0.5), shininess=0)
    mesh.attach(shading)
    np.testing.assert_allclose(render()[LEFT], [191, 191, 191, 255], atol=1)
    with pytest.raises(ValueError, match='Invalid direction'):
        shading.light_dir = (0, 1)
    shading.light_dir = (0, 0, -1)
    np.testing.assert_allclose(render()[LEFT], [64, 64, 64, 255], atol=1)
    mesh.detach(shading)
    np.testing.assert_array_equal(render()[LEFT], WHITE)


def test_instanced_shading_normals_and_empty_stream_recovery(filter_scene):
    parent, render = filter_scene
    # Tilt the second plane: its transformed unit normal has z=1/2.
    identity = np.eye(3, dtype=np.float32)
    tilt = np.array([[0.5, 0, -np.sqrt(3) / 2], [0, 1, 0],
                     [np.sqrt(3) / 2, 0, 0.5]], np.float32)
    mesh = scene.InstancedMesh(
        vertices=VERTICES[:3], faces=FACES[:1], color='white', shading=None,
        instance_positions=np.array([[0, 0, 0], [36, 0, 0]], np.float32),
        instance_transforms=np.stack([identity, tilt]), parent=parent)
    mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)
    shading = InstancedShadingFilter(shading='smooth', light_dir=(0, 0, 1),
                                     ambient_light=(1, 1, 1, 0.25),
                                     diffuse_light=(1, 1, 1, 0.5), shininess=0)
    mesh.attach(shading)
    image = render()
    np.testing.assert_allclose(image[LEFT], [191, 191, 191, 255], atol=1)
    np.testing.assert_allclose(image[12, 40], [128, 128, 128, 255], atol=1)
    mesh.instance_transforms = np.empty((0, 3, 3), np.float32)
    assert not np.any(render())
    mesh.instance_transforms = np.stack([identity, identity])
    np.testing.assert_allclose(render()[RIGHT], [191, 191, 191, 255], atol=1)
