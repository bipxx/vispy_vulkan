# SPDX-License-Identifier: AGPL-3.0-only
"""Analytic landmarks and recovery for the reviewed Visual acceptance rows."""

import gc

import numpy as np
import pytest

from vispy import _dawn, gloo, scene, visuals
from vispy.color import Colormap
from vispy.geometry import MeshData
from vispy.visuals.transforms import MatrixTransform, STTransform

pytestmark = pytest.mark.gpu
SIZE = (128, 96)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)


@pytest.fixture
def canvas():
    canvas = scene.SceneCanvas(app='dawn_headless', size=SIZE, show=False,
                               bgcolor='black', config={'samples': 0})
    canvas.set_current()
    try:
        yield canvas
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


def pixel(frame, x, y, color, atol=0):
    np.testing.assert_allclose(frame[y, x, :3], color, atol=atol,
                               err_msg=f'pixel at ({x}, {y})')


def near(frame, x, y, color, radius=2):
    patch = frame[y-radius:y+radius+1, x-radius:x+radius+1, :3]
    assert np.any(np.all(patch == color, axis=-1)), (x, y, color, patch)


def projection(x, y, z, origin):
    """Use the supplied images of the three basis vectors as matrix rows."""
    matrix = np.eye(4)
    matrix[:3, :3] = (x, y, z)
    matrix[3, :3] = origin
    return MatrixTransform(matrix)


def test_linear_region_transformed_alpha_and_recovery(canvas):
    vertical = scene.visuals.LinearRegion([0, 40], color=[(1, 0, 0, 0), (1, 0, 0, 1)],
                                          parent=canvas.scene)
    vertical.transform = STTransform(translate=(16, 0))
    horizontal = scene.visuals.LinearRegion([64, 84], color=(0, 0, 1, .5),
                                            vertical=False, parent=canvas.scene)
    baseline = canvas.render()
    pixel(baseline, 26, 32, (67, 0, 0), atol=2)
    pixel(baseline, 46, 32, (194, 0, 0), atol=2)
    pixel(baseline, 80, 72, (0, 0, 128), atol=1)
    pixel(baseline, 80, 32, BLACK)
    with pytest.raises(ValueError, match='1D'):
        vertical.set_data(pos=[[0, 40]])
    np.testing.assert_array_equal(canvas.render(), baseline)
    vertical.set_data(pos=[48, 88])
    horizontal.set_data(pos=[48, 60])
    recovered = canvas.render()
    pixel(recovered, 26, 32, BLACK)
    pixel(recovered, 74, 32, (67, 0, 0), atol=2)
    pixel(recovered, 112, 54, (0, 0, 128), atol=1)
    pixel(recovered, 112, 72, BLACK)


def test_line_plot_implicit_x_xyz_and_recovery(canvas):
    plot = scene.visuals.LinePlot(np.array([0, 0, 2]), color='red',
                                  symbol='disc', marker_size=8, edge_width=0,
                                  face_color='blue', parent=canvas.scene)
    plot.transform = STTransform(scale=(24, 10, 1), translate=(24, 22, 0))
    baseline = canvas.render()
    near(baseline, 24, 22, BLUE)
    near(baseline, 48, 22, BLUE)
    near(baseline, 72, 42, BLUE)
    near(baseline, 36, 22, RED)
    with pytest.raises(ValueError, match='two dimensions'):
        plot.set_data(np.zeros((3, 2, 1)), color='green')
    np.testing.assert_array_equal(canvas.render(), baseline)

    plot.transform = projection((24, 0, 0), (0, 10, 0), (0, 8, .1), (24, 22, 0))
    plot.set_data(([0, 1, 2], [2, 2, 2], [1, 1, 2]), connect='segments')
    frame = canvas.render()
    near(frame, 24, 50, BLUE)
    near(frame, 48, 50, BLUE)
    near(frame, 72, 58, BLUE)
    near(frame, 36, 50, RED)
    pixel(frame, 60, 54, BLACK)
    pixel(frame, 24, 22, BLACK)


