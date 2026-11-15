"""Multidimensional sampler arrays, LOD/grad, derivative uniformity, and Mesa guard (SHD-01, SHD-06).

Verifies multidimensional sampler array helper dispatch and single-slot rebinding,
preprocessor macro expansion, explicit texture2DLod / texture2DGradEXT vs 3-arg
bias refusal, strict vs non-uniform control-flow implicit derivative compilation
modes, and the pinned WSL Mesa 26.1.8 (9c5) vs system Lavapipe 4x MSAA guard.
"""
from __future__ import annotations

from contextlib import contextmanager
import sys

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@contextmanager
def _headless_canvas(size=(12, 12), samples=0):
    from vispy import _dawn, app, gloo

    config = {"samples": int(samples)} if samples else None
    canvas = app.Canvas(app="dawn_headless", size=size, config=config, show=False)
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


def test_multidimensional_sampler_helpers_rebinding_and_index_bounds():
    with _headless_canvas(size=(8, 8)) as (_canvas, gloo, _dawn, objects):
        from vispy.gloo.preprocessor import preprocess

        quad = gloo.VertexBuffer(
            np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        )
        uv = gloo.VertexBuffer(
            np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        )
        objects.extend([quad, uv])

        frag_src = preprocess(
            """
            #define CENTER_UV vec2(0.5)
            uniform sampler2D u_grid[2][2];
            uniform isampler2D u_ints[2];
            varying vec2 v_uv;
            vec4 fetch_cell(sampler2D img, vec2 coord) {
                return texture2D(img, coord);
            }
            void main() {
                vec4 c;
                if (v_uv.y < 0.5) {
                    c = (v_uv.x < 0.5) ? fetch_cell(u_grid[0][0], CENTER_UV)
                                       : fetch_cell(u_grid[0][1], CENTER_UV);
                } else {
                    c = (v_uv.x < 0.5) ? fetch_cell(u_grid[1][0], CENTER_UV)
                                       : fetch_cell(u_grid[1][1], CENTER_UV);
                }
                int tag = texelFetch(u_ints[1], ivec2(0, 0), 0).r;
                c.a = (tag == 77) ? 1.0 : 0.25;
                gl_FragColor = c;
            }
            """
        )
        prog = gloo.Program(
            "attribute vec2 a_pos; attribute vec2 a_uv; varying vec2 v_uv; void main() { v_uv = a_uv; gl_Position = vec4(a_pos, 0.0, 1.0); }",
            frag_src,
        )
        objects.append(prog)
        prog["a_pos"] = quad
        prog["a_uv"] = uv

        palette = {
            (0, 0): np.array([255, 0, 0, 255], dtype=np.uint8),
            (0, 1): np.array([0, 255, 0, 255], dtype=np.uint8),
            (1, 0): np.array([0, 0, 255, 255], dtype=np.uint8),
            (1, 1): np.array([255, 255, 0, 255], dtype=np.uint8),
        }
        for (r, c), rgba in palette.items():
            tex = gloo.Texture2D(
                np.broadcast_to(rgba, (2, 2, 4)).copy(), interpolation="nearest"
            )
            objects.append(tex)
            prog[f"u_grid[{r}][{c}]"] = tex

        for slot, val in enumerate((11, 77)):
            itex = gloo.Texture2D(
                np.full((2, 2, 1), val, dtype=np.int32),
                format="red",
                internalformat="r32i",
                interpolation="nearest",
            )
            objects.append(itex)
            prog[f"u_ints[{slot}]"] = itex

        gloo.set_state(blend=False, depth_test=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 0.0))
        prog.draw("triangle_strip")
        img = gloo.read_pixels((0, 0, 8, 8), alpha=True)
        # Bottom-left (v_uv.y<0.5, v_uv.x<0.5) -> row 6, col 1; top-right -> row 1, col 6.
        np.testing.assert_allclose(img[6, 1], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(img[6, 6], [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(img[1, 1], [0, 0, 255, 255], atol=2)
        np.testing.assert_allclose(img[1, 6], [255, 255, 0, 255], atol=2)

        # Rebinding a single leaf slot updates only that quadrant while preserving the other three.
        replacement = gloo.Texture2D(
            np.broadcast_to(np.array([64, 192, 255, 255], dtype=np.uint8), (2, 2, 4)).copy(),
            interpolation="nearest",
        )
        objects.append(replacement)
        prog["u_grid[1][0]"] = replacement
        gloo.clear(color=(0.0, 0.0, 0.0, 0.0))
        prog.draw("triangle_strip")
        rebound = gloo.read_pixels((0, 0, 8, 8), alpha=True)
        np.testing.assert_allclose(rebound[1, 1], [64, 192, 255, 255], atol=2)
        np.testing.assert_allclose(rebound[6, 1], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(rebound[1, 6], [255, 255, 0, 255], atol=2)

        # Dynamic runtime indexing and out-of-bounds static indices are explicitly refused.
        vsrc = "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }"
        dyn_res = _dawn.compile_variant(
            vsrc,
            "uniform sampler2D u_arr[2]; uniform int u_idx; void main() { gl_FragColor = texture2D(u_arr[u_idx], vec2(0.5)); }",
        )
        oob_res = _dawn.compile_variant(
            vsrc,
            "uniform sampler2D u_arr[2][2]; void main() { gl_FragColor = texture2D(u_arr[2][0], vec2(0.5)); }",
        )
        assert dyn_res["ok"] is False and dyn_res["error"]
        assert oob_res["ok"] is False and oob_res["error"]


def test_explicit_lod_grad_bias_refusal_and_non_uniform_derivative_modes():
    with _headless_canvas(size=(8, 8)) as (_canvas, gloo, _dawn, objects):
        quad = gloo.VertexBuffer(
            np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        )
        uv = gloo.VertexBuffer(
            np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        )
        tex = gloo.Texture2D(
            np.array(
                [[[255, 0, 0, 255], [0, 255, 0, 255]], [[0, 0, 255, 255], [255, 255, 255, 255]]],
                dtype=np.uint8,
            ),
            interpolation="nearest",
        )
        objects.extend([quad, uv, tex])

        vsrc = (
            "attribute vec2 a_pos; attribute vec2 a_uv; varying vec2 v_uv; "
            "void main() { v_uv = a_uv; gl_Position = vec4(a_pos, 0.0, 1.0); }"
        )

        # 1. 3-argument bias form under base_level_sampling=True is explicitly refused.
        bias_res = _dawn.compile_variant(
            vsrc,
            "uniform sampler2D u_tex; varying vec2 v_uv; void main() { gl_FragColor = texture2D(u_tex, v_uv, 1.0); }",
            base_level_sampling=True,
        )
        assert bias_res["ok"] is False and "bias is unsupported" in bias_res["error"]

        # 2. Implicit derivatives inside data-dependent control flow: strict-v1 refuses, chromium-non-uniform-v1 admits.
        non_uniform_fsrc = """
        uniform sampler2D u_tex;
        uniform float u_threshold;
        varying vec2 v_uv;
        void main() {
            vec4 out_c = vec4(0.0, 0.0, 0.0, 1.0);
            if (v_uv.x > u_threshold) {
                float dx = dFdx(v_uv.x);
                out_c = texture2D(u_tex, v_uv) + vec4(dx * 0.0);
            }
            gl_FragColor = out_c;
        }
        """
        strict_res = _dawn.compile_variant(
            vsrc,
            non_uniform_fsrc,
            base_level_sampling=False,
            allow_non_uniform_derivatives=False,
        )
        relaxed_res = _dawn.compile_variant(
            vsrc,
            non_uniform_fsrc,
            base_level_sampling=False,
            allow_non_uniform_derivatives=True,
        )
        assert strict_res["spirv_derivative_mode"] == "strict-v1"
        assert strict_res["ok"] is False and strict_res["error"]
        assert relaxed_res["spirv_derivative_mode"] == "allow-nonuniform-v1"
        assert relaxed_res["ok"] is True

        # 3. Explicit texture2DLod and texture2DGradEXT inside non-uniform branches compile & render accurately.
        explicit_fsrc = """
        #extension GL_EXT_shader_texture_lod : enable
        uniform sampler2D u_tex;
        varying vec2 v_uv;
        void main() {
            if (v_uv.x < 0.5) {
                gl_FragColor = texture2DLod(u_tex, vec2(0.25, 0.25), 0.0);
            } else {
                gl_FragColor = texture2DGradEXT(u_tex, vec2(0.75, 0.25), vec2(0.0), vec2(0.0));
            }
        }
        """
        prog = gloo.Program(vsrc, explicit_fsrc)
        objects.append(prog)
        prog["a_pos"] = quad
        prog["a_uv"] = uv
        prog["u_tex"] = tex
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        out = gloo.read_pixels((0, 0, 8, 8), alpha=True)
        np.testing.assert_allclose(out[4, 1], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(out[4, 6], [0, 255, 0, 255], atol=2)


def test_shd06_driver_profile_and_4x_msaa_clip_capability_guard():
    with _headless_canvas(size=(16, 16), samples=4) as (_canvas, gloo, _dawn, objects):
        info = _dawn.device_info()
        assert info["ok"] is True
        assert info["backend"] == "Vulkan"
        assert info["core_features_and_limits"] is True

        # On Linux software Vulkan (WSL Lavapipe), enforce the qualified Mesa 26.1.8 (9c5) driver floor
        # rather than silently running on unpatched system Mesa 24.x/25.2.8 with broken 4x MSAA clipping.
        if sys.platform.startswith("linux") and info["software"]:
            assert "Mesa 26.1." in info["driver"], f"Unqualified Linux software driver: {info['driver']}"

        assert int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES)) == 4
        tri = gloo.VertexBuffer(
            np.array([[-1.2, -1.2], [1.2, -1.2], [0.0, 1.4]], dtype=np.float32)
        )
        prog = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.25, 1.0); }",
            "void main() { gl_FragColor = vec4(0.125, 0.625, 0.875, 1.0); }",
        )
        objects.extend([tri, prog])
        prog["a_pos"] = tri

        gloo.set_state(depth_test=True, scissor_test=False, blend=False, multisample=True)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)
        gloo.set_state(scissor_test=True)
        gloo.set_scissor(2, 2, 12, 12)
        prog.draw("triangles")
        gloo.set_state(scissor_test=False)

        msaa = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        # Interior center is solidly shaded; outside the scissor box stays cleared black.
        np.testing.assert_allclose(msaa[8, 8], [32, 159, 223, 255], atol=3)
        np.testing.assert_allclose(msaa[0, 0], [0, 0, 0, 255], atol=2)
        np.testing.assert_allclose(msaa[15, 15], [0, 0, 0, 255], atol=2)
