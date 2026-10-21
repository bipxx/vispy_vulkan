"""Submission lifetime checks use owned-resource counters, not RSS guesses."""

import time

import numpy as np
import pytest

from vispy import _dawn, app, gloo

from tools.fixture_gloo import FRAG, FULL, VERT

pytestmark = pytest.mark.gpu


def solid_program():
    program = gloo.Program(VERT, FRAG)
    program["a_position"] = gloo.VertexBuffer(FULL)
    program["u_color"] = (1, 0, 0, 1)
    return program


def ready_for_frame(canvas):
    """Cooperate with the event loop while the bounded frame ring is full."""
    deadline = time.monotonic() + 3
    while not _dawn.frame_ready(canvas._backend._dawn_canvas_id):
        _dawn.process_events()
        assert time.monotonic() < deadline, "frame ring failed to become ready"
        time.sleep(.001)


def test_warm_present_has_no_deliberate_completion_waits_and_tickets_retire():
    canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 16, 16)
        program = solid_program()
        program.draw("triangles")
        _dawn.present(canvas._backend._dawn_canvas_id)
        _dawn.finish(canvas._backend._dawn_canvas_id)
        _dawn.process_events()
        before = _dawn.probe()
        peak_pending = 0
        peak_queued = 0
        for frame in range(36):
            ready_for_frame(canvas)
            program["u_color"] = (frame / 35, 0, 0, 1)
            program.draw("triangles")
            _dawn.present(canvas._backend._dawn_canvas_id)
            _dawn.process_events()
            progress = _dawn.probe()
            peak_pending = max(peak_pending, progress["pending_tickets"])
            peak_queued = max(peak_queued, progress["queued_frames"])
        hot = _dawn.probe()
        assert hot["completion_waits"] == before["completion_waits"]
        assert hot["finish_calls"] == before["finish_calls"]
        assert hot["application_presents"] - before["application_presents"] <= 36
        assert peak_pending <= 3 and peak_queued <= 3
        _dawn.finish(canvas._backend._dawn_canvas_id)
        _dawn.process_events()
        completed = _dawn.probe()
        assert completed["pending_tickets"] == 0
        assert completed["queued_frames"] == 0
        assert completed["application_presents"] - before["application_presents"] == 36
        assert completed["retired_tickets"] > before["retired_tickets"]
        assert completed["completion_waits"] > hot["completion_waits"]
        print("warm presents", 36, "completion waits", hot["completion_waits"] - before["completion_waits"],
              "peak tickets", peak_pending, "retired", completed["retired_tickets"] - before["retired_tickets"])
    finally:
        canvas.close()


def test_repeated_texture_and_buffer_generations_have_bounded_live_allocations():
    canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
    canvas.set_current()
    gloo.set_viewport(0, 0, 16, 16)
    base = _dawn.probe()
    texture_bytes = 64 * 64 * 4
    texture = gloo.Texture2D(np.zeros((64, 64, 4), np.uint8))
    program = gloo.Program(VERT, """
        uniform sampler2D u_texture;
        void main() { gl_FragColor = texture2D(u_texture, vec2(0.5)); }
        """)
    program["a_position"] = gloo.VertexBuffer(FULL)
    program["u_texture"] = texture
    peak_pending = 0
    try:
        for frame in range(96):
            ready_for_frame(canvas)
            texture.set_data(np.full((64, 64, 4), [frame, 0, 0, 255], np.uint8))
            program["a_position"].set_data(FULL)
            program.draw("triangles")
            _dawn.present(canvas._backend._dawn_canvas_id)
            _dawn.process_events()
            current = _dawn.probe()
            peak_pending = max(peak_pending, current["pending_tickets"])
        image = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        _dawn.process_events()
        complete = _dawn.probe()
        assert np.all(image == [95, 0, 0, 255])
        assert peak_pending <= 3 and complete["pending_tickets"] == 0
        assert complete["retired_tickets"] > base["retired_tickets"]
        # Counters measure renderer-owned buffer/texture allocation versions.
        # The bound includes a resident version plus at most three in flight.
        assert complete["live_texture_bytes"] - base["live_texture_bytes"] <= 4 * texture_bytes + 16 * 16 * 4
        assert complete["live_buffer_bytes"] - base["live_buffer_bytes"] <= 4 * FULL.nbytes + 4096
        program["a_position"].delete()
        texture.delete()
        program.delete()
        canvas.context.flush_commands()
        _dawn.finish(canvas._backend._dawn_canvas_id)
        _dawn.process_events()
        print("resource generations", 96, "peak tickets", peak_pending,
              "live texture bytes", complete["live_texture_bytes"] - base["live_texture_bytes"],
              "live buffer bytes", complete["live_buffer_bytes"] - base["live_buffer_bytes"])
    finally:
        canvas.close()


def test_close_with_submitted_work_drains_owned_callbacks():
    before = _dawn.probe()
    for _ in range(12):
        canvas = app.Canvas(app="dawn_headless", size=(32, 32), show=False)
        canvas.set_current()
        gloo.set_viewport(0, 0, 32, 32)
        solid_program().draw("triangles")
        _dawn.present(canvas._backend._dawn_canvas_id)
        canvas.close()
        _dawn.process_events()
    after = _dawn.probe()
    assert after["pending_tickets"] == 0
    assert after["retired_tickets"] > before["retired_tickets"]


def test_existing_program_and_data_survive_device_generation_change():
    canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
    recovery = None
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 16, 16)
        program = solid_program()
        program.draw("triangles")
        before = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        assert np.all(before == [255, 0, 0, 255])
        _dawn.lose_device()
        recovery = app.Canvas(app="dawn_headless", size=(2, 2), show=False)
        assert _dawn.device_info()["ok"]
        canvas.set_current()
        program.draw("triangles")
        after = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        assert np.array_equal(before, after)
        program["u_color"] = (0, 1, 0, 1)
        program.draw("triangles")
        changed = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        assert np.all(changed == [0, 255, 0, 255])
    finally:
        if recovery is not None:
            recovery.close()
        canvas.close()