def test_line_connectivity_and_agg_recovery(canvas):
    points = np.array([(16, 20), (48, 20), (48, 60), (92, 60)], np.float32)
    line = scene.visuals.Line(points, color='red', parent=canvas.scene)
    for connect, drawn in [
        ('strip', (True, True, True)),
        ('segments', (True, False, True)),
        (np.array([False, True, False]), (False, True, False)),
        (np.array([[0, 1], [2, 3]]), (True, False, True)),
    ]:
        line.set_data(connect=connect)
        frame = canvas.render()
        for (x, y), present in zip(((32, 20), (48, 40), (72, 60)), drawn):
            if present:
                near(frame, x, y, RED)
            else:
                np.testing.assert_array_equal(frame[y-2:y+3, x-2:x+3, :3], 0)

    with pytest.raises(ValueError, match='method'):
        line.method = 'unknown'
    np.testing.assert_array_equal(canvas.render(), frame)
    line.set_data(connect='strip', width=8, color='blue')
    line.method = 'agg'
    recovered = canvas.render()
    pixel(recovered, 48, 40, BLUE)
    pixel(recovered, 48, 21, BLUE)
    pixel(recovered, 55, 14, BLACK)


@pytest.mark.parametrize('method', ['points', 'instanced'])
@pytest.mark.parametrize('scaling', ['fixed', 'scene'])
def test_markers_symbols_scaling_and_recovery(canvas, method, scaling):
    view = canvas.central_widget.add_view(border_width=0)
    view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, 64, 48),
                                             flip=(False, True, False))
    marker = scene.visuals.Markers(method=method, scaling=scaling, antialias=0,
                                   parent=view.scene)
    points = np.array([(16, 16), (44, 16)], np.float32)
    style = dict(symbol=['disc', 'square'], size=16, edge_width=2,
                 edge_color='red', face_color='blue')
    marker.set_data(points, **style)
    baseline = canvas.render()
    radius = 8 if scaling == 'fixed' else 16
    pixel(baseline, 32, 32, BLUE)
    near(baseline, 88 + radius - 2, 32 + radius - 2, RED)
    pixel(baseline, 32 + radius - 1, 32 + radius - 1, BLACK)
    pixel(baseline, 88 + radius + 2, 32, BLACK)
    with pytest.raises(ValueError, match='negative'):
        marker.set_data(points, **dict(style, edge_width=-1))
    np.testing.assert_array_equal(canvas.render(), baseline)
    marker.set_data(points + (0, 20), **dict(style, face_color='lime'))
    recovered = canvas.render()
    pixel(recovered, 32, 72, GREEN)
    pixel(recovered, 32, 32, BLACK)


def test_mesh_normals_face_and_vertex_recovery(canvas):
    vertices = np.array([(12, 15, 0), (72, 15, 0), (12, 51, 0)], np.float32)
    mesh = MeshData(vertices=vertices, faces=np.array([[0, 1, 2]]))
    normals = scene.visuals.MeshNormals(mesh, primitive='face', length=20, color='red',
                                        parent=canvas.scene)
    normals.transform = projection((1, 0, 0), (0, 1, 0), (1, 0, .03), (0, 0, 0))
    baseline = canvas.render()
    np.testing.assert_allclose(normals.pos, [(32, 27, 0), (32, 27, 20)])
    near(baseline, 48, 27, RED)
    pixel(baseline, 54, 27, BLACK)
    with pytest.raises(ValueError, match='primitive'):
        normals.set_data(primitive='edge', length=20)
    np.testing.assert_array_equal(canvas.render(), baseline)
    normals.set_data(primitive='vertex', length=12, color='blue')
    frame = canvas.render()
    endpoints = vertices + (0, 0, 12)
    np.testing.assert_allclose(normals.pos[1::2], endpoints)
    for x, y, _ in vertices:
        near(frame, int(x) + 9, int(y), BLUE)
        pixel(frame, int(x) + 14, int(y), BLACK)
    pixel(frame, 48, 27, BLACK)


