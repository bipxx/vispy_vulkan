"""Public stencil/MSAA readback, FBO attachment, and raw gloo.gl refusal tests (SCI-06, API-05).

Verifies public gloo.read_pixels and FrameBuffer.read stencil/depth/color modes
across 1x and 4x MSAA targets, cropped viewports, FrameBuffer/RenderBuffer
resize and separate depth_component+stencil attachment refusal, and raw gloo.gl
immediate-mode refusals (glReadPixels GL_STENCIL_INDEX, glBindFramebuffer,
invalid glClear mask) with queued-draw survival and clean RGBA/stencil recovery.
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@contextmanager
def _headless_canvas(size=(12, 10), samples=0):
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


@pytest.mark.parametrize("samples", (0, 4))
def test_default_framebuffer_stencil_msaa_crop_and_raw_gl_refusal_recovery(samples):
    from vispy.gloo.gl.dawn import DawnCompatibilityError

    with _headless_canvas(size=(12, 10), samples=samples) as (_canvas, gloo, _dawn, objects):
        if samples == 4:
            assert int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES)) == 4

        quad = gloo.VertexBuffer(
            np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        )
        prog = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.extend([quad, prog])
        prog["a_pos"] = quad
        prog["u_color"] = (0.25, 0.75, 0.5, 1.0)

        # Clear full default framebuffer stencil=11, scissor interior (2, 2, 6, 4) stencil=93 + incr to 94.
        gloo.set_state(blend=False, depth_test=False, stencil_test=True, scissor_test=False)
        gloo.set_stencil_mask(0xFF)
        gloo.set_clear_stencil(11)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0), stencil=True)

        gloo.set_state(scissor_test=True)
        gloo.set_scissor(2, 2, 6, 4)
        gloo.set_clear_stencil(93)
        gloo.clear(color=False, depth=False, stencil=True)
        gloo.set_stencil_func("equal", 93, 0xFF)
        gloo.set_stencil_op("keep", "keep", "incr")
        # Note: prog.draw flushes, then we queue an un-flushed scissor clear to prove raw GL refusal leaves queue intact!
        prog.draw("triangle_strip")
        gloo.set_scissor(8, 1, 3, 2)
        gloo.set_clear_stencil(211)
        gloo.clear(color=False, depth=False, stencil=True)
        gloo.set_state(scissor_test=False)

        # Raw immediate OpenGL calls refuse synchronously without consuming or corrupting queued GLIR commands.
        for bad_call in (
            lambda: gloo.gl.glReadPixels(0, 0, 4, 4, 0x1901, gloo.gl.GL_UNSIGNED_BYTE),
            lambda: gloo.gl.glBindFramebuffer(gloo.gl.GL_FRAMEBUFFER, 0),
            lambda: gloo.gl.glClear(0x0200),
        ):
            with pytest.raises(DawnCompatibilityError):
                bad_call()
        assert int(gloo.gl.glGetError()) == int(gloo.gl.GL_NO_ERROR)

        # Subsequent public stencil and RGBA readbacks succeed with exact values across 1x and 4x MSAA!
        st_full = gloo.read_pixels((0, 0, 12, 10), mode="stencil", out_type="unsigned_byte", alpha=False)
        st_crop_f = gloo.read_pixels((2, 2, 6, 4), mode="stencil", out_type="float", alpha=True)
        rgba = gloo.read_pixels((0, 0, 12, 10), mode="color", out_type="unsigned_byte", alpha=True)

        assert st_full.shape == (10, 12, 1) and st_full.dtype == np.uint8
        assert st_crop_f.shape == (4, 6, 1) and st_crop_f.dtype == np.float32
        # Scissor (2, 2, 6, 4) in bottom-left origin maps to rows [10-6 : 10-2] = [4:8], cols [2:8].
        assert np.all(st_full[4:8, 2:8, 0] == 94)
        assert np.all(st_crop_f[:, :, 0] == 94.0)
        # Un-flushed scissor clear (8, 1, 3, 2) maps to rows [7:9], cols [8:11] == 211!
        assert np.all(st_full[7:9, 8:11, 0] == 211)
        assert int(st_full[0, 0, 0]) == 11
        np.testing.assert_allclose(rgba[5, 4], [64, 191, 128, 255], atol=2)
        np.testing.assert_allclose(rgba[0, 0], [0, 0, 0, 255], atol=2)


def test_framebuffer_renderbuffer_resize_crop_and_attachment_boundaries():
    with _headless_canvas(size=(10, 8), samples=0) as (_canvas, gloo, _dawn, objects):
        quad = gloo.VertexBuffer(
            np.array([[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        )
        prog = gloo.Program(
            "attribute vec2 a_pos; uniform float u_z; void main() { gl_Position = vec4(a_pos, u_z, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.extend([quad, prog])
        prog["a_pos"] = quad

        # 1. Separate depth_component Texture2D + stencil RenderBuffer on FrameBuffer is explicitly refused.
        bad_color = gloo.Texture2D(np.zeros((8, 10, 4), dtype=np.uint8))
        bad_depth = gloo.Texture2D(
            np.zeros((8, 10), dtype=np.float32),
            format="depth_component",
            internalformat="depth_component",
        )
        bad_stencil = gloo.RenderBuffer((8, 10), format="stencil")
        bad_fbo = gloo.FrameBuffer(color=bad_color, depth=bad_depth, stencil=bad_stencil)
        objects.extend([bad_color, bad_depth, bad_stencil, bad_fbo])

        with pytest.raises(RuntimeError, match="separate stencil with depth_component is unsupported"):
            with bad_fbo:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
                _canvas.context.finish()

        # 2. Color + depth_component Texture2D (without stencil) honors depth_test and disables stencil_test cleanly.
        depth_only_color = gloo.Texture2D(np.zeros((8, 10, 4), dtype=np.uint8))
        depth_only_tex = gloo.Texture2D(
            np.ones((8, 10), dtype=np.float32),
            format="depth_component",
            internalformat="depth_component",
        )
        depth_only_fbo = gloo.FrameBuffer(color=depth_only_color, depth=depth_only_tex)
        objects.extend([depth_only_color, depth_only_tex, depth_only_fbo])

        with depth_only_fbo:
            gloo.set_viewport(0, 0, 10, 8)
            gloo.set_state(depth_test=True, stencil_test=True, blend=False)
            gloo.set_stencil_func("never", 1, 0xFF)
            gloo.set_depth_func("less")
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)
            prog["u_z"] = -0.5
            prog["u_color"] = (1.0, 0.5, 0.0, 1.0)
            # Because depth_only_fbo has no stencil attachment, stencil_func('never') does not discard!
            prog.draw("triangle_strip")
            do_img = depth_only_fbo.read(mode="color", crop=(1, 1, 4, 3))
        assert do_img.shape == (3, 4, 4)
        np.testing.assert_allclose(do_img[1, 1], [255, 128, 0, 255], atol=2)

        # 3. RenderBuffer color + RenderBuffer stencil-only attachment + FrameBuffer.resize((new_h, new_w)).
        rb_color = gloo.RenderBuffer((6, 8), format="color")
        rb_stencil = gloo.RenderBuffer((6, 8), format="stencil")
        rb_fbo = gloo.FrameBuffer(color=rb_color, stencil=rb_stencil)
        objects.extend([rb_color, rb_stencil, rb_fbo])

        rb_fbo.resize((10, 14))
        assert rb_fbo.shape == (10, 14)
        with rb_fbo:
            gloo.set_viewport(0, 0, 14, 10)
            gloo.set_state(depth_test=False, stencil_test=True, blend=False)
            gloo.set_clear_stencil(7)
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0), stencil=True)
            gloo.set_stencil_func("always", 142, 0xFF)
            gloo.set_stencil_op("keep", "keep", "replace")
            prog["u_z"] = 0.0
            prog["u_color"] = (0.0, 1.0, 1.0, 1.0)
            prog.draw("triangle_strip")
            st_crop = rb_fbo.read(mode="stencil", alpha=False, crop=(3, 2, 5, 4))
            col_crop = rb_fbo.read(mode="color", alpha=False, crop=(3, 2, 5, 4))

        assert st_crop.shape == (4, 5, 1) and np.all(st_crop == 142)
        assert col_crop.shape == (4, 5, 3)
        np.testing.assert_allclose(col_crop[2, 2], [0, 255, 255], atol=2)
