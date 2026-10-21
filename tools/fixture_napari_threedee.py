"""Real registered napari-threedee layer manipulator and Qt mouse workflows.

Inputs, projection landmarks, whole-frame exact comparison and event/state
requirements are authored before examining candidate output. Picking belongs
to the installed plugin's CPU ray/sphere callbacks; no GPU ID-picking claim is
made. Importing this module creates no Qt application or renderer.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (256, 192)
DATA_SHAPE = (12, 16, 20)
CASES = ("handles", "selection", "translation", "miss", "retirement")
PLUGIN = "napari-threedee"
WIDGET = "layer manipulator"
ORIGIN = (0., 0., 0.)
RADIUS = 8.
HANDLE_SIZE = 2.
CAMERA = {"center": (4.5, 5.5, 7.5), "zoom": 6., "angles": (20., 35., 0.), "perspective": 0.}
AXES = {
    "x": {"id": 2, "vector": (0., 0., 1.), "color": (1., .75, .52, 1.)},
    "y": {"id": 1, "vector": (0., 1., 0.), "color": (.75, .68, .83, 1.)},
    "z": {"id": 0, "vector": (1., 0., 0.), "color": (.5, .8, .5, 1.)},
}


def phantom():
    """Asymmetric 3D intensities distinguish data axes and actual translation."""
    data = np.zeros(DATA_SHAPE, np.float32)
    data[2:5, 3:7, 4:9] = .25
    data[6:10, 8:13, 11:17] = 1
    data[1:3, 11:14, 16:19] = .5
    return data


def handle_world(axis, origin=ORIGIN):
    # The pinned public radius uses Translator.length=floor(radius/7)+1.
    distance = RADIUS + np.floor(RADIUS / 7) + 1
    return np.asarray(origin, float) + distance * np.asarray(AXES[axis]["vector"])


def world_to_canvas(transform, world):
    """CPU scene transform; never locate landmarks by examining pixels."""
    mapped = np.asarray(transform.map(np.asarray(world)[::-1]), float)
    assert mapped.shape == (4,) and mapped[3] != 0
    return mapped[:2] / mapped[3]


def projected_axis_distance(start, end, view_direction, axis):
    """Canvas-plane drag projected onto the pinned host's unit world axis."""
    vector = np.asarray(AXES[axis]["vector"], float)
    direction = np.asarray(view_direction, float)
    direction /= np.linalg.norm(direction)
    screen_axis = vector - np.dot(vector, direction) * direction
    assert np.dot(vector, screen_axis) > .1, "fixed camera must see this axis"
    return float(np.dot(np.asarray(end) - start, screen_axis))


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    data = phantom()
    return {"case": name, "plugin": PLUGIN, "registered_widget": WIDGET,
            "input": {"shape": list(data.shape), "dtype": data.dtype.str,
                      "sha256": hashlib.sha256(data.tobytes()).hexdigest()},
            "size": list(SIZE), "camera": {k: list(v) if isinstance(v, tuple) else v for k, v in CAMERA.items()},
            "origin": list(ORIGIN), "radius": RADIUS, "handle_size": HANDLE_SIZE,
            "handle_world": {axis: handle_world(axis).tolist() for axis in AXES},
            "event_api": "real QtTest.QTest mousePress/mouseMove/mouseRelease on the installed canvas widget",
            "picking": "installed CPU ray/sphere callbacks, not GPU ID picking",
            "comparison": "whole-frame exact uint8 RGBA; no alignment, edge masks or fitted tolerance"}


