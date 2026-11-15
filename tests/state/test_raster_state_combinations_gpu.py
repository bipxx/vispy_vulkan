"""GPU truth tables for Gloo raster state combinations and STA-01/STA-02 contracts.

Covers dither disabled/enabled boundary diagnostics, disabled-MSAA transitions
on 1x and 4x targets, integer vs fractional polygon_offset depth bias, mixed vs
compatible constant blend_color equations, and ordered two-sided stencil +
reversed-depth recovery on the active Dawn Vulkan profile.
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@contextmanager
def _headless_canvas(size=(16, 12), samples=0):
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


def _fullscreen_quad(gloo, objects, z=0.0):
    verts = np.array(
        [[-1.0, -1.0, z], [1.0, -1.0, z], [-1.0, 1.0, z], [1.0, 1.0, z]],
        dtype=np.float32,
    )
    vbo = gloo.VertexBuffer(verts)
    objects.append(vbo)
    return vbo


def test_dither_disabled_noop_and_enabled_atomic_refusal():
    with _headless_canvas(size=(12, 8), samples=0) as (_canvas, gloo, _dawn, objects):
        prog = gloo.Program(
            "attribute vec3 a_pos; void main() { gl_Position = vec4(a_pos, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.append(prog)
        prog["a_pos"] = _fullscreen_quad(gloo, objects, z=0.25)
        prog["u_color"] = (0.25, 0.5, 0.75, 1.0)

        gloo.set_state(depth_test=True, blend=False, dither=False)
        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))
        gloo.clear(color=True, depth=True)
        prog.draw("triangle_strip")
        before = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        assert before.shape == (8, 12, 4)
        np.testing.assert_allclose(before[4, 6], [64, 128, 191, 255], atol=2)

        # GL_DITHER (0x0BD0 == 3024) is explicitly rejected when enabled and unrepresented as a live query.
        with pytest.raises(RuntimeError, match="unsupported GL query 3024"):
            gloo.gl.glGetParameter(0x0BD0)

        with pytest.raises(RuntimeError, match="unsupported capability dither"):
            gloo.set_state(dither=True)
            _canvas.context.finish()

        # Refusal is atomic: prior depth_test=True and clear/draw routes remain operational.
        assert bool(gloo.gl.glGetParameter(gloo.gl.GL_DEPTH_TEST)) is True
        prog["u_color"] = (1.0, 0.25, 0.0, 1.0)
        gloo.clear(color=True, depth=True)
        prog.draw("triangle_strip")
        recovered = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        np.testing.assert_allclose(recovered[4, 6], [255, 64, 0, 255], atol=2)


def test_multisample_state_transitions_on_single_and_4x_targets():
    with _headless_canvas(size=(8, 8), samples=0) as (_canvas, gloo, _dawn, objects):
        prog = gloo.Program(
            "attribute vec3 a_pos; void main() { gl_Position = vec4(a_pos, 1.0); }",
            "void main() { gl_FragColor = vec4(0.0, 1.0, 0.5, 1.0); }",
        )
        objects.append(prog)
        prog["a_pos"] = _fullscreen_quad(gloo, objects)

        gloo.set_state(multisample=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        assert int(gloo.gl.glGetParameter(0x809D)) == 0
        img_off = gloo.read_pixels((0, 0, 8, 8), alpha=True)
        np.testing.assert_allclose(img_off[3, 3], [0, 255, 128, 255], atol=2)

        gloo.set_state(multisample=True)
        gloo.flush()
        assert int(gloo.gl.glGetParameter(0x809D)) == 1

    with _headless_canvas(size=(12, 12), samples=4) as (_canvas, gloo, _dawn, objects):
        assert int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES)) == 4
        prog = gloo.Program(
            "attribute vec3 a_pos; void main() { gl_Position = vec4(a_pos, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.append(prog)
        prog["a_pos"] = _fullscreen_quad(gloo, objects)
        prog["u_color"] = (0.0, 0.5, 1.0, 1.0)

        gloo.set_state(multisample=False)
        gloo.flush()
        assert int(gloo.gl.glGetParameter(0x809D)) == 0

        # Drawing to a 4-sample default framebuffer while multisample=False is explicitly refused.
        with pytest.raises(
            RuntimeError,
            match="disabled multisample rasterization requires a separate single-sample target",
        ):
            prog.draw("triangle_strip")
            _canvas.context.finish()

        # Drawing to a bound 1-sample FrameBuffer while multisample=False succeeds.
        color_tex = gloo.Texture2D(np.zeros((12, 12, 4), dtype=np.uint8))
        fbo = gloo.FrameBuffer(color=color_tex)
        objects.extend([color_tex, fbo])
        with fbo:
            gloo.set_viewport(0, 0, 12, 12)
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            prog.draw("triangle_strip")
            single_img = gloo.read_pixels((0, 0, 12, 12), alpha=True)
        np.testing.assert_allclose(single_img[6, 6], [0, 128, 255, 255], atol=2)

        # Re-enabling multisample restores drawing on the 4-sample default framebuffer.
        gloo.set_state(multisample=True)
        gloo.set_viewport(0, 0, 12, 12)
        prog["u_color"] = (0.75, 0.25, 0.5, 1.0)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("triangle_strip")
        msaa_img = gloo.read_pixels((0, 0, 12, 12), alpha=True)
        np.testing.assert_allclose(msaa_img[6, 6], [191, 64, 128, 255], atol=2)


def test_polygon_offset_integer_bias_and_fractional_refusal_recovery():
    with _headless_canvas(size=(12, 12), samples=0) as (_canvas, gloo, _dawn, objects):
        prog = gloo.Program(
            "attribute vec3 a_pos; void main() { gl_Position = vec4(a_pos, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.append(prog)
        quad = _fullscreen_quad(gloo, objects, z=0.0)
        prog["a_pos"] = quad

        gloo.set_state(depth_test=True, polygon_offset_fill=False, blend=False)
        gloo.set_depth_func("less")
        gloo.set_clear_depth(1.0)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)

        # Base coplanar pass at z_ndc = 0.0 -> window depth 0.5 (red).
        prog["u_color"] = (1.0, 0.0, 0.0, 1.0)
        prog.draw("triangle_strip")

        # Coplanar pass with positive integer units (+8.0) is pushed deeper -> occluded under 'less'.
        gloo.set_state(polygon_offset_fill=True)
        gloo.set_polygon_offset(1.25, 8.0)
        prog["u_color"] = (0.0, 1.0, 0.0, 1.0)
        prog.draw("triangle_strip")
        occluded = gloo.read_pixels((0, 0, 12, 12), alpha=True)
        np.testing.assert_allclose(occluded[6, 6], [255, 0, 0, 255], atol=2)
        assert float(gloo.gl.glGetParameter(0x8038)) == pytest.approx(1.25)
        assert float(gloo.gl.glGetParameter(0x2A00)) == pytest.approx(8.0)

        # Negative integer units (-8.0) pulls coplanar pass closer -> passes 'less' (green).
        gloo.set_polygon_offset(0.0, -8.0)
        prog.draw("triangle_strip")
        closer = gloo.read_pixels((0, 0, 12, 12), alpha=True)
        np.testing.assert_allclose(closer[6, 6], [0, 255, 0, 255], atol=2)

        # Fractional constant bias on polygon topology is refused cleanly; non-polygon topologies ignore it.
        gloo.set_polygon_offset(0.0, 0.5)
        prog["u_color"] = (1.0, 1.0, 0.0, 1.0)
        prog.draw("lines")
        _canvas.context.finish()

        with pytest.raises(
            RuntimeError,
            match="fractional/out-of-range constant bias requires a shader conversion",
        ):
            prog.draw("triangle_strip")
            _canvas.context.finish()

        # Restoring integer units recovers polygon drawing on the same canvas.
        gloo.set_polygon_offset(0.0, -16.0)
        prog["u_color"] = (0.0, 0.0, 1.0, 1.0)
        prog.draw("triangle_strip")
        recovered = gloo.read_pixels((0, 0, 12, 12), alpha=True)
        np.testing.assert_allclose(recovered[6, 6], [0, 0, 255, 255], atol=2)


def test_blend_color_equations_mixed_refusal_and_two_sided_stencil_reversed_depth():
    with _headless_canvas(size=(16, 8), samples=0) as (_canvas, gloo, _dawn, objects):
        prog = gloo.Program(
            "attribute vec3 a_pos; void main() { gl_Position = vec4(a_pos, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.append(prog)
        prog["a_pos"] = _fullscreen_quad(gloo, objects, z=0.0)

        # 1. Compatible constant_color RGB + constant_alpha A blending.
        gloo.set_state(blend=True, depth_test=False, stencil_test=False, cull_face=False)
        gloo.set_blend_color((0.25, 0.5, 0.75, 0.5))
        gloo.set_blend_equation("func_add", "func_add")
        gloo.set_blend_func(
            "constant_color",
            "one_minus_constant_color",
            "constant_alpha",
            "one_minus_constant_alpha",
        )
        gloo.clear(color=(1.0, 0.0, 0.0, 1.0))
        prog["u_color"] = (0.0, 1.0, 1.0, 0.0)
        prog.draw("triangle_strip")
        # Expected RGB = src*(0.25,0.5,0.75) + dst*(0.75,0.5,0.25) = (0.75, 0.5, 0.75); A = 0*0.5 + 1*0.5 = 0.5
        blended = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        np.testing.assert_allclose(blended[4, 8], [191, 128, 191, 128], atol=2)

        # 2. Mixed constant_color and constant_alpha RGB factors are refused atomically.
        gloo.set_blend_func("constant_color", "constant_alpha", "one", "zero")
        with pytest.raises(
            RuntimeError,
            match="mixed constant-alpha/constant-color RGB factors require independent constants",
        ):
            prog.draw("triangle_strip")
            _canvas.context.finish()

        # 3. Min/Max blend equations recover and preserve GL state selectors.
        gloo.set_blend_func("one", "one")
        gloo.set_blend_equation("max", "max")
        gloo.clear(color=(0.8, 0.2, 0.4, 1.0))
        prog["u_color"] = (0.3, 0.7, 0.9, 1.0)
        prog.draw("triangle_strip")
        max_img = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        np.testing.assert_allclose(max_img[4, 8], [204, 179, 230, 255], atol=3)
        assert int(gloo.gl.glGetParameter(0x8009)) == int(gloo.gl.GL_MAX)
        assert int(gloo.gl.glGetParameter(0x883D)) == int(gloo.gl.GL_MAX)

        gloo.set_blend_equation("min", "min")
        prog.draw("triangle_strip")
        min_img = gloo.read_pixels((0, 0, 16, 8), alpha=True)
        np.testing.assert_allclose(min_img[4, 8], [77, 179, 230, 255], atol=3)

        # 4. Ordered two-sided stencil + reversed-depth [1.0, 0.0] interaction (STA-01 / STA-02).
        color = gloo.Texture2D(np.zeros((8, 16, 4), dtype=np.uint8))
        packed = gloo.RenderBuffer((8, 16), format=0x88F0)
        fbo = gloo.FrameBuffer(color=color, depth=packed, stencil=packed)
        # Left half CCW (front-facing), right half CW (back-facing) at clip z = -0.25 -> reversed depth = 0.625.
        two_tris = gloo.VertexBuffer(
            np.array(
                [
                    [-1.0, -1.0, -0.25],
                    [0.0, -1.0, -0.25],
                    [-0.5, 1.0, -0.25],
                    [0.0, -1.0, -0.25],
                    [0.5, 1.0, -0.25],
                    [1.0, -1.0, -0.25],
                ],
                dtype=np.float32,
            )
        )
        objects.extend([color, packed, fbo, two_tris])
        prog["a_pos"] = two_tris

        with fbo:
            gloo.set_viewport(0, 0, 16, 8)
            gloo.set_state(blend=False, cull_face=False, depth_test=True, stencil_test=True)
            gloo.set_depth_range(1.0, 0.0)
            gloo.set_depth_func("greater")
            gloo.set_clear_depth(0.0)
            gloo.set_clear_stencil(5)
            gloo.set_stencil_mask(0xFF)
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True, stencil=True)

            gloo.set_stencil_func("always", 19, 0xFF, "front")
            gloo.set_stencil_func("always", 73, 0xFF, "back")
            gloo.set_stencil_op("keep", "keep", "replace", "front")
            gloo.set_stencil_op("keep", "keep", "replace", "back")
            prog["u_color"] = (0.0, 1.0, 0.0, 1.0)
            prog.draw("triangles")

            stencil = gloo.read_pixels((0, 0, 16, 8), mode="stencil", out_type="unsigned_byte", alpha=False)
            depth = gloo.read_pixels((0, 0, 16, 8), mode="depth", out_type="float")

        # Bottom-center of left triangle (x=4, y=1 in GL bottom-origin -> row 6) is CCW=19; right (x=12) is CW=73.
        assert int(stencil[6, 4, 0]) == 19
        assert int(stencil[6, 12, 0]) == 73
        assert int(stencil[0, 0, 0]) == 5
        assert float(depth[6, 4, 0]) == pytest.approx(0.625, abs=1e-3)
        assert float(depth[0, 0, 0]) == pytest.approx(0.0, abs=1e-4)
