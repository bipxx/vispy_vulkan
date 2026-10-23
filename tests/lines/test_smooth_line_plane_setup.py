"""Arithmetic cancellation, admission and retained-axial controls; no oracle."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_plane_setup import HYPOTHESES,evaluate_plane,fma32,predict_planes
sys.path.pop(0)


def test_fused_rounding_retains_product_residue_after_cancellation():
    a,b,c=np.float32(1+2**-23),np.float32(1-2**-23),np.float32(-1)
    assert fma32(a,b,c)==np.float32(-2**-46)
    assert np.float32(np.float32(a*b)+c)==0


def test_plane_evaluation_paths_have_explicit_rounding_boundaries():
    a,b=np.float32(1+2**-23),np.float32(0)
    x,y,c=np.float32(1-2**-23),np.float32(0),np.float32(-1)
    assert evaluate_plane(a,b,c,x,y,'float32-split')==0
    assert evaluate_plane(a,b,c,x,y,'float32-fused')==np.float32(-2**-46)
    assert evaluate_plane(a,b,c,x,y,'float64')==-(2**-46)


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_all_plane_paths_preserve_axial_predictions(hypothesis):
    for index in (0,65,256,768,1536,2304):
        probe=training_probes()[index]
        np.testing.assert_array_equal(predict_planes(probe,hypothesis),predict_axial_staged(probe))


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_oblique_output_is_bounded_with_separate_generated_rgb(hypothesis):
    frame=predict_planes(training_probes()[3072],hypothesis)
    assert frame.shape==(64,64,4) and frame.dtype==np.uint8
    assert np.any((frame[:,:,3]>0)&(frame[:,:,3]<255))
    assert np.all(frame[frame[:,:,0]==0]==0)
    assert set(np.unique(frame[:,:,:3]))=={0,255}


@pytest.mark.parametrize('hypothesis',(None,('split','float16','none'),True))
def test_unknown_arithmetic_refuses(hypothesis):
    with pytest.raises(ValueError,match='twelve declared'):
        predict_planes(training_probes()[3072],hypothesis)
