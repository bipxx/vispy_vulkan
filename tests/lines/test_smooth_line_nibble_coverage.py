"""Coverage encoding, orientation and admission controls; no reference arrays."""
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_nibble_coverage import HYPOTHESES,minor_code,predict_nibble,predict_nibble_normal_caps
sys.path.pop(0)


def test_four_bit_expansion_has_sixteen_values_and_no_middle_code():
    coverage = (np.arange(16,dtype=np.float64)+.5)/16
    code = minor_code(coverage,np.ones(16))
    assert set(map(int,code)) == set(range(0,15,2)) | set(range(17,32,2))
    assert len(set(code)) == 16 and 16 not in code


@pytest.mark.parametrize('dtype',(np.float32,np.float64))
def test_directed_ties_and_saturation(dtype):
    cov = np.array([-.5,0,.5,.5,1,2],dtype=dtype)
    direction = np.array([1,1,-1,1,1,1],dtype=dtype)
    np.testing.assert_array_equal(minor_code(cov,direction),[0,0,17,14,31,31])


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
@pytest.mark.parametrize('predictor',(predict_nibble,predict_nibble_normal_caps))
def test_axial_path_remains_identical(hypothesis,predictor):
    for index in (0,65,256,768,1536,2304):
        probe = training_probes()[index]
        np.testing.assert_array_equal(predictor(probe,hypothesis),predict_axial_staged(probe))


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
@pytest.mark.parametrize('predictor',(predict_nibble,predict_nibble_normal_caps))
def test_transpose_and_reversal_preserve_oriented_geometry(hypothesis,predictor):
    probe = next(p for p in training_probes() if p.identity=='oblique-2-r0-w384-p000-000')
    transposed = replace(probe,start_units=probe.end_units[::-1],end_units=probe.start_units[::-1])
    np.testing.assert_array_equal(predictor(probe,hypothesis).transpose(1,0,2),
                                  predictor(transposed,hypothesis))


@pytest.mark.parametrize('hypothesis',(None,('float64','float32'),True))
def test_undeclared_arithmetic_refuses(hypothesis):
    with pytest.raises(ValueError,match='three declared'):
        predict_nibble(training_probes()[3072],hypothesis)
