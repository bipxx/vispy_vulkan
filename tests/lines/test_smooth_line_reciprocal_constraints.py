"""Exact central-inversion identity and distinct-input controls; no frames."""
from dataclasses import replace
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_reciprocal_constraints import local_product_key
sys.path.pop(0)

PROBE=Probe('forward',(3072,3072),(12288,9984),256)


def test_reversal_plus_central_inversion_preserves_every_local_product():
    reverse=replace(PROBE,identity='reverse',start_units=PROBE.end_units,end_units=PROBE.start_units)
    expected=(9216,6912,256,-1474560,63406080,69304320)
    assert local_product_key(PROBE,29,24)==expected
    assert local_product_key(reverse,30,26)==expected


def test_width_length_and_signed_cross_are_not_erased():
    key=local_product_key(PROBE,29,24)
    assert local_product_key(replace(PROBE,width_units=832),29,24)!=key
    assert local_product_key(replace(PROBE,end_units=(12292,9987)),29,24)!=key
    assert local_product_key(PROBE,29,25)!=key


@pytest.mark.parametrize('x,y',((-1,0),(64,0),(True,0),(0,1.0)))
def test_non_training_pixels_refuse(x,y):
    with pytest.raises(ValueError): local_product_key(PROBE,x,y)
