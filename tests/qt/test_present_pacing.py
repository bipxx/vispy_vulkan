# SPDX-License-Identifier: AGPL-3.0-only
"""Native presentation under vsync paces like OpenGL's blocking swap (plan P2; user, 2026-10-30).

A vsynced surface presents through FIFO, and its paint returns once its own frame's GPU work has retired. So no
presented frame is still in flight when the paint returns, and frames cannot queue ahead of the display. The wait is
counted as present_pacing_waits, never as completion_waits or finish_calls, which the frame benchmark's measured-work
gate forbids. Without vsync, and on a headless canvas, nothing waits.
"""
import os
import time

import pytest

pytestmark = pytest.mark.gpu
FRAMES = 12
qt_api = os.environ.get("QT_API", "pyqt6")


def paint(monkeypatch, vsync):
    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'native')
    from vispy import _dawn, app, gloo
    canvas = app.Canvas(app=qt_api, size=(64, 48), show=True, vsync=vsync)
    painted = []

    @canvas.events.draw.connect
    def draw(event):
        gloo.set_clear_color((len(painted) % 2, 0.5, 1, 1))
        gloo.clear()
        painted.append(event)

    def one_paint():
        count = len(painted)
        canvas.update()
        deadline = time.monotonic() + 5
        while len(painted) == count:
            assert time.monotonic() < deadline, 'no paint'
            canvas.app.process_events()

    try:
        for _ in range(3):  # attach and configure the surface
            one_paint()
        surface = _dawn.benchmark_surface_info(int(canvas.native._dawn_canvas_id))
        before, in_flight = _dawn.probe(), []
        for _ in range(FRAMES):
            one_paint()
            in_flight.append(_dawn.probe()['pending_tickets'])  # probe() retires completed tickets first
        after = _dawn.probe()
    finally:
        canvas.close()
    return surface, before, after, in_flight


def test_a_vsynced_native_paint_returns_after_its_frame_retires(monkeypatch):
    surface, before, after, in_flight = paint(monkeypatch, True)
    assert surface['attached'] and surface['vsync_requested'] and surface['present_mode'] == 'fifo'
    assert in_flight == [0] * FRAMES
    assert after['application_presents'] - before['application_presents'] >= FRAMES
    assert after['present_pacing_waits'] > before['present_pacing_waits']
    assert after['present_pacing_wait_ns'] > before['present_pacing_wait_ns']
    assert after['present_pacing_timeouts'] == before['present_pacing_timeouts']
    for name in ('completion_waits', 'finish_calls'):
        assert after[name] == before[name], name


def test_unpaced_native_and_headless_frames_do_not_wait(monkeypatch):
    surface, before, after, _ = paint(monkeypatch, False)
    assert surface['attached'] and not surface['vsync_requested']
    assert after['application_presents'] - before['application_presents'] >= FRAMES
    assert after['present_pacing_waits'] == before['present_pacing_waits']
    from vispy import _dawn, app, gloo
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), show=False)
    with canvas:
        before = _dawn.probe()
        for index in range(FRAMES):
            gloo.clear(color=(index % 2, 0, 0, 1))
            gloo.flush()
        after = _dawn.probe()
    canvas.close()
    assert after['dawn_queue_submits'] - before['dawn_queue_submits'] >= FRAMES
    assert after['present_pacing_waits'] == before['present_pacing_waits']
