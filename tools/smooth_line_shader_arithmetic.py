# SPDX-License-Identifier: AGPL-3.0-only
"""Measure shader arithmetic bits, independently of line images or model selection.

Inputs are runtime uniforms. The byte transport is linear RGBA8, blend disabled,
and little endian by explicit shifts, independently of the host's byte order.
This observes this compiler/device path; it does not identify rasterizer setup.
"""
from __future__ import annotations

import numpy as np

OPERATIONS = {
    'identity-x': 'u_direction.x',
    'identity-y': 'u_direction.y',
    'squared-length': 'dot(u_direction, u_direction)',
    'inverse-sqrt': 'inversesqrt(dot(u_direction, u_direction))',
    'reciprocal-sqrt': '1.0 / sqrt(dot(u_direction, u_direction))',
    'product-x': 'u_direction.x * inversesqrt(dot(u_direction, u_direction))',
    'product-y': 'u_direction.y * inversesqrt(dot(u_direction, u_direction))',
    'normalize-x': 'normalize(u_direction).x',
    'normalize-y': 'normalize(u_direction).y',
}
VERTEX = '''#version 330
in vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
'''
# All are directions already present in the original training descriptors.
TRAINING_DIRECTIONS = tuple((sign*x, sign*y)
    for x,y in ((36,9),(36,18),(36,27),(27,36),(18,36),(9,36),(36,36),(36,-18))
    for sign in (1,-1))
def _byte_controls():
    for channel in range(4):
        for byte in range(256):
            bits=(0x3f010203 & ~(255 << (8*channel))) | (byte << (8*channel))
            # A high-byte replacement can produce a subnormal. Set the low
            # exponent bit, in another channel, without changing that byte.
            if (bits >> 23) & 255 == 0:
                bits |= 1 << 23
            yield bits


CONTROL_BITS = (0x00000000, 0x80000000, 0x3f800000, 0xbf800000,
                0x3eaaaaab, 0x3f010203, 0x41234567, 0xc1234567,
                0x7f7fffff, 0xff7fffff) + tuple(_byte_controls())
READBACKS = 2*len(CONTROL_BITS) + 2*len(TRAINING_DIRECTIONS)*len(OPERATIONS)


def fragment(operation):
    if operation not in OPERATIONS:
        raise ValueError('Undeclared shader arithmetic operation')
    return '''#version 330
uniform vec2 u_direction;
void main() {
    uint bits = floatBitsToUint(''' + OPERATIONS[operation] + ''');
    uvec4 bytes = (uvec4(bits) >> uvec4(0u, 8u, 16u, 24u)) & uvec4(255u);
    gl_FragColor = vec4(bytes) / 255.0;
}
'''


def rgba_bits(rgba):
    """Decode exactly one RGBA8 texel, including signed-zero float encodings."""
    if not isinstance(rgba, np.ndarray) or rgba.dtype != np.uint8 or rgba.shape != (1,1,4):
        raise ValueError('Exactly one unmodified RGBA8 texel required')
    return sum(int(byte) << (8*i) for i,byte in enumerate(rgba[0,0]))


def float_from_bits(bits):
    if type(bits) is not int or not 0 <= bits <= 0xffffffff:
        raise ValueError('Unsigned 32-bit integer required')
    return np.array([bits],dtype=np.uint32).view(np.float32)[0]


def measure(gloo):
    """Require an already-current owned single-sample 1x1 linear RGBA8 target.

    Returns raw frames and bits before any comparison with line observations.
    The caller owns device/package/state/teardown admission and persistence.
    """
    programs = {name:gloo.Program(VERTEX,fragment(name)) for name in OPERATIONS}
    positions = gloo.VertexBuffer(np.array([[-1,-1],[3,-1],[-1,3]],np.float32))
    for program in programs.values():
        program['a_position'] = positions
    gloo.set_viewport(0,0,1,1)
    gloo.set_state(blend=False, depth_test=False, stencil_test=False,
                   scissor_test=False, cull_face=False)

    def read(operation, direction):
        program=programs[operation]
        # Explicit float32 runtime transport, never a source literal.
        program['u_direction']=np.asarray(direction,dtype=np.float32)
        gloo.clear(color=(0,0,0,0),depth=False,stencil=False)
        program.draw('triangles')
        rgba=gloo.read_pixels((0,0,1,1),alpha=True)
        return dict(rgba=rgba.tolist(),bits=f'{rgba_bits(rgba):08x}')

    controls=[]
    for bits in CONTROL_BITS:
        # Both identity channels independently exercise byte transport.
        value=float_from_bits(bits)
        for operation in ('identity-x','identity-y'):
            controls.append(dict(operation=operation,input_bits=f'{bits:08x}',
                                 **read(operation,(value,value))))
    rows=[]
    for repeat,indices in enumerate((range(16),range(15,-1,-1))):
        for index in indices:
            direction=TRAINING_DIRECTIONS[index]
            for operation in OPERATIONS:
                rows.append(dict(repeat=repeat,direction=list(direction),operation=operation,
                                 **read(operation,direction)))
    return dict(controls=controls,measurements=rows,renderer_qualified=False,
                rasterizer_algorithm_identified=False,reference_arrays_accessed=False)


def validate_transport_and_repeats(result):
    """Admit transport and stability only; never validate a line coverage model."""
    expected_controls=[(op,f'{bits:08x}') for bits in CONTROL_BITS
                       for op in ('identity-x','identity-y')]
    if [(r['operation'],r['input_bits']) for r in result['controls']] != expected_controls:
        raise ValueError('Incomplete byte-transport controls')
    for row in result['controls']:
        if row['bits'] != row['input_bits']:
            raise ValueError('Shader identity byte transport differs')
    expected=[(repeat,list(TRAINING_DIRECTIONS[i]),op)
              for repeat,indices in enumerate((range(16),range(15,-1,-1)))
              for i in indices for op in OPERATIONS]
    rows=result['measurements']
    if [(r['repeat'],r['direction'],r['operation']) for r in rows] != expected:
        raise ValueError('Incomplete preregistered measurement sequence')
    first={(tuple(r['direction']),r['operation']):r['bits'] for r in rows if r['repeat']==0}
    for row in [*result['controls'],*rows]:
        raw=row['rgba']
        if (type(raw) is not list or len(raw)!=1 or type(raw[0]) is not list or
                len(raw[0])!=1 or type(raw[0][0]) is not list or len(raw[0][0])!=4 or
                any(type(v) is not int or not 0<=v<=255 for v in raw[0][0])):
            raise ValueError('Saved readback is not one exact RGBA8 texel')
        if f'{rgba_bits(np.array(row["rgba"],dtype=np.uint8)):08x}' != row['bits']:
            raise ValueError('Saved bits differ from raw bytes')
    for row in rows:
        if row['bits'] != first[tuple(row['direction']),row['operation']]:
            raise ValueError('Shader arithmetic changed on reverse repeat')
