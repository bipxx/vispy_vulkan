"""Fixed public mesh/filter/layout/text scenes, authored before candidate pixels.

Each scene has one final color read. Comparison covers every pixel; text and
layout are exact, and shaded/filter meshes permit one UNORM8 rounding step.
No candidate alignment, edge exclusion, or fitted color transform is allowed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (224, 160)
BACKGROUND = (16, 24, 32, 255)
CASES = ('mesh_flat', 'mesh_smooth', 'surface_plot', 'mesh_texture_clip',
         'mesh_filter_detach', 'mesh_wireframe_clip', 'mesh_perspective',
         'mesh_polygon_offset', 'grid_clipping', 'axes_colorbar',
         'text_dpi96', 'text_dpi120', 'text_dpi144')
EXACT = {'mesh_polygon_offset', 'grid_clipping', 'axes_colorbar',
         'text_dpi96', 'text_dpi120', 'text_dpi144'}
ORTHOGRAPHIC = {'mesh_flat', 'mesh_smooth', 'surface_plot', 'mesh_texture_clip',
                'mesh_filter_detach', 'mesh_wireframe_clip', 'mesh_polygon_offset'}
TEXT = 'Ag\n15'
TEXT_PLACEMENTS = (((32, 24), 'left', 'top', 0),
                   ((112, 80), 'center', 'center', 30),
                   ((192, 136), 'right', 'bottom', -90))


def array_record(array):
    array = np.ascontiguousarray(array)
    return dict(shape=list(array.shape), dtype=array.dtype.str,
                sha256=hashlib.sha256(array.tobytes()).hexdigest())


def context_provenance(gloo):
    return {key: str(gloo.gl.glGetParameter(getattr(gloo.gl, 'GL_' + key.upper())))
            for key in ('renderer', 'version')}


def inputs():
    vertices = np.array([[24, 24, 0], [200, 24, 0],
                         [24, 136, 0], [200, 136, 64]], np.float32)
    faces = np.array([[0, 1, 2], [1, 3, 2]], np.uint32)
    texcoords = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], np.float32)
    texture = np.empty((8, 8, 4), np.uint8)
    texture[:4, :4], texture[:4, 4:] = (255, 0, 0, 255), (0, 255, 0, 255)
    texture[4:, :4], texture[4:, 4:] = (0, 0, 255, 255), (255, 255, 0, 255)
    x = np.linspace(24, 200, 7, dtype=np.float32)
    y = np.linspace(24, 136, 5, dtype=np.float32)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    z = (16 * (1 - ((xx - 112) / 88) ** 2) * (yy - 24) / 112).astype(np.float32)
    planes = np.array([[[112, 0, 0], [1, 0, 0]],
                       [[0, 120, 0], [0, -1, 0]]], np.float32)
    return dict(vertices=vertices, faces=faces, texcoords=texcoords, texture=texture,
                x=x, y=y, z=z, planes=planes)


def face_normals(vertices, faces):
    triangles = np.asarray(vertices, dtype=np.float64)[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    return normals / np.linalg.norm(normals, axis=1)[:, None]


def case_contract(name):
    if name not in CASES:
        raise ValueError(name)
    data = inputs()
    return dict(case=name, size=list(SIZE), background=list(BACKGROUND),
                dpi=int(name.removeprefix('text_dpi')) if name.startswith('text_') else 96,
                inputs={key: array_record(value) for key, value in data.items()},
                face_normals=face_normals(data['vertices'], data['faces']).tolist(),
                clipping_halfspaces='x >= 112 and y <= 120 in visual coordinates',
                lighting=dict(ambient=.2, diffuse=.8, specular=0, direction=[0, 0, 1]),
                text=TEXT, text_placements=freeze(TEXT_PLACEMENTS), font='OpenSans', font_size=18,
                mesh_projection=dict(rect=[0, 0, *SIZE], depth_value=1000, flip=[False, True, False])
                if name in ORTHOGRAPHIC else None,
                comparison=dict(full_frame_max_abs_u8=0 if name in EXACT else 1,
                                alpha_exact=True, excluded_pixels=0,
                                candidate_alignment_or_color_fit=False),
                reads=1)


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert image[2, 2].tolist() == list(BACKGROUND), (name, image[2, 2])
    if not name.startswith('text_') and name != 'axes_colorbar':
        assert np.all(image[..., 3] == 255), name
    foreground = np.any(image[..., :3] != BACKGROUND[:3], axis=2)
    assert np.count_nonzero(foreground) > 100, 'Blank or trivial scene'
    if name in ('mesh_flat', 'mesh_smooth', 'surface_plot'):
        assert not np.any(np.all(image[40:120, 40:184] == BACKGROUND, axis=2)), 'Clipped mesh interior'
        assert np.ptp(image[40:120, 40:184, 0]) > 4, 'Missing lighting/height variation'
    if name in ('mesh_texture_clip', 'mesh_wireframe_clip'):
        assert np.all(image[30:130, 30:108] == BACKGROUND), 'Left clipping plane leaked'
        assert np.all(image[124:134, 116:194] == BACKGROUND), 'Bottom clipping plane leaked'
        assert np.any(image[40:112, 120:192, :3] != BACKGROUND[:3]), 'All clipped mesh discarded'
    if name == 'mesh_filter_detach':
        assert image[64, 64].tolist() == [255, 255, 255, 255]
        assert image[96, 160].tolist() == [255, 255, 255, 255]
    if name == 'mesh_polygon_offset':
        assert image[80, 112].tolist() == [0, 0, 255, 255]
    if name == 'grid_clipping':
        assert image[80, 56].tolist() == [255, 0, 0, 255]
        assert image[80, 168].tolist() == [0, 255, 0, 255]
        assert np.all(image[16:144, 110:114] == BACKGROUND), 'ViewBox draw spilled into spacing'
        assert np.all(image[0:4] == BACKGROUND), 'ViewBox draw spilled outside layout'


def compare(name, actual, reference):
    assert actual.shape == reference.shape == (SIZE[1], SIZE[0], 4)
    assert actual.dtype == reference.dtype == np.uint8
    limit = case_contract(name)['comparison']['full_frame_max_abs_u8']
    delta = np.abs(actual.astype(np.int16) - reference.astype(np.int16))
    assert np.array_equal(actual[..., 3], reference[..., 3]), 'Alpha differs'
    assert int(delta.max()) <= limit, (name, int(delta.max()), int(np.count_nonzero(delta)))
    assert_landmarks(name, actual)


def render(name, backend='dawn_headless'):
    contract = case_contract(name)
    import vispy
    from vispy import scene
    from vispy.visuals.filters import TextureFilter, WireframeFilter
    from vispy.visuals.filters.clipping_planes import PlanesClipper
    from vispy.visuals.transforms import STTransform

    data = inputs()
    canvas = scene.SceneCanvas(app=backend, size=SIZE, dpi=contract['dpi'],
                               bgcolor=tuple(value / 255 for value in BACKGROUND),
                               show=backend == 'pyqt6', decorate=False, config={'samples': 0})
    if backend == 'pyqt6':
        canvas.app.native.setQuitOnLastWindowClosed(False)
        canvas._backend._vispy_warmup()
    parser = canvas.context.shared.parser
    original = parser.parse
    commands, shaders, uploads = [], {}, {}
    texts, views = [], []

    def parse(batch):
        batch = list(batch)
        for command in batch:
            commands.append(freeze(command))
            if command[0] == 'DATA' and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
            if command[0] == 'DATA' and isinstance(command[3], np.ndarray):
                uploads.setdefault(command[1], []).append((command[2], command[3].copy()))
        return original(batch)

    parser.parse = parse
    try:
        mesh_parent = canvas.scene
        if name in ORTHOGRAPHIC:
            canvas.central_widget.border_width = 0
            view = canvas.central_widget.add_view(border_width=0)
            view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, *SIZE), aspect=None, flip=(False, True, False))
            view.camera.depth_value = 1000
            mesh_parent = view.scene
            views.append(view)
        if name in ('mesh_flat', 'mesh_smooth', 'surface_plot'):
            shading = 'flat' if name == 'mesh_flat' else 'smooth'
            if name == 'surface_plot':
                visual = scene.visuals.SurfacePlot(x=data['x'], y=data['y'], z=data['z'],
                                                   color=(1, .5, .25, 1), shading=shading, parent=mesh_parent)
            else:
                visual = scene.visuals.Mesh(vertices=data['vertices'], faces=data['faces'],
                                            color=(1, .5, .25, 1), shading=shading, parent=mesh_parent)
            visual.shading_filter.ambient_light = (1, 1, 1, .2)
            visual.shading_filter.diffuse_light = (1, 1, 1, .8)
            visual.shading_filter.specular_light = (1, 1, 1, 0)
            visual.shading_filter.light_dir = (0, 0, 1)
            visual.set_gl_state(blend=False, depth_test=True)
        elif name in ('mesh_texture_clip', 'mesh_filter_detach', 'mesh_wireframe_clip'):
            visual = scene.visuals.Mesh(vertices=data['vertices'], faces=data['faces'], color='white',
                                        shading=None, parent=mesh_parent)
            texture = TextureFilter(data['texture'], data['texcoords'])
            planes = PlanesClipper(data['planes'], coord_system='visual')
            visual.attach(texture)
            visual.attach(planes)
            if name == 'mesh_filter_detach':
                visual.detach(planes)
                visual.detach(texture)
            elif name == 'mesh_wireframe_clip':
                visual.attach(WireframeFilter(color='black', width=1.5))
            visual.set_gl_state(blend=False, depth_test=True)
        elif name == 'mesh_perspective':
            view = canvas.central_widget.add_view()
            view.camera = scene.cameras.TurntableCamera(fov=45, elevation=25, azimuth=35,
                                                        distance=4, center=(0, 0, 0))
            vertices = (data['vertices'] - [112, 80, 16]) / [88, 56, 64]
            scene.visuals.Mesh(vertices=vertices.astype(np.float32), faces=data['faces'],
                               face_colors=np.array([[1, 0, 0, 1], [0, 1, 0, 1]], np.float32),
                               shading=None, parent=view.scene)
            views.append(view)
        elif name == 'mesh_polygon_offset':
            vertices = data['vertices'].copy()
            vertices[:, 2] = 0
            for order, color in enumerate(('red', 'blue')):
                visual = scene.visuals.Mesh(vertices=vertices, faces=data['faces'], color=color,
                                            shading=None, parent=mesh_parent)
                visual.order = order
                visual.set_gl_state(blend=False, depth_test=True, depth_func='less',
                                    polygon_offset_fill=order == 0, polygon_offset=(1, 1))
        elif name == 'grid_clipping':
            canvas.central_widget.padding = 8
            grid = canvas.central_widget.add_grid(spacing=8, border_width=0)
            for column, color in enumerate(('red', 'green')):
                view = grid.add_view(row=0, col=column, border_width=0)
                view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, 1, 1))
                scene.visuals.Rectangle(center=(.5, .5), width=3, height=3,
                                        color=(1, 0, 0, 1) if column == 0 else (0, 1, 0, 1),
                                        border_color=None, parent=view.scene)
                views.append(view)
        elif name == 'axes_colorbar':
            canvas.central_widget.padding = 8
            grid = canvas.central_widget.add_grid(spacing=0)
            axis = scene.AxisWidget(orientation='bottom', axis_color='white', text_color='white',
                                    axis_label='x', axis_font_size=9, tick_font_size=8)
            axis.height_max = 28
            grid.add_widget(axis, row=1, col=0)
            view = grid.add_view(row=0, col=0)
            view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, 1, 1))
            scene.visuals.Image(data['texture'], interpolation='nearest', parent=view.scene,
                                method='subdivide').transform = STTransform(scale=(.125, .125, 1))
            axis.link_view(view)
            bar = scene.ColorBarWidget(cmap='grays', orientation='right', clim=(0, 1),
                                       label='value', label_color='white', border_width=0)
            bar.width_max = 42
            grid.add_widget(bar, row=0, col=1, row_span=2)
            views.append(view)
        else:
            for position, anchor_x, anchor_y, rotation in TEXT_PLACEMENTS:
                texts.append(scene.visuals.Text(TEXT, pos=position, anchor_x=anchor_x, anchor_y=anchor_y,
                                                rotation=rotation, face='OpenSans', font_size=18, method='cpu',
                                                color='white', parent=canvas.scene))
        image = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        extras = {}
        seen_atlases = set()
        for text in texts:
            atlas = text._font._atlas
            if atlas.id in seen_atlases:
                continue
            seen_atlases.add(atlas.id)
            array = np.zeros(atlas.shape, np.uint8)
            for offset, patch in uploads.get(atlas.id, []):
                slices = tuple(slice(start, start + count) for start, count in zip(offset, patch.shape))
                array[slices] = patch
            assert int(array.max()) > 128, 'Real CPU SDF atlas upload missing'
            extras['cpu_atlas_' + str(len(extras))] = array
        params = dict(contract)
        if texts:
            font = Path(vispy.__file__).resolve().parent / 'util/fonts/data/OpenSans-Regular.ttf'
            params.update(font_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),
                          font_license='Apache-2.0; bundled OpenSans font',
                          glyphs={char: {key: freeze(value) for key, value in glyph.items() if key != 'bitmap'}
                                  for char, glyph in sorted(texts[0]._font._glyphs.items())})
        params['view_rectangles'] = [[float(value) for value in (*view.pos, *view.size)] for view in views]
        params['cpu_atlases'] = {key: array_record(value) for key, value in extras.items()}
        from vispy import gloo
        params['context'] = context_provenance(gloo)
        return image, commands, shaders, params, extras
    finally:
        parser.parse = original
        canvas.close()
