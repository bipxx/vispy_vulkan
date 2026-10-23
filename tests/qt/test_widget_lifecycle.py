"""QWidget lifecycle for the installed Qt binding."""

import os

import pytest

pytestmark = pytest.mark.gpu

qt_api = os.environ.get("QT_API", "pyqt6")


def test_native_is_parentable_qwidget_not_qopenglwidget():
    os.environ.setdefault("QT_API", qt_api)
    from vispy import app

    application = app.use_app(qt_api)
    qt_backend = application.backend_module
    canvas = app.Canvas(app=qt_api, size=(40, 30), show=False, resizable=True)
    native = canvas.native
    qwidget = qt_backend.QWidget
    print("QWidget rather than QOpenGLWidget", type(native).__name__, [cls.__name__ for cls in type(native).__mro__])
    assert isinstance(native, qwidget)
    assert not any(cls.__name__ in ("QGLWidget", "QOpenGLWidget")
                   for cls in type(native).__mro__)
    parent = qwidget()
    native.setParent(parent)
    assert native.parent() is parent
    for ratio in (1, 1.25, 1.5, 2):
        native._dawn_ratio_override = ratio
        native.resizeGL(40, 30)
        assert canvas.physical_size == (int(round(40 * ratio)), int(round(30 * ratio)))
    native._dawn_ratio_override = None
    overlay = qwidget(native)
    overlay.setGeometry(0, 0, 4, 4)
    overlay.show()
    assert overlay.parent() is native
    parent.show()
    native.show()
    app.process_events()
    native.showMinimized()
    app.process_events()
    native.showNormal()
    app.process_events()
    shot = native.grabFramebuffer()
    assert shot.width() > 0 and shot.height() > 0
    from vispy import _dawn
    trace = "\n".join(_dawn.debug_trace())
    print("hwnd surface configured", "hwnd surface configured" in trace)
    print("swapchain present", "swapchain present" in trace)
    readback = native._dawn_presentation == 'readback'
    if readback:
        assert not _dawn.benchmark_surface_info(int(native._dawn_canvas_id))['attached']
        assert native.grab().width() > 0
    else:
        assert "hwnd surface configured" in trace
        assert "swapchain present" in trace
    old_info = _dawn.device_info()
    before_loss = _dawn.probe()
    _dawn.lose_device()
    # device_info() initializes/recreates the device. Observe without recovering
    # here so that the real QWidget paint below must perform recovery.
    lost = _dawn.probe()
    assert lost["device_generation"] == before_loss["device_generation"]
    marked = len(_dawn.debug_trace())

    import numpy as np
    from vispy import gloo

    def draw(event):
        gloo.set_clear_color((1, 0, 0, 1))
        gloo.clear()
        program = gloo.Program(
            "attribute vec2 a_position; void main() { gl_Position = vec4(a_position, 0.0, 1.0); }",
            "void main() { gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0); }",
        )
        program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program.draw("triangles")

    canvas.events.draw.connect(draw)
    # QPainter presentation requires a genuine Qt paint dispatch, including
    # Qt's backing-store redirection; do not call the virtual method directly.
    native.update()
    for _ in range(100):
        application.process_events()
        if _dawn.probe()['device_generation'] > before_loss['device_generation']:
            break
    fresh = _dawn.debug_trace()[marked:]
    configured = any(line.startswith("hwnd surface configured") for line in fresh)
    presented = "swapchain present" in fresh
    print("hwnd surface configured after loss", configured)
    print("swapchain present after loss", presented)
    if readback:
        assert not configured and not presented
        assert not _dawn.benchmark_surface_info(int(native._dawn_canvas_id))['attached']
    else:
        assert configured
        assert presented
    recovered = _dawn.probe()
    assert recovered["device_generation"] > before_loss["device_generation"]
    recovered_info = _dawn.device_info()
    assert recovered_info["ok"], recovered_info["error"]
    assert recovered_info["loss_count"] == old_info["loss_count"] + 1
    image = np.array(_dawn.read_pixels(int(native._dawn_canvas_id), 0, 0, 4, 4, True))
    assert image.shape == (4, 4, 4)
    np.testing.assert_array_equal(image, np.full_like(image, [255, 0, 0, 255]))
    canvas.close()
    parent.close()
    print("QWidget lifecycle ok")


def test_handle_detach_and_late_events_after_canvas_close(monkeypatch):
    from vispy import _dawn, app

    canvas = app.Canvas(app=qt_api, size=(24, 16), show=True)
    native = canvas.native
    canvas_id = int(native._dawn_canvas_id)
    application = canvas.app
    application.process_events()
    try:
        original = native.effectiveWinId
        if native._dawn_presentation == 'readback':
            def unexpected_handle_request():
                raise AssertionError('readback profile requested a native window handle')
            monkeypatch.setattr(native, 'effectiveWinId', unexpected_handle_request)
            native._dawn_surface()
            assert not _dawn.benchmark_surface_info(canvas_id)['attached']
        else:
            monkeypatch.setattr(native, "effectiveWinId", lambda: None)
            native._dawn_surface()
            assert not _dawn.benchmark_surface_info(canvas_id)["attached"]
            monkeypatch.setattr(native, "effectiveWinId", original)
            native._dawn_surface()
            assert _dawn.benchmark_surface_info(canvas_id)["attached"]
        canvas.close()
        # Qt can deliver handle/resize events while destroying the QWidget.
        native._dawn_surface()
        native.resizeGL(24, 16)
        native._poll_dawn()
        assert native.context() is None
        application.process_events()
    finally:
        canvas.close()
