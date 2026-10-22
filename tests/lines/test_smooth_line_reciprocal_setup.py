"""Precision-path, domain and retained-axial controls without oracle files."""
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_reciprocal_setup import HYPOTHESES,predict_reciprocal,reciprocal_length
sys.path.pop(0)


@pytest.mark.parametrize('arithmetic',('float64','float32-sqrt-recip','float32-rsqrt'))
def test_reciprocal_uses_both_components_and_is_direction_independent(arithmetic):
    value=reciprocal_length(3,4,arithmetic)
    assert value==reciprocal_length(-3,-4,arithmetic)
    assert value==reciprocal_length(4,3,arithmetic)
    assert abs(float(value)-.2)<1e-8


def test_single_round_rsqrt_and_sqrt_then_reciprocal_are_distinct_paths():
    # A reproducible binary32 double-rounding case, independent of any frames.
    differences=[(a,b) for a in range(1,12) for b in range(1,12)
                 if reciprocal_length(a,b,'float32-rsqrt')!=reciprocal_length(a,b,'float32-sqrt-recip')]
    assert differences


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_all_paths_preserve_axial_predictions(hypothesis):
    for index in (0,256,1536):
        probe=training_probes()[index]
        np.testing.assert_array_equal(predict_reciprocal(probe,hypothesis),predict_axial_staged(probe))


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_oblique_frames_keep_white_rgb_and_independent_fractional_alpha(hypothesis):
    image=predict_reciprocal(training_probes()[3072],hypothesis)
    assert image.dtype==np.uint8 and image.shape==(64,64,4)
    assert set(np.unique(image[:,:,:3]))=={0,255}
    assert np.all(image[image[:,:,0]==0]==0)
    assert np.any((image[:,:,3]>0)&(image[:,:,3]<255))


@pytest.mark.parametrize('hypothesis',(None,('float64','float16','none'),True))
def test_undeclared_arithmetic_refuses(hypothesis):
    with pytest.raises(ValueError,match='twelve declared'):
        predict_reciprocal(training_probes()[3072],hypothesis)
