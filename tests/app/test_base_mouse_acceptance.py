# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""Base backend and mouse history contracts independent of a window toolkit."""

import subprocess
import sys

import numpy as np
import pytest

from vispy import app
from vispy.app.base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend
from vispy.app.backends import _dawn_headless


class CanvasAdapter(BaseCanvasBackend):
    def _vispy_get_position(self):
        return (2, 3)

    def _vispy_get_size(self):
        return (24, 16)


def test_base_adapter_defaults():
    application = BaseApplicationBackend()
    assert application._vispy_get_native_app() is application
    assert application._vispy_reuse() is None
    for hook in (application._vispy_process_events, application._vispy_run, application._vispy_quit):
        with pytest.raises(NotImplementedError):
            hook()

    canvas = app.Canvas(app="dawn_headless", create_native=False)
    adapter = CanvasAdapter(canvas)
    assert canvas.native is adapter
    assert canvas.physical_size == (24, 16)
    assert adapter._vispy_get_geometry() == (2, 3, 24, 16)
    assert adapter._vispy_get_fb_bind_location() == 0
    with pytest.raises(NotImplementedError):
        canvas.update()
    # This deliberately minimal adapter has no native resources to close.
    with pytest.raises(NotImplementedError):
        canvas.close()

    timer = app.Timer(app="dawn_headless")
    timer_adapter = BaseTimerBackend(timer)
    assert timer_adapter._vispy_get_native_timer() is timer_adapter
    with pytest.raises(NotImplementedError):
        timer_adapter._vispy_start(1)
    with pytest.raises(NotImplementedError):
        timer_adapter._vispy_stop()


def test_base_adapter_rejects_capability_and_sharing_then_accepts_valid_kwargs(monkeypatch):
    monkeypatch.setitem(_dawn_headless.capability, "context", False)
    application = app.Application("dawn_headless")

    canvas = app.Canvas(app=application, create_native=False, size=(24, 16))
    adapter = CanvasAdapter(canvas)
    kwargs = canvas._backend_kwargs
    with pytest.raises(RuntimeError, match="Config vsync is not supported"):
        adapter._process_backend_kwargs(dict(kwargs, vsync=True))

    peer = app.Canvas(app=application, create_native=False)
    peer.context.shared.add_ref("contract", adapter)
    with pytest.raises(RuntimeError, match="Cannot share context"):
        adapter._process_backend_kwargs(dict(kwargs, context=peer.context))

    processed = adapter._process_backend_kwargs(kwargs)
    assert processed.size == (24, 16)
    assert processed.context is canvas.context
    assert adapter._vispy_mouse_data == {
        "press_event": None, "last_event": None, "last_mouse_press": None,
    }
    with pytest.raises(NotImplementedError):
        canvas.close()


def test_mouseevent_extra_button_drag_order_and_coordinates():
    press = app.MouseEvent("mouse_press", pos=(7, 9), button=8, buttons=[8])
    move = app.MouseEvent("mouse_move", pos=(12, 13), button=8, buttons=[8],
                          press_event=press, last_event=press)
    release = app.MouseEvent("mouse_release", pos=(18, 21), button=8, buttons=[],
                             press_event=press, last_event=move)
    assert release.press_event is press
    assert release.last_event is move
    assert release.button == 8 and release.buttons == []
    assert move.buttons == [8]
    assert release.drag_events() == [move, release]
    np.testing.assert_array_equal(release.trail(), [(12, 13), (18, 21)])


def test_mouseevent_rejects_malformed_history():
    press = app.MouseEvent("mouse_press", pos=(7, 9), button=8)
    malformed = app.MouseEvent("mouse_move", press_event=press, last_event=object())
    with pytest.raises(TypeError, match="MouseEvent"):
        malformed.trail()


def test_mouseevent_rejects_cyclic_history():
    code = """
from vispy import app

press = app.MouseEvent("mouse_press", pos=(7, 9), button=8)
cyclic = app.MouseEvent("mouse_move", press_event=press)
cyclic._last_event = cyclic
print("checking cyclic history", flush=True)
try:
    cyclic.drag_events()
except ValueError as error:
    assert "cycle" in str(error)
else:
    raise AssertionError("cyclic history was accepted")
"""
    try:
        subprocess.run([sys.executable, "-B", "-S", "-c", code], check=True,
                       capture_output=True, timeout=2)
    except subprocess.TimeoutExpired as error:
        assert b"checking cyclic history" in (error.stdout or b"")
        raise


def test_mouseevent_clean_drag_after_hover():
    hover = app.MouseEvent("mouse_move", pos=(2, 4), buttons=[])
    assert hover.trail() is None
    new_press = app.MouseEvent("mouse_press", pos=(4, 6), button=1, last_event=hover)
    new_move = app.MouseEvent("mouse_move", pos=(9, 14), button=1,
                              press_event=new_press, last_event=new_press)
    assert new_move.drag_events() == [new_move]
    np.testing.assert_array_equal(new_move.trail(), [(9, 14)])
