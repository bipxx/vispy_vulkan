# SPDX-License-Identifier: AGPL-3.0-only
"""Named array composition, shared stages and live updates against scalar references."""
import numpy as np
import pytest
from vispy import app, gloo
from vispy.visuals.shaders import Variable, ModularProgram

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('gtype,components', [('float', 1), ('int', 1), ('bool', 1),
    ('vec3', 3), ('bvec3', 3), ('mat2', 4), ('mat2x3', 6), ('mat4x2', 8)])
@pytest.mark.parametrize('shape', [(3,), (2, 3), (2, 2, 3)])
@pytest.mark.parametrize('topology', ['triangles', 'lines'])
def test_composed_arrays_shared_stages_collisions_and_updates(gtype, components, shape, topology):
    from tools.immediate_state_wheel_smoke import _composed_uniform_array_case
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), show=False, config={'samples': 0})
    try:
        canvas.set_current()
        _composed_uniform_array_case(gloo, np, Variable, ModularProgram,
                                     gtype, components, shape, topology)
    finally:
        canvas.set_current()
        canvas.context.flush_commands()
        canvas.close()
