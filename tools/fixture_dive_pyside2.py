"""Unchanged DIVE public exports through the real PySide2 Qt5 binding.

Analytic inputs and exact landmark assertions are shared with the preserved
PyQt5 attempt. Rendering is explicitly called only by a hardware qualification
process; importing this module does not import Qt or VisPy.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import numpy as np

try:
    from .fixture_dive import SIZE, CASES, inputs, landmark_spec, assert_landmarks
    from .fixture_gloo import freeze
except ImportError:
    from fixture_dive import SIZE, CASES, inputs, landmark_spec, assert_landmarks
    from fixture_gloo import freeze


def qimage_rgba(image):
    """Copy Qt5's public constBits buffer, respecting row stride and lifetime."""
    from PySide2 import QtGui

    image = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
    if image.isNull():
        raise ValueError("DIVE returned a null screenshot image")
    size = image.sizeInBytes() if hasattr(image, "sizeInBytes") else image.byteCount()
    pointer = image.constBits()
    if hasattr(pointer, "setsize"):
        pointer.setsize(size)
    rgba = np.frombuffer(pointer, np.uint8, count=size).reshape(image.height(), image.bytesPerLine())
    return rgba[:, :image.width() * 4].reshape(image.height(), image.width(), 4).copy()


def render(name):
    if name not in CASES:
        raise ValueError(name)
    from vispy import app
    app.use_app("PySide2")  # DIVE resolves its Qt binding at import time.
    import pandas as pd
    from DIVE import DIVEWidget
    from PySide2 import QtCore, QtGui, QtWidgets

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
        return qimage_rgba(QtGui.QImage(str(path))), path.read_bytes()

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
