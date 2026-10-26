# SPDX-License-Identifier: AGPL-3.0-only
"""Static opaque-array leaves preserve texture dimensions, words and rebinding."""
import numpy as np
import pytest
from vispy import app, gloo

from tools.immediate_state_wheel_smoke import _static_sampler_array_case, _cube_face_update_case

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('sampler', ['sampler1D', 'sampler2D', 'sampler3D', 'samplerCube', 'isampler2D', 'usampler2D'])
@pytest.mark.parametrize('shape', [(2,), (2, 2), (2, 2, 2)])
def test_literal_sampler_shapes_types_and_rebinding(sampler, shape):
    _static_sampler_array_case(app, gloo, np, sampler, shape)


def test_cube_face_order_and_partial_update_preserve_other_faces():
    _cube_face_update_case(app, gloo, np)
