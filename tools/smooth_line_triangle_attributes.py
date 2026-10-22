# SPDX-License-Identifier: AGPL-3.0-only
"""Rounded rectangle triangle-attribute interpolation hypotheses; CPU research."""
from itertools import product
import numpy as np
try:
    from .smooth_line_mechanism import Probe, SIZE
    from .smooth_line_directed_axial import predict_axial_staged
    from .smooth_line_quad_planes import coverage_quad, NORMALIZATIONS, CORNERS, GEOMETRIES, _validate
    from .smooth_line_float_intervals import ORDERS, evaluate_plane
except ImportError:
    from smooth_line_mechanism import Probe, SIZE
    from smooth_line_directed_axial import predict_axial_staged
    from smooth_line_quad_planes import coverage_quad, NORMALIZATIONS, CORNERS, GEOMETRIES, _validate
    from smooth_line_float_intervals import ORDERS, evaluate_plane

SETUPS = ('split32', 'float64-then32')
DIAGONALS = ('0-2', '1-3')
MASKS = ('quantized-alpha', 'positive-geometry')
HYPOTHESES = tuple(product(NORMALIZATIONS, CORNERS, GEOMETRIES, SETUPS, DIAGONALS, ORDERS, MASKS))
_HYPOTHESES = frozenset(HYPOTHESES)


def triangle_plane(vertices, attributes, setup):
    """Solve an affine attribute using two vertex differences; transport FP32."""
    if setup not in SETUPS:
        raise ValueError('Declared triangle setup required')
    vertices = np.asarray(vertices, np.float32)
    attributes = np.asarray(attributes, np.float32)
    if vertices.shape != (3, 2) or attributes.shape != (3,) or not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(attributes)):
        raise ValueError('Three finite vertices and attributes required')
    dtype = np.float32 if setup == 'split32' else np.float64
    v, f = vertices.astype(dtype), attributes.astype(dtype)
    x1, y1 = v[1]-v[0]
    x2, y2 = v[2]-v[0]
    f1, f2 = dtype(f[1]-f[0]), dtype(f[2]-f[0])
    det = dtype(dtype(x1*y2)-dtype(y1*x2))
    if not np.isfinite(det) or det == 0:
        raise ValueError('Nondegenerate finite rounded triangle required')
    a = dtype(dtype(dtype(f1*y2)-dtype(f2*y1))/det)
    b = dtype(dtype(dtype(x1*f2)-dtype(x2*f1))/det)
    c = dtype(dtype(f[0]-dtype(a*v[0,0]))-dtype(b*v[0,1]))
    result = np.asarray((a,b,c), np.float32)
    if not np.all(np.isfinite(result)):
        raise ValueError('Finite transported triangle coefficients required')
    return result


def triangle_partition(quad, diagonal, x, y):
    """Exact dyadic diagonal orientation for bounded half-pixel coordinates."""
    if diagonal not in DIAGONALS:
        raise ValueError('Declared diagonal required')
    quad = np.asarray(quad, np.float32)
    if quad.shape != (4,2) or not np.all(np.isfinite(quad)) or np.max(np.abs(quad)) > 128:
        raise ValueError('Bounded finite rounded quad required')
    if diagonal == '0-2':
        first, second, edge, inside = (0,1,2), (0,2,3), (0,2), 1
    else:
        first, second, edge, inside = (0,1,3), (1,2,3), (1,3), 0
    x,y=np.broadcast_arrays(np.asarray(x,np.float64),np.asarray(y,np.float64))
    if not all(np.all(np.isfinite(v)) and np.all(np.abs(v)<=128) and np.all(v*2==np.floor(v*2)) for v in (x,y)):
        raise ValueError('Bounded half-pixel coordinates required')
    scale=max(2,*(float(v).as_integer_ratio()[1] for v in quad.flat))
    exact=np.asarray([[int(float(v)*scale) for v in row] for row in quad],dtype=object)
    p,q=exact[list(edge)]
    d=q-p
    reference=d[0]*(exact[inside,1]-p[1])-d[1]*(exact[inside,0]-p[0])
    if reference == 0:
        raise ValueError('Nondegenerate diagonal required')
    X=np.asarray([int(float(v)*scale) for v in x.flat],dtype=object).reshape(x.shape)
    Y=np.asarray([int(float(v)*scale) for v in y.flat],dtype=object).reshape(y.shape)
    cross=d[0]*(Y-p[1])-d[1]*(X-p[0])
    return first, second, cross >= 0 if reference > 0 else cross <= 0


