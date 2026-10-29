# SPDX-License-Identifier: AGPL-3.0-only
"""napari layer-control changes after a first frame (W5: B03, H01, V04).

Every case draws once, changes layer state through napari's public API, and captures the next frame:
- B03: an opacity change; a first-layer transition (hiding the bottom layer makes an additive layer the first
  visible one, which napari blends differently); a multichannel additive stack reordered.
- H01: a layer removed (napari collects garbage and requests a finish), then napari's public screenshot; the
  harness itself never asks for a finish.
The glFinish commands of the change and the capture are counted with Qt paint events suppressed (the Dawn Qt
backend's readback presentation finishes once per paint by design; its cost is W8's measurement) and recorded as
evidence. They are not compared: OpenGL's QOpenGLWidget.grabFramebuffer synchronizes inside Qt, while the Dawn
readback logs the same synchronization as a glFinish.
- V04: volume controls changed after a first frame: the iso threshold, the attenuated-MIP attenuation, and the
  translucent opacity with a smaller ray step.
The comparison per case is fixed here, before any capture: these frames draw no antialiased lines, so every case is
exact. Landmarks are semantic and exact.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:  # direct oracle capture invocation
    from fixture_gloo import freeze

SIZE = (160, 120)
CASES = ("opacity_mutation", "first_layer_transition", "additive_reorder", "removal_screenshot", "volume_iso",
         "volume_attenuated_mip", "volume_translucent_step")
CRITERIA = {name: "exact" for name in CASES}
BACKGROUND = (0, 0, 0, 255)
ROWS, COLUMNS = 30, 40
_Y, _X = np.arange(ROWS)[:, None], np.arange(COLUMNS)[None, :]
IMAGE_A = ((_Y * 7 + _X * 5) % 256).astype(np.uint8)
IMAGE_B = (np.hypot(_Y - 15, _X - 20) * 12 % 256).astype(np.uint8)
CHANNELS = np.stack([IMAGE_A, IMAGE_B, ((_X * 11 + _Y * 3) % 256).astype(np.uint8)])
LABELS = ((_Y // 10) * 4 + _X // 10 + 1).astype(np.uint8)  # twelve 10x10 blocks, no background
_AXIS = np.linspace(-1, 1, 24, dtype=np.float32)
_VZ, _VY, _VX = np.meshgrid(_AXIS, _AXIS, _AXIS, indexing="ij")
VOLUME = np.clip(1 - np.sqrt((_VX / .9) ** 2 + (_VY / .7) ** 2 + (_VZ / .5) ** 2), 0, 1).astype(np.float32)
CAMERA_2D = {"center": [0, 14.5, 19.5], "zoom": 4}  # each image pixel covers 4x4 canvas pixels
CAMERA_3D = {"center": [11.5, 11.5, 11.5], "zoom": 5, "angles": [-25, 35, 130]}
TRANSLUCENT_RAMP = [[0, 0, 0, 0], [1, .6, .1, 1]]  # opaque colormaps would stop every ray at the zero boundary
TRANSLUCENT_LIMITS = (0, .4)  # the ramp saturates inside the volume, so the composite is not near black
FIRST, CHANGED = "first", "changed"
CONTROLS = {
    "opacity_mutation": {FIRST: {"opacity": 1.0}, CHANGED: {"opacity": .35}},
    "first_layer_transition": {FIRST: {"bottom_visible": True}, CHANGED: {"bottom_visible": False}},
    "additive_reorder": {FIRST: {"order": ["red", "green", "blue"]}, CHANGED: {"order": ["blue", "red", "green"]}},
    "removal_screenshot": {FIRST: {"layers": ["image", "labels"]}, CHANGED: {"layers": ["image"]}},
    "volume_iso": {FIRST: {"iso_threshold": .3}, CHANGED: {"iso_threshold": .5}},
    "volume_attenuated_mip": {FIRST: {"attenuation": .05}, CHANGED: {"attenuation": .5}},
    "volume_translucent_step": {FIRST: {"opacity": 1.0, "relative_step_size": .8},
                                CHANGED: {"opacity": .6, "relative_step_size": .4}},
}


def inputs(name):
    if name.startswith("volume_"):
        return [VOLUME]
    return {"opacity_mutation": [IMAGE_A], "first_layer_transition": [IMAGE_A, IMAGE_B], "additive_reorder": [CHANNELS],
            "removal_screenshot": [IMAGE_A, LABELS]}[name]


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    digest = hashlib.sha256()
    for array in inputs(name):
        digest.update(np.ascontiguousarray(array).tobytes())
    return {"case": name, "size": list(SIZE), "camera": CAMERA_3D if name.startswith("volume_") else CAMERA_2D,
            "controls": CONTROLS[name], "background": list(BACKGROUND), "criterion": CRITERIA[name],
            "inputs_sha256": digest.hexdigest()}


def _setup(name, viewer):
    first = CONTROLS[name][FIRST]
    if name == "opacity_mutation":
        return [viewer.add_image(IMAGE_A, colormap="viridis", contrast_limits=(0, 255), interpolation2d="nearest",
                                 opacity=first["opacity"], name="image")]
    if name == "first_layer_transition":
        return [viewer.add_image(IMAGE_A, colormap="gray", contrast_limits=(0, 255), interpolation2d="nearest",
                                 blending="translucent", name="bottom"),
                viewer.add_image(IMAGE_B, colormap="magenta", contrast_limits=(0, 255), interpolation2d="nearest",
                                 blending="additive", opacity=.8, name="top")]
    if name == "additive_reorder":
        return viewer.add_image(CHANNELS, channel_axis=0, name=first["order"], colormap=first["order"],
                                blending="additive", opacity=[1, .25, .75], contrast_limits=[(0, 255)] * 3,
                                interpolation2d="nearest")
    if name == "removal_screenshot":
        return [viewer.add_image(IMAGE_A, colormap="viridis", contrast_limits=(0, 255), interpolation2d="nearest",
                                 name="image"),
                viewer.add_labels(LABELS, opacity=.5, name="labels")]
    rendering = {"volume_iso": "iso", "volume_attenuated_mip": "attenuated_mip",
                 "volume_translucent_step": "translucent"}[name]
    colormap, limits = "magma", (0, 1)
    if name == "volume_translucent_step":
        from napari.utils.colormaps import Colormap

        colormap, limits = Colormap(TRANSLUCENT_RAMP, name="amber_ramp"), TRANSLUCENT_LIMITS
    layer = viewer.add_image(VOLUME, rendering=rendering, colormap=colormap, contrast_limits=limits, name="volume",
                             **{key: value for key, value in first.items() if key != "relative_step_size"})
    viewer.dims.ndisplay = 3
    return [layer]


def _change(name, viewer, layers, canvas):
    changed = CONTROLS[name][CHANGED]
    if name == "first_layer_transition":
        layers[0].visible = changed["bottom_visible"]
    elif name == "additive_reorder":
        viewer.layers.move(2, 0)
        assert [layer.name for layer in viewer.layers] == changed["order"]
    elif name == "removal_screenshot":
        viewer.layers.remove("labels")
        assert [layer.name for layer in viewer.layers] == changed["layers"]
    else:
        for key, value in changed.items():
            if key == "relative_step_size":
                canvas.layer_to_visual[layers[0]].node.relative_step_size = value
            else:
                setattr(layers[0], key, value)


def render(name):
    """Draw once, change the layer state, and capture the next frame, with a fixed camera and canvas size."""
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


def _near(image, rgb, tolerance=2):
    return int(np.all(np.abs(image[..., :3].astype(np.int16) - np.asarray(rgb)) <= tolerance, axis=2).sum())


def assert_landmarks(name, image):
    """Semantic, exact checks of each changed state."""
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8, (name, image.shape)
    colored = np.any(image[..., :3] != BACKGROUND[:3], axis=2)
    if name.startswith("volume_"):
        assert image[0, 0].tolist() == list(BACKGROUND) and 800 < colored.sum() < 0.9 * colored.size, name
        return
    assert colored.sum() > 0.8 * colored.size, name  # the image fills the canvas
    if name == "opacity_mutation":
        # viridis(1) blended at 0.35 over black: no pixel keeps the full-opacity yellow.
        assert _near(image, (253, 231, 37)) == 0 and image[..., :3].max() <= 0.35 * 255 + 2, name
    elif name == "first_layer_transition":
        # Only the magenta layer remains visible: no green channel anywhere.
        assert image[..., 1].max() == 0 and image[..., 0].max() > 150, name
    elif name == "additive_reorder":
        # The additive stack keeps all three channels, at opacities 1, 0.25 and 0.75.
        assert image[..., 0].max() > 150 and image[..., 1].max() > 40 and image[..., 2].max() > 150, name
    else:
        # The removed labels leave the plain viridis image: both ends of the colormap appear.
        assert _near(image, (253, 231, 37)) > 0 and _near(image, (68, 1, 84)) > 0, name
