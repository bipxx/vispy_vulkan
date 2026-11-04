# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari_volume.py (decision D30).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin: the napari version is bound by each reference packet in
tests/reference/napari-volume-opengl-napari-<version>/ instead (tools/napari_host_packets.py).
"""
from __future__ import annotations

import hashlib

import numpy as np

try:
    from .fixture_napari_volume import CASES, SIZE, assert_landmarks, freeze, labels
except ImportError:  # direct oracle capture invocation
    from fixture_napari_volume import CASES, SIZE, assert_landmarks, freeze, labels


def render(name):
    if name not in CASES:
        raise ValueError(name)
    import napari
    from napari.utils.colormaps import DirectLabelColormap

    viewer = napari.Viewer(ndisplay=3, show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    scene.app.native.setQuitOnLastWindowClosed(False)
    commands, shaders, inputs = [], {}, []
    parser = scene.context.shared.parser
    original = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA" and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
        return original(batch)

    parser.parse = log

    def record(array):
        inputs.append({"shape": list(array.shape), "dtype": array.dtype.str,
                       "sha256": hashlib.sha256(array.tobytes()).hexdigest()})
        return array

    try:
        data = labels()
        cmap = DirectLabelColormap(color_dict={0: (0, 0, 0, 0), 7: (1, 0, 0, 1),
            65537: (0, 1, 0, 1), 16777473: (0, 0, 1, 1), None: (1, 1, 0, 1)})
        kwargs = {"colormap": cmap, "opacity": 1, "blending": "translucent",
                  "rendering": "iso_categorical" if name.startswith("iso_") else "translucent",
                  "iso_gradient_mode": "smooth" if name.endswith("smooth") else "fast"}
        if name == "categorical_plane":
            kwargs.update(depiction="plane", plane={"position": (15.5, 15.5, 15.5),
                                                    "normal": (0, 1, 0), "thickness": 1})
        if name == "categorical_clip":
            kwargs.update(experimental_clipping_planes=[
                {"position": (15.5, 15.5, 15.5), "normal": (0, 0, 1), "enabled": True}])
        layer = viewer.add_labels(record(data), **kwargs)
        if name == "categorical_edit":
            layer.data[12:20, :, 17:22][layer.data[12:20, :, 17:22] != 0] = 16777473
            layer.refresh()
            record(layer.data)
        canvas.native.setFixedSize(*SIZE)
        scene.app.native.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        viewer.scene.camera.center = (15.5, 15.5, 15.5)
        viewer.scene.camera.zoom = 2.4
        viewer.scene.camera.perspective = 0
        viewer.scene.camera.set_view_direction((0, 1, 0), up_direction=(-1, 0, 0))
        scene.bgcolor = (32 / 255, 64 / 255, 128 / 255, 1)
        viewer._layer_slicer.wait_until_idle(timeout=10)
        scene.app.native.processEvents()
        scene.app.native.processEvents()
        node = canvas.layer_to_visual[layer].node
        # Hold the quality setting identical for both implementations.
        node.relative_step_size = .5
        canvas.on_draw(None)
        image = np.array(scene.render(size=SIZE, alpha=True), copy=True)
        params = {"case": name, "size": list(SIZE), "inputs": inputs,
            "labels": [0, 7, 65537, 16777473], "method": node.method,
            "depiction": str(layer.depiction), "iso_gradient_mode": node.iso_gradient_mode,
            "relative_step_size": node.relative_step_size, "interpolation": node.interpolation,
            "camera_center": list(viewer.scene.camera.center), "camera_zoom": viewer.scene.camera.zoom,
            "camera_view_direction": list(viewer.scene.camera.view_direction),
            "camera_up_direction": list(viewer.scene.camera.up_direction),
            "camera_scale_factor": canvas.view.camera.scale_factor,
            "native_mro": [cls.__name__ for cls in type(canvas.native).__mro__]}
        return image, commands, shaders, params
    finally:
        viewer.close()
