# SPDX-License-Identifier: AGPL-3.0-only
"""The positioned-line rule (tools/positioned_line_comparison.py, D19; D8 revised under it): intensity on a stroke may
differ, but a gap, a stray, a shift, an interior or alpha change, or widespread differences still fail. CPU only."""
from pathlib import Path

import numpy as np
import pytest

from tools import positioned_line_comparison as rule
from tools.positioned_line_comparison import positioned_line_difference

ROOT = Path(__file__).resolve().parents[2]
SCHEDULED = ROOT / 'tests/reference/napari-render-plane-scheduled-opengl'
BACKGROUND, STROKE = (40, 40, 40, 255), (200, 120, 60, 255)


def stroke_frame(height=24, width=32, rows=(10, 13), columns=(4, 28)):
    """A uniform background with one 3-pixel-wide antialiased horizontal stroke."""
    frame = np.empty((height, width, 4), np.uint8)
    frame[:] = BACKGROUND
    frame[rows[0]:rows[1], columns[0]:columns[1]] = STROKE
    frame[rows[0] - 1, columns[0]:columns[1]] = (90, 70, 50, 255)  # antialiased fringe rows
    frame[rows[1], columns[0]:columns[1]] = (90, 70, 50, 255)
    return frame


def test_identical_frames_pass():
    frame = stroke_frame()
    assert positioned_line_difference(frame.copy(), frame) is None


def test_a_different_intensity_on_the_stroke_edge_passes():
    reference = stroke_frame(height=100, width=100)
    candidate = reference.copy()
    candidate[9, 20:25] = (160, 110, 70, 255)  # brighter fringe: 70 levels, at the stroke's own place
    assert positioned_line_difference(candidate, reference) is None


def test_a_gap_in_a_wide_stroke_fails():
    reference = stroke_frame()
    candidate = reference.copy()
    candidate[9:14, 12:19] = BACKGROUND  # the stroke's uniform middle row is an interior change
    assert positioned_line_difference(candidate, reference) is not None


def test_a_gap_in_a_thin_stroke_fails_on_position():
    # A 1-pixel core with fringes, so every stroke pixel is an edge; a large frame keeps the gap under the 1% cap.
    reference = stroke_frame(height=100, width=100, rows=(10, 11), columns=(4, 96))
    candidate = reference.copy()
    candidate[9:12, 12:19] = BACKGROUND
    assert 'not on an edge of both frames' in positioned_line_difference(candidate, reference)


def test_a_stray_block_away_from_the_stroke_fails():
    reference = stroke_frame()
    candidate = reference.copy()
    candidate[18:21, 20:23] = STROKE
    assert 'interior' in positioned_line_difference(candidate, reference)


def test_a_shifted_stroke_fails():
    reference = stroke_frame()
    candidate = stroke_frame(rows=(12, 15))
    assert positioned_line_difference(candidate, reference) is not None


def test_interior_and_alpha_changes_fail():
    reference = stroke_frame()
    candidate = reference.copy()
    candidate[2, 2, 0] ^= 1
    assert 'interior' in positioned_line_difference(candidate, reference)
    candidate = reference.copy()
    candidate[9, 10, 3] = 254
    assert 'alpha' in positioned_line_difference(candidate, reference)


def test_too_many_pixels_beyond_the_edge_bound_fail():
    reference = stroke_frame(height=100, width=100, columns=(4, 96))
    candidate = reference.copy()
    candidate[9, 20:40] = (160, 110, 70, 255)  # 20 > 0.1% of 10,000 pixels, below the 1% differing cap
    assert 'exceed' in positioned_line_difference(candidate, reference)


def test_widespread_differences_fail_the_frame_cap():
    reference = stroke_frame()
    candidate = reference.copy()
    candidate[9, 4:28] = (100, 75, 52, 255)  # every fringe pixel of one row, more than 1% of the frame
    assert 'pixels differ' in positioned_line_difference(candidate, reference)


def test_shape_and_dtype_must_match():
    frame = stroke_frame()
    assert positioned_line_difference(frame[:-1], frame) is not None
    assert positioned_line_difference(frame.astype(np.int16), frame) is not None


def test_the_rule_keeps_the_smooth_line_constants_and_the_d12_edge_limit():
    from tools import smooth_line_parity
    assert rule.EDGE_TOLERANCE == smooth_line_parity.EDGE_TOLERANCE == 32
    assert rule.MAX_DIFFERING_FRACTION == smooth_line_parity.MAX_DIFFERING_FRACTION == .01
    assert rule.MAX_OVER_FRACTION == .001


@pytest.mark.parametrize('name', ('plane_handles', 'plane_translation', 'plane_rotation', 'plane_clipped'))
def test_each_d8_reference_matches_itself(name):
    reference = np.load(SCHEDULED / f'{name}.rgba.npy', allow_pickle=False)
    assert positioned_line_difference(reference.copy(), reference) is None


# Only the tests are re-exported into CI's curated list (tests/contract/curated_contracts.py).
__all__ = [name for name in dir() if name.startswith('test_')]
