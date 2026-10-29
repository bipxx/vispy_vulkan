"""Agg line caps, joins, acute and degenerate joins, and scaled width (W5, M09).

Each case draws Agg lines (vispy Line(method="agg")) on a fixed 128x96 scene canvas and reads the frame once. The
Agg visual antialiases in its own shader, not with driver line smoothing, and the existing scene fixture's Agg cases
match OpenGL exactly, so every case here is compared exactly; this is fixed before any capture.

- caps: one line per distinct vispy 0.17 cap code. joins: miter, round and bevel at a right angle and an acute bend;
  joins other than round have no public setter, so the case sets the visual's own join uniform in both renderers.
- degenerate: a 10-degree turn, a full reversal and a repeated vertex. Upstream draws nothing for the last two
  polylines (not even their regular segments); the landmarks record that, and parity is exact.
- px_scale2, px_scale3: the canvas with vispy's px_scale of 2 and 3 (physical pixels per logical pixel, as on a
  high-DPI display), read at its physical size. The Agg width is in logical pixels and scales with the pixel
  transform. Neither the canvas dpi nor a larger render size scales line width.
"""
from __future__ import annotations

import hashlib

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (128, 96)
CASES = ("caps", "joins", "degenerate", "px_scale2", "px_scale3")
CRITERIA = {name: "exact" for name in CASES}
PX_SCALES = {"px_scale2": 2, "px_scale3": 3}
GREEN = (0, 255, 0, 255)
CAPS = ("none", "round", "triangle in", "triangle out", "square", "|")  # every distinct vispy 0.17 cap code
CAP_ROWS = (10, 24, 38, 52, 66, 80)
JOINS = ("miter", "round", "bevel")
JOIN_BASES = (8, 38, 68)
DEGENERATE = (
    [[16, 14], [110, 14], [16, 30.5]],  # a 10-degree turn
    [[16, 50], [100, 50], [40, 50]],  # a full reversal along the same line
    [[16, 74], [60, 74], [60, 74], [110, 86]],  # a repeated vertex: a zero-length segment
)
ZIGZAG = [[16, 70], [40, 22], [64, 70], [88, 22], [112, 70]]


def polylines(name):
    if name == "caps":
        return [[[24, row], [104, row]] for row in CAP_ROWS]
    if name == "joins":
        return [[[16, base], [52, base], [52, base + 20], [100, base + 4]] for base in JOIN_BASES]
    if name == "degenerate":
        return [list(map(list, line)) for line in DEGENERATE]
    return [ZIGZAG]


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    lines = polylines(name)
    digest = hashlib.sha256(np.asarray([point for line in lines for point in line], np.float32).tobytes())
    scale = PX_SCALES.get(name, 1)
    return {"case": name, "size": list(SIZE), "px_scale": scale, "render_size": [SIZE[0] * scale, SIZE[1] * scale],
            "width": {"caps": 9, "joins": 7}.get(name, 5), "polylines": lines,
            "caps": list(CAPS) if name == "caps" else ["round"], "joins": list(JOINS) if name == "joins" else ["round"],
            "color": list(GREEN), "criterion": CRITERIA[name], "inputs_sha256": digest.hexdigest()}


def render(name, backend="dawn_headless"):
    """Draw the case's Agg lines once and read the frame at the case's render size."""
    params = specification(name)
    from vispy import scene
    from vispy.visuals.line.line import joins

    canvas = scene.SceneCanvas(app=backend, size=SIZE, show=backend == "pyqt6", decorate=False, bgcolor=(0, 0, 0, 1),
                               config={"samples": 0}, px_scale=params["px_scale"])
    if backend == "pyqt6":
        canvas.app.native.setQuitOnLastWindowClosed(False)
        canvas._backend._vispy_warmup()
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
    try:
        color = tuple(value / 255 for value in GREEN)
        for index, line in enumerate(params["polylines"]):
            cap = params["caps"][index] if name == "caps" else "round"
            visual = scene.visuals.Line(pos=np.asarray(line, np.float32), color=color, width=params["width"],
                                        method="agg", antialias=True, line_caps=(cap, cap), parent=canvas.scene)
            if name == "joins":
                visual._line_visual._U["linejoin"] = joins[params["joins"][index]]
        image = np.array(canvas.render(size=tuple(params["render_size"]), alpha=True), copy=True)
        params["pixel_scale"] = float(canvas.pixel_scale)
        return image, commands, shaders, params
    finally:
        parser.parse = original
        canvas.close()


def assert_landmarks(name, image):
    """Semantic, exact checks away from antialiased edges."""
    width, height = specification(name)["render_size"]
    assert image.shape == (height, width, 4) and image.dtype == np.uint8, (name, image.shape)
    assert image[0, 0].tolist() == [0, 0, 0, 255] and image[-1, 0].tolist() == [0, 0, 0, 255], name
    green = np.all(image == GREEN, axis=2)
    if name == "caps":
        for row in CAP_ROWS:  # each 9-px line's centre is fully covered
            assert green[row, 64], (name, row)
    elif name == "joins":
        for base in JOIN_BASES:
            assert green[base, 34] and green[base + 10, 52], (name, base)
    elif name == "degenerate":
        # The 10-degree turn is drawn; upstream draws nothing for the reversal and the repeated vertex.
        assert green[14, 60] and image[50, 70, :3].max() == 0 and image[74, 40, :3].max() == 0, name
    else:
        scale = width / SIZE[0]  # the zigzag's first two segments, mid-way
        assert green[round(46 * scale), round(28 * scale)] and green[round(46 * scale), round(52 * scale)], name
    assert 0.002 * green.size < green.sum() < 0.5 * green.size, (name, int(green.sum()))
