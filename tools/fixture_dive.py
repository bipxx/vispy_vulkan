"""Unmodified pinned DIVEWidget public data, artist and PNG export workflows.

Landmarks are defined from the analytic input and the host's CPU scene
transform, before reading pixels. No image alignment or tolerance fitting.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (640, 480)
CASES = ("scatter", "scatter_edit", "image", "image_edit")
BLACK, RED, BLUE, WHITE = ([0, 0, 0, 255], [255, 0, 0, 255],
                          [0, 0, 255, 255], [255, 255, 255, 255])


def inputs(name, edited=False):
    """Fixed asymmetric data; edit keeps the normalization range unchanged."""
    if name.startswith("scatter"):
        return {"x": np.array([-1, 1, .5 if edited else -.5], np.float64),
                "y": np.array([-1, 1, 0], np.float64)}
    values = np.zeros((8, 8), np.float32)
    if edited:
        values[:, 4:6] = 1
    else:
        values[:, 2:4] = 1
    values[5:7, 6:8] = 1
    return {"values": values}


def landmark_spec(name, edited=False):
    """Coordinates in DIVE's documented normalized -.5 to +.5 space."""
    if name.startswith("scatter"):
        return {"left": {"world": [-.25, 0, 0], "rgba": BLACK if edited else RED},
                "right": {"world": [.25, 0, 0], "rgba": BLUE if edited else BLACK}}
    return {"left": {"world": [-.1875, 0, 0], "rgba": BLACK if edited else WHITE},
            "right": {"world": [.1875, 0, 0], "rgba": WHITE if edited else BLACK}}


def assert_landmarks(name, image, params, *, before=None):
    assert image.ndim == 3 and image.shape[2] == 4 and image.dtype == np.uint8
    assert image.shape[:2] == tuple(reversed(params["screenshot_size"]))
    assert params["screenshot_api"] == "DIVEWidget.take_screenshot"
    edited = name.endswith("_edit")
    stages = [(image, params["landmarks"], edited)]
    if edited:
        assert before is not None and not np.array_equal(before, image), "public edit must change exported pixels"
        stages.append((before, params["before_landmarks"], False))
    for frame, landmarks, is_edited in stages:
        spec = landmark_spec(name, is_edited)
        assert set(landmarks) == set(spec)
        for key, record in landmarks.items():
            assert record["world"] == spec[key]["world"]
            assert record["rgba"] == spec[key]["rgba"]
            x, y = record["pixel"]
            assert 1 <= x < frame.shape[1] - 1 and 1 <= y < frame.shape[0] - 1
            assert np.all(frame[y - 1:y + 2, x - 1:x + 2] == record["rgba"]), (
                name, key, "analytic 3x3 face landmark", frame[y, x].tolist(), record)


