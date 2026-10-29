# SPDX-License-Identifier: AGPL-3.0-only
"""The wide-line comparison (W5, M08), with decisions D15 and D16.

The fixtures (tools/fixture_wide_lines.py, tools/fixture_wide_lines_depth.py) fixed every frame as exact before
capture, and decision D5 kept them exact. Two user decisions (2026-10-29) followed:

- D15: smooth (antialiased) cases use the smooth-line criterion (tools/smooth_line_parity.py) without its 1% frame
  cap, like D9-D11, and alpha must match exactly. In these 32x24 frames the cap is under 8 pixels, while GL's
  driver-defined smooth coverage differs on up to 68 edge pixels. Aliased cases stay exact.
- D16: both reference packets were captured with the shared fixture before its reviewed replacement on 2026-10-11,
  which added only the depth clear for depth_occlusion_smooth. The packets keep that capture binding, and the tests
  pin both exact hashes.
"""
from __future__ import annotations

import numpy as np

try:
    from .smooth_line_parity import smooth_line_difference
except ImportError:
    from smooth_line_parity import smooth_line_difference

CAPTURED_SHARED_FIXTURE_SHA256 = "f689a08a8df084058eaa5cacf9c9833a155b1a2c210bcd8ad325c182852d750c"  # decision D16
CANONICAL_SHARED_FIXTURE_SHA256 = "2568d76fa52e1c1f252ec0913f3c0e6d8a2b226ef55a2cdc2bd6c64baf004ed5"


def wide_line_difference(smooth, image, reference):
    """Return None if ``image`` matches ``reference`` (smooth cases: decision D15; aliased: exact), else why not."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return "shape or dtype differs"
    if not smooth:
        difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
        differing = np.any(difference, axis=2)
        return None if not differing.any() else "%d pixels differ, by up to %d" % (int(differing.sum()),
                                                                                  int(difference.max()))
    if not np.array_equal(image[..., 3], reference[..., 3]):
        return "alpha differs"
    return smooth_line_difference(image, reference, max_differing_fraction=None)
