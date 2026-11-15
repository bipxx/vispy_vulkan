"""GPU sampling, precision, NaN/Inf, depth-compare, and layout tests (TEX-01, API-05).

Verifies signed/unsigned integer Texture2D sampling and sub-region updates,
float32 NaN/Inf/-0.0 bit-pattern preservation and linear/mipmap filter gates,
float16 rounding/filtering/NaN propagation, depth_component hardware depth test
and shadow/scalar mismatch refusals, plus Texture3D, TextureCube, and
TextureEmulated3D wrapper contracts.
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@contextmanager
def _headless_canvas(size=(16, 16)):
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


def _quad_buffers(gloo, objects):
    pos = gloo.VertexBuffer(
        np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    )
    uv = gloo.VertexBuffer(
        np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    )
    objects.extend([pos, uv])
    return pos, uv


def test_integer_sint_uint_textures_subdata_wrapping_and_refusals():
    with _headless_canvas(size=(4, 4)) as (_canvas, gloo, _dawn, objects):
        sint_data = np.array(
            [[[-2147483648], [-1]], [[0], [2147483647]]], dtype=np.int32
        )
        uint_data = np.array(
            [[[0], [1]], [[2147483648], [4294967295]]], dtype=np.uint32
        )
        sint_tex = gloo.Texture2D(
            sint_data,
            format="red",
            internalformat="r32i",
            interpolation="nearest",
            wrapping=("repeat", "mirrored_repeat"),
        )
        uint_tex = gloo.Texture2D(
            uint_data,
            format="red",
            internalformat="r32ui",
            interpolation="nearest",
            wrapping="clamp_to_edge",
        )
        objects.extend([sint_tex, uint_tex])

        with pytest.raises(ValueError):
            sint_tex.interpolation = "linear"
        with pytest.raises(ValueError):
            sint_tex.set_data(np.zeros((2, 2, 1), dtype=np.float32))
        with pytest.raises(ValueError):
            gloo.Texture3D(np.zeros((2, 2, 2, 1), dtype=np.int32), format="red", internalformat="r32i")

        pos, uv = _quad_buffers(gloo, objects)
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
            uniform isampler2D u_sint;
            uniform usampler2D u_uint;
            varying vec2 v_uv;
            void main() {
                int sv = texture2D(u_sint, v_uv).r;
                uint uv_val = texture2D(u_uint, v_uv).r;
                float r = (sv == -2147483648) ? 1.0 : ((sv == -1) ? 0.5 : 0.0);
                float g = (sv == 2147483647) ? 1.0 : ((sv == 0) ? 0.25 : 0.0);
                float b = (uv_val == 4294967295u) ? 1.0 : ((uv_val == 2147483648u) ? 0.5 : 0.0);
                gl_FragColor = vec4(r, g, b, 1.0);
            }
            """,
        )
        objects.append(prog)
        prog["a_pos"] = pos
        prog["a_uv"] = uv
        prog["u_sint"] = sint_tex
        prog["u_uint"] = uint_tex

        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        # Note read_pixels row 0 is top of image (v_uv.y ~ 1), row 3 is bottom (v_uv.y ~ 0).
        img = gloo.read_pixels((0, 0, 4, 4), alpha=True)
        np.testing.assert_allclose(img[3, 0], [255, 0, 0, 255], atol=2)     # (0,0): -2147483648, 0u
        np.testing.assert_allclose(img[3, 3], [128, 0, 0, 255], atol=2)     # (0,1): -1, 1u
        np.testing.assert_allclose(img[0, 0], [0, 64, 128, 255], atol=2)    # (1,0): 0, 2147483648u
        np.testing.assert_allclose(img[0, 3], [0, 255, 255, 255], atol=2)   # (1,1): 2147483647, 4294967295u

        # Sub-region offset update mutates only texel (1, 0) while preserving neighbors.
        sint_tex.set_data(np.array([[[-1]]], dtype=np.int32), offset=(1, 0))
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        updated = gloo.read_pixels((0, 0, 4, 4), alpha=True)
        np.testing.assert_allclose(updated[0, 0], [128, 0, 128, 255], atol=2)
        np.testing.assert_allclose(updated[0, 3], [0, 255, 255, 255], atol=2)

        # Binding a float texture to an integer sampler uniform raises an explicit mismatch and recovers.
        bad_float_tex = gloo.Texture2D(
            np.zeros((2, 2, 1), dtype=np.float32), format="red", internalformat="r32f"
        )
        objects.append(bad_float_tex)
        with pytest.raises(ValueError, match="requires an explicit matching integer Texture2D"):
            prog["u_sint"] = bad_float_tex

        prog["u_sint"] = sint_tex
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        recovered = gloo.read_pixels((0, 0, 4, 4), alpha=True)
        np.testing.assert_allclose(recovered[0, 3], [0, 255, 255, 255], atol=2)


