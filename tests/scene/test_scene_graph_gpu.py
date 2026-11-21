# SPDX-License-Identifier: AGPL-3.0-only
"""Rendered scene graph, wrapper, filter and transform acceptance."""
import numpy as np
import pytest

from vispy import _dawn, scene, visuals
from vispy.scene import filters, transforms
from vispy.scene.node import Node

pytestmark = pytest.mark.gpu
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)


def box(parent, center, color='red', size=(12, 12)):
    return scene.visuals.Rectangle(center=center, width=size[0], height=size[1],
                                   color=color, parent=parent)


def pixel(frame, x, y, rgb):
    np.testing.assert_array_equal(frame[y, x], rgb)


def test_scene_filters_exports_and_color_coefficients(canvas_factory, draw):
    exports = ('Filter', 'PrimitivePickingFilter', 'Clipper', 'Alpha', 'ColorFilter',
               'IsolineFilter', 'ZColormapFilter', 'PickingFilter', 'MarkerPickingFilter',
               'TextureFilter', 'ShadingFilter', 'InstancedShadingFilter',
               'WireframeFilter', 'FacePickingFilter')
    assert all(getattr(filters, name) is getattr(visuals.filters, name) for name in exports)
    canvas = canvas_factory()
    white = box(canvas.scene, (25, 30), 'white')
    white.attach(filters.ColorFilter((.25, .5, 1, 1)))
    white.attach(filters.Alpha(.5))
    white.set_gl_state('translucent', depth_test=False, cull_face=False)
    frame = draw(canvas)
    np.testing.assert_allclose(frame[30, 25], (32, 64, 128), atol=1)
    pixel(frame, 5, 5, BLACK)


def test_scene_filters_rejected_attachment_and_owner_transfer(canvas_factory, draw):
    canvas = canvas_factory()
    left = box(canvas.scene, (25, 30), 'white')
    right = box(canvas.scene, (60, 30), 'white')
    tint = filters.ColorFilter((0, 0, 1, 1))
    with pytest.raises(AttributeError, match='_attach'):
        left.attach(object())
    left.attach(tint)
    pixel(draw(canvas), 25, 30, BLUE)
    left.detach(tint)
    right.attach(tint)
    frame = draw(canvas)
    pixel(frame, 25, 30, (255, 255, 255))
    pixel(frame, 60, 30, BLUE)


def test_node_parent_transform_order_visibility_and_view_clip(canvas_factory, draw):
    canvas = canvas_factory()
    view = scene.widgets.ViewBox(parent=canvas.scene, pos=(10, 10), size=(50, 55))
    first = Node(parent=view.scene)
    second = Node(parent=view.scene)
    first.transform = transforms.STTransform(translate=(10, 0))
    second.transform = transforms.STTransform(translate=(20, 0))
    box(first, (20, 25), size=(36, 20))
    box(second, (20, 25), 'blue', size=(36, 20))
    second.order = -1
    frame = draw(canvas)
    pixel(frame, 40, 35, RED)
    pixel(frame, 58, 35, BLUE)
    pixel(frame, 62, 35, BLACK)
    first.visible = False
    pixel(draw(canvas), 40, 35, BLUE)
    view.scene.clip_children = False
    pixel(draw(canvas), 62, 35, BLUE)
    view.scene.clip_children = True
    pixel(draw(canvas), 62, 35, BLACK)


def test_node_detach_reparent_updates_only_new_owner(canvas_factory, draw, monkeypatch):
    first, second = canvas_factory(), canvas_factory()
    left = scene.widgets.ViewBox(parent=first.scene, pos=(10, 0), size=(40, 60))
    right = scene.widgets.ViewBox(parent=second.scene, pos=(60, 10), size=(40, 60))
    subtree = Node(parent=left.scene)
    child = box(subtree, (20, 25), size=(60, 12))
    pixel(draw(first), 30, 25, RED)
    subtree.parent = None
    assert child.canvas is None
    pixel(draw(first), 30, 25, BLACK)
    subtree.parent = right.scene
    assert child.canvas is second
    updates = []
    monkeypatch.setattr(first, 'update', lambda **kwargs: updates.append('old'))
    monkeypatch.setattr(second, 'update', lambda **kwargs: updates.append('new'))
    subtree.update()
    assert updates == ['new']
    frame = draw(second)
    pixel(frame, 80, 35, RED)
    pixel(frame, 58, 35, BLACK)
    pixel(draw(first), 30, 25, BLACK)


def test_grouped_viewbox_overlay_reparents_without_duplicate_clipping(canvas_factory, draw):
    canvas = canvas_factory()
    view = scene.widgets.ViewBox(parent=canvas.scene, pos=(10, 10), size=(40, 40))
    overlay = Node(parent=view)
    branch = Node(parent=overlay)
    child = box(branch, (35, 20), size=(30, 10))
    assert dict(child._clippers) == {view: view.clipper}
    frame = draw(canvas)
    pixel(frame, 48, 30, RED)
    pixel(frame, 53, 30, BLACK)

    overlay.parent = view.scene
    assert dict(child._clippers) == {view.scene: view.scene.clipper}
    view.scene.clip_children = False
    assert not child._clippers
    pixel(draw(canvas), 53, 30, RED)

    view.scene.clip_children = True
    assert dict(child._clippers) == {view.scene: view.scene.clipper}
    pixel(draw(canvas), 53, 30, BLACK)


