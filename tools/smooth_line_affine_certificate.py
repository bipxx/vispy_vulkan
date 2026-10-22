# SPDX-License-Identifier: AGPL-3.0-only
"""Exact verification of diagnostic affine nibble certificates, never a predictor."""
from fractions import Fraction
import struct


def verify_affine_nibble(samples,coefficients):
    """Check saturated floor(A*X+B*Y+C) for doubled pixel centers X,Y.

    Nibble0 has only a strict upper bound; nibble15 has only a lower bound.
    All other nibbles have inclusive lower and strict upper bounds. Numerical
    solvers may propose certificates, but this function uses exact rationals.
    """
    if (type(coefficients) is not tuple or len(coefficients)!=3 or
            any(type(c) is not Fraction for c in coefficients)):
        raise ValueError('Three exact rational coefficients required')
    a,b,c=coefficients
    count=0
    first=None
    for index,sample in enumerate(samples):
        if (type(sample) not in (tuple,list) or len(sample)!=3 or
                any(type(v) is not int for v in sample)):
            raise ValueError('Exact doubled pixel coordinates and nibble required')
        x,y,n=sample
        if not (1<=x<=127 and x%2 and 1<=y<=127 and y%2 and 0<=n<=15):
            raise ValueError('Training pixel center and four-bit nibble required')
        value=a*x+b*y+c
        passed=(n==0 or value>=n) and (n==15 or value<n+1)
        if not passed and first is None:
            first=dict(index=index,sample=list(sample),
                value=dict(numerator=value.numerator,denominator=value.denominator))
        count+=1
    if not count:
        raise ValueError('At least one observation required')
    return dict(verified=first is None,samples_checked=count,first_violation=first)


def affine_intercept_interval(samples,a,b):
    """Intersect exact nibble bounds for C with fixed rational slopes A,B.

    No representative constant is chosen. Missing bounds are unbounded; every
    finite upper bound is strict. Retain the observations imposing the bounds.
    """
    if type(a) is not Fraction or type(b) is not Fraction:
        raise ValueError('Exact rational slopes required')
    lower=upper=None
    count=0
    for sample in samples:
        if (type(sample) not in (tuple,list) or len(sample)!=3 or
                any(type(v) is not int for v in sample)):
            raise ValueError('Exact doubled pixel coordinates and nibble required')
        x,y,n=sample
        if not (1<=x<=127 and x%2 and 1<=y<=127 and y%2 and 0<=n<=15):
            raise ValueError('Training pixel center and four-bit nibble required')
        base=a*x+b*y
        if n>0:
            bound=Fraction(n)-base
            if lower is None or bound>lower[0]:lower=(bound,list(sample))
        if n<15:
            bound=Fraction(n+1)-base
            if upper is None or bound<upper[0]:upper=(bound,list(sample))
        count+=1
    if not count:raise ValueError('At least one observation required')
    def record(bound,inclusive):
        if bound is None:return None
        value,witness=bound
        return dict(numerator=value.numerator,denominator=value.denominator,
                    inclusive=inclusive,witness=witness)
    return dict(feasible=lower is None or upper is None or lower[0]<upper[0],
                samples_checked=count,lower=record(lower,True),upper=record(upper,False))


def binary32_interval_member(lower,upper):
    """Exact existence test for a finite binary32 in [lower,upper).

    Bisect the ordered finite encoding space, including signed zeros and
    subnormals. Rational endpoints are never rounded to binary64. A returned
    member is an existence certificate only, not a selected model constant.
    """
    if type(lower) is not Fraction or type(upper) is not Fraction:
        raise ValueError('Exact finite rational bounds required')
    if lower>=upper:return dict(exists=False,reason='empty-interval')
    def decode(key):
        bits=(key^0x80000000) if key&0x80000000 else (~key&0xffffffff)
        value=struct.unpack('>f',struct.pack('>I',bits))[0]
        return bits,Fraction.from_float(value)
    first,last=0x00800000,0xff7fffff
    lo,hi=first,last+1
    while lo<hi:
        mid=(lo+hi)//2
        if decode(mid)[1]<lower:lo=mid+1
        else:hi=mid
    if lo>last:return dict(exists=False,reason='above-finite-range')
    bits,value=decode(lo)
    member=dict(bits=f'{bits:08x}',numerator=value.numerator,denominator=value.denominator)
    return dict(exists=value<upper,first_at_or_above_lower=member,
                reason='member' if value<upper else 'no-representable-value-before-upper')
