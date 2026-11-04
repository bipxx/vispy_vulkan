# SPDX-License-Identifier: AGPL-3.0-only
"""The world position napari gives a mouse event at a canvas pixel, for the plugin successor fixtures (D31).

napari 0.10 computes mouse-event positions with ViewerModel.canvas_to_world (napari #9517), which replaced
VispyCanvas._map_canvas2world. The successors predict their drag landmarks from the same positions the plugin receives.
"""


def world_position(viewer, canvas, xy):
    """The world position of canvas pixel xy = (x, y), as napari computes it for mouse events."""
    if hasattr(viewer, 'canvas_to_world'):
        return viewer.canvas_to_world(tuple(xy)[::-1])
    return canvas._map_canvas2world(tuple(xy), canvas.view)
