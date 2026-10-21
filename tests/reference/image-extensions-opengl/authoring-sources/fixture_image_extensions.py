"""Independent public image/label extension workflows; no renderer patches.

All data, landmarks and exact comparison criteria are authored before any
candidate render. Private attributes below are read-only observations of the
actual selected host texture; all mutations use public layer/visual APIs.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (128, 96)
DATA_SIZE = (24, 32)
BACKGROUND = (32, 64, 128, 255)
HIGH_A, HIGH_B = 16777216, 16777217
CASES = (
    "scalar_uint8_host", "scalar_int8_host", "rgb_three",
    "cpu_scalar_nan", "gpu_scalar_nan", "rgba_nan",
    "multiplicative", "additive_channels", "labels_signed_remap",
    "labels_paint_tile", "multiscale_level0_retained",
    "multiscale_level1_edit", "slice_change",
)
VISPY_CASES = {"cpu_scalar_nan", "gpu_scalar_nan", "rgba_nan"}
COMPARISON = {"full_frame_exact": True, "landmark_max_abs_u8": 1,
              "candidate_alignment_or_color_fit": False}


def array_record(array):
    array = np.asarray(array)
    return {"shape": list(array.shape), "dtype": array.dtype.str,
            "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()}


def _blocks(values, dtype=np.uint8, shape=DATA_SIZE):
    data = np.empty(shape, dtype=dtype)
    width = shape[1] // 4
    for index, value in enumerate(values):
        data[:, width * index:width * (index + 1)] = value
    return data


def input_arrays(name):
    """New copies of deterministic authoring arrays; this imports no GUI."""
    if name not in CASES:
        raise ValueError(name)
    if name == "scalar_uint8_host":
        return [_blocks([0, 64, 192, 255])]
    if name == "scalar_int8_host":
        return [_blocks([-128, -64, 64, 127], np.int8)]
    if name == "rgb_three":
        data = np.empty((*DATA_SIZE, 3), np.uint8)
        data[:] = (20, 40, 60)
        data[2:10, 3:11] = (255, 0, 0)
        data[12:20, 18:28] = (0, 255, 0)
        data[12:20, 3:11] = (0, 0, 255)
        return [data]
    if name in ("cpu_scalar_nan", "gpu_scalar_nan"):
        data = _blocks([10, 12.5, 15, 20], np.float32)
        data[2:8, 2:6] = np.nan
        return [data]
    if name == "rgba_nan":
        data = np.empty((*DATA_SIZE, 4), np.float32)
        data[:] = (.25, .5, .75, 1)
        data[2:8, 2:6, 0] = np.nan
        data[12:20, 18:28, 3] = np.nan
        return [data]
    if name == "multiplicative":
        first = np.empty((*DATA_SIZE, 4), np.uint8)
        second = np.empty_like(first)
        first[:] = (128, 192, 64, 255)
        second[:] = (128, 64, 192, 128)
        second[2:10, 3:11] = (64, 192, 128, 64)
        return [first, second]
    if name == "additive_channels":
        channels = np.empty((3, *DATA_SIZE), np.float32)
        channels[0], channels[1], channels[2] = .25, .5, .75
        channels[:, 2:8, 2:6] = 0
        return [channels]
    if name in ("labels_signed_remap", "labels_paint_tile"):
        return [_blocks([-7, 0, HIGH_A, HIGH_B], np.int32)]
    if name.startswith("multiscale_"):
        return [_blocks([0, 64, 128, 255]),
                _blocks([32, 96, 160, 224], shape=(12, 16)),
                _blocks([224, 160, 96, 32], shape=(6, 8))]
    if name == "slice_change":
        return [np.stack([_blocks([0, 64, 128, 255]),
                          _blocks([32, 96, 160, 224]),
                          _blocks([255, 192, 64, 0])])]
    raise AssertionError(name)


def paint_mask():
    """Integer-center public brush_size5 disc: radius2.5, not a fitted mask."""
    y, x = np.mgrid[:DATA_SIZE[0], :DATA_SIZE[1]]
    return (y - 6) ** 2 + (x - 10) ** 2 <= 2.5 ** 2


def final_arrays(name):
    data = input_arrays(name)
    if name == "labels_paint_tile":
        data[0][paint_mask()] = HIGH_B
    elif name.startswith("multiscale_"):
        data[1][2:4, 5:7] = 255
    elif name == "slice_change":
        data[0][1, 4:8, 9:13] = 255
    return data


def case_contract(name):
    landmarks = []

    def point(y, x, rgba):
        landmarks.append({"row": y, "column": x, "rgba": list(rgba)})

    def gray(values):
        for x, value in zip((16, 48, 80, 112), values):
            point(48, x, (value, value, value, 255))

    if name in ("scalar_uint8_host", "scalar_int8_host"):
        gray((0, 64, 192, 255))
    elif name == "rgb_three":
        point(20, 28, (255, 0, 0, 255))
        point(64, 92, (0, 255, 0, 255))
        point(64, 28, (0, 0, 255, 255))
        point(80, 16, (20, 40, 60, 255))
    elif name in ("cpu_scalar_nan", "gpu_scalar_nan"):
        gray((0, 64, 128, 255))
        point(20, 16, (0, 0, 0, 255) if name.startswith("cpu_") else BACKGROUND)
    elif name == "rgba_nan":
        point(20, 16, (0, 128, 191, 255))
        point(64, 92, BACKGROUND)
        point(80, 16, (64, 128, 191, 255))
    elif name == "multiplicative":
        point(48, 80, (64, 48, 48, 255))
        point(20, 28, (32, 145, 32, 255))
    elif name == "additive_channels":
        point(48, 80, (32, 32, 143, 255))
        point(20, 16, (0, 0, 0, 255))
    elif name in ("labels_signed_remap", "labels_paint_tile"):
        for x, color in zip((16, 48, 80, 112),
                            ((255, 0, 0, 255), BACKGROUND,
                             (0, 255, 0, 255), (0, 0, 255, 255))):
            point(48, x, color)
        if name == "labels_paint_tile":
            point(26, 42, (0, 0, 255, 255))
            point(18, 34, BACKGROUND)  # Brush bounding-box corner stays zero.
            point(14, 42, BACKGROUND)  # Outside the updated bounding box.
    elif name == "multiscale_level0_retained":
        gray((0, 64, 128, 255))
        point(24, 48, (64, 64, 64, 255))
    elif name == "multiscale_level1_edit":
        gray((32, 96, 160, 224))
        point(24, 48, (255, 255, 255, 255))
    elif name == "slice_change":
        gray((32, 96, 160, 224))
        point(24, 44, (255, 255, 255, 255))
        point(24, 32, (96, 96, 96, 255))
    else:
        raise ValueError(name)
    return {"case": name, "size": list(SIZE),
            "workflow": "public ImageVisual" if name in VISPY_CASES else "public napari0.9.2",
            "comparison": COMPARISON.copy(), "landmarks": landmarks,
            "inputs": [array_record(a) for a in input_arrays(name)],
            "final_inputs": [array_record(a) for a in final_arrays(name)],
            "readbacks": "one final scene.render; no intermediate readback",
            "multiscale_revision_scope": "per-level CPU content plus real selected-texture GLIR uploads; no fictitious per-level GPU cache"}


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4), image.shape
    for landmark in case_contract(name)["landmarks"]:
        y, x = landmark["row"], landmark["column"]
        delta = np.abs(image[y, x].astype(np.int16) - landmark["rgba"])
        assert delta.max() <= COMPARISON["landmark_max_abs_u8"], (
            name, y, x, image[y, x].tolist(), landmark["rgba"])


class _Trace:
    def __init__(self, parser):
        self.parser, self.original = parser, parser.parse
        self.commands, self.shaders, self.uploads = [], {}, []
        self.stage, self.stage_commands = "initial", []

        def log(batch):
            for command in batch:
                index = len(self.commands)
                self.commands.append(freeze(command))
                self.stage_commands.append({"stage": self.stage, "command_index": index})
                if command[0] == "DATA":
                    if isinstance(command[3], str):
                        self.shaders[str(command[1])] = command[3]
                    elif isinstance(command[3], np.ndarray):
                        self.uploads.append({"id": command[1], "offset": [int(v) for v in command[2]]
                            if isinstance(command[2], tuple) else command[2],
                            "array": command[3].copy(), "stage": self.stage,
                            "command_index": index})
            return self.original(batch)

        parser.parse = log

    def close(self):
        self.parser.parse = self.original

    def records(self, texture_id):
        return [{"offset": item["offset"], "stage": item["stage"],
                 "command_index": item["command_index"], **array_record(item["array"])}
                for item in self.uploads if item["id"] == texture_id]

    def full_texture(self, texture_id, shape):
        result = None
        for item in self.uploads:
            if item["id"] != texture_id:
                continue
            patch = item["array"]
            if patch.ndim > len(shape) and patch.shape[-1] == 1:
                patch = patch[..., 0]
            offset = item["offset"]
            if not isinstance(offset, list):
                continue
            offset = offset[:len(shape)]
            if result is None:
                result = np.zeros(shape, patch.dtype)
            slices = tuple(slice(start, start + length) for start, length in zip(offset, patch.shape))
            result[slices] = patch
        assert result is not None, "selected texture has no actual parsed upload"
        return result


def _context_samples():
    from vispy import gloo
    return int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))


def _render_vispy(name, backend):
    from vispy import scene
    from vispy.visuals.transforms import STTransform

    canvas = scene.SceneCanvas(app=backend, size=SIZE, show=backend == "pyqt6",
        decorate=False, bgcolor=tuple(v / 255 for v in BACKGROUND), config={"samples": 0})
    if backend == "pyqt6":
        canvas.app.native.setQuitOnLastWindowClosed(False)
        canvas._backend._vispy_warmup()
    trace = _Trace(canvas.context.shared.parser)
    try:
        fmt = None if name == "cpu_scalar_nan" else "r32f" if name == "gpu_scalar_nan" else "rgba32f"
        data = input_arrays(name)[0]
        visual = scene.visuals.Image(data, cmap="gray", clim=(10, 20) if data.ndim == 2 else (0, 1),
            interpolation="nearest", texture_format=fmt, parent=canvas.scene)
        visual.transform = STTransform(scale=(4, 4, 1))
        visual.set_gl_state(blend=True, depth_test=False,
            blend_func=("src_alpha", "one_minus_src_alpha", "one", "one_minus_src_alpha"))
        canvas.set_current()
        samples = _context_samples()
        trace.stage = "final_read"
        image = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        params = case_contract(name)
        params.update(texture_format_requested=fmt, clim=[float(v) for v in visual.clim],
            texture_uploads=trace.records(visual._texture.id),
            current_context_samples=samples, sample_query_scope="actual current context; render export allocates its own single-sample FBO",
            stage_commands=trace.stage_commands)
        return image, trace.commands, trace.shaders, params
    finally:
        trace.close()
        canvas.close()


def _render_host(name):
    assert metadata.version("napari") == "0.9.2"
    assert metadata.version("numba") == "0.68.0"
    import napari
    from napari._qt.qt_event_loop import get_qapp
    from napari.utils.colormaps import DirectLabelColormap

    qapp = get_qapp()
    qapp.setQuitOnLastWindowClosed(False)
    viewer = napari.Viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    trace = _Trace(scene.context.shared.parser)
    data = input_arrays(name)
    params = case_contract(name)
    source_revisions = [{"stage": "initial", "levels": [array_record(a) for a in data]}]
    labels_events = []

    def ready(stage, draw=True):
        trace.stage = stage
        viewer._layer_slicer.wait_until_idle(timeout=10)  # CPU slicing, no GPU wait.
        qapp.processEvents()
        qapp.processEvents()
        if draw:
            canvas.on_draw(None)  # Public host scheduling; no intermediate readback.

    try:
        kwargs = {"interpolation2d": "nearest", "blending": "opaque"}
        if name.startswith("labels_"):
            cmap = DirectLabelColormap(color_dict={0: (0, 0, 0, 0), -7: (1, 0, 0, 1),
                HIGH_A: (0, 1, 0, 1), HIGH_B: (0, 0, 1, 1), None: (1, 1, 0, 1)})
            layer = viewer.add_labels(data[0], colormap=cmap, opacity=1, blending="translucent")

            def observe(event):
                labels_events.append({"offset": [int(v) for v in event.offset], **array_record(event.data)})

            layer.events.labels_update.connect(observe)
        elif name == "multiplicative":
            viewer.add_image(data[0], rgb=True, **kwargs)
            layer = viewer.add_image(data[1], rgb=True, interpolation2d="nearest", blending="multiplicative")
        elif name == "additive_channels":
            layers = viewer.add_image(data[0], channel_axis=0, rgb=False,
                colormap=["red", "green", "blue"], contrast_limits=(0, 1),
                opacity=[1, .25, .75], blending="additive", interpolation2d="nearest")
            layer = layers[0]
        elif name.startswith("multiscale_"):
            layer = viewer.add_image(data, multiscale=True, locked_data_level=0,
                contrast_limits=(0, 255), colormap="gray", **kwargs)
        elif name == "slice_change":
            layer = viewer.add_image(data[0], rgb=False, contrast_limits=(0, 255), colormap="gray", **kwargs)
            viewer.dims.set_point(0, 0)
        elif name == "rgb_three":
            layer = viewer.add_image(data[0], rgb=True, **kwargs)
        else:
            clim = (-128, 127) if name == "scalar_int8_host" else (0, 255)
            layer = viewer.add_image(data[0], colormap="gray", contrast_limits=clim, **kwargs)
        canvas.native.setFixedSize(*SIZE)
        qapp.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        viewer.scene.camera.center = (0, 11.5, 15.5)
        viewer.scene.camera.zoom = 4
        scene.bgcolor = tuple(value / 255 for value in BACKGROUND)
        ready("prewarm")
        if name == "labels_paint_tile":
            trace.stage = "paint_offset_tile"
            layer.brush_size = 5
            layer.paint((6, 10), HIGH_B)
            assert np.array_equal(layer.data, final_arrays(name)[0])
            source_revisions.append({"stage": "painted", "levels": [array_record(layer.data)]})
            ready("painted")
        elif name.startswith("multiscale_"):
            layer.locked_data_level = 1
            ready("selected_level1")
            data[1][2:4, 5:7] = 255
            layer.refresh()
            source_revisions.append({"stage": "level1_edit", "levels": [array_record(a) for a in data]})
            ready("level1_edit")
            layer.locked_data_level = 2
            ready("selected_level2")
            layer.locked_data_level = 0
            ready("revisited_level0")
            if name == "multiscale_level1_edit":
                layer.locked_data_level = 1
                ready("revisited_level1")
            params.update(final_data_level=layer.data_level,
                          selected_level_sequence=[0, 1, 2, 0] + ([1] if name.endswith("edit") else []))
            assert source_revisions[0]["levels"][0] == source_revisions[-1]["levels"][0]
            assert source_revisions[0]["levels"][2] == source_revisions[-1]["levels"][2]
        elif name == "slice_change":
            viewer.dims.set_point(0, 2)
            ready("selected_slice2")
            data[0][1, 4:8, 9:13] = 255
            viewer.dims.set_point(0, 1)
            layer.refresh()
            source_revisions.append({"stage": "slice1_edit", "levels": [array_record(a) for a in data],
                "slice_records": [array_record(a) for a in data[0]]})
            ready("selected_slice1_edit")
            params["selected_slice_sequence"] = [0, 2, 1]
            params["initial_slice_records"] = [array_record(a) for a in input_arrays(name)[0]]
            assert params["initial_slice_records"][0] == source_revisions[-1]["slice_records"][0]
            assert params["initial_slice_records"][2] == source_revisions[-1]["slice_records"][2]
        elif name == "additive_channels":
            layer.opacity = .5
            viewer.layers.move(2, 0)
            ready("reordered_opacity")
        scene.set_current()
        samples = _context_samples()
        trace.stage = "final_read"
        image = np.array(scene.render(size=SIZE, alpha=True), copy=True)
        node = canvas.layer_to_visual[layer].node
        texture_id = node._texture.id
        params.update(camera_rect=list(canvas.view.camera.rect.pos + canvas.view.camera.rect.size),
            source_revisions=source_revisions, partial_labels_events=labels_events,
            selected_texture_uploads=trace.records(texture_id), stage_commands=trace.stage_commands,
            current_context_samples=samples, sample_query_scope="actual current context; scene.render uses a separate single-sample export FBO",
            layer_types=[type(item).__name__ for item in viewer.layers],
            layer_names=[item.name for item in viewer.layers],
            native_mro=[cls.__name__ for cls in type(canvas.native).__mro__])
        if name.startswith("labels_"):
            uploaded = trace.full_texture(texture_id, DATA_SIZE)
            raw = layer.data
            witness = []
            for value in (-7, 0, HIGH_A, HIGH_B):
                y, x = np.argwhere(raw == value)[0]
                codes = np.unique(uploaded[raw == value])
                assert codes.size == 1, (value, codes)
                witness.append({"source_id": value, "uploaded_code": int(uploaded[y, x]),
                                "source_dtype": raw.dtype.str, "upload_dtype": uploaded.dtype.str})
            assert len({w["uploaded_code"] for w in witness}) == 4
            params["actual_label_remap"] = witness
            if name == "labels_paint_tile":
                assert any(e["offset"] == [4, 8] and e["shape"][:2] == [5, 5] for e in labels_events)
                assert any(e["offset"][:2] == [4, 8] and e["shape"][:2] == [5, 5]
                           for e in params["selected_texture_uploads"] if isinstance(e["offset"], list))
        return image, trace.commands, trace.shaders, params
    finally:
        trace.close()
        viewer.close()
        qapp.processEvents()


def render(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    return _render_vispy(name, backend) if name in VISPY_CASES else _render_host(name)
