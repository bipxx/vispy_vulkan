# SPDX-License-Identifier: AGPL-3.0-only
"""Frame parity for smooth (antialiased) lines.

OpenGL ``GL_LINE_SMOOTH`` coverage is driver-defined. The Dawn renderer's analytic
coverage (docs/smooth-lines.md) reproduces interiors exactly but may differ slightly
on antialiased edge pixels. Pixels whose 3x3 reference neighbourhood is uniform must
match exactly; other pixels may differ by at most EDGE_TOLERANCE per channel, and at
most MAX_DIFFERING_FRACTION of the frame may differ at all. Semantic checks such as
fixture landmarks stay separate and exact.
"""
import numpy as np

EDGE_TOLERANCE = 32  # of 255; NVIDIA GL_LINE_SMOOTH vs analytic coverage measured 26-29
MAX_DIFFERING_FRACTION = .01


def reference_edges(reference):
    """Pixels whose 3x3 neighbourhood in ``reference`` is not uniform."""
    height, width = reference.shape[:2]
    padded = np.pad(reference.astype(np.int16), ((1, 1), (1, 1), (0, 0)), mode='edge')
    windows = np.stack([padded[y:y + height, x:x + width] for y in range(3) for x in range(3)])
    return np.any(windows.max(axis=0) != windows.min(axis=0), axis=2)


def smooth_line_difference(image, reference):
    """Return None if ``image`` matches ``reference`` under the smooth-line rule, else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return 'shape or dtype differs'
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    differing = np.any(difference, axis=2)
    interior = differing & ~reference_edges(reference)
    if interior.any():
        return '%d interior pixels differ' % int(interior.sum())
    if difference.max() > EDGE_TOLERANCE:
        return 'edge difference %d exceeds %d' % (int(difference.max()), EDGE_TOLERANCE)
    if differing.sum() > MAX_DIFFERING_FRACTION * differing.size:
        return '%d pixels differ' % int(differing.sum())
    return None
