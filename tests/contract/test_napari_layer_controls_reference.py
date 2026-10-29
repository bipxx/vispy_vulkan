# SPDX-License-Identifier: AGPL-3.0-only
"""The napari layer-control OpenGL references (W5: B03, H01, V04) stay bound to this fixture and its exact criteria."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_napari_layer_controls import BACKGROUND, CASES, CRITERIA, SIZE, assert_landmarks, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'tests/reference/napari-layer-controls-opengl'
FIXED = ('case', 'size', 'camera', 'controls', 'background', 'criterion', 'inputs_sha256')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_layer_control_criteria_are_the_ones_fixed_before_capture():
    assert CRITERIA == {name: 'exact' for name in CASES}
    assert set(CASES) == {'opacity_mutation', 'first_layer_transition', 'additive_reorder', 'removal_screenshot',
                          'volume_iso', 'volume_attenuated_mip', 'volume_translucent_step'}
    # Every case changes its state after a first frame.
    for name in CASES:
        controls = specification(name)['controls']
        assert set(controls) == {'first', 'changed'} and controls['first'] != controls['changed'], name


def test_layer_control_references_bind_the_fixture_criteria_and_artifacts():
    manifest = json.loads((REFERENCE / 'manifest.json').read_text(encoding='utf-8'))
    origins = manifest['provenance']
    assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0' and origins['napari_version'] == '0.9.2'
    assert origins['fixture_source_sha256'] == digest(ROOT / 'tools/fixture_napari_layer_controls.py')
    assert origins['capture_source_sha256'] == digest(ROOT / 'tools/oracle_napari_layer_controls_capture.py')
    assert manifest['comparison']['criteria'] == CRITERIA and not manifest['errors']
    assert set(manifest['fixtures']) == set(CASES)
    for name, record in manifest['fixtures'].items():
        assert {key: record['parameters'][key] for key in FIXED} == {key: specification(name)[key] for key in FIXED}
        for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
            assert digest(REFERENCE / artifact['file']) == artifact['sha256']
        assert_landmarks(name, np.load(REFERENCE / record['rgba']['file'], allow_pickle=False))
    # H01: napari's layer removal requests its own finish; the reference records how many.
    assert manifest['fixtures']['removal_screenshot']['parameters']['finish_commands'] >= 1


def test_finish_counts_are_recorded_evidence_not_compared():
    # Decision D13: OpenGL's grabFramebuffer synchronizes inside Qt; the Dawn readback logs the same synchronization.
    from tools.napari_layer_controls_comparison import COMPARED_PARAMETERS
    assert 'finish_commands' not in COMPARED_PARAMETERS
    manifest = json.loads((REFERENCE / 'manifest.json').read_text(encoding='utf-8'))
    assert all(isinstance(record['parameters']['finish_commands'], int) for record in manifest['fixtures'].values())


def test_volume_iso_shading_rule_allows_only_few_small_edge_differences():
    # Decision D14: uniform reference neighbourhoods stay exact; at most 0.1% of the frame differs, by at most 4.
    from tools.napari_layer_controls_comparison import (MAX_SHADING_FRACTION, MAX_SHADING_LEVELS, SHADING,
                                                        layer_control_difference)
    assert SHADING == {'volume_iso'} and MAX_SHADING_FRACTION == .001 and MAX_SHADING_LEVELS == 4
    frame = np.empty((SIZE[1], SIZE[0], 4), np.uint8)
    frame[...] = BACKGROUND
    frame[40:60, 20:140] = (240, 110, 92, 255)
    shaded = frame.copy()
    shaded[40, 30:49, 1] += 4  # 19 edge pixels: 0.099% of 160x120, 4 levels
    assert layer_control_difference('volume_iso', shaded, frame) is None
    uniform = shaded.copy()
    uniform[50, 80, 1] += 1
    assert 'uniform pixels differ' in layer_control_difference('volume_iso', uniform, frame)
    deeper = shaded.copy()
    deeper[40, 30, 1] += 1
    assert 'exceeds 4' in layer_control_difference('volume_iso', deeper, frame)
    wider = shaded.copy()
    wider[40, 49, 1] += 1  # the 20th edge pixel
    assert 'shading pixels differ' in layer_control_difference('volume_iso', wider, frame)
    for name in sorted(set(CASES) - SHADING):
        assert 'pixels differ' in layer_control_difference(name, shaded, frame), name


@pytest.mark.parametrize('name', CASES)
def test_layer_control_landmarks_refuse_a_blank_frame(name):
    blank = np.empty((SIZE[1], SIZE[0], 4), np.uint8)
    blank[...] = BACKGROUND
    with pytest.raises(AssertionError):
        assert_landmarks(name, blank)


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
