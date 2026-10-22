"""Finite exploratory oblique extensions of the exact axial training mechanism.

No renderer integration or model selection. All hypotheses are fixed before the
whole oblique comparison; a nonzero-error winner cannot be admitted.
"""
from itertools import product

import numpy as np

try:
    from .smooth_line_mechanism import Probe, SIZE
    from .smooth_line_directed_axial import predict_axial_staged
except ImportError:
    from smooth_line_mechanism import Probe, SIZE
    from smooth_line_directed_axial import predict_axial_staged

HYPOTHESES = tuple(product(('normal-space', 'major-space'), ('nearest31', 'floor32'), ('float64', 'float32')))


def _snap(values, bias, dtype):
    perturbed = np.nextafter(values, np.full_like(values, np.inf if bias > 0 else -np.inf))
    center = np.floor(perturbed) + dtype(.5)
    return center + np.trunc((perturbed-center)*dtype(16))/dtype(16)


def predict_oblique(probe, hypothesis):
    if type(hypothesis) is not tuple or hypothesis not in HYPOTHESES:
        raise ValueError('Only the eight declared oblique hypotheses are allowed')
    if type(probe) is not Probe or any(type(value) is not int for value in
            (*probe.start_units, *probe.end_units, probe.width_units)):
        raise ValueError('Exact integer probe required')
    x0, y0 = probe.start_units
    x1, y1 = probe.end_units
    if (x0, y0) == (x1, y1) or not 256 <= probe.width_units <= 2048:
        raise ValueError('Nondegenerate training-scale width >=1 required')
    if any(abs(value) > 64*256 for value in (x0, y0, x1, y1)):
        raise ValueError('Training-scale domain exceeded')
    if x0 == x1 or y0 == y1:
        return predict_axial_staged(probe)
    geometry, quantizer, precision = hypothesis
    dtype = np.float64 if precision == 'float64' else np.float32
    horizontal = abs(x1-x0) >= abs(y1-y0)
    a0, b0, a1, b1 = (x0, y0, x1, y1) if horizontal else (y0, x0, y1, x1)
    a0, b0, a1, b1 = (dtype(value)/dtype(256) for value in (a0, b0, a1, b1))
    slope = dtype((b1-b0)/(a1-a0))
    normal = dtype(np.sqrt(dtype(1)+slope*slope))
    major = np.arange(SIZE[0], dtype=dtype)+dtype(.5)
    minor = np.arange(SIZE[1], dtype=dtype)+dtype(.5)
    centerline = b0+(major-a0)*slope
    width = dtype(probe.width_units)/dtype(256)
    if geometry == 'normal-space':
        half_extent = (width+dtype(1))*normal/dtype(2)
        gradient = dtype(1)/normal
        cap_extension = dtype(.125)*normal
    else:
        half_extent = (width*normal+dtype(1))/dtype(2)
        gradient = dtype(1)
        cap_extension = dtype(.125)
    raw_upper, raw_lower = centerline-half_extent, centerline+half_extent
    sign = 1 if a1 > a0 else -1
    bias = -sign if horizontal else sign
    upper, lower = _snap(raw_upper, bias, dtype), _snap(raw_lower, bias, dtype)
    coverage = np.clip(np.minimum(minor[:, None]-upper[None, :], lower[None, :]-minor[:, None])*gradient,
                       dtype(0), dtype(1))
    raw_coverage = np.minimum(minor[:, None]-raw_upper[None, :], raw_lower[None, :]-minor[:, None])*gradient
    if quantizer == 'nearest31':
        minor_code = np.floor(dtype(31)*coverage+dtype(.5)).astype(np.int32)
    else:
        minor_code = np.minimum(31, np.floor(dtype(32)*coverage)).astype(np.int32)
    minor_code = np.where(raw_coverage >= dtype(1), 31, minor_code)
    # Perpendicular endpoint planes, evaluated at each minor pixel center.
    cap0, cap1 = a0-(minor-b0)*slope, a1-(minor-b1)*slope
    start, end = np.minimum(cap0, cap1)-cap_extension, np.maximum(cap0, cap1)+cap_extension
    left = major-dtype(.5)
    longitudinal = np.clip(np.minimum(end[:, None], left[None, :]+dtype(1))-
                           np.maximum(start[:, None], left[None, :]), dtype(0), dtype(1))
    factor = np.where(longitudinal > 0, np.minimum(32, np.ceil(dtype(32)*longitudinal)+1), 0).astype(np.int32)
    code = (minor_code*factor)//32
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[:, :, :3] = np.where(code[:, :, None] > 0, 255, 0)
    image[:, :, 3] = ((263*code+16)//32).astype(np.uint8)
    return image if horizontal else image.transpose(1, 0, 2).copy()
