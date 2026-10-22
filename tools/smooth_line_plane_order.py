# SPDX-License-Identifier: AGPL-3.0-only
"""Declared coordinate parenthesizations for bounded plane setup/evaluation."""
import numpy as np
try:
    from .smooth_line_plane_setup import fma32
except ImportError:
    from smooth_line_plane_setup import fma32

SETUP_PATHS=('split','fused-x-outer','fused-y-outer')
EVALUATION_PATHS=('sum-then-constant','x-constant-first','y-constant-first',
                  'fused-x-outer','fused-y-outer','float64')


def ordered_constant(a,b,x,y,offset,path):
    if path=='split':return np.float32(offset-np.float32(np.float32(a*x)+np.float32(b*y)))
    if path=='fused-x-outer':return fma32(-a,x,fma32(-b,y,offset))
    if path=='fused-y-outer':return fma32(-b,y,fma32(-a,x,offset))
    raise ValueError('Declared constant order required')


def ordered_evaluation(a,b,c,x,y,path):
    if path=='sum-then-constant':return np.float32(np.float32(np.float32(a*x)+np.float32(b*y))+c)
    if path=='x-constant-first':return np.float32(np.float32(np.float32(a*x)+c)+np.float32(b*y))
    if path=='y-constant-first':return np.float32(np.float32(np.float32(b*y)+c)+np.float32(a*x))
    if path=='fused-x-outer':return fma32(a,x,fma32(b,y,c))
    if path=='fused-y-outer':return fma32(b,y,fma32(a,x,c))
    if path=='float64':return np.float64(a)*np.float64(x)+np.float64(b)*np.float64(y)+np.float64(c)
    raise ValueError('Declared evaluation order required')
