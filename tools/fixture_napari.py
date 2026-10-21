"""Unmodified napari scientific image/label fixtures for both renderers."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:  # direct tools/oracle_napari_capture.py invocation
    from fixture_gloo import freeze

SIZE = (128, 96)
DATA_SIZE = (24, 32)
CASES = (
    "scalar_clim", "scalar_gamma", "scalar_nan", "scalar_auto_clim", "scalar_colormap",
    "rgba_nearest", "scalar_linear", "signed_int16", "unsigned_uint16",
    "labels_sparse", "labels_edit", "transparent_export",
    "blend_opaque", "blend_translucent", "blend_translucent_no_depth",
    "blend_additive", "blend_minimum",
)
EXACT = {"labels_sparse", "labels_edit", "rgba_nearest", "blend_opaque"}


def _blocks(values, dtype=np.float32):
    array = np.empty(DATA_SIZE, dtype)
    for index, value in enumerate(values):
        array[:, index * 8:(index + 1) * 8] = value
    return array


def render(name):
    """Capture scene export once after all edits with fixed camera and pixels."""
    if name not in CASES:
        raise ValueError(name)
    assert metadata.version("napari") == "0.9.2", "required pinned napari dependency"
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


def masks(name, shape):
    """Fixed edge bands based on the prescribed camera, never image fitting."""
    edge = np.zeros(shape[:2], bool)
    columns = (32, 64, 96)
    rows = ()
    if name in ("rgba_nearest", "transparent_export") or name.startswith("blend_"):
        columns, rows = (12, 44, 72, 112), (8, 40, 48, 80)
    elif name == "labels_edit":
        columns, rows = (32, 36, 56, 64, 96), (8, 32)
    elif name == "scalar_nan":
        columns, rows = (8, 24, 32, 64, 96), (8, 32)
    for column in columns:
        edge[:, max(0, column - 1):column + 1] = True
    for row in rows:
        edge[max(0, row - 1):row + 1] = True
    return ~edge, edge


def assert_landmarks(name, image):
    assert image.shape == (96, 128, 4), image.shape
    if name.startswith("labels_"):
        for x, color in zip((16, 48, 80, 112), ([32, 64, 128, 255], [255, 0, 0, 255],
                                               [0, 255, 0, 255], [0, 0, 255, 255])):
            assert image[48, x].tolist() == color, (name, x, image[48, x])
        if name == "labels_edit":
            assert image[20, 44].tolist() == [0, 0, 255, 255]
    elif name in ("scalar_clim", "scalar_gamma", "scalar_auto_clim", "signed_int16", "unsigned_uint16", "scalar_linear"):
        values = {"scalar_clim": (0, 0, 128, 255), "scalar_gamma": (0, 16, 64, 255),
                  "scalar_auto_clim": (0, 109, 182, 255), "signed_int16": (0, 127, 128, 255),
                  "unsigned_uint16": (0, 128, 195, 255), "scalar_linear": (0, 0, 128, 255)}[name]
        for x, value in zip((16, 48, 80, 112), values):
            assert np.max(np.abs(image[48, x, :3].astype(int) - value)) <= 1, (name, x, image[48, x])
    elif name == "rgba_nearest":
        assert image[20, 28].tolist() == [255, 0, 0, 255]
        assert image[64, 92].tolist() == [0, 255, 0, 255]
        assert image[80, 16].tolist() == [20, 40, 60, 255]
    elif name == "transparent_export":
        assert image[80, 16, 3] == 0
        assert abs(int(image[20, 28, 3]) - 128) <= 1
        assert image[64, 92, 3] == 255
    elif name == "scalar_nan":
        assert image[20, 16].tolist() == [32, 64, 128, 255], image[20, 16]
        assert image[48, 16].tolist() == [0, 0, 0, 255], image[48, 16]
