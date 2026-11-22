# SPDX-License-Identifier: AGPL-3.0-only
"""Scene traversal and parent recovery for the 37 generated visual aliases."""
import numpy as np
import pytest

from vispy import scene, visuals
from vispy.geometry import MeshData
from vispy.visuals.transforms import STTransform

pytestmark = pytest.mark.gpu

SEGMENT = np.array([[1, 2], [9, 2]], np.float32)
CONTOUR_TRIANGLE = np.array([[1, 2, 0], [9, 2, 0], [1, 8, 0]], np.float32)
MESH_TRIANGLE = np.array([[0, 0, 0], [4, 0, 0], [0, 6, 0]], np.float32)
FACES = np.array([[0, 1, 2]], np.uint32)

# The reviewed scene cases use the same input for ordinary use and recovery.
# Lambdas construct fresh visual resources and consume the scene-specific kwargs.
CASES = {
    'arrow': lambda **kw: scene.visuals.Arrow(
        SEGMENT, arrows=np.array([[1, 2, 9, 2]], np.float32),
        arrow_type='stealth', **kw),
    'axis': lambda **kw: scene.visuals.Axis(
        pos=SEGMENT, domain=(0, 10), tick_direction=(0, 1), **kw),
    'box': lambda **kw: scene.visuals.Box(
        width=4, height=6, depth=2, color='red', edge_color='white', **kw),
    'colorbar': lambda **kw: scene.visuals.ColorBar(
        cmap='grays', orientation='bottom', size=(20, 4), pos=(12, 10),
        label='Scale', **kw),
    'compleximage': lambda **kw: scene.visuals.ComplexImage(
        np.array([[1+0j, 0+2j], [3+0j, 0+4j]], np.complex64),
        complex_mode='magnitude', cmap='grays', clim=(0, 4), **kw),
    'compound': lambda **kw: scene.visuals.Compound([
        visuals.LineVisual(SEGMENT, color='red'),
        visuals.MarkersVisual(pos=SEGMENT, size=6, face_color='green'),
    ], **kw),
    'cube': lambda **kw: scene.visuals.Cube(
        size=6, color='red', edge_color='white', **kw),
    'ellipse': lambda **kw: scene.visuals.Ellipse(
        center=(12, 10), radius=(4, 2), color='green', border_color='white', **kw),
    'graph': lambda **kw: scene.visuals.Graph(
        np.array([[0, 1], [0, 0]], np.float32), directed=True, layout='circular',
        line_color='white', node_size=6, face_color='red', **kw),
    'gridlines': lambda **kw: scene.visuals.GridLines(
        scale=(4, 4), color='white', grid_bounds=(0, 24, 0, 24), **kw),
    'gridmesh': lambda **kw: scene.visuals.GridMesh(
        np.array([[0, 4], [0, 4]], np.float32),
        np.array([[0, 0], [6, 6]], np.float32), np.zeros((2, 2), np.float32),
        shading=None, color='red', **kw),
    'histogram': lambda **kw: scene.visuals.Histogram(
        np.array([0.25, 0.75, 1.25, 1.75, 1.9]), bins=np.array([0., 1., 2.]),
        color='red', **kw),
    'image': lambda **kw: scene.visuals.Image(
        np.full((4, 8, 4), [255, 0, 0, 255], np.uint8),
        interpolation='nearest', **kw),
    'infiniteline': lambda **kw: scene.visuals.InfiniteLine(
        pos=9, color='red', vertical=True, **kw),
    'instancedmesh': lambda **kw: scene.visuals.InstancedMesh(
        vertices=MESH_TRIANGLE, faces=FACES,
        instance_positions=np.array([[0, 0, 0], [6, 0, 0]], np.float32),
        instance_transforms=np.repeat(np.eye(3, dtype=np.float32)[None], 2, axis=0),
        color='red', **kw),
    'isocurve': lambda **kw: scene.visuals.Isocurve(
        np.array([[0, 2], [0, 2]], np.float32), levels=[1], color_lev=['red'], **kw),
    'isoline': lambda **kw: scene.visuals.Isoline(
        vertices=CONTOUR_TRIANGLE, tris=FACES, data=np.array([0., 2., 0.]),
        levels=[1.], color_lev=['red'], **kw),
    'isosurface': lambda **kw: scene.visuals.Isosurface(
        np.indices((4, 4, 4), dtype=np.float32)[2], level=1.5, color='red', **kw),
    'line': lambda **kw: scene.visuals.Line(
        SEGMENT, color='red', width=2, connect='segments', **kw),
    'linearregion': lambda **kw: scene.visuals.LinearRegion(
        pos=(3., 8.), color='red', vertical=True, **kw),
    'lineplot': lambda **kw: scene.visuals.LinePlot(
        SEGMENT, color='red', symbol='o', face_color='green', marker_size=6, **kw),
    'markers': lambda **kw: scene.visuals.Markers(
        pos=SEGMENT, size=8, face_color='red', edge_width=0, **kw),
    'mesh': lambda **kw: scene.visuals.Mesh(
        vertices=MESH_TRIANGLE, faces=FACES, color='red', shading=None, **kw),
    'meshnormals': lambda **kw: scene.visuals.MeshNormals(
        MeshData(vertices=MESH_TRIANGLE, faces=FACES),
        primitive='face', length=3, color='red', **kw),
    'plane': lambda **kw: scene.visuals.Plane(
        width=6, height=4, width_segments=2, direction='+z', color='red', **kw),
    'polygon': lambda **kw: scene.visuals.Polygon(
        pos=CONTOUR_TRIANGLE[:, :2], color='red', border_color='white', **kw),
    'rectangle': lambda **kw: scene.visuals.Rectangle(
        center=(12, 10), width=8, height=4, radius=[1., 0., 0., 0.], color='red',
        **kw),
    'regularpolygon': lambda **kw: scene.visuals.RegularPolygon(
        center=(12, 10), radius=5, sides=5, color='red', border_color='white', **kw),
    'scrollinglines': lambda **kw: scene.visuals.ScrollingLines(
        n_lines=2, line_size=4, dx=2., columns=1, cell_size=(12., 6.), **kw),
    'spectrogram': lambda **kw: scene.visuals.Spectrogram(
        np.tile(np.sin(2 * np.pi * np.arange(32) * 4 / 32), 4),
        n_fft=32, step=32, fs=32, window=None, color_scale='linear', **kw),
    'sphere': lambda **kw: scene.visuals.Sphere(
        radius=4, rows=12, cols=16, method='latitude', color='red', **kw),
    'surfaceplot': lambda **kw: scene.visuals.SurfacePlot(
        x=np.array([0., 4.]), y=np.array([0., 6.]), z=np.zeros((2, 2), np.float32),
        shading=None, color='red', **kw),
    'text': lambda **kw: scene.visuals.Text(
        'Ag15', pos=(12, 12), font_size=12, face='OpenSans', color='white', **kw),
    'tube': lambda **kw: scene.visuals.Tube(
        np.array([[1, 1, 0], [5, 1, 0], [5, 5, 0]], np.float32),
        radius=1., closed=False, tube_points=8, shading=None, color='red', **kw),
    'volume': lambda **kw: scene.visuals.Volume(
        np.pad(np.ones((4, 4, 4), np.float32), 2), clim=(0, 1), method='mip',
        interpolation='nearest', **kw),
    'windbarb': lambda **kw: scene.visuals.Windbarb(
        pos=SEGMENT, wind=np.array([[0, 0], [10, 0]], np.float32), trig=False,
        size=10, edge_color='white', face_color='white', **kw),
    'xyzaxis': lambda **kw: scene.visuals.XYZAxis(width=2, **kw),
}

