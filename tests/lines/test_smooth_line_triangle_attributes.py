# SPDX-License-Identifier: AGPL-3.0-only
"""Exact affine examples, attribute definitions and triangle transport controls."""
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_triangle_attributes import (SETUPS,DIAGONALS,HYPOTHESES,triangle_plane,
    triangle_partition,quad_attributes,predict_triangle_pixels,predict_triangle_attributes)
sys.path.pop(0)
P=Probe('oblique',(3072,4096),(12288,10240),832)


@pytest.mark.parametrize('setup',SETUPS)
@pytest.mark.parametrize('reverse',(False,True))
def test_exact_affine_attributes_reproduce_vertices_and_known_gradient(setup,reverse):
    v=np.array([[2,3],[6,3],[2,11]],np.float32)
    f=np.array([5,13,-19],np.float32) # 2*x-3*y+10
    if reverse:v,f=v[::-1],f[::-1]
    plane=triangle_plane(v,f,setup)
    np.testing.assert_array_equal(plane,[2,-3,10])
    np.testing.assert_array_equal(v@plane[:2]+plane[2],f)


@pytest.mark.parametrize('setup',SETUPS)
def test_partition_of_unity_preserves_constant_attributes(setup):
    v=np.array([[1.25,2.5],[5.75,3.25],[2.5,9.5]],np.float32)
    np.testing.assert_array_equal(triangle_plane(v,[2,2,2],setup),[0,0,2])


@pytest.mark.parametrize('setup',SETUPS)
def test_singular_and_nonfinite_triangles_refuse(setup):
    with pytest.raises(ValueError):triangle_plane([[0,0],[1,1],[2,2]],[0,1,2],setup)
    with pytest.raises(ValueError):triangle_plane([[0,0],[np.nan,1],[2,2]],[0,1,2],setup)


@pytest.mark.parametrize('diagonal',DIAGONALS)
def test_diagonal_partition_matches_independent_rational_orientation(diagonal):
    quad=np.array([[.25,.5],[8.25,.5],[8.5,8.75],[.5,8.5]],np.float32)
    x=np.array([.5,1.5,4.5,7.5]);y=np.array([7.5,1.5,4.5,1.5])
    first,second,chosen=triangle_partition(quad,diagonal,x,y)
    edge,inside=((0,2),1) if diagonal=='0-2' else ((1,3),0)
    q=[[Fraction(float(v)) for v in row] for row in quad]
    a,b=q[edge[0]],q[edge[1]]
    def cross(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
    sign=cross(q[inside]);expected=[cross((Fraction(float(X)),Fraction(float(Y))))*sign>=0 for X,Y in zip(x,y)]
    np.testing.assert_array_equal(chosen,expected)
    assert set(first)|set(second)=={0,1,2,3}


@pytest.mark.parametrize('diagonal',DIAGONALS)
def test_diagonal_boundary_uses_first_triangle(diagonal):
    quad=np.array([[0,0],[8,0],[8,8],[0,8]],np.float32)
    assert triangle_partition(quad,diagonal,4.5,4.5 if diagonal=='0-2' else 3.5)[2]


def test_extreme_dyadic_corner_does_not_lose_orientation_to_double_rounding():
    tiny=np.nextafter(np.float32(0),np.float32(1))
    quad=np.array([[0,tiny],[8,0],[8,8],[0,8]],np.float32)
    # The diagonal lies infinitesimally above (.5,.5), toward vertex1.
    assert triangle_partition(quad,'0-2',.5,.5)[2]


@pytest.mark.parametrize('geometry',('inner','support'))
def test_attribute_corners_have_declared_opposite_sums(geometry):
    attrs=quad_attributes(P,geometry)
    offset=.5 if geometry=='inner' else 0
    transverse=P.width_units/256+(0 if geometry=='inner' else 1)+2*offset
    length=np.sqrt(36**2+24**2)
    longitudinal=np.float32(length+(.25 if geometry=='inner' else 1.25)+2*offset)
    np.testing.assert_array_equal(attrs[:,0]+attrs[:,2],transverse)
    np.testing.assert_array_equal(attrs[:,1]+attrs[:,3],longitudinal)


@pytest.mark.parametrize('hypothesis',(HYPOTHESES[0],HYPOTHESES[-1]))
def test_full_frame_and_selected_pixel_transport_are_identical(hypothesis):
    pixels=((0,0),(12,16),(28,27),(48,40),(63,63))
    image=predict_triangle_attributes(P,hypothesis)
    np.testing.assert_array_equal(predict_triangle_pixels(P,hypothesis,pixels),[image[y,x] for x,y in pixels])
    assert image.shape==(64,64,4) and image.dtype==np.uint8
    assert np.any((image[:,:,3]>0)&(image[:,:,3]<255))


def test_axial_delegate_is_preserved():
    p=replace(P,end_units=(12288,4096))
    np.testing.assert_array_equal(predict_triangle_attributes(p,HYPOTHESES[0]),predict_axial_staged(p))


def test_family_and_input_domain_are_explicit():
    assert len(HYPOTHESES)==len(set(HYPOTHESES))==576
    with pytest.raises(ValueError):predict_triangle_pixels(P,('fit',),((0,0),))
    with pytest.raises(ValueError):predict_triangle_pixels(P,HYPOTHESES[0],((.5,0),))
    with pytest.raises(ValueError):predict_triangle_pixels(replace(P,end_units=(17000,4096)),HYPOTHESES[0],((0,0),))
    with pytest.raises(ValueError):triangle_partition(np.zeros((4,2),np.float32),'0-2',0,0)
