"""Certificate checks must preserve strict quantization bounds exactly."""
from fractions import Fraction as F
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_affine_certificate import verify_affine_nibble,affine_intercept_interval,binary32_interval_member
sys.path.pop(0)


def test_saturated_extremes_do_not_create_artificial_bounds():
    assert verify_affine_nibble([(1,1,0),(127,1,15)],(F(1),F(0),F(-20)))['verified']


def test_lower_bound_is_inclusive_and_upper_is_strict():
    assert verify_affine_nibble([(1,1,1)],(F(0),F(0),F(1)))['verified']
    assert not verify_affine_nibble([(1,1,0)],(F(0),F(0),F(1)))['verified']


def test_sub_binary64_difference_is_not_rounded_to_a_boundary():
    inside=F(1)-F(1,2**55)
    assert float(inside)==1.0
    assert verify_affine_nibble([(1,1,0)],(F(0),F(0),inside))['verified']


def test_conflicting_identical_pixel_cannot_verify():
    result=verify_affine_nibble([(1,1,0),(1,1,1)],(F(0),F(0),F(1,2)))
    assert not result['verified'] and result['first_violation']['index']==1


@pytest.mark.parametrize('samples,coefficients',[
    ([],(F(0),F(0),F(0))),
    ([(0,1,1)],(F(0),F(0),F(0))),
    ([(1,1,16)],(F(0),F(0),F(0))),
    ([(True,1,1)],(F(0),F(0),F(0))),
    ([(1,1,1)],(0.,0.,1.)),
])
def test_inexact_or_out_of_domain_input_refuses(samples,coefficients):
    with pytest.raises(ValueError):verify_affine_nibble(samples,coefficients)


def test_fixed_slopes_yield_an_interval_without_selecting_a_constant():
    result=affine_intercept_interval([(1,1,1),(3,1,2)],F(1,2),F(0))
    assert result['feasible']
    assert result['lower']['numerator']==1 and result['lower']['denominator']==2
    assert result['upper']['numerator']==3 and result['upper']['denominator']==2
    assert result['lower']['inclusive'] and not result['upper']['inclusive']


def test_equal_lower_upper_bounds_are_infeasible():
    result=affine_intercept_interval([(1,1,0),(3,1,1)],F(0),F(0))
    assert not result['feasible']
    assert result['lower']['numerator']==result['upper']['numerator']==1


@pytest.mark.parametrize('n,missing',[(0,'lower'),(15,'upper')])
def test_saturated_constraints_can_have_an_unbounded_side(n,missing):
    result=affine_intercept_interval([(1,1,n)],F(0),F(0))
    assert result['feasible'] and result[missing] is None


def test_interval_does_not_round_rational_endpoints_to_binary64():
    tiny=F(1,2**55)
    result=affine_intercept_interval([(1,1,1)],tiny,F(0))
    lower=F(result['lower']['numerator'],result['lower']['denominator'])
    assert float(lower)==1.0 and lower==1-tiny


@pytest.mark.parametrize('samples,a,b',[( [],F(0),F(0)), ([(1,1,0)],0.,F(0)),
    ([(2,1,0)],F(0),F(0)), ([(1,1,True)],F(0),F(0))])
def test_interval_input_validation(samples,a,b):
    with pytest.raises(ValueError):affine_intercept_interval(samples,a,b)


def test_binary32_gap_with_rational_bounds_is_proved_empty():
    assert not binary32_interval_member(F(1)+F(1,2**26),F(1)+F(1,2**25))['exists']


def test_binary32_strict_upper_bound_excludes_next_value():
    assert not binary32_interval_member(F(1)+F(1,2**26),F(1)+F(1,2**23))['exists']


def test_binary32_inclusive_lower_bound_admits_exact_next_value():
    result=binary32_interval_member(F(1)+F(1,2**23),F(1)+F(1,2**22))
    assert result['exists'] and result['first_at_or_above_lower']['bits']=='3f800001'


@pytest.mark.parametrize('lower,upper,bits',[
    (F(-1),F(-1)+F(1,2**25),'bf800000'),
    (F(1,2**149),F(2,2**149),'00000001'),
    (F(-2,2**149),F(-1,2**149),'80000002'),
    (F(0),F(1,2**150),'80000000'),
])
def test_binary32_negative_subnormal_and_zero_ranges(lower,upper,bits):
    result=binary32_interval_member(lower,upper)
    assert result['exists'] and result['first_at_or_above_lower']['bits']==bits


def test_binary32_extreme_range_and_empty_interval():
    assert not binary32_interval_member(F(2**129),F(2**130))['exists']
    assert not binary32_interval_member(F(-2**130),F(-2**129))['exists']
    assert not binary32_interval_member(F(1),F(1))['exists']


def test_binary32_interval_rejects_inexact_bounds():
    with pytest.raises(ValueError):binary32_interval_member(0.,F(1))
