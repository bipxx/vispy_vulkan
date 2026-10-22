# SPDX-License-Identifier: AGPL-3.0-only
"""Exact fixed-grid plane hypotheses with explicit geometric constants; training only."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe,SIZE
    from .smooth_line_fixed_precision import ROUNDINGS,quantized_sqrt_ratio
    from .smooth_line_directed_axial import predict_axial_staged
except ImportError:
    from smooth_line_mechanism import Probe,SIZE
    from smooth_line_fixed_precision import ROUNDINGS,quantized_sqrt_ratio
    from smooth_line_directed_axial import predict_axial_staged

HYPOTHESES=tuple(product(range(8,33),ROUNDINGS,('homogeneous','rounded-normal'),
                        ('none','oriented-boundary')))


def predict_fixed_planes(probe,hypothesis):
    if (type(hypothesis) is not tuple or len(hypothesis)!=4 or
            type(hypothesis[0]) is not int or hypothesis not in HYPOTHESES):
        raise ValueError('Only the400 declared fixed-plane hypotheses are allowed')
    if type(probe) is not Probe or any(type(v) is not int for v in
            (*probe.start_units,*probe.end_units,probe.width_units)):
        raise ValueError('Exact integer probe required')
    if (probe.start_units==probe.end_units or not 256<=probe.width_units<=2048 or
            max(abs(v) for v in (*probe.start_units,*probe.end_units))>64*256):
        raise ValueError('Nondegenerate training-scale geometry required')
    x0,y0=probe.start_units;x1,y1=probe.end_units
    if x0==x1 or y0==y1:return predict_axial_staged(probe)
    bits,rounding,constant,ties=hypothesis
    scale=1<<bits
    dx,dy=x1-x0,y1-y0
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]]
    xx,yy=2*xx+1,2*yy+1
    def plane(a,b,x,y):
        squared=a*a+b*b
        nx=int(quantized_sqrt_ratio(a,squared,bits,rounding)*scale)
        ny=int(quantized_sqrt_ratio(b,squared,bits,rounding)*scale)
        if constant=='homogeneous':
            c=quantized_sqrt_ratio(-a*x-b*y,squared*256**2,bits,rounding)
        else:
            c=quantized_sqrt_ratio(-nx*x-ny*y,(256*scale)**2,bits,rounding)
        ci=int(c*scale)
        # All products fit signed64 on the declared64px/32-fraction-bit domain.
        bound=127*(abs(nx)+abs(ny))+2*abs(ci)
        assert bound<(2**63-(probe.width_units+256)*scale)//256
        return nx*xx+ny*yy+2*ci
    left=plane(-dy,dx,x0,y0)
    right=plane(dy,-dx,x0,y0)
    minor=np.minimum(left,right)
    numerator=(probe.width_units+256)*scale+256*minor
    denominator=32*scale
    assert int(np.max(np.abs(numerator)))<2**63
    nibble=numerator//denominator
    if ties=='oriented-boundary':
        strict=(numerator+denominator-1)//denominator-1
        nibble=np.where(left-right>=0,strict,nibble)
    nibble=np.clip(nibble,0,15)
    code=2*nibble+(nibble>>3)
    along=np.minimum(plane(dx,dy,x0,y0),plane(-dx,-dy,x1,y1))
    overlap=np.clip(5*scale//4+along,0,2*scale)
    factor=np.where(overlap>0,np.minimum(32,(32*overlap+2*scale-1)//(2*scale)+1),0)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
