# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""Public app entry points on the real offscreen Dawn backend."""

import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

from vispy import _dawn, app, gloo
from vispy.app import _default_app

pytestmark = pytest.mark.gpu
SIZE = (24, 16)
RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)


@pytest.fixture
def default_app(monkeypatch):
    monkeypatch.setattr(_default_app, "default_app", None)
    monkeypatch.setenv("_VISPY_TESTING_APP", "dawn_headless")
    monkeypatch.delenv("_VISPY_RUNNING_GALLERY_EXAMPLES", raising=False)


def pump_until(predicate):
    deadline = time.monotonic() + 3
    while not predicate():
        assert time.monotonic() < deadline, "headless event pump timed out"
        app.process_events()
        time.sleep(0.001)


def read_clear(canvas, color):
    gloo.set_viewport(0, 0, *canvas.physical_size)
    gloo.clear(color=color)
    return gloo.read_pixels()


def assert_frame(frame, size, color):
    width, height = size
    assert frame.shape == (height, width, 4)
    assert frame.dtype == np.uint8
    np.testing.assert_array_equal(frame, np.broadcast_to(np.array(color) * 255, frame.shape))


def run_with_watchdog(application, run):
    def fail(event):
        raise TimeoutError("headless blocking loop timed out")

    timer = app.Timer(interval=3, app=application, connect=fail)
    timer.events.timeout.ignore_callback_errors = False
    timer.start()
    try:
        return run()
    finally:
        if timer.running:
            timer.stop()

def test_application_create_identity():
    application = app.Application("dawn_headless")
    native = application.native
    assert application.create() is None
    assert application.native is native
    with app.Canvas(app=application, size=SIZE) as canvas:
        assert canvas.app is application
        assert canvas.app.native is native


def test_application_blocking_draw_failure_and_reentry(default_app):
    application = app.use_app("dawn_headless")
    with app.Canvas(size=SIZE, autoswap=False) as canvas:
        error = RuntimeError("failed draw in Application.run")
        canvas.events.draw.ignore_callback_errors = False

        def fail(event):
            raise error

        canvas.events.draw.connect(fail)
        canvas.update()
        with pytest.raises(RuntimeError) as caught:
            run_with_watchdog(application, lambda: application.run(allow_interactive=False))
        assert caught.value is error
        canvas.events.draw.disconnect(fail)
        frames = []

        def recover(event):
            frames.append(read_clear(canvas, GREEN))
            application.quit()

        canvas.events.draw.connect(recover)
        canvas.update()
        run_with_watchdog(application, lambda: application.run(allow_interactive=False))
        assert len(frames) == 1
        assert_frame(frames[0], SIZE, GREEN)


def test_create_materializes_one_native_default(default_app):
    assert _default_app.default_app is None
    app.create()
    application = app.use_app()
    native = application.native
    app.create()
    with app.Canvas(size=SIZE) as canvas:
        assert canvas.app is application
        assert canvas.app.native is native
        assert canvas.physical_size == SIZE


def test_create_retries_native_startup(default_app, monkeypatch):
    from vispy.app.backends import _dawn_headless

    error = RuntimeError("injected native startup failure")
    calls = []

    def fail(backend):
        calls.append(backend)
        raise error

    with monkeypatch.context() as patch:
        patch.setattr(_dawn_headless.ApplicationBackend, "_vispy_get_native_app", fail)
        with pytest.raises(RuntimeError) as caught:
            app.create()
    assert caught.value is error
    app.create()
    with app.Canvas(size=SIZE) as canvas:
        assert calls == [canvas.app.native]
        assert canvas.app is app.use_app()


def test_process_events_delivers_queued_draw(default_app):
    app.create()
    with app.Canvas(size=SIZE, autoswap=False) as canvas:
        frames = []
        canvas.events.draw.connect(lambda event: frames.append(read_clear(canvas, RED)))
        canvas.update()
        canvas.update()
        assert frames == []
        pump_until(lambda: frames)
        app.process_events()
        assert len(frames) == 1
        assert_frame(frames[0], SIZE, RED)


def test_process_events_recovers_after_draw_error(default_app):
    app.create()
    with app.Canvas(size=SIZE, autoswap=False) as canvas:
        error = ValueError("queued draw failed")
        frames = []
        invocations = []
        canvas.events.draw.ignore_callback_errors = False

        def draw(event):
            invocations.append(event.type)
            if len(invocations) == 1:
                raise error
            frames.append(read_clear(canvas, GREEN))

        canvas.events.draw.connect(draw)
        canvas.update()
        with pytest.raises(ValueError) as caught:
            pump_until(lambda: invocations)
        assert caught.value is error
        canvas.update()
        pump_until(lambda: frames)
        assert invocations == ["draw", "draw"]
        assert_frame(frames[0], SIZE, GREEN)


