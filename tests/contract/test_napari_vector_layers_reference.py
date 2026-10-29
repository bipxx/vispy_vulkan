# SPDX-License-Identifier: AGPL-3.0-only
"""The napari vector-layer OpenGL references (W4, M11) stay bound to this fixture and its criteria fixed before capture."""
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.fixture_napari_vector_layers import CASES, CRITERIA, assert_landmarks, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'tests/reference/napari-vector-layers-opengl'
FIXED = ('case', 'size', 'camera_center', 'camera_zoom', 'background', 'criterion', 'inputs_sha256')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_vector_layer_criteria_are_the_ones_fixed_before_capture():
    assert CRITERIA == {'vectors': 'exact', 'tracks': 'smooth_line', 'shapes_selected': 'smooth_line'}
    assert set(CRITERIA) == set(CASES)


def test_vector_layer_references_bind_the_fixture_criteria_and_artifacts():
    manifest = json.loads((REFERENCE / 'manifest.json').read_text(encoding='utf-8'))
    origins = manifest['provenance']
    assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0' and origins['napari_version'] == '0.9.2'
    assert origins['fixture_source_sha256'] == digest(ROOT / 'tools/fixture_napari_vector_layers.py')
    assert origins['capture_source_sha256'] == digest(ROOT / 'tools/oracle_napari_vector_layers_capture.py')
    assert manifest['comparison']['criteria'] == CRITERIA and not manifest['errors']
    assert set(manifest['fixtures']) == set(CASES)
    for name, record in manifest['fixtures'].items():
        assert {key: record['parameters'][key] for key in FIXED} == {key: specification(name)[key] for key in FIXED}
        for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
            assert digest(REFERENCE / artifact['file']) == artifact['sha256']
        assert_landmarks(name, np.load(REFERENCE / record['rgba']['file'], allow_pickle=False))


def test_tracks_and_shapes_documented_difference_drops_only_the_frame_cap():
    # Decision D10: like D9, antialiased edges may differ within the bound beyond 1% of the frame; nothing else relaxes.
    from tools.fixture_napari_vector_layers import BACKGROUND, SIZE
    from tools.napari_vector_layers_comparison import DOCUMENTED_DIFFERENCE, smooth_line_case_difference
    from tools.smooth_line_parity import EDGE_TOLERANCE, smooth_line_difference
    assert DOCUMENTED_DIFFERENCE == {name for name, criterion in CRITERIA.items() if criterion == 'smooth_line'}
    frame = np.empty((SIZE[1], SIZE[0], 4), np.uint8)
    frame[...] = BACKGROUND
    frame[40:44, 8:120] = (240, 240, 240, 255)
    rows = frame.copy()
    rows[40, 8:120, :3] -= 12
    rows[43, 8:120, :3] -= 12
    assert smooth_line_difference(rows, frame) == '%d pixels differ' % (2 * 112)
    for name in sorted(DOCUMENTED_DIFFERENCE):
        assert smooth_line_case_difference(name, rows, frame) is None
        for label, changed in (('interior', rows.copy()), ('edge difference', rows.copy()), ('alpha', rows.copy())):
            if label == 'interior':
                changed[41, 60, 0] -= 1
            elif label == 'edge difference':
                changed[40, 60, 0] = frame[40, 60, 0] - EDGE_TOLERANCE - 1
            else:
                changed[40, 60, 3] -= 1
            assert label in smooth_line_case_difference(name, changed, frame), (name, label)


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
