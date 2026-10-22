# SPDX-License-Identifier: AGPL-3.0-only
"""Complete local 2D segment inputs, retaining signed direction, for diagnostics."""


def local_window_key(probe,x,y):
    if type(x) is not int or type(y) is not int or not (0<=x<64 and 0<=y<64):
        raise ValueError('Integer training pixel required')
    if any(type(v) is not int for v in (*probe.start_units,*probe.end_units,probe.width_units)):
        raise ValueError('Exact integer geometry required')
    x0,y0=probe.start_units
    x1,y1=probe.end_units
    return (x1-x0,y1-y0,probe.width_units,x*256+128-x0,y*256+128-y0)