def queue_draw(canvas, target):
    canvas.push_fbo(target, (0, 0), SIZE)
    try:
        gloo.clear(color=(0, 0, 0, 1), depth=True)
        canvas.draw_visual(canvas.scene)
    finally:
        canvas.pop_fbo()
    return _dawn.probe()['pending_draws']


@pytest.fixture
def targets(canvas):
    colors = [gloo.RenderBuffer(SIZE[::-1], format='color') for _ in range(2)]
    depths = [gloo.RenderBuffer(SIZE[::-1], format='depth') for _ in range(2)]
    targets = [gloo.FrameBuffer(color=color, depth=depth)
               for color, depth in zip(colors, depths)]
    try:
        yield targets
    finally:
        for resource in targets + colors + depths:
            resource.delete()


def test_mesh_scalar_interpolation_and_queued_recovery(canvas, targets):
    vertices = np.array([(16, 16), (80, 16), (16, 80), (80, 80)], np.float32)
    values = np.array([0, 1, 0, 1], np.float32)
    mesh = scene.visuals.Mesh(vertices=vertices, faces=np.array([[0, 1, 2]]),
                              vertex_values=values, parent=canvas.scene)
    mesh.cmap = Colormap(['red', 'blue'])
    mesh.clim = (0, 1)
    first = queue_draw(canvas, targets[0])
    with pytest.raises((TypeError, ValueError), match='[Vv]ert'):
        mesh.set_data(vertices=np.zeros((3, 4)), faces=np.array([[0, 1, 2]]))
    mesh.set_data(vertices=vertices + (24, 0), faces=np.array([[1, 3, 2]]),
                  vertex_values=values)
    assert 0 < first < queue_draw(canvas, targets[1])
    with targets[0]:
        old = targets[0].read()
    with targets[1]:
        new = targets[1].read()
    pixel(old, 32, 24, (189, 0, 66), atol=2)
    pixel(old, 72, 72, BLACK)
    pixel(new, 32, 24, BLACK)
    pixel(new, 88, 72, (62, 0, 193), atol=2)
    assert _dawn.probe()['pending_draws'] == 0


def test_plane_segmented_orientation_and_construction_recovery(canvas):
    front = scene.visuals.Plane(width=40, height=32, width_segments=2,
                                height_segments=2, color='red', edge_color='white',
                                parent=canvas.scene)
    front.transform = STTransform(translate=(32, 38))
    baseline = canvas.render()
    pixel(baseline, 22, 30, RED)
    near(baseline, 32, 30, WHITE)
    near(baseline, 32, 22, WHITE)
    pixel(baseline, 10, 30, BLACK)
    with pytest.raises(ValueError, match='[Dd]irection'):
        scene.visuals.Plane(direction='unknown', parent=canvas.scene)
    np.testing.assert_array_equal(canvas.render(), baseline)
    side = scene.visuals.Plane(width=40, height=32, width_segments=2,
                               height_segments=2, direction='-x', color='blue',
                               edge_color='white', parent=canvas.scene)
    side.transform = projection((0, 0, 1), (0, 1, 0), (1, 0, 0), (90, 38, 0))
    recovered = canvas.render()
    np.testing.assert_array_equal(recovered[:, :58], baseline[:, :58])
    pixel(recovered, 80, 30, BLUE)
    near(recovered, 90, 30, WHITE)
    pixel(recovered, 112, 30, BLACK)


