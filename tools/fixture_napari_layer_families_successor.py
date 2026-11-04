# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari_layer_families.py (decision D30).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin: the napari version is bound by each reference packet in
tests/reference/napari-layer-families-opengl-napari-<version>/ instead (tools/napari_host_packets.py).
"""
from __future__ import annotations

import numpy as np

try:
    from .fixture_napari_layer_families import (BACKGROUND, CAMERAS, CASES, CRITERIA, EXPORT_SIZE, HISTOGRAM_IMAGE,
                                                HISTOGRAM_SIZE, IMAGE, SIZE, SURFACE_FACES, SURFACE_VALUES,
                                                SURFACE_VERTICES, assert_landmarks, freeze, inputs, specification)
except ImportError:  # direct oracle capture invocation
    from fixture_napari_layer_families import (BACKGROUND, CAMERAS, CASES, CRITERIA, EXPORT_SIZE, HISTOGRAM_IMAGE,
                                               HISTOGRAM_SIZE, IMAGE, SIZE, SURFACE_FACES, SURFACE_VALUES,
                                               SURFACE_VERTICES, assert_landmarks, freeze, inputs, specification)


def render(name):
    """Capture the case once after all layer state is set, with a fixed camera and canvas size."""
    params = specification(name)
    import napari

    viewer = napari.Viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    commands, shaders, patched = [], {}, []

    def watch(parser):
        original = parser.parse

        def log(batch):
            for command in batch:
                commands.append(freeze(command))
                if command[0] == "DATA" and isinstance(command[3], str):
                    shaders[str(command[1])] = command[3]
            return original(batch)

        parser.parse = log
        patched.append((parser, original))

    watch(scene.context.shared.parser)
    widget = None
    try:
        if name in ("labels_r8", "labels_r16"):
            viewer.add_labels(inputs(name)[0], name="labels")
        elif name in ("surface_shaded", "surface_wireframe"):
            layer = viewer.add_surface((SURFACE_VERTICES, SURFACE_FACES, SURFACE_VALUES), colormap="viridis",
                                       contrast_limits=(-3, 3), name="surface",
                                       shading="smooth" if name == "surface_shaded" else "none")
            if name == "surface_wireframe":
                layer.wireframe.visible = True
                layer.wireframe.color = "white"
                layer.wireframe.width = 1
            viewer.dims.ndisplay = 3
        elif name == "histogram":
            layer = viewer.add_image(HISTOGRAM_IMAGE, colormap="viridis", contrast_limits=(0, 255), name="image")
        else:
            layer = viewer.add_image(IMAGE, scale=(0.5, 0.5), colormap="viridis", contrast_limits=(0, 255),
                                     interpolation2d="nearest", name="image")
            if name == "scale_bar_axes":
                viewer.canvas.overlays.scale_bar.visible = True
                viewer.scene.overlays.axes.visible = True
            elif name == "colorbar":
                layer.colorbar.visible = True
        canvas.native.setFixedSize(*SIZE)
        scene.app.native.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        if CAMERAS[name] is not None:
            camera = viewer.scene.camera
            if "angles" in CAMERAS[name]:
                camera.perspective = 0
                camera.angles = tuple(CAMERAS[name]["angles"])
            camera.center = tuple(CAMERAS[name]["center"])
            camera.zoom = CAMERAS[name]["zoom"]
        scene.bgcolor = tuple(value / 255 for value in BACKGROUND)
        viewer._layer_slicer.wait_until_idle(timeout=10)
        scene.app.native.processEvents()
        scene.app.native.processEvents()
        canvas.on_draw(None)
        if name == "histogram":
            from napari._qt.widgets.qt_histogram import QtHistogramWidget

            for _ in layer.histogram.compute():  # synchronous: the widget then draws without a worker thread
                pass
            widget = QtHistogramWidget(layer)
            watch(widget.canvas.context.shared.parser)
            widget.canvas.bgcolor = tuple(value / 255 for value in BACKGROUND)
            layer.histogram.enabled = True
            widget.show()
            scene.app.native.processEvents()
            scene.app.native.processEvents()
            assert not layer.histogram._dirty and widget._compute_worker is None
            image = np.array(widget.canvas.render(size=HISTOGRAM_SIZE, alpha=True), copy=True)
        elif name == "sized_export":
            # napari resizes the canvas for the export, so release the fixed size first.
            canvas.native.setMinimumSize(1, 1)
            canvas.native.setMaximumSize(16777215, 16777215)
            image = np.array(viewer.screenshot(size=EXPORT_SIZE, canvas_only=True, flash=False), copy=True)
        else:
            image = np.array(scene.render(size=SIZE, alpha=True), copy=True)
        params["layer_types"] = [type(item).__name__ for item in viewer.layers]
        params["native_mro"] = [cls.__name__ for cls in type(canvas.native).__mro__]
        params["ndisplay"] = viewer.dims.ndisplay
        return image, commands, shaders, params
    finally:
        for parser, original in patched:
            parser.parse = original
        if widget is not None:
            widget.cleanup()
            widget.close()
        viewer.close()
