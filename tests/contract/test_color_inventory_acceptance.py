"""Source acceptance for the reviewed color inventory cases."""

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from vispy.color import Color, ColorArray, get_color_dict, get_color_names
from vispy.color import get_colormap, get_colormaps
from vispy.color.colormap import (
    BaseColormap, Colormap, CubeHelixColormap, Diverging, HSL, HSLuv,
    MatplotlibColormap, RedYellowBlueCyan, SingleHue,
)


def test_basecolormap():
    class GrayRamp(BaseColormap):
        def map(self, t):
            return np.column_stack((t, t, t, np.ones_like(t)))

    assert_allclose(GrayRamp()[[-1, 0.25, 2]].rgba,
                    [[0, 0, 0, 1], [.25, .25, .25, 1], [1, 1, 1, 1]])
    with pytest.raises(NotImplementedError):
        BaseColormap().map(np.array([[0.5]]))


def test_color():
    color = Color('#33669980')
    color.alpha = 0.25
    assert_array_equal(color.RGBA, [51, 102, 153, 63])
    with pytest.raises(ValueError, match='missing-color-1137'):
        Color('missing-color-1137')
    assert_array_equal(Color('RED').RGB, [255, 0, 0])


def test_color_names_dict():
    colors = get_color_dict()
    assert get_color_names() == sorted(colors)
    assert colors['cornflowerblue'].lower() == '#6495ed'
    colors['red'] = '#000000'
    assert get_color_dict()['red'].lower() == '#ff0000'
    assert_array_equal(Color('red').RGB, [255, 0, 0])


def test_colorarray():
    colors = ColorArray([(1, 0, 0, .25), (0, 1, 0, .75)])
    colors.rgb = [(0, 0, 1), (1, 1, 1)]
    assert_allclose(colors.rgba, [[0, 0, 1, .25], [1, 1, 1, .75]])
    indexed = ColorArray(['red', 'blue'])
    with pytest.raises(ValueError):
        indexed[0, 1]
    assert_allclose(indexed[1].rgba, [[0, 0, 1, 1]])


def test_colormap_invalid_interpolation_preserves_mapping():
    cmap = Colormap(['black', 'white'])
    with pytest.raises(ValueError, match='interpolation mode'):
        cmap.interpolation = 'spline'
    assert_allclose(cmap[0.5].rgba, [[.5, .5, .5, 1]])


def test_cubehelixcolormap():
    cmap = CubeHelixColormap(reverse=False, nlev=8)
    assert_allclose(cmap[[0, 1]].rgba, [[0, 0, 0, 1], [1, 1, 1, 1]])
    with pytest.raises(TypeError):
        CubeHelixColormap(nlev='invalid')


def test_diverging():
    assert_allclose(Diverging(center='dark')[0.5].rgba,
                    [[.133, .133, .133, 1]], atol=1e-6, rtol=0)
    cmap = Diverging()
    with pytest.raises(RuntimeError):
        cmap[0.5] = 'red'
    assert_allclose(cmap[0.5].rgba, [[.92, .92, .92, 1]])


def test_get_colormap_matplotlib_fallback():
    pytest.importorskip('matplotlib')
    assert_allclose(get_colormap('gray_r')[[0, 1]].rgba,
                    [[1, 1, 1, 1], [0, 0, 0, 1]])


def test_get_colormap_unknown_and_existing_instance():
    with pytest.raises(KeyError, match='__missing_1137__'):
        get_colormap('__missing_1137__')
    cmap = Colormap(['black', 'white'])
    assert get_colormap(cmap) is cmap


def test_get_colormaps():
    maps = get_colormaps()
    assert maps['grays'] is get_colormap('grays')
    del maps['viridis']
    assert 'viridis' in get_colormaps()


def test_hsl():
    assert_allclose(HSL(ncolors=3)[[0, .5, 1]].rgba,
                    [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]], atol=1e-7)
    with pytest.raises(ValueError, match='interpolation mode'):
        HSL(ncolors=3, interpolation='unknown')


def test_hsluv():
    cmap = HSLuv(ncolors=3, saturation=0, value=0.5)
    assert_allclose(cmap[0.5].rgba, [[.46137, .46137, .46137, 1]],
                    atol=.002, rtol=0)
    with pytest.raises(AssertionError):
        HSLuv(ncolors=3, interpolation='zero', controls=[0, 1])


def test_matplotlibcolormap():
    pytest.importorskip('matplotlib')
    assert_allclose(MatplotlibColormap('gray')[[0, 1]].rgba,
                    [[0, 0, 0, 1], [1, 1, 1, 1]])
    with pytest.raises(ValueError, match='__missing_1137__'):
        MatplotlibColormap('__missing_1137__')


def test_named_colormaps():
    assert_allclose(get_colormap('grays')[[0, .25, 1]].rgba,
                    [[0, 0, 0, 1], [.25, .25, .25, 1], [1, 1, 1, 1]])
    assert_allclose(get_colormap('HiLo')[[-1, 2]].rgba,
                    [[0, 0, 1, 1], [1, 0, 0, 1]])


def test_redyellowbluecyan():
    cmap = RedYellowBlueCyan(limits=(.25, .5, 1))
    mapped = cmap[[0, .5, 1]].rgba
    assert_allclose(mapped[:, 3], [1, 0, 1])
    assert_allclose(mapped[[0, 2], :3], [[0, 1, 1], [1, 1, 0]])
    with pytest.raises(ValueError):
        RedYellowBlueCyan(limits=(.5, .25, 1))


def test_singlehue():
    cmap = SingleHue(hue=0, saturation_range=[0, 1], value=1)
    assert_allclose(cmap[[0, 1]].rgba, [[1, 1, 1, 1], [1, 0, 0, 1]])
    with pytest.raises(IndexError):
        SingleHue(saturation_range=[1])
