# SPDX-License-Identifier: AGPL-3.0-only
"""Preregistered global slope/intercept then normalization hypotheses; no renderer."""
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

SLOPES = ('divide32', 'reciprocal32', 'float64')
CONSTANTS = ('split32', 'fused32', 'float64-then32', 'float64')
EVALUATIONS = ('center-split32', 'center-fused32', 'residual-split32', 'residual-fused32', 'float64')
NORMALIZATIONS = ('sqrt32-reciprocal', 'fused-sqrt32-reciprocal', 'sqrt64-reciprocal-then32', 'float64')
COVERAGES = ('split32', 'fused32', 'float64')
CAPS = ('relative', 'global')
TIES = ('none', 'oriented-nextafter')
MASKS = ('quantized-alpha', 'positive-geometry')
HYPOTHESES = tuple(product(SLOPES, CONSTANTS, EVALUATIONS, NORMALIZATIONS, COVERAGES, CAPS, TIES, MASKS))
_HYPOTHESIS_SET = frozenset(HYPOTHESES)


def fma32_exact(a, b, c):
    """Finite binary32 FMA, retaining a below-binary64 midpoint perturbation.

    The binary32 product is exact in binary64. TwoSum recovers addition error;
    only a binary64 sum landing exactly on a binary32 midpoint needs correction.
    Overflow/NaN behavior is outside this bounded training helper's domain.
    """
    a, b, c = np.asarray(a, np.float32), np.asarray(b, np.float32), np.asarray(c, np.float32)
    if not all(np.all(np.isfinite(value)) for value in (a, b, c)):
        raise ValueError('Finite binary32 FMA operands required')
    p, c64 = a.astype(np.float64) * b.astype(np.float64), c.astype(np.float64)
    total = p + c64
    z = total - p
    error = (p - (total - z)) + (c64 - z)
    rounded = total.astype(np.float32)
    if not np.all(np.isfinite(rounded)):
        raise ValueError('Finite binary32 FMA result required')
    r64 = rounded.astype(np.float64)
    target = np.where(r64 < total, np.inf, -np.inf).astype(np.float32)
    neighbor = np.nextafter(rounded, target)
    midpoint = (r64 + neighbor.astype(np.float64)) * .5
    lower, upper = np.minimum(rounded, neighbor), np.maximum(rounded, neighbor)
    corrected = np.where(error > 0, upper, lower)
    return np.asarray(np.where((total == midpoint) & (error != 0), corrected, rounded), dtype=np.float32)


def intercept(m, x, y, path):
    if path == 'split32':
        return np.float32(np.float32(y) - np.float32(np.float32(m) * np.float32(x)))
    if path == 'fused32':
        return fma32_exact(-np.float32(m), np.float32(x), np.float32(y))
    value = np.float64(y) - np.float64(m) * np.float64(x)
    if path == 'float64-then32':
        return np.float32(value)
    if path == 'float64':
        return value
    raise ValueError('Declared intercept path required')


def residual(m, c, x, y, path):
    if path == 'float64':
        return np.float64(y) - (np.float64(m) * np.float64(x) + np.float64(c))
    m, c, x, y = (np.asarray(value, np.float32) for value in (m, c, x, y))
    if path == 'center-split32':
        return np.float32(y - np.float32(np.float32(m * x) + c))
    if path == 'center-fused32':
        return np.float32(y - fma32_exact(m, x, c))
    if path == 'residual-split32':
        return np.float32(np.float32(y - c) - np.float32(m * x))
    if path == 'residual-fused32':
        return fma32_exact(-m, x, np.float32(y - c))
    raise ValueError('Declared residual path required')


def gradient(m, path):
    m32 = np.float32(m)
    if path in ('sqrt32-reciprocal', 'fused-sqrt32-reciprocal'):
        squared = (np.float32(np.float32(m32 * m32) + np.float32(1)) if path == 'sqrt32-reciprocal'
                   else fma32_exact(m32, m32, np.float32(1)))
        return np.float32(np.float32(1) / np.float32(np.sqrt(squared)))
    value = np.float64(1) / np.sqrt(np.float64(1) + np.float64(m) * np.float64(m))
    if path == 'sqrt64-reciprocal-then32':
        return np.float32(value)
    if path == 'float64':
        return value
    raise ValueError('Declared normalization path required')


def normalized_offset(value, scale, offset, path):
    if path == 'float64':
        return np.float64(offset) + np.float64(value) * np.float64(scale)
    if path == 'split32':
        return np.float32(np.float32(offset) + np.float32(np.float32(value) * np.float32(scale)))
    if path == 'fused32':
        return fma32_exact(np.float32(value), np.float32(scale), np.float32(offset))
    raise ValueError('Declared coverage path required')


