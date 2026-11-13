"""Closing the native window retires its canvas while a shared peer still draws."""

import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def test_native_window_close_releases_owner_and_preserves_shared_peer():
    from vispy import _dawn, app, gloo

    application = app.use_app('pyqt6')
    first = app.Canvas(app='pyqt6', size=(24, 18), show=False, vsync=False)
    second = app.Canvas(app='pyqt6', size=(24, 18), shared=first, show=False, vsync=False)
    program = gloo.Program(
        'attribute vec2 a_position; void main() { gl_Position=vec4(a_position,0.,1.); }',
        'uniform vec4 u_color; void main() { gl_FragColor=u_color; }')
    vertices = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    program['a_position'] = vertices
    program['u_color'] = (1., 0., 0., 1.)
    draws = [0, 0]
    closes = []

    def draw(index, canvas):
        def paint(event):
            draws[index] += 1
            gloo.set_viewport(0, 0, *canvas.physical_size)
            gloo.set_state(depth_test=False, stencil_test=False, blend=False, cull_face=False)
            gloo.clear(color=(0., 0., 0., 1.))
            program.draw('triangles')
        return paint

    first.events.close.connect(lambda event: closes.append('first'))
    for index, canvas in enumerate((first, second)):
        canvas.events.draw.ignore_callback_errors = False
        canvas.events.draw.connect(draw(index, canvas))

    def pump_until(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            _dawn.process_events()
            assert time.monotonic() < deadline, 'shared close recovery timed out'
            time.sleep(.001)

    native = first.native
    try:
        first.show()
        second.show()
        pump_until(lambda: all(draws))
        _dawn.finish(second.native._dawn_canvas_id)
        assert native.close()
        application.process_events()
        assert first._closed and native._dawn_closed and closes == ['first']
        assert native.context() is None
        # Queued Qt work cannot revive the retired canvas.
        native.resizeGL(24, 18)
        native.paintEvent(None)
        native._poll_dawn()
        native.close()
        assert closes == ['first']
        before = draws[1]
        program['u_color'] = (0., 1., 0., 1.)
        second.update()
        pump_until(lambda: draws[1] > before)
        second.set_current()
        _dawn.finish(second.native._dawn_canvas_id)
        np.testing.assert_array_equal(
            _dawn.read_pixels(second.native._dawn_canvas_id, 0, 0, 2, 2, True),
            np.full((2, 2, 4), [0, 255, 0, 255], dtype=np.uint8))
        program.delete()
        vertices.delete()
        second.context.flush_commands()
    finally:
        first.close()
        second.close()
        application.process_events()
        _dawn.process_events()
    gauges = {name: _dawn.probe()[name] for name in (
        'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
        'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
        'line_resource_pool_busy_slots', 'line_resource_pool_bytes')}
    assert not any(gauges.values()), gauges
    print('native close callback once; late events ignored; shared peer green; shutdown gauges', gauges)


def test_pending_peer_snapshot_survives_parsed_deletes_and_other_window_close():
    from vispy import _dawn, app, gloo

    application = app.use_app('pyqt6')
    first = app.Canvas(app='pyqt6', size=(24, 18), show=False)
    peer = app.Canvas(app='pyqt6', size=(24, 18), shared=first, show=False)
    program = gloo.Program(
        'attribute vec2 a_position; void main() { gl_Position=vec4(a_position,0.,1.); }',
        'void main() { gl_FragColor=vec4(0.,1.,0.,1.); }')
    vertices = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    program['a_position'] = vertices
    try:
        peer.set_current()
        gloo.set_viewport(0, 0, *peer.physical_size)
        gloo.set_state(depth_test=False, stencil_test=False, blend=False, cull_face=False)
        gloo.clear(color=(0., 0., 0., 1.))
        program.draw('triangles')
        # Keep a real immutable native draw snapshot pending while erasing its
        # original namespace entries; no finish/readback before peer close.
        assert _dawn.probe()['pending_draws'] > 0
        program.delete()
        vertices.delete()
        peer.context.flush_commands()
        assert first.native.close()
        assert first._closed and first.native._dawn_closed
        _dawn.present(peer.native._dawn_canvas_id)
        _dawn.finish(peer.native._dawn_canvas_id)
        np.testing.assert_array_equal(
            _dawn.read_pixels(peer.native._dawn_canvas_id, 0, 0, 2, 2, True),
            np.full((2, 2, 4), [0, 255, 0, 255], dtype=np.uint8))
    finally:
        first.close()
        peer.close()
        application.process_events()
        _dawn.process_events()
    gauges = {name: _dawn.probe()[name] for name in (
        'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
        'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
        'line_resource_pool_busy_slots', 'line_resource_pool_bytes')}
    assert not any(gauges.values()), gauges
    print('pending peer snapshot survives parsed DELETE and native close; exact green pixels; gauges', gauges)