def test_run_and_quit_from_timer_in_bounded_process():
    env = os.environ.copy()
    env.pop("_VISPY_RUNNING_GALLERY_EXAMPLES", None)
    result = subprocess.run(
        [sys.executable, "-B", "-S", str(Path(__file__).resolve()), "run"],
        env=env, capture_output=True, text=True, timeout=90, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def run_from_timer():
    app.use_app("dawn_headless")
    with app.Canvas(size=SIZE, autoswap=False) as canvas:
        frames = []
        ticks = []
        timer = app.Timer(interval=0.001)

        def tick(event):
            ticks.append(event.iteration)
            timer.stop()
            canvas.update()

        def draw(event):
            frames.append(read_clear(canvas, RED))
            app.quit()

        timer.events.timeout.ignore_callback_errors = False
        canvas.events.draw.ignore_callback_errors = False
        timer.connect(tick)
        canvas.events.draw.connect(draw)
        timer.start()
        try:
            run_with_watchdog(canvas.app, app.run)
            assert ticks == [0]
            assert not timer.running
            assert len(frames) == 1
            assert_frame(frames[0], SIZE, RED)
        finally:
            if timer.running:
                timer.stop()
    app.quit()


def test_quit_reenters_after_close_callback_failure(default_app):
    app.create()
    with app.Canvas(size=SIZE, autoswap=False) as failed:
        with app.Canvas(size=SIZE, autoswap=False) as survivor:
            error = RuntimeError("close callback failed before loop exit")
            close_events, frames = [], []

            def close_failed(event):
                close_events.append(event.type)
                app.quit()
                raise error

            failed.events.close.ignore_callback_errors = False
            failed.events.close.connect(close_failed)
            with pytest.raises(RuntimeError) as caught:
                failed.close()
            assert caught.value is error
            failed.close()
            app.quit()

            def draw(event):
                frames.append(read_clear(survivor, RED))
                app.quit()

            survivor.events.draw.connect(draw)
            survivor.update()
            run_with_watchdog(survivor.app, app.run)
            assert close_events == ["close"]
            assert len(frames) == 1
            assert_frame(frames[0], SIZE, RED)

def test_run_gallery_failure_and_reentry(default_app, monkeypatch):
    app.create()
    with app.Canvas(size=SIZE, autoswap=False) as canvas:
        error = RuntimeError("failed draw in app.run")
        canvas.events.draw.ignore_callback_errors = False
        calls = []
        frames = []

        def draw(event):
            calls.append(event.type)
            if len(calls) == 1:
                raise error
            frames.append(read_clear(canvas, GREEN))
            app.quit()

        canvas.events.draw.connect(draw)
        canvas.update()
        monkeypatch.setenv("_VISPY_RUNNING_GALLERY_EXAMPLES", "1")
        assert app.run() == 0
        assert calls == []
        monkeypatch.delenv("_VISPY_RUNNING_GALLERY_EXAMPLES")
        with pytest.raises(RuntimeError) as caught:
            run_with_watchdog(canvas.app, app.run)
        assert caught.value is error
        canvas.update()
        run_with_watchdog(canvas.app, app.run)
        assert calls == ["draw", "draw"]
        assert_frame(frames[0], SIZE, GREEN)


def test_canvas_constructor_and_frame_after_resize(default_app):
    with app.Canvas(title="GPU target", size=SIZE, position=(7, 11),
                    config={"depth_size": 0}, autoswap=False) as canvas:
        assert canvas.title == "GPU target"
        assert canvas.fullscreen is False
        assert canvas.context.config["depth_size"] == 0
        assert canvas.size == canvas.physical_size == SIZE
        assert canvas.pixel_scale == 1
        assert_frame(read_clear(canvas, RED), SIZE, RED)
        canvas.size = (19, 13)
        assert canvas.size == canvas.physical_size == (19, 13)
        assert_frame(read_clear(canvas, GREEN), (19, 13), GREEN)


def test_canvas_constructor_position(default_app):
    with app.Canvas(title="GPU target", size=SIZE, position=(7, 11),
                    config={"depth_size": 0}, autoswap=False) as canvas:
        position = canvas.position
    assert position == (7, 11)


def test_canvas_shared_peer_recovers_after_loss_and_pending_close(default_app):
    with app.Canvas(size=SIZE, autoswap=False) as canvas:
        with app.Canvas(size=SIZE, shared=canvas, autoswap=False) as peer:
            assert canvas.context.shared is peer.context.shared
            closed, draws = [], []
            canvas.events.close.connect(lambda event: closed.append(event.type))
            canvas.events.draw.connect(lambda event: draws.append(event.type))
            canvas.size = (19, 13)
            canvas.update()
            _dawn.lose_device()
            canvas.close()
            canvas.close()
            frames = []
            peer.events.draw.connect(lambda event: frames.append(read_clear(peer, GREEN)))
            peer.update()
            pump_until(lambda: frames)
            assert closed == ["close"]
            assert draws == []
            assert_frame(frames[0], SIZE, GREEN)


def test_timer_interval_change_order_and_owner_thread(default_app):
    application = app.use_app()
    owner = threading.get_ident()
    timer = app.Timer(interval=30, iterations=2, app=application)
    events = []
    timer.events.start.connect(lambda event: events.append(("start", timer.interval)))
    timer.events.stop.connect(lambda event: events.append(("stop", timer.interval)))
    timer.connect(lambda event: events.append(("tick", event.iteration, threading.get_ident())))
    try:
        timer.start()
        app.process_events()
        assert events == [("start", 30)]
        timer.interval = 0.001
        pump_until(lambda: not timer.running)
        assert events == [
            ("start", 30), ("stop", 0.001), ("start", 0.001),
            ("tick", 0, owner), ("tick", 1, owner), ("stop", 0.001),
        ]
    finally:
        if timer.running:
            timer.stop()


def test_timer_restart_in_callback_and_recovery_after_failure(default_app):
    timer = app.Timer(interval=0, iterations=2)
    timer.events.timeout.ignore_callback_errors = False
    error = RuntimeError("timer generation failed")
    ticks = []

    def tick(event):
        ticks.append(event.iteration)
        if len(ticks) == 1:
            timer.stop()
            timer.start()
        elif len(ticks) == 3:
            raise error

    timer.connect(tick)
    try:
        timer.start()
        with pytest.raises(RuntimeError) as caught:
            pump_until(lambda: not timer.running)
        assert caught.value is error
        assert ticks == [0, 0, 1]
        assert not timer.running
        with app.Canvas(size=SIZE, autoswap=False) as canvas:
            frames = []
            canvas.events.draw.connect(lambda event: frames.append(read_clear(canvas, RED)))
            timer.disconnect(tick)
            timer.connect(lambda event: canvas.update())
            timer.start(iterations=1)
            pump_until(lambda: frames and not timer.running)
            assert len(frames) == 1
            assert_frame(frames[0], SIZE, RED)
    finally:
        if timer.running:
            timer.stop()


def test_timer_callback_exception_and_explicit_restart(default_app):
    timer = app.Timer(interval=0)
    timer.events.timeout.ignore_callback_errors = False
    error = RuntimeError("timer callback failed")
    ticks = []

    def fail(event):
        ticks.append(event.iteration)
        raise error

    timer.connect(fail)
    try:
        timer.start()
        with pytest.raises(RuntimeError) as caught:
            pump_until(lambda: not timer.running)
        assert caught.value is error
        assert ticks == [0]
        timer.stop()
        timer.disconnect(fail)

        with app.Canvas(size=SIZE, autoswap=False) as canvas:
            frames = []
            canvas.events.draw.connect(lambda event: frames.append(read_clear(canvas, RED)))

            def redraw(event):
                ticks.append(event.iteration)
                canvas.update()

            timer.connect(redraw)
            timer.start(iterations=1)
            pump_until(lambda: frames and not timer.running)
            assert ticks == [0, 0]
            assert len(frames) == 1
            assert_frame(frames[0], SIZE, RED)
    finally:
        if timer.running:
            timer.stop()


def test_use_app_autoselection_and_reuse(default_app, monkeypatch):
    from vispy.util import config

    monkeypatch.delenv("_VISPY_TESTING_APP")
    previous = config["default_backend"]
    config["default_backend"] = "dawn_headless"
    try:
        application = app.use_app()
    finally:
        config["default_backend"] = previous
    assert application.backend_name == "dawn_headless"
    assert app.use_app("dawn_headless") is app.use_app() is application


def test_use_app_retries_unavailable_backend_and_refuses_switch(default_app):
    with pytest.raises(RuntimeError, match='Could not import backend "_test"'):
        app.use_app("_test")
    assert _default_app.default_app is None
    application = app.use_app("dawn_headless")
    with pytest.raises(RuntimeError, match="Can only select a backend once"):
        app.use_app("pyqt6")
    assert app.use_app("DAWN_HEADLESS") is application
    assert app.use_app().native is application.native


if __name__ == "__main__" and sys.argv[1:] == ["run"]:
    run_from_timer()
