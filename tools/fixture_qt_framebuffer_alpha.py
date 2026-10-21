"""Fixed public Qt widget capture semantics, independent of renderer results."""

from __future__ import annotations

import numpy as np

SIZE = (16, 12)
CASES = ("opaque_alpha", "quarter_alpha", "zero_alpha", "redraw_and_ownership", "no_alpha_buffer")
VERTEX = "attribute vec2 a_position; void main(){gl_Position=vec4(a_position,0.,1.);}"
FRAGMENT = "uniform vec4 u_color; void main(){gl_FragColor=u_color;}"


def parameters(name):
    if name not in CASES:
        raise ValueError(name)
    return {"case": name, "size": list(SIZE), "decorate": False, "alpha_size": 0 if name == "no_alpha_buffer" else 8,
            "clear": [0., 0., 0., .25 if name == "quarter_alpha" else 0. if name == "zero_alpha" else 1.],
            "first_color": [.5, .25, .125, .5], "second_color": [0., .5, .25, .5],
            "blend_func": ["src_alpha", "one_minus_src_alpha", "src_alpha", "one_minus_src_alpha"],
            "redraw": name == "redraw_and_ownership", "comparison": "exact independent full-frame arrays",
            "raw_alpha_policy": "ordinary direct drawing retains blend alpha; Qt paint clears only alpha to current clear color"}


def qimage_rgba(image, backend):
    fmt = backend.QtGui.QImage.Format.Format_RGBA8888 if hasattr(backend.QtGui.QImage, "Format") else backend.QtGui.QImage.Format_RGBA8888
    copied = image.convertToFormat(fmt)
    pointer = copied.constBits()
    size = copied.sizeInBytes() if hasattr(copied, "sizeInBytes") else copied.byteCount()
    if hasattr(pointer, "setsize"):
        pointer.setsize(size)
    data = np.frombuffer(pointer, np.uint8, count=size).reshape(copied.height(), copied.bytesPerLine())
    return data[:, :copied.width()*4].reshape(copied.height(), copied.width(), 4).copy()


def assert_semantics(name, arrays):
    spec = parameters(name)
    for image in arrays.values():
        assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    before, native = arrays["raw_before"], arrays["native"]
    # GL fixed-point blending permits the adjacent rounding endpoints. Exact
    # candidate equality is separately required against the frozen GL arrays.
    rgb = np.array([64, 32, 16])
    assert np.max(np.abs(before[..., :3].astype(np.int16) - rgb)) <= 1
    alpha = (.5 * .5 + (1 - .5) * spec["clear"][3]) * 255
    assert np.max(np.abs(before[..., 3].astype(np.float64) - alpha)) <= 1
    clear_alpha = round(spec["clear"][3] * 255)
    if name == "no_alpha_buffer":
        assert np.all(native[..., 3] == 255)
    else:
        assert np.max(np.abs(native[..., 3].astype(np.int16) - clear_alpha)) <= 1
    if name == "zero_alpha":
        assert np.all(native[..., :3] == 0), "Qt's premultiplied QImage conversion at zero alpha"
    if spec["redraw"]:
        assert np.max(np.abs(native[..., :3].astype(np.int16) - [0, 64, 32])) <= 1
        assert np.array_equal(arrays["owned_first"], arrays["owned_after_close"])
        assert np.max(np.abs(arrays["owned_first"][..., :3].astype(np.int16) - rgb)) <= 1


def render(name, api="pyqt6"):
    from vispy import app, gloo
    spec = parameters(name)
    application = app.use_app(api)
    backend = application.backend_module
    canvas = app.Canvas(app=api, size=SIZE, show=False, vsync=False, decorate=False,
                        config={"alpha_size": spec["alpha_size"], "samples": 0})
    canvas.events.draw.ignore_callback_errors = False
    program = gloo.Program(VERTEX, FRAGMENT)
    program["a_position"] = np.array([[-1,-1],[3,-1],[-1,3]], np.float32)
    program["u_color"] = tuple(spec["first_color"])
    draw_calls = []

    def draw(event):
        draw_calls.append(len(draw_calls))
        gloo.set_viewport(0, 0, *SIZE)
        gloo.set_clear_color(tuple(spec["clear"]))
        gloo.clear(color=True, depth=False, stencil=False)
        gloo.set_state(blend=True, depth_test=False, blend_func=tuple(spec["blend_func"]))
        program.draw("triangles")

    canvas.events.draw.connect(draw)
    owned = None
    arrays = {}
    try:
        canvas.show()
        for _ in range(10):
            application.process_events()
        assert canvas.native.isVisible() and canvas.physical_size == SIZE, (canvas.size, canvas.physical_size, canvas.native.isVisible())
        canvas.set_current()
        canvas.events.draw(region=None)
        arrays["raw_before"] = gloo.read_pixels(alpha=True)
        owned = canvas.native.grabFramebuffer()
        arrays["owned_first"] = qimage_rgba(owned, backend)
        before_grab = len(draw_calls)
        if spec["redraw"]:
            program["u_color"] = tuple(spec["second_color"])
        returned = canvas.native.grabFramebuffer()
        arrays["native"] = qimage_rgba(returned, backend)
        observations = {"draws_before_last_grab": before_grab, "draws_after_last_grab": len(draw_calls),
                        "qimage_has_alpha": bool(returned.hasAlphaChannel()),
                        "qimage_format": int(returned.format().value) if hasattr(returned.format(), "value") else int(returned.format()),
                        "dpr": float(returned.devicePixelRatio()), "config": dict(canvas.context.config),
                        "backend_origin": backend.__file__, "actual_physical_size": list(canvas.physical_size)}
        assert observations["draws_after_last_grab"] > before_grab, "native widget capture must redraw"
    finally:
        canvas.close()
        application.process_events()
    arrays["owned_after_close"] = qimage_rgba(owned, backend)
    assert np.array_equal(arrays["owned_first"], arrays["owned_after_close"])
    assert_semantics(name, arrays)
    return arrays, spec, observations
