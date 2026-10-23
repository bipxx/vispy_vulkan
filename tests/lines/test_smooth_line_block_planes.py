"""Block coordinate boundaries, immutable sharing and held axial behavior."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_block_planes import TILE_SIZES,PATHS,block_coordinates,predict_block_planes
from smooth_line_directed_axial import predict_axial_staged
sys.path.pop(0)


def test_block_boundary_moves_the_anchor_and_resets_relative_coordinates():
    ox,oy,x,y=block_coordinates(4)
    assert (ox[3,3],oy[3,3],x[3,3],y[3,3])==(.5,.5,3,3)
    assert (ox[4,4],oy[4,4],x[4,4],y[4,4])==(4.5,4.5,0,0)


@pytest.mark.parametrize('size',TILE_SIZES)
def test_anchor_and_relative_coordinate_exactly_recover_pixel_center(size):
    ox,oy,x,y=block_coordinates(size)
    yy,xx=np.mgrid[:64,:64]
    np.testing.assert_array_equal(ox+x,xx+.5)
    np.testing.assert_array_equal(oy+y,yy+.5)
    assert all(a.dtype==np.float32 and not a.flags.writeable for a in (ox,oy,x,y))


def test_single_pixel_control_has_zero_local_coordinate_everywhere():
    _,_,x,y=block_coordinates(1)
    assert not np.any(x) and not np.any(y)


@pytest.mark.parametrize('size',(0,3,True,2.0))
def test_unregistered_block_size_refuses(size):
    with pytest.raises(ValueError):block_coordinates(size)


@pytest.mark.parametrize('size',TILE_SIZES)
def test_axial_path_is_held(size):
    p=Probe('axis',(3072,3072),(12288,3072),832)
    np.testing.assert_array_equal(predict_block_planes(p,(size,PATHS[0])),predict_axial_staged(p))
