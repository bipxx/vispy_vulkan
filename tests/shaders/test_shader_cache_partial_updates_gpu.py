"""Partial uniform/buffer array updates, ModularProgram rebuilds, and shader cache limits (SHD-02).

Verifies indexed uniform array / matrix-array / integer-vector updates without
recompilation, partial VertexBuffer and IndexBuffer sub-range mutations,
ModularProgram / MultiProgram Variable value updates vs Function code-change
cache invalidation, and bounded _dawn.configure_shader_cache eviction recovery.
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@contextmanager
def _headless_canvas(size=(16, 8)):
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


def test_partial_uniform_array_matrix_and_buffer_subrange_mutations():
    with _headless_canvas(size=(16, 8)) as (_canvas, gloo, _dawn, objects):
        quad = gloo.VertexBuffer(
            np.array(
                [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]], dtype=np.float32
            )
        )
        uv = gloo.VertexBuffer(
            np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float32)
        )
        ibo = gloo.IndexBuffer(np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32))
        objects.extend([quad, uv, ibo])

        prog = gloo.Program(
            """
            attribute vec2 a_pos;
            attribute vec2 a_uv;
            varying vec2 v_uv;
            void main() {
                v_uv = a_uv;
                gl_Position = vec4(a_pos, 0.0, 1.0);
            }
            """,
            """
            uniform vec4 u_colors[4];
            uniform mat2 u_mats[2];
            uniform ivec2 u_tags[2];
            varying vec2 v_uv;
            void main() {
                int band = int(clamp(floor(v_uv.x * 4.0), 0.0, 3.0));
                vec4 base = (band == 0) ? u_colors[0]
                          : (band == 1) ? u_colors[1]
                          : (band == 2) ? u_colors[2]
                                        : u_colors[3];
                vec2 scaled = (band < 2) ? (u_mats[0] * vec2(1.0, 0.0))
                                         : (u_mats[1] * vec2(1.0, 0.0));
                float tag_alpha = (u_tags[1].x == 42) ? 1.0 : 0.25;
                gl_FragColor = vec4(clamp(base.rgb * scaled.x, 0.0, 1.0), tag_alpha);
            }
            """,
        )
        objects.append(prog)
        prog["a_pos"] = quad
        prog["a_uv"] = uv
        prog["u_colors"] = np.array(
            [
                [1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 1.0],
                [0.0, 0.0, 1.0, 1.0],
                [1.0, 1.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        prog["u_mats"] = np.array(
            [[1.0, 0.0, 0.0, 1.0], [0.5, 0.0, 0.0, 1.0]], dtype=np.float32
        )
        prog["u_tags"] = np.array([[7, 8], [42, 99]], dtype=np.int32)

        gloo.set_state(blend=False, depth_test=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 0.0))
        prog.draw("triangles", ibo)
        img0 = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        misses_before = _dawn.probe()["portable_shader_misses"]

        np.testing.assert_allclose(img0[4, 2], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(img0[4, 6], [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(img0[4, 10], [0, 0, 128, 255], atol=2)
        np.testing.assert_allclose(img0[4, 14], [128, 128, 0, 255], atol=2)

        # Partial element updates mutate only band 2 color and right-half matrix scale, with zero shader recompiles.
        prog["u_colors[2]"] = np.array([0.0, 1.0, 1.0, 1.0], dtype=np.float32)
        prog["u_mats[1]"] = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        prog["u_tags[1]"] = np.array([9, 99], dtype=np.int32)
        gloo.clear(color=(0.0, 0.0, 0.0, 0.0))
        prog.draw("triangles", ibo)
        img1 = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        assert _dawn.probe()["portable_shader_misses"] == misses_before

        np.testing.assert_allclose(img1[4, 2], [255, 0, 0, 64], atol=2)
        np.testing.assert_allclose(img1[4, 6], [0, 255, 0, 64], atol=2)
        np.testing.assert_allclose(img1[4, 10], [0, 255, 255, 64], atol=2)
        np.testing.assert_allclose(img1[4, 14], [255, 255, 0, 64], atol=2)

        # Sub-range IndexBuffer + VertexBuffer updates mutate only the second triangle without disturbing the first.
        ibo.set_subdata(np.array([0, 0, 0], dtype=np.uint32), offset=3)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangles", ibo)
        half = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        # Bottom-right (row 7, col 14) is covered by triangle (0,1,2); top-left (row 0, col 1) was only in (0,2,3)!
        np.testing.assert_allclose(half[7, 14, :3], [255, 255, 0], atol=2)
        np.testing.assert_allclose(half[0, 1, :3], [0, 0, 0], atol=2)

        # Restore second triangle indices via slice assignment and partially shift vertex 3 via set_subdata.
        ibo[3:6] = np.array([0, 2, 3], dtype=np.uint32)
        quad.set_subdata(np.array([[-1.0, 1.0]], dtype=np.float32), offset=3)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangles", ibo)
        restored = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        np.testing.assert_allclose(restored[0, 1, :3], [255, 0, 0], atol=2)


def test_modular_multiprogram_variable_vs_code_invalidation_and_cache_eviction():
    from vispy.visuals.shaders import Function, ModularProgram, MultiProgram, Variable

    with _headless_canvas(size=(8, 8)) as (_canvas, gloo, _dawn, objects):
        try:
            # Boundary validation on _dawn.configure_shader_cache.
            with pytest.raises(RuntimeError, match="shader cache requires 1..128 entries"):
                _dawn.configure_shader_cache(0, 1024)
            with pytest.raises(RuntimeError, match="shader cache requires 1..128 entries"):
                _dawn.configure_shader_cache(129, 1024)

            # Distinct portable compile_variant options produce distinct cache keys; identical call hits cache.
            vsrc = "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }"
            fsrc = "uniform vec4 u_c; void main() { gl_FragColor = u_c + vec4(0.000123); }"
            c1 = _dawn.compile_variant(vsrc, fsrc, base_level_sampling=True, has_depth=False)
            c2 = _dawn.compile_variant(vsrc, fsrc, base_level_sampling=True, has_depth=False)
            c3 = _dawn.compile_variant(vsrc, fsrc, base_level_sampling=False, has_depth=False)
            c_depth = _dawn.compile_variant(vsrc, fsrc, base_level_sampling=True, has_depth=True)
            assert c1["ok"] and c2["ok"] and c3["ok"] and c_depth["ok"]
            assert c2["cache_hit"] is True and c1["cache_key"] == c2["cache_key"]
            assert c3["cache_key"] != c1["cache_key"]

            # ModularProgram & MultiProgram: Variable value mutation skips recompile; Function code edit invalidates & replays.
            quad = gloo.VertexBuffer(
                np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
            )
            objects.append(quad)

            f_tint = Function("vec4 apply_tint(vec4 c) { return c; }")
            color_var = Variable("uniform vec4 u_color", (0.25, 0.5, 0.75, 1.0))

            mp = MultiProgram(
                "void main() { gl_Position = vec4($pos, 0.0, 1.0); }",
                "void main() { gl_FragColor = $tint($color); }",
            )
            sub = mp.add_program("p0")
            objects.append(sub)
            mp.vert["pos"] = quad
            mp.frag["tint"] = f_tint
            mp.frag["color"] = color_var

            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            sub.draw("triangle_strip")
            first_px = gloo.read_pixels((0, 0, 8, 8), alpha=True)[4, 4]
            np.testing.assert_allclose(first_px, [64, 128, 191, 255], atol=2)

            misses0 = _dawn.probe()["portable_shader_misses"]
            color_var.value = (0.75, 0.25, 0.5, 1.0)
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            sub.draw("triangle_strip")
            assert _dawn.probe()["portable_shader_misses"] == misses0
            np.testing.assert_allclose(
                gloo.read_pixels((0, 0, 8, 8), alpha=True)[4, 4], [191, 64, 128, 255], atol=2
            )

            # Mutating Function code invalidates shader identity, recompiles (+1 miss), and replays bound quad + color_var.
            mp.frag["tint"] = Function("vec4 apply_tint(vec4 c) { return vec4(c.bgr, c.a); }")
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            sub.draw("triangle_strip")
            rebuilt_px = gloo.read_pixels((0, 0, 8, 8), alpha=True)[4, 4]
            assert _dawn.probe()["portable_shader_misses"] >= misses0 + 1
            np.testing.assert_allclose(rebuilt_px, [128, 64, 191, 255], atol=2)

            # Shrinking shader cache to 2 entries evicts LRU entries cleanly while keeping live Programs runnable.
            _dawn.configure_shader_cache(2, 64 * 1024 * 1024)
            progs = []
            for idx, ch in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
                p = ModularProgram(
                    "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
                    f"void main() {{ gl_FragColor = vec4({ch[0]:.1f}, {ch[1]:.1f}, {ch[2]:.1f}, {1.0 - idx * 0.0001:.6f}); }}",
                )
                p["a_pos"] = quad
                objects.append(p)
                progs.append((p, ch))
                p.draw("triangle_strip")

            assert _dawn.probe()["artifact_cache_entries"] <= 2
            # Program 0 (evicted from global cache) still retains its live artifact and renders accurately!
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            progs[0][0].draw("triangle_strip")
            np.testing.assert_allclose(
                gloo.read_pixels((0, 0, 8, 8), alpha=True)[4, 4, :3], [255, 0, 0], atol=2
            )
        finally:
            _dawn.configure_shader_cache(128, 64 * 1024 * 1024)
