# SPDX-License-Identifier: AGPL-3.0-only
"""D31: the plugin successors read a canvas pixel's world position the way napari gives it to mouse events."""
from tools.napari_world_position import world_position


class Viewer010:
    """napari 0.10 and later: ViewerModel.canvas_to_world takes a (y, x) canvas position."""

    def __init__(self):
        self.calls = []

    def canvas_to_world(self, position):
        self.calls.append(position)
        return (0.0, *position)


class Canvas092:
    """napari 0.9.2: VispyCanvas._map_canvas2world takes an (x, y) canvas position and a view."""

    view = object()

    def __init__(self):
        self.calls = []

    def _map_canvas2world(self, position, view):
        assert view is self.view
        self.calls.append(position)
        return (1.0, *position)


def test_world_position_uses_canvas_to_world_where_napari_has_it():
    viewer, canvas = Viewer010(), Canvas092()
    assert world_position(viewer, canvas, (3, 7)) == (0.0, 7, 3)
    assert viewer.calls == [(7, 3)] and canvas.calls == []


def test_world_position_falls_back_to_the_napari_092_canvas_method():
    canvas = Canvas092()
    assert world_position(object(), canvas, [3, 7]) == (1.0, 3, 7)
    assert canvas.calls == [(3, 7)]


__all__ = [name for name in dir() if name.startswith('test_')]
