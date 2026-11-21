# SPDX-License-Identifier: AGPL-3.0-only
"""Analytic raster and recovery checks for the reviewed visual inventory."""

import numpy as np
import pytest

from vispy import scene
from vispy.color import Colormap
from vispy.scene.visuals import create_visual_node
from vispy.visuals import CompoundVisual, MeshVisual, Visual
from vispy.visuals.filters import ColorFilter
from vispy.visuals.transforms import MatrixTransform, STTransform, TransformSystem

pytestmark = pytest.mark.gpu

BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
BLUE = (0, 0, 255, 255)


@pytest.fixture
def canvas():
    canvas = scene.SceneCanvas(app='dawn_headless', size=(160, 144), dpi=96,
                               bgcolor='black', show=False, config={'samples': 0})
    try:
        yield canvas
    finally:
        canvas.close()


def pixel(frame, x, y, color, atol=0):
    np.testing.assert_allclose(frame[y, x], color, atol=atol)


def line_pixel(frame, x, y, color):
    patch = frame[y-1:y+2, x-1:x+2]
    assert np.any(np.all(patch == color, axis=-1)), (x, y, color, patch)


def rectangle_vertices(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x0, y1], [x1, y1]], np.float32)


def test_arrow_shaft_head_transform_and_invalid_style_recovery(canvas):
    points = np.array([[16, 25], [56, 25], [16, 55], [56, 55]], np.float32)
    arrow = scene.visuals.Arrow(
        pos=points, arrows=points.reshape(-1, 4), connect='segments',
        color='red', arrow_color='lime', arrow_type='triangle_60',
        arrow_size=18, parent=canvas.scene)
    frame = canvas.render()
    for y in (25, 55):
        line_pixel(frame, 30, y, RED)
        line_pixel(frame, 53, y, GREEN)
        pixel(frame, 70, y, BLACK)

    arrow.transform = STTransform(scale=(1.5, .8), translate=(12, 12))
    frame = canvas.render()
    line_pixel(frame, 52, 32, RED)
    line_pixel(frame, 93, 32, GREEN)
    pixel(frame, 30, 25, BLACK)
    with pytest.raises(ValueError, match='greater than zero'):
        arrow.arrow_size = 0
    with pytest.raises(ValueError, match='Invalid arrow type'):
        arrow.arrow_type = 'unknown'
    points[:, 1] += 55
    arrow.set_data(pos=points, arrows=points.reshape(-1, 4))
    frame = canvas.render()
    line_pixel(frame, 52, 76, RED)
    line_pixel(frame, 93, 76, GREEN)
    pixel(frame, 93, 32, BLACK)


