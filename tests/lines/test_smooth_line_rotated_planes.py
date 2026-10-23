"""Normal rotation does not commute with signed product rounding."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_normalized_planes import normalized_direction
from smooth_line_rotated_planes import HYPOTHESES,predict_rotated_planes
from smooth_line_directed_axial import predict_axial_staged
sys.path.pop(0)


@pytest.mark.parametrize('path',('sqrt-recip','rsqrt'))
def test_rotate_before_rounding_can_tilt_a_power_of_two_slope(path):
    tx,ty=normalized_direction(-9,-36,path)
    nx,ny=normalized_direction(36,-9,path)
    assert -float(ty)+4*float(tx)==0
    assert float(nx)+4*float(ny)>0


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_axial_delegation_remains_exact(hypothesis):
    p=Probe('axis',(3072,3072),(12288,3072),832)
    np.testing.assert_array_equal(predict_rotated_planes(p,hypothesis),predict_axial_staged(p))


def test_undeclared_path_refuses():
    with pytest.raises(ValueError,match='forty-eight'):
        predict_rotated_planes(Probe('p',(3072,3072),(12288,9984),256),('fit',))
