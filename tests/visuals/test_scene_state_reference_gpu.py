# SPDX-License-Identifier: AGPL-3.0-only
"""Selected 3D camera/state scenes retain their independent reference criteria."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_mesh_layout_extensions import case_contract, compare, render
from tools.mesh_layout_reference import load_case

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('name', ['mesh_perspective', 'mesh_polygon_offset'])
def test_selected_scene_camera_depth_state_matches_frozen_upstream(name):
    reference, expected, reference_extras = load_case(name)
    actual, commands, shaders, parameters, extras = render(name, 'dawn_headless')
    assert commands and shaders
    for key, value in case_contract(name).items():
        assert parameters[key] == expected[key] == value, key
    assert parameters['view_rectangles'] == expected['view_rectangles']
    assert extras == reference_extras == {}
    if directory := os.environ.get('VISPY_SCENE_STATE_EVIDENCE'):
        path = Path(directory) / name
        path.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path / 'frames.npz', actual=actual, reference=reference)
        for leaf, value in [('commands', commands), ('shaders', shaders),
                            ('parameters', parameters)]:
            (path / (leaf + '.json')).write_text(json.dumps(value, indent=2) + '\n',
                                               encoding='utf-8')
    compare(name, actual, reference)
    difference = np.abs(actual.astype(np.int16) - reference.astype(np.int16))
    print('frozen scene reference:', name, 'maximum channel difference:', int(difference.max()))
