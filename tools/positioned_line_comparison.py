# SPDX-License-Identifier: AGPL-3.0-only
"""Frame parity for lines judged by position, not exact intensity (decision D19; D8 revised under it).

The user's rule (2026-10-29): lines pass when they are correctly positioned and look right; exact pixels are not
required. This is the smooth-line criterion (tools/smooth_line_parity.py, decision D5) with one allowance. Pixels
whose 3x3 reference neighbourhood is uniform match exactly, alpha matches exactly, at most MAX_DIFFERING_FRACTION of
the frame differs, and edge pixels differ by at most EDGE_TOLERANCE. The allowance: a pixel beyond EDGE_TOLERANCE is
allowed when it lies on an edge in both frames, so both frames draw the stroke there, only with a different intensity,
and when at most MAX_OVER_FRACTION of the frame is such pixels. A gap or a stray pixel leaves one frame uniform where
the other has a stroke, so it still fails. Fixture landmarks stay separate and exact.
Fixed before D8's four cases were re-run, with CPU negative controls in tests/contract/test_positioned_line_comparison.py.
"""
import numpy as np

from tools.smooth_line_parity import EDGE_TOLERANCE, MAX_DIFFERING_FRACTION, reference_edges

MAX_OVER_FRACTION = .001  # of the frame; the edge-pixel limit of D12 and D17


def positioned_line_difference(image, reference):
    """Return None if ``image`` matches ``reference`` under the positioned-line rule, else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return 'shape or dtype differs'
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    if difference.shape[2] == 4 and difference[..., 3].any():
        return '%d pixels differ in alpha' % int(np.count_nonzero(difference[..., 3]))
    differing = np.any(difference, axis=2)
    reference_edge = reference_edges(reference)
    interior = differing & ~reference_edge
    if interior.any():
        return '%d interior pixels differ' % int(interior.sum())
    if differing.sum() > MAX_DIFFERING_FRACTION * differing.size:
        return '%d pixels differ' % int(differing.sum())
    over = difference.max(axis=2) > EDGE_TOLERANCE
    unpositioned = over & ~(reference_edge & reference_edges(image))
    if unpositioned.any():
        return '%d pixels beyond %d are not on an edge of both frames' % (int(unpositioned.sum()), EDGE_TOLERANCE)
    if over.sum() > MAX_OVER_FRACTION * over.size:
        return '%d pixels exceed %d' % (int(over.sum()), EDGE_TOLERANCE)
    return None
