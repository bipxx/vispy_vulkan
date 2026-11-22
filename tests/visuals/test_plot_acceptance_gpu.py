"""Reviewed plot entry-point contracts on the Dawn headless backend."""
import numpy as np
import pytest
from numpy.testing import assert_allclose

from vispy import scene
from vispy.geometry import MeshData
from vispy.plot import Fig, PlotWidget
from vispy.scene.cameras import TurntableCamera

pytestmark = pytest.mark.gpu
SIZE = (480, 360)


@pytest.fixture
def canvas():
    with scene.SceneCanvas(app='dawn_headless', size=SIZE, show=False) as target:
        yield target


@pytest.fixture
def axes(canvas):
    return canvas.central_widget.add_widget(PlotWidget())


def _pixel_at(image, visual, position):
    mapped = visual.transforms.get_transform('visual', 'canvas').map(position)
    x, y = np.floor(mapped[:2] / mapped[3]).astype(int)
    assert 0 <= x < image.shape[1] and 0 <= y < image.shape[0]
    return image[y, x, :3]


def test_fig():
    with Fig(app='dawn_headless', show=False, size=(160, 120)) as fig:
        upper = fig[0, 0:2]
        lower = fig[1, 0]
        assert isinstance(upper, PlotWidget) and isinstance(lower, PlotWidget)
        assert fig.plot_widgets == (upper, lower)

    with Fig(app='dawn_headless', show=False, size=(160, 120)) as fig:
        upper = fig[0, 0:2]
        lower = fig[1:3, 0:2]
        right = fig[1:3, 2]
        with pytest.raises(ValueError, match='collision'):
            fig[1:3, 1]
        assert fig[1:3, 2] is right
        assert fig.plot_widgets == (upper, lower, right)


@pytest.mark.parametrize(
    'options, expected_color', [({}, 'k'), ({'fg_color': 'red'}, 'red')], ids=['default', 'custom']
)
def test_plotwidget(canvas, options, expected_color):
    axes = canvas.central_widget.add_widget(PlotWidget(**options))
    with pytest.raises(ValueError):
        axes.plot([0, 1], line_kind='--')
    line = axes.plot(([0, 100], [0, 100]), xlabel='x', line_kind='-')
    canvas.show(run=False)
    canvas.render()
    assert line.parent is axes.view.scene
    assert axes.xlabel.text == 'x'
    assert_allclose(axes.xaxis.axis.domain, (-5, 105), atol=0.1)
    assert axes.xaxis.axis.axis_color == expected_color


def test_colorbar(canvas, axes):
    with pytest.raises(ValueError):
        axes.colorbar('grays', position='diagonal', clim=(0, 1))
    right = axes.colorbar('grays', position='right', clim=(0, 1))
    assert right.orientation == 'right'

    bar = axes.colorbar('grays', position='bottom', clim=(0, 1), label='signal')
    image = canvas.render()
    x, y = bar.rect.center
    offset = 0.35 * bar.rect.width
    dark = _pixel_at(image, bar, (x - offset, y, 0, 1))
    light = _pixel_at(image, bar, (x + offset, y, 0, 1))
    assert np.all(light.astype(int) - dark.astype(int) >= 150)
    assert bar.label.text == 'signal'


def test_histogram(axes):
    hist = axes.histogram([0.25, 0.75, 1.25], bins=[0, 1, 2], orientation='v')
    # Vertical orientation uses the x coordinate for the bin counts.
    assert hist.bounds(0) == (0, 2)
    positions = hist.mesh_data.get_vertices()
    assert_allclose(positions[[1, 4], 0], [2, 1])
    with pytest.raises(ValueError, match='orientation'):
        axes.histogram([0.25, 0.75], orientation='diagonal')
    recovered = axes.histogram([0.25, 0.75], bins=[0, 1, 2], orientation='h')
    assert recovered.parent is axes.view.scene
    assert recovered.bounds(1) == (0, 2)


