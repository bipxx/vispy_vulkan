"""Signed rounding and retained axial controls, without oracle arrays."""
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_signed_plane_setup import HYPOTHESES,round_normal,predict_signed_planes
sys.path.pop(0)


@pytest.mark.parametrize('value',(.6,-.6,.8,-.8))
def test_directed_rounding_brackets_the_input(value):
    lower,upper=round_normal(value,'negative-infinity'),round_normal(value,'positive-infinity')
    assert np.float64(lower)<=value<=np.float64(upper)
    assert np.nextafter(lower,np.float32(np.inf))==upper
    zero=round_normal(value,'zero')
    assert zero==(lower if value>0 else upper)


def test_signed_rounding_is_not_magnitude_symmetric():
    assert round_normal(-.6,'negative-infinity')!=-round_normal(.6,'negative-infinity')
    assert round_normal(-.6,'zero')==-round_normal(.6,'zero')


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_all_paths_preserve_axial_predictions(hypothesis):
    probe=training_probes()[65]
    np.testing.assert_array_equal(predict_signed_planes(probe,hypothesis),predict_axial_staged(probe))


@pytest.mark.parametrize('hypothesis',(None,True,(('split','float32-split','none'),'unknown')))
def test_unknown_model_refuses(hypothesis):
    with pytest.raises(ValueError,match='forty-eight'):
        predict_signed_planes(training_probes()[3072],hypothesis)
