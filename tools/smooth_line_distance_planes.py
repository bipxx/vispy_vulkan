# SPDX-License-Identifier: AGPL-3.0-only
"""Zero-offset absolute distance planes with separately staged coverage; training only."""
import numpy as np
try:
    from .smooth_line_mechanism import Probe,SIZE
    from .smooth_line_normalized_planes import HYPOTHESES,normalized_direction
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_plane_setup import plane_constant,evaluate_plane
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe,SIZE
    from smooth_line_normalized_planes import HYPOTHESES,normalized_direction
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_plane_setup import plane_constant,evaluate_plane
    from smooth_line_nibble_coverage import minor_code


def predict_distance_planes(probe,hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the twenty-four declared distance-plane hypotheses are allowed')
    if type(probe) is not Probe or any(type(v) is not int for v in
            (*probe.start_units,*probe.end_units,probe.width_units)):
        raise ValueError('Exact integer probe required')
    if (probe.start_units==probe.end_units or not 256<=probe.width_units<=2048 or
            max(abs(v) for v in (*probe.start_units,*probe.end_units))>64*256):
        raise ValueError('Nondegenerate training-scale geometry required')
    x0,y0=(np.float32(v)/np.float32(256) for v in probe.start_units)
    x1,y1=(np.float32(v)/np.float32(256) for v in probe.end_units)
    if x0==x1 or y0==y1:
        return predict_axial_staged(probe)
    normalization,setup,evaluation,ties=hypothesis
    tx,ty=normalized_direction(np.float32(x1-x0),np.float32(y1-y0),normalization)
    nx,ny=-ty,tx
    half=np.float32((np.float32(probe.width_units)/np.float32(256)+np.float32(1))/np.float32(2))
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]]
    xx,yy=xx.astype(np.float32)+np.float32(.5),yy.astype(np.float32)+np.float32(.5)
    def distance(a,b,x,y):
        c=plane_constant(a,b,x,y,np.float32(0),setup)
        return evaluate_plane(a,b,c,xx,yy,evaluation)
    side=distance(nx,ny,x0,y0)
    minor=side.dtype.type(half)-np.abs(side)
    if ties=='oriented-nextafter':
        code=minor_code(minor,side)
    else:
        nibble=np.clip(np.floor(minor*minor.dtype.type(16)),0,15).astype(np.int32)
        code=2*nibble+(nibble>>3)
    along=np.minimum(distance(tx,ty,x0,y0),distance(-tx,-ty,x1,y1))
    overlap=np.clip(along.dtype.type(.625)+along,0,1)
    factor=np.where(overlap>0,np.minimum(32,np.ceil(overlap.dtype.type(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