def test_float32_nan_inf_signed_zero_linear_gate_and_mipmap_refusal():
    with _headless_canvas(size=(4, 4)) as (_canvas, gloo, _dawn, objects):
        qnan = np.uint32(0x7FC12345).view(np.float32)
        specials = np.array(
            [[[qnan], [np.float32(np.inf)]], [[np.float32(-np.inf)], [np.float32(-0.0)]]],
            dtype=np.float32,
        )
        tex = gloo.Texture2D(
            specials, format="red", internalformat="r32f", interpolation="nearest"
        )
        fbo_color = gloo.Texture2D(
            np.zeros((4, 4, 4), dtype=np.float32), format="rgba", internalformat="rgba32f"
        )
        fbo = gloo.FrameBuffer(color=fbo_color)
        objects.extend([tex, fbo_color, fbo])

        pos, uv = _quad_buffers(gloo, objects)
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
            uniform sampler2D u_tex;
            varying vec2 v_uv;
            void main() {
                float v = texture2D(u_tex, v_uv).r;
                float is_nan_flag = isnan(v) ? 1.0 : 0.0;
                float is_pos_inf = (isinf(v) && v > 0.0) ? 1.0 : 0.0;
                float is_neg_inf = (isinf(v) && v < 0.0) ? 1.0 : 0.0;
                gl_FragColor = vec4(v, is_nan_flag, is_pos_inf, is_neg_inf);
            }
            """,
        )
        objects.append(prog)
        prog["a_pos"] = pos
        prog["a_uv"] = uv
        prog["u_tex"] = tex

        with fbo:
            gloo.set_viewport(0, 0, 4, 4)
            gloo.set_state(blend=False)
            gloo.clear(color=(0.0, 0.0, 0.0, 0.0))
            prog.draw("triangle_strip")
            raw = gloo.read_pixels((0, 0, 4, 4), mode="color", out_type="float")

        assert np.isnan(raw[3, 0, 0]) and raw[3, 0, 1] == pytest.approx(1.0)
        assert np.isposinf(raw[3, 3, 0]) and raw[3, 3, 2] == pytest.approx(1.0)
        assert np.isneginf(raw[0, 0, 0]) and raw[0, 0, 3] == pytest.approx(1.0)
        assert raw[0, 3, 0] == 0.0 and np.signbit(raw[0, 3, 0])

        # Linear float32 filtering follows device_info()['float32_filterable'].
        info = _dawn.device_info()
        grad_tex = gloo.Texture2D(
            np.array([[[0.0], [1.0]], [[0.0], [1.0]]], dtype=np.float32),
            format="red",
            internalformat="r32f",
            interpolation="linear",
            wrapping="clamp_to_edge",
        )
        objects.append(grad_tex)
        prog_lin = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform sampler2D u_tex; void main() { float v = texture2D(u_tex, vec2(0.5, 0.5)).r; gl_FragColor = vec4(v, v, v, 1.0); }",
        )
        objects.append(prog_lin)
        prog_lin["a_pos"] = pos
        prog_lin["u_tex"] = grad_tex

        if info["float32_filterable"]:
            gloo.set_viewport(0, 0, 4, 4)
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            prog_lin.draw("triangle_strip")
            lin_img = gloo.read_pixels((0, 0, 4, 4), alpha=True)
            np.testing.assert_allclose(lin_img[2, 2], [128, 128, 128, 255], atol=3)
        else:
            with pytest.raises(RuntimeError, match="Float32Filterable"):
                prog_lin.draw("triangle_strip")
                _canvas.context.finish()

        # Mipmapped GLIR filter token without mip allocation is explicitly refused and recovers.
        grad_tex._glir.command("FILTERS", grad_tex.id, "linear_mipmap_linear", "linear")
        with pytest.raises(RuntimeError, match="unsupported operation"):
            prog_lin.draw("triangle_strip")
            _canvas.context.finish()

        grad_tex.interpolation = "nearest"
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog_lin.draw("triangle_strip")
        rec_img = gloo.read_pixels((0, 0, 4, 4), alpha=True)
        assert rec_img.shape == (4, 4, 4)


def test_float16_precision_bounds_and_depth_component_comparison_contracts():
    with _headless_canvas(size=(4, 4)) as (_canvas, gloo, _dawn, objects):
        pos, uv = _quad_buffers(gloo, objects)

        # 1. Float16 sub-ULP rounding (1.0 + 2^-12 -> 1.0; 1.0 + 2^-10 -> 1.0009765625) + NaN propagation.
        f16_src = np.array(
            [
                [[1.0 + 2.0**-12, 1.0 + 2.0**-10, np.nan, 1.0], [0.0, 1.0, 0.5, 1.0]],
                [[0.0, 1.0, 0.5, 1.0], [1.0, 0.0, 0.5, 1.0]],
            ],
            dtype=np.float32,
        )
        tex16 = gloo.Texture2D(
            f16_src, format="rgba", internalformat="rgba16f", interpolation="nearest"
        )
        fbo16_color = gloo.Texture2D(
            np.zeros((4, 4, 4), dtype=np.float32), format="rgba", internalformat="rgba16f"
        )
        fbo16 = gloo.FrameBuffer(color=fbo16_color)
        objects.extend([tex16, fbo16_color, fbo16])

        prog16 = gloo.Program(
            "attribute vec2 a_pos; attribute vec2 a_uv; varying vec2 v_uv; void main() { v_uv = a_uv; gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform sampler2D u_tex; varying vec2 v_uv; void main() { gl_FragColor = texture2D(u_tex, v_uv); }",
        )
        objects.append(prog16)
        prog16["a_pos"] = pos
        prog16["a_uv"] = uv
        prog16["u_tex"] = tex16

        with fbo16:
            gloo.set_viewport(0, 0, 4, 4)
            gloo.clear(color=(0.0, 0.0, 0.0, 0.0))
            prog16.draw("triangle_strip")
            out16 = gloo.read_pixels((0, 0, 4, 4), mode="color", out_type="float")

        assert out16[3, 0, 0] == pytest.approx(1.0, abs=0.0)
        assert out16[3, 0, 1] == pytest.approx(1.0 + 2.0**-10, abs=1e-7)
        assert np.isnan(out16[3, 0, 2])

        # 2. Depth texture upload NaN refusal + hardware depth-compare rasterization + readback.
        depth_tex = gloo.Texture2D(
            np.array([[0.25, 0.75], [0.25, 0.75]], dtype=np.float32),
            format="depth_component",
            internalformat="depth_component",
        )
        color_tex = gloo.Texture2D(np.zeros((2, 2, 4), dtype=np.uint8))
        depth_fbo = gloo.FrameBuffer(color=color_tex, depth=depth_tex)
        objects.extend([depth_tex, color_tex, depth_fbo])

        with pytest.raises(RuntimeError, match="depth_component upload requires non-NaN values"):
            bad_depth = gloo.Texture2D(
                np.array([[np.nan, 0.5], [0.5, 0.5]], dtype=np.float32),
                format="depth_component",
                internalformat="depth_component",
            )
            bad_fbo = gloo.FrameBuffer(color=color_tex, depth=bad_depth)
            objects.extend([bad_depth, bad_fbo])
            with bad_fbo:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=False)
                _canvas.context.finish()

        prog_depth = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "void main() { gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }",
        )
        objects.append(prog_depth)
        prog_depth["a_pos"] = pos

        with depth_fbo:
            gloo.set_viewport(0, 0, 2, 2)
            gloo.set_state(depth_test=True, blend=False)
            gloo.set_depth_func("less")
            # Clear color only so uploaded depth_tex [0.25 left, 0.75 right] acts as hardware compare reference!
            gloo.clear(color=(1.0, 0.0, 0.0, 1.0), depth=False)
            # Quad at z_ndc = 0.0 -> window depth 0.5: fails (< 0.25 false) on left, passes (< 0.75 true) on right.
            prog_depth.draw("triangle_strip")
            cmp_color = depth_fbo.read(mode="color")
            cmp_depth = gloo.read_pixels((0, 0, 2, 2), mode="depth", out_type="float")

        np.testing.assert_allclose(cmp_color[:, 0, 0], 255, atol=2)
        np.testing.assert_allclose(cmp_color[:, 0, 1:3], 0, atol=2)
        np.testing.assert_allclose(cmp_color[:, 1, 0], 0, atol=2)
        np.testing.assert_allclose(cmp_color[:, 1, 1], 255, atol=2)
        np.testing.assert_allclose(cmp_depth[:, 0, 0], 0.25, atol=1e-4)
        np.testing.assert_allclose(cmp_depth[:, 1, 0], 0.50, atol=1e-4)

        # Binding depth_component Texture2D to ordinary sampler2D and sampler2DShadow shader compilation are refused cleanly.
        prog16["u_tex"] = depth_tex
        with pytest.raises(RuntimeError):
            prog16.draw("triangle_strip")
            _canvas.context.finish()

        shadow_info = _dawn.compile_variant(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform sampler2DShadow u_shadow; void main() { gl_FragColor = vec4(1.0); }",
        )
        assert shadow_info["ok"] is False and shadow_info["error"]


def test_texture3d_cube_and_emulated3d_api05_contracts():
    from vispy.visuals.shaders import ModularProgram

    with _headless_canvas(size=(4, 4)) as (_canvas, gloo, _dawn, objects):
        pos, uv = _quad_buffers(gloo, objects)

        # 1. Texture3D vs TextureEmulated3D slice equivalence and sub-volume update.
        vol = np.zeros((2, 2, 2, 4), dtype=np.uint8)
        vol[0] = [64, 0, 0, 255]
        vol[1] = [0, 192, 0, 255]
        tex3d = gloo.Texture3D(vol, interpolation="nearest", wrapping="clamp_to_edge")
        emu3d = gloo.TextureEmulated3D(vol, interpolation="nearest", wrapping="clamp_to_edge")
        objects.extend([tex3d, emu3d])
        assert emu3d.shape == (2, 2, 2, 4) and emu3d.depth == 2

        patch = np.array([[[[0, 0, 255, 255]]]], dtype=np.uint8)
        tex3d.set_data(patch, offset=(1, 1, 1))
        vol2 = vol.copy()
        vol2[1, 1, 1] = [0, 0, 255, 255]
        emu3d.set_data(vol2)

        prog3d = gloo.Program(
            "attribute vec2 a_pos; attribute vec2 a_uv; varying vec2 v_uv; void main() { v_uv = a_uv; gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform sampler3D u_vol; varying vec2 v_uv; void main() { gl_FragColor = texture3D(u_vol, vec3(v_uv, 0.75)); }",
        )
        prog_emu = ModularProgram(
            "attribute vec2 a_pos; attribute vec2 a_uv; varying vec2 v_uv; void main() { v_uv = a_uv; gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform sampler2D u_vol; varying vec2 v_uv; void main() { gl_FragColor = $sample(u_vol, vec3(v_uv, 0.75)); }",
        )
        objects.extend([prog3d, prog_emu])
        prog3d["a_pos"] = pos
        prog3d["a_uv"] = uv
        prog3d["u_vol"] = tex3d
        prog_emu["a_pos"] = pos
        prog_emu["a_uv"] = uv
        prog_emu["u_vol"] = emu3d
        prog_emu.frag["sample"] = emu3d.glsl_sample

        gloo.set_state(depth_test=False, blend=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog3d.draw("triangle_strip")
        img3d = gloo.read_pixels((0, 0, 4, 4), alpha=True)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog_emu.draw("triangle_strip")
        img_emu = gloo.read_pixels((0, 0, 4, 4), alpha=True)

        np.testing.assert_allclose(img3d[0, 3], [0, 0, 255, 255], atol=2)
        np.testing.assert_allclose(img3d[3, 0], [0, 192, 0, 255], atol=2)
        np.testing.assert_allclose(img_emu, img3d, atol=2)

        # 2. TextureCube 6-face axis sampling (+X, -X, +Y, -Y, +Z, -Z).
        face_colors = np.array(
            [
                [255, 0, 0, 255],
                [0, 255, 0, 255],
                [0, 0, 255, 255],
                [255, 255, 0, 255],
                [255, 0, 255, 255],
                [0, 255, 255, 255],
            ],
            dtype=np.uint8,
        )
        cube_data = np.broadcast_to(face_colors[:, None, None, :], (6, 2, 2, 4)).copy()
        cube = gloo.TextureCube(cube_data, interpolation="nearest", wrapping="clamp_to_edge")
        objects.append(cube)
        prog_cube = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform samplerCube u_cube; uniform vec3 u_dir; void main() { gl_FragColor = textureCube(u_cube, u_dir); }",
        )
        objects.append(prog_cube)
        prog_cube["a_pos"] = pos
        prog_cube["u_cube"] = cube

        directions = [
            (1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, -1.0),
        ]
        for idx, direction in enumerate(directions):
            prog_cube["u_dir"] = direction
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            prog_cube.draw("triangle_strip")
            got = gloo.read_pixels((0, 0, 4, 4), alpha=True)[2, 2]
            np.testing.assert_allclose(got, face_colors[idx], atol=2)
