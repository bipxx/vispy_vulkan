# SPDX-License-Identifier: AGPL-3.0-only
"""Diagnostic finite-precision constant intervals; never a raster predictor."""
import numpy as np
try:
    from .smooth_line_slope_planes import fma32_exact
except ImportError:
    from smooth_line_slope_planes import fma32_exact

ORDERS = ('sum-then-constant', 'x-constant-first', 'y-constant-first',
          'fused-x-outer', 'fused-y-outer', 'float64')


def ordered_keys(values):
    values = np.asarray(values, np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError('Finite binary32 constants required')
    bits = values.view(np.uint32)
    return np.where(bits & np.uint32(0x80000000), ~bits, bits ^ np.uint32(0x80000000)).astype(np.uint64)


def decode_keys(keys):
    keys = np.asarray(keys, dtype=np.uint64)
    if np.any(keys < 0x00800000) or np.any(keys > 0xff7fffff):
        raise ValueError('Ordered finite binary32 keys required')
    bits = np.where(keys & np.uint64(0x80000000), keys ^ np.uint64(0x80000000),
                    ~keys & np.uint64(0xffffffff)).astype(np.uint32)
    return bits.view(np.float32)


def evaluate_plane(a, b, c, x, y, order, offset=0):
    """Fixed FP32 coefficients/constants; explicit rounding at every operation."""
    if order not in ORDERS:
        raise ValueError('Declared finite evaluation order required')
    a, b, c, x, y = (np.asarray(value, np.float32) for value in (a, b, c, x, y))
    if order == 'float64':
        value = a.astype(np.float64) * x.astype(np.float64) + b.astype(np.float64) * y.astype(np.float64) + c.astype(np.float64)
        return value + np.float64(offset)
    if order == 'sum-then-constant':
        value = np.float32(np.float32(np.float32(a * x) + np.float32(b * y)) + c)
    elif order == 'x-constant-first':
        value = np.float32(np.float32(np.float32(a * x) + c) + np.float32(b * y))
    elif order == 'y-constant-first':
        value = np.float32(np.float32(np.float32(b * y) + c) + np.float32(a * x))
    elif order == 'fused-x-outer':
        value = fma32_exact(a, x, fma32_exact(b, y, c))
    else:
        value = fma32_exact(b, y, fma32_exact(a, x, c))
    return np.float32(value + np.float32(offset))


def constant_interval(samples, a, b, order, *, offset=0, constant_bounds=(-512, 512)):
    """Intersect all saturated floor(16*evaluate(C)) constraints on binary32 C.

    Return ordered-key bounds only, without choosing/evaluating a common member
    as a model. The finite search domain is explicit. For the admitted groups,
    a non-saturated observation and |a|,|b|<=2 bound every possible C inside it.
    Signed zeros and subnormals participate in the ordered encoding search.
    """
    if order not in ORDERS:
        raise ValueError('Declared finite evaluation order required')
    if not samples:
        raise ValueError('At least one exact nibble observation required')
    for sample in samples:
        if (type(sample) not in (tuple, list) or len(sample) != 3 or any(type(v) is not int for v in sample)):
            raise ValueError('Exact doubled coordinates and nibble required')
        x, y, n = sample
        if not (1 <= x <= 127 and x % 2 and 1 <= y <= 127 and y % 2 and 0 <= n <= 15):
            raise ValueError('Odd in-frame doubled coordinates and nibble0..15 required')
    coefficients = np.asarray((a, b, offset), dtype=np.float64)
    if not np.all(np.isfinite(coefficients)) or max(abs(float(a)), abs(float(b))) > 2 or abs(float(offset)) > 8:
        raise ValueError('Bounded finite coefficients/offset required')
    if len(constant_bounds) != 2:
        raise ValueError('Two binary32 constant bounds required')
    low, high = (np.float32(value) for value in constant_bounds)
    if not np.isfinite(low) or not np.isfinite(high) or not -512 <= low <= high <= 512:
        raise ValueError('Ordered constant bounds inside[-512,512] required')
    first, last = int(ordered_keys(low)), int(ordered_keys(high))
    if first > last:
        raise ValueError('Ordered signed-zero bounds required')
    data = np.asarray(samples, dtype=np.int64)
    x, y = data[:, 0].astype(np.float32) / 2, data[:, 1].astype(np.float32) / 2
    n = data[:, 2]

    def first_at_least(threshold):
        lo = np.full(len(samples), first, dtype=np.uint64)
        hi = np.full(len(samples), last + 1, dtype=np.uint64)
        while np.any(lo < hi):
            mid = (lo + hi) // 2
            # The sentinel is the float immediately beyond the finite domain.
            values = evaluate_plane(a, b, decode_keys(mid), x, y, order, offset)
            scaled = values * values.dtype.type(16)
            reached = scaled >= threshold
            active = lo < hi
            hi = np.where(active & reached, mid, hi)
            lo = np.where(active & ~reached, mid + 1, lo)
        return lo

    lower = np.where(n > 0, first_at_least(n), np.uint64(first))
    upper = np.where(n < 15, first_at_least(n + 1), np.uint64(last + 1))
    lo, hi = int(lower.max()), int(upper.min())
    return dict(feasible=lo < hi, samples_checked=len(samples),
        lower_ordered_key=lo, upper_exclusive_ordered_key=hi,
        lower_witness=None if lo == first else list(samples[int(lower.argmax())]),
        upper_witness=None if hi == last + 1 else list(samples[int(upper.argmin())]),
        domain_first_ordered_key=first, domain_last_ordered_key=last,
        coefficient_a_bits=f'{int(np.float32(a).view(np.uint32)):08x}',
        coefficient_b_bits=f'{int(np.float32(b).view(np.uint32)):08x}',
        offset_bits=f'{int(np.float32(offset).view(np.uint32)):08x}',
        common_constant_selected_for_prediction=False)
