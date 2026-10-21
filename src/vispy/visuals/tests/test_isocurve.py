"""CPU-only contour preparation; no canvas or renderer is needed."""
import sys
import types
from unittest import mock

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from vispy.geometry.isocurve import isocurve as marching_squares
from vispy.visuals import IsocurveVisual
from vispy.visuals import isocurve as iso_module


DATA = np.tile(np.linspace(0., 1., 5), (5, 1))
PALETTE = np.array([[1., 0., 0., 1.], [0., 1., 0., 1.],
                    [0., 0., 1., 1.], [1., 1., 0., 1.],
                    [1., 0., 1., 1.], [0., 1., 1., 1.]])


@pytest.fixture(autouse=True)
def optional_extractor(monkeypatch):
    # Exercise the actual VisPy marching-squares implementation by default.
    # Explicit branch tests below supply only the optional extractor's return.
    parent = types.ModuleType('skimage')
    parent.__path__ = []
    measure = types.ModuleType('skimage.measure')
    monkeypatch.setitem(sys.modules, 'skimage', parent)
    monkeypatch.setitem(sys.modules, 'skimage.measure', measure)
    return measure


def prepared(levels, colors=None, data=DATA):
    levels = np.asarray(levels)
    visual = IsocurveVisual(data.copy(), levels=levels,
                           color_lev='red' if colors is None else colors)
    return visual, visual._prepare_draw(visual)


def assert_empty(visual):
    assert visual._verts.shape == (0, 2)
    assert visual._li.shape == (0,)
    assert visual._connect.shape == (0,)
    assert visual._connect.dtype == bool
    assert visual._cl.shape == (0, 4)
    assert visual.pos.shape == (0, 2)
    assert visual._color.shape == (0, 4)
    assert not visual._need_recompute
    assert not visual._need_color_update


def assert_colors(visual, indices, palette):
    offset = 0
    for count, level in zip(visual._li, indices):
        assert_array_equal(visual._cl[offset:offset + count],
                           np.tile(palette[level], (count, 1)))
        offset += count
    assert offset == len(visual._verts) == len(visual._cl)


@pytest.mark.parametrize('levels', [[2.], [-1.], [-1., 2.], [], [0., 1.]])
def test_isocurve_no_levels_in_range(levels):
    visual, result = prepared(levels)
    assert result is False
    assert_empty(visual)
    with mock.patch.object(visual, '_compute_iso_line', wraps=visual._compute_iso_line) as compute:
        assert visual._prepare_draw(visual) is False
        assert compute.call_count == 0


@pytest.mark.parametrize('empty_levels', [[2.], [], [0., 1.]])
def test_isocurve_levels_valid_empty_valid(empty_levels):
    visual, result = prepared([.25, .75], PALETTE[:2])
    assert result is not False
    original = visual.pos.copy()
    visual.color = 'red'
    visual.levels = np.asarray(empty_levels)
    assert visual._prepare_draw(visual) is False
    assert_empty(visual)
    visual.color = 'blue'
    assert visual._prepare_draw(visual) is False
    assert_empty(visual)
    visual.levels = np.array([.25, .75])
    assert visual._prepare_draw(visual) is not False
    assert_array_equal(visual.pos, original)
    assert_array_equal(visual._cl, np.tile([0., 0., 1., 1.], (len(original), 1)))


@pytest.mark.parametrize('shift', [2., -2.])
def test_isocurve_data_valid_empty_valid(shift):
    visual, result = prepared([.5])
    assert result is not False
    original = visual.pos.copy()
    visual.set_data(DATA + shift)
    assert visual._prepare_draw(visual) is False
    assert_empty(visual)
    visual.color = 'blue'
    assert visual._prepare_draw(visual) is False
    visual.set_data(DATA.copy())
    assert visual._prepare_draw(visual) is not False
    assert_array_equal(visual.pos, original)
    assert_array_equal(visual._cl, np.tile([0., 0., 1., 1.], (len(original), 1)))


@pytest.mark.parametrize('levels,indices', [
    ([2., .75, -1., .25, 3., .5], [1, 3, 5]),
    ([-1., .25, 2., .75], [1, 3]),
    ([.75, 2., .25], [0, 2]),
])
def test_isocurve_colors_follow_original_level_indices(levels, indices):
    visual, result = prepared(levels, PALETTE[:len(levels)])
    assert result is not False
    assert len(visual._li) == len(indices)
    assert_colors(visual, indices, PALETTE)


@pytest.mark.parametrize('levels', [[.25], [.75], [.25, .75]])
def test_isocurve_normal_marching_squares_unchanged(levels):
    visual, result = prepared(levels, PALETTE[:len(levels)])
    assert result is not False
    vertices = []
    connects = []
    for level in levels:
        paths = marching_squares(DATA.astype(float).T, level,
                                 extend_to_edge=True, connected=True)
        verts = np.vstack(paths)
        gaps = np.add.accumulate([len(path) for path in paths]) - 1
        connect = np.ones(gaps[-1], dtype=bool)
        connect[gaps[:-1]] = False
        vertices.append(verts)
        connects.append(np.hstack((connect, [False])))
    assert_array_equal(visual.pos, np.vstack(vertices))
    assert_array_equal(visual._connect, np.hstack(connects))
    assert_colors(visual, range(len(levels)), PALETTE)


@pytest.mark.parametrize('backend', ['marching_squares', 'optional_extractor'])
@pytest.mark.parametrize('levels,indices', [([.25, .5, .75], [0, 2]),
                                           ([.5, .25, .75], [1, 2])])
def test_isocurve_selected_level_without_lines(optional_extractor, monkeypatch,
                                               backend, levels, indices):
    calls = []
    def contours(data, level, **kwargs):
        calls.append(level)
        return [] if level == .5 else [np.array([[level, 0.], [level, 1.]])]
    if backend == 'optional_extractor':
        optional_extractor.find_contours = contours
    else:
        monkeypatch.setattr(iso_module, 'isocurve', contours)
    visual, result = prepared(levels, PALETTE[:3])
    assert result is not False
    assert calls == levels
    assert_array_equal(visual._li, [2, 2])
    assert_array_equal(visual._connect, [True, False, True, False])
    assert_colors(visual, indices, PALETTE)


@pytest.mark.parametrize('backend', ['marching_squares', 'optional_extractor'])
def test_isocurve_all_selected_levels_without_lines(optional_extractor,
                                                   monkeypatch, backend):
    def contours(data, level, **kwargs):
        return []
    if backend == 'optional_extractor':
        optional_extractor.find_contours = contours
    else:
        monkeypatch.setattr(iso_module, 'isocurve', contours)
    visual, result = prepared([.25, .75])
    assert result is False
    assert_empty(visual)


def test_isocurve_color_change_reuses_level_indices():
    levels = np.array([.75, 2., .25])
    visual, result = prepared(levels, PALETTE[:3])
    assert result is not False
    original = visual.pos.copy()
    with mock.patch.object(visual, '_compute_iso_line', wraps=visual._compute_iso_line) as compute:
        visual.color = PALETTE[:3][::-1]
        assert visual._prepare_draw(visual) is not False
        assert compute.call_count == 0
    assert_array_equal(visual.pos, original)
    assert_colors(visual, [0, 2], PALETTE[:3][::-1])


def test_isocurve_color_count_mismatch_still_refuses():
    with pytest.raises(TypeError, match='Color/level mismatch'):
        prepared([.25, .5, .75], PALETTE[:2])


def test_isocurve_uniform_data_still_skips_preparation():
    visual, result = prepared([.5], data=np.ones((4, 4)))
    assert result is False
