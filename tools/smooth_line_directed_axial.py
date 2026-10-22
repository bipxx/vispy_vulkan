"""Exploratory integer axial mechanism; not a selected model or renderer path.

Derived from the admitted training observations. Oblique/short/degenerate lines,
custom fragments and general state are deliberately not represented here.
"""
import numpy as np

try:
    from .smooth_line_mechanism import Probe, SIZE
except ImportError:
    from smooth_line_mechanism import Probe, SIZE


def snap_ramp_intercept(numerator, direction_bias):
    """Coordinates in 1/512 pixel; snap toward a pixel center on a 1/16 grid.

    The +/-1 perturbation is half the smallest training coordinate unit. It
    chooses directed equality cases without a floating epsilon or tolerance.
    """
    if type(numerator) is not int or type(direction_bias) is not int or direction_bias not in (-1, 1):
        raise ValueError('Exact integer intercept and directed perturbation required')
    value = numerator + direction_bias
    center = (value // 512) * 512 + 256
    delta = value - center
    step = abs(delta) // 32
    return center + (step if delta >= 0 else -step) * 32


def _axial_factors(probe):
    if type(probe) is not Probe or any(type(value) is not int for value in
            (*probe.start_units, *probe.end_units, probe.width_units)):
        raise ValueError('Exact integer probe required')
    x0, y0 = probe.start_units
    x1, y1 = probe.end_units
    if probe.width_units < 256 or (x0 == x1) == (y0 == y1):
        raise ValueError('Exploratory mechanism admits nondegenerate axial widths >=1 only')
    if any(abs(value) > 64 * 256 for value in (x0, y0, x1, y1)) or probe.width_units > 8 * 256:
        raise ValueError('Training-scale arithmetic domain exceeded')
    horizontal = y0 == y1
    minor = y0 if horizontal else x0
    major0, major1 = (x0, x1) if horizontal else (y0, y1)
    sign = 1 if major1 > major0 else -1
    bias = -sign if horizontal else sign
    upper = snap_ramp_intercept(2 * minor - (probe.width_units + 256), bias)
    lower = snap_ramp_intercept(2 * minor + (probe.width_units + 256), bias)
    minor_centers = np.arange(SIZE[1 if horizontal else 0], dtype=np.int64) * 512 + 256
    minor_coverage = np.clip(np.minimum(minor_centers - upper, lower - minor_centers), 0, 512)
    start, end = min(major0, major1) - 32, max(major0, major1) + 32
    major_left = np.arange(SIZE[0 if horizontal else 1], dtype=np.int64) * 256
    major_coverage = np.maximum(0, np.minimum(end, major_left + 256) - np.maximum(start, major_left))
    return horizontal, minor_coverage, major_coverage


def _image(coverage_code, horizontal, alpha):
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[:, :, :3] = np.where(coverage_code[:, :, None] > 0, 255, 0)
    image[:, :, 3] = alpha.astype(np.uint8)
    return image if horizontal else image.transpose(1, 0, 2).copy()


def predict_axial(probe):
    """Retained first, refused hypothesis; predictions are unchanged."""
    horizontal, minor_coverage, major_coverage = _axial_factors(probe)
    product = minor_coverage[:, None] * major_coverage[None, :]
    # One fixed candidate quantizer and fixed reciprocal expansion, no level table.
    coverage_code = (31 * product + 65536) // 131072
    alpha = ((8415 * coverage_code + 512) // 1024).astype(np.uint8)
    return _image(coverage_code, horizontal, alpha)


def predict_axial_staged(probe):
    """Second training-derived hypothesis: quantize factors before multiplication.

    Still CPU-only and unselected. The arithmetic encoding is a hypothesis,
    not a measured-level lookup or proof of the driver's internal precision.
    """
    horizontal, minor, major = _axial_factors(probe)
    minor_code = (31 * minor + 256) // 512
    major_factor = np.where(major > 0, np.minimum(32, (32 * major + 255) // 256 + 1), 0)
    coverage_code = (minor_code[:, None] * major_factor[None, :]) // 32
    alpha = (263 * coverage_code + 16) // 32
    return _image(coverage_code, horizontal, alpha)
