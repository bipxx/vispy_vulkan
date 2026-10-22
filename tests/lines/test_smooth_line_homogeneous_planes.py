"""Homogeneous raw-C and unchanged axial contracts without oracle payloads."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_homogeneous_planes import HYPOTHESES,homogeneous_plane,predict_homogeneous_planes
from smooth_line_directed_axial import predict_axial_staged
sys.path.pop(0)


@pytest.mark.parametrize('normalization',('sqrt-recip','rsqrt'))
@pytest.mark.parametrize('rounding',('nearest','positive-infinity'))
def test_raw_constant_is_zero_on_an_exact_through_origin_line(normalization,rounding):
    a,b,c=homogeneous_plane(3,4,4,-3,0,normalization,rounding)
    assert c==0 and a>0 and b>0


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_axial_delegation_remains_exact(hypothesis):
    p=Probe('axis',(3072,3072),(12288,3072),832)
    np.testing.assert_array_equal(predict_homogeneous_planes(p,hypothesis),predict_axial_staged(p))


def test_unregistered_path_refuses():
    with pytest.raises(ValueError,match='forty-eight'):
        predict_homogeneous_planes(Probe('p',(3072,3072),(12288,9984),256),('fit',))
