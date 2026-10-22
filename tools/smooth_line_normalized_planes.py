# SPDX-License-Identifier: AGPL-3.0-only
"""Staged signed reciprocal products feeding absolute coverage planes; training only."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe, SIZE
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_directed_normalization import roundup32
    from .smooth_line_plane_setup import plane_constant, evaluate_plane
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe, SIZE
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_directed_normalization import roundup32
    from smooth_line_plane_setup import plane_constant, evaluate_plane
    from smooth_line_nibble_coverage import minor_code

HYPOTHESES=tuple(product(('sqrt-recip','rsqrt'),('split','fused'),
                        ('float32-split','float32-fused','float64'),
                        ('none','oriented-nextafter')))


def normalized_direction(dx,dy,arithmetic):
    dx,dy=np.float32(dx),np.float32(dy)
    squared=np.float32(np.float32(dx*dx)+np.float32(dy*dy))
    if not np.isfinite(squared) or squared<=0:
        raise ValueError('Finite nonzero training direction required')
    if arithmetic=='sqrt-recip':
        inverse=np.float32(1)/np.float32(np.sqrt(squared))
    elif arithmetic=='rsqrt':
        inverse=np.float32(np.float64(1)/np.sqrt(np.float64(squared)))
    else:
        raise ValueError('Declared reciprocal arithmetic required')
    return tuple(roundup32(np.float64(v)*np.float64(inverse)) for v in (dx,dy))


def predict_normalized_planes(probe,hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the twenty-four declared normalized-plane hypotheses are allowed')
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
    def coverage(a,b,x,y,offset):
        c=plane_constant(a,b,x,y,offset,setup)
        return evaluate_plane(a,b,c,xx,yy,evaluation)
    left=coverage(nx,ny,x0,y0,half)
    right=coverage(-nx,-ny,x0,y0,half)
    minor=np.minimum(left,right)
    if ties=='oriented-nextafter':
        code=minor_code(minor,left-right)
    else:
        nibble=np.clip(np.floor(minor*minor.dtype.type(16)),0,15).astype(np.int32)
        code=2*nibble+(nibble>>3)
    start=coverage(tx,ty,x0,y0,np.float32(.625))
    end=coverage(-tx,-ty,x1,y1,np.float32(.625))
    overlap=np.clip(np.minimum(start,end),0,1)
    factor=np.where(overlap>0,np.minimum(32,np.ceil(overlap.dtype.type(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
