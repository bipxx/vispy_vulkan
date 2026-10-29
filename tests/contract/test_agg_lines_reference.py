# SPDX-License-Identifier: AGPL-3.0-only
"""The Agg line OpenGL references (M09) stay bound to this fixture and its exact criteria."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_agg_lines import CASES, CRITERIA, assert_landmarks, specification

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'tests/reference/agg-lines-opengl'
FIXED = ('case', 'size', 'px_scale', 'render_size', 'width', 'polylines', 'caps', 'joins', 'color', 'criterion',
         'inputs_sha256')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_agg_line_criteria_are_exact_and_cover_every_cap_and_join():
    assert CRITERIA == {name: 'exact' for name in CASES}
    assert set(CASES) == {'caps', 'joins', 'degenerate', 'px_scale2', 'px_scale3'}
    assert specification('caps')['caps'] == ['none', 'round', 'triangle in', 'triangle out', 'square', '|']
    assert specification('joins')['joins'] == ['miter', 'round', 'bevel']
    assert [specification(name)['px_scale'] for name in ('px_scale2', 'px_scale3')] == [2, 3]


def test_agg_line_references_bind_the_fixture_criteria_and_artifacts():
    manifest = json.loads((REFERENCE / 'manifest.json').read_text(encoding='utf-8'))
    origins = manifest['provenance']
    assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0'
    assert origins['fixture_source_sha256'] == digest(ROOT / 'tools/fixture_agg_lines.py')
    assert origins['capture_source_sha256'] == digest(ROOT / 'tools/oracle_agg_lines_capture.py')
    pinned = json.loads((ROOT / 'compat/upstream_manifest.json').read_text(encoding='utf-8'))
    assert origins['line_source_sha256'] == pinned['files']['visuals/line/line.py']
    assert manifest['comparison']['criteria'] == CRITERIA and not manifest['errors']
    assert set(manifest['fixtures']) == set(CASES)
    for name, record in manifest['fixtures'].items():
        assert {key: record['parameters'][key] for key in FIXED} == {key: specification(name)[key] for key in FIXED}
        assert record['parameters']['pixel_scale'] == specification(name)['px_scale']
        for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
            assert digest(REFERENCE / artifact['file']) == artifact['sha256']
        assert_landmarks(name, np.load(REFERENCE / record['rgba']['file'], allow_pickle=False))


@pytest.mark.parametrize('name', CASES)
def test_agg_line_landmarks_refuse_a_blank_frame(name):
    width, height = specification(name)['render_size']
    blank = np.zeros((height, width, 4), np.uint8)
    blank[..., 3] = 255
    with pytest.raises(AssertionError):
        assert_landmarks(name, blank)


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
