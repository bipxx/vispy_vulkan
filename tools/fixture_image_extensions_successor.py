# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_image_extensions.py (decision D30).

Its inputs, criteria and landmarks are the retained module's own objects. _render_host is the retained one without
its napari 0.9.2 pin, render dispatches to it, and case_contract names the host workflow without a napari version:
each reference packet in tests/reference/image-extensions-opengl-napari-<version>/ records the version instead
(tools/napari_host_packets.py).
"""
from __future__ import annotations

import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_image_extensions import (BACKGROUND, CASES, COMPARISON, DATA_SIZE, HIGH_A, HIGH_B, SIZE,
                                           VISPY_CASES, array_record, assert_landmarks, final_arrays, input_arrays,
                                           paint_mask, _Trace, _context_samples, _render_vispy)
    from .fixture_image_extensions import case_contract as retained_case_contract
except ImportError:  # direct oracle capture invocation
    from fixture_image_extensions import (BACKGROUND, CASES, COMPARISON, DATA_SIZE, HIGH_A, HIGH_B, SIZE,
                                          VISPY_CASES, array_record, assert_landmarks, final_arrays, input_arrays,
                                          paint_mask, _Trace, _context_samples, _render_vispy)
    from fixture_image_extensions import case_contract as retained_case_contract


def case_contract(name):
    """The retained contract, with the host workflow named without its napari version."""
    contract = retained_case_contract(name)
    if name not in VISPY_CASES:
        assert contract["workflow"] == "public napari0.9.2", contract["workflow"]
        contract["workflow"] = "public napari"
    return contract


def _render_host(name):
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
            selected_texture_descriptor_from_gloo={"shape": list(node._texture.shape),
                "format": node._texture.format, "internalformat": node._texture.internalformat,
                "interpolation": node._texture.interpolation},
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
