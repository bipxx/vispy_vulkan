"""Mutation controls for exact native/GL training comparison; no oracle files."""
from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from smooth_line_frame_comparison import canonical_rows, compare_frame, compare_training_streams, validate_rows
sys.path.pop(0)


def frame():
    image = np.zeros((64, 64, 4), dtype=np.uint8)
    image[20, 12:52, :3] = 255
    image[20, 12:52, 3] = 132
    return image


@pytest.mark.parametrize('mutation', ('role', 'order', 'geometry', 'bool-index', 'float-width', 'extra-key'))
def test_descriptors_refuse_before_consuming_frames(mutation):
    rows = deepcopy(list(canonical_rows()))
    if mutation == 'role':
        rows[0]['study'] = 'new-holdout-role-0'
    elif mutation == 'order':
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == 'geometry':
        rows[0]['start_units'][0] += 1
    elif mutation == 'bool-index':
        rows[0]['index'] = False
    elif mutation == 'float-width':
        rows[0]['width_units'] = 256.0
    else:
        rows[0]['admitted'] = True
    def untouched():
        raise AssertionError('Frame access before descriptor refusal')
        yield
    with pytest.raises(ValueError, match='Canonical'):
        compare_training_streams(rows, untouched(), untouched())


def test_canonical_union_has_exact_role_boundaries():
    rows = validate_rows(canonical_rows())
    assert len(rows) == 11136
    assert rows[7039]['study'] == 'original' and rows[7039]['index'] == 7039
    assert rows[7040]['study'] == 'corner' and rows[7040]['index'] == 0


def test_alpha_error_retains_full_byte_error_without_mask_error():
    actual, reference = frame(), frame()
    actual[20, 20, 3] += 1
    metrics = compare_frame(actual, reference)
    assert metrics['differing_pixels'] == metrics['alpha_differences'] == metrics['maximum_channel_error'] == 1
    assert metrics['generated_mask_differences'] == 0


def test_generated_zero_alpha_is_not_mistaken_for_clear():
    actual, reference = frame(), frame()
    actual[19, 20, :3] = 255
    metrics = compare_frame(actual, reference)
    assert metrics['differing_pixels'] == metrics['generated_mask_differences'] == 1
    assert metrics['alpha_differences'] == 0 and metrics['maximum_channel_error'] == 255


@pytest.mark.parametrize('bad', ('float', 'shape', 'colored', 'opaque-background'))
def test_non_observation_frames_refuse(bad):
    actual = frame()
    if bad == 'float':
        actual = actual.astype(np.float32)
    elif bad == 'shape':
        actual = actual[:, :, :3]
    elif bad == 'colored':
        actual[20, 20, 0] = 254
    else:
        actual[0, 0, 3] = 1
    with pytest.raises(ValueError):
        compare_frame(actual, frame())


def test_truncated_stream_cannot_return_a_pass():
    with pytest.raises(ValueError, match='Exactly one frame'):
        compare_training_streams(canonical_rows(), iter((frame(),)), iter((frame(),)))


def test_complete_nontrivial_stream_matches_and_extra_frame_refuses():
    rows, image = canonical_rows(), frame()
    result = compare_training_streams(rows, (image for _ in rows), (image for _ in rows))
    assert result['exact_nontrivial_training_match'] and result['rows_checked'] == 11136
    assert {key: value['rows'] for key, value in result['groups'].items()} == {
        'original-axial': 3072, 'original-oblique': 3968, 'corner': 4096}
    assert not result['renderer_qualified'] and not result['portable_generated_fallback_implemented']
    with pytest.raises(ValueError, match='Exactly one frame'):
        compare_training_streams(rows, (image for _ in range(11137)), (image for _ in rows))


@pytest.mark.parametrize('kind', ('clear', 'aliased'))
def test_equal_trivial_frames_cannot_pass(kind):
    image = frame()
    image[:, :, 3] = 0 if kind == 'clear' else 255
    if kind == 'clear':
        image[:, :, :3] = 0
    else:
        image[:, :, 3][image[:, :, 0] == 0] = 0
    rows = canonical_rows()
    result = compare_training_streams(rows, (image for _ in rows), (image for _ in rows))
    assert result['differing_pixels'] == 0 and len(result['invalid_rows']) == 11136
    assert not result['exact_nontrivial_training_match']
