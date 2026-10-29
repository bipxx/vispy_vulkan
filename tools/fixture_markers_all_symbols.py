"""Every vispy 0.17 marker symbol at small and large sizes, with and without edges (W5, M02).

Each case draws all fifteen symbol shaders in a fixed grid: a row each for size 8 and 24, with edge width 0 and 2,
green faces and red edges, on a black 512x160 scene canvas without a camera. The cases vary the drawing method (points
and instanced), antialiasing (0 and 1), and scene scaling under a 2x view zoom.

Every case uses decision D17's documented difference (user, 2026-10-29, under D4), fixed before this capture: pixels
whose reference 3x3 neighbourhood is uniform stay exact, and other pixels may differ, by any amount, on at most 0.1% of
the frame. Aliased markers flip whole edge pixels where the inside/outside test ties exactly (an earlier exact capture
measured 41 such pixels on arrow, diamond and tailed_arrow).
"""
from __future__ import annotations

import hashlib

import numpy as np

try:
    from .fixture_gloo import freeze
    from .smooth_line_parity import reference_edges
except ImportError:
    from fixture_gloo import freeze
    from smooth_line_parity import reference_edges

SIZE = (512, 160)
SYMBOLS = ("arrow", "clobber", "cross", "cross_lines", "diamond", "disc", "hbar", "ring", "square", "star",
           "tailed_arrow", "triangle_down", "triangle_up", "vbar", "x")
ROWS = ((20, 8., 0.), (48, 8., 2.), (84, 24., 0.), (128, 24., 2.))  # (y, size, edge width)
CASES = ("points_aa0", "points_aa1", "instanced_aa0", "instanced_aa1", "points_scene_zoom2")
CRITERIA = {name: "edge_pixels" for name in CASES}  # decision D17
MAX_EDGE_FRACTION = .001
FACE, EDGE = (0., 1., 0., 1.), (1., 0., 0., 1.)


def grid():
    positions, sizes, edges, symbols = [], [], [], []
    for y, size, edge in ROWS:
        for column, symbol in enumerate(SYMBOLS):
            positions.append([24 + 32 * column, y])
            sizes.append(size)
            edges.append(edge)
            symbols.append(symbol)
    return (np.asarray(positions, np.float32), np.asarray(sizes, np.float32), np.asarray(edges, np.float32), symbols)


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    positions, sizes, edges, symbols = grid()
    digest = hashlib.sha256(positions.tobytes() + sizes.tobytes() + edges.tobytes() + ",".join(symbols).encode())
    return {"case": name, "size": list(SIZE), "method": name.split("_")[0],
            "antialias": 0. if name.endswith("aa0") else 1., "scaling": "scene" if "scene" in name else "fixed",
            "zoom": 2 if name.endswith("zoom2") else 1, "symbols": list(SYMBOLS), "rows": [list(row) for row in ROWS],
            "face_color": list(FACE), "edge_color": list(EDGE), "criterion": CRITERIA[name], "inputs_sha256": digest.hexdigest()}


def render(name, backend="dawn_headless"):
    """Draw the symbol grid once and read the frame."""
    params = specification(name)
    from vispy import scene

    canvas = scene.SceneCanvas(app=backend, size=SIZE, show=backend == "pyqt6", decorate=False, bgcolor=(0, 0, 0, 1),
                               config={"samples": 0})
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
        positions, sizes, edges, symbols = grid()
        parent = canvas.scene
        if params["zoom"] != 1:
            # A 2x zoom about the canvas centre: markers keep their grid order and scene scaling doubles their size.
            view = scene.Node(parent=canvas.scene)
            view.transform = scene.transforms.STTransform(scale=(2, 2), translate=(-SIZE[0] / 2, -SIZE[1] / 2))
            parent = view
        markers = scene.visuals.Markers(parent=parent, method=params["method"], scaling=params["scaling"],
                                        antialias=params["antialias"])
        markers.set_data(pos=positions, size=sizes, edge_width=edges, face_color=FACE, edge_color=EDGE, symbol=symbols)
        image = np.array(canvas.render(alpha=True), copy=True)
        return image, commands, shaders, params
    finally:
        parser.parse = original
        canvas.close()


def difference(image, reference):
    """Return None if ``image`` matches ``reference`` under decision D17's marker rule, else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return "shape or dtype differs"
    differing = np.any(image != reference, axis=2)
    interior = differing & ~reference_edges(reference)
    if interior.any():
        return "%d interior pixels differ" % int(interior.sum())
    if differing.sum() > MAX_EDGE_FRACTION * differing.size:
        return "%d edge pixels differ" % int(differing.sum())
    return None


def assert_landmarks(name, image):
    """Semantic, exact checks: background corners and solid faces at the large markers' centres."""
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8, (name, image.shape)
    assert image[0, 0].tolist() == [0, 0, 0, 255] and image[-1, -1].tolist() == [0, 0, 0, 255], name
    green = np.all(image[..., :3] == (0, 255, 0), axis=2)
    red = np.all(image[..., :3] == (255, 0, 0), axis=2)
    if specification(name)["zoom"] == 1:
        for column, symbol in enumerate(SYMBOLS):  # filled symbols are solid green at the large rows' centres
            if symbol in ("disc", "square", "diamond", "star"):
                assert green[84, 24 + 32 * column] and green[128, 24 + 32 * column], (name, symbol)
        assert red.sum() > 200, (name, int(red.sum()))  # the size-24 markers' 2-px edges
    assert 0.01 * green.size < green.sum() < 0.5 * green.size, (name, int(green.sum()))
