# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari_vector_layers.py (decision D30).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin: the napari version is bound by each reference packet in
tests/reference/napari-vector-layers-opengl-napari-<version>/ instead (tools/napari_host_packets.py).
"""
from __future__ import annotations

import numpy as np

try:
    from .fixture_napari_vector_layers import (BACKGROUND, CASES, CRITERIA, FACE_COLORS, SHAPES, SHAPE_TYPES, SIZE,
                                               TRACKS, VECTORS, VECTOR_COLORS, assert_landmarks, freeze, specification)
except ImportError:  # direct oracle capture invocation
    from fixture_napari_vector_layers import (BACKGROUND, CASES, CRITERIA, FACE_COLORS, SHAPES, SHAPE_TYPES, SIZE,
                                              TRACKS, VECTORS, VECTOR_COLORS, assert_landmarks, freeze, specification)


def render(name):
    """Capture the scene once after all layer state is set, with a fixed camera and canvas size."""
    params = specification(name)
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
