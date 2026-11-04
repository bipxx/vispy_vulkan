# SPDX-License-Identifier: AGPL-3.0-only
"""Native presentation under vsync paces like OpenGL's swap (plan P2; user, 2026-10-30 and 2026-10-31).

A vsynced surface presents through FIFO. A frame produced in less than one refresh interval, counted from the
previous paced paint's return, returns once its own frame's GPU work has retired, so presented frames cannot queue
ahead of the display. A slower frame cannot outrun the display: its paint returns once the previous frame has retired,
so at most one frame is still in flight, as OpenGL's driver lets one frame render ahead. The waits are counted as
present_pacing_waits and present_render_ahead_waits, never as completion_waits or finish_calls, which the frame
benchmark's measured-work gate forbids. Without vsync, and on a headless canvas, nothing waits.
"""
import os
import sys
import time

import pytest

pytestmark = pytest.mark.gpu
FRAMES = 12
EVERY_FRAME_FAST = 10_000_000_000  # a 10 s refresh interval: every frame is produced within one refresh
qt_api = os.environ.get("QT_API", "pyqt6")


def paint(monkeypatch, vsync, phases):
    """Attach a 64x48 Qt canvas with 3 paints, then paint each phase of (frames, seconds slept in every draw,
    refresh interval override in ns, 0 for the display's). Per phase, return the surface info, the probe before and
    after, and the frames in flight after each paint."""
    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'native')
    from vispy import _dawn, app, gloo
    canvas = app.Canvas(app=qt_api, size=(64, 48), show=True, vsync=vsync)
    painted, delay = [], [0.0]

    @canvas.events.draw.connect
    def draw(event):
        if delay[0]:
            time.sleep(delay[0])
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

    results = []
    try:
        canvas_id = int(canvas.native._dawn_canvas_id)
        for _ in range(3):  # attach and configure the surface
            one_paint()
        for frames, seconds, interval_ns in phases:
            _dawn.diagnostic_present_refresh_interval(canvas_id, interval_ns)
            delay[0] = seconds
            surface, before, in_flight = _dawn.benchmark_surface_info(canvas_id), _dawn.probe(), []
            for _ in range(frames):
                one_paint()
                in_flight.append(_dawn.probe()['pending_tickets'])  # probe() retires completed tickets first
            results.append((surface, before, _dawn.probe(), in_flight))
    finally:
        canvas.close()
    return results


def assert_no_forbidden_waits(before, after):
    assert after['present_pacing_timeouts'] == before['present_pacing_timeouts']
    for name in ('completion_waits', 'finish_calls'):
        assert after[name] == before[name], name


def ready_for_frame(canvas):
    """Cooperate with the event loop while the bounded frame ring is full (tests/native/test_submission_lifetime.py)."""
    from vispy import _dawn
    deadline = time.monotonic() + 3
    while not _dawn.frame_ready(canvas._backend._dawn_canvas_id):
        _dawn.process_events()
        assert time.monotonic() < deadline, "frame ring failed to become ready"
        time.sleep(.001)


def test_a_vsynced_native_paint_returns_after_its_frame_retires(monkeypatch):
    [(surface, before, after, in_flight)] = paint(monkeypatch, True, [(FRAMES, 0.0, EVERY_FRAME_FAST)])
    assert surface['attached'] and surface['vsync_requested'] and surface['present_mode'] == 'fifo'
    assert surface['refresh_interval_source'] == 'diagnostic' and surface['refresh_interval_ns'] == EVERY_FRAME_FAST
    assert in_flight == [0] * FRAMES
    assert after['application_presents'] - before['application_presents'] >= FRAMES
    assert after['present_pacing_waits'] > before['present_pacing_waits']
    assert after['present_pacing_wait_ns'] > before['present_pacing_wait_ns']
    assert after['present_render_ahead'] == before['present_render_ahead']
    assert_no_forbidden_waits(before, after)


def test_a_vsynced_paint_slower_than_a_refresh_renders_one_frame_ahead(monkeypatch):
    slow, fast = paint(monkeypatch, True, [(FRAMES, 0.1, 0), (4, 0.0, EVERY_FRAME_FAST)])
    surface, before, after, in_flight = slow
    # The display's refresh interval (a 60 Hz default where the platform reports none) is under the 0.1 s each
    # frame takes, so every paint returns before its frame retires, once the previous frame has.
    assert surface['refresh_interval_source'] == ('display' if sys.platform == 'win32' else 'default')
    assert 1_000_000 <= surface['refresh_interval_ns'] < 50_000_000
    assert after['present_render_ahead'] - before['present_render_ahead'] == FRAMES
    assert after['present_pacing_waits'] == before['present_pacing_waits']
    assert max(in_flight) <= 1
    assert_no_forbidden_waits(before, after)
    # Frames produced within a refresh wait for their own frame again.
    surface, before, after, in_flight = fast
    assert in_flight == [0] * 4
    assert after['present_render_ahead'] == before['present_render_ahead']
    assert_no_forbidden_waits(before, after)


def test_unpaced_native_and_headless_frames_do_not_wait(monkeypatch):
    [(surface, before, after, _)] = paint(monkeypatch, False, [(FRAMES, 0.0, 0)])
    assert surface['attached'] and not surface['vsync_requested']
    assert after['application_presents'] - before['application_presents'] >= FRAMES
    for name in ('present_pacing_waits', 'present_render_ahead'):
        assert after[name] == before[name], name
    from vispy import _dawn, app, gloo
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), show=False)
    with canvas:
        before = _dawn.probe()
        for index in range(FRAMES):
            ready_for_frame(canvas)
            gloo.clear(color=(index % 2, 0, 0, 1))
            gloo.flush()
        after = _dawn.probe()
    canvas.close()
    assert after['dawn_queue_submits'] - before['dawn_queue_submits'] >= FRAMES
    for name in ('present_pacing_waits', 'present_render_ahead'):
        assert after[name] == before[name], name