def test_polygon_concave_border_and_clear_recovery(canvas):
    points = np.array([(16, 16), (72, 16), (72, 36),
                       (36, 36), (36, 80), (16, 80)], np.float32)
    polygon = scene.visuals.Polygon(points, color='red', border_color='white',
                                    border_width=4, border_method='agg', parent=canvas.scene)
    baseline = canvas.render()
    pixel(baseline, 58, 26, RED)
    pixel(baseline, 26, 66, RED)
    pixel(baseline, 58, 66, BLACK)
    pixel(baseline, 58, 36, WHITE)
    pixel(baseline, 36, 66, WHITE)
    polygon.pos = np.empty((0, 2), np.float32)
    np.testing.assert_array_equal(canvas.render()[..., :3], 0)
    polygon.pos = points + (20, 0)
    recovered = canvas.render()
    pixel(recovered, 26, 66, BLACK)
    pixel(recovered, 46, 66, RED)
    pixel(recovered, 56, 66, WHITE)
    pixel(recovered, 60, 66, BLACK)


def test_rectangle_asymmetric_corners_and_recovery(canvas):
    radii = (18, 0, 12, 4)
    rect = scene.visuals.Rectangle(center=(56, 44), width=64, height=52, radius=radii,
                                    color='blue', border_color='white', border_width=4,
                                    border_method='agg', parent=canvas.scene)
    baseline = canvas.render()
    pixel(baseline, 25, 19, BLACK)
    pixel(baseline, 84, 22, BLUE)
    pixel(baseline, 56, 44, BLUE)
    pixel(baseline, 56, 18, WHITE)
    with pytest.raises(ValueError, match='[Rr]adius'):
        rect.radius = (-2, 0, 0, 0)
    assert rect.radius == radii
    np.testing.assert_array_equal(canvas.render(), baseline)
    rect.width = 72
    rect.radius = (0, 18, 4, 12)
    recovered = canvas.render()
    pixel(recovered, 25, 23, BLUE)
    pixel(recovered, 90, 20, BLACK)
    pixel(recovered, 56, 18, WHITE)


def test_regular_polygon_side_count_and_recovery(canvas):
    polygon = scene.visuals.RegularPolygon(center=(56, 46), radius=28, sides=3,
                                           color='red', border_color='white',
                                           border_width=4, border_method='agg',
                                           parent=canvas.scene)
    triangle = canvas.render()
    pixel(triangle, 56, 46, RED)
    pixel(triangle, 38, 46, BLACK)
    pixel(triangle, 42, 46, WHITE)
    polygon.sides = 8
    octagon = canvas.render()
    pixel(octagon, 34, 46, RED)
    pixel(octagon, 28, 46, WHITE)
    pixel(octagon, 32, 22, BLACK)
    with pytest.raises(ValueError, match='3 sides'):
        polygon.sides = 2
    np.testing.assert_array_equal(canvas.render(), octagon)
    polygon.sides = 6
    recovered = canvas.render()
    pixel(recovered, 56, 46, RED)
    pixel(recovered, 56, 22, WHITE)
    pixel(recovered, 56, 18, BLACK)


def test_scrolling_lines_wraparound_and_invalid_row_recovery(canvas):
    lines = scene.visuals.ScrollingLines(
        n_lines=2, line_size=5, dx=16,
        pos_offset=np.array([(16, 16, 0), (16, 54, 0)], np.float32),
        color=np.array([(1, 0, 0, 1), (0, 1, 0, 1)], np.float32),
        parent=canvas.scene,
    )
    lines.set_data(0, np.array([0, 0, 0, 0, 0], np.float32))
    lines.set_data(1, np.array([2, 2, 2, 2, 2], np.float32))
    baseline = canvas.render()
    near(baseline, 40, 16, RED)
    near(baseline, 40, 56, GREEN)
    pixel(baseline, 40, 36, BLACK)
    with pytest.raises((IndexError, ValueError)):
        lines.set_data(2, np.zeros(5, np.float32))
    np.testing.assert_array_equal(canvas.render(), baseline)
    lines.roll_data(np.array([[4, 4, 8], [2, 2, 2]], np.float32))
    lines.roll_data(np.array([[8, 12, 12], [2, 2, 2]], np.float32))
    # Last five values are [4, 8, 8, 12, 12]. Their displayed order
    # crosses the physical end of the texture between x=64 and x=80.
    frame = canvas.render()
    near(frame, 24, 22, RED)
    near(frame, 40, 24, RED)
    near(frame, 56, 26, RED)
    near(frame, 72, 28, RED)
    near(frame, 72, 56, GREEN)
    pixel(frame, 40, 16, BLACK)


