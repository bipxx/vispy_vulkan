# SPDX-License-Identifier: AGPL-3.0-only
"""Scientific inputs and criteria, checked without constructing a canvas."""
import numpy as np
import pytest
from tools.fixture_color_volume import CASES,METHODS,phantom,input_arrays,case_contract,assert_landmarks


def test_all_exposed_original_methods_have_both_color_forms():
    assert len(CASES)==len(set(CASES))==24
    assert all(f'{kind}_{method}' in CASES for kind in ('rgb','rgba') for method in METHODS)


@pytest.mark.parametrize('name',CASES)
def test_inputs_are_finite_distinct_float_channels_with_fixed_contract(name):
    arrays=input_arrays(name);spec=case_contract(name)
    assert spec['comparison']==dict(full_frame_exact=True,excluded_pixels=0)
    assert spec['cmap']=='grays' and spec['texture_format']=='auto'
    for data in arrays:
        assert data.shape[:3]==(32,32,32) and data.shape[3] in (3,4)
        assert data.dtype==np.float32 and np.all(np.isfinite(data))
        assert data.min()>=0 and data.max()<=1
        assert not np.array_equal(data[...,0],data[...,1])
        assert not np.array_equal(data[...,1],data[...,2])
    assert len(arrays)==(2 if name.endswith('_update') or '_to_' in name else 1)


def test_rgba_opaque_is_rgb_with_independent_alpha_and_low_alpha_keeps_rgb():
    rgb=input_arrays('rgb_mip')[0];opaque=input_arrays('rgba_mip_opaque')[0]
    low=input_arrays('rgba_mip_alpha_low')[0]
    np.testing.assert_array_equal(rgb,opaque[...,:3])
    np.testing.assert_array_equal(rgb,low[...,:3])
    assert np.all(opaque[...,3]==1) and np.all(low[...,3]==.125)


@pytest.mark.parametrize('name',['rgb_iso','rgba_iso'])
def test_iso_threshold_has_finite_color_and_opacity_crossing_before_capture(name):
    data=input_arrays(name)[0]
    alpha=data[...,3] if data.shape[-1]==4 else 1
    luminance=(data[...,:3]@np.array([.2126,.7152,.0722],np.float32))*alpha
    threshold=case_contract(name)['threshold']
    assert luminance.min()<threshold<luminance.max()


def test_plane_landmarks_from_source_camera_basis_and_pixel_centers():
    # Official PerspectiveCamera +z basis: right=cross(+y,+z)=+x.
    # Square96 viewport, ortho width40, center(15.5,15.5,15.5).
    right=np.cross([0,1,0],[0,0,1]);np.testing.assert_array_equal(right,[1,0,0])
    data=phantom(3)
    for px,color in [(32,[1,.125,.25]),(64,[.125,1,.5])]:
        for y in range(47,50):
            for x in range(px-1,px+2):
                wx=15.5+(x+.5-48)*40/96
                wz=15.5-(y+.5-48)*40/96
                xi,zi=int(np.floor(wx+.5)),int(np.floor(wz+.5))
                # Both centered Y plane samples are inside the ellipsoid.
                for yi in (15,16):np.testing.assert_array_equal(data[zi,yi,xi],color)


@pytest.mark.parametrize('name',['rgb_update','rgba_update','rgb_to_rgba','rgba_to_rgb'])
def test_public_data_mutations_preserve_spatial_shape_and_have_independent_content(name):
    first,second=input_arrays(name)
    assert first.shape[:3]==second.shape[:3]
    if name.endswith('_update'):
        np.testing.assert_array_equal(first[...,0],second[...,2])
        np.testing.assert_array_equal(first[...,2],second[...,0])
        assert not np.shares_memory(first,second)
    else:assert first.shape[-1]!=second.shape[-1]


def test_plane_landmarks_reject_channel_swap_blank_and_interior_change():
    image=np.zeros((96,96,4),np.uint8);image[...,3]=255
    image[47:50,31:34,:3]=[255,32,64];image[47:50,63:66,:3]=[32,255,128]
    assert_landmarks('rgb_plane',image)
    image[48,32,0]=0
    with pytest.raises(AssertionError):assert_landmarks('rgb_plane',image)
    with pytest.raises(AssertionError):assert_landmarks('rgb_mip',np.zeros_like(image))


@pytest.mark.parametrize('bad',[0,1,2,5,True])
def test_invalid_channel_counts_rejected(bad):
    with pytest.raises(ValueError):phantom(bad)
