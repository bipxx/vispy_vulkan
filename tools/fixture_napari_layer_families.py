# SPDX-License-Identifier: AGPL-3.0-only
"""napari layer families without an independent OpenGL reference yet (W4).

Default cyclic labels through napari's r8 (uint8) and r16 (uint16) label textures; a Surface layer with smooth
shading and with its wireframe; the scale bar and axes overlays; a layer colorbar; the layer-controls histogram
canvas; and a sized screenshot export. Each is captured once after all state is set, with a fixed camera and canvas
size. The comparison per case is fixed here, before any capture: frames without antialiased lines are exact; the
overlay and histogram frames draw napari's antialiased (smooth) lines and use the smooth-line criterion
(tools/smooth_line_parity.py). Landmarks are semantic and exact.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:  # direct oracle capture invocation
    from fixture_gloo import freeze

SIZE = (256, 192)
EXPORT_SIZE = (96, 160)  # rows, columns: viewer.screenshot(size=...)
HISTOGRAM_SIZE = (300, 150)  # napari's default histogram canvas
CASES = ("labels_r8", "labels_r16", "surface_shaded", "surface_wireframe", "scale_bar_axes", "colorbar",
         "histogram", "sized_export")
CRITERIA = {"labels_r8": "exact", "labels_r16": "exact", "surface_shaded": "exact", "surface_wireframe": "exact",
            "scale_bar_axes": "smooth_line", "colorbar": "smooth_line", "histogram": "smooth_line",
            "sized_export": "exact"}
BACKGROUND = (0, 0, 0, 255)
ROWS, COLUMNS, BLOCK = 48, 64, 8
_BLOCKS = (np.arange(ROWS)[:, None] // BLOCK) * (COLUMNS // BLOCK) + np.arange(COLUMNS)[None, :] // BLOCK
LABELS_R8 = _BLOCKS.astype(np.uint8)  # 48 labels in 8x8 blocks; label 0 (top left) is the transparent background
# napari's default cyclic colormap repeats every 49 labels; a step of 1601 (33 mod 49) gives 40 distinct colours.
R16_IDS = np.array([0, 255, 256, 257, 4095, 4096, 65534, 65535, *(300 + 1601 * k for k in range(40))], np.uint16)
LABELS_R16 = R16_IDS[_BLOCKS]
IMAGE = ((np.arange(ROWS)[:, None] * 5 + np.arange(COLUMNS)[None, :] * 3) % 256).astype(np.uint8)
HISTOGRAM_IMAGE = np.clip(np.hypot(np.arange(ROWS)[:, None] - 20, np.arange(COLUMNS)[None, :] - 40) * 6,
                          0, 255).astype(np.uint8)
_GY, _GX = np.meshgrid(np.linspace(0, 12, 7), np.linspace(0, 16, 9), indexing="ij")
_GZ = 3 * np.sin(_GX / 3) * np.cos(_GY / 3)
SURFACE_VERTICES = np.stack([_GZ.ravel(), _GY.ravel(), _GX.ravel()], axis=1).astype(np.float32)  # napari (z, y, x)
SURFACE_FACES = np.array([face for row in range(6) for column in range(8) for i in [row * 9 + column]
                          for face in ([i, i + 1, i + 9], [i + 1, i + 10, i + 9])], np.int32)
SURFACE_VALUES = _GZ.ravel().astype(np.float32)
CAMERAS = {
    "labels_r8": {"center": [0, 23.5, 31.5], "zoom": 4},  # each label pixel covers 4x4 canvas pixels
    "labels_r16": {"center": [0, 23.5, 31.5], "zoom": 4},
    "surface_shaded": {"center": [0, 6, 8], "zoom": 12, "angles": [-20, 30, 125]},
    "surface_wireframe": {"center": [0, 6, 8], "zoom": 12, "angles": [-20, 30, 125]},
    "scale_bar_axes": {"center": [0, 8.75, 12.75], "zoom": 8},  # scale 0.5: each image pixel covers 4x4; the
    "colorbar": {"center": [0, 11.75, 15.75], "zoom": 8},        # axes origin sits 26 canvas pixels in
    "histogram": None,  # the histogram canvas's own camera
    "sized_export": {"center": [0, 11.75, 15.75], "zoom": 8},
}


def inputs(name):
    if name in ("labels_r8", "labels_r16"):
        return [LABELS_R8 if name == "labels_r8" else LABELS_R16]
    if name in ("surface_shaded", "surface_wireframe"):
        return [SURFACE_VERTICES, SURFACE_FACES, SURFACE_VALUES]
    return [HISTOGRAM_IMAGE if name == "histogram" else IMAGE]


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    digest = hashlib.sha256()
    for array in inputs(name):
        digest.update(np.ascontiguousarray(array).tobytes())
    size = {"histogram": list(HISTOGRAM_SIZE), "sized_export": [EXPORT_SIZE[1], EXPORT_SIZE[0]]}.get(name, list(SIZE))
    return {"case": name, "size": size, "camera": CAMERAS[name], "background": list(BACKGROUND),
            "criterion": CRITERIA[name], "inputs_sha256": digest.hexdigest()}


def render(name):
    """Capture the case once after all layer state is set, with a fixed camera and canvas size."""
    params = specification(name)
    assert metadata.version("napari") == "0.9.2", "required pinned napari dependency"
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


def assert_landmarks(name, image):
    """Semantic, exact checks that do not depend on antialiased edges."""
    width, height = specification(name)["size"]
    assert image.shape == (height, width, 4) and image.dtype == np.uint8, (name, image.shape)
    colors = {tuple(pixel) for pixel in image.reshape(-1, 4)[::7].tolist()}
    if name in ("labels_r8", "labels_r16"):
        # Label 0 is transparent: its 8x8 block (32x32 canvas pixels, top left) shows the background.
        assert np.all(image[:32, :32] == BACKGROUND), name
        assert len(colors) >= 30, (name, len(colors))
    elif name in ("surface_shaded", "surface_wireframe"):
        assert image[0, 0].tolist() == list(BACKGROUND) and image[-1, -1].tolist() == list(BACKGROUND), name
        assert np.any(image[..., :3] != BACKGROUND[:3], axis=2).sum() > 3000, name
        if name == "surface_wireframe":
            assert np.all(image[..., :3] >= 240, axis=2).sum() >= 50, name
        else:
            assert len(colors) >= 50, (name, len(colors))
    elif name == "scale_bar_axes":
        # The axes origin is 26 canvas pixels in, so the corner shows the background. napari draws the x and y axes
        # in cyan and magenta (lines and arrowheads), and the scale bar and its label in white.
        assert image[0, 0].tolist() == list(BACKGROUND), name
        assert _near(image, (0, 255, 255)) >= 50 and _near(image, (255, 0, 255)) >= 50, name
        assert _near(image, (255, 255, 255)) >= 100, name
    elif name in ("colorbar", "sized_export"):
        # Both ends of viridis appear in the image (and the colorbar); the colorbar's tick labels are white.
        assert _near(image, (253, 231, 37)) >= 100 and _near(image, (68, 1, 84)) >= 100, name
        if name == "colorbar":
            assert _near(image, (255, 255, 255)) >= 10, name
    else:
        # Bars in viridis(0.75) over the background; the histogram's lines are antialiased, so they are not checked.
        assert _near(image, (122, 209, 81)) >= 4000 and _near(image, BACKGROUND[:3], 0) >= 20000, name


def _near(image, rgb, tolerance=2):
    return int(np.all(np.abs(image[..., :3].astype(np.int16) - np.asarray(rgb)) <= tolerance, axis=2).sum())
