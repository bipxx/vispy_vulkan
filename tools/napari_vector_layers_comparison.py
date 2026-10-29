# SPDX-License-Identifier: AGPL-3.0-only
"""The napari vector-layer comparison (W4, M11), with decision D10's documented difference.

The fixture (tools/fixture_napari_vector_layers.py, bound to its references by hash) fixed each case's criterion before
capture: vectors exact; tracks and shapes_selected the smooth-line criterion (tools/smooth_line_parity.py).

Decision D10 (user, 2026-10-29) closes tracks and shapes_selected with a documented difference, as D9 did for the mesh
axes/colorbar scene. Their antialiased edge pixels follow GL's driver-defined smooth coverage within the bound, but
more than 1% of each frame differs. So the frame cap does not apply to them, and alpha must match exactly instead.
Interiors stay exact and every edge stays within the bound; the fixture's landmarks are checked separately.
"""
from __future__ import annotations

import numpy as np

try:
    from .smooth_line_parity import smooth_line_difference
except ImportError:
    from smooth_line_parity import smooth_line_difference

DOCUMENTED_DIFFERENCE = frozenset({"tracks", "shapes_selected"})  # decision D10: no frame cap, exact alpha


def smooth_line_case_difference(name, image, reference):
    """Return None if a smooth-line case matches its reference, else why not."""
    if name not in DOCUMENTED_DIFFERENCE:
        return smooth_line_difference(image, reference)
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return "shape or dtype differs"
    if not np.array_equal(image[..., 3], reference[..., 3]):
        return "alpha differs"
    return smooth_line_difference(image, reference, max_differing_fraction=None)
