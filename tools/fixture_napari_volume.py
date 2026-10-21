"""Unmodified napari categorical 3D workflows and host-composed shaders."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (96, 96)
CASES = ("iso_categorical_fast", "iso_categorical_smooth", "translucent_categorical",
         "categorical_plane", "categorical_clip", "categorical_edit")


def labels():
    axis = np.linspace(-1, 1, 32, dtype=np.float32)
    z, y, x = np.meshgrid(axis, axis, axis, indexing="ij")
    inside = (x / .7) ** 2 + (y / .55) ** 2 + (z / .4) ** 2 <= 1
    return np.where(inside, np.where(x < 0, 7, 65537), 0).astype(np.int32)


def render(name):
    if name not in CASES:
        raise ValueError(name)
    assert metadata.version("napari") == "0.9.2"
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


def assert_landmarks(name, image):
    assert image.shape == (96, 96, 4)
    background = [32, 64, 128, 255]
    assert image[2, 2].tolist() == background
    if name == "categorical_clip":
        assert image[48, 32].tolist() == background
    else:
        left = image[48, 32]
        assert left[0] >= 200 and left[1] == left[2] == 0 and left[3] == 255, left
    # x=60 projects to data x=20.7, inside the edited [17,22) block.
    right = image[48, 60 if name == "categorical_edit" else 64]
    if name == "categorical_edit":
        assert right.tolist() == [0, 0, 255, 255], right
    else:
        assert right[1] >= 200 and right[0] == right[2] == 0 and right[3] == 255, right
    assert np.any(image[..., :3] != np.asarray(background[:3]))
