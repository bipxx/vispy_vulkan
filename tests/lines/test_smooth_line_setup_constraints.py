"""Geometric invariance and exact contradiction controls, without oracle data."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from smooth_line_setup_constraints import (affine_ramp_constraint, central_pixels, decode_alpha,
                                         directed_infinite_line, minor_distance_numerators, translation_pairs,
                                         fixed_affine_intercept)
sys.path.pop(0)


def row(start=(3072,3072), end=(12288,7680), width=832):
    return dict(start_units=list(start), end_units=list(end), width_units=width)


def test_infinite_geometry_retains_direction_width_and_perpendicular_offset():
    original = row()
    translated = row((3584,3328), (12800,7936))
    reversed_row = row(tuple(original['end_units']), tuple(original['start_units']))
    shifted = row((3072,3073), (12288,7681))
    assert directed_infinite_line(original) == directed_infinite_line(translated)
    assert all(directed_infinite_line(original) != directed_infinite_line(other)
               for other in (reversed_row, shifted, row(width=833)))
    assert translation_pairs([original, translated, reversed_row, shifted]) == ((0,1),)


def test_reversal_preserves_distance_and_central_mask():
    original = row()
    reverse = row(tuple(original['end_units']), tuple(original['start_units']))
    np.testing.assert_array_equal(central_pixels(original), central_pixels(reverse))
    np.testing.assert_array_equal(minor_distance_numerators(original), minor_distance_numerators(reverse))


def test_decode_checks_every_possible_byte():
    codes = np.arange(32, dtype=np.int32)
    valid = ((263*codes+16)//32).astype(np.uint8)
    np.testing.assert_array_equal(decode_alpha(valid), codes)
    for invalid in set(range(256))-set(map(int,valid)):
        with pytest.raises(ValueError):
            decode_alpha(np.array([invalid], dtype=np.uint8))


def test_exact_linear_samples_admit_and_duplicates_do_not_change_bounds():
    samples = [(0,2), (4,10), (8,18), (12,26)]
    proof = affine_ramp_constraint(samples)
    assert proof['feasible'] and proof['informative']
    repeated = affine_ramp_constraint(samples*3)
    assert repeated['lower_twice_gradient'] == proof['lower_twice_gradient']
    assert repeated['upper_twice_gradient'] == proof['upper_twice_gradient']


def test_nonlinear_samples_produce_exact_contradictory_witnesses():
    proof = affine_ramp_constraint([(0,2), (4,8), (8,17), (12,25)])
    assert not proof['feasible']
    lo, hi = proof['lower_twice_gradient'], proof['upper_twice_gradient']
    assert lo['numerator']*hi['denominator'] >= hi['numerator']*lo['denominator']


def test_touching_strict_bounds_are_infeasible():
    # First pair requires a<1; second requires a>1. Closed bounds would false-pass.
    proof = affine_ramp_constraint([(0,1), (2,2), (4,5)])
    assert not proof['feasible']


def test_conflicting_equal_distances_refuse_without_fitting():
    proof = affine_ramp_constraint([(0,2), (0,3)])
    assert not proof['feasible'] and proof['reason'] == 'conflicting-code-at-identical-distance'


@pytest.mark.parametrize('samples', ([(0,0)], [(0,31)], [(True,2)], [(1.0,2)], [(0,2.0)]))
def test_out_of_domain_samples_refuse(samples):
    with pytest.raises(ValueError):
        affine_ramp_constraint(samples)


@pytest.mark.parametrize('geometry', (row((0,0),(0,0)), row(width=True), row((True,0),(1,1))))
def test_bad_geometry_refuses(geometry):
    with pytest.raises(ValueError):
        directed_infinite_line(geometry)


def test_fixed_gradient_bounds_retain_rational_witnesses_and_open_upper():
    result = fixed_affine_intercept([(0,1),(2,2),(4,3)],1,2)
    assert result['feasible']
    assert result['lower']['numerator'] == 1 and result['lower']['denominator'] == 1
    assert result['upper']['numerator'] == 2 and result['upper']['denominator'] == 1
    assert result['lower']['inclusive'] and not result['upper']['inclusive']


def test_fixed_gradient_touching_bounds_refuse():
    result = fixed_affine_intercept([(0,0),(2,2)],1,2)
    assert not result['feasible']
    assert result['lower']['numerator'] == result['upper']['numerator'] == 1


@pytest.mark.parametrize('samples,numerator,denominator',(
    ([],1,2), ([(0,16)],1,2), ([(0,True)],1,2), ([(0,1)],True,2), ([(0,1)],1,0)))
def test_invalid_fixed_gradient_constraints_refuse(samples,numerator,denominator):
    with pytest.raises(ValueError):
        fixed_affine_intercept(samples,numerator,denominator)
