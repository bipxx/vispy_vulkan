"""Exact grid rounding must handle signs, irrational roots and tie parity."""
from fractions import Fraction as F
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_fixed_precision import ROUNDINGS,quantized_sqrt_ratio,binary_fraction_interval_member
sys.path.pop(0)


@pytest.mark.parametrize('mode,positive,negative',[
    ('nearest-even',F(5,8),F(-5,8)),('negative-infinity',F(1,2),F(-5,8)),
    ('positive-infinity',F(5,8),F(-1,2)),('zero',F(1,2),F(-1,2))])
def test_three_fifths_uses_signed_rounding(mode,positive,negative):
    assert quantized_sqrt_ratio(3,25,3,mode)==positive
    assert quantized_sqrt_ratio(-3,25,3,mode)==negative


def test_irrational_root_rounding_uses_exact_squared_comparisons():
    assert quantized_sqrt_ratio(1,2,3,'nearest-even')==F(3,4)
    assert quantized_sqrt_ratio(1,2,3,'negative-infinity')==F(5,8)


@pytest.mark.parametrize('mode',ROUNDINGS)
def test_exact_grid_values_and_zero_are_held(mode):
    assert quantized_sqrt_ratio(0,17,8,mode)==0
    assert quantized_sqrt_ratio(-3,4,1,mode)==F(-3,2)


@pytest.mark.parametrize('numerator,expected',[(1,0),(3,2),(-1,0),(-3,-2)])
def test_nearest_halfway_uses_even_integer(numerator,expected):
    assert quantized_sqrt_ratio(numerator,4,0,'nearest-even')==expected


@pytest.mark.parametrize('lower,upper,expected',[(F(1,3),F(2,3),F(1,2)),(F(-2,3),F(-1,3),F(-1,2))])
def test_fraction_grid_membership_in_both_signs(lower,upper,expected):
    result=binary_fraction_interval_member(lower,upper,2)
    assert result['exists'] and F(result['numerator'],result['denominator'])==expected


def test_fraction_grid_strict_upper_and_empty_interval():
    assert not binary_fraction_interval_member(F(1,3),F(1,2),1)['exists']
    assert not binary_fraction_interval_member(F(1),F(1),8)['exists']


@pytest.mark.parametrize('args',[(True,2,8,'zero'),(1,0,8,'zero'),(1,2,True,'zero'),(1,2,49,'zero'),(1,2,8,'fit')])
def test_sqrt_grid_input_refuses(args):
    with pytest.raises(ValueError):quantized_sqrt_ratio(*args)


def test_inexact_grid_interval_refuses():
    with pytest.raises(ValueError):binary_fraction_interval_member(0.,F(1),8)