def quad_attributes(probe, geometry):
    """Ideal inward distances at vertices ordered left-start,left-end,right-end,right-start."""
    _validate(probe)
    if geometry not in GEOMETRIES:
        raise ValueError('Declared rectangle geometry required')
    delta = (np.asarray(probe.end_units,np.float64)-probe.start_units)/256
    length = np.sqrt(np.sum(delta*delta))
    offset = .5 if geometry == 'inner' else 0
    across = probe.width_units/256 + (0 if geometry == 'inner' else 1)
    along = length + (.25 if geometry == 'inner' else 1.25)
    return np.asarray([[offset,along+offset,across+offset,offset],
                       [offset,offset,across+offset,along+offset],
                       [across+offset,offset,offset,along+offset],
                       [across+offset,along+offset,offset,offset]],np.float32)


def predict_triangle_pixels(probe, hypothesis, pixels):
    if type(hypothesis) is not tuple or hypothesis not in _HYPOTHESES:
        raise ValueError('Only the576 declared triangle-attribute hypotheses are allowed')
    _validate(probe)
    if not pixels or any(type(p) not in (list,tuple) or len(p)!=2 or any(type(v) is not int for v in p)
                         or not (0<=p[0]<SIZE[0] and 0<=p[1]<SIZE[1]) for p in pixels):
        raise ValueError('Integer in-frame pixels required')
    if probe.start_units[0]==probe.end_units[0] or probe.start_units[1]==probe.end_units[1]:
        image=predict_axial_staged(probe)
        return np.asarray([image[y,x] for x,y in pixels],np.uint8)
    normalization,corner,geometry,setup,diagonal,order,mask=hypothesis
    quad,_=coverage_quad(probe,normalization,corner,geometry)
    attrs=quad_attributes(probe,geometry)
    x,y=np.asarray(pixels,np.float32).T+np.float32(.5)
    first,second,choose_first=triangle_partition(quad,diagonal,x,y)
    values=[]
    for k in range(4):
        planes=[triangle_plane(quad[list(indices)],attrs[list(indices),k],setup) for indices in (first,second)]
        evaluated=[evaluate_plane(*plane,x,y,order) for plane in planes]
        values.append(np.where(choose_first,evaluated[0],evaluated[1]))
    left,end,right,start=values
    minor=np.minimum(left,right)
    nibble=np.clip(np.floor(minor*minor.dtype.type(16)),0,15).astype(np.int32)
    code=2*nibble+(nibble>>3)
    overlap=np.clip(np.minimum(start,end),0,1)
    factor=np.where(overlap>0,np.minimum(32,np.ceil(overlap.dtype.type(32)*overlap)+1),0).astype(np.int32)
    combined=code*factor//32
    generated=combined>0 if mask=='quantized-alpha' else (minor>0)&(overlap>0)
    result=np.zeros((len(pixels),4),np.uint8)
    result[:,:3]=np.where(generated[:,None],255,0)
    result[:,3]=((263*combined+16)//32).astype(np.uint8)
    return result


def predict_triangle_attributes(probe,hypothesis):
    pixels=tuple((x,y) for y in range(SIZE[1]) for x in range(SIZE[0]))
    return predict_triangle_pixels(probe,hypothesis,pixels).reshape(SIZE[1],SIZE[0],4)