@pytest.mark.parametrize('rotated', [False, True], ids=['horizontal', 'vertical'])
def test_axis_tick_raster_and_collapsed_domain_recovery(canvas, rotated):
    start, end = (20, 25), (140, 25)
    direction = (0, 1)
    if rotated:
        start, end = (25, 15), (25, 135)
        direction = (1, 0)
    axis = scene.visuals.Axis(
        pos=(start, end), domain=(0, 1), tick_direction=direction,
        axis_color='blue', tick_color='lime', text_color='red',
        major_tick_length=12, minor_tick_length=5, tick_label_margin=4,
        tick_font_size=10, parent=canvas.scene)

    def check(domain):
        frame = canvas.render()
        np.testing.assert_array_equal(axis._text.text, ['0', '0.5', '1'])
        origin, span = np.array(start), np.subtract(end, start)
        anchors = origin + np.linspace(0, 1, 3)[:, None] * span
        if domain == (1, 0):
            anchors = anchors[::-1]
        np.testing.assert_allclose(np.asarray(axis._text.pos)[:, :2],
                                   anchors + 16 * np.array(direction))
        line_pixel(frame, *(origin + span // 2 + 9 * np.array(direction)), GREEN)
        line_pixel(frame, *(origin + span // 10 + 3 * np.array(direction)), GREEN)
        pixel(frame, *(origin + span // 10 + 9 * np.array(direction)), BLACK)
        assert frame[..., 0].max() > 100

    check((0, 1))
    axis.domain = (.5, .5)
    canvas.render()
    axis.domain = (1, 0)
    check((1, 0))


class TriangleVisual(Visual):
    """A single triangle with deliberately literal bounds and fragment color."""

    def __init__(self):
        super().__init__(
            'attribute vec2 pos; void main() { gl_Position = $transform(vec4(pos, 0., 1.)); }',
            'void main() { gl_FragColor = vec4(1., 0., 0., 1.); }')
        self.shared_program['pos'] = np.array([[0, 0], [16, 0], [0, 16]], np.float32)
        self._draw_mode = 'triangles'
        self.freeze()

    def _compute_bounds(self, axis, view):
        return (0, 16) if axis in (0, 1) else (0, 0)

    def _prepare_transforms(self, view):
        view.view_program.vert['transform'] = view.get_transform()


def test_basevisual_shared_view_state_and_transform_rebinding(canvas):
    triangle = TriangleVisual()
    holder = create_visual_node(CompoundVisual)([triangle], parent=canvas.scene)
    holder.transform = STTransform(translate=(20, 30))
    first = triangle.view()
    second = triangle.view()
    assert first.bounds(0) == second.bounds(0) == (0, 16)
    pixel(canvas.render(), 23, 33, RED)
    first.visible = False
    assert not second.visible
    pixel(canvas.render(), 23, 33, BLACK)
    second.visible = True
    pixel(canvas.render(), 23, 33, RED)

    events = []
    second.events.update.connect(lambda event: events.append(event.source))
    old = second.transforms
    second.transforms = TransformSystem()
    assert events == [second]
    old.visual_transform = STTransform(translate=(100, 100))
    assert events == [second]
    second.transform = STTransform(scale=(2, 3), translate=(7, 11))
    assert events == [second, second]
    np.testing.assert_allclose(second.get_transform('visual', 'scene').map((2, 3)),
                               (11, 20, 0, 1))
    np.testing.assert_allclose(first.get_transform('visual', 'scene').map((2, 3)),
                               (2, 3, 0, 1))
    pixel(canvas.render(), 23, 33, RED)


def test_compound_order_bounds_and_removed_child_recovery(canvas):
    faces = np.array([[0, 1, 2], [1, 3, 2]], np.uint32)
    left = MeshVisual(rectangle_vertices(0, 0, 32, 24), faces, color='red')
    right = MeshVisual(rectangle_vertices(20, 0, 48, 24), faces, color='lime')
    for child in (left, right):
        child.update_gl_state(depth_test=False)
    compound = create_visual_node(CompoundVisual)([left, right], parent=canvas.scene)
    compound.transform = STTransform(translate=(20, 40))
    np.testing.assert_equal(compound.bounds(0), [0, 48])
    np.testing.assert_equal(compound.bounds(1), [0, 24])
    frame = canvas.render()
    tint = ColorFilter((.5, .25, 1., 1.))
    compound.attach(tint)
    tinted = canvas.render()
    pixel(tinted, 32, 52, (128, 0, 0, 255), atol=1)
    pixel(tinted, 65, 52, (0, 64, 0, 255), atol=1)
    compound.detach(tint)
    np.testing.assert_array_equal(canvas.render(), frame)
    pixel(frame, 32, 52, RED)
    pixel(frame, 46, 52, GREEN)
    pixel(frame, 65, 52, GREEN)
    pixel(frame, 70, 52, BLACK)

    updates = []
    compound.events.update.connect(lambda event: updates.append(event.source))
    compound.remove_subvisual(right)
    assert updates == [compound]
    right.update()
    assert updates == [compound]
    removed = canvas.render()
    pixel(removed, 46, 52, RED)
    pixel(removed, 65, 52, BLACK)
    assert compound.bounds(0) == (0, 32)
    compound.add_subvisual(right)
    updates.clear()
    right.update()
    assert updates == [compound]
    np.testing.assert_equal(compound.bounds(0), [0, 48])
    np.testing.assert_array_equal(canvas.render(), frame)


def test_box_segmented_face_colors_and_border_restoration(canvas):
    # The two width cells have two triangles each. Use a single selected
    # plane to isolate their face colors and outline from back-face depth.
    box = scene.visuals.Box(
        width=40, height=8, depth=24, width_segments=2, planes=['-z'],
        face_colors=np.array([RED, RED, BLUE, BLUE]) / 255.,
        edge_color='lime', parent=canvas.scene)
    box.transform = STTransform(scale=(1, 1, .01), translate=(60, 60))
    np.testing.assert_equal(box.bounds(0), [-20, 20])
    np.testing.assert_equal(box.bounds(1), [-12, 12])
    assert len(box.mesh.mesh_data.get_faces()) == 4
    frame = canvas.render()
    pixel(frame, 50, 60, RED)
    pixel(frame, 70, 60, BLUE)
    line_pixel(frame, 40, 60, GREEN)
    pixel(frame, 37, 60, BLACK)
    box.border.visible = False
    without_edge = canvas.render()
    assert not np.any(without_edge[..., 1])
    pixel(without_edge, 50, 60, RED)
    pixel(without_edge, 70, 60, BLUE)
    box.border.visible = True
    np.testing.assert_array_equal(canvas.render(), frame)


@pytest.mark.parametrize('size', [24., (38, 12, 20)], ids=['cube', 'cuboid'])
def test_cube_deprecation_invalid_size_and_valid_geometry(canvas, size):
    with pytest.warns(DeprecationWarning, match='BoxVisual'):
        with pytest.raises(ValueError, match='unpack'):
            scene.visuals.Cube(size=(20, 30))
    with pytest.warns(DeprecationWarning, match='BoxVisual'):
        cube = scene.visuals.Cube(size=size, color='blue', edge_color='lime',
                                  parent=canvas.scene)
    cube.transform = STTransform(scale=(1, 1, .01), translate=(60, 60))
    wx, hy, dz = (size,) * 3 if isinstance(size, float) else (size[0], size[2], size[1])
    for axis, extent in enumerate((wx, hy, dz)):
        np.testing.assert_equal(cube.bounds(axis), [-extent / 2, extent / 2])
    frame = canvas.render()
    pixel(frame, 60, 60, BLUE)
    line_pixel(frame, int(60 - wx / 2), 60, GREEN)
    pixel(frame, int(57 - wx / 2), 60, BLACK)
    pixel(frame, 60, int(63 + hy / 2), BLACK)


@pytest.mark.parametrize('orientation', ['top', 'bottom', 'left', 'right'])
def test_colorbar_ramp_labels_and_invalid_size_recovery(canvas, orientation):
    bar = scene.visuals.ColorBar(
        Colormap(['red', 'blue']), orientation, (72, 14), pos=(80, 72),
        label='Signal', label_color='white', border_width=2,
        border_color='lime', clim=(0, 10), parent=canvas.scene)
    for text in (bar.label, *bar.ticks):
        text.font_size = 6
    horizontal = orientation in ('top', 'bottom')
    frame = canvas.render()

    def check(frame, length):
        delta = length // 4
        low = (80 - delta, 72) if horizontal else (80, 72 + delta)
        high = (80 + delta, 72) if horizontal else (80, 72 - delta)
        pixel(frame, *low, (191, 0, 64, 255), atol=4)
        pixel(frame, *high, (64, 0, 191, 255), atol=4)
        edge = {'top': (80, 79), 'bottom': (80, 65),
                'left': (87, 72), 'right': (73, 72)}[orientation]
        line_pixel(frame, *edge, GREEN)
        major = 0 if horizontal else 1
        expected_ticks = [80 - length / 2, 80 + length / 2] if horizontal else [
            72 + length / 2, 72 - length / 2]
        np.testing.assert_allclose(
            np.asarray([tick.pos for tick in bar.ticks]).reshape(2, -1)[:, major],
            expected_ticks)
        assert bar.label.text == 'Signal'
        assert [tick.text for tick in bar.ticks] == ['0', '10']
        assert np.count_nonzero(np.all(frame[..., :3] > 100, axis=-1)) > 6

    check(frame, 72)
    with pytest.raises(ValueError, match='Major axis'):
        bar.size = (8, 14)
    bar.size = (88, 14)
    check(canvas.render(), 88)
    bar.size = (72, 14)
    np.testing.assert_array_equal(canvas.render(), frame)


def test_ellipse_arc_and_invalid_radius_recovery(canvas):
    ellipse = scene.visuals.Ellipse(
        center=(60, 60), radius=(26, 14), color='red', border_color='blue',
        border_width=2, parent=canvas.scene)
    frame = canvas.render()
    pixel(frame, 40, 60, RED)
    pixel(frame, 60, 70, RED)
    line_pixel(frame, 86, 60, BLUE)
    line_pixel(frame, 60, 74, BLUE)
    pixel(frame, 60, 77, BLACK)
    ellipse.span_angle = 180
    arc = canvas.render()
    pixel(arc, 60, 67, RED)
    pixel(arc, 60, 53, BLACK)
    with pytest.raises(ValueError, match='radius must be'):
        ellipse.radius = (1, 2, 3)
    ellipse.radius = (20, 10)
    ellipse.span_angle = 360
    recovered = canvas.render()
    np.testing.assert_equal(ellipse.bounds(0), [40, 80])
    np.testing.assert_equal(ellipse.bounds(1), [50, 70])
    pixel(recovered, 75, 60, RED)
    pixel(recovered, 83, 60, BLACK)
    line_pixel(recovered, 80, 60, BLUE)


@pytest.fixture
def complex_image(canvas):
    samples = np.array([[1, 1j], [-1, -1j]], dtype=np.complex64)
    image = scene.visuals.ComplexImage(
        samples, clim=(-1, 1), cmap='grays', parent=canvas.scene)
    image.transform = STTransform(scale=(24, 24), translate=(20, 20))
    probes = [(32, 32), (56, 32), (32, 56), (56, 56)]

    def check(values):
        frame = canvas.render()
        for (x, y), gray in zip(probes, values):
            pixel(frame, x, y, (gray, gray, gray, 255), atol=1)

    return image, samples, check


def test_compleximage_four_modes_and_invalid_mode_recovery(complex_image):
    image, _, check = complex_image
    for mode, clim, levels in [
            ('magnitude', (0, 2), (128, 128, 128, 128)),
            ('real', (-1, 1), (255, 128, 0, 128)),
            ('imaginary', (-1, 1), (128, 255, 128, 0)),
            ('phase', (-np.pi, np.pi), (128, 191, 255, 64))]:
        image.complex_mode = mode
        image.clim = clim
        check(levels)

    with pytest.raises(ValueError, match='complex_mode'):
        image.complex_mode = 'unknown'
    check((128, 191, 255, 64))
    image.complex_mode = 'imaginary'
    image.clim = (-1, 1)
    check((128, 255, 128, 0))


def test_compleximage_real_data_recovery(complex_image):
    image, samples, check = complex_image
    image.complex_mode = 'phase'
    image.clim = (-np.pi, np.pi)
    check((128, 191, 255, 64))
    image.clim = (0, 1)
    image.set_data(np.array([[.25, .75], [1, 0]], np.float32))
    check((64, 191, 255, 0))
    image.set_data(samples)
    image.clim = (-1, 1)
    image.complex_mode = 'imaginary'
    check((128, 255, 128, 0))


def test_graph_directed_edges_and_invalid_adjacency_recovery(canvas):
    from vispy.visuals.graphs.util import _straight_line_vertices

    nodes = np.array([[24, 28], [100, 28], [100, 102]], np.float32)

    def layout(adjacency, directed):
        edges, arrows = _straight_line_vertices(adjacency, nodes, directed)
        yield nodes, edges, arrows

    style = dict(line_color='red', arrow_size=20, arrow_type='triangle_60',
                 line_width=1, face_color='lime', border_color='lime',
                 border_width=0, node_size=7)
    adjacency = np.array([[0, 1, 0], [0, 0, 0], [0, 0, 0]])
    graph = scene.visuals.Graph(adjacency, layout=layout, directed=True,
                                animate=True, parent=canvas.scene, **style)
    assert not graph.animate_layout()
    assert graph.animate_layout()
    frame = canvas.render()
    for x, y in nodes.astype(int):
        line_pixel(frame, x, y, GREEN)
    line_pixel(frame, 50, 28, RED)
    # The wing of the default gray arrow sits near the destination.
    assert np.any(np.all(frame[23:26, 90:100, :3] > 50, axis=-1))
    pixel(frame, 30, 24, BLACK)
    pixel(frame, 100, 65, BLACK)

    with pytest.raises(ValueError, match='should be square'):
        graph.set_data(np.zeros((3, 2)))
    np.testing.assert_array_equal(canvas.render(), frame)
    graph.set_data(adjacency.T + np.array([[0, 0, 0], [0, 0, 1], [0, 0, 0]]),
                   **style)
    graph.set_final_layout()
    recovered = canvas.render()
    line_pixel(recovered, 100, 65, RED)
    assert np.any(np.all(recovered[23:26, 24:34, :3] > 50, axis=-1))
    assert not np.any(recovered[23:26, 90:96, :3])


def test_gridlines_translated_spacing_and_clip_recovery(canvas):
    grid = scene.visuals.GridLines(
        color='red', grid_bounds=(-20, 40, -20, 40), border_width=0,
        parent=canvas.scene)
    grid.transform = STTransform(translate=(40, 40))
    frame = canvas.render()
    assert 140 <= frame[40, 40, 0] <= 160
    pixel(frame, 50, 50, BLACK)
    pixel(frame, 85, 40, BLACK)

    grid.transform = MatrixTransform()
    grid.transform.scale((2, 2, 1))
    grid.transform.rotate(90, (0, 0, 1))
    grid.transform.translate((40, 40, 0))
    scaled = canvas.render()
    assert 140 <= scaled[40, 40, 0] <= 160
    assert scaled[110, 39:41, 0].max() > 100
    pixel(scaled, 110, 40, BLACK)
    pixel(scaled, 30, 50, BLACK)
    grid.grid_bounds = (100, 110, 100, 110)
    assert not np.any(canvas.render()[..., :3])
    grid.grid_bounds = (-20, 40, -20, 40)
    np.testing.assert_array_equal(canvas.render(), scaled)

    # Draw the same occluder in front of and behind the grid plane.
    occluder = scene.visuals.Mesh(
        rectangle_vertices(34, 34, 46, 46), np.array([[0, 1, 2], [1, 3, 2]]),
        color='blue', parent=canvas.scene)
    occluder.order = -1
    grid.update_gl_state(depth_test=True)
    occluder.transform = STTransform(translate=(0, 0, -.5))
    pixel(canvas.render(), 40, 40, BLUE)
    occluder.transform = STTransform(translate=(0, 0, .5))
    behind = canvas.render()
    assert 140 <= behind[40, 40, 0] <= 160
    assert behind[40, 40, 2] == 255

def test_gridmesh_colored_height_grid_and_mismatched_update_recovery(canvas):
    x, y = np.meshgrid([20, 50, 80], [30, 70])
    z = np.tile([0, .2, .4], (2, 1))
    colors = np.broadcast_to(np.array([RED, GREEN, BLUE]) / 255., (2, 3, 4))
    mesh = scene.visuals.GridMesh(x, y, z, colors=colors, shading=None,
                                   parent=canvas.scene)
    frame = canvas.render()
    assert mesh.bounds(0) == (20, 80)
    assert mesh.bounds(1) == (30, 70)
    np.testing.assert_allclose(mesh.bounds(2), (0, .4))
    pixel(frame, 34, 50, (132, 123, 0, 255), atol=2)
    pixel(frame, 64, 50, (0, 132, 123, 255), atol=2)
    pixel(frame, 18, 50, BLACK)
    pixel(frame, 50, 73, BLACK)

    with pytest.raises(ValueError):
        mesh.set_data(zs=z[:, :2])
    mesh.set_data(zs=z + .2)
    np.testing.assert_allclose(mesh.bounds(2), (.2, .6))
    np.testing.assert_array_equal(canvas.render(), frame)


@pytest.mark.parametrize('orientation', ['h', 'v'])
def test_histogram_explicit_bins_and_invalid_input_recovery(canvas, orientation):
    with pytest.raises(ValueError, match='Only 1D'):
        scene.visuals.Histogram([[1, 2]])
    with pytest.raises(ValueError, match='orientation'):
        scene.visuals.Histogram([1, 2], orientation='diagonal')

    # Deliberately nonuniform bin widths, and a sample on the last edge.
    hist = scene.visuals.Histogram(
        [.5, 1, 1.5, 2.5, 3.7, 4], bins=[0, 1, 3, 4],
        orientation=orientation, color='red', parent=canvas.scene)
    hist.transform = STTransform(scale=(20, 20), translate=(20, 20))
    frame = canvas.render()
    for axis, extent in enumerate((4, 3) if orientation == 'h' else (3, 4)):
        assert hist.bounds(axis) == (0, extent)
    for bin_pos, count in ((.5, 1), (2, 3), (3.5, 2)):
        for height, color in ((count - .25, RED), (count + .25, BLACK)):
            coords = (bin_pos, height) if orientation == 'h' else (height, bin_pos)
            pixel(frame, *(20 + int(20 * value) for value in coords), color)
    pixel(frame, 18, 18, BLACK)


@pytest.mark.parametrize('vertical', [True, False], ids=['vertical', 'horizontal'])
def test_infiniteline_translated_viewport_and_invalid_data_recovery(canvas, vertical):
    line = scene.visuals.InfiniteLine(pos=20, vertical=vertical,
                                    color=(1, 0, 0, 1), parent=canvas.scene)
    line.transform = STTransform(translate=(8, 12))
    fixed = 28 if vertical else 32

    def check(frame, pos, color):
        for across in (3, 70, 138):
            x, y = (pos, across) if vertical else (across, pos)
            line_pixel(frame, x, y, color)
            pixel(frame, x + (4 if vertical else 0), y + (0 if vertical else 4), BLACK)

    check(canvas.render(), fixed, RED)
    with pytest.raises((ValueError, TypeError)):
        line.set_data(pos=[1, 2])
    with pytest.raises(ValueError, match='4 element'):
        line.set_data(color=(1, 0, 0))
    line.set_data(pos=42, color=(0, 0, 1, 1))
    frame = canvas.render()
    check(frame, fixed + 22, BLUE)
    pixel(frame, *((fixed, 70) if vertical else (70, fixed)), BLACK)


@pytest.mark.parametrize('shading', [
    pytest.param(None, id='unlit'),
    pytest.param('smooth', id='ambient-only'),
])
def test_instancedmesh_transformed_color_and_invalid_stream_recovery(canvas, shading):
    vertices = rectangle_vertices(0, 0, 20, 16)
    faces = np.array([[0, 1, 2], [1, 3, 2]], np.uint32)
    transforms = np.array([np.eye(3), np.diag([.5, 2., 1.])])
    mesh = scene.visuals.InstancedMesh(
        vertices=vertices, faces=faces, instance_positions=[[20, 22, 0], [70, 22, 0]],
        instance_transforms=transforms, instance_colors=np.array([RED, GREEN]) / 255.,
        color='white', shading=shading, parent=canvas.scene)
    if shading:
        mesh.shading_filter.ambient_light = (1, 1, 1, 1)
        mesh.shading_filter.diffuse_light = (1, 1, 1, 0)
        mesh.shading_filter.specular_light = (1, 1, 1, 0)
    assert mesh.bounds(0) == (20, 80)
    assert mesh.bounds(1) == (22, 54)
    frame = canvas.render()
    pixel(frame, 30, 30, RED)
    pixel(frame, 75, 48, GREEN)
    pixel(frame, 84, 30, BLACK)
    pixel(frame, 30, 48, BLACK)

    with pytest.raises(ValueError, match='reshape'):
        mesh.instance_transforms = np.zeros((2, 2, 2))
    np.testing.assert_array_equal(canvas.render(), frame)
    transforms[1] = np.diag([2., .5, 1.])
    mesh.instance_transforms = transforms
    assert mesh.bounds(0) == (20, 110)
    assert mesh.bounds(1) == (22, 38)
    recovered = canvas.render()
    pixel(recovered, 30, 30, RED)
    pixel(recovered, 98, 25, GREEN)
    pixel(recovered, 75, 48, BLACK)


def test_isocurve_unsorted_levels_palette_and_empty_recovery(canvas):
    data = np.tile(np.arange(5, dtype=np.float32), (5, 1))
    curve = scene.visuals.Isocurve(
        data, levels=[2.5, .5], color_lev=['red', 'lime'], parent=canvas.scene)
    curve.transform = STTransform(scale=(20, 20), translate=(20, 20))
    frame = canvas.render()
    # Both extractors use pixel-center coordinates. The two contour x
    # positions in the source field are 3 and 1.
    for y in (40, 55, 80):
        line_pixel(frame, 80, y, RED)
        line_pixel(frame, 40, y, GREEN)
        pixel(frame, 60, y, BLACK)

    curve.color = ['red', 'lime', 'blue']
    with pytest.raises(TypeError, match='Color/level mismatch'):
        canvas.render()
    curve.color = ['red', 'lime']
    curve.levels = []
    assert not np.any(canvas.render()[..., :3])
    curve.levels = [2.5, .5]
    np.testing.assert_array_equal(canvas.render(), frame)


def test_isoline_joined_triangle_crossings_and_out_of_range_recovery(canvas):
    vertices = np.column_stack((rectangle_vertices(20, 20, 100, 100), np.zeros(4)))
    contour = scene.visuals.Isoline(
        vertices=vertices, tris=np.array([[0, 1, 2], [1, 3, 2]]),
        data=np.array([0., 1., 0., 1.]), levels=np.array([.5]),
        color_lev='lime', parent=canvas.scene)
    frame = canvas.render()
    for y in range(22, 98):
        line_pixel(frame, 60, y, GREEN)
        pixel(frame, 65, y, BLACK)
    contour.levels = np.array([2.])
    assert not np.any(canvas.render()[..., :3])
    contour.levels = np.array([.5])
    np.testing.assert_array_equal(canvas.render(), frame)


def test_isosurface_planar_ramp_topology_and_empty_recovery(canvas):
    field = np.broadcast_to(np.arange(3, dtype=np.float32)[:, None, None],
                            (3, 4, 5)).copy()
    surface = scene.visuals.Isosurface(field, level=.5, color='blue',
                                       parent=canvas.scene)
    surface.transform = MatrixTransform()
    surface.transform.rotate(90, (0, 1, 0))
    surface.transform.scale((20, 20, .01))
    surface.transform.translate((20, 20, 0))
    frame = canvas.render()
    pixel(frame, 40, 40, BLUE)
    pixel(frame, 95, 75, BLUE)
    pixel(frame, 105, 75, BLACK)
    pixel(frame, 40, 85, BLACK)
    vertices = surface.mesh_data.get_vertices()
    assert len(vertices) == 20
    assert len(surface.mesh_data.get_faces()) == 24
    np.testing.assert_allclose(vertices[:, 0], .5)
    assert [surface.bounds(i) for i in range(3)] == [(.5, .5), (0, 3), (0, 4)]
    surface.level = 3.
    assert not np.any(canvas.render()[..., :3])
    surface.level = .5
    np.testing.assert_array_equal(canvas.render(), frame)
    np.testing.assert_array_equal(surface.mesh_data.get_vertices(), vertices)


def test_image_nonlinear_sampling_resize_and_device_loss_recovery(canvas):
    from vispy import _dawn
    from vispy.visuals.transforms import ChainTransform, LogTransform

    image = scene.visuals.Image(
        np.tile(np.array([0., 0., 1.], np.float32), (2, 1)), cmap='grays',
        clim=(0, 1), texture_format='auto', interpolation='nearest',
        parent=canvas.scene)
    # log2(x) maps the source interval [1, 2] to 64 output pixels.
    image.transform = ChainTransform([
        STTransform(scale=(64, 32), translate=(40, 25)), LogTransform(base=(2, 0, 0))])
    frame = canvas.render()
    pixel(frame, 60, 45, BLACK)
    pixel(frame, 125, 45, (255, 255, 255, 255))
    # A one-tap custom kernel samples at the same continuous coordinate.
    for interpolation in ('linear', 'custom'):
        image.interpolation = interpolation
        frame = canvas.render()
        for x in (80, 105, 120):
            source_x = 2 ** ((x + .5 - 40) / 64)
            gray = round(255 * np.clip(source_x - 1.5, 0, 1))
            pixel(frame, x, 45, (gray, gray, gray, 255), atol=2)
    with pytest.raises(ValueError, match='interpolation'):
        image.interpolation = 'unknown'

    image.interpolation = 'nearest'
    rgba = np.empty((3, 4, 4), np.float32)
    rgba[:, :2] = np.array(GREEN) / 255.
    rgba[:, 2:] = np.array(BLUE) / 255.
    image.set_data(rgba)
    frame = canvas.render()
    pixel(frame, 80, 90, GREEN)
    pixel(frame, 130, 90, BLUE)
    pixel(frame, 130, 125, BLACK)
    _dawn.lose_device()
    np.testing.assert_array_equal(canvas.render(), frame)

    rgba[:, 2:] = np.array(RED) / 255.
    image.set_data(rgba)
    recovered = canvas.render()
    pixel(recovered, 80, 90, GREEN)
    pixel(recovered, 130, 90, RED)
