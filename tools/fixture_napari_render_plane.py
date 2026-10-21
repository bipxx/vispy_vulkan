"""Registered render-plane manipulator with analytic public Qt workflows."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import numpy as np

try:
    from .fixture_gloo import freeze
    from .fixture_napari_threedee_overlay import AXES, world_to_canvas, projected_axis_distance
except ImportError:
    from fixture_gloo import freeze
    from fixture_napari_threedee_overlay import AXES, world_to_canvas, projected_axis_distance

SIZE = (256, 192)
SHAPE = (20, 24, 28)
POSITION = (8., 12., 14.)
NORMAL = (1., 0., 0.)
RADIUS = 4.
HANDLE_SIZE = 2.
WIDGET = "render plane manipulator"
CASES = ("plane_handles", "plane_translation", "plane_rotation", "plane_clipped")
CAMERA = {"center": POSITION, "zoom": 5., "angles": (20., 35., -20.), "perspective": 0.}


def phantom():
    data = np.full(SHAPE, .125, np.float32)
    data[:, 3:8, 4:10] = .25
    data[:, 14:20, 17:24] = 1
    data[14:18, 2:6, 20:24] = .5
    return data


def local_handle(kind, axis):
    if kind == "translator":
        assert axis == "z"
        return np.asarray(AXES[axis]["vector"]) * (RADIUS + np.floor(RADIUS / 7) + 1)
    vector = sum((np.asarray(spec["vector"]) for key, spec in AXES.items() if key != axis), np.zeros(3))
    return vector / np.linalg.norm(vector) * RADIUS


def rodrigues(axis, angle):
    axis = np.asarray(axis, float)
    axis /= np.linalg.norm(axis)
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) * np.cos(angle) + np.outer(axis, axis) * (1 - np.cos(angle)) + cross * np.sin(angle)


def intersect(click, direction, origin, normal):
    denominator = np.dot(direction, normal)
    assert abs(denominator) > .1
    return click + np.dot(np.asarray(origin) - click, normal) / denominator * direction


def rotation_from_drag(first, last, direction, origin, axis):
    start = intersect(np.asarray(first), direction, origin, axis) - origin
    end = intersect(np.asarray(last), direction, origin, axis) - origin
    angle = np.arctan2(np.dot(axis, np.cross(start, end)), np.dot(start, end))
    return rodrigues(axis, angle), float(angle)


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    data = phantom()
    return {"case": name, "registered_widget": WIDGET, "plugin": "napari-threedee",
            "input": {"shape": list(data.shape), "dtype": data.dtype.str, "sha256": hashlib.sha256(data.tobytes()).hexdigest()},
            "size": list(SIZE), "camera": {key: list(value) if isinstance(value, tuple) else value for key, value in CAMERA.items()},
            "plane_position": list(POSITION), "plane_normal": list(NORMAL), "plane_thickness": 1.,
            "radius": RADIUS, "handle_size": HANDLE_SIZE, "volume_blending": "translucent_no_depth",
            "depiction": "plane", "rendering": "mip", "interpolation3d": "nearest",
            "clip_plane": {"position": list(POSITION), "normal": [0., 1., 0.], "enabled": True} if name == "plane_clipped" else None,
            "event_api": "real QtTest mousePress/mouseMove/mouseRelease on the installed Qt canvas",
            "picking": "installed CPU ray/sphere callbacks, not GPU ID picking",
            "cleanup_scope": "two mouse callback owners, detached visual, public viewer close and clean process exit; not proof of all signal disconnections",
            "comparison": "whole-frame exact uint8 RGBA, independently projected face landmarks, no fitting"}


def render(name):
    assert metadata.version("napari") == "0.9.2" and metadata.version("napari-threedee") == "0.0.29"
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
            qt.processEvents()
            record("initialized")
            first = np.asarray(canvas._map_canvas2world(tuple(first_xy), canvas.view))
            last = np.asarray(canvas._map_canvas2world(tuple(end_xy), canvas.view))
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


def assert_landmarks(name, image, params, extras):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert image[1, 1].tolist() == [0, 0, 0, 255]
    for key, landmark in params["landmarks"].items():
        x, y = np.rint(landmark["pixel"]).astype(int)
        assert 1 <= x < SIZE[0] - 1 and 1 <= y < SIZE[1] - 1
        face = image[y, x, :3].astype(int)
        assert face.min() > 0 and image[y, x, 3] == 255, (name, key, face)
        axis = landmark["axis"]
        if axis == "x":
            assert face[0] > face[1] > face[2]
        elif axis == "y":
            assert face[2] > face[0] > face[1]
        else:
            assert face[1] > face[0] and face[0] == face[2]
    for key, landmark in params.get("scientific_landmarks", {}).items():
        x, y = np.rint(landmark["pixel"]).astype(int)
        # Fixed normalized-byte quantization margin, declared before either
        # renderer runs. The entire frame still requires exact oracle equality.
        assert np.max(np.abs(image[y, x].astype(int) - landmark["rgba"])) <= 1, (name, key, image[y, x])
    if name in ("plane_translation", "plane_rotation"):
        assert not np.array_equal(image, extras["before"])
        moved = next(stage for stage in params["stages"] if stage["stage"] == "moved")
        key = "position" if name == "plane_translation" else "normal"
        expected = params["analytic_plane_position"] if name == "plane_translation" else params["analytic_plane_normal"]
        np.testing.assert_allclose(moved[key], expected, rtol=0, atol=1e-6)
    retired = params["stages"][-1]
    assert retired["stage"] == "retired_layer_removed" and retired["owned_callbacks"] == [False, False]
