# SPDX-License-Identifier: AGPL-3.0-only
"""Exact geometric invariants and affine-ramp constraints for training analysis.

These diagnostics neither predict coverage nor select a renderer mechanism.
"""
from itertools import combinations
from math import gcd

import numpy as np


def _geometry(row):
    if type(row) is not dict:
        raise ValueError('Exact integer geometry required')
    for name in ('start_units', 'end_units'):
        values = row.get(name)
        if type(values) not in (list, tuple) or len(values) != 2 or any(type(v) is not int for v in values):
            raise ValueError('Exact integer geometry required')
    if type(row.get('width_units')) is not int or row['width_units'] <= 0:
        raise ValueError('Positive exact integer width required')
    x, y = row['start_units']
    dx, dy = (b-a for a, b in zip(row['start_units'], row['end_units']))
    if dx == dy == 0:
        raise ValueError('Nondegenerate geometry required')
    if max(abs(v) for v in (*row['start_units'], *row['end_units'])) > 64*256:
        raise ValueError('Training-scale geometry required')
    return x, y, dx, dy


def directed_infinite_line(row):
    """Primitive integer normal and intercept; preserve orientation and width."""
    x, y, dx, dy = _geometry(row)
    divisor = gcd(dx, dy)
    a, b = dy//divisor, -dx//divisor
    return a, b, -a*x-b*y, row['width_units']


def translation_pairs(rows):
    groups = {}
    for index, row in enumerate(rows):
        groups.setdefault(directed_infinite_line(row), []).append(index)
    return tuple(pair for group in groups.values() for pair in combinations(group, 2))


def central_pixels(row):
    """Exact central-half projection test, independent of coverage observations."""
    x, y, dx, dy = _geometry(row)
    yy, xx = np.mgrid[:64, :64]
    dot = (xx*256+128-x)*dx + (yy*256+128-y)*dy
    square = dx*dx+dy*dy
    return (4*dot > square) & (4*dot < 3*square)


def minor_distance_numerators(row):
    """Unnormalized minor distance on a fixed integer scale per direction."""
    x, y, dx, dy = _geometry(row)
    yy, xx = np.mgrid[:64, :64]
    xx, yy = xx*256+128-x, yy*256+128-y
    if abs(dx) >= abs(dy):
        return yy*abs(dx)-xx*dy*(1 if dx > 0 else -1)
    return xx*abs(dy)-yy*dx*(1 if dy > 0 else -1)


def decode_alpha(alpha):
    """Invert the arithmetic training encoder; reject values outside its image."""
    if not isinstance(alpha, np.ndarray) or alpha.dtype != np.uint8:
        raise ValueError('RGBA8 alpha required')
    code = (alpha.astype(np.int32)*32+131)//263
    if np.any((263*code+16)//32 != alpha):
        raise ValueError('Alpha is outside the declared arithmetic encoding')
    return code


def affine_ramp_constraint(samples):
    """Can code=nearest(a*u+b), a>=0, explain all unsaturated samples?

    Samples are integer (u, code) pairs with 0<code<31. The code interval is
    [k-.5,k+.5). Every pair yields strict rational bounds on 2*a. Comparing
    integer cross-products avoids floating tolerances. A refusal retains the
    two bound witnesses or the conflicting duplicate coordinate.
    """
    values = {}
    count = 0
    for sample in samples:
        if type(sample) not in (list, tuple) or len(sample) != 2:
            raise ValueError('Integer coordinate/code pairs required')
        u, k = sample
        if type(u) is not int or type(k) is not int or not 0 < k < 31:
            raise ValueError('Unsaturated integer code required')
        count += 1
        if u in values and values[u] != k:
            return dict(feasible=False, reason='conflicting-code-at-identical-distance',
                        witness=[[u, values[u]], [u, k]], samples_seen=count)
        values[u] = k
    points = sorted(values.items())
    if len(points) < 2:
        return dict(feasible=True, informative=False, unique_distances=len(points), samples_seen=count)
    lower, upper = None, None
    for index, (ui, ki) in enumerate(points):
        for uj, kj in points[index+1:]:
            denominator = uj-ui
            lo, hi = 2*(kj-ki)-2, 2*(kj-ki)+2
            witness = [[ui, ki], [uj, kj]]
            if lower is None or lo*lower[1] > lower[0]*denominator:
                lower = (lo, denominator, witness)
            if upper is None or hi*upper[1] < upper[0]*denominator:
                upper = (hi, denominator, witness)
    feasible = (upper[0] > 0 and lower[0]*upper[1] < upper[0]*lower[1])
    def bound(value):
        divisor = gcd(value[0], value[1])
        return dict(numerator=value[0]//divisor, denominator=value[1]//divisor,
                    strict=True, witness=value[2])
    return dict(feasible=feasible, informative=True, unique_distances=len(points), samples_seen=count,
                lower_twice_gradient=bound(lower), upper_twice_gradient=bound(upper))


def fixed_affine_intercept(samples, gradient_numerator, gradient_denominator):
    """Exact intercept interval for nibble=floor(a*u+b), with fixed rational a.

    The lower bound is inclusive and the upper bound is exclusive. Witnesses
    identify the observations imposing each bound; no midpoint is selected.
    """
    if (type(gradient_numerator) is not int or type(gradient_denominator) is not int or
            gradient_numerator < 0 or gradient_denominator <= 0):
        raise ValueError('Nonnegative exact rational gradient required')
    lower = upper = None
    count = 0
    for sample in samples:
        if type(sample) not in (list,tuple) or len(sample) != 2:
            raise ValueError('Integer coordinate/nibble pairs required')
        u,n = sample
        if type(u) is not int or type(n) is not int or not 0 <= n < 16:
            raise ValueError('Integer coordinate and four-bit nibble required')
        count += 1
        lo = n*gradient_denominator-gradient_numerator*u
        hi = (n+1)*gradient_denominator-gradient_numerator*u
        if lower is None or lo > lower[0]:
            lower = (lo,[u,n])
        if upper is None or hi < upper[0]:
            upper = (hi,[u,n])
    if count == 0:
        raise ValueError('At least one observation required')
    def bound(value,inclusive):
        divisor = gcd(value[0],gradient_denominator)
        return dict(numerator=value[0]//divisor,denominator=gradient_denominator//divisor,
                    inclusive=inclusive,witness=value[1])
    return dict(feasible=lower[0] < upper[0],samples_seen=count,
                lower=bound(lower,True),upper=bound(upper,False))
