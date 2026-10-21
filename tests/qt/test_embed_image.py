"""Unmodified napari image, a custom Function, and a resident 4096 pan."""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _qimage_rgba(image):
    from PyQt6.QtGui import QImage

    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pointer = converted.bits()
    pointer.setsize(converted.sizeInBytes())
    array = np.frombuffer(pointer, np.uint8).reshape(
        converted.height(), converted.bytesPerLine() // 4, 4
    )
    return np.array(array[:, : converted.width(), :4])


def test_napari_image_and_custom_function_match_clear_oracle_path():
    os.environ.setdefault("QT_API", "pyqt6")
    pytest.importorskip("napari")
    import napari
    from vispy import app, gloo
    from vispy.visuals.shaders import Function
    from vispy.visuals.transforms import STTransform

    data = np.zeros((16, 16), np.float32)
    data[4:12, 4:12] = 1
    viewer = napari.Viewer(show=False)
    viewer.add_image(data, colormap="gray", rendering="translucent")
    canvas = viewer.window._qt_viewer.canvas
    native = canvas.native
    scene = canvas._scene_canvas
    print("native", type(native).__name__, "mro", [cls.__name__ for cls in type(native).__mro__])
    assert not any(cls.__name__ == "QOpenGLWidget" for cls in type(native).__mro__)
    assert any(cls.__name__ == "QWidget" for cls in type(native).__mro__)
    rendered = scene.render(alpha=True)
    scene.set_current()
    scene.events.draw(region=None)
    grabbed = _qimage_rgba(native.grabFramebuffer())
    height = min(rendered.shape[0], grabbed.shape[0])
    width = min(rendered.shape[1], grabbed.shape[1])
    difference = np.abs(rendered[:height, :width].astype(np.int16) - grabbed[:height, :width].astype(np.int16))
    crop = (40, 30, 20, 16)
    cropped = scene.render(crop=crop, alpha=True)
    x, y, crop_w, crop_h = crop
    origin_matches = np.array_equal(rendered[0, 0], grabbed[0, 0])
    crop_matches = np.array_equal(cropped, rendered[y:y + crop_h, x:x + crop_w])
    alpha_opaque = bool(np.all(rendered[:, :, 3] == 255))
    center = rendered[height // 2, width // 2]
    print(
        "napari", napari.__version__,
        "oracle agreement", "maxabs", int(difference.max()),
        "crop", crop_matches, "alpha", alpha_opaque, "origin", origin_matches,
        "center", center.tolist(),
    )
    assert int(difference.max()) == 0
    assert crop_matches
    assert alpha_opaque
    assert origin_matches
    assert center[0] > 200 and rendered[0, 0, 0] < 10
    viewer.close()

    class Blue(Function):
        def __init__(self):
            Function.__init__(self, "void blue() { gl_FragColor = vec4(0.1, 0.2, 0.9, 1.0); }")

    class Shift(Function):
        def __init__(self):
            Function.__init__(self, "vec4 shift(vec4 pos) { return pos + vec4($dx, 0.0, 0.0, 0.0); }")

    headless = app.Canvas(app="dawn_headless", size=(8, 6), show=False)
    from vispy.visuals.shaders import ModularProgram

    program = ModularProgram(
        "attribute vec2 a_position; void main() { gl_Position = $shift(vec4(a_position, 0.0, 1.0)); }",
        "void main() { $blue(); }",
    )
    shift = Shift()
    shift["dx"] = 0.0
    program.vert["shift"] = shift
    program.frag["blue"] = Blue()
    program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    placed = STTransform(scale=(1, 1, 1), translate=(0, 0, 0))

    def draw(event):
        gloo.set_clear_color((0, 0, 0, 1))
        gloo.clear()
        program.draw("triangles")

    headless.events.draw.connect(draw)
    painted = headless.render()
    print("function subclass", type(Blue()).__bases__[0].__name__, "pixel", painted[0, 0].tolist(), "transform", placed.scale.tolist())
    assert painted[0, 0].tolist() == [25, 51, 229, 255]


def test_resident_4096_pan_reuses_texture():
    os.environ.setdefault("QT_API", "pyqt6")
    from vispy import app, gloo, scene
    from vispy import _dawn

    canvas = scene.SceneCanvas(app="dawn_headless", size=(32, 32), show=False)
    view = canvas.central_widget.add_view()
    image = np.zeros((64, 64), np.float32)
    image[16:48, 16:48] = 1
    visual = scene.visuals.Image(image, parent=view.scene, cmap="grays")
    view.camera = scene.PanZoomCamera(aspect=1)
    view.camera.set_range()
    canvas.app.process_events()
    visual.draw() if False else None
    canvas.update()
    before = _dawn.probe()
    view.camera.pan(1, 0)
    canvas.update()
    after = _dawn.probe()
    print("pan uploads", before["texture_uploads"], after["texture_uploads"], "finish", before["finish_calls"], after["finish_calls"])
    assert after["texture_uploads"] == before["texture_uploads"]
    assert after["finish_calls"] == before["finish_calls"]
    # The 4096 case uses the same upload path with a resident allocation.
    big = gloo.Texture2D(np.zeros((4096, 4096, 4), np.uint8), interpolation="nearest")
    uploads = _dawn.probe()["texture_uploads"]
    canvas2 = app.Canvas(app="dawn_headless", size=(4, 4), show=False)
    with canvas2:
        program = gloo.Program(
            "attribute vec2 a_position; uniform vec2 u_pan; void main() { gl_Position = vec4(a_position + u_pan, 0.0, 1.0); }",
            "uniform sampler2D u_texture; void main() { gl_FragColor = texture2D(u_texture, vec2(0.5)); }",
        )
        program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program["u_texture"] = big
        program["u_pan"] = (0, 0)
        program.draw("triangles")
        _dawn.present(canvas2._backend._dawn_canvas_id)
        mid_probe = _dawn.probe()
        mid = mid_probe["texture_uploads"]
        mid_finish = mid_probe["finish_calls"]
        program["u_pan"] = (0.02, 0)
        program.draw("triangles")
        _dawn.present(canvas2._backend._dawn_canvas_id)
        end = _dawn.probe()
    print(
        "4096 uploads", uploads, mid, end["texture_uploads"],
        "zero texture reupload", end["texture_uploads"] == mid,
        "finish delta", end["finish_calls"] - mid_finish,
    )
    assert end["texture_uploads"] == mid
    assert end["finish_calls"] == mid_finish
