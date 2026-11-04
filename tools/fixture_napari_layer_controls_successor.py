# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari_layer_controls.py (decision D30).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin: the napari version is bound by each reference packet in
tests/reference/napari-layer-controls-opengl-napari-<version>/ instead (tools/napari_host_packets.py).
"""
from __future__ import annotations

import numpy as np

try:
    from .fixture_napari_layer_controls import (BACKGROUND, CAMERA_3D, CASES, CONTROLS, CRITERIA, FIRST, SIZE,
                                                assert_landmarks, freeze, specification, _change, _setup)
except ImportError:  # direct oracle capture invocation
    from fixture_napari_layer_controls import (BACKGROUND, CAMERA_3D, CASES, CONTROLS, CRITERIA, FIRST, SIZE,
                                               assert_landmarks, freeze, specification, _change, _setup)


def render(name):
    """Draw once, change the layer state, and capture the next frame, with a fixed camera and canvas size."""
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
        layers = _setup(name, viewer)
        if name == "volume_translucent_step":
            canvas.layer_to_visual[layers[0]].node.relative_step_size = CONTROLS[name][FIRST]["relative_step_size"]
        canvas.native.setFixedSize(*SIZE)
        scene.app.native.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        camera = viewer.scene.camera
        if name.startswith("volume_"):
            camera.perspective = 0
            camera.angles = tuple(CAMERA_3D["angles"])
        camera.center = tuple(params["camera"]["center"])
        camera.zoom = params["camera"]["zoom"]
        scene.bgcolor = tuple(value / 255 for value in BACKGROUND)
        viewer._layer_slicer.wait_until_idle(timeout=10)
        scene.app.native.processEvents()
        canvas.on_draw(None)
        np.array(scene.render(size=SIZE, alpha=True), copy=True)  # the first frame
        scene.app.native.processEvents()
        canvas.native.setUpdatesEnabled(False)  # from here on, only the change and the capture issue commands
        first_commands = len(commands)
        try:
            _change(name, viewer, layers, canvas)
            viewer._layer_slicer.wait_until_idle(timeout=10)
            scene.app.native.processEvents()
            scene.app.native.processEvents()
            if name == "removal_screenshot":
                image = np.array(viewer.screenshot(canvas_only=True, flash=False), copy=True)
            else:
                canvas.on_draw(None)
                image = np.array(scene.render(size=SIZE, alpha=True), copy=True)
        finally:
            canvas.native.setUpdatesEnabled(True)
        params["finish_commands"] = sum(1 for command in commands[first_commands:] if command[:2] == ["FUNC", "glFinish"])
        params["layer_types"] = [type(item).__name__ for item in viewer.layers]
        params["layer_names"] = [item.name for item in viewer.layers]
        params["native_mro"] = [cls.__name__ for cls in type(canvas.native).__mro__]
        params["ndisplay"] = viewer.dims.ndisplay
        return image, commands, shaders, params
    finally:
        parser.parse = original
        viewer.close()
