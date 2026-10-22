# SPDX-License-Identifier: AGPL-3.0-only
"""Normalize an unrounded homogeneous plane rather than its rounded normal dot."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe,SIZE
    from .smooth_line_directed_normalization import roundup32
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_plane_setup import evaluate_plane
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe,SIZE
    from smooth_line_directed_normalization import roundup32
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_plane_setup import evaluate_plane
    from smooth_line_nibble_coverage import minor_code

HYPOTHESES=tuple(product(('sqrt-recip','rsqrt'),('nearest','positive-infinity'),
    ('float32-split','float32-fused','float64'),('none','oriented-nextafter'),
    ('coverage-offset','distance-first')))


def homogeneous_plane(a,b,x,y,offset,normalization,constant_rounding):
    a,b,x,y=(np.float32(v) for v in (a,b,x,y))
    squared=np.float32(np.float32(a*a)+np.float32(b*b))
    if not np.isfinite(squared) or squared<=0:
        raise ValueError('Finite nonzero training normal required')
    if normalization=='sqrt-recip':inverse=np.float32(1)/np.float32(np.sqrt(squared))
    elif normalization=='rsqrt':inverse=np.float32(np.float64(1)/np.sqrt(np.float64(squared)))
    else:raise ValueError('Declared reciprocal path required')
    raw_c=np.float32(-np.float64(a)*np.float64(x)-np.float64(b)*np.float64(y))
    value=np.float64(raw_c)*np.float64(inverse)+np.float64(offset)
    if constant_rounding=='nearest':c=np.float32(value)
    elif constant_rounding=='positive-infinity':c=roundup32(value)
    else:raise ValueError('Declared constant rounding required')
    return (roundup32(np.float64(a)*np.float64(inverse)),
            roundup32(np.float64(b)*np.float64(inverse)),c)


def predict_homogeneous_planes(probe,hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the forty-eight declared homogeneous-plane hypotheses are allowed')
    if type(probe) is not Probe or any(type(v) is not int for v in
            (*probe.start_units,*probe.end_units,probe.width_units)):
        raise ValueError('Exact integer probe required')
    if (probe.start_units==probe.end_units or not 256<=probe.width_units<=2048 or
            max(abs(v) for v in (*probe.start_units,*probe.end_units))>64*256):
        raise ValueError('Nondegenerate training-scale geometry required')
    x0,y0=(np.float32(v)/np.float32(256) for v in probe.start_units)
    x1,y1=(np.float32(v)/np.float32(256) for v in probe.end_units)
    if x0==x1 or y0==y1:return predict_axial_staged(probe)
    normalization,rounding,evaluation,ties,stage=hypothesis
    dx,dy=np.float32(x1-x0),np.float32(y1-y0)
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]]
    xx,yy=xx.astype(np.float32)+np.float32(.5),yy.astype(np.float32)+np.float32(.5)
    half=np.float32((probe.width_units/256+1)/2)
    def plane(a,b,x,y,offset):
        a,b,c=homogeneous_plane(a,b,x,y,offset,normalization,rounding)
        return evaluate_plane(a,b,c,xx,yy,evaluation)
    side_offset=half if stage=='coverage-offset' else np.float32(0)
    left=plane(-dy,dx,x0,y0,side_offset)
    right=plane(dy,-dx,x0,y0,side_offset)
    minor=np.minimum(left,right)
    if stage=='distance-first':minor=minor.dtype.type(half)+minor
    if ties=='oriented-nextafter':code=minor_code(minor,left-right)
    else:
        nibble=np.clip(np.floor(minor*minor.dtype.type(16)),0,15).astype(np.int32)
        code=2*nibble+(nibble>>3)
    offset=np.float32(.625) if stage=='coverage-offset' else np.float32(0)
    along=np.minimum(plane(dx,dy,x0,y0,offset),plane(-dx,-dy,x1,y1,offset))
    if stage=='distance-first':along=along.dtype.type(.625)+along
    overlap=np.clip(along,0,1)
    factor=np.where(overlap>0,np.minimum(32,np.ceil(overlap.dtype.type(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
