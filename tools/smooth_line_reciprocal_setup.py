# SPDX-License-Identifier: AGPL-3.0-only
"""Fixed shared reciprocal-length hypotheses for saved training comparison only."""
from itertools import product
import numpy as np

try:
    from .smooth_line_mechanism import Probe, SIZE
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe, SIZE
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_nibble_coverage import minor_code

HYPOTHESES=tuple(product(('float64','float32-sqrt-recip','float32-rsqrt'),
                         ('float64','float32'),('none','oriented-nextafter')))


def reciprocal_length(dx,dy,arithmetic):
    if arithmetic=='float64':
        return np.float64(1)/np.sqrt(np.float64(dx)*np.float64(dx)+np.float64(dy)*np.float64(dy))
    dx,dy=np.float32(dx),np.float32(dy)
    squared=np.float32(np.float32(dx*dx)+np.float32(dy*dy))
    if arithmetic=='float32-sqrt-recip':
        return np.float32(1)/np.float32(np.sqrt(squared))
    if arithmetic=='float32-rsqrt':
        # One binary32 rounding of reciprocal sqrt of the binary32 squared norm.
        # This does not assume a particular GPU approximate-rsqrt instruction.
        return np.float32(np.float64(1)/np.sqrt(np.float64(squared)))
    raise ValueError('Declared reciprocal arithmetic required')


def predict_reciprocal(probe,hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the twelve declared reciprocal hypotheses are allowed')
    if type(probe) is not Probe or any(type(v) is not int for v in
            (*probe.start_units,*probe.end_units,probe.width_units)):
        raise ValueError('Exact integer probe required')
    x0,y0=probe.start_units
    x1,y1=probe.end_units
    if ((x0,y0)==(x1,y1) or not 256<=probe.width_units<=2048 or
            max(abs(v) for v in (x0,y0,x1,y1))>64*256):
        raise ValueError('Nondegenerate training-scale geometry required')
    if x0==x1 or y0==y1:
        return predict_axial_staged(probe)
    normal,evaluation,ties=hypothesis
    dtype=np.float64 if evaluation=='float64' else np.float32
    # All input positions/deltas are exact binary fractions in this domain.
    x0,y0,x1,y1=(dtype(v)/dtype(256) for v in (x0,y0,x1,y1))
    dx,dy=dtype(x1-x0),dtype(y1-y0)
    inverse=dtype(reciprocal_length(dx,dy,normal))
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]]
    xx,yy=xx.astype(dtype)+dtype(.5),yy.astype(dtype)+dtype(.5)
    # Normalize the exact edge/dot expressions once, rather than normalizing a
    # slope and subtracting a separately interpolated centerline.
    cross=(yy-y0)*dx-(xx-x0)*dy
    distance=cross*inverse
    half=(dtype(probe.width_units)/dtype(256)+dtype(1))/dtype(2)
    coverage=half-np.abs(distance)
    if ties=='oriented-nextafter':
        code=minor_code(coverage,cross)
    else:
        nibble=np.clip(np.floor(dtype(16)*coverage),0,15).astype(np.int32)
        code=2*nibble+(nibble>>3)
    start=((xx-x0)*dx+(yy-y0)*dy)*inverse
    end=((x1-xx)*dx+(y1-yy)*dy)*inverse
    overlap=np.clip(dtype(.625)+np.minimum(start,end),dtype(0),dtype(1))
    factor=np.where(overlap>0,np.minimum(32,np.ceil(dtype(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