def test_spectrogram_tone_bin_window_and_scale_recovery(canvas):
    # 16 DFT samples at 128 Hz, with a 24 Hz tone of unit amplitude.
    x = np.cos(2 * np.pi * 3 * np.arange(48) / 16)
    spectrum = scene.visuals.Spectrogram(
        x, n_fft=16, step=16, fs=128, window=None, color_scale='linear',
        cmap=Colormap(['black', 'white']), clim=(0, .5), parent=canvas.scene,
    )
    spectrum.transform = STTransform(scale=(24, 8), translate=(16, 12))
    baseline = canvas.render()
    assert spectrum.freqs[3] == 24
    for x in (28, 52, 76):
        pixel(baseline, x, 40, WHITE)
        pixel(baseline, x, 32, BLACK)
        pixel(baseline, x, 48, BLACK)

    spectrum.window = 'hann'
    windowed = canvas.render()
    # Hann coherent gain is (N-1)/(2*N) for the symmetric window.
    pixel(windowed, 52, 40, (119, 119, 119), atol=2)
    assert 50 <= windowed[32, 52, 0] <= 75
    with pytest.raises(ValueError, match='color_scale'):
        spectrum.color_scale = 'unsupported'
    np.testing.assert_array_equal(canvas.render(), windowed)
    spectrum.color_scale = 'log'
    spectrum.clim = (-24, 0)
    recovered = canvas.render()
    # 20*log10((15/32)/2) = -12.60 dB, halfway up the chosen transfer range.
    pixel(recovered, 52, 40, (121, 121, 121), atol=3)
    assert recovered[32, 52, 0] < 75
    assert recovered[48, 52, 0] < 75


def test_sphere_latitude_ico_edges_and_construction_recovery(canvas):
    sphere = scene.visuals.Sphere(radius=22, rows=12, cols=16, method='latitude',
                                  color='red', edge_color='white', parent=canvas.scene)
    sphere.transform = STTransform(scale=(1, 1, .03), translate=(32, 46))
    baseline = canvas.render()
    pixel(baseline, 38, 50, RED)
    near(baseline, 32, 46, WHITE)
    near(baseline, 53, 46, WHITE)
    pixel(baseline, 52, 66, BLACK)
    with pytest.raises(Exception, match='Invalid method'):
        scene.visuals.Sphere(method='unknown', parent=canvas.scene)
    np.testing.assert_array_equal(canvas.render(), baseline)

    ico = scene.visuals.Sphere(radius=22, subdivisions=1, method='ico',
                               color='blue', edge_color='white', shading='flat',
                               parent=canvas.scene)
    ico.transform = STTransform(scale=(1, 1, .03), translate=(93, 46))
    frame = canvas.render()
    np.testing.assert_array_equal(frame[:, :61], baseline[:, :61])
    foreground = np.any(frame[:, 61:, :3] != 0, axis=2)
    assert np.all(foreground[36:56, 22:42])
    pixel(frame, 112, 65, BLACK)
    assert np.count_nonzero(np.all(frame[26:67, 72:115, :3] == WHITE, axis=-1)) > 20


