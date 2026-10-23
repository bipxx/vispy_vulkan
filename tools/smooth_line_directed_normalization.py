# SPDX-License-Identifier: AGPL-3.0-only
"""Signed reciprocal-product rounding hypothesis; training only, no renderer path."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe,SIZE
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_nibble_coverage import minor_code
except ImportError:
    from smooth_line_mechanism import Probe,SIZE
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_nibble_coverage import minor_code

HYPOTHESES=tuple(product(('sqrt-recip','rsqrt'),('float32','float64')))

def roundup32(value):
    value=np.float64(value)
    rounded=np.float32(value)
    return np.nextafter(rounded,np.float32(np.inf)) if np.float64(rounded)<value else rounded

def predict_directed_normalization(probe, hypothesis):
    normal_caps=True
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the four declared directed-normalization hypotheses are allowed')
    if type(probe) is not Probe or any(type(v) is not int for v in
            (*probe.start_units, *probe.end_units, probe.width_units)):
        raise ValueError('Exact integer probe required')
    x0, y0 = probe.start_units
    x1, y1 = probe.end_units
    if (x0,y0) == (x1,y1) or not 256 <= probe.width_units <= 2048:
        raise ValueError('Nondegenerate training width required')
    if max(abs(v) for v in (x0,y0,x1,y1)) > 64*256:
        raise ValueError('Training-scale geometry required')
    if x0 == x1 or y0 == y1:
        return predict_axial_staged(probe)
    setup = np.float32
    evaluate = np.float64 if hypothesis[1] == 'float64' else np.float32
    horizontal = abs(x1-x0) >= abs(y1-y0)
    a0,b0,a1,b1 = (x0,y0,x1,y1) if horizontal else (y0,x0,y1,x1)
    # Both slopes are explicit: setup precision must not silently change the
    # rational centerline when only the normal coefficient precision changes.
    major_delta=setup(a1-a0)/setup(256)
    minor_delta=setup(b1-b0)/setup(256)
    squared=setup(setup(major_delta*major_delta)+setup(minor_delta*minor_delta))
    if hypothesis[0]=='sqrt-recip':
        inverse=setup(1)/setup(np.sqrt(squared))
    else:
        inverse=setup(np.float64(1)/np.sqrt(np.float64(squared)))
    gradient=abs(roundup32(np.float64(major_delta)*np.float64(inverse)))
    slope = evaluate(b1-b0)/evaluate(a1-a0)
    a0,b0,a1,b1 = (evaluate(v)/evaluate(256) for v in (a0,b0,a1,b1))
    major = np.arange(SIZE[0],dtype=evaluate)+evaluate(.5)
    minor = np.arange(SIZE[1],dtype=evaluate)+evaluate(.5)
    centerline = b0+(major-a0)*slope
    distance = (minor[:,None]-centerline[None,:])*evaluate(gradient)
    half = (evaluate(probe.width_units)/evaluate(256)+evaluate(1))/evaluate(2)
    coverage = half-np.abs(distance)
    sign = 1 if a1 > a0 else -1
    oriented_distance = distance*(sign if horizontal else -sign)
    code = minor_code(coverage,oriented_distance)
    if normal_caps:
        # Signed distances from both endpoint planes, positive inside the line.
        # The fixed .625 is a half-pixel footprint plus the retained 1/8 extension.
        along_start = ((major[None,:]-a0)+(minor[:,None]-b0)*slope)*evaluate(gradient)*sign
        along_end = ((a1-major[None,:])+(b1-minor[:,None])*slope)*evaluate(gradient)*sign
        overlap = np.clip(evaluate(.625)+np.minimum(along_start,along_end),evaluate(0),evaluate(1))
    else:
        # Preserve the prior staged cap rule; this is not a cap qualification.
        cap0,cap1 = a0-(minor-b0)*slope,a1-(minor-b1)*slope
        start,end = np.minimum(cap0,cap1)-evaluate(.125),np.maximum(cap0,cap1)+evaluate(.125)
        left = major-evaluate(.5)
        overlap = np.clip(np.minimum(end[:,None],left[None,:]+evaluate(1))-
                          np.maximum(start[:,None],left[None,:]),evaluate(0),evaluate(1))
    factor = np.where(overlap > 0,np.minimum(32,np.ceil(evaluate(32)*overlap)+1),0).astype(np.int32)
    combined = code*factor//32
    image = np.zeros((SIZE[1],SIZE[0],4),dtype=np.uint8)
    image[:,:,:3] = np.where(combined[:,:,None] > 0,255,0)
    image[:,:,3] = ((263*combined+16)//32).astype(np.uint8)
    return image if horizontal else image.transpose(1,0,2).copy()
