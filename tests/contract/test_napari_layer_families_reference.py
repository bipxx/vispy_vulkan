# SPDX-License-Identifier: AGPL-3.0-only
"""The napari layer-family OpenGL references (W4) stay bound to this fixture and its criteria fixed before capture."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_napari_layer_families import BACKGROUND, CASES, CRITERIA, assert_landmarks, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'tests/reference/napari-layer-families-opengl'
FIXED = ('case', 'size', 'camera', 'background', 'criterion', 'inputs_sha256')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_layer_family_criteria_are_the_ones_fixed_before_capture():
    assert CRITERIA == {'labels_r8': 'exact', 'labels_r16': 'exact', 'surface_shaded': 'exact',
                        'surface_wireframe': 'exact', 'scale_bar_axes': 'smooth_line', 'colorbar': 'smooth_line',
                        'histogram': 'smooth_line', 'sized_export': 'exact'}
    assert set(CRITERIA) == set(CASES)


def test_layer_family_references_bind_the_fixture_criteria_and_artifacts():
    manifest = json.loads((REFERENCE / 'manifest.json').read_text(encoding='utf-8'))
    origins = manifest['provenance']
    assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0' and origins['napari_version'] == '0.9.2'
    assert origins['fixture_source_sha256'] == digest(ROOT / 'tools/fixture_napari_layer_families.py')
    assert origins['capture_source_sha256'] == digest(ROOT / 'tools/oracle_napari_layer_families_capture.py')
    assert manifest['comparison']['criteria'] == CRITERIA and not manifest['errors']
    assert set(manifest['fixtures']) == set(CASES)
    for name, record in manifest['fixtures'].items():
        assert {key: record['parameters'][key] for key in FIXED} == {key: specification(name)[key] for key in FIXED}
        for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
            assert digest(REFERENCE / artifact['file']) == artifact['sha256']
        assert_landmarks(name, np.load(REFERENCE / record['rgba']['file'], allow_pickle=False))


def frame_with_block(name):
    width, height = specification(name)['size']
    frame = np.empty((height, width, 4), np.uint8)
    frame[...] = BACKGROUND
    frame[40:60, 8:width - 8] = (240, 240, 240, 255)
    return frame


def lowered_border(frame):
    # The block's whole border, 12 levels darker: edge pixels only, more than 1% of every case's frame.
    border = frame.copy()
    border[[40, 59], 8:-8, :3] -= 12
    border[41:59, [8, -9], :3] -= 12
    assert np.any(border != frame, axis=2).sum() > .01 * frame.shape[0] * frame.shape[1]
    return border


@pytest.mark.parametrize('name', ['colorbar', 'histogram'])
def test_colorbar_and_histogram_documented_difference_drops_only_the_frame_cap(name):
    # Decision D11: like D9 and D10, antialiased edges may differ within the bound beyond 1% of the frame.
    from tools.napari_layer_families_comparison import DOCUMENTED_DIFFERENCE, layer_family_difference
    from tools.smooth_line_parity import EDGE_TOLERANCE, smooth_line_difference
    assert DOCUMENTED_DIFFERENCE == {'colorbar', 'histogram'}
    frame = frame_with_block(name)
    rows = lowered_border(frame)
    assert smooth_line_difference(rows, frame).endswith('pixels differ')
    assert layer_family_difference(name, rows, frame) is None
    for label, changed in (('interior', rows.copy()), ('edge difference', rows.copy()), ('alpha', rows.copy())):
        if label == 'interior':
            changed[41, 60, 0] -= 1
        elif label == 'edge difference':
            changed[40, 60, 0] = frame[40, 60, 0] - EDGE_TOLERANCE - 1
        else:
            changed[40, 60, 3] -= 1
        assert label in layer_family_difference(name, changed, frame), (name, label)


def test_surface_shaded_edge_pixel_rule_allows_only_few_edge_flips():
    # Decision D12: a flipped face at a near-tie edge pixel may differ by any amount; interiors stay exact, and at
    # most 0.1% of the frame may differ.
    from tools.napari_layer_families_comparison import EDGE_PIXELS, MAX_EDGE_FRACTION, layer_family_difference
    assert EDGE_PIXELS == {'surface_shaded'} and MAX_EDGE_FRACTION == .001
    frame = frame_with_block('surface_shaded')
    flipped = frame.copy()
    flipped[40, 10:17, :3] = (17, 10, 28)  # 7 edge pixels, any level
    assert layer_family_difference('surface_shaded', flipped, frame) is None
    interior = flipped.copy()
    interior[41, 60, 0] -= 1
    assert 'interior' in layer_family_difference('surface_shaded', interior, frame)
    many = frame.copy()
    many[40, 8:58, :3] = (17, 10, 28)  # 50 edge pixels: 0.1017% of 256x192
    assert 'edge pixels differ' in layer_family_difference('surface_shaded', many, frame)


def test_other_layer_families_keep_their_fixed_criteria():
    from tools.napari_layer_families_comparison import layer_family_difference
    for name in ('labels_r8', 'labels_r16', 'surface_wireframe', 'sized_export'):
        frame = frame_with_block(name)
        changed = frame.copy()
        changed[40, 10, 0] -= 1
        assert layer_family_difference(name, frame, frame.copy()) is None
        assert 'pixels differ' in layer_family_difference(name, changed, frame), name
    frame = frame_with_block('scale_bar_axes')
    assert layer_family_difference('scale_bar_axes', lowered_border(frame), frame).endswith('pixels differ')


@pytest.mark.parametrize('name', CASES)
def test_layer_family_landmarks_refuse_a_blank_frame(name):
    width, height = specification(name)['size']
    blank = np.empty((height, width, 4), np.uint8)
    blank[...] = BACKGROUND
    with pytest.raises(AssertionError):
        assert_landmarks(name, blank)


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
