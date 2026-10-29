# SPDX-License-Identifier: AGPL-3.0-only
"""The napari layer-family comparison (W4), with decisions D11 and D12.

The fixture (tools/fixture_napari_layer_families.py, bound to its references by hash) fixed each case's criterion
before capture: exact, or the smooth-line criterion (tools/smooth_line_parity.py) for frames with napari's
antialiased lines. Two user decisions (2026-10-29) then closed cases that failed only on driver-defined pixels:

- D11: colorbar and histogram get the documented difference of D9 and D10. Their antialiased box, tick and axis
  lines follow GL's driver-defined smooth coverage within the bound, but more than 1% of each frame differs. So the
  frame cap does not apply to them, and alpha must match exactly instead.
- D12: surface_shaded differs only where the folded surface's front and back faces meet. Vertex-precision differences
  decide which face covers a near-tie pixel, so a flipped pixel can differ by any amount. Interiors (uniform reference
  3x3 neighbourhoods) stay exact, and at most 0.1% of the frame may differ, only on edge pixels.

Every other case keeps the fixture's criterion. The fixture's landmarks are checked separately.
"""
from __future__ import annotations

import numpy as np

try:
    from .fixture_napari_layer_families import CRITERIA
    from .smooth_line_parity import reference_edges, smooth_line_difference
except ImportError:
    from fixture_napari_layer_families import CRITERIA
    from smooth_line_parity import reference_edges, smooth_line_difference

DOCUMENTED_DIFFERENCE = frozenset({"colorbar", "histogram"})  # decision D11: no frame cap, exact alpha
EDGE_PIXELS = frozenset({"surface_shaded"})  # decision D12: exact interiors, at most 0.1% of the frame on edges
MAX_EDGE_FRACTION = .001


def layer_family_difference(name, image, reference):
    """Return None if ``image`` matches ``reference`` under the case's comparison, else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return "shape or dtype differs"
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    differing = np.any(difference, axis=2)
    if name in EDGE_PIXELS:
        interior = differing & ~reference_edges(reference)
        if interior.any():
            return "%d interior pixels differ" % int(interior.sum())
        if differing.sum() > MAX_EDGE_FRACTION * differing.size:
            return "%d edge pixels differ" % int(differing.sum())
        return None
    if CRITERIA[name] == "exact":
        return None if not differing.any() else "%d pixels differ, by up to %d" % (int(differing.sum()),
                                                                                  int(difference.max()))
    if name in DOCUMENTED_DIFFERENCE:
        if not np.array_equal(image[..., 3], reference[..., 3]):
            return "alpha differs"
        return smooth_line_difference(image, reference, max_differing_fraction=None)
    return smooth_line_difference(image, reference)