def test_surface_plot_nonuniform_ridge_and_recovery(canvas):
    x = np.array([20, 36, 84], np.float32)
    y = np.array([42, 56, 78], np.float32)
    flat = np.zeros((3, 3), np.float32)
    colors = np.empty((3, 3, 4), np.float32)
    colors[:] = [(1, 0, 0, 1)]
    colors[1] = (0, 0, 1, 1)
    surface = scene.visuals.SurfacePlot(x, y, flat, colors=colors, shading=None,
                                       parent=canvas.scene)
    surface.transform = projection((1, 0, 0), (0, 1, 0), (0, -1, .03), (0, 0, 0))
    peer = scene.visuals.Rectangle(center=(108, 42), width=12, height=12,
                                    color='lime', parent=canvas.scene)
    baseline = canvas.render()
    pixel(baseline, 36, 33, BLACK)
    pixel(baseline, 28, 48, (120, 0, 135), atol=2)
    pixel(baseline, 60, 48, (130, 0, 125), atol=2)
    pixel(baseline, 108, 42, GREEN)
    with pytest.raises(TypeError, match='shape'):
        surface.set_data(z=np.zeros((3, 2), np.float32))
    np.testing.assert_array_equal(canvas.render(), baseline)
    ridge = flat.copy()
    ridge[1] = 20
    surface.set_data(z=ridge)
    recovered = canvas.render()
    pixel(recovered, 36, 33, (3, 0, 252), atol=2)
    pixel(recovered, 22, 33, BLACK)
    pixel(recovered, 108, 42, GREEN)
    assert peer.parent is canvas.scene


def test_text_unicode_anchors_rotation_and_device_recovery(canvas):
    old = scene.visuals.Text('ÉÉ', pos=(16, 42), anchor_x='left', anchor_y='top',
                             face='OpenSans', font_size=19, color='white',
                             parent=canvas.scene)
    rotated = scene.visuals.Text('ÉÉ', pos=(90, 56), rotation=90, anchor_x='center',
                                 face='OpenSans', font_size=19, color='red',
                                 parent=canvas.scene)
    baseline = canvas.render()
    left_y, left_x = np.nonzero(baseline[:, :64, 1] > 96)
    right_y, right_x = np.nonzero(baseline[:, 64:, 0] > 96)
    assert 15 <= left_x.min() <= 22 and left_x.max() < 57
    assert 12 <= left_y.min() <= 17 and 33 <= left_y.max() <= 38
    assert np.ptp(left_x) > np.ptp(left_y)
    assert np.ptp(right_y) > np.ptp(right_x)
    assert 84 <= 64 + (right_x.min() + right_x.max()) / 2 <= 96
    assert 50 <= (right_y.min() + right_y.max()) / 2 <= 62

    _dawn.lose_device()
    canvas.set_current()
    np.testing.assert_array_equal(canvas.render(), baseline)
    added = scene.visuals.Text('Ω', pos=(32, 73), face='OpenSans', font_size=19,
                               color='blue', font_manager=old._font_manager,
                               parent=canvas.scene)
    recovered = canvas.render()
    np.testing.assert_array_equal(recovered[:49], baseline[:49])
    np.testing.assert_array_equal(recovered[:, 64:], baseline[:, 64:])
    omega_y, omega_x = np.nonzero(recovered[50:, :64, 2] > 96)
    assert 20 <= omega_x.min() < 32 < omega_x.max() <= 44
    assert 10 <= omega_y.min() < 23 < omega_y.max() <= 37
    assert added.parent is rotated.parent


