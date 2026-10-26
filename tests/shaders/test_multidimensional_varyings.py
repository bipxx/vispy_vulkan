# SPDX-License-Identifier: AGPL-3.0-only
"""Nested stage interfaces against independent window-space interpolation."""
import numpy as np
import pytest
from vispy import app, gloo
from tools.immediate_state_wheel_smoke import _multidimensional_varying_case

pytestmark = pytest.mark.gpu

CASES = [(t,m) for t in ('float','vec3','mat2x3') for m in ('smooth','noperspective','flat')]
CASES += [(t,'flat') for t in ('int','ivec2','uvec3')]

@pytest.mark.parametrize('gtype,interpolation', CASES)
@pytest.mark.parametrize('shape', [(2,2),(2,1,2)])
@pytest.mark.parametrize('topology', ['triangles','lines'])
def test_nested_stage_values_and_interpolation(gtype, interpolation, shape, topology):
    _multidimensional_varying_case(app,gloo,np,gtype,interpolation,shape,topology)
