# SPDX-License-Identifier: AGPL-3.0-only
"""GL-shaped state operations must preserve actual GLIR rendering order."""
import numpy as np
import pytest

from vispy import app, gloo
from vispy.gloo import gl
from vispy.gloo.gl.dawn import DawnCompatibilityError

pytestmark = pytest.mark.gpu


def test_raw_clear_and_scissor_preserve_queued_gloo_work():
    canvas = app.Canvas(app='dawn_headless', size=(12, 8))
    try:
        canvas.set_current()
        gl.glViewport(0, 0, 12, 8)
        assert canvas.context.get_viewport() == (0, 0, 12, 8)
        gloo.clear(color='blue')  # Queued before the raw state changes.
        gl.glScissor(0, 0, 6, 8)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glClearColor(1, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glFinish()
        image = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        assert np.all(image[:, :6] == [255, 0, 0, 255])
        assert np.all(image[:, 6:] == [0, 0, 255, 255])
        assert gl.glGetError() == gl.GL_NO_ERROR
    finally:
        canvas.close()


def test_raw_state_respects_framebuffer_binding_and_canvas_selection():
    first = app.Canvas(app='dawn_headless', size=(8, 8))
    second = app.Canvas(app='dawn_headless', size=(8, 8))
    try:
        first.set_current()
        gloo.set_viewport(0, 0, 8, 8)
        gloo.clear(color='blue')
        color = gloo.Texture2D(np.zeros((8, 8, 4), dtype=np.uint8))
        target = gloo.FrameBuffer(color=color)
        with target:
            gl.glClearColor(1, 0, 0, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [255, 0, 0, 255])
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 0, 255, 255])
        second.set_current()
        gl.glViewport(0, 0, 8, 8)
        gl.glClearColor(0, 1, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 255, 0, 255])
        first.set_current()
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 0, 255, 255])
        target.delete()
        color.delete()
        first.context.flush_commands()
    finally:
        first.close()
        second.close()


def test_raw_color_mask_and_invalid_state_are_not_silently_ignored():
    canvas = app.Canvas(app='dawn_headless', size=(8, 8))
    try:
        canvas.set_current()
        gl.glViewport(0, 0, 8, 8)
        gloo.clear(color=(0, 0, 1, 1))
        gl.glColorMask(True, False, False, False)
        gl.glClearColor(1, 1, 0, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        image = gloo.read_pixels((0, 0, 8, 8), alpha=True)
        assert np.all(image == [255, 0, 255, 255])
        with pytest.raises(RuntimeError, match='glViewport'):
            gl.glViewport(0, 0, -1, 8)
        assert canvas.context.get_viewport() == (0, 0, 8, 8)
        gl.glColorMask(True, True, True, True)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [255, 255, 0, 0])
        with pytest.raises(DawnCompatibilityError, match='glCreateProgram'):
            gl.glCreateProgram()
        with pytest.raises(DawnCompatibilityError, match='glDrawArrays'):
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
        with pytest.raises(DawnCompatibilityError, match='buffer mask'):
            gl.glClear(1)
    finally:
        canvas.close()
    with pytest.raises(DawnCompatibilityError, match='current Dawn canvas'):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