def test_image(canvas, axes):
    data = np.zeros((12, 20, 3), dtype=np.uint8)
    data[3:9, 5:15] = (255, 0, 0)
    image = axes.image(data)
    pixels = canvas.render()
    assert_allclose(_pixel_at(pixels, image, (10, 6, 0, 1)), [255, 0, 0], atol=2)
    assert axes.camera.aspect == 1
    with pytest.raises(ValueError):
        axes.image(np.zeros((2, 2), dtype=np.float32), interpolation='bogus')
    recovered = axes.image(np.zeros((2, 2), dtype=np.float32), interpolation='nearest')
    assert recovered.parent is axes.view.scene


def test_mesh(axes):
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.array([[0, 1, 2]])
    data = MeshData(vertices=vertices, faces=faces)
    assert axes.mesh(meshdata=data, shading=None).bounds(0) == (0, 1)
    with pytest.raises(ValueError, match='meshdata'):
        axes.mesh(vertices=vertices, faces=faces, meshdata=data)
    recovered = axes.mesh(meshdata=data, shading=None)
    assert recovered.parent is axes.view.scene
    assert recovered.bounds(0) == (0, 1)


def test_plot(axes):
    line = axes.plot([0, 2, 0], color='green', symbol='o')
    assert_allclose([line.bounds(0), line.bounds(1)], [(0, 2), (0, 2)])
    xyz = axes.plot(np.array([[0, 1, 2], [2, 4, 8]]))
    assert_allclose(xyz.bounds(2), (2, 8))
    with pytest.raises(ValueError):
        axes.plot([0, 2, 0], line_kind='--')
    recovered = axes.plot([0, 2, 0], line_kind='-')
    assert axes.visuals == [line, xyz, recovered]


def test_spectrogram(canvas, axes):
    signal = np.cos(2 * np.pi * np.arange(64) / 8)
    spec = axes.spectrogram(
        signal, n_fft=32, fs=32, window=None, color_scale='linear', cmap='grays', clim=(0, 0.5)
    )
    assert spec.freqs.shape == (17,)
    assert spec.freqs[4] == 4
    pixels = canvas.render()
    assert np.all(_pixel_at(pixels, spec, (1.5, 4.5, 0, 1)) >= 245)
    assert np.all(_pixel_at(pixels, spec, (1.5, 8.5, 0, 1)) <= 5)
    with pytest.raises(ValueError):
        axes.spectrogram(np.ones((2, 32)), n_fft=32)
    recovered = axes.spectrogram(np.ones(32), n_fft=32, color_scale='linear')
    assert recovered.freqs.shape == (17,)
    assert recovered.parent is axes.view.scene


def test_surface(axes):
    surface = axes.surface(np.array([[0, 1], [1, 2]]), x=np.array([0, 3]),
                           y=np.array([0, 4]), shading=None)
    assert [surface.bounds(axis) for axis in range(3)] == [(0, 3), (0, 4), (0, 2)]
    with pytest.raises(TypeError, match='shape'):
        axes.surface(np.zeros((2, 2)), x=np.arange(3), y=np.arange(2))
    recovered = axes.surface(np.zeros((2, 2)), x=np.arange(2), y=np.arange(2))
    assert recovered.parent is axes.view.scene


def test_volume(canvas, axes):
    volume = axes.volume(np.ones((8, 8, 8), dtype=np.float32), clim=(0, 1), method='mip')
    assert volume.parent is axes.view.scene
    assert isinstance(axes.camera, TurntableCamera)
    image = canvas.render()
    assert np.all(_pixel_at(image, axes.view, (*axes.view.rect.center, 0, 1)) >= 245)
    with pytest.raises(ValueError):
        axes.volume(np.zeros((8, 8), dtype=np.float32))
    recovered = axes.volume(np.zeros((8, 8, 8), dtype=np.float32), clim=(0, 1))
    assert recovered.method == 'mip'
    assert recovered.parent is axes.view.scene
