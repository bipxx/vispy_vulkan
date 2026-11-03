# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari_threedee_initialized.py (decisions D30 and D31).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin (the plugin's stays), reading drag positions with world_position (napari
0.10 computes mouse-event positions with ViewerModel.canvas_to_world), and with every mouse move settled by
QtTest.QTest.qWait(10), so napari's 5 ms throttle delivers the final move before the fixture asserts on it, as
the scheduled fixture's moves are (D19; a single processEvents() raced). The napari version is bound by each
reference packet in tests/reference/napari-threedee-initialized-opengl-napari-<version>/.
"""
from __future__ import annotations

import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_napari_threedee_initialized import (AXES, CAMERA, CASES, DATA_SHAPE, HANDLE_SIZE, ORIGIN, PLUGIN,
                                                      RADIUS, SIZE, WIDGET, assert_landmarks, freeze, handle_world,
                                                      phantom, projected_axis_distance, specification, world_to_canvas)
    from .napari_world_position import world_position
except ImportError:  # direct oracle capture invocation
    from fixture_napari_threedee_initialized import (AXES, CAMERA, CASES, DATA_SHAPE, HANDLE_SIZE, ORIGIN, PLUGIN,
                                                     RADIUS, SIZE, WIDGET, assert_landmarks, freeze, handle_world,
                                                     phantom, projected_axis_distance, specification, world_to_canvas)
    from napari_world_position import world_position


def render(name):
    if name not in CASES:
        raise ValueError(name)
    assert metadata.version(PLUGIN) == "0.0.29"
    import napari
    from qtpy import QtCore, QtTest, QtWidgets

    viewer = napari.Viewer(ndisplay=2, show=True)
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
        # Initialize both public camera modes before the plugin adds its
        # intentionally empty rotator markers to the scene bounds graph.
        viewer.dims.ndisplay = 3
        qt.processEvents()
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
                QtTest.QTest.qWait(10)  # Deliver napari's public 5 ms throttled mouse-move timer.
                qt.processEvents()
                record("drag_initialized")
                np.testing.assert_array_equal(widget.model.origin, ORIGIN)
                before = world_position(viewer, canvas, (first_move.x(), first_move.y()))
                after = world_position(viewer, canvas, (end.x(), end.y()))
                near = np.asarray(transform.imap([start.x(), start.y(), -1, 1]), float)
                far = np.asarray(transform.imap([start.x(), start.y(), 1, 1]), float)
                direction = (far[:3] / far[3] - near[:3] / near[3])[::-1]
                distance = projected_axis_distance(np.asarray(before), np.asarray(after), direction, "x")
                expected = np.asarray(ORIGIN) + distance * np.asarray(AXES["x"]["vector"])
                params["analytic_drag_translation"] = expected.tolist()
                assert distance > .25, distance
                QtTest.QTest.mouseMove(canvas.native, end)
                QtTest.QTest.qWait(10)  # Deliver napari's public 5 ms throttled mouse-move timer.
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
