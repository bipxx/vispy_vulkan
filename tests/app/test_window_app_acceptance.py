# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""Acceptance on real toolkit windows, selected explicitly by the operator."""

import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

from vispy import app, gloo

pytestmark = [
    pytest.mark.needs_window,
    pytest.mark.gpu,
    pytest.mark.skipif(os.getenv("VISPY_TEST_WINDOWS") != "1", reason="needs-window"),
]
QT_BINDINGS = ["PyQt5", "PyQt6", "PySide6"]
SIZE = (80, 60)
QUADRANTS = [(0, 0, 255), (255, 255, 0), (255, 0, 0), (0, 255, 0)]


class KnownWindowGap(Exception):
    pass


def wait_until(condition):
    deadline = time.monotonic() + 5
    while not condition():
        app.process_events()
        assert time.monotonic() < deadline, "timed out waiting for native window state"
        time.sleep(0.005)


def draw_quadrants(canvas):
    @canvas.events.draw.connect
    def draw(event):
        w, h = canvas.physical_size
        left, bottom = w // 2, h // 2
        gloo.set_viewport(0, 0, w, h)
        gloo.set_state(scissor_test=True)
        try:
            for rect, rgb in zip(
                [(0, bottom, left, h - bottom), (left, bottom, w - left, h - bottom),
                 (0, 0, left, bottom), (left, 0, w - left, bottom)],
                QUADRANTS,
            ):
                gloo.set_scissor(*rect)
                gloo.clear(color=tuple(c / 255 for c in rgb) + (1,))
        finally:
            gloo.set_state(scissor_test=False)

    canvas.events.draw.ignore_callback_errors = False
    canvas.update()


