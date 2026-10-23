# SPDX-License-Identifier: AGPL-3.0-only
"""Exact local-product identity for testing reciprocal-only coverage models."""


def local_product_key(probe,x,y):
    if type(x) is not int or type(y) is not int or not (0<=x<64 and 0<=y<64):
        raise ValueError('Training pixel coordinates required')
    values=(*probe.start_units,*probe.end_units,probe.width_units)
    if any(type(value) is not int for value in values):
        raise ValueError('Exact integer geometry required')
    x0,y0=probe.start_units
    x1,y1=probe.end_units
    dx,dy=x1-x0,y1-y0
    if dx==dy==0 or probe.width_units<=0:
        raise ValueError('Nondegenerate positive-width geometry required')
    px,py=x*256+128,y*256+128
    cross=(py-y0)*dx-(px-x0)*dy
    start=(px-x0)*dx+(py-y0)*dy
    end=(x1-px)*dx+(y1-py)*dy
    # Keep slope and length; erase only simultaneous endpoint/delta reversal.
    sign=1 if dx>0 or (dx==0 and dy>0) else -1
    return (sign*dx,sign*dy,probe.width_units,cross,start,end)
