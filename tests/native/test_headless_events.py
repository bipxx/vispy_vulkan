"""Headless updates and timers must cause real nonblocking presented frames."""

import time

import numpy as np
import pytest

from vispy import _dawn, app, gloo

from tools.fixture_gloo import FRAG, FULL

pytestmark = pytest.mark.gpu
VERT = """
attribute vec2 a_position;
uniform vec2 u_scale;
uniform vec2 u_shift;
void main() { gl_Position = vec4(a_position * u_scale + u_shift, 0.0, 1.0); }
"""


def prepared_canvas():
    canvas = app.Canvas(app="dawn_headless", size=(12, 8), show=False)
    canvas.set_current()
    gloo.set_viewport(0, 0, 12, 8)
    program = gloo.Program(VERT, FRAG)
    program["a_position"] = gloo.VertexBuffer(FULL)
    program["u_color"] = (1, 0, 0, 1)
    program["u_scale"] = (1, 1)
    program["u_shift"] = (0, 0)
    program.draw("triangles")
    _dawn.present(canvas._backend._dawn_canvas_id)
    _dawn.finish(canvas._backend._dawn_canvas_id)
    _dawn.process_events()
    return canvas, program


def process_until(canvas, condition):
    deadline = time.monotonic() + 3
    while not condition():
        canvas.app.process_events()
        assert time.monotonic() < deadline, "headless event loop did not deliver the requested frame"
        time.sleep(.001)


def assert_interactive_counters(before, after, frames):
    assert after["completion_waits"] == before["completion_waits"]
    assert after["finish_calls"] == before["finish_calls"]
    assert after["application_presents"] - before["application_presents"] <= frames
    assert after["buffer_uploads"] == before["buffer_uploads"]
    assert after["texture_uploads"] == before["texture_uploads"]
    assert after["pending_tickets"] <= 3


def test_update_coalesces_requests_but_delivers_real_color_changes():
    canvas, program = prepared_canvas()
    draws = []

    def draw(event):
        draws.append(tuple(program["u_color"]))
        program.draw("triangles")

    canvas.events.draw.connect(draw)
    try:
        before = _dawn.probe()
        program["u_scale"] = (.5, 1)
        program["u_shift"] = (-.5, 0)
        program["u_color"] = (0, 1, 0, 1)
        for _ in range(5):
            canvas.update()
        process_until(canvas, lambda: len(draws) == 1)
        program["u_color"] = (0, 0, 1, 1)
        program["u_shift"] = (.5, 0)
        canvas.update()
        process_until(canvas, lambda: len(draws) == 2)
        hot = _dawn.probe()
        assert draws == [(0, 1, 0, 1), (0, 0, 1, 1)]
        assert_interactive_counters(before, hot, 2)
        # Only the final capture waits. Both ordinary frames precede it.
        image = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        assert np.all(image[:, :6] == [0, 255, 0, 255])
        assert np.all(image[:, 6:] == [0, 0, 255, 255])
        assert _dawn.probe()["application_presents"] - before["application_presents"] == 2
        print("headless update", len(draws), "real frames, 0 GPU completion waits")
    finally:
        canvas.close()


def test_timer_updates_render_all_three_requested_frames():
    canvas, program = prepared_canvas()
    ticks, draws = [], []
    colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]

    def draw(event):
        draws.append(tuple(program["u_color"]))
        program.draw("triangles")

    def tick(event):
        ticks.append(event.iteration)
        program["u_color"] = colors[event.iteration]
        program["u_scale"] = (1 / 3, 1)
        program["u_shift"] = ((event.iteration - 1) * 2 / 3, 0)
        canvas.update()

    canvas.events.draw.connect(draw)
    timer = None
    try:
        before = _dawn.probe()
        timer = app.Timer(interval=.005, iterations=3, connect=tick,
                          start=True, app=canvas.app)
        process_until(canvas, lambda: not timer.running and len(draws) == 3)
        hot = _dawn.probe()
        assert ticks == [0, 1, 2] and draws == colors
        assert_interactive_counters(before, hot, 3)
        image = gloo.read_pixels((0, 0, 12, 8), alpha=True)
        for index, color in enumerate(([255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255])):
            assert np.all(image[:, index * 4:(index + 1) * 4] == color)
        assert _dawn.probe()["application_presents"] - before["application_presents"] == 3
        print("headless timer", len(ticks), "ticks,", len(draws), "real frames, 0 GPU completion waits")
    finally:
        if timer is not None:
            timer.stop()
        canvas.close()
