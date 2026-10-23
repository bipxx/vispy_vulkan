# SPDX-License-Identifier: AGPL-3.0-only
"""Retain original scalar regions/tolerances and exact categorical semantics."""
import copy
import json
import numpy as np
import pytest
from tools import volume_wheel_reference as reference


def candidate_params(name, params):
    result = copy.deepcopy(params)
    if name not in reference.DIRECT_CASES:
        result['native_mro'] = ['DawnCanvas', 'QWidget']
    return result


@pytest.mark.parametrize('name', reference.CASES)
def test_original_reference_and_comparison_contract(name):
    image, params = reference.load_case(name)
    assert not image.flags.writeable
    measured = reference.compare_case(name, image, image, candidate_params(name, params), params)
    assert measured['comparison_criteria_passed']
    assert measured['interior_maximum_channel_error'] == measured['edge_differing_pixels'] == 0


def test_scalar_original_two_step_interior_tolerance_is_preserved():
    image, params = reference.load_case('mip')
    interior, _ = reference.scalar.masks('mip', image.shape)
    assert interior[0, 0]
    changed = image.copy()
    changed[0, 0, 0] = 2
    measured = reference.compare_case('mip', changed, image, params, params)
    assert measured['interior_maximum_channel_error'] == 2
    changed[0, 0, 0] = 3
    with pytest.raises(AssertionError, match='Original interior error exceeded'):
        reference.compare_case('mip', changed, image, params, params)


def test_scalar_original_edge_band_is_checked_not_discarded():
    image, params = reference.load_case('mip')
    _, edge = reference.scalar.masks('mip', image.shape)
    changed = image.copy()
    changed[edge, 0] ^= 1
    with pytest.raises(AssertionError, match='Original edge mismatch exceeded'):
        reference.compare_case('mip', changed, image, params, params)


def test_categorical_alpha_difference_cannot_pass_with_identical_rgb():
    name = 'categorical_edit'
    image, params = reference.load_case(name)
    changed = image.copy()
    changed[0, 0, 3] ^= 1
    with pytest.raises(AssertionError, match='Exact categorical RGBA differs'):
        reference.compare_case(name, changed, image, candidate_params(name, params), params)


@pytest.mark.parametrize('name,key,value', [
    ('mip', 'relative_step_size', 1),
    ('iso', 'threshold', .5),
    ('categorical_edit', 'inputs', []),
    ('categorical_clip', 'labels', [0, 7, 65537]),
])
def test_matching_frame_cannot_hide_quality_or_semantic_changes(name, key, value):
    image, params = reference.load_case(name)
    changed = candidate_params(name, params)
    changed[key] = value
    with pytest.raises(AssertionError, match='Volume parameters differ'):
        reference.compare_case(name, image, image, changed, params)


def test_original_opengl_widget_cannot_masquerade_as_candidate_widget():
    image, params = reference.load_case('categorical_plane')
    with pytest.raises(AssertionError):
        reference.compare_case('categorical_plane', image, image, params, params)


def test_a_modified_manifest_is_not_a_new_reference(tmp_path):
    packet = tmp_path / 'volume-opengl'
    packet.mkdir()
    manifest = reference.load_manifest('volume-opengl')
    manifest['comparison']['interior_max_abs_u8'] = 255
    (packet / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='manifest differs'):
        reference.load_manifest('volume-opengl', tmp_path)


def test_missing_case_remains_an_error():
    with pytest.raises(ValueError, match='Unknown required volume case'):
        reference.load_case('skip-failing-volume')