ALIAS_PARAMS = list(CASES)


@pytest.fixture
def canvas():
    canvas = scene.SceneCanvas(app='dawn_headless', size=(64, 64), show=False,
                               bgcolor='black', dpi=96, config={'samples': 0})
    try:
        yield canvas
    finally:
        canvas.close()


def record_draw(monkeypatch, node, calls):
    original = node.draw

    def draw():
        calls.append(node.name)
        return original()

    monkeypatch.setattr(node, 'draw', draw)


@pytest.mark.parametrize('alias', ALIAS_PARAMS)
def test_scene_alias_draw_order_and_transform(canvas, monkeypatch, alias):
    group = scene.Node(parent=canvas.scene)
    group.transform = STTransform(translate=(8, 5, 0))
    subject = CASES[alias](parent=group, name='subject')
    peer = scene.visuals.Rectangle(center=(7, 6), width=4, height=4,
                                   color='white', parent=group, name='peer')
    subject.transform = STTransform(translate=(3, 4, 0))
    subject.order = 2
    peer.order = 0

    calls = []
    record_draw(monkeypatch, subject, calls)
    record_draw(monkeypatch, peer, calls)
    frame = canvas.render()

    assert calls == ['peer', 'subject']
    np.testing.assert_allclose(
        subject.get_transform('visual', 'scene').map((1, 2, 0, 1)),
        (12, 11, 0, 1), rtol=0, atol=1e-6)
    if alias == 'image':
        # The red 8-by-4 image starts at (11, 9) after both translations
        # and covers the white peer, which is drawn first.
        expected = np.zeros((64, 64, 3), np.uint8)
        expected[9:13, 11:19, 0] = 255
        np.testing.assert_array_equal(frame[..., :3], expected)


@pytest.mark.parametrize('alias', ALIAS_PARAMS)
def test_scene_alias_invalid_parent_and_recovery(canvas, monkeypatch, alias):
    left = scene.Node(parent=canvas.scene)
    left.transform = STTransform(translate=(8, 5, 0))
    subject = CASES[alias](parent=left, name='subject')
    subject.transform = STTransform(translate=(3, 4, 0))
    right = scene.Node(parent=canvas.scene)
    right.transform = STTransform(translate=(20, 5, 0))

    changes = []
    calls = []

    def parent_changed(event):
        changes.append((event.old, event.new))

    subject.events.parent_change.connect(parent_changed)
    record_draw(monkeypatch, subject, calls)

    # Populate the canvas draw-order cache while the subject is attached.
    initial = canvas.render()
    assert calls == ['subject']
    calls.clear()

    with pytest.raises(ValueError, match='Parent must be Node instance or None'):
        subject.parent = object()
    assert changes == []
    assert subject.parent is left
    assert left.children == [subject]
    assert right.children == []

    subject.parent = None
    detached = canvas.render()
    assert calls == []
    assert left.children == []
    assert subject.canvas is None
    np.testing.assert_array_equal(detached[..., :3], 0)

    subject.parent = right
    recovered = canvas.render()
    assert calls == ['subject']
    assert changes == [(left, None), (None, right)]
    assert right.children == [subject]
    assert subject.canvas is canvas
    np.testing.assert_allclose(
        subject.get_transform('visual', 'scene').map((1, 2, 0, 1)),
        (24, 11, 0, 1), rtol=0, atol=1e-6)
    if alias == 'image':
        expected = np.zeros((64, 64, 3), np.uint8)
        expected[9:13, 11:19, 0] = 255
        np.testing.assert_array_equal(initial[..., :3], expected)
        expected.fill(0)
        expected[9:13, 23:31, 0] = 255
        np.testing.assert_array_equal(recovered[..., :3], expected)
