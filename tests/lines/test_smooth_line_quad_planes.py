"""Rounded rectangle orientation, exact axis corners and axial preservation."""
from dataclasses import replace
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_quad_planes import NORMALIZATIONS,CORNERS,GEOMETRIES,HYPOTHESES,coverage_quad,predict_quad_planes
from smooth_line_directed_axial import predict_axial_staged
sys.path.pop(0)
P=Probe('axis',(3072,3072),(12288,3072),832)


@pytest.mark.parametrize('normalization',NORMALIZATIONS)
@pytest.mark.parametrize('corner',CORNERS)
@pytest.mark.parametrize('geometry',GEOMETRIES)
def test_axis_rectangle_corners_are_exact_and_immutable(normalization,corner,geometry):
    quad,offset=coverage_quad(P,normalization,corner,geometry)
    ext,radius=(.125,1.625) if geometry=='inner' else (.625,2.125)
    expected=[[12-ext,12-radius],[48+ext,12-radius],[48+ext,12+radius],[12-ext,12+radius]]
    np.testing.assert_array_equal(quad,expected)
    assert quad.dtype==np.float32 and not quad.flags.writeable
    assert offset==(.5 if geometry=='inner' else 0)


@pytest.mark.parametrize('geometry',GEOMETRIES)
def test_reversing_direction_preserves_rectangle_with_rotated_vertex_order(geometry):
    forward,_=coverage_quad(P,'divide32','split32',geometry)
    reverse,_=coverage_quad(replace(P,start_units=P.end_units,end_units=P.start_units),'divide32','split32',geometry)
    np.testing.assert_array_equal(reverse,forward[[2,3,0,1]])


@pytest.mark.parametrize('geometry',GEOMETRIES)
def test_axial_delegate_is_held(geometry):
    hypothesis=('float64','split32',geometry,'float32','normal-dot','float64','none')
    np.testing.assert_array_equal(predict_quad_planes(P,hypothesis),predict_axial_staged(P))


@pytest.mark.parametrize('constant',('normal-dot','determinant'))
@pytest.mark.parametrize('precision',('float32','float64'))
def test_oblique_frame_domain(constant,precision):
    p=Probe('oblique',(5376,12543),(3072,3327),832)
    frame=predict_quad_planes(p,('divide32','split32','inner',precision,constant,'float64','none'))
    assert frame.shape==(64,64,4) and frame.dtype==np.uint8
    assert np.any((frame[:,:,3]>0)&(frame[:,:,3]<255))


def test_unregistered_geometry_refuses():
    with pytest.raises(ValueError,match='576 declared'):predict_quad_planes(P,('fit',))
