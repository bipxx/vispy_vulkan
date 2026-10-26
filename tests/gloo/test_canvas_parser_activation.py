# SPDX-License-Identifier: AGPL-3.0-only
from types import SimpleNamespace
import numpy as np
import pytest
import vispy
from vispy import gloo
from vispy.gloo.context import GLContext, set_current_canvas, forget_canvas


def test_shared_parser_tracks_activation_before_any_flush():
    class Canvas:
        def __init__(self, canvas_id, shared=None):
            self.context=GLContext(shared=shared)
            self._backend=SimpleNamespace(_dawn_canvas_id=canvas_id)
    first=Canvas(17)
    second=Canvas(23,first.context.shared)
    try:
        set_current_canvas(first)
        assert first.context.shared.parser.canvas_id==17
        set_current_canvas(second)
        assert first.context.shared.parser.canvas_id==23
        set_current_canvas(first)
        assert second.context.shared.parser.canvas_id==17
        # Reactivating an already current canvas must also refresh its native
        # identity (for example after backend recreation).
        first._backend._dawn_canvas_id=29
        set_current_canvas(first)
        assert first.context.shared.parser.canvas_id==29
    finally:
        forget_canvas(first)
        forget_canvas(second)


@pytest.fixture
def readback(monkeypatch):
    events = []
    pending = ["draw"]
    state = {"viewport": (0, 0, 2, 2)}
    pixels = np.arange(48, dtype=np.uint8).reshape(4, 3, 4)

    def finish():
        events.append("finish")
        pending.clear()
        # A queued viewport update must be applied before the default query.
        state["viewport"] = (1, 2, 3, 4)

    def viewport(canvas_id):
        assert canvas_id == 19
        events.append("viewport")
        return state["viewport"]

    def read_pixels(*args):
        events.append(("read", args))
        return pixels

    native = SimpleNamespace(viewport=viewport, read_pixels=read_pixels)
    canvas = SimpleNamespace(
        _backend=SimpleNamespace(_dawn_canvas_id=19),
        context=SimpleNamespace(finish=finish),
    )
    monkeypatch.setattr(vispy, "_dawn", native, raising=False)
    monkeypatch.setattr(gloo.context, "get_current_canvas", lambda: canvas)
    return SimpleNamespace(events=events, pending=pending, pixels=pixels)


@pytest.mark.parametrize("viewport", [
    (0, 0, 3),
    (0, 0, 3, 4, 5),
    [[0, 0, 3, 4]],
    ("invalid", 0, 3, 4),
])
def test_invalid_viewport_preserves_pending_work(readback, viewport):
    with pytest.raises(ValueError):
        gloo.read_pixels(viewport=viewport)
    assert readback.events == []
    assert readback.pending == ["draw"]


def test_explicit_viewport_finishes_before_native_readback(readback):
    result = gloo.read_pixels(viewport=(1, 2, 3, 4))
    assert readback.events == [
        "finish", ("read", (19, 1, 2, 3, 4, True, False, "color")),
    ]
    np.testing.assert_array_equal(result, readback.pixels)
    assert not np.shares_memory(result, readback.pixels)


def test_default_viewport_observes_queued_update(readback):
    gloo.read_pixels()
    assert readback.events == [
        "finish", "viewport", ("read", (19, 1, 2, 3, 4, True, False, "color")),
    ]
