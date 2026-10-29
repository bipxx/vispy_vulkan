"""One million fixed-seed markers in one Markers visual (W5, M06).

A 1280x720 black scene canvas without a camera draws 1,000,000 markers from a fixed seed: positions over the canvas,
sizes 2-8 px, edge width 0-1, opaque random face colours, white edges and a mix of the fifteen symbols, in buffer
order. The cases are the two drawing methods with antialiasing on.

Every case uses decision D17's documented difference (user, 2026-10-29, under D4), fixed before this capture: at most
0.5% of the frame's pixels may differ by more than 2 levels, and every other pixel stays within 2. An earlier exact
capture measured 1-2 level differences on fractional point sizes (OpenGL appears to quantize sprite size) and 0.24% of
pixels differing by more, through equal-depth occlusion in the dense overlap.
"""
from __future__ import annotations

import hashlib

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (1280, 720)
COUNT = 1_000_000
SEED = 20261029
SYMBOLS = ("arrow", "clobber", "cross", "cross_lines", "diamond", "disc", "hbar", "ring", "square", "star",
           "tailed_arrow", "triangle_down", "triangle_up", "vbar", "x")
CASES = ("points", "instanced")
CRITERIA = {name: "within_2_levels" for name in CASES}  # decision D17
LEVELS, MAX_BEYOND_FRACTION = 2, .005


def markers():
    rng = np.random.default_rng(SEED)
    positions = (rng.random((COUNT, 2)) * np.asarray(SIZE)).astype(np.float32)
    sizes = rng.uniform(2, 8, COUNT).astype(np.float32)
    edges = rng.uniform(0, 1, COUNT).astype(np.float32)
    faces = np.concatenate([rng.random((COUNT, 3)), np.ones((COUNT, 1))], axis=1).astype(np.float32)
    symbols = rng.integers(0, len(SYMBOLS), COUNT)
    return positions, sizes, edges, faces, [SYMBOLS[index] for index in symbols]


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    positions, sizes, edges, faces, symbols = markers()
    digest = hashlib.sha256()
    for array in (positions, sizes, edges, faces):
        digest.update(array.tobytes())
    digest.update(",".join(symbols).encode())
    return {"case": name, "size": list(SIZE), "count": COUNT, "seed": SEED, "method": name, "antialias": 1.,
            "scaling": "fixed", "edge_color": [1., 1., 1., 1.], "criterion": CRITERIA[name],
            "inputs_sha256": digest.hexdigest()}


def render(name, backend="dawn_headless"):
    """Draw the million markers once and read the frame."""
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
        positions, sizes, edges, faces, symbols = markers()
        visual = scene.visuals.Markers(parent=canvas.scene, method=params["method"], scaling="fixed", antialias=1.)
        visual.set_data(pos=positions, size=sizes, edge_width=edges, face_color=faces, edge_color=(1, 1, 1, 1),
                        symbol=symbols)
        image = np.array(canvas.render(alpha=True), copy=True)
        return image, commands, shaders, params
    finally:
        parser.parse = original
        canvas.close()


def difference(image, reference):
    """Return None if ``image`` matches ``reference`` under decision D17's million-marker rule, else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return "shape or dtype differs"
    beyond = np.any(np.abs(image.astype(np.int16) - reference.astype(np.int16)) > LEVELS, axis=2)
    if beyond.sum() > MAX_BEYOND_FRACTION * beyond.size:
        return "%d pixels differ by more than %d levels" % (int(beyond.sum()), LEVELS)
    return None


def assert_landmarks(name, image):
    """Semantic checks: the frame is dense with many distinct markers (antialiased blending also lowers alpha)."""
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8, (name, image.shape)
    covered = np.any(image[..., :3] > 0, axis=2)
    assert covered.mean() > 0.9, (name, float(covered.mean()))  # a million markers cover nearly every pixel
    assert len(np.unique(image[::8, ::8, :3].reshape(-1, 3), axis=0)) > 1000, name
