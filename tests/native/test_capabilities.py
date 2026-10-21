"""Reported native limits must describe real, enabled device allocations."""

import numpy as np
import pytest

from vispy import _dawn, app, gloo

from tools.fixture_gloo import FULL, VERT

pytestmark = pytest.mark.gpu


def sample(texture):
    program = gloo.Program(VERT, """
        uniform sampler2D u_texture;
        void main() { gl_FragColor = texture2D(u_texture, vec2(0.5)); }
        """)
    program["a_position"] = gloo.VertexBuffer(FULL)
    program["u_texture"] = texture
    return program


def test_texture_dimension_at_reported_limit_allocates_and_above_limit_fails():
    info = _dawn.device_info()
    limit = info["max_texture_dimension_2d"]
    assert limit >= 8192
    canvas = app.Canvas(app="dawn_headless", size=(2, 2), show=False)
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 2, 2)
        texture = gloo.Texture2D(np.full((1, limit, 4), [0, 255, 0, 255], np.uint8))
        sample(texture).draw("triangles")
        image = gloo.read_pixels((0, 0, 2, 2), alpha=True)
        assert np.all(image == [0, 255, 0, 255]), (limit, image)
        # The Python object carries the descriptor; validation must reject the
        # oversized native allocation before an error handle reaches a draw.
        oversized = gloo.Texture2D(shape=(1, limit + 1, 4))
        with pytest.raises(RuntimeError, match="(?i)limit|dimension|size"):
            sample(oversized).draw("triangles")
            gloo.read_pixels((0, 0, 2, 2), alpha=True)
        print("granted dimension", limit, "allocation succeeded; above-limit rejected")
    finally:
        canvas.close()


def test_unsupported_glir_operation_is_contextual_error():
    canvas = app.Canvas(app="dawn_headless", size=(2, 2), show=False)
    try:
        with pytest.raises(RuntimeError, match="glUnknownFixtureCommand"):
            _dawn.execute(canvas._backend._dawn_canvas_id,
                          [("FUNC", "glUnknownFixtureCommand", 1)], [])
    finally:
        canvas.close()


def test_host_gl_backend_selection_preserves_queries_on_existing_and_new_canvases():
    import vispy
    from vispy.util import config

    previous = config['gl_backend']
    canvas = app.Canvas(app="dawn_headless", size=(2, 2), show=False)
    second = None
    try:
        for backend in ('gl+', 'gl2', 'gl+ debug'):
            vispy.use(gl=backend)
            # napari makes these queries after selecting gl+ on import.
            assert gloo.gl.glGetParameter(gloo.gl.GL_MAX_TEXTURE_SIZE) == _dawn.device_info()['max_texture_dimension_2d']
            assert gloo.gl.glGetParameter(gloo.gl.GL_RENDERER) == _dawn.device_info()['device']
            assert gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES) == 0
            with pytest.raises(RuntimeError, match='unsupported GL query'):
                gloo.gl.glGetParameter(0x7FFFFFFF)
        canvas.set_current()
        gloo.set_viewport(0, 0, 2, 2)
        gloo.clear(color=(0, 1, 0, 1))
        assert np.all(gloo.read_pixels((0, 0, 2, 2), alpha=True) == [0, 255, 0, 255])
        second = app.Canvas(app="dawn_headless", size=(2, 2), show=False, config={'samples': 4})
        second.set_current()
        assert gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES) == 4
        print('host GL selection retains native capabilities, capture and per-canvas sample queries')
    finally:
        if second is not None:
            second.close()
        canvas.close()
        vispy.use(gl=previous)
