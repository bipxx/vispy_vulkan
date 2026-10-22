"""A cancellation case must distinguish the two coordinate nesting orders."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_plane_order import ordered_constant,ordered_evaluation
sys.path.pop(0)


@pytest.mark.parametrize('path,expected',[
    ('sum-then-constant',1),('x-constant-first',1),('y-constant-first',0),
    ('fused-x-outer',0),('fused-y-outer',1),('float64',1)])
def test_coordinate_nesting_controls_cancellation(path,expected):
    f=np.float32
    assert ordered_evaluation(f(-2**24),f(1),f(2**24),f(1),f(1),path)==expected


def test_constant_setup_has_both_coordinate_nestings():
    f=np.float32
    assert ordered_constant(f(2**24),f(-1),f(1),f(1),f(2**24),'fused-x-outer')==0
    assert ordered_constant(f(2**24),f(-1),f(1),f(1),f(2**24),'fused-y-outer')==1


@pytest.mark.parametrize('operation',(ordered_constant,ordered_evaluation))
def test_undeclared_order_refuses(operation):
    with pytest.raises(ValueError,match='Declared'):operation(1,1,1,1,1,'fit')
