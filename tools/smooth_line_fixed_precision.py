# SPDX-License-Identifier: AGPL-3.0-only
"""Exact binary-grid arithmetic for coefficient-format diagnostics."""
from fractions import Fraction
from math import isqrt

ROUNDINGS=('nearest-even','negative-infinity','positive-infinity','zero')


def quantized_sqrt_ratio(numerator,radicand,fraction_bits,rounding):
    """Quantize numerator/sqrt(radicand) without approximating the square root."""
    if (type(numerator) is not int or type(radicand) is not int or radicand<=0 or
            type(fraction_bits) is not int or not 0<=fraction_bits<=48 or rounding not in ROUNDINGS):
        raise ValueError('Declared exact sqrt ratio and binary grid required')
    scale=1<<fraction_bits
    square=(abs(numerator)*scale)**2
    low=isqrt(square//radicand)
    exact=low*low*radicand==square
    if rounding=='nearest-even':
        comparison=4*square-radicand*(2*low+1)**2
        magnitude=low+(comparison>0 or (comparison==0 and low%2==1))
    else:
        away=(rounding=='positive-infinity' and numerator>=0 or
              rounding=='negative-infinity' and numerator<0)
        magnitude=low+(away and not exact)
    return Fraction(-magnitude if numerator<0 else magnitude,scale)


def binary_fraction_interval_member(lower,upper,fraction_bits):
    """Existence on an unbounded-integer binary fractional grid in [lo,hi)."""
    if (type(lower) is not Fraction or type(upper) is not Fraction or
            type(fraction_bits) is not int or not 0<=fraction_bits<=48):
        raise ValueError('Exact rational interval and binary precision required')
    if lower>=upper:return dict(exists=False,reason='empty-interval')
    scale=1<<fraction_bits
    integer=-((-lower.numerator*scale)//lower.denominator)
    value=Fraction(integer,scale)
    return dict(exists=value<upper,numerator=value.numerator,denominator=value.denominator,
                fraction_bits=fraction_bits,integer_bits_bounded=False)
