"""CPU domain, orientation and retained-axial controls; no reference arrays."""
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_oblique_hypotheses import HYPOTHESES,predict_oblique
sys.path.pop(0)


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_each_extension_preserves_the_exact_axial_path(hypothesis):
    for index in (0,65,256,512,768,1536,2304):
        probe=training_probes()[index]
        np.testing.assert_array_equal(predict_oblique(probe,hypothesis),predict_axial_staged(probe))


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_oblique_transpose_with_reversed_endpoints_preserves_orientation(hypothesis):
    probe=next(p for p in training_probes() if p.identity=='oblique-2-r0-w384-p000-000')
    transposed=replace(probe,start_units=probe.end_units[::-1],end_units=probe.start_units[::-1])
    np.testing.assert_array_equal(predict_oblique(probe,hypothesis).transpose(1,0,2),predict_oblique(transposed,hypothesis))


@pytest.mark.parametrize('hypothesis',HYPOTHESES)
def test_output_is_bounded_rgba8_with_independent_generated_mask(hypothesis):
    probe=next(p for p in training_probes() if p.identity=='oblique-6-r0-w256-p000-000')
    frame=predict_oblique(probe,hypothesis)
    assert frame.dtype==np.uint8 and frame.shape==(64,64,4)
    assert set(np.unique(frame[:,:,:3]))=={0,255}
    assert np.all(frame[frame[:,:,0]==0]==0)
    assert np.any(frame[:,:,3])


@pytest.mark.parametrize('hypothesis',(None,('normal-space','nearest31','float16'),('unknown',),True))
def test_undeclared_hypothesis_refuses(hypothesis):
    with pytest.raises(ValueError,match='eight declared'):
        predict_oblique(training_probes()[3072],hypothesis)
