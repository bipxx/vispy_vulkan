# SPDX-License-Identifier: AGPL-3.0-only
from types import SimpleNamespace
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
