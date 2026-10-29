# SPDX-License-Identifier: AGPL-3.0-only
"""The napari vector-layer OpenGL references (W4, M11) stay bound to this fixture and its criteria fixed before capture."""
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.fixture_napari_vector_layers import CASES, CRITERIA, assert_landmarks, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'tests/reference/napari-vector-layers-opengl'
FIXED = ('case', 'size', 'camera_center', 'camera_zoom', 'background', 'criterion', 'inputs_sha256')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_vector_layer_criteria_are_the_ones_fixed_before_capture():
    assert CRITERIA == {'vectors': 'exact', 'tracks': 'smooth_line', 'shapes_selected': 'smooth_line'}
    assert set(CRITERIA) == set(CASES)


def test_vector_layer_references_bind_the_fixture_criteria_and_artifacts():
    manifest = json.loads((REFERENCE / 'manifest.json').read_text(encoding='utf-8'))
    origins = manifest['provenance']
    assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0' and origins['napari_version'] == '0.9.2'
    assert origins['fixture_source_sha256'] == digest(ROOT / 'tools/fixture_napari_vector_layers.py')
    assert origins['capture_source_sha256'] == digest(ROOT / 'tools/oracle_napari_vector_layers_capture.py')
    assert manifest['comparison']['criteria'] == CRITERIA and not manifest['errors']
    assert set(manifest['fixtures']) == set(CASES)
    for name, record in manifest['fixtures'].items():
        assert {key: record['parameters'][key] for key in FIXED} == {key: specification(name)[key] for key in FIXED}
        for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
            assert digest(REFERENCE / artifact['file']) == artifact['sha256']
        assert_landmarks(name, np.load(REFERENCE / record['rgba']['file'], allow_pickle=False))


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
