"""Non-standard attribute strides, offsets, divisors, and attribute-limit boundaries (SHD-03).

Verifies structured interleaved VertexBuffer views with >2048-byte strides
(exercising compact_layout), mat2 column attributes, constant scalar/vector
attributes, divisor=1/2/3 instanced tile stepping, mismatched size/divisor
diagnostics, and >max_vertex_attributes polygon refusal vs wide-line compute
admission with same-canvas recovery.
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@contextmanager
def _headless_canvas(size=(24, 8)):
    from vispy import _dawn, app, gloo

    canvas = app.Canvas(app="dawn_headless", size=size, show=False)
    canvas.set_current()
    objects = []
    try:
        gloo.set_viewport(0, 0, size[0], size[1])
        yield canvas, gloo, _dawn, objects
    finally:
        for obj in reversed(objects):
            try:
                obj.delete()
            except Exception:
                pass
        try:
            gloo.flush()
        except Exception:
            pass
        canvas.close()
        _dawn.process_events()


def test_oversized_stride_structured_views_matrix_attributes_and_multi_divisors():
    with _headless_canvas(size=(24, 8)) as (_canvas, gloo, _dawn, objects):
        # Structured dtype with 2100-byte stride (> max_vertex_buffer_array_stride == 2048) + non-zero field offsets!
        rec_dtype = np.dtype(
            [
                ("pad0", np.uint8, (12,)),
                ("pos", np.float32, (2,)),
                ("pad1", np.uint8, (2076,)),
                ("shade", np.float32, (1,)),
            ]
        )
        assert rec_dtype.itemsize == 2100
        raw = np.zeros(4, dtype=rec_dtype)
        # Unit tile spanning [0, 1] x [-1, 1]; divisor=1 x-offset places 6 horizontal tiles across [-1, 1].
        raw["pos"] = np.array(
            [[0.0, -1.0], [1.0 / 3.0, -1.0], [0.0, 1.0], [1.0 / 3.0, 1.0]],
            dtype=np.float32,
        )
        raw["shade"] = 1.0
        structured_vbo = gloo.VertexBuffer(raw)
        objects.append(structured_vbo)

        # 6 instances: divisor=1 x-shift (6 items), divisor=2 red channel (3 items), divisor=3 green channel (2 items).
        x_offsets = gloo.VertexBuffer(
            np.array([-1.0 + i * (1.0 / 3.0) for i in range(6)], dtype=np.float32),
            divisor=1,
        )
        red_div2 = gloo.VertexBuffer(
            np.array([0.25, 0.50, 1.00], dtype=np.float32),
            divisor=2,
        )
        green_div3 = gloo.VertexBuffer(
            np.array([0.25, 0.75], dtype=np.float32),
            divisor=3,
        )
        # Per-instance mat2 attribute (divisor=1) packed as (6, 4) column-major identity vectors.
        basis_div1 = gloo.VertexBuffer(
            np.tile(np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32), (6, 1)),
            divisor=1,
        )
        objects.extend([x_offsets, red_div2, green_div3, basis_div1])

        prog = gloo.Program(
            """
            attribute vec2 a_pos;
            attribute float a_shade;
            attribute float a_xoff;
            attribute float a_red;
            attribute float a_green;
            attribute float a_blue_const;
            attribute mat2 a_basis;
            varying vec4 v_color;
            void main() {
                vec2 p = a_basis * a_pos + vec2(a_xoff, 0.0);
                v_color = vec4(a_red * a_shade, a_green * a_shade, a_blue_const, 1.0);
                gl_Position = vec4(p, 0.0, 1.0);
            }
            """,
            "varying vec4 v_color; void main() { gl_FragColor = v_color; }",
        )
        objects.append(prog)
        prog["a_pos"] = structured_vbo["pos"]
        prog["a_shade"] = structured_vbo["shade"]
        prog["a_xoff"] = x_offsets
        prog["a_red"] = red_div2
        prog["a_green"] = green_div3
        prog["a_blue_const"] = 0.5
        prog["a_basis"] = basis_div1

        gloo.set_state(blend=False, depth_test=False, cull_face=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        img = gloo.read_pixels((0, 0, 24, 8), alpha=True)

        expected_reds = [64, 64, 128, 128, 255, 255]
        expected_greens = [64, 64, 64, 191, 191, 191]
        for tile in range(6):
            cx = tile * 4 + 2
            np.testing.assert_allclose(
                img[4, cx],
                [expected_reds[tile], expected_greens[tile], 128, 255],
                atol=2,
            )


def test_attribute_count_divisor_mismatch_and_max_vertex_attributes_boundaries():
    with _headless_canvas(size=(12, 8)) as (_canvas, gloo, _dawn, objects):
        # 1. Mismatched per-vertex attribute lengths and mismatched divisor * size refuse cleanly and recover.
        prog = gloo.Program(
            "attribute vec2 a_pos; attribute vec3 a_col; attribute float a_inst_a; attribute float a_inst_b; "
            "varying vec3 v_col; void main() { v_col = a_col + vec3(a_inst_a + a_inst_b); gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "varying vec3 v_col; void main() { gl_FragColor = vec4(clamp(v_col, 0.0, 1.0), 1.0); }",
        )
        v_pos3 = gloo.VertexBuffer(np.array([[-1.0, -1.0], [1.0, -1.0], [0.0, 1.0]], dtype=np.float32))
        v_col4 = gloo.VertexBuffer(np.ones((4, 3), dtype=np.float32))
        v_col3 = gloo.VertexBuffer(np.full((3, 3), [0.25, 0.5, 0.75], dtype=np.float32))
        i_a2 = gloo.VertexBuffer(np.zeros(2, dtype=np.float32), divisor=1)
        i_b3 = gloo.VertexBuffer(np.zeros(3, dtype=np.float32), divisor=1)
        i_b1_div2 = gloo.VertexBuffer(np.zeros(1, dtype=np.float32), divisor=2)
        objects.extend([prog, v_pos3, v_col4, v_col3, i_a2, i_b3, i_b1_div2])

        prog["a_pos"] = v_pos3
        prog["a_col"] = v_col4
        prog["a_inst_a"] = i_a2
        prog["a_inst_b"] = i_b1_div2
        with pytest.raises(RuntimeError, match="All attributes must have the same size"):
            prog.draw("triangles")

        prog["a_col"] = v_col3
        prog["a_inst_b"] = i_b3
        with pytest.raises(RuntimeError, match="All attributes with divisors must have the same size"):
            prog.draw("triangles")

        prog["a_inst_b"] = i_b1_div2
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangles")
        np.testing.assert_allclose(
            gloo.read_pixels((0, 0, 12, 8), alpha=True)[6, 6], [64, 128, 191, 255], atol=2
        )

        # 2. Active attributes exceeding max_vertex_attributes: polygon draw refuses; wide lines succeed via compute storage!
        max_attrs = int(_dawn.device_info()["max_vertex_attributes"])
        over = max_attrs + 2
        decls = "\n".join(f"attribute float a_{k};" for k in range(over))
        expr = " + ".join(f"a_{k}" for k in range(over))
        many_prog = gloo.Program(
            f"""
            attribute vec2 a_xy;
            {decls}
            varying float v_sum;
            void main() {{
                v_sum = ({expr}) / float({over});
                gl_Position = vec4(a_xy, 0.0, 1.0);
            }}
            """,
            "varying float v_sum; void main() { gl_FragColor = vec4(clamp(v_sum, 0.0, 1.0), 0.25, 0.5, 1.0); }",
        )
        objects.append(many_prog)
        line_xy = gloo.VertexBuffer(
            np.array([[-0.9, 0.0], [0.9, 0.0], [0.0, 0.9]], dtype=np.float32)
        )
        ones_vbo = gloo.VertexBuffer(np.ones(3, dtype=np.float32))
        objects.extend([line_xy, ones_vbo])
        many_prog["a_xy"] = line_xy
        for k in range(over):
            many_prog[f"a_{k}"] = ones_vbo

        with pytest.raises(RuntimeError, match="exceed granted attribute limit"):
            many_prog.draw("triangles")

        # Wide lines evaluate endpoints in compute storage without consuming hardware vertex input slots!
        gloo.set_line_width(4.0)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        many_prog.draw("line_strip")
        line_img = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        np.testing.assert_allclose(line_img[4, 6], [255, 64, 128, 255], atol=3)
        gloo.set_line_width(1.0)
        _dawn.shutdown()