def render(name):
    if name not in CASES:
        raise ValueError(name)
    assert metadata.version("napari") == "0.9.2"
    assert metadata.version(PLUGIN) == "0.0.29"
    import napari
    from qtpy import QtCore, QtTest, QtWidgets

    viewer = napari.Viewer(ndisplay=3, show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    qt = QtWidgets.QApplication.instance()
    qt.setQuitOnLastWindowClosed(False)
    commands, shaders, stages, extras = [], {}, [], {}
    parser = scene.context.shared.parser
    original_parse = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA" and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
        return original_parse(batch)

    parser.parse = log
    try:
        params = specification(name)
        layer = viewer.add_image(phantom(), name="asymmetric-science", contrast_limits=(0, 1),
                                 colormap="gray", rendering="mip", interpolation3d="nearest", blending="opaque")
        dock, widget = viewer.window.add_plugin_dock_widget(PLUGIN, WIDGET)
        assert type(widget).__name__ == "QtLayerManipulatorWidget"
        assert type(widget).__module__.startswith("napari_threedee.")
        widget.model.set_layers(layer)
        widget.activate_button.click()
        assert widget.model.enabled and widget.activate_button.isChecked()
        # Public ndisplay transitions also establish the plugin's documented
        # foreground order, rather than changing its private visual state.
        viewer.dims.ndisplay = 2
        viewer.dims.ndisplay = 3
        assert widget.model.enabled
        widget.model.radius = RADIUS
        widget.model.handle_size = HANDLE_SIZE
        widget.model.origin = np.asarray(ORIGIN)
        canvas.native.setFixedSize(*SIZE)
        qt.processEvents()
        canvas.size = SIZE[::-1]
        scene.central_widget.size = SIZE
        scene.bgcolor = (0, 0, 0, 1)
        for key, value in CAMERA.items():
            setattr(viewer.scene.camera, key, value)
        viewer._layer_slicer.wait_until_idle(timeout=10)
        qt.processEvents()
        qt.processEvents()
        canvas.on_draw(None)
        transform = canvas.view.transform * canvas.view.scene.transform
        projected = {axis: world_to_canvas(transform, handle_world(axis)) for axis in AXES}
        points = {axis: QtCore.QPoint(*np.rint(value).astype(int)) for axis, value in projected.items()}
        for axis, point in points.items():
            assert 3 <= point.x() < SIZE[0] - 3 and 3 <= point.y() < SIZE[1] - 3, (axis, projected)
        params["initial_projection"] = {axis: value.tolist() for axis, value in projected.items()}
        backend = widget.model._backend  # Read-only observations of installed callback ownership.
        owned = (backend._mouse_callback, widget.model._mouse_callback)
        assert all(callback in layer.mouse_drag_callbacks for callback in owned)

        def record(stage):
            selected = backend.manipulator_model.selected_axis_id
            stages.append({"stage": stage, "origin": np.asarray(widget.model.origin).tolist(),
                           "translate": np.asarray(layer.translate).tolist(), "enabled": bool(widget.model.enabled),
                           "selected_axis_id": None if selected is None else int(selected),
                           "is_dragging": bool(backend.is_dragging), "mouse_pan": bool(layer.mouse_pan),
                           "owned_callbacks": [callback in layer.mouse_drag_callbacks for callback in owned],
                           "colors": {str(int(axis)): color.tolist() for axis, color in zip(
                               backend.vispy_visual_data.translator_handle_data.axis_identifiers,
                               backend.vispy_visual_data.translator_handle_colors)}})

        def capture(stage):
            canvas.on_draw(None)
            image = np.array(viewer.screenshot(canvas_only=True, flash=False), copy=True)
            assert image.shape == (SIZE[1], SIZE[0], 4), image.shape
            record(stage)
            return image

        record("activated")
        if name in ("selection", "translation", "miss"):
            extras["before"] = capture("before_events")
        initial_pan = layer.mouse_pan
        if name in ("selection", "translation"):
            start = points["x"]
            params["press_pixel"] = [start.x(), start.y()]
            QtTest.QTest.mousePress(canvas.native, QtCore.Qt.MouseButton.LeftButton, pos=start)
            qt.processEvents()
            record("pressed")
            assert backend.is_dragging and not layer.mouse_pan
            assert widget.model.selected_translator.id == AXES["x"]["id"]
            if name == "selection":
                image = capture("selected")
            else:
                desired_end = world_to_canvas(transform, handle_world("x") + (0., 0., 2.))
                end = QtCore.QPoint(*np.rint(desired_end).astype(int))
                params["drag_pixel"] = [end.x(), end.y()]
                # First move initializes the installed generator's drag plane;
                # the second exercises its actual translation update.
                screen_axis = desired_end - projected["x"]
                initialize = np.rint(np.array([start.x(), start.y()]) + screen_axis / np.linalg.norm(screen_axis) * 2).astype(int)
                first_move = QtCore.QPoint(*initialize)
                params["initialization_pixel"] = initialize.tolist()
                assert first_move != start and first_move != end
                QtTest.QTest.mouseMove(canvas.native, first_move)
                qt.processEvents()
                record("drag_initialized")
                np.testing.assert_array_equal(widget.model.origin, ORIGIN)
                before = canvas._map_canvas2world((first_move.x(), first_move.y()), canvas.view)
                after = canvas._map_canvas2world((end.x(), end.y()), canvas.view)
                near = np.asarray(transform.imap([start.x(), start.y(), -1, 1]), float)
                far = np.asarray(transform.imap([start.x(), start.y(), 1, 1]), float)
                direction = (far[:3] / far[3] - near[:3] / near[3])[::-1]
                distance = projected_axis_distance(np.asarray(before), np.asarray(after), direction, "x")
                expected = np.asarray(ORIGIN) + distance * np.asarray(AXES["x"]["vector"])
                params["analytic_drag_translation"] = expected.tolist()
                assert distance > .25, distance
                QtTest.QTest.mouseMove(canvas.native, end)
                qt.processEvents()
                record("moved")
                np.testing.assert_allclose(widget.model.origin, expected, rtol=0, atol=1e-6)
                np.testing.assert_allclose(layer.translate, expected, rtol=0, atol=1e-6)
                QtTest.QTest.mouseRelease(canvas.native, QtCore.Qt.MouseButton.LeftButton, pos=end)
                qt.processEvents()
                assert not backend.is_dragging and widget.model.selected_translator is None
                assert layer.mouse_pan == initial_pan
                image = capture("translated")
        elif name == "miss":
            miss = QtCore.QPoint(3, 3)
            params["press_pixel"] = [miss.x(), miss.y()]
            QtTest.QTest.mouseClick(canvas.native, QtCore.Qt.MouseButton.LeftButton, pos=miss)
            qt.processEvents()
            assert not backend.is_dragging and widget.model.selected_translator is None
            np.testing.assert_array_equal(widget.model.origin, ORIGIN)
            np.testing.assert_array_equal(layer.translate, ORIGIN)
            assert layer.mouse_pan == initial_pan
            image = capture("missed")
            np.testing.assert_array_equal(image, extras["before"])
        elif name == "retirement":
            widget.activate_button.click()
            assert not widget.model.enabled
            assert widget.model._mouse_callback not in layer.mouse_drag_callbacks
            record("deactivated")
            # The pinned backend retires its own mouse callback on ndisplay=2.
            # We observe that separately rather than claiming the button alone
            # removes both callback owners.
            viewer.dims.ndisplay = 2
            qt.processEvents()
            assert not any(callback in layer.mouse_drag_callbacks for callback in owned)
            record("two_dimensional")
            image = capture("retired")
            viewer.layers.remove(layer)
            qt.processEvents()
            assert not any(callback in layer.mouse_drag_callbacks for callback in owned)
            assert backend.vispy_visual.parent is None and not widget.model.enabled
            record("layer_removed")
        else:
            image = capture("handles")
        params["stages"] = stages
        params["final_projection"] = {
            axis: world_to_canvas(transform, handle_world(axis, widget.model.origin)).tolist() for axis in AXES}
        params["screenshot_api"] = "napari.Viewer.screenshot(canvas_only=True, flash=False)"
        params["native_mro"] = [cls.__name__ for cls in type(canvas.native).__mro__]
        params["widget_origin"] = type(widget).__module__
        if name == "selection":
            QtTest.QTest.mouseRelease(canvas.native, QtCore.Qt.MouseButton.LeftButton, pos=points["x"])
            qt.processEvents()
            assert not backend.is_dragging and widget.model.selected_translator is None
            assert layer.mouse_pan == initial_pan
            record("released_after_capture")
        assert_landmarks(name, image, params, extras)
        return image, commands, shaders, params, extras
    finally:
        parser.parse = original_parse
        viewer.close()
        qt.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def assert_landmarks(name, image, params, extras):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert image[1, 1].tolist() == [0, 0, 0, 255], (name, image[1, 1])
    assert np.any(image[..., :3] > 0), "blank output cannot admit this plugin"
    assert params["picking"] == "installed CPU ray/sphere callbacks, not GPU ID picking"
    if name == "retirement":
        assert params["stages"][-1]["stage"] == "layer_removed"
        assert params["stages"][-1]["owned_callbacks"] == [False, False]
        return
    for axis, spec in AXES.items():
        x, y = np.rint(params["final_projection"][axis]).astype(int)
        face = image[y, x, :3].astype(int)
        assert face.min() > 0 and image[y, x, 3] == 255, (name, axis, face)
        # Spherical shading scales the prescribed face color uniformly. These
        # strict component orderings follow the pinned analytic axis palette.
        if axis == "x":
            assert face[0] > face[1] > face[2], (name, axis, face)
        elif axis == "y":
            assert face[2] > face[0] > face[1], (name, axis, face)
        else:
            assert face[1] > face[0] and face[0] == face[2], (name, axis, face)
    if name in ("selection", "translation"):
        assert not np.array_equal(image, extras["before"]), (name, "real event must change pixels")
    if name == "selection":
        selected = next(stage for stage in params["stages"] if stage["stage"] == "selected")
        assert selected["selected_axis_id"] == 2 and selected["is_dragging"]
        for axis, spec in AXES.items():
            factor = 1 if axis == "x" else .5
            np.testing.assert_array_equal(selected["colors"][str(spec["id"])], np.asarray(spec["color"]) * factor)
    if name == "translation":
        moved = next(stage for stage in params["stages"] if stage["stage"] == "translated")
        np.testing.assert_allclose(moved["translate"], params["analytic_drag_translation"], rtol=0, atol=1e-6)
        assert moved["selected_axis_id"] is None and not moved["is_dragging"]
    if name == "miss":
        np.testing.assert_array_equal(image, extras["before"])
