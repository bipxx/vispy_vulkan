# SPDX-License-Identifier: AGPL-3.0-only
"""The marker references (M02 all symbols, M06 one million markers) stay bound to their fixtures and decision D17."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools import fixture_markers_all_symbols as symbols
from tools import fixture_markers_million as million

ROOT = Path(__file__).resolve().parents[2]
PACKETS = ((symbols, 'tests/reference/markers-all-symbols-opengl', 'tools/fixture_markers_all_symbols.py',
            'tools/oracle_markers_all_symbols_capture.py'),
           (million, 'tests/reference/markers-million-opengl', 'tools/fixture_markers_million.py',
            'tools/oracle_markers_million_capture.py'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_marker_criteria_are_decision_d17():
    assert symbols.CRITERIA == {name: 'edge_pixels' for name in symbols.CASES} and symbols.MAX_EDGE_FRACTION == .001
    assert million.CRITERIA == {name: 'within_2_levels' for name in million.CASES}
    assert (million.LEVELS, million.MAX_BEYOND_FRACTION) == (2, .005)


@pytest.mark.parametrize('module,reference,fixture,capture', PACKETS)
def test_marker_references_bind_their_fixture_criteria_and_artifacts(module, reference, fixture, capture):
    manifest = json.loads((ROOT / reference / 'manifest.json').read_text(encoding='utf-8'))
    origins = manifest['provenance']
    assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0'
    assert origins['fixture_source_sha256'] == digest(ROOT / fixture)
    assert origins['capture_source_sha256'] == digest(ROOT / capture)
    pinned = json.loads((ROOT / 'compat/upstream_manifest.json').read_text(encoding='utf-8'))
    assert origins['markers_source_sha256'] == pinned['files']['visuals/markers.py']
    assert manifest['comparison']['criteria'] == module.CRITERIA and not manifest['errors']
    assert set(manifest['fixtures']) == set(module.CASES)
    for name, record in manifest['fixtures'].items():
        assert record['parameters'] == module.specification(name)
        for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
            assert digest(ROOT / reference / artifact['file']) == artifact['sha256']
        module.assert_landmarks(name, np.load(ROOT / reference / record['rgba']['file'], allow_pickle=False))


def test_all_symbol_rule_allows_only_few_edge_flips():
    # Decision D17, M02: uniform reference neighbourhoods exact; at most 0.1% of the frame differs, by any amount.
    frame = np.zeros((symbols.SIZE[1], symbols.SIZE[0], 4), np.uint8)
    frame[..., 3] = 255
    frame[60:100, 100:200] = (0, 255, 0, 255)
    flipped = frame.copy()
    flipped[60, 100:181, :3] = 0  # 81 edge pixels: 0.099% of 512x160
    assert symbols.difference(flipped, frame) is None
    wider = flipped.copy()
    wider[60, 181, :3] = 0
    assert 'edge pixels differ' in symbols.difference(wider, frame)
    interior = flipped.copy()
    interior[80, 150, 1] -= 1
    assert 'interior pixels differ' in symbols.difference(interior, frame)


def test_million_rule_bounds_levels_and_large_differences():
    # Decision D17, M06: at most 0.5% of pixels may differ by more than 2 levels; every other pixel within 2.
    rng = np.random.default_rng(3)
    frame = rng.integers(10, 245, (million.SIZE[1], million.SIZE[0], 4), dtype=np.uint8)
    within = frame.copy()
    within[..., 1] += 2
    assert million.difference(within, frame) is None
    allowed = int(million.MAX_BEYOND_FRACTION * frame.shape[0] * frame.shape[1])
    beyond = frame.copy()
    beyond.reshape(-1, 4)[:allowed, 0] += 3
    assert million.difference(beyond, frame) is None
    beyond.reshape(-1, 4)[allowed, 0] += 3
    assert 'more than 2 levels' in million.difference(beyond, frame)


@pytest.mark.parametrize('module,name', [(symbols, name) for name in symbols.CASES] +
                         [(million, name) for name in million.CASES])
def test_marker_landmarks_refuse_a_blank_frame(module, name):
    blank = np.zeros((module.SIZE[1], module.SIZE[0], 4), np.uint8)
    blank[..., 3] = 255
    with pytest.raises(AssertionError):
        module.assert_landmarks(name, blank)


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