def test_tube_varying_radius_closed_seam_and_construction_recovery(canvas):
    points = [(14, 24, 0), (40, 24, 0), (64, 38, 0)]
    tube = scene.visuals.Tube(points, radius=[3, 7, 10], color='red',
                              tube_points=16, shading=None, parent=canvas.scene)
    tube.transform = STTransform(scale=(1, 1, .08))
    baseline = canvas.render()
    pixel(baseline, 19, 24, RED)
    pixel(baseline, 19, 29, BLACK)
    pixel(baseline, 36, 29, RED)
    pixel(baseline, 55, 35, RED)
    with pytest.raises(ValueError, match='radii list'):
        scene.visuals.Tube(points, radius=[3, 7], parent=canvas.scene)
    np.testing.assert_array_equal(canvas.render(), baseline)
    ring = [(76, 54, 0), (108, 54, 0), (108, 82, 0), (76, 82, 0), (76, 54, 0)]
    loop = scene.visuals.Tube(ring, radius=5, closed=True, color='blue',
                              tube_points=16, shading=None, parent=canvas.scene)
    loop.transform = STTransform(scale=(1, 1, .08))
    recovered = canvas.render()
    np.testing.assert_array_equal(recovered[:45, :67], baseline[:45, :67])
    for x, y in [(76, 55), (76, 70), (90, 54), (108, 68), (92, 82)]:
        pixel(recovered, x, y, BLUE)
    pixel(recovered, 92, 68, BLACK)
    assert tube.parent is canvas.scene


def test_visual_shared_program_two_views_and_shader_recovery(canvas):
    from vispy.visuals.shaders import Function

    class Triangle(visuals.Visual):
        def __init__(self):
            super().__init__(
                vcode="""attribute vec2 pos;
                         void main() {gl_Position = $transform(vec4(pos, 0., 1.));}""",
                fcode="""uniform vec4 tint;
                         void main() {gl_FragColor = $paint(tint);}""",
            )
            self.shared_program['pos'] = gloo.VertexBuffer(
                np.array([(0, 0), (24, 0), (0, 24)], np.float32))
            self.shared_program['tint'] = (1., 0., 0., 1.)
            self._draw_mode = 'triangles'
            self.set_gl_state('opaque', depth_test=False)

        def _prepare_transforms(self, view):
            view.view_program.vert['transform'] = view.get_transform()

    valid = 'vec4 paint(vec4 c) { return c; }'
    triangle = Triangle()
    triangle.shared_program.frag['paint'] = Function(valid)
    other = triangle.view()
    for view, offset in [(triangle, (16, 22)), (other, (72, 50))]:
        view.transforms.configure(canvas=canvas, viewport=(0, 0, *SIZE))
        view.transforms.visual_transform = STTransform(translate=offset)

    def draw():
        gloo.set_viewport(0, 0, *SIZE)
        gloo.clear(color=(0, 0, 0, 1))
        triangle.draw()
        other.draw()
        return gloo.read_pixels()

    baseline = draw()
    pixel(baseline, 20, 26, RED)
    pixel(baseline, 76, 54, RED)
    pixel(baseline, 42, 26, BLACK)
    pixel(baseline, 52, 54, BLACK)
    triangle.shared_program['tint'] = (0., 1., 0., 1.)
    shared = draw()
    pixel(shared, 20, 26, GREEN)
    pixel(shared, 76, 54, GREEN)

    triangle.shared_program.frag['paint'] = Function(
        'vec4 paint(vec4 c) { return unknown_variable; }')
    with pytest.raises(RuntimeError, match='unknown_variable'):
        draw()
    triangle.shared_program.frag['paint'] = Function(valid)
    np.testing.assert_array_equal(draw(), shared)
    assert _dawn.probe()['pending_draws'] == 0


