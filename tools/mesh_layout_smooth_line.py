# SPDX-License-Identifier: AGPL-3.0-only
"""Installed-wheel mesh/layout comparison with the smooth-line criterion for the axes/colorbar scene.

The pinned fixture (tools/fixture_mesh_layout_extensions.py) compares axes_colorbar exactly. Its axis and
colorbar lines are smooth (antialiased) lines, so decision D5 compares that scene with
tools/smooth_line_parity.py instead: uniform reference neighbourhoods exact, edges within the bound, at most 1%
of the frame differing. The fixture's landmarks stay exact. Every other scene keeps the fixture's comparison.
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


def compare(name, actual, reference):
    """The fixture's comparison, except the smooth-line criterion for the scenes in SMOOTH_LINE."""
    if name not in SMOOTH_LINE:
        return fixture_compare(name, actual, reference)
    assert actual.shape == reference.shape == (SIZE[1], SIZE[0], 4)
    assert actual.dtype == reference.dtype == np.uint8
    reason = smooth_line_difference(actual, reference)
    assert reason is None, (name, reason)
    assert_landmarks(name, actual)