def predict_slope_pixels(probe, hypothesis, pixels):
    try:
        registered = type(hypothesis) is tuple and hypothesis in _HYPOTHESIS_SET
    except TypeError:
        registered = False
    if not registered:
        raise ValueError('Only the5760 declared slope/intercept hypotheses are allowed')
    if type(probe) is not Probe or any(type(v) is not int for v in (*probe.start_units, *probe.end_units, probe.width_units)):
        raise ValueError('Exact integer probe required')
    if (probe.start_units == probe.end_units or not 256 <= probe.width_units <= 2048 or
            max(abs(v) for v in (*probe.start_units, *probe.end_units)) > 64 * 256):
        raise ValueError('Nondegenerate training-scale geometry required')
    pixels = tuple(pixels)
    if any(type(p) is not tuple or len(p) != 2 or any(type(v) is not int for v in p) or
           not 0 <= p[0] < SIZE[0] or not 0 <= p[1] < SIZE[1] for p in pixels):
        raise ValueError('Integer in-frame pixel coordinates required')
    if not pixels:
        return np.empty((0, 4), dtype=np.uint8)
    x0, y0 = probe.start_units
    x1, y1 = probe.end_units
    if x0 == x1 or y0 == y1:
        image = predict_axial_staged(probe)
        return np.asarray([image[y, x] for x, y in pixels], dtype=np.uint8)
    slope_path, constant_path, evaluation, normalization, coverage_path, caps, ties, mask = hypothesis
    horizontal = abs(x1 - x0) >= abs(y1 - y0)
    a0, b0, a1, b1 = (x0, y0, x1, y1) if horizontal else (y0, x0, y1, x1)
    da, db = a1 - a0, b1 - b0
    if slope_path == 'float64':
        m = np.float64(db) / np.float64(da)
    elif slope_path == 'divide32':
        m = np.float32(np.float32(db) / np.float32(da))
    else:
        m = np.float32(np.float32(db) * np.float32(np.float32(1) / np.float32(da)))
    a0, b0, a1, b1 = (np.float64(v) / 256 for v in (a0, b0, a1, b1))
    xy = np.asarray(pixels, dtype=np.float64) + .5
    major, minor = (xy[:, 0], xy[:, 1]) if horizontal else (xy[:, 1], xy[:, 0])
    c = intercept(m, a0, b0, constant_path)
    signed = residual(m, c, major, minor, evaluation)
    g = gradient(m, normalization)
    half = probe.width_units / 512 + .5
    side = normalized_offset(-np.abs(signed), g, half, coverage_path)
    direction = 1 if da > 0 else -1
    oriented = signed * (direction if horizontal else -direction)
    if ties == 'oriented-nextafter':
        code = minor_code(side, oriented)
    else:
        nibble = np.clip(np.floor(side * side.dtype.type(16)), 0, 15).astype(np.int32)
        code = 2 * nibble + (nibble >> 3)
    if caps == 'relative':
        start = residual(-m, 0, minor - b0, major - a0, evaluation)
        end = residual(-m, 0, b1 - minor, a1 - major, evaluation)
    else:
        c0 = intercept(m, b0, -a0, constant_path)
        c1 = intercept(m, b1, -a1, constant_path)
        start = residual(-m, -c0, minor, major, evaluation)
        end = -residual(-m, -c1, minor, major, evaluation)
    along_start = normalized_offset(direction * start, g, .625, coverage_path)
    along_end = normalized_offset(direction * end, g, .625, coverage_path)
    overlap = np.clip(np.minimum(along_start, along_end), 0, 1)
    factor = np.where(overlap > 0, np.minimum(32, np.ceil(overlap.dtype.type(32) * overlap) + 1), 0).astype(np.int32)
    combined = code * factor // 32
    generated = combined > 0 if mask == 'quantized-alpha' else (side > 0) & (overlap > 0)
    result = np.zeros((len(pixels), 4), dtype=np.uint8)
    result[:, :3] = np.where(generated[:, None], 255, 0)
    result[:, 3] = ((263 * combined + 16) // 32).astype(np.uint8)
    return result


def predict_slope_planes(probe, hypothesis):
    pixels = tuple((x, y) for y in range(SIZE[1]) for x in range(SIZE[0]))
    return predict_slope_pixels(probe, hypothesis, pixels).reshape(SIZE[1], SIZE[0], 4)
