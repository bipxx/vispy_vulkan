# SPDX-License-Identifier: AGPL-3.0-only
"""Unmodified napari vector-style layers for both renderers (consolidated plan W4, coverage M11).

Vectors (a triangle mesh), tracks (antialiased lines) and a shapes selection (meshes, the antialiased selection
outline and its handles), each captured once with a fixed camera. The comparison per case is fixed here, before any
capture: mesh-only frames are exact; frames with antialiased lines use the smooth-line criterion
(tools/smooth_line_parity.py). Landmarks are semantic and exact.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:  # direct oracle capture invocation
    from fixture_gloo import freeze

SIZE = (128, 96)
CASES = ("vectors", "tracks", "shapes_selected")
CRITERIA = {"vectors": "exact", "tracks": "smooth_line", "shapes_selected": "smooth_line"}
BACKGROUND = (0, 0, 0, 255)
VECTORS = np.array([[[4, 4], [0, 6]], [[8, 10], [4, 4]], [[16, 6], [-4, 8]],
                    [[12, 22], [6, -6]], [[20, 26], [-8, 0]]], np.float32)
VECTOR_COLORS = np.array([[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1], [1, 1, 0, 1], [0, 1, 1, 1]], np.float32)
TRACKS = np.array([[track, t, y, x] for track, path in enumerate((
    [(4 + 3 * t, 4 + 5 * t) for t in range(5)],
    [(20 - 3 * t, 6 + 5 * t) for t in range(5)],
    [(12, 4 + 6 * t) for t in range(5)])) for t, (y, x) in enumerate(path)], np.float32)
# napari reads a two-point ellipse as centre and radii, so the ellipse gives its four bounding-box corners.
SHAPES = ([[2, 3], [10, 12]], [[12, 4], [12, 14], [20, 14], [20, 4]], [[4, 18], [10, 28], [18, 24], [14, 18]])
SHAPE_TYPES = ("rectangle", "ellipse", "polygon")
FACE_COLORS = np.array([[.8, .2, .2, 1], [.2, .8, .2, 1], [.2, .2, .8, 1]], np.float32)


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    inputs = {"vectors": VECTORS, "tracks": TRACKS,
              "shapes_selected": np.concatenate([np.asarray(shape, np.float32).ravel() for shape in SHAPES])}[name]
    return {"case": name, "size": list(SIZE), "camera_center": [0, 11.5, 15.5], "camera_zoom": 4,
            "background": list(BACKGROUND), "criterion": CRITERIA[name],
            "inputs_sha256": hashlib.sha256(np.ascontiguousarray(inputs).tobytes()).hexdigest()}


def render(name):
    """Capture the scene once after all layer state is set, with a fixed camera and canvas size."""
    params = specification(name)
    assert metadata.version("napari") == "0.9.2", "required pinned napari dependency"
    import napari

    viewer = napari.Viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    commands, shaders = [], {}
    parser = scene.context.shared.parser
    original = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA" and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
        return original(batch)

    parser.parse = log
    try:
        if name == "vectors":
            viewer.add_vectors(VECTORS, edge_width=1.0, length=1.0, edge_color=VECTOR_COLORS, opacity=1, name="vectors")
        elif name == "tracks":
            viewer.add_tracks(TRACKS, tail_width=2, tail_length=10, head_length=0, color_by="track_id",
                              colormap="hsv", name="tracks")
            viewer.dims.set_point(0, 4)
        else:
            layer = viewer.add_shapes([np.asarray(shape, np.float32) for shape in SHAPES], shape_type=list(SHAPE_TYPES),
                                      edge_width=1, edge_color="white", face_color=FACE_COLORS, opacity=1, name="shapes")
            layer.mode = "select"
            layer.selected_data = {0, 1, 2}
            layer._set_highlight(force=True)
        canvas.native.setFixedSize(*SIZE)
        scene.app.native.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        viewer.scene.camera.center = (0, 11.5, 15.5)
        viewer.scene.camera.zoom = 4
        scene.bgcolor = tuple(value / 255 for value in BACKGROUND)
        viewer._layer_slicer.wait_until_idle(timeout=10)
        scene.app.native.processEvents()
        scene.app.native.processEvents()
        canvas.on_draw(None)
        image = np.array(scene.render(size=SIZE, alpha=True), copy=True)
        params["camera_rect"] = list(canvas.view.camera.rect.pos + canvas.view.camera.rect.size)
        params["layer_types"] = [type(item).__name__ for item in viewer.layers]
        params["native_mro"] = [cls.__name__ for cls in type(canvas.native).__mro__]
        return image, commands, shaders, params
    finally:
        parser.parse = original
        viewer.close()


def assert_landmarks(name, image):
    """Semantic, exact checks that do not depend on antialiased edges."""
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8, image.shape
    assert image[1, 1].tolist() == list(BACKGROUND), (name, image[1, 1])
    colored = np.any(image[..., :3] != BACKGROUND[:3], axis=2)
    assert colored.sum() > 200, (name, int(colored.sum()))
    if name == "vectors":
        for color in (VECTOR_COLORS * 255).astype(int)[:, :3]:
            assert np.any(np.all(image[..., :3] == color, axis=2)), (name, color.tolist())
    elif name == "shapes_selected":
        for color in np.rint(FACE_COLORS * 255).astype(int)[:, :3]:
            assert np.any(np.all(np.abs(image[..., :3].astype(int) - color) <= 1, axis=2)), (name, color.tolist())
