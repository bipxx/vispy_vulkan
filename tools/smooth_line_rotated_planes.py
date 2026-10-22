# SPDX-License-Identifier: AGPL-3.0-only
"""Rotate each unrounded plane normal before signed normalization; training only."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe,SIZE
    from .smooth_line_normalized_planes import normalized_direction,HYPOTHESES as PATHS
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_plane_setup import plane_constant,evaluate_plane
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe,SIZE
    from smooth_line_normalized_planes import normalized_direction,HYPOTHESES as PATHS
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_plane_setup import plane_constant,evaluate_plane
    from smooth_line_nibble_coverage import minor_code

HYPOTHESES=tuple(product(PATHS,('coverage-offset','distance-first')))


def predict_rotated_planes(probe,hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the forty-eight declared rotated-plane hypotheses are allowed')
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
    (normalization,setup,evaluation,ties),stage=hypothesis
    dx,dy=np.float32(x1-x0),np.float32(y1-y0)
    # Opposing and rotated normals are signed integer-direction inputs to
    # normalization. Negating already rounded coefficients is a different path.
    normals=[normalized_direction(a,b,normalization) for a,b in
             ((-dy,dx),(dy,-dx),(dx,dy),(-dx,-dy))]
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]]
    xx,yy=xx.astype(np.float32)+np.float32(.5),yy.astype(np.float32)+np.float32(.5)
    half=np.float32((np.float32(probe.width_units)/np.float32(256)+np.float32(1))/np.float32(2))
    def plane(normal,x,y,offset):
        a,b=normal
        c=plane_constant(a,b,x,y,offset,setup)
        return evaluate_plane(a,b,c,xx,yy,evaluation)
    side_offset=half if stage=='coverage-offset' else np.float32(0)
    left=plane(normals[0],x0,y0,side_offset)
    right=plane(normals[1],x0,y0,side_offset)
    minor=np.minimum(left,right)
    if stage=='distance-first':minor=minor.dtype.type(half)+minor
    if ties=='oriented-nextafter':
        code=minor_code(minor,left-right)
    else:
        nibble=np.clip(np.floor(minor*minor.dtype.type(16)),0,15).astype(np.int32)
        code=2*nibble+(nibble>>3)
    cap_offset=np.float32(.625) if stage=='coverage-offset' else np.float32(0)
    along=np.minimum(plane(normals[2],x0,y0,cap_offset),plane(normals[3],x1,y1,cap_offset))
    if stage=='distance-first':along=along.dtype.type(.625)+along
    overlap=np.clip(along,0,1)
    factor=np.where(overlap>0,np.minimum(32,np.ceil(overlap.dtype.type(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    image=np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3]=np.where(combined[:,:,None]>0,255,0)
    image[:,:,3]=((263*combined+16)//32).astype(np.uint8)
    return image
