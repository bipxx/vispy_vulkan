"""Fixed-grid domain and held axial contracts at both precision extremes."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_fixed_planes import HYPOTHESES,predict_fixed_planes
from smooth_line_directed_axial import predict_axial_staged
sys.path.pop(0)


@pytest.mark.parametrize('bits',(8,32))
@pytest.mark.parametrize('constant',('homogeneous','rounded-normal'))
def test_axial_delegate_is_held_at_precision_extremes(bits,constant):
    p=Probe('axis',(3072,3072),(12288,3072),832)
    np.testing.assert_array_equal(predict_fixed_planes(p,(bits,'nearest-even',constant,'none')),predict_axial_staged(p))


@pytest.mark.parametrize('bits',(8,32))
@pytest.mark.parametrize('constant',('homogeneous','rounded-normal'))
def test_extreme_precision_frame_has_fractional_alpha_and_consistent_generation(bits,constant):
    p=Probe('oblique',(5376,12543),(3072,3327),832)
    frame=predict_fixed_planes(p,(bits,'positive-infinity',constant,'oriented-boundary'))
    assert frame.dtype==np.uint8 and frame.shape==(64,64,4)
    assert np.any((frame[:,:,3]>0)&(frame[:,:,3]<255))
    assert np.all(frame[frame[:,:,0]==0]==0)


@pytest.mark.parametrize('bits',(7,32.0))
def test_unregistered_precision_refuses(bits):
    with pytest.raises(ValueError,match='400 declared'):
        predict_fixed_planes(Probe('p',(3072,3072),(12288,9984),256),(bits,'zero','homogeneous','none'))
