# SPDX-License-Identifier: AGPL-3.0-only
"""Version-agnostic successor of tools/fixture_napari_render_plane_scheduled.py (decisions D30 and D31).

Its inputs, criteria, specification and landmarks are the retained module's own objects. render is the retained
render without its napari 0.9.2 pin (the plugin's stays), reading drag positions with world_position (napari
0.10 computes mouse-event positions with ViewerModel.canvas_to_world), and with every mouse move settled by
QtTest.QTest.qWait(10), so napari's 5 ms throttle delivers the final move before the fixture asserts on it, as
the scheduled fixture's moves are (D19; a single processEvents() raced). The napari version is bound by each
reference packet in tests/reference/napari-render-plane-scheduled-opengl-napari-<version>/.
"""
from __future__ import annotations

import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_napari_render_plane_scheduled import (AXES, CAMERA, CASES, HANDLE_SIZE, NORMAL, POSITION, RADIUS,
                                                        SHAPE, SIZE, WIDGET, assert_landmarks, freeze, local_handle,
                                                        phantom, projected_axis_distance, rodrigues, rotation_from_drag,
                                                        specification, world_to_canvas)
    from .napari_world_position import world_position
except ImportError:  # direct oracle capture invocation
    from fixture_napari_render_plane_scheduled import (AXES, CAMERA, CASES, HANDLE_SIZE, NORMAL, POSITION, RADIUS,
                                                       SHAPE, SIZE, WIDGET, assert_landmarks, freeze, local_handle,
                                                       phantom, projected_axis_distance, rodrigues, rotation_from_drag,
                                                       specification, world_to_canvas)
    from napari_world_position import world_position


