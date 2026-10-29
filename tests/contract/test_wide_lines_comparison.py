# SPDX-License-Identifier: AGPL-3.0-only
"""The wide-line comparison (M08): decision D15's smooth-case rule and decision D16's pinned fixture replacement."""
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.smooth_line_parity import EDGE_TOLERANCE, smooth_line_difference
from tools.wide_lines_comparison import (CANONICAL_SHARED_FIXTURE_SHA256, CAPTURED_SHARED_FIXTURE_SHA256,
                                         wide_line_difference)

ROOT = Path(__file__).resolve().parents[2]


def frames():
    frame = np.zeros((24, 32, 4), np.uint8)
    frame[..., 3] = 255
    frame[8:16, 4:28] = (0, 255, 0, 255)
    border = frame.copy()
    border[[8, 15], 4:28, 1] -= 19  # 48 edge pixels: 6% of the 768-pixel frame, 19 levels
    return frame, border


def test_smooth_wide_line_cases_drop_only_the_frame_cap():
    # Decision D15: like D9-D11, antialiased edges may differ within the bound beyond 1% of the frame.
    frame, border = frames()
    assert smooth_line_difference(border, frame).endswith('pixels differ')
    assert wide_line_difference(True, border, frame) is None
    for label, changed in (('interior', border.copy()), ('edge difference', border.copy()), ('alpha', border.copy())):
        if label == 'interior':
            changed[11, 16, 1] -= 1
        elif label == 'edge difference':
            changed[8, 16, 1] = frame[8, 16, 1] - EDGE_TOLERANCE - 1
        else:
            changed[8, 16, 3] -= 1
        assert label in wide_line_difference(True, changed, frame), label
    # Aliased cases stay exact.
    assert wide_line_difference(False, frame, frame.copy()) is None
    assert 'pixels differ' in wide_line_difference(False, border, frame)


def test_shared_wide_line_fixture_replacement_is_pinned_exactly():
    # Decision D16: both packets keep the shared fixture they were captured with; the current fixture is the reviewed
    # replacement, and any other change still fails.
    current = hashlib.sha256((ROOT / 'tools/fixture_wide_lines.py').read_bytes()).hexdigest()
    assert current == CANONICAL_SHARED_FIXTURE_SHA256 != CAPTURED_SHARED_FIXTURE_SHA256
    wide = json.loads((ROOT / 'tests/reference/wide-lines-opengl/manifest.json').read_text())
    depth = json.loads((ROOT / 'tests/reference/wide-lines-depth-opengl/manifest.json').read_text())
    assert wide['provenance']['wide_fixture_sha256'] == CAPTURED_SHARED_FIXTURE_SHA256
    assert depth['provenance']['shared_fixed_fixture_sha256'] == CAPTURED_SHARED_FIXTURE_SHA256


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
