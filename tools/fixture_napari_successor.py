# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari.py (decision D30).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin: the napari version is bound by each reference packet in
tests/reference/napari-opengl-napari-<version>/ instead (tools/napari_host_packets.py).
"""
from __future__ import annotations

import hashlib

import numpy as np

try:
    from .fixture_napari import CASES, DATA_SIZE, EXACT, SIZE, assert_landmarks, freeze, masks, _blocks
except ImportError:  # direct oracle capture invocation
    from fixture_napari import CASES, DATA_SIZE, EXACT, SIZE, assert_landmarks, freeze, masks, _blocks


def render(name):
    """Capture scene export once after all edits with fixed camera and pixels."""
    if name not in CASES:
        raise ValueError(name)
    import napari
    from napari.utils.colormaps import Colormap, DirectLabelColormap

    viewer = napari.Viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    commands, shaders, inputs = [], {}, []
    parser = scene.context.shared.parser
    original = parser.parse

    def log(commands_batch):
        for command in commands_batch:
            commands.append(freeze(command))
            if command[0] == "DATA" and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
        return original(commands_batch)

    parser.parse = log

    def record(array):
        inputs.append({"shape": list(array.shape), "dtype": array.dtype.str,
                       "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()})
        return array

    try:
        params = {"camera_center": [0, 11.5, 15.5], "camera_zoom": 4,
                  "size": list(SIZE), "data_size": list(DATA_SIZE), "case": name}
        if name.startswith("labels_"):
            labels = _blocks([0, 7, 65537, 16777473], np.int32)
            cmap = DirectLabelColormap(color_dict={0: (0, 0, 0, 0),
                7: (1, 0, 0, 1), 65537: (0, 1, 0, 1), 16777473: (0, 0, 1, 1),
                None: (1, 1, 0, 1)})
            layer = viewer.add_labels(record(labels), colormap=cmap, opacity=1,
                                      blending="translucent")
            if name == "labels_edit":
                layer.data[2:8, 9:14] = 16777473
                layer.refresh()
                record(layer.data)
            params["labels"] = [0, 7, 65537, 16777473]
        elif name.startswith("blend_"):
            first = np.full((*DATA_SIZE, 4), [.2, .4, .6, 1], np.float32)
            second = np.full((*DATA_SIZE, 4), [.8, .3, .1, .5], np.float32)
            second[2:10, 3:11] = [.1, .9, .2, .25]
            viewer.add_image(record(first), rgb=True, blending="opaque",
                             interpolation2d="nearest")
            layer = viewer.add_image(record(second), rgb=True, blending=name[6:],
                                     interpolation2d="nearest", opacity=.75)
            params["blending"] = name[6:]
        elif name == "rgba_nearest":
            data = np.zeros((*DATA_SIZE, 4), np.uint8)
            data[:] = [20, 40, 60, 255]
            data[2:10, 3:11] = [255, 0, 0, 255]
            data[12:20, 18:28] = [0, 255, 0, 255]
            layer = viewer.add_image(record(data), rgb=True, blending="opaque",
                                     interpolation2d="nearest")
        elif name == "transparent_export":
            data = np.zeros((*DATA_SIZE, 4), np.uint8)
            data[2:10, 3:11] = [255, 0, 0, 128]
            data[12:20, 18:28] = [0, 255, 0, 255]
            layer = viewer.add_image(record(data), rgb=True, blending="translucent",
                                     interpolation2d="nearest")
        else:
            data = _blocks([-10, 5, 15, 25])
            kwargs = {"colormap": "gray", "contrast_limits": (10, 20),
                      "interpolation2d": "nearest", "blending": "opaque"}
            if name == "scalar_gamma":
                data = _blocks([0, .25, .5, 1])
                kwargs.update(contrast_limits=(0, 1), gamma=2)
            elif name == "scalar_nan":
                data = _blocks([0, .25, .5, 1])
                data[2:8, 2:6] = np.nan
                kwargs.update(contrast_limits=(0, 1), blending="translucent")
            elif name == "scalar_auto_clim":
                kwargs.pop("contrast_limits")
            elif name == "scalar_linear":
                kwargs.update(interpolation2d="linear")
            elif name == "scalar_colormap":
                data = _blocks([0, .25, .5, 1])
                kwargs.update(contrast_limits=(0, 1), colormap=Colormap(
                    colors=[(0, 0, 0, 1), (1, 0, 0, 1), (0, 1, 1, 1)],
                    controls=[0, .5, 1], name="fixture-scientific"))
            elif name == "signed_int16":
                data = _blocks([-30000, -100, 100, 30000], np.int16)
                kwargs.update(contrast_limits=(-30000, 30000))
            elif name == "unsigned_uint16":
                data = _blocks([0, 32768, 50000, 65535], np.uint16)
                kwargs.update(contrast_limits=(0, 65535))
            layer = viewer.add_image(record(data), **kwargs)
            params.update(contrast_limits=list(layer.contrast_limits), gamma=layer.gamma,
                          interpolation=layer.interpolation2d)
        canvas.native.setFixedSize(*SIZE)
        scene.app.native.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        viewer.scene.camera.center = (0, 11.5, 15.5)
        viewer.scene.camera.zoom = 4
        if name == "transparent_export":
            scene.bgcolor = (0, 0, 0, 0)
        elif name.startswith("labels_") or name == "scalar_nan":
            # A visible background distinguishes transparent NaNs/label zero
            # from an incorrect opaque zero-intensity sample.
            scene.bgcolor = (32 / 255, 64 / 255, 128 / 255, 1)
        else:
            scene.bgcolor = (0, 0, 0, 1)
        # Finish the host's asynchronous data slicing before the capture.
        # This waits on CPU slicing futures, outside any measured render path.
        viewer._layer_slicer.wait_until_idle(timeout=10)
        scene.app.native.processEvents()
        scene.app.native.processEvents()
        canvas.on_draw(None)
        image = np.array(scene.render(size=SIZE, alpha=True), copy=True)
        params["camera_rect"] = list(canvas.view.camera.rect.pos + canvas.view.camera.rect.size)
        params["inputs"] = inputs
        params["layer_types"] = [type(item).__name__ for item in viewer.layers]
        params["native_mro"] = [cls.__name__ for cls in type(canvas.native).__mro__]
        return image, commands, shaders, params
    finally:
        viewer.close()
