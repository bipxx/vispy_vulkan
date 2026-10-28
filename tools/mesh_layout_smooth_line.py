# SPDX-License-Identifier: AGPL-3.0-only
"""Installed-wheel mesh/layout comparison with the smooth-line criterion for the axes/colorbar scene.

The pinned fixture (tools/fixture_mesh_layout_extensions.py) compares axes_colorbar exactly. Its axis and
colorbar lines are smooth (antialiased) lines, so decision D5 compares that scene with
tools/smooth_line_parity.py instead: uniform reference neighbourhoods exact, edges within the bound, at most 1%
of the frame differing. The fixture's landmarks stay exact. Every other scene keeps the fixture's comparison.

Decision D9 (user, 2026-10-28) closes axes_colorbar with a documented difference: its 166-px antialiased axis line's
edge rows follow GL's driver-defined side coverage, about 11-12 levels from Dawn's, which alone exceeds the 1% frame
cap in this 224x160 frame. So the frame cap does not apply to that scene, and alpha must match exactly instead.
Interiors stay exact, every edge stays within the bound, and the landmarks stay exact.
"""
from __future__ import annotations

import numpy as np

try:
    from .fixture_mesh_layout_extensions import SIZE, assert_landmarks, compare as fixture_compare
    from .smooth_line_parity import smooth_line_difference
except ImportError:
    from fixture_mesh_layout_extensions import SIZE, assert_landmarks, compare as fixture_compare
    from smooth_line_parity import smooth_line_difference

SMOOTH_LINE = frozenset({'axes_colorbar'})
DOCUMENTED_DIFFERENCE = frozenset({'axes_colorbar'})  # decision D9: no frame cap, exact alpha


def compare(name, actual, reference):
    """The fixture's comparison, except the smooth-line criterion for the scenes in SMOOTH_LINE."""
    if name not in SMOOTH_LINE:
        return fixture_compare(name, actual, reference)
    assert actual.shape == reference.shape == (SIZE[1], SIZE[0], 4)
    assert actual.dtype == reference.dtype == np.uint8
    if name in DOCUMENTED_DIFFERENCE:
        assert np.array_equal(actual[..., 3], reference[..., 3]), (name, 'Alpha differs')
        reason = smooth_line_difference(actual, reference, max_differing_fraction=None)
    else:
        reason = smooth_line_difference(actual, reference)
    assert reason is None, (name, reason)
    assert_landmarks(name, actual)