def render(name):
    assert metadata.version("napari-threedee") == "0.0.29"
    params = specification(name)
    import napari
    from qtpy import QtCore, QtTest, QtWidgets
    viewer = napari.Viewer(ndisplay=2, show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene = canvas._scene_canvas
    qt = QtWidgets.QApplication.instance()
    qt.setQuitOnLastWindowClosed(False)
    commands, shaders, extras, stages = [], {}, {}, []
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
        options = {"experimental_clipping_planes": [params["clip_plane"]]} if params["clip_plane"] else {}
        layer = viewer.add_image(phantom(), name="asymmetric-plane-science", depiction="plane", rendering="mip",
                                 plane={"position": POSITION, "normal": NORMAL, "thickness": 1.},
                                 contrast_limits=(0, 1), colormap="gray", interpolation3d="nearest",
                                 blending="translucent_no_depth", **options)
        viewer.dims.ndisplay = 3
        qt.processEvents()
        # Fix the camera before activating the public plane model, whose normal
        # orientation uses the camera up direction. This declared camera keeps
        # its up dot initial normal safely positive (about .28).
        for key, value in CAMERA.items():
            setattr(viewer.scene.camera, key, value)
        dock, widget = viewer.window.add_plugin_dock_widget("napari-threedee", WIDGET)
        assert type(widget).__name__ == "QtRenderPlaneManipulatorWidget"
        widget.model.set_layers(layer)
        widget.activate_button.click()
        assert widget.model.enabled
        viewer.dims.ndisplay = 2
        viewer.dims.ndisplay = 3
        widget.model.radius, widget.model.handle_size = RADIUS, HANDLE_SIZE
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
        backend = widget.model._backend  # Read installed state; never replace callbacks.
        owned = (backend._mouse_callback, widget.model._mouse_callback)
        assert all(callback in layer.mouse_drag_callbacks for callback in owned)
        np.testing.assert_allclose(widget.model.origin, POSITION, rtol=0, atol=1e-12)
        np.testing.assert_allclose(widget.model.rotation_matrix, np.eye(3), rtol=0, atol=1e-12)
        transform = canvas.view.transform * canvas.view.scene.transform

        def handle_world(kind, axis):
            return np.asarray(widget.model.origin) + np.asarray(widget.model.rotation_matrix) @ local_handle(kind, axis)

        def record(stage):
            selection = backend.manipulator_model.selected_axis_id
            stages.append({"stage": stage, "origin": np.asarray(widget.model.origin).tolist(),
                           "position": list(layer.plane.position), "normal": list(layer.plane.normal),
                           "enabled": bool(widget.model.enabled), "is_dragging": bool(backend.is_dragging),
                           "selected_axis_id": int(selection) if selection is not None else None,
                           "mouse_pan": bool(layer.mouse_pan), "owned_callbacks": [callback in layer.mouse_drag_callbacks for callback in owned]})

        def capture(stage):
            canvas.on_draw(None)
            image = np.array(viewer.screenshot(canvas_only=True, flash=False), copy=True)
            record(stage)
            return image

        record("activated")
        if name in ("plane_translation", "plane_rotation"):
            extras["before"] = capture("before_events")
            kind, axis = ("translator", "z") if name == "plane_translation" else ("rotator", "x")
            world = handle_world(kind, axis)
            screen = world_to_canvas(transform, world)
            if kind == "translator":
                target = world + np.asarray(AXES[axis]["vector"]) * 2
            else:
                target = np.asarray(POSITION) + rodrigues(AXES[axis]["vector"], np.deg2rad(15)) @ local_handle(kind, axis)
            destination = world_to_canvas(transform, target)
            start_xy, end_xy = np.rint(screen).astype(int), np.rint(destination).astype(int)
            delta = destination - screen
            first_xy = np.rint(start_xy + delta / np.linalg.norm(delta) * 2).astype(int)
            assert not np.array_equal(first_xy, start_xy) and not np.array_equal(first_xy, end_xy)
            points = [QtCore.QPoint(*xy) for xy in (start_xy, first_xy, end_xy)]
            params["event_pixels"] = {"press": start_xy.tolist(), "initialize": first_xy.tolist(), "move": end_xy.tolist()}
            initial_pan = layer.mouse_pan
            QtTest.QTest.mousePress(canvas.native, QtCore.Qt.MouseButton.LeftButton, pos=points[0])
            qt.processEvents()
            record("pressed")
            selected = widget.model.selected_translator if kind == "translator" else widget.model.selected_rotator
            assert selected is not None and selected.id == AXES[axis]["id"]
            assert backend.is_dragging and not layer.mouse_pan
            QtTest.QTest.mouseMove(canvas.native, points[1])
            QtTest.QTest.qWait(10)  # Deliver napari's public 5 ms throttled mouse-move timer.
            qt.processEvents()
            record("initialized")
            first = np.asarray(world_position(viewer, canvas, tuple(first_xy)))
            last = np.asarray(world_position(viewer, canvas, tuple(end_xy)))
            near, far = (np.asarray(transform.imap([*first_xy, z, 1])) for z in (-1, 1))
            direction = (far[:3] / far[3] - near[:3] / near[3])[::-1]
            direction /= np.linalg.norm(direction)
            if kind == "translator":
                distance = projected_axis_distance(first, last, direction, axis)
                expected = np.asarray(POSITION) + distance * np.asarray(AXES[axis]["vector"])
                params["analytic_plane_position"] = expected.tolist()
                assert abs(distance) > .1
            else:
                rotation, angle = rotation_from_drag(first, last, direction, np.asarray(POSITION), np.asarray(AXES[axis]["vector"]))
                expected = rotation @ np.asarray(NORMAL)
                params["analytic_plane_normal"] = expected.tolist()
                params["analytic_rotation_radians"] = angle
                assert abs(angle) > .02
            QtTest.QTest.mouseMove(canvas.native, points[2])
            QtTest.QTest.qWait(10)  # Deliver napari's public 5 ms throttled mouse-move timer.
            qt.processEvents()
            record("moved")
            np.testing.assert_allclose(layer.plane.position if kind == "translator" else layer.plane.normal, expected, rtol=0, atol=1e-6)
            QtTest.QTest.mouseRelease(canvas.native, QtCore.Qt.MouseButton.LeftButton, pos=points[2])
            qt.processEvents()
            assert not backend.is_dragging and layer.mouse_pan == initial_pan
            assert widget.model.selected_translator is None and widget.model.selected_rotator is None
        image = capture("final")
        params["landmarks"] = {f"{kind}_{axis}": {"pixel": world_to_canvas(transform, handle_world(kind, axis)).tolist(), "axis": axis}
            for kind, axes in (("translator", ("z",)), ("rotator", ("x", "y", "z"))) for axis in axes}
        if name != "plane_rotation":
            z = float(layer.plane.position[0])
            params["scientific_landmarks"] = {"quarter": {"pixel": world_to_canvas(transform, [z, 5., 6.]).tolist(), "rgba": [0, 0, 0, 255] if name == "plane_clipped" else [64, 64, 64, 255]},
                                              "white": {"pixel": world_to_canvas(transform, [z, 17., 20.]).tolist(), "rgba": [255, 255, 255, 255]}}
        # The public cleanup contract is mandatory in every captured case.
        widget.activate_button.click()
        assert not widget.model.enabled and widget.model._mouse_callback not in layer.mouse_drag_callbacks
        viewer.dims.ndisplay = 2
        qt.processEvents()
        assert not any(callback in layer.mouse_drag_callbacks for callback in owned)
        viewer.layers.remove(layer)
        qt.processEvents()
        assert not any(callback in layer.mouse_drag_callbacks for callback in owned)
        assert backend.vispy_visual.parent is None
        record("retired_layer_removed")
        params["stages"] = stages
        assert_landmarks(name, image, params, extras)
        return image, commands, shaders, params, extras
    finally:
        parser.parse = original
        viewer.close()
        qt.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