def landmarks(w, h):
    return [(w // 4, h // 4), (3 * w // 4, h // 4),
            (w // 4, 3 * h // 4), (3 * w // 4, 3 * h // 4)]


def run_qt_child(binding, case):
    env = os.environ.copy()
    env["VISPY_QT_PRESENTATION"] = "readback"
    env["QT_API"] = binding.lower()
    for name in ("_VISPY_TESTING_APP", "_VISPY_RUNNING_GALLERY_EXAMPLES", "QT_QPA_PLATFORM"):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-B", "-S", str(Path(__file__).resolve()), binding, case],
        env=env, capture_output=True, text=True, timeout=45, check=False,
    )
    if result.returncode == 77:
        pytest.skip(result.stdout.strip())
    if result.returncode == 78:
        raise KnownWindowGap(result.stdout.strip())
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("binding", QT_BINDINGS)
@pytest.mark.parametrize("case", ["scale-change", "queued-hide-scale-restore"])
def test_qt_live_scale_and_pointer(binding, case):
    run_qt_child(binding, case)


@pytest.mark.parametrize("binding", QT_BINDINGS)
@pytest.mark.parametrize("case", ["cold", "napari", "loop-failure"])
def test_qt_application_identity_and_loop_reentry(binding, case):
    run_qt_child(binding, case)


@pytest.mark.parametrize("binding", QT_BINDINGS)
def test_qt_extra_buttons_and_focus_cancellation(binding):
    run_qt_child(binding, "mouse")


def qt_mouse(canvas, core, gui, widgets):
    qt = core.Qt
    widget = canvas.native
    seen = []
    for kind in ("mouse_press", "mouse_move", "mouse_release"):
        getattr(canvas.events, kind).connect(seen.append)

    extra = qt.MouseButton.ExtraButton3
    left = qt.MouseButton.LeftButton
    nothing = qt.MouseButton.NoButton
    types = core.QEvent.Type

    def send(kind, x, y, button, buttons):
        pos = core.QPointF(x, y)
        global_pos = core.QPointF(widget.mapToGlobal(core.QPoint(x, y)))
        event = gui.QMouseEvent(kind, pos, pos, global_pos, button, buttons,
                                qt.KeyboardModifier.NoModifier)
        widgets.QApplication.sendEvent(widget, event)

    send(types.MouseButtonPress, 7, 9, extra, extra)
    send(types.MouseMove, 11, 14, nothing, extra)
    send(types.MouseButtonRelease, 15, 17, extra, nothing)
    assert [event.type for event in seen] == ["mouse_press", "mouse_move", "mouse_release"]
    assert [event.button for event in seen] == [6, 6, 6]
    assert [event.buttons for event in seen] == [[6], [6], []]
    assert seen[2].press_event is seen[0]
    np.testing.assert_array_equal(seen[2].trail(), [(11, 14), (15, 17)])
    seen.clear()

    send(types.MouseButtonPress, 7, 9, left, left)
    send(types.MouseButtonPress, 8, 9, extra, left | extra)
    widgets.QApplication.sendEvent(widget, gui.QFocusEvent(types.FocusOut))
    send(types.MouseButtonPress, 10, 12, left, left)
    time.sleep(0.012)  # base move throttling is 10 ms
    send(types.MouseMove, 18, 19, nothing, left)
    if seen[-2].press_event is seen[0] and seen[-1].press_event is seen[0]:
        raise KnownWindowGap("Qt FocusOut left the previous press active")
    assert seen[-1].press_event is seen[-2]
    assert seen[-2].press_event is None
    assert seen[-1].buttons == [1]
    np.testing.assert_array_equal(seen[-1].trail(), [(18, 19)])


def qt_scale(canvas, application, core, gui, widgets, recovery):
    screens = application.native.screens()
    handle = canvas.native.windowHandle()
    source = handle.screen()
    target = next((s for s in screens if s.devicePixelRatio() != source.devicePixelRatio()), None)
    if target is None:
        print("needs-window with two screens at different device pixel ratios")
        return 77

    def check(screen, logical_size):
        ratio = screen.devicePixelRatio()
        w, h = (round(n * ratio) for n in logical_size)
        wait_until(lambda: handle.screen() == screen and canvas.physical_size == (w, h))
        wait_until(lambda: getattr(canvas.native, "_dawn_last_image", None) is not None
                   and (canvas.native._dawn_last_image.width(),
                        canvas.native._dawn_last_image.height()) == (w, h))
        image = canvas.native._dawn_last_image
        assert [image.pixelColor(x, y).getRgb()[:3] for x, y in landmarks(w, h)] == QUADRANTS
        assert canvas.size == logical_size

    check(source, SIZE)
    if recovery:
        canvas.update()
        canvas.show(False)
        canvas.size = (92, 68)
    canvas.native.move(target.availableGeometry().topLeft() + core.QPoint(24, 24))
    canvas.show()
    canvas.update()
    check(target, (92, 68) if recovery else SIZE)

    seen = []
    canvas.events.mouse_press.connect(lambda event: seen.append(tuple(event.pos)))
    qt = core.Qt
    point = core.QPointF(13, 17)
    absolute = core.QPointF(canvas.native.mapToGlobal(core.QPoint(13, 17)))
    event = gui.QMouseEvent(core.QEvent.Type.MouseButtonPress, point, point, absolute,
                            qt.MouseButton.LeftButton, qt.MouseButton.LeftButton,
                            qt.KeyboardModifier.NoModifier)
    widgets.QApplication.sendEvent(canvas.native, event)
    assert seen == [(13, 17)]
    return 0


def qt_loop_failure(core):
    error = RuntimeError("native Qt draw failure")
    failed = app.Canvas(size=SIZE)
    try:
        def fail(event):
            raise error

        failed.events.draw.ignore_callback_errors = False
        failed.events.draw.connect(fail)
        core.QTimer.singleShot(0, lambda: failed.show())
        with pytest.raises(RuntimeError) as caught:
            app.run()
        assert caught.value is error
    finally:
        failed.close()

    canvas = app.Canvas(size=SIZE)
    try:
        draw_quadrants(canvas)
        canvas.show()
        poll = core.QTimer()
        poll.timeout.connect(lambda: app.quit() if getattr(canvas.native, "_dawn_last_image", None) is not None else None)
        poll.start(5)
        try:
            app.run()
        finally:
            poll.stop()
        w, h = canvas.physical_size
        image = canvas.native._dawn_last_image
        assert [image.pixelColor(x, y).getRgb()[:3] for x, y in landmarks(w, h)] == QUADRANTS
    finally:
        canvas.close()


def qt_child(binding, case):
    from importlib import import_module
    try:
        core, gui, widgets = [import_module(f"{binding}.{part}")
                              for part in ("QtCore", "QtGui", "QtWidgets")]
        if case == "napari":
            from napari._qt.qt_event_loop import get_qapp
    except ImportError as error:
        print(f"needs-window prerequisite: {error}")
        return 77

    assert widgets.QApplication.instance() is None
    if case == "napari":
        host = get_qapp()
        assert widgets.QApplication.instance() is host
        selected = app.use_app()
        assert selected.backend_name == binding
        assert selected.native is host
        assert app.Application(binding).native is host
        return 0

    application = app.use_app() if case == "cold" else app.use_app(binding)
    assert application.backend_name == binding
    assert widgets.QApplication.instance() is None
    app.create()
    native = widgets.QApplication.instance()
    assert native is not None
    assert application.native is app.use_app().native is native
    if case == "cold":
        return 0

    native.setQuitOnLastWindowClosed(False)
    if case in ("timer-order", "timer-error"):
        check_native_timer(case == "timer-error")
        return 0
    if case == "loop-failure":
        qt_loop_failure(core)
        return 0
    canvas = app.Canvas(size=SIZE, title="Live scale", show=True)
    try:
        draw_quadrants(canvas)
        wait_until(lambda: getattr(canvas.native, "_dawn_last_image", None) is not None)
        if case == "mouse":
            qt_mouse(canvas, core, gui, widgets)
            return 0
        return qt_scale(canvas, application, core, gui, widgets, case == "queued-hide-scale-restore")
    finally:
        canvas.close()


@pytest.fixture
def tk_host(monkeypatch):
    tk = pytest.importorskip("tkinter")
    from vispy.app import _default_app

    monkeypatch.setattr(_default_app, "default_app", None)
    monkeypatch.delenv("_VISPY_RUNNING_GALLERY_EXAMPLES", raising=False)
    root = tk.Tk()
    try:
        application = app.use_app("tkinter")
        assert application.native is root
        yield root, tk
    finally:
        try:
            app.quit()
        finally:
            try:
                root.update_idletasks()
            except tk.TclError:
                pass
            root.destroy()


@pytest.mark.parametrize("queued_resize", [False, True], ids=["scale", "queued-resize"])
def test_tk_live_scaling_and_embedded_photo(tk_host, queued_resize):
    root, tk = tk_host
    parent = tk.Frame(root)
    parent.pack()
    canvas = app.Canvas(size=SIZE, parent=parent, show=True, backend_kwargs={"presentation": "raster"})
    canvas.native.pack()
    try:
        wait_until(lambda: canvas.native.winfo_viewable())
        draw_quadrants(canvas)
        wait_until(lambda: canvas._backend._photo is not None)
        initial = canvas._backend._photo
        host_calls = []
        parent.bind("<<HostReady>>", lambda event: host_calls.append(event.widget))
        scale = float(root.tk.call("tk", "scaling"))
        if queued_resize:
            canvas.update()
        root.tk.call("tk", "scaling", scale * 1.5)
        assert float(root.tk.call("tk", "scaling")) > scale * 1.3
        size = (92, 68) if queued_resize else SIZE
        canvas.size = size
        canvas.update()
        wait_until(lambda: canvas._backend._photo is not None
                   and canvas._backend._photo is not initial
                   and (canvas._backend._photo.width(), canvas._backend._photo.height()) == size)
        photo = canvas._backend._photo
        assert canvas.size == canvas.physical_size == size
        assert [photo.get(x, y) for x, y in landmarks(*size)] == QUADRANTS
        assert canvas.native.winfo_parent() == str(parent)

        seen = []
        canvas.events.mouse_press.connect(lambda event: seen.append(tuple(event.pos)))
        canvas.native.focus_force()
        app.process_events()
        canvas.native.event_generate("<ButtonPress-1>", x=13, y=17)
        canvas.native.event_generate("<ButtonRelease-1>", x=13, y=17)
        parent.event_generate("<<HostReady>>")
        assert seen == [(13, 17)]
        assert host_calls == [parent]
    finally:
        canvas.close()


@pytest.mark.parametrize("failure", [False, True], ids=["timer-quit", "close-error"])
def test_tk_module_quit_retires_owned_resources_and_keeps_host(tk_host, failure):
    root, _ = tk_host
    first = app.Canvas(size=SIZE, parent=root, show=True)
    peer = app.Canvas(size=SIZE, parent=root, show=True)
    draw_quadrants(first)
    wait_until(lambda: first._backend._photo is not None)
    assert [first._backend._photo.get(x, y) for x, y in landmarks(*SIZE)] == QUADRANTS
    error = RuntimeError("close callback failed")
    close_events = []

    def close_first(event):
        close_events.append("first")
        if failure:
            raise error

    first.events.close.ignore_callback_errors = False
    first.events.close.connect(close_first)
    peer.events.close.connect(lambda event: close_events.append("peer"))
    ticks = []
    timer = app.Timer(interval=0.005)

    def tick(event):
        ticks.append(event.iteration)
        app.quit()

    timer.events.timeout.ignore_callback_errors = False
    timer.connect(tick)
    timer.start()
    watchdog = root.after(5000, root.quit)
    try:
        if failure:
            with pytest.raises(RuntimeError) as caught:
                app.run()
            assert caught.value is error
        else:
            app.run()
    finally:
        root.after_cancel(watchdog)
    app.quit()
    assert ticks == [0]
    assert sorted(close_events) == ["first", "peer"]
    assert not timer.running
    assert first._closed
    assert peer._closed
    delivered = []
    root.after_idle(lambda: delivered.append("host"))
    root.update()
    assert delivered == ["host"]


@pytest.mark.parametrize("binding", QT_BINDINGS)
@pytest.mark.parametrize("case", ["timer-order", "timer-error"])
def test_qt_timer_delivery_and_recovery(binding, case):
    run_qt_child(binding, case)


def check_native_timer(failure):
    owner = threading.get_ident()
    timer = app.Timer(interval=30, iterations=2)
    ticks, events = [], []
    error = RuntimeError("native timer callback failure")
    timer.events.timeout.ignore_callback_errors = False
    timer.events.start.connect(lambda event: events.append("start"))
    timer.events.stop.connect(lambda event: events.append("stop"))

    def tick(event):
        ticks.append((event.iteration, threading.get_ident()))
        if failure and len(ticks) == 1:
            timer.stop()
            timer.start()
        elif failure and len(ticks) == 3:
            raise error

    timer.connect(tick)
    try:
        timer.start()
        app.process_events()
        assert ticks == []
        timer.interval = 0.005
        if failure:
            try:
                with pytest.raises(RuntimeError) as caught:
                    wait_until(lambda: not timer.running)
            except pytest.fail.Exception:
                if ticks == [(0, owner), (1, owner)]:
                    raise KnownWindowGap("timer stopped before delivering the third tick") from None
                raise
            assert caught.value is error
            assert not timer.running
            assert ticks == [(0, owner), (0, owner), (1, owner)]
            timer.disconnect(tick)
            timer.connect(lambda event: ticks.append((event.iteration, threading.get_ident())))
            timer.start(iterations=1)
            wait_until(lambda: not timer.running)
            assert ticks[-1] == (0, owner)
            assert len(ticks) == 4
        else:
            wait_until(lambda: not timer.running)
            assert ticks == [(0, owner), (1, owner)]
            assert events == ["start", "stop", "start", "stop"]
    finally:
        if timer.running:
            timer.stop()


@pytest.mark.parametrize("failure", [
    pytest.param(False, id="order"),
    pytest.param(True, id="callback-error"),
])
def test_tk_timer_delivery_and_recovery(tk_host, failure):
    check_native_timer(failure)


def test_tk_extra_button_and_focus_cancellation(tk_host):
    root, tk = tk_host
    if sys.platform.startswith("linux") and tk.TkVersion < 8.7:
        pytest.skip("needs-window: additional button injection on legacy X11 Tk")
    canvas = app.Canvas(size=SIZE, parent=root, show=True)
    canvas.native.pack()
    try:
        wait_until(lambda: canvas.native.winfo_viewable())
        draw_quadrants(canvas)
        wait_until(lambda: canvas._backend._photo is not None)
        canvas.native.focus_force()
        app.process_events()
        seen = []
        for kind in ("mouse_press", "mouse_move", "mouse_release"):
            getattr(canvas.events, kind).connect(seen.append)

        widget = canvas.native
        widget.event_generate("<ButtonPress-4>", x=7, y=9)
        widget.event_generate("<Motion>", x=11, y=14)
        widget.event_generate("<ButtonRelease-4>", x=15, y=17)
        assert [event.type for event in seen] == ["mouse_press", "mouse_move", "mouse_release"]
        assert [event.button for event in seen] == [4, 4, 4]
        assert [event.buttons for event in seen] == [[4], [4], []]
        assert seen[-1].press_event is seen[0]
        np.testing.assert_array_equal(seen[-1].trail(), [(11, 14), (15, 17)])
        seen.clear()

        widget.event_generate("<ButtonPress-1>", x=7, y=9)
        widget.event_generate("<ButtonPress-4>", x=8, y=9)
        widget.event_generate("<FocusOut>")
        assert [event.button for event in seen[2:]] == [1, 4]
        assert [event.buttons for event in seen[2:]] == [[4], []]
        widget.event_generate("<ButtonPress-1>", x=10, y=12)
        time.sleep(0.012)
        widget.event_generate("<Motion>", x=18, y=19)
        assert seen[-1].press_event is seen[-2]
        assert seen[-2].press_event is None
        assert seen[-1].buttons == [1]
        np.testing.assert_array_equal(seen[-1].trail(), [(18, 19)])
    finally:
        canvas.close()

if __name__ == "__main__":
    try:
        sys.exit(qt_child(*sys.argv[1:]))
    except KnownWindowGap as error:
        print(error)
        sys.exit(78)
