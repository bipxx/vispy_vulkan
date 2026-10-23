# SPDX-License-Identifier: AGPL-3.0-only
"""Original whole-frame references and semantic changes must remain distinguishable."""
import copy
import json
from pathlib import Path
import pytest
from tools.fixture_image_extensions import CASES
from tools import image_wheel_reference as reference


@pytest.mark.parametrize('name', CASES)
def test_original_reference_and_all_semantic_joins(name):
    image, params = reference.load_case(name)
    assert not image.flags.writeable
    reference.compare_case(name, image, image, params, params)


def test_one_non_landmark_alpha_change_fails_the_full_frame():
    image, params = reference.load_case('cpu_scalar_nan')
    changed = image.copy()
    changed[0, 0, 3] ^= 1
    with pytest.raises(AssertionError, match='Full-frame RGBA differs'):
        reference.compare_case('cpu_scalar_nan', changed, image, params, params)


@pytest.mark.parametrize('name,key', [
    ('labels_signed_remap', 'actual_label_remap'),
    ('labels_paint_tile', 'partial_labels_events'),
    ('multiscale_level1_edit', 'selected_level_sequence'),
    ('multiscale_level0_retained', 'source_revisions'),
    ('slice_change', 'selected_slice_sequence'),
    ('slice_change', 'initial_slice_records'),
])
def test_matching_pixels_do_not_hide_changed_semantic_observations(name, key):
    image, params = reference.load_case(name)
    changed = copy.deepcopy(params)
    del changed[key]
    with pytest.raises(AssertionError):
        reference.compare_case(name, image, image, changed, params)
    changed[key] = []
    with pytest.raises(AssertionError):
        reference.compare_case(name, image, image, changed, params)


def test_manifest_cannot_be_replaced_with_a_weaker_case_selection(tmp_path):
    manifest = json.loads((reference.REFERENCE / 'manifest.json').read_bytes())
    del manifest['fixtures']['gpu_scalar_nan']
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='manifest differs'):
        reference.load_manifest(tmp_path)


def test_corrupt_original_frame_is_refused_before_decoding(tmp_path):
    manifest = reference.load_manifest()
    record = manifest['fixtures']['rgba_nan']['rgba']
    path = tmp_path / record['file']
    path.write_bytes(b'not the original expected frame')
    with pytest.raises(ValueError, match='Reference bytes differ'):
        reference.read_record(tmp_path, record)


def test_unknown_case_is_not_a_pass_or_an_implicit_subset():
    with pytest.raises(ValueError, match='Unknown required image case'):
        reference.load_case('missing-required-labels')
