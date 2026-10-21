"""Small scientific scene fixtures with fixed geometry, fonts, and DPI."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (128, 96)
CASES = ("line_gl_segments", "line_agg_round", "line_agg_square", "shapes",
         "mesh_clip", "marker_symbols", "text_dpi96", "text_dpi144", "text_dpi192")
EXACT = {"line_gl_segments", "shapes", "mesh_clip", "marker_symbols",
         "text_dpi96", "text_dpi144", "text_dpi192"}
LINE = np.array([[20, 70], [20, 20], [100, 20]], np.float32)
MARKERS = np.array([[24, 24], [64, 24], [104, 24], [24, 72], [64, 72], [104, 72]], np.float32)
SYMBOLS = ("disc", "square", "diamond", "triangle_up", "cross", "star")


def render(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    import vispy
    from vispy import scene
    from vispy.visuals.filters.clipping_planes import PlanesClipper

    dpi = int(name.removeprefix("text_dpi")) if name.startswith("text_") else 96
    canvas = scene.SceneCanvas(app=backend, size=SIZE, dpi=dpi,
        show=backend == "pyqt6", decorate=False, bgcolor=(0, 0, 0, 1), config={"samples": 0})
    if backend == "pyqt6":
        canvas.app.native.setQuitOnLastWindowClosed(False)
        canvas._backend._vispy_warmup()
    commands, shaders, uploads = [], {}, {}
    parser = canvas.context.shared.parser
    original = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA":
                if isinstance(command[3], str):
                    shaders[str(command[1])] = command[3]
                elif isinstance(command[3], np.ndarray):
                    uploads.setdefault(command[1], []).append((command[2], command[3].copy()))
        return original(batch)

    parser.parse = log
    try:
        params = {"case": name, "size": list(SIZE), "dpi": dpi}
        text = None
        if name == "line_gl_segments":
            pos = np.array([[16, 24], [112, 24], [16, 72], [112, 72]], np.float32)
            scene.visuals.Line(pos=pos, color=(0, 1, 0, 1), method="gl", width=1,
                               antialias=False, connect="segments", parent=canvas.scene)
            params.update(positions=pos.tolist(), width=1, method="gl", connect="segments")
        elif name.startswith("line_agg_"):
            cap = name.removeprefix("line_agg_")
            scene.visuals.Line(pos=LINE, color=(0, 1, 0, 1), method="agg", width=7,
                antialias=True, line_caps=(cap, cap), parent=canvas.scene)
            params.update(positions=LINE.tolist(), width=7, method="agg", caps=[cap, cap])
        elif name == "shapes":
            scene.visuals.Rectangle(center=(24, 24), width=24, height=20,
                color=(1, 0, 0, 1), border_color=None, parent=canvas.scene)
            scene.visuals.Ellipse(center=(88, 24), radius=(16, 10), num_segments=64,
                color=(0, 1, 0, 1), border_color=None, parent=canvas.scene)
            scene.visuals.Polygon(pos=np.array([[20, 80], [44, 52], [60, 80]], np.float32),
                color=(0, 0, 1, 1), border_color=None, triangulate=False, parent=canvas.scene)
            params["geometry"] = "red rectangle, green ellipse64, blue triangle fan"
        elif name == "mesh_clip":
            mesh = scene.visuals.Mesh(vertices=np.array([[16, 16, 0], [112, 16, 0],
                [16, 80, 0], [112, 80, 0]], np.float32),
                faces=np.array([[0, 1, 2], [2, 1, 3]], np.uint32),
                color=(0, 0, 1, 1), shading=None, parent=canvas.scene)
            planes = np.array([[[64, 0, 0], [1, 0, 0]]], np.float32)
            mesh.attach(PlanesClipper(planes, coord_system="visual"))
            params["planes"] = planes.tolist()
        elif name == "marker_symbols":
            markers = scene.visuals.Markers(parent=canvas.scene)
            markers.set_data(MARKERS, size=16, edge_width=2, edge_color=(1, 0, 0, 1),
                face_color=(0, 1, 0, 1), symbol=SYMBOLS)
            params.update(positions=MARKERS.tolist(), symbols=list(SYMBOLS), size=16, edge_width=2)
        else:
            text = scene.visuals.Text("Ag 15", pos=(12, 48), anchor_x="left", anchor_y="baseline",
                color=(1, 1, 1, 1), face="OpenSans", font_size=16, method="cpu", parent=canvas.scene)
            font = Path(vispy.__file__).resolve().parent / "util/fonts/data/OpenSans-Regular.ttf"
            params.update(text="Ag 15", position=[12, 48], face="OpenSans", font_size=16,
                method="cpu", font_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),
                font_license="Apache License, Version 2.0 (font SFNT name ID 13)")
        image = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        extras = {}
        if text is not None:
            atlas = text._font._atlas
            # Reconstruct the CPU-generated atlas from the real upload commands.
            # No second GPU readback is inserted into the fixture.
            array = np.zeros(atlas.shape, np.uint8)
            for offset, patch in uploads[atlas.id]:
                slices = tuple(slice(start, start + count) for start, count in zip(offset, patch.shape))
                array[slices] = patch
            extras["cpu_atlas"] = array
            params["atlas_shape"] = list(array.shape)
            params["glyphs"] = {char: {key: freeze(value) for key, value in glyph.items()
                if key != "bitmap"} for char, glyph in text._font._glyphs.items()}
        return image, commands, shaders, params, extras
    finally:
        canvas.close()


def masks(name, shape):
    """Bands specified from geometry before any candidate capture."""
    y, x = np.mgrid[:shape[0], :shape[1]]
    x, y = x + .5, y + .5
    if name.startswith("line_agg_"):
        distances = []
        for start, end in zip(LINE[:-1], LINE[1:]):
            delta = end - start
            t = np.clip(((x - start[0]) * delta[0] + (y - start[1]) * delta[1]) /
                        np.dot(delta, delta), 0, 1)
            distances.append(np.hypot(x - start[0] - t * delta[0], y - start[1] - t * delta[1]))
        distance = np.minimum.reduce(distances)
        edge = np.abs(distance - 3.5) <= 1
    else:
        edge = np.zeros(shape[:2], bool)
    return ~edge, edge


def assert_landmarks(name, image, extras):
    assert image.shape == (96, 128, 4)
    assert image[2, 2].tolist() == [0, 0, 0, 255]
    if name == "shapes":
        assert image[24, 24].tolist() == [255, 0, 0, 255]
        assert image[24, 88].tolist() == [0, 255, 0, 255]
        assert image[70, 44].tolist() == [0, 0, 255, 255]
    if name == "mesh_clip":
        assert image[48, 32].tolist() == [0, 0, 0, 255]
        assert image[48, 96].tolist() == [0, 0, 255, 255]
    if name.startswith("line_agg_"):
        assert image[20, 64].tolist() == [0, 255, 0, 255]
        assert image[48, 20].tolist() == [0, 255, 0, 255]
    if name == "marker_symbols":
        # Fixed installed-upstream pixel centers, authored before candidate
        # execution. The cross/star SDF yields [2, 253] at the half-pixel sample.
        centers = ([0, 255, 0, 255],) * 4 + ([2, 253, 0, 255],) * 2
        for symbol, (x, y), expected in zip(SYMBOLS, MARKERS.astype(int), centers):
            assert image[y, x].tolist() == expected, (symbol, image[y, x])
    if name.startswith("text_"):
        assert extras["cpu_atlas"].dtype == np.uint8
        # Values above the SDF midpoint denote glyph interiors; antialiased
        # thin strokes need not reach the full unsigned-byte range.
        assert np.max(extras["cpu_atlas"]) > 128, int(np.max(extras["cpu_atlas"]))
        assert np.count_nonzero(image[..., :3]) > 100
    assert np.any(image[..., :3] != 0), "blank scene cannot admit a visual"
