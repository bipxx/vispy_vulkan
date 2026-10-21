"""Real pinned glue Qt scatter/volume viewers without host source changes."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (128, 128)
CASES = ("scatter", "scatter_edit", "scatter_axes", "volume", "volume_edit")


def render(name):
    if name not in CASES:
        raise ValueError(name)
    assert metadata.version("glue-vispy-viewers") == "1.4.0"
    from glue.config import settings
    from glue.core import Data, DataCollection
    from glue_qt.app.application import GlueApplication
    from glue_qt.utils import get_qapp
    from glue_vispy_viewers.scatter.qt.scatter_viewer import VispyScatterViewer
    from glue_vispy_viewers.volume.qt.volume_viewer import VispyVolumeViewer
    from glue.viewers.volume3d.viewer_state import VolumeViewerState3D
    from qtpy import QtWidgets

    qt = get_qapp()
    qt.setQuitOnLastWindowClosed(False)
    old_background, old_foreground = settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR
    settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR = "black", "white"
    original_dialog = QtWidgets.QMessageBox.critical
    dialogs = []

    def reject_dialog(*args, **kwargs):
        dialogs.append(str(args[2] if len(args) > 2 else args))
        raise RuntimeError("glue requested an error dialog: " + dialogs[-1])

    # A GUI error is qualification failure; a test must never wait for a dialog.
    QtWidgets.QMessageBox.critical = reject_dialog
    application = None
    commands, shaders, inputs = [], {}, []

    def record(array):
        inputs.append({"shape": list(array.shape), "dtype": array.dtype.str,
            "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()})
        return array

    try:
        if name.startswith("scatter"):
            x = record(np.array([.25, .75], np.float32))
            y = record(np.array([.5, .5], np.float32))
            z = record(np.array([.5, .5], np.float32))
            data = Data(label="analytic scatter", x=x, y=y, z=z)
        else:
            axis = np.linspace(-1, 1, 32, dtype=np.float32)
            z, y, x = np.meshgrid(axis, axis, axis, indexing="ij")
            data = Data(label="analytic volume", intensity=record(
                ((x / .7) ** 2 + (y / .55) ** 2 + (z / .4) ** 2 <= 1).astype(np.float32)))
        application = GlueApplication(DataCollection([data]))
        if name.startswith("scatter"):
            viewer = application.new_data_viewer(VispyScatterViewer)
        else:
            viewer = application.new_data_viewer(VispyVolumeViewer,
                state=VolumeViewerState3D(resolution=32, downsample=False))
        canvas = viewer._vispy_widget.canvas
        parser = canvas.context.shared.parser
        original = parser.parse

        def log(batch):
            for command in batch:
                commands.append(freeze(command))
                if command[0] == "DATA" and isinstance(command[3], str):
                    shaders[str(command[1])] = command[3]
            return original(batch)

        parser.parse = log
        assert viewer.add_data(data)
        state = viewer.state
        state.visible_axes = name == "scatter_axes"
        state.perspective_view = False
        layer = state.layers[0]
        layer.alpha = 1
        layer.color_mode = "Fixed"
        layer.color = "#ff0000" if name.startswith("scatter") else "#00ff00"
        if name.startswith("scatter"):
            state.x_att, state.y_att, state.z_att = (data.id[axis] for axis in "xyz")
            layer.size_mode, layer.size = "Fixed", 14
            state.set_limits(0, 1, 0, 1, 0, 1)
            if name == "scatter_edit":
                data.update_components({data.id["x"]: record(np.array([.5, .75], np.float32))})
                layer.color = "#0000ff"
        else:
            layer.attribute = data.id["intensity"]
            layer.v_min, layer.v_max = 0, 1
            state.set_limits(-.5, 31.5, -.5, 31.5, -.5, 31.5)
            if name == "volume_edit":
                updated = np.zeros((32, 32, 32), np.float32)
                updated[10:22, 8:24, 18:26] = 1
                data.update_components({data.id["intensity"]: record(updated)})
                layer.color = "#0000ff"
        canvas.native.setFixedSize(*SIZE)
        application.show()
        viewer.show()
        qt.processEvents()
        canvas.size = SIZE
        canvas.central_widget.size = SIZE
        camera = viewer._vispy_widget.view.camera
        camera.azimuth, camera.elevation = 0, 0
        camera.center, camera.scale_factor = (0, 0, 0), 2.5
        canvas.app.process_events()
        assert not dialogs, dialogs
        assert viewer._opengl_ok, "the unmodified host's context availability check must succeed"
        image = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        params = {"case": name, "size": list(SIZE), "inputs": inputs,
            "viewer_class": type(viewer).__name__, "axes": state.visible_axes,
            "native_mro": [cls.__name__ for cls in type(canvas.native).__mro__],
            "camera": {"azimuth": camera.azimuth, "elevation": camera.elevation,
                "center": list(camera.center), "scale_factor": camera.scale_factor},
            "color": layer.color, "alpha": layer.alpha,
            "limits": [state.x_min, state.x_max, state.y_min, state.y_max, state.z_min, state.z_max],
            "host_context_available": bool(viewer._opengl_ok), "error_dialogs": dialogs}
        if not name.startswith("scatter"):
            params["resolution"] = state.resolution
            params["downsample"] = state.downsample
            params["clim"] = [layer.v_min, layer.v_max]
        return image, commands, shaders, params
    finally:
        if application is not None:
            for group in application.viewers:
                for viewer in group:
                    viewer.close(warn=False)
            application.close()
        settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR = old_background, old_foreground
        QtWidgets.QMessageBox.critical = original_dialog


def assert_landmarks(name, image):
    assert image.shape == (128, 128, 4)
    assert image[2, 2].tolist() == [0, 0, 0, 255]
    if name in ("scatter", "scatter_axes"):
        assert image[64, 38].tolist() == [255, 0, 0, 255], image[64, 38]
        assert image[64, 90].tolist() == [255, 0, 0, 255], image[64, 90]
    elif name == "scatter_edit":
        assert image[64, 38].tolist() == [0, 0, 0, 255]
        assert image[64, 64].tolist() == [0, 0, 255, 255], image[64, 64]
    elif name == "volume":
        assert image[64, 64].tolist() == [0, 255, 0, 255], image[64, 64]
    elif name == "volume_edit":
        assert image[64, 64].tolist() == [0, 0, 0, 255], image[64, 64]
        assert image[64, 88].tolist() == [0, 0, 255, 255], image[64, 88]
    assert np.any(image[..., :3] != 0), "blank host frame cannot establish admission"
