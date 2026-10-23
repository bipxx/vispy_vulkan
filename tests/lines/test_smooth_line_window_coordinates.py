"""Translation identity retains phase, signed direction and local pixel position."""
from dataclasses import replace
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_window_coordinates import local_window_key
sys.path.pop(0)

P=Probe('p',(3072,3072),(12288,9984),832)


def test_integer_shift_preserves_all_local_inputs():
    shifted=replace(P,start_units=(4096,2048),end_units=(13312,8960))
    assert local_window_key(P,29,24)==local_window_key(shifted,33,20)


def test_key_retains_direction_width_and_local_position():
    key=local_window_key(P,29,24)
    assert local_window_key(replace(P,start_units=P.end_units,end_units=P.start_units),29,24)!=key
    assert local_window_key(replace(P,width_units=256),29,24)!=key
    assert local_window_key(P,30,24)!=key


@pytest.mark.parametrize('x,y',((True,0),(0,1.0),(-1,0),(64,0)))
def test_inexact_or_outside_pixels_refuse(x,y):
    with pytest.raises(ValueError):local_window_key(P,x,y)