def test_scene_transforms_exports_and_affine_polar_shader(canvas_factory, draw):
    assert transforms.__all__ == visuals.transforms.__all__
    assert all(getattr(transforms, name) is getattr(visuals.transforms, name)
               for name in transforms.__all__)
    canvas = canvas_factory()
    marker = scene.visuals.Markers(pos=np.array([[0., 20., 0.], [np.pi / 2, 20., 0.]]),
                                   size=9, face_color=['red', 'blue'],
                                   edge_width=0, parent=canvas.scene)
    marker.transform = transforms.ChainTransform([
        transforms.STTransform(scale=(2, 1), translate=(15, 20)),
        transforms.PolarTransform(),
    ])
    np.testing.assert_allclose(marker.transform.map((0, 20, 0))[:3], (55, 20, 0))
    np.testing.assert_allclose(marker.transform.imap((15, 40, 0))[:3],
                               (np.pi / 2, 20, 0))
    frame = draw(canvas)
    pixel(frame, 55, 20, RED)
    pixel(frame, 15, 40, BLUE)


def test_scene_transforms_singular_inverse_then_shader_recovers(canvas_factory, draw):
    canvas = canvas_factory()
    marker = scene.visuals.Markers(pos=np.array([[10., 20., 0.]]), size=9,
                                   face_color='red', edge_width=0, parent=canvas.scene)
    matrix = transforms.MatrixTransform()
    offset = transforms.STTransform(translate=(12, 7))
    chain = transforms.ChainTransform([offset, matrix])
    marker.transform = chain
    pixel(draw(canvas), 22, 27, RED)
    np.testing.assert_allclose(chain.imap((22, 27, 0))[:3], (10, 20, 0))
    with pytest.raises(np.linalg.LinAlgError, match='Singular'):
        matrix.scale((0, 1, 1))
    np.testing.assert_allclose(chain.imap((22, 27, 0))[:3], (10, 20, 0))
    pixel(draw(canvas), 22, 27, RED)
    matrix.scale((3, 1, 1))
    np.testing.assert_allclose(chain.imap((42, 27, 0))[:3], (10, 20, 0))
    frame = draw(canvas)
    pixel(frame, 42, 27, RED)
    pixel(frame, 22, 27, BLACK)


def test_default_headless_resize_events_and_retry(canvas_factory, draw, monkeypatch):
    canvas = canvas_factory(size=(40, 30))
    box(canvas.scene, (20, 15))
    events = []
    canvas.events.resize.connect(lambda event: events.append(
        (event.size, event.physical_size, canvas.size, canvas.physical_size)
    ))

    canvas.size = (50, 35)
    resized = ((50, 35),) * 4
    assert events == [resized]
    canvas.size = (50, 35)
    assert events == [resized]

    def reject_resize(*args):
        raise RuntimeError('drawable resize failed')

    with monkeypatch.context() as patch:
        patch.setattr(_dawn, 'configure_canvas', reject_resize)
        with pytest.raises(RuntimeError, match='drawable resize failed'):
            canvas.size = (60, 45)
    assert canvas.size == canvas.physical_size == (50, 35)
    assert events == [resized]
    frame = draw(canvas)
    assert frame.shape == (35, 50, 3)
    pixel(frame, 20, 15, RED)

    canvas.size = (60, 45)
    assert events == [resized, ((60, 45),) * 4]
    frame = draw(canvas)
    assert frame.shape == (45, 60, 3)
    pixel(frame, 20, 15, RED)
    pixel(frame, 59, 44, BLACK)


@pytest.mark.parametrize('alias,arguments,inside,outside', [
    ('Rectangle', dict(center=(25, 25), width=20, height=10, color='red'), (25, 25), (25, 33)),
    ('Ellipse', dict(center=(25, 25), radius=(10, 7), color='red'), (25, 25), (35, 31)),
    ('Polygon', dict(pos=np.array([[15, 15], [35, 15], [15, 35]]), color='red'),
     (19, 19), (30, 30)),
    ('Mesh', dict(vertices=np.array([[15, 15, 0], [35, 15, 0], [15, 35, 0]]),
                  faces=np.array([[0, 1, 2]]), color='red'), (19, 19), (30, 30)),
    ('Image', dict(data=np.full((12, 12, 3), RED, dtype=np.uint8)), (5, 5), (15, 5)),
    ('Markers', dict(pos=np.array([[25., 25., 0.]]), size=9, face_color='red', edge_width=0),
     (25, 25), (35, 25)),
])
def test_scene_visual_alias_geometry_picking_and_reparent(canvas_factory, draw,
                                                          alias, arguments, inside, outside):
    canvas = canvas_factory()
    first = Node(parent=canvas.scene)
    second = Node(parent=canvas.scene)
    second.transform = transforms.STTransform(translate=(40, 0))
    visual = getattr(scene.visuals, alias)(parent=first, **arguments)
    visual.interactive = True
    frame = draw(canvas)
    pixel(frame, *inside, RED)
    pixel(frame, *outside, BLACK)
    assert canvas.visual_at(inside) is visual
    visual.parent = None
    assert canvas.visual_at(inside) is None
    pixel(draw(canvas), *inside, BLACK)
    visual.parent = second
    shifted = (inside[0] + 40, inside[1])
    frame = draw(canvas)
    pixel(frame, *inside, BLACK)
    pixel(frame, *shifted, RED)
    assert canvas.visual_at(shifted) is visual
