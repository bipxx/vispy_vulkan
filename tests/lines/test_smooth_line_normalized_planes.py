"""Arithmetic boundary and domain controls without reference frames."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_normalized_planes import HYPOTHESES,normalized_direction,predict_normalized_planes
sys.path.pop(0)


@pytest.mark.parametrize('arithmetic',('sqrt-recip','rsqrt'))
def test_signed_product_stage_crosses_exact_four_fifths(arithmetic):
    forward=normalized_direction(36,27,arithmetic)
    reverse=normalized_direction(-36,-27,arithmetic)
    assert forward[0]==np.nextafter(np.float32(.8),np.float32(np.inf))
    assert reverse[0]==-np.float32(.8)


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_endpoint_rejection_before_arithmetic(hypothesis):
    with pytest.raises(ValueError,match='Nondegenerate'):
        predict_normalized_planes(Probe('zero',(3072,3072),(3072,3072),256),hypothesis)


@pytest.mark.parametrize('direction',((0,0),(np.inf,1)))
def test_invalid_direction_refuses(direction):
    with pytest.raises(ValueError,match='Finite nonzero'):
        normalized_direction(*direction,'sqrt-recip')


def test_unregistered_arithmetic_refuses():
    with pytest.raises(ValueError,match='twenty-four'):
        predict_normalized_planes(Probe('p',(3072,3072),(12288,9984),256),('fit',))