def render(name):
    if name not in CASES:
        raise ValueError(name)
    from vispy import app
    app.use_app("PyQt5")  # DIVE resolves its Qt binding at import time.
    import pandas as pd
    from DIVE import DIVEWidget
    from PyQt5 import QtCore, QtGui, QtWidgets

    qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt.setQuitOnLastWindowClosed(False)
    qt.setStyle("Fusion")
    qt.setFont(QtGui.QFont("Arial", 10))
    widget = DIVEWidget()
    manager = widget._dive_manager
    canvas = manager.canvas
    commands, shaders = [], {}
    parser = canvas.context.shared.parser
    original = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA" and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
        return original(batch)

    parser.parse = log
    arrays = []

    def dataframe(edited=False):
        data = inputs(name, edited)
        for key, value in data.items():
            arrays.append({"field": key, "edited": edited, "dtype": value.dtype.str,
                           "shape": list(value.shape), "sha256": hashlib.sha256(value.tobytes()).hexdigest()})
        return pd.DataFrame(data) if name.startswith("scatter") else pd.DataFrame({"values": [data["values"]]})

    def settle():
        # A fixed bounded paint interval, with no image-driven convergence.
        for _ in range(20):
            qt.processEvents(QtCore.QEventLoop.AllEvents, 10)
        assert canvas.native.isVisible() and canvas.native.width() > 0

    def landmarks(edited=False):
        axis = canvas.axes[0]
        transform = axis.view.scene.node_transform(canvas.scene)
        offset = canvas.native.pos()  # Exactly the public export's composition offset.
        result = landmark_spec(name, edited)
        for record in result.values():
            point = np.asarray(transform.map(record["world"]), np.float64)
            record["pixel"] = [int(round(point[0] + offset.x())), int(round(point[1] + offset.y()))]
        return result

    def screenshot(path):
        assert not path.exists(), "public export must create a fresh PNG"
        widget.take_screenshot(str(path))
        assert path.is_file() and path.stat().st_size > 0, "DIVE swallowed a screenshot failure"
        image = QtGui.QImage(str(path)).convertToFormat(QtGui.QImage.Format_RGBA8888)
        assert not image.isNull()
        pointer = image.bits()
        pointer.setsize(image.byteCount())
        rgba = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine())
        rgba = rgba[:, :image.width() * 4].reshape(image.height(), image.width(), 4).copy()
        return rgba, path.read_bytes()

    extras = {}
    try:
        widget.setFixedSize(*SIZE)
        widget.set_settings(canvas_theme="dark", gui_theme="default", axis_label_size=14, axis_tick_size=10)
        data = dataframe()
        widget.add_data("analytic", data)
        widget.add_axis("xy", "2d", x_label="X", y_label="Y", x_grid=False, y_grid=False)
        if name.startswith("scatter"):
            widget.add_scatter_artist("xy", "points", "analytic", "x", "y", marker="o",
                                      marker_size=14, marker_color="red", line_width=0, edge_width=0)
            artist_name = "points"
        else:
            widget.add_image_artist("xy", "pixels", "analytic", "values", width=1, height=1,
                                    colormap="grays", interpolation="Nearest")
            artist_name = "pixels"
        assert widget.get_data("analytic")["data"].equals(data)
        assert widget.get_axis("xy")["x_grid"] is False
        assert widget.get_artist("xy", artist_name)["data_name"] == "analytic"
        widget.display_axis("xy")
        widget.show()
        settle()
        assert len(canvas.axes) == 1
        before_landmarks = landmarks()
        with tempfile.TemporaryDirectory(prefix="dive-public-export-") as directory:
            directory = Path(directory)
            if name.endswith("_edit"):
                extras["before"], extras["before_png"] = screenshot(directory / "before.png")
                data = dataframe(edited=True)
                widget.edit_data("analytic", data=data)
                assert widget.get_data("analytic")["data"].equals(data)
                if name.startswith("scatter"):
                    widget.edit_artist("xy", artist_name, marker_color="blue")
                    assert widget.get_artist("xy", artist_name)["marker_color"] == "blue"
                settle()
            points = landmarks(name.endswith("_edit"))
            image, extras["png"] = screenshot(directory / "after.png")
        params = {"case": name, "widget_size": list(SIZE), "screenshot_size": [image.shape[1], image.shape[0]],
                  "canvas_size": list(canvas.size), "canvas_offset": [canvas.native.x(), canvas.native.y()],
                  "device_pixel_ratio": float(canvas.native.devicePixelRatioF()), "inputs": arrays,
                  "screenshot_api": "DIVEWidget.take_screenshot", "qt_style": qt.style().objectName(),
                  "qt_font": qt.font().toString(), "axis": "2d", "grid": False,
                  "canvas_theme": "dark", "artist": artist_name, "landmarks": points,
                  "native_mro": [cls.__name__ for cls in type(canvas.native).__mro__]}
        if name.endswith("_edit"):
            params["before_landmarks"] = before_landmarks
        return image, commands, shaders, params, extras
    finally:
        parser.parse = original
        canvas.close()
        widget.close()
        widget.deleteLater()
        qt.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        qt.processEvents()
