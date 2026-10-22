# SPDX-License-Identifier: AGPL-3.0-only
"""Rounded expanded-rectangle geometry before edge-plane setup; training only."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe,SIZE
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_plane_order import EVALUATION_PATHS,ordered_evaluation
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe,SIZE
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_plane_order import EVALUATION_PATHS,ordered_evaluation
    from smooth_line_nibble_coverage import minor_code

NORMALIZATIONS=('float64','divide32','reciprocal32')
CORNERS=('split32','float64-then32')
GEOMETRIES=('inner','support')
HYPOTHESES=tuple(product(NORMALIZATIONS,CORNERS,GEOMETRIES,('float32','float64'),
    ('normal-dot','determinant'),EVALUATION_PATHS,('none','oriented-nextafter')))


def _validate(probe):
    if type(probe) is not Probe or any(type(v) is not int for v in
            (*probe.start_units,*probe.end_units,probe.width_units)):
        raise ValueError('Exact integer probe required')
    if (probe.start_units==probe.end_units or not 256<=probe.width_units<=2048 or
            max(abs(v) for v in (*probe.start_units,*probe.end_units))>64*256):
        raise ValueError('Nondegenerate training-scale geometry required')


def coverage_quad(probe,normalization,corner,geometry):
    _validate(probe)
    if normalization not in NORMALIZATIONS or corner not in CORNERS or geometry not in GEOMETRIES:
        raise ValueError('Declared rounded-quad geometry required')
    p0=np.asarray(probe.start_units,dtype=np.float64)/256
    p1=np.asarray(probe.end_units,dtype=np.float64)/256
    delta=p1-p0
    if normalization=='float64':
        tangent=delta/np.sqrt(np.sum(delta*delta))
    else:
        d=delta.astype(np.float32)
        length=np.float32(np.sqrt(np.float32(np.float32(d[0]*d[0])+np.float32(d[1]*d[1]))))
        tangent=d/length if normalization=='divide32' else d*(np.float32(1)/length)
    normal=np.asarray([-tangent[1],tangent[0]])
    radius=probe.width_units/512+(0.5 if geometry=='support' else 0)
    extension=.625 if geometry=='support' else .125
    records=((p0,-1,-1),(p1,1,-1),(p1,1,1),(p0,-1,1))
    points=[]
    for point,along,side in records:
        if corner=='split32':
            longitudinal=np.asarray(along*extension*tangent,dtype=np.float32)
            transverse=np.asarray(side*radius*normal,dtype=np.float32)
            value=np.float32(np.float32(point.astype(np.float32)+longitudinal)+transverse)
        else:
            value=np.asarray(point+along*extension*tangent.astype(np.float64)+side*radius*normal.astype(np.float64),dtype=np.float32)
        points.append(value)
    quad=np.asarray(points,dtype=np.float32)
    quad.setflags(write=False)
    return quad,np.float32(0 if geometry=='support' else .5)


def predict_quad_planes(probe,hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the576 declared rounded-quad hypotheses are allowed')
    _validate(probe)
    if probe.start_units[0]==probe.end_units[0] or probe.start_units[1]==probe.end_units[1]:
        return predict_axial_staged(probe)
    normalization,corner,geometry,precision,constant,evaluation,ties=hypothesis
    quad,offset=coverage_quad(probe,normalization,corner,geometry)
    dtype=np.float32 if precision=='float32' else np.float64
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]]
    xx,yy=xx.astype(np.float32)+np.float32(.5),yy.astype(np.float32)+np.float32(.5)
    values=[]
    for index in range(4):
        x,y=(dtype(v) for v in quad[index])
        u,v=(dtype(w) for w in quad[(index+1)%4])
        dx,dy=dtype(u-x),dtype(v-y)
        length=dtype(np.sqrt(dtype(dtype(dx*dx)+dtype(dy*dy))))
        if not np.isfinite(length) or length<=0:raise ValueError('Nondegenerate rounded edge required')
        a,b=dtype(-dy/length),dtype(dx/length)
        if constant=='normal-dot':
            c=dtype(dtype(offset)-dtype(dtype(a*x)+dtype(b*y)))
        else:
            raw=dtype(dtype(x*v)-dtype(y*u))
            c=dtype(dtype(offset)+dtype(raw/length))
        if evaluation!='float64':a,b,c=np.float32(a),np.float32(b),np.float32(c)
        values.append(ordered_evaluation(a,b,c,xx,yy,evaluation))
    left,end,right,start=values
    minor=np.minimum(left,right)
    if ties=='oriented-nextafter':code=minor_code(minor,left-right)
    else:
        nibble=np.clip(np.floor(minor*minor.dtype.type(16)),0,15).astype(np.int32)
        code=2*nibble+(nibble>>3)
    overlap=np.clip(np.minimum(start,end),0,1)
    factor=np.where(overlap>0,np.minimum(32,np.ceil(overlap.dtype.type(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
