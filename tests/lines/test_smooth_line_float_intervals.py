# SPDX-License-Identifier: AGPL-3.0-only
"""Threshold searches must preserve one shared constant and actual FP orders."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from smooth_line_float_intervals import ORDERS, ordered_keys, decode_keys, evaluate_plane, constant_interval
sys.path.pop(0)


def test_ordered_encoding_roundtrip_including_signed_zero_and_subnormals():
    bits = np.array([0xc4000000, 0xbf800000, 0x80000001, 0x80000000,
                     0, 1, 0x3f800000, 0x44000000], np.uint32)
    values = bits.view(np.float32)
    keys = ordered_keys(values)
    assert np.all(keys[1:] > keys[:-1])
    np.testing.assert_array_equal(decode_keys(keys).view(np.uint32), bits)


@pytest.mark.parametrize('order', ORDERS)
@pytest.mark.parametrize('offset', (0, 2.125))
def test_exact_single_observation_bounds(order, offset):
    interval = constant_interval([(1, 1, 1)], 0, 0, order, offset=offset)
    assert interval['feasible'] and not interval['common_constant_selected_for_prediction']
    assert interval['lower_ordered_key'] == int(ordered_keys(np.float32(1 / 16 - offset)))
    assert interval['upper_exclusive_ordered_key'] == int(ordered_keys(np.float32(2 / 16 - offset)))


@pytest.mark.parametrize('order', ORDERS)
def test_no_per_pixel_constant_can_hide_conflicting_observations(order):
    interval = constant_interval([(7, 9, 1), (7, 9, 2)], .5, -.25, order)
    assert not interval['feasible']
    assert interval['lower_ordered_key'] >= interval['upper_exclusive_ordered_key']


@pytest.mark.parametrize('order', ORDERS)
@pytest.mark.parametrize('nibble', (0, 15))
def test_saturation_keeps_only_the_original_one_sided_constraint(order, nibble):
    interval = constant_interval([(1, 1, nibble)], 0, 0, order)
    assert interval['feasible']
    if nibble == 0:
        assert interval['lower_ordered_key'] == interval['domain_first_ordered_key']
        assert interval['upper_exclusive_ordered_key'] == int(ordered_keys(np.float32(1 / 16)))
    else:
        assert interval['lower_ordered_key'] == int(ordered_keys(np.float32(15 / 16)))
        assert interval['upper_exclusive_ordered_key'] == interval['domain_last_ordered_key'] + 1


@pytest.mark.parametrize('order', ORDERS)
def test_small_domain_binary_search_matches_exhaustive_float_encodings(order):
    center = int(ordered_keys(np.float32(-1 / 16)))
    keys = np.arange(center - 4, center + 5, dtype=np.uint64)
    constants = decode_keys(keys)
    value = evaluate_plane(.5, -.25, constants, .5, .5, order)
    nibbles = np.clip(np.floor(value * value.dtype.type(16)), 0, 15)
    expected = keys[nibbles == 1]
    interval = constant_interval([(1, 1, 1)], .5, -.25, order,
        constant_bounds=(constants[0], constants[-1]))
    actual = np.arange(interval['lower_ordered_key'], interval['upper_exclusive_ordered_key'], dtype=np.uint64)
    np.testing.assert_array_equal(actual, expected)


def test_fused_evaluation_preserves_the_below_binary64_midpoint_addend():
    a = np.float32(1 + 2 ** -12)
    tiny = np.float32(2 ** -60)
    fused = evaluate_plane(a, 0, tiny, a, 0, 'fused-x-outer')
    split = evaluate_plane(a, 0, tiny, a, 0, 'sum-then-constant')
    assert fused == np.nextafter(split, np.float32(np.inf))


@pytest.mark.parametrize('sample', [[(0, 1, 1)], [(1, 2, 1)], [(1, 1, 16)], [(True, 1, 1)], []])
def test_invalid_observations_refuse(sample):
    with pytest.raises(ValueError):
        constant_interval(sample, 1, 1, ORDERS[0])


def test_unknown_order_or_unbounded_inputs_refuse():
    with pytest.raises(ValueError):
        constant_interval([(1, 1, 1)], 1, 1, 'fitted-order')
    with pytest.raises(ValueError):
        constant_interval([(1, 1, 1)], np.inf, 1, ORDERS[0])