@pytest.mark.parametrize(('dtype', 'interpolation'), [
    ('uint8', 'nearest'), ('float32', 'linear'),
])
def test_volume_oblique_clip_and_queued_recovery(canvas, targets, dtype, interpolation):
    view = canvas.central_widget.add_view(border_width=0)
    view.camera = scene.cameras.TurntableCamera(
        fov=0, azimuth=0, elevation=90, scale_factor=20, center=(8, 8, 8))
    # Rays along Z see a constant value at each X. The plane keeps x+y >= 16.
    ramp = np.broadcast_to(32 + 8*np.arange(16), (16, 16, 16)).astype(dtype)
    volume = scene.visuals.Volume(
        ramp, clim=(0, 255), cmap=Colormap(['black', 'white']), method='mip',
        texture_format='auto', interpolation=interpolation,
        clipping_planes=[[(8, 8, 8), (1, 1, 0)]],
        clipping_planes_coord_system='visual', parent=view.scene,
    )
    first = queue_draw(canvas, targets[0])
    with pytest.raises(ValueError, match='3D array'):
        volume.set_data(ramp[0])
    volume.set_data((ramp + 48).astype(dtype))
    assert 0 < first < queue_draw(canvas, targets[1])
    with targets[0]:
        old = targets[0].read()
    with targets[1]:
        new = targets[1].read()
    # In the center row x=88 projects near voxel x=13; x=40 is clipped.
    pixel(old, 88, 48, (136, 136, 136), atol=5)
    pixel(new, 88, 48, (184, 184, 184), atol=5)
    for frame in (old, new):
        pixel(frame, 40, 48, BLACK)
        pixel(frame, 4, 4, BLACK)
    assert _dawn.probe()['pending_draws'] == 0


def test_windbarb_calm_speed_bins_and_direction_recovery(canvas):
    barb = scene.visuals.Windbarb(parent=canvas.scene)
    positions = np.array([(28, 25), (92, 25), (28, 72), (92, 72)], np.float32)
    # The wind parameter takes half-knots. These produce calm, half-barb,
    # full-barb and flag glyphs, all with an eastward input direction.
    wind = np.array([(0, 0), (2.5, 0), (5, 0), (25, 0)], np.float32)
    style = dict(size=22, edge_width=2, antialias=.5,
                 face_color='white', edge_color='white')
    barb.set_data(positions, wind, **style)
    baseline = canvas.render()
    pixel(baseline, 28, 25, BLACK)
    assert baseline[28:33, 26:30, 0].max() >= 160
    for x, y in positions[1:].astype(int):
        assert baseline[y-1:y+1, x-10:x-7, 0].max() >= 180
        pixel(baseline, x+9, y, BLACK)

    # The half-barb ends about 19 px left of center. The full barb
    # reaches 25 px left and 7 px up. The flag fills the wedge below it.
    pixel(baseline, 70, 21, BLACK)
    assert baseline[66:70, 4:8, 0].max() >= 180
    assert baseline[69:71, 69:71, 0].min() >= 180
    with pytest.raises(ValueError, match='negative'):
        barb.set_data(positions, wind, **dict(style, edge_width=-1))
    np.testing.assert_array_equal(canvas.render(), baseline)
    wind[:, 1] = 180
    barb.set_data(positions, wind, **style)
    recovered = canvas.render()
    np.testing.assert_array_equal(recovered[:38, :44], baseline[:38, :44])
    for x, y in positions[1:].astype(int):
        assert recovered[y-1:y+1, x+8:x+11, 0].max() >= 180
        pixel(recovered, x-9, y, BLACK)

def test_xyz_axis_projected_triads_and_visibility_recovery(canvas):
    axis = scene.visuals.XYZAxis(parent=canvas.scene)
    basis = ((30, 0, 0), (0, -26, 0), (-20, 16, 1))
    axis.transform = projection(*basis, (45, 52, 0))
    baseline = canvas.render()
    near(baseline, 72, 52, RED)
    near(baseline, 45, 29, GREEN)
    near(baseline, 28, 66, BLUE)
    pixel(baseline, 78, 52, BLACK)

    axis.visible = False
    np.testing.assert_array_equal(canvas.render()[..., :3], 0)
    axis.transform = projection(*basis, (78, 66, 0))
    axis.visible = True
    frame = canvas.render()
    near(frame, 105, 66, RED)
    near(frame, 78, 43, GREEN)
    near(frame, 61, 80, BLUE)
    pixel(frame, 65, 52, BLACK)
    assert axis.parent is canvas.scene
