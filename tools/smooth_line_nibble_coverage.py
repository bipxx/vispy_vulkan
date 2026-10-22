# SPDX-License-Identifier: AGPL-3.0-only
"""Training-derived normal-distance/nibble hypothesis; no renderer integration.

The three declared arithmetic paths test coefficient and evaluation precision.
All use floor(16*coverage), saturate to four bits, then replicate the high bit
to expand four bits to five. Endpoint arithmetic is retained as a hypothesis.
"""
import numpy as np

try:
    from .smooth_line_mechanism import Probe, SIZE
    from .smooth_line_directed_axial import predict_axial_staged
except ImportError:
    from smooth_line_mechanism import Probe, SIZE
    from smooth_line_directed_axial import predict_axial_staged

HYPOTHESES = (('float64', 'float64'), ('float32', 'float64'), ('float32', 'float32'))


def minor_code(coverage, oriented_distance):
    """Directed one-ULP tie choice followed by a fixed nibble expansion."""
    target = np.where(oriented_distance < 0, np.inf, -np.inf).astype(coverage.dtype)
    directed = np.nextafter(coverage, target)
    nibble = np.clip(np.floor(directed*coverage.dtype.type(16)), 0, 15).astype(np.int32)
    return 2*nibble + (nibble >> 3)


def predict_nibble(probe, hypothesis):
    """Retained first family, including its refused major-axis cap rule."""
    return _predict(probe,hypothesis,False)


def predict_nibble_normal_caps(probe, hypothesis):
    """Second family: use normal longitudinal distance for cap coverage."""
    return _predict(probe,hypothesis,True)


def _predict(probe, hypothesis, normal_caps):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the three declared nibble arithmetic hypotheses are allowed')
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
    setup = np.float64 if hypothesis[0] == 'float64' else np.float32
    evaluate = np.float64 if hypothesis[1] == 'float64' else np.float32
    horizontal = abs(x1-x0) >= abs(y1-y0)
    a0,b0,a1,b1 = (x0,y0,x1,y1) if horizontal else (y0,x0,y1,x1)
    # Both slopes are explicit: setup precision must not silently change the
    # rational centerline when only the normal coefficient precision changes.
    setup_slope = setup(b1-b0)/setup(a1-a0)
    gradient = setup(1)/setup(np.sqrt(setup(1)+setup_slope*setup_slope))
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
