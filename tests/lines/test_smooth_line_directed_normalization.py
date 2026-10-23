"""Directed product rounding and retained-domain controls, without reference data."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_directed_normalization import HYPOTHESES,roundup32,predict_directed_normalization
sys.path.pop(0)


def test_rounding_after_rounded_reciprocal_preserves_signed_stage_difference():
    inverse=np.float32(1)/np.float32(45)
    forward=roundup32(np.float64(36)*np.float64(inverse))
    backward=roundup32(np.float64(-36)*np.float64(inverse))
    nearest=np.float32(.8)
    assert forward==np.nextafter(nearest,np.float32(np.inf))
    assert backward==-nearest


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_axial_path_is_held(hypothesis):
    for index in (0,65,256,1536):
        probe=training_probes()[index]
        np.testing.assert_array_equal(predict_directed_normalization(probe,hypothesis),predict_axial_staged(probe))


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_rgba_domain_and_generation_mask(hypothesis):
    frame=predict_directed_normalization(training_probes()[4064],hypothesis)
    assert frame.dtype==np.uint8 and frame.shape==(64,64,4)
    assert np.any((frame[:,:,3]>0)&(frame[:,:,3]<255))
    assert np.all(frame[frame[:,:,0]==0]==0)


@pytest.mark.parametrize('hypothesis',(None,True,('unknown','float32')))
def test_unregistered_arithmetic_refuses(hypothesis):
    with pytest.raises(ValueError,match='four declared'):
        predict_directed_normalization(training_probes()[4064],hypothesis)
