"""Deterministic public-gloo fixtures shared by OpenGL and Dawn.

There is one final color readback per target. No fixture inserts a finish,
capture, or present between dependent draws and updates.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

SIZE = (32, 24)
VERT = """
attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
"""
FRAG = """
uniform vec4 u_color;
void main() { gl_FragColor = u_color; }
"""
TEX_VERT = """
attribute vec2 a_position;
attribute vec2 a_texcoord;
varying vec2 v_texcoord;
void main() {
    v_texcoord = a_texcoord;
    gl_Position = vec4(a_position, 0.0, 1.0);
}
"""
TEX_FRAG = """
uniform sampler2D u_texture;
varying vec2 v_texcoord;
void main() { gl_FragColor = texture2D(u_texture, v_texcoord); }
"""


def rectangle(x0=-1, x1=1, y0=-1, y1=1):
    return np.array([[x0, y0], [x1, y0], [x0, y1],
                     [x0, y1], [x1, y0], [x1, y1]], np.float32)


FULL = rectangle()
LEFT = rectangle(-1, 0)
RIGHT = rectangle(0, 1)
UV = (FULL + 1) / 2


@dataclass(frozen=True)
class Fixture:
    name: str
    operation: str
    edge_columns: tuple[int, ...] = ()
    edge_rows: tuple[int, ...] = ()
    exact: bool = False
    size: tuple[int, int] = SIZE


FIXTURES = {
    name: Fixture(name, operation, cols, rows, exact)
    for name, operation, cols, rows, exact in [
        ("uniform_snapshot", "two colors and transforms before one read", (16,), (), True),
        ("buffer_snapshot", "two buffer generations before one read", (16,), (), True),
        ("texture_snapshot_resize", "filtered resize and two texture generations", (16,), (), True),
        ("framebuffer_sample", "offscreen draw followed by attachment sampling", (), (), True),
        ("shared_canvases", "shared context with independent owned targets", (32,), (), True),
        ("delete_snapshot", "delete vertex buffer after recording its draw", (), (), True),
        ("draw_then_clear", "red draw then blue clear", (), (), True),
        ("clear_then_draw", "blue clear then left red draw", (16,), (), True),
        ("clear_only_fbo", "blue canvas then red clear-only framebuffer", (), (), True),
        ("viewport", "half-width viewport with full geometry", (16,), (), True),
        ("scissor", "center rectangle scissor", (8, 24), (6, 18), True),
        ("indexed_uint8", "four vertices selected by six uint8 indices", (), (), True),
        ("indexed_uint16", "four vertices selected by six uint16 indices", (), (), True),
        ("indexed_uint32", "four vertices selected by six uint32 indices", (), (), True),
        ("interleaved", "structured position/color buffer with field offsets", (), (), True),
        ("constant_attribute", "constant color and buffered positions", (), (), True),
        ("partial_texture", "corner patch preserves outside texels", (8,), (18,), True),
        ("partial_texture_snapshot", "old texture left, patched texture right", (16, 20), (18,), True),
        ("float_texture_clim", "r32f 15 with clim 10..20", (), (), False),
        ("float_texture_range", "r32f values below zero and above one", (8, 16, 24), (), False),
        ("mat2", "non-symmetric column-major mat2 transform", (), (), False),
        ("mat3", "non-symmetric column-major mat3 transform", (), (), False),
        ("mat4", "non-symmetric column-major mat4 transform", (), (), False),
        ("scalar_array", "second and third scalar-array entries", (), (), False),
        ("vector_array", "second vec3-array entry", (), (), False),
        ("matrix_array", "second mat3-array entry", (), (), False),
        ("bool_uniform", "boolean branch with boolean negation", (), (), True),
        ("triangle_strip", "four vertices as triangle_strip", (), (), True),
        ("instanced_divisor1", "two rectangle instances with per-instance offsets", (16,), (), True),
        ("instanced_divisor2", "four instances sharing offsets in pairs", (16,), (), True),
        ("vertex_post_hook", "gl_Position edits after helper returns apply before conversion", (), (12,), True),
        ("nested_framebuffer", "nested deactivation restores the outer attachment", (), (), True),
        ("reattach_snapshot", "pending draw keeps its original attachment", (16,), (), True),
        ("resize_target_snapshot", "pending target/sample keeps the old allocation", (16,), (), True),
        ("delete_target_snapshot", "pending attachment sample survives deletion", (16,), (), True),
        ("blend_separate", "distinct RGB and alpha blend factors", (), (), False),
        ("depth_occlusion", "near geometry occludes a later farther draw", (), (), True),
        ("depth_clear_only", "depth-only clear preserves color and resets depth", (16,), (), True),
        ("color_mask", "per-draw channel write masks", (16,), (), True),
        ("stencil", "first draw writes a stencil mask used by the second", (16,), (), True),
        ("scissor_clear", "clear respects the current scissor rectangle", (8, 24), (6, 18), True),
        ("depth_range", "different depth ranges order two overlapping draws", (), (), True),
        ("msaa4", "asymmetric triangle resolved from actual four-sample target", (), (), False),
        ("cull_frontface", "CCW front-facing draw survives backface culling, CW does not", (16,), (), True),
    ]
}


def freeze(value):
    """JSON-safe filtered GLIR, including exact ndarray payload hashes."""
    if isinstance(value, np.ndarray):
        raw = np.ascontiguousarray(value)
        return {"array": {"dtype": raw.dtype.str, "shape": list(raw.shape),
                          "sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
                          "bytes": raw.nbytes}}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [freeze(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class Runner:
    def __init__(self, backend, samples=0):
        from vispy import app, gloo

        self.app, self.gloo, self.backend = app, gloo, backend
        self.samples = samples
        self.commands, self.shaders, self.canvases = [], {}, []
        self.readbacks = 0

    def canvas(self, shared=None):
        canvas = self.app.Canvas(app=self.backend, size=SIZE, show=self.backend == "pyqt6",
                                 shared=shared, decorate=False,
                                 config={"samples": self.samples, "stencil_size": 8})
        self.canvases.append(canvas)
        if self.backend == "pyqt6":
            canvas._backend._vispy_warmup()
        canvas.set_current()
        parser = canvas.context.shared.parser
        if not getattr(parser, "_fixture_logging", False):
            original = parser.parse

            def parse(commands):
                for command in commands:
                    self.commands.append(freeze(command))
                    if command[0] == "DATA" and isinstance(command[3], str):
                        self.shaders[str(command[1])] = command[3]
                return original(commands)

            parser.parse = parse
            parser._fixture_logging = True
        self.gloo.set_viewport(0, 0, *SIZE)
        self.gloo.set_state(blend=False, depth_test=False, scissor_test=False,
                            cull_face=False)
        self.clear((0, 0, 0, 1))
        return canvas

    def clear(self, color):
        self.gloo.set_clear_color(color)
        self.gloo.clear(color=True, depth=False, stencil=False)

    def solid(self, positions=FULL, color=(1, 0, 0, 1), vert=VERT, frag=FRAG):
        program = self.gloo.Program(vert, frag)
        program["a_position"] = self.gloo.VertexBuffer(positions)
        if "u_color" in program:
            program["u_color"] = color
        return program

    def textured(self, texture, positions=FULL, frag=TEX_FRAG):
        program = self.gloo.Program(TEX_VERT, frag)
        program["a_position"] = self.gloo.VertexBuffer(positions)
        program["a_texcoord"] = self.gloo.VertexBuffer(UV)
        program["u_texture"] = texture
        return program

    def read(self):
        self.readbacks += 1
        if self.samples and self.backend == "pyqt6":
            # Qt owns the OpenGL default framebuffer's multisample resolve.
            from PyQt6.QtGui import QImage

            assert int(self.gloo.gl.glGetParameter(32937)) == self.samples
            qimage = self.canvases[-1].native.grabFramebuffer().convertToFormat(QImage.Format.Format_RGBA8888)
            pointer = qimage.bits()
            pointer.setsize(qimage.sizeInBytes())
            raw = np.frombuffer(pointer, np.uint8).reshape(qimage.height(), qimage.bytesPerLine())
            rgba = raw[:, :qimage.width() * 4].reshape(qimage.height(), qimage.width(), 4)
            # Match gloo.read_pixels' declared bottom-left viewport crop even
            # when the desktop scales the physical Qt target above SIZE.
            return rgba[-SIZE[1]:, :SIZE[0]].copy()
        return self.gloo.read_pixels((0, 0, *SIZE), alpha=True).copy()

    def close(self):
        for canvas in reversed(self.canvases):
            canvas.close()


def render(name, backend="dawn_headless"):
    """Return RGBA, filtered GLIR, expanded gloo sources, and readback count."""
    if name not in FIXTURES:
        raise ValueError(name)
    r = Runner(backend, samples=4 if name == "msaa4" else 0)
    gloo = r.gloo
    canvas = r.canvas()
    try:
        if name == "uniform_snapshot":
            p = r.solid(LEFT, vert="""
                attribute vec2 a_position;
                uniform vec2 u_shift;
                void main() { gl_Position = vec4(a_position + u_shift, 0.0, 1.0); }
                """)
            p["u_shift"] = (0, 0)
            p.draw("triangles")
            p["u_shift"] = (1, 0)
            p["u_color"] = (0, 1, 0, 1)
            p.draw("triangles")
        elif name == "buffer_snapshot":
            p = r.solid(LEFT)
            p.draw("triangles")
            p["a_position"].set_data(RIGHT)
            p["u_color"] = (0, 1, 0, 1)
            p.draw("triangles")
        elif name == "texture_snapshot_resize":
            tex = gloo.Texture2D(np.full((2, 2, 4), [0, 0, 255, 255], np.uint8))
            tex.set_data(np.array([[[255, 0, 0, 255]]], np.uint8))
            p = r.textured(tex, LEFT)
            p.draw("triangles")
            tex.set_data(np.array([[[0, 255, 0, 255]]], np.uint8))
            p["a_position"].set_data(RIGHT)
            p.draw("triangles")
        elif name in ("framebuffer_sample", "clear_only_fbo"):
            tex = gloo.Texture2D(shape=(SIZE[1], SIZE[0], 4))
            fbo = gloo.FrameBuffer(color=tex)
            r.clear((0, 0, 1, 1))
            with fbo:
                r.clear((1, 0, 0, 1))
                if name == "framebuffer_sample":
                    r.solid(color=(0, 1, 0, 1)).draw("triangles")
            if name == "framebuffer_sample":
                r.textured(tex).draw("triangles")
        elif name == "shared_canvases":
            second = r.canvas(shared=canvas.context)
            canvas.set_current()
            r.clear((0, 0, 0, 1))
            r.solid().draw("triangles")
            second.set_current()
            r.solid(color=(0, 0, 1, 1)).draw("triangles")
            blue = r.read()
            canvas.set_current()
            red = r.read()
            image = np.concatenate((red, blue), axis=1)
            return image, r.commands, r.shaders, r.readbacks
        elif name == "delete_snapshot":
            p = r.solid(color=(0, 1, 0, 1))
            p.draw("triangles")
            p["a_position"].delete()
        elif name == "draw_then_clear":
            r.solid().draw("triangles")
            r.clear((0, 0, 1, 1))
        elif name == "clear_then_draw":
            r.clear((0, 0, 1, 1))
            r.solid(LEFT).draw("triangles")
        elif name == "viewport":
            gloo.set_viewport(0, 0, SIZE[0] // 2, SIZE[1])
            r.solid().draw("triangles")
        elif name == "scissor":
            gloo.set_scissor(8, 6, 16, 12)
            gloo.set_state(scissor_test=True)
            r.solid().draw("triangles")
        elif name.startswith("indexed_"):
            positions = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32)
            indices = np.array([0, 1, 2, 2, 1, 3], dtype=name.split("_")[1])
            r.solid(positions, (0, 1, 0, 1)).draw("triangles", gloo.IndexBuffer(indices))
        elif name == "interleaved":
            data = np.zeros(6, dtype=[("a_position", np.float32, 2),
                                      ("padding", np.float32, 3),
                                      ("a_color", np.float32, 4)])
            data["a_position"] = FULL
            data["padding"] = -999
            data["a_color"] = (0, 1, 0, 1)
            p = gloo.Program("""
                attribute vec2 a_position;
                attribute vec4 a_color;
                varying vec4 v_color;
                void main() { v_color = a_color; gl_Position = vec4(a_position, 0, 1); }
                """, "varying vec4 v_color; void main() { gl_FragColor = v_color; }")
            buf = gloo.VertexBuffer(data)
            p["a_position"] = buf["a_position"]
            p["a_color"] = buf["a_color"]
            p.draw("triangles")
        elif name == "constant_attribute":
            p = gloo.Program("""
                attribute vec2 a_position;
                attribute vec4 a_color;
                varying vec4 v_color;
                void main() { v_color = a_color; gl_Position = vec4(a_position, 0, 1); }
                """, "varying vec4 v_color; void main() { gl_FragColor = v_color; }")
            p["a_position"] = gloo.VertexBuffer(FULL)
            p["a_color"] = (0, 1, 0, 1)
            p.draw("triangles")
        elif name in ("partial_texture", "partial_texture_snapshot"):
            tex = gloo.Texture2D(np.full((4, 4, 4), [255, 0, 0, 255], np.uint8),
                                 interpolation="nearest")
            p = r.textured(tex, LEFT if name.endswith("snapshot") else FULL)
            if name.endswith("snapshot"):
                p.draw("triangles")
                p["a_position"].set_data(RIGHT)
            tex.set_data(np.array([[[0, 255, 0, 255]]], np.uint8), offset=(0, 0))
            p.draw("triangles")
        elif name in ("float_texture_clim", "float_texture_range"):
            data = np.array([[15]], np.float32) if name.endswith("clim") else np.array([[-10, 0, 10, 20]], np.float32)
            tex = gloo.Texture2D(data, internalformat="r32f", interpolation="nearest")
            frag = """
                uniform sampler2D u_texture;
                varying vec2 v_texcoord;
                uniform vec2 u_clim;
                void main() {
                    float value = (texture2D(u_texture, v_texcoord).r - u_clim.x) / (u_clim.y - u_clim.x);
                    gl_FragColor = vec4(value, value, value, 1.0);
                }
                """
            p = r.textured(tex, frag=frag)
            p["u_clim"] = (10, 20) if name.endswith("clim") else (-10, 20)
            p.draw("triangles")
        elif name in ("mat2", "mat3", "mat4", "matrix_array"):
            dim = 3 if name == "matrix_array" else int(name[-1])
            vector = "vec%d(%s)" % (dim, ",".join("1.0" for _ in range(dim)))
            declaration = f"uniform mat{dim} u_matrix" + ("[2]" if name == "matrix_array" else "") + ";"
            expr = ("u_matrix[1]" if name == "matrix_array" else "u_matrix") + " * " + vector
            frag = declaration + f"\nvoid main() {{ vec{dim} v = {expr}; gl_FragColor = vec4(v.x, v.y, 0.0, 1.0); }}"
            p = r.solid(frag=frag)
            # OpenGL consumes columns in the flattened public uniform input.
            matrix = np.zeros((dim, dim), np.float32)
            matrix[0, 0], matrix[1, 0], matrix[0, 1], matrix[1, 1] = .2, .3, .1, .3
            if name == "matrix_array":
                p["u_matrix[0]"] = np.zeros_like(matrix)
                p["u_matrix[1]"] = matrix
            else:
                p["u_matrix"] = matrix
            p.draw("triangles")
        elif name in ("scalar_array", "vector_array"):
            frag = """
                uniform float u_values[3];
                void main() { gl_FragColor = vec4(u_values[1], u_values[2], 0.0, 1.0); }
                """ if name == "scalar_array" else """
                uniform vec3 u_values[2];
                void main() { gl_FragColor = vec4(u_values[1], 1.0); }
                """
            p = r.solid(frag=frag)
            p["u_values"] = np.array([[0], [.5], [.75]], np.float32) if name == "scalar_array" else np.array([[0, 0, 0], [.25, .5, .75]], np.float32)
            p.draw("triangles")
        elif name == "bool_uniform":
            p = r.solid(frag="""
                uniform bool u_flag;
                uniform bool u_other;
                void main() {
                    if (u_flag && !u_other) gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0);
                    else gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
                }
                """)
            p["u_flag"], p["u_other"] = True, False
            p.draw("triangles")
        elif name == "triangle_strip":
            r.solid(np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32),
                    (0, 1, 0, 1)).draw("triangle_strip")
        elif name.startswith("instanced_divisor"):
            p = gloo.Program("""
                attribute vec2 a_position;
                attribute vec2 a_offset;
                void main() { gl_Position = vec4(a_position + a_offset, 0.0, 1.0); }
                """, FRAG)
            p["a_position"] = gloo.VertexBuffer(LEFT)
            offsets = gloo.VertexBuffer(np.array([[0, 0], [1, 0]], np.float32))
            offsets.divisor = int(name[-1])
            p["a_offset"] = offsets
            p["u_color"] = (0, 1, 0, 1)
            p.draw("triangles")
        elif name == "vertex_post_hook":
            p = r.solid(color=(0, 1, 0, 1), vert="""
                attribute vec2 a_position;
                void position() { gl_Position = vec4(a_position, 0.0, 1.0); }
                void main() {
                    position();
                    gl_Position.y *= 0.5;
                    gl_Position.y += 0.5;
                }
                """)
            p.draw("triangles")
        elif name in ("nested_framebuffer", "reattach_snapshot", "resize_target_snapshot", "delete_target_snapshot"):
            tex = gloo.Texture2D(shape=(SIZE[1], SIZE[0], 4))
            other = gloo.Texture2D(shape=(SIZE[1], SIZE[0], 4))
            outer, inner = gloo.FrameBuffer(color=tex), gloo.FrameBuffer(color=other)
            with outer:
                r.solid().draw("triangles")
                if name == "nested_framebuffer":
                    with inner:
                        r.solid(color=(0, 1, 0, 1)).draw("triangles")
                    r.solid(color=(0, 0, 1, 1)).draw("triangles")
            if name == "nested_framebuffer":
                r.textured(tex).draw("triangles")
            elif name == "reattach_snapshot":
                outer.color_buffer = other
                with outer:
                    r.solid(color=(0, 1, 0, 1)).draw("triangles")
                r.textured(tex, LEFT).draw("triangles")
                r.textured(other, RIGHT).draw("triangles")
            else:
                r.textured(tex, LEFT).draw("triangles")
                if name == "resize_target_snapshot":
                    tex.resize((SIZE[1], SIZE[0], 4))
                    with outer:
                        r.solid(color=(0, 1, 0, 1)).draw("triangles")
                    r.textured(tex, RIGHT).draw("triangles")
                else:
                    tex.delete()
                    outer.delete()
                    r.solid(RIGHT, color=(0, 1, 0, 1)).draw("triangles")
        elif name == "blend_separate":
            r.clear((.25, .5, .75, .5))
            gloo.set_state(blend=True)
            gloo.set_blend_func("src_alpha", "one_minus_src_alpha", "one", "one_minus_src_alpha")
            r.solid(color=(.8, .4, .2, .25)).draw("triangles")
        elif name in ("depth_occlusion", "depth_clear_only", "depth_range"):
            gloo.clear(color=False, depth=True, stencil=False)
            gloo.set_state(depth_test=True)
            gloo.set_depth_func("less")
            p = r.solid(vert="""
                attribute vec2 a_position;
                uniform float u_depth;
                void main() { gl_Position = vec4(a_position, u_depth, 1.0); }
                """)
            if name == "depth_range":
                gloo.set_depth_range(.6, .9)
            p["u_depth"] = -.5
            p.draw("triangles")
            if name == "depth_clear_only":
                gloo.set_clear_depth(1)
                gloo.clear(color=False, depth=True, stencil=False)
                p["a_position"].set_data(LEFT)
            elif name == "depth_range":
                gloo.set_depth_range(0, 1)
            p["u_depth"] = 0 if name == "depth_range" else .5
            p["u_color"] = (0, 1, 0, 1)
            p.draw("triangles")
        elif name == "color_mask":
            r.clear((0, 0, 1, 1))
            gloo.set_color_mask(True, False, False, False)
            r.solid(LEFT, color=(1, 1, 1, 1)).draw("triangles")
            gloo.set_color_mask(False, True, False, False)
            r.solid(RIGHT, color=(1, 1, 1, 1)).draw("triangles")
        elif name == "stencil":
            gloo.set_clear_stencil(0)
            gloo.clear(color=False, depth=False, stencil=True)
            gloo.set_state(stencil_test=True)
            gloo.set_stencil_mask(255)
            gloo.set_stencil_func("always", 1, 255)
            gloo.set_stencil_op("keep", "keep", "replace")
            gloo.set_color_mask(False, False, False, False)
            r.solid(LEFT).draw("triangles")
            gloo.set_color_mask(True, True, True, True)
            gloo.set_stencil_func("equal", 1, 255)
            gloo.set_stencil_op("keep", "keep", "keep")
            r.solid(color=(0, 1, 0, 1)).draw("triangles")
        elif name == "scissor_clear":
            r.solid(color=(0, 0, 1, 1)).draw("triangles")
            gloo.set_scissor(8, 6, 16, 12)
            gloo.set_state(scissor_test=True)
            r.clear((1, 0, 0, 1))
        elif name == "msaa4":
            pixels = np.array([[3, 3], [29, 21], [3, 21]], np.float32)
            positions = pixels * np.array([2 / SIZE[0], -2 / SIZE[1]], np.float32) + np.array([-1, 1], np.float32)
            p = r.solid(positions, color=(0, 1, 0, 1))

            def draw(event):
                gloo.set_viewport(0, 0, *SIZE)
                r.clear((0, 0, 0, 1))
                p.draw("triangles")

            canvas.events.draw.connect(draw)
            draw(None)
        elif name == "cull_frontface":
            gloo.set_state(cull_face=True)
            gloo.set_cull_face("back")
            gloo.set_front_face("ccw")
            r.solid(LEFT, color=(0, 1, 0, 1)).draw("triangles")
            gloo.set_front_face("cw")
            r.solid(RIGHT, color=(0, 1, 0, 1)).draw("triangles")
        image = r.read()
        return image, r.commands, r.shaders, r.readbacks
    finally:
        r.close()


def comparison_masks(name, shape):
    """One-pixel bands are fixed from fixture geometry before candidate capture."""
    fixture = FIXTURES[name]
    height, width = shape[:2]
    edge = np.zeros((height, width), bool)
    for x in fixture.edge_columns:
        edge[:, max(0, x - 1):min(width, x + 1)] = True
    for y in fixture.edge_rows:
        edge[max(0, y - 1):min(height, y + 1), :] = True
    if name == "msaa4":
        y, x = np.mgrid[:height, :width]
        x, y = x + .5, y + .5
        # Distance to the three prescribed edges in physical pixel space.
        edge = (np.abs(x - 3) <= 1) | (np.abs(y - 21) <= 1)
        edge |= np.abs(18 * (x - 3) - 26 * (y - 3)) / np.sqrt(18**2 + 26**2) <= 1
    return ~edge, edge


def assert_numeric_landmarks(name, image):
    """Checks scientifically meaningful results in addition to reference parity."""
    center = image[SIZE[1] // 2, SIZE[0] // 2]
    if name == "float_texture_clim":
        assert np.max(np.abs(center[:3].astype(int) - 128)) <= 1, center
    elif name == "float_texture_range":
        for column, value in zip((4, 12, 20, 28), (0, 85, 170, 255)):
            assert np.max(np.abs(image[12, column, :3].astype(int) - value)) <= 1
    elif name in ("mat2", "mat3", "mat4", "matrix_array"):
        assert np.max(np.abs(center[:2].astype(int) - [128, 102])) <= 1, center
    elif name == "scalar_array":
        assert np.max(np.abs(center[:3].astype(int) - [128, 191, 0])) <= 1, center
    elif name == "vector_array":
        assert np.max(np.abs(center[:3].astype(int) - [64, 128, 191])) <= 1, center
    elif name == "partial_texture":
        assert image[21, 4].tolist() == [0, 255, 0, 255]
        assert image[3, 28].tolist() == [255, 0, 0, 255]
    elif name == "partial_texture_snapshot":
        assert image[21, 4].tolist() == [255, 0, 0, 255]
        assert image[21, 18].tolist() == [0, 255, 0, 255]
        assert image[3, 28].tolist() == [255, 0, 0, 255]


def expected_image(name):
    """Analytic landmarks/regions, fixed without observing candidate pixels."""
    width, height = SIZE
    image = np.empty((height, width * (2 if name == "shared_canvases" else 1), 4), np.uint8)
    image[:] = [0, 0, 0, 255]
    red, green, blue = [255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255]
    if name in ("uniform_snapshot", "buffer_snapshot", "texture_snapshot_resize", "reattach_snapshot",
                "resize_target_snapshot", "delete_target_snapshot"):
        image[:, :16], image[:, 16:] = red, green
    elif name in ("framebuffer_sample", "delete_snapshot", "indexed_uint8", "indexed_uint16",
                  "indexed_uint32", "interleaved", "constant_attribute", "bool_uniform",
                  "triangle_strip", "instanced_divisor1", "instanced_divisor2"):
        image[:] = green
    elif name == "shared_canvases":
        image[:, :32], image[:, 32:] = red, blue
    elif name in ("draw_then_clear", "clear_only_fbo", "nested_framebuffer"):
        image[:] = blue
    elif name == "clear_then_draw":
        image[:, :16], image[:, 16:] = red, blue
    elif name == "viewport":
        image[:, :16] = red
    elif name == "scissor":
        image[6:18, 8:24] = red
    elif name == "vertex_post_hook":
        image[:12] = green
    elif name == "blend_separate":
        image[:] = [99, 122, 156, 160]
    elif name == "depth_occlusion":
        image[:] = red
    elif name == "depth_clear_only":
        image[:, :16], image[:, 16:] = green, red
    elif name == "depth_range":
        image[:] = green
    elif name == "color_mask":
        image[:, :16], image[:, 16:] = [255, 0, 255, 255], [0, 255, 255, 255]
    elif name in ("stencil", "cull_frontface"):
        image[:, :16] = green
    elif name == "scissor_clear":
        image[:] = blue
        image[6:18, 8:24] = red
    elif name == "msaa4":
        y, x = np.mgrid[:height, :width]
        x, y = x + .5, y + .5
        inside = (x >= 3) & (y <= 21) & (18 * (x - 3) <= 26 * (y - 3))
        image[inside] = green
    elif name in ("partial_texture", "partial_texture_snapshot"):
        image[:] = red
        image[18:, 16:20] = green if name.endswith("snapshot") else red
        if name == "partial_texture":
            image[18:, :8] = green
    elif name == "float_texture_clim":
        image[:] = [128, 128, 128, 255]
    elif name == "float_texture_range":
        for block, value in enumerate((0, 85, 170, 255)):
            image[:, block * 8:(block + 1) * 8] = [value, value, value, 255]
    elif name in ("mat2", "mat3", "mat4", "matrix_array"):
        image[:] = [128, 102, 0, 255]
    elif name == "scalar_array":
        image[:] = [128, 191, 0, 255]
    elif name == "vector_array":
        image[:] = [64, 128, 191, 255]
    else:
        raise ValueError(name)
    return image


def assert_expected_regions(name, image):
    expected = expected_image(name)
    assert image.shape == expected.shape
    difference = np.abs(image.astype(np.int16) - expected.astype(np.int16))
    tolerance = 0 if FIXTURES[name].exact else 1
    if name == "msaa4":
        interior, _ = comparison_masks(name, image.shape)
        difference = difference[interior]
    assert difference.max() <= tolerance, (name, int(difference.max()),
        np.unique(image.reshape(-1, 4), axis=0).tolist())
