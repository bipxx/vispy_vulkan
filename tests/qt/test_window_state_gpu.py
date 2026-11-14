"""Real Qt minimize/restore must stop submission and recover rendered content."""

import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def test_same_size_minimize_stops_submissions_then_restores_pixels():
    from vispy import _dawn, app, gloo

    application = app.use_app('pyqt6')
    canvas = app.Canvas(app='pyqt6', size=(40, 30), show=False, vsync=False)
    native = canvas.native
    canvas_id = int(native._dawn_canvas_id)
    color = [1., 0., 0., 1.]
    draws = []

    def draw(event):
        draws.append(tuple(color))
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color=color, depth=True)

    canvas.events.draw.ignore_callback_errors = False
    canvas.events.draw.connect(draw)

    def pump_until(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            _dawn.process_events()
            assert time.monotonic() < deadline, 'Qt state transition timed out'
            time.sleep(.001)

    try:
        canvas.show()
        pump_until(lambda: bool(draws))
        _dawn.finish(canvas_id)
        application.process_events()
        initial_size = tuple(canvas.physical_size)
        canvas.set_current()
        np.testing.assert_array_equal(
            _dawn.read_pixels(canvas_id, 0, 0, 2, 2, True),
            np.full((2, 2, 4), [255, 0, 0, 255], dtype=np.uint8))

        native.showMinimized()
        pump_until(native.isMinimized)
        application.process_events()
        before = dict(_dawn.probe())
        before_draws = len(draws)
        color[:] = [0., 1., 0., 1.]
        for _ in range(8):
            canvas.update()
            application.process_events()
            _dawn.process_events()
        suspended = dict(_dawn.probe())
        assert len(draws) == before_draws
        assert suspended['application_presents'] == before['application_presents']
        assert suspended['dawn_queue_submits'] == before['dawn_queue_submits']
        assert suspended['pending_tickets'] == suspended['queued_frames'] == 0

        native.showNormal()
        pump_until(lambda: len(draws) > before_draws)
        _dawn.finish(canvas_id)
        assert tuple(canvas.physical_size) == initial_size
        config = _dawn.framebuffer_config(canvas_id)
        assert (config['width'], config['height']) == initial_size
        np.testing.assert_array_equal(
            _dawn.read_pixels(canvas_id, 0, 0, 2, 2, True),
            np.full((2, 2, 4), [0, 255, 0, 255], dtype=np.uint8))
        assert _dawn.probe()['application_presents'] > suspended['application_presents']
        print('minimize: no draw/present/submit; restore: same size and exact green pixels',
              'device', _dawn.device_info())
    finally:
        canvas.close()
        application.process_events()
        _dawn.process_events()
    closed = _dawn.probe()
    assert closed['pending_tickets'] == closed['queued_frames'] == 0
