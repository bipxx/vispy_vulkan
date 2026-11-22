"""Source acceptance for the reviewed I/O inventory cases."""

import gzip
import struct
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from vispy import config
from vispy.io import (
    datasets, imread, imsave, load_crate, load_data_file, load_iris,
    load_spatial_filters, read_mesh, read_png, write_mesh, write_png,
)
from vispy.io.stl import HeaderError, load_stl, load_stl_binary
from vispy.io.wavefront import WavefrontReader, WavefrontWriter
from vispy.util import fetching


_TRIANGLE = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
_FACE = np.array([[0, 1, 2]])
_BAD_STL = b'solid tiny\ninvalid\nendsolid tiny\n'
_RGBA = np.array([[[12, 34, 56, 78]]], dtype=np.uint8)


def _unexpected_fetch(*args, **kwargs):
    pytest.fail('A cached dataset unexpectedly attempted a network fetch')


@pytest.fixture
def dataset_cache(tmp_path, monkeypatch):
    previous = config['data_path']
    config['data_path'] = str(tmp_path)
    monkeypatch.setattr(fetching, '_fetch_file', _unexpected_fetch)
    try:
        yield tmp_path
    finally:
        config['data_path'] = previous


def test_dataset_packing():
    packed = datasets.pack_unit(np.array([0.5, 0.25]))
    assert packed.dtype == np.uint8
    assert_array_equal(packed, [[128, 0, 0, 0], [64, 0, 0, 0]])
    ieee = datasets.pack_ieee(np.array([0.5], dtype='<f4'))
    assert ieee.dtype == np.uint8
    assert_array_equal(ieee, [[0, 0, 0, 63]])
    with pytest.raises(ValueError):
        datasets.pack_ieee(np.array([0.5], dtype=np.float64))
    assert datasets.pack_ieee(np.empty(0, dtype=np.float64)).shape == (0, 4)


def test_imread_pillow_palette(tmp_path, monkeypatch):
    image = pytest.importorskip('PIL.Image')
    filename = tmp_path / 'palette.png'
    with image.new('P', (2, 1)) as fixture:
        fixture.putpalette([0, 0, 255, 255, 255, 0])
        fixture.putdata([0, 1])
        fixture.save(filename)
    monkeypatch.setitem(sys.modules, 'imageio', None)
    assert_array_equal(imread(str(filename)), [[[0, 0, 255], [255, 255, 0]]])


def test_imread_missing_dependencies(monkeypatch):
    for module in ('imageio', 'PIL', 'PIL.Image'):
        monkeypatch.setitem(sys.modules, module, None)
    with pytest.raises(RuntimeError, match='imageio or PIL'):
        imread('fixture.png')


def test_imsave_imageio_alpha(tmp_path):
    pytest.importorskip('imageio')
    image = pytest.importorskip('PIL.Image')
    filename = tmp_path / 'alpha.png'
    imsave(str(filename), _RGBA)
    with image.open(filename) as saved:
        assert saved.format == 'PNG'
        assert saved.getpixel((0, 0)) == (12, 34, 56, 78)


def test_imsave_missing_dependencies(tmp_path, monkeypatch):
    for module in ('imageio', 'PIL', 'PIL.Image'):
        monkeypatch.setitem(sys.modules, module, None)
    filename = tmp_path / 'alpha.png'
    with pytest.raises(RuntimeError, match='imageio or PIL'):
        imsave(str(filename), _RGBA)
    assert not filename.exists()


def test_load_crate(dataset_cache):
    fixture = dataset_cache / 'orig' / 'crate.npz'
    fixture.parent.mkdir()
    rgb = np.zeros((256, 256, 3), dtype=np.uint8)
    rgb[0, 0] = [17, 33, 65]
    np.savez(fixture, crate=rgb)
    result = load_crate()
    assert result.shape == (256, 256, 3)
    assert result.dtype == np.uint8
    assert_array_equal(result[0, 0], [17, 33, 65])
    np.savez(fixture, wrong=rgb)
    with pytest.raises(KeyError, match='crate'):
        load_crate()


def test_load_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fetching, '_fetch_file', _unexpected_fetch)
    cached = tmp_path / 'probe.txt'
    cached.write_bytes(b'cached')
    actual = Path(load_data_file('probe.txt', directory=tmp_path,
                                 force_download='2000-01-01'))
    assert actual == cached
    assert actual.read_bytes() == b'cached'

    attempted = []

    def fail_fetch(url, filename):
        attempted.append((url, Path(filename)))
        raise RuntimeError('offline test fixture')

    monkeypatch.setattr(fetching, '_fetch_file', fail_fetch)
    with pytest.raises(RuntimeError, match='offline test fixture'):
        load_data_file('missing.txt', directory=tmp_path)
    assert len(attempted) == 1
    assert attempted[0][0].endswith('/missing.txt')
    assert attempted[0][1] == tmp_path / 'missing.txt'
    assert not attempted[0][1].exists()


def test_load_iris(dataset_cache):
    fixture = dataset_cache / 'iris' / 'iris.npz'
    fixture.parent.mkdir()
    data = np.arange(600, dtype=float).reshape(150, 4)
    data[0] = [5.1, 3.5, 1.4, 0.2]
    group = np.repeat([0, 1, 2], 50)
    np.savez(fixture, data=data, group=group)
    with load_iris() as iris:
        assert iris['data'].shape == (150, 4)
        assert_array_equal(iris['data'][0], [5.1, 3.5, 1.4, 0.2])
        assert_array_equal(iris['group'], group)
    fixture.write_bytes(b'corrupt archive')
    with pytest.raises(ValueError):
        load_iris()
    np.savez(fixture, data=data, group=group)
    with load_iris() as iris:
        assert iris['data'][0, 0] == 5.1


def test_load_spatial_filters(tmp_path, monkeypatch):
    unpacked, names = load_spatial_filters(packed=False)
    packed, packed_names = load_spatial_filters(packed=True)
    assert unpacked.shape == (16, 1024)
    assert packed.shape == (16, 1024, 4)
    assert packed.dtype == np.uint8
    assert names[0] == 'Linear'
    assert packed_names == names
    decoded = packed[0, 512] @ (256.0 ** -np.arange(1, 5))
    assert decoded == pytest.approx(unpacked[0, 512], abs=1e-7, rel=0)
    monkeypatch.setattr(datasets, 'DATA_DIR', str(tmp_path))
    with pytest.raises(FileNotFoundError, match='spatial-filters[.]npy'):
        load_spatial_filters()


def test_read_mesh(tmp_path):
    filename = tmp_path / 'triangle.obj'
    filename.write_text('v 0 0 0\nv 2 0 0\nv 0 3 0\nf 1 2 3\n', encoding='ascii')
    vertices, faces, normals, uv = read_mesh(str(filename))
    assert_array_equal(vertices, [[0, 0, 0], [2, 0, 0], [0, 3, 0]])
    assert_array_equal(faces, _FACE)
    assert_array_equal(normals, [[0, 0, 1]] * 3)
    assert uv is None
    bad = tmp_path / 'bad.stl'
    bad.write_bytes(_BAD_STL)
    with pytest.raises(HeaderError):
        read_mesh(str(bad))


def test_read_png(tmp_path):
    image = pytest.importorskip('PIL.Image')
    pil = pytest.importorskip('PIL')
    pixels = [(12, 34, 56, 78), (90, 12, 34, 255)]
    filename = tmp_path / 'rgba.png'
    with image.new('RGBA', (2, 1)) as fixture:
        fixture.putdata(pixels)
        fixture.save(filename)
    result = read_png(str(filename))
    assert result.shape == (1, 2, 4)
    assert result.dtype == np.uint8
    assert_array_equal(result, [pixels])

    bad = tmp_path / 'corrupt.png'
    bad.write_bytes(b'\x89PNG\r\n\x1a\n')
    with pytest.raises(pil.UnidentifiedImageError):
        read_png(str(bad))


def test_stl_loaders():
    header = b'acceptance fixture'.ljust(80, b' ') + struct.pack('<I', 1)
    facet = struct.pack('<12fH', 0, 0, 1, *_TRIANGLE.ravel(), 0)
    result = load_stl_binary(BytesIO(header + facet))
    assert_array_equal(result['vertices'], _TRIANGLE)
    assert_array_equal(result['faces'], _FACE)
    assert_array_equal(result['face_normals'], [[0, 0, 1]])
    with pytest.raises(HeaderError, match='Incorrect number of values'):
        load_stl(BytesIO(_BAD_STL))


def test_wavefrontreader(tmp_path):
    filename = tmp_path / 'triangle.obj'
    filename.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n', encoding='ascii')
    vertices, faces, normals, _ = WavefrontReader.read(str(filename))
    assert_array_equal(vertices, _TRIANGLE)
    assert_array_equal(faces, _FACE)
    assert_array_equal(normals, [[0, 0, 1]] * 3)
    with pytest.raises(FileNotFoundError):
        WavefrontReader.read(str(tmp_path / 'missing.obj'))


def test_wavefrontwriter(tmp_path):
    filename = tmp_path / 'triangle.obj.gz'
    WavefrontWriter.write(str(filename), _TRIANGLE, _FACE, None, None)
    with gzip.open(filename, 'rt', encoding='ascii') as saved:
        assert [line for line in saved.read().splitlines()
                if line.startswith('f ')] == ['f 1 2 3']
    bad = tmp_path / 'triangle.txt'
    with pytest.raises(ValueError, match='Filename must end'):
        WavefrontWriter.write(str(bad), _TRIANGLE, _FACE, None, None)
    assert not bad.exists()


def test_write_mesh(tmp_path):
    filename = tmp_path / 'triangle.obj.gz'
    write_mesh(str(filename), _TRIANGLE, _FACE, None, None, format='obj')
    with gzip.open(filename, 'rt', encoding='ascii') as saved:
        assert 'f 1 2 3' in saved.read().splitlines()
    existing = tmp_path / 'triangle.obj'
    existing.write_bytes(b'keep')
    with pytest.raises(OSError):
        write_mesh(str(existing), _TRIANGLE, _FACE, None, None, overwrite=False)
    assert existing.read_bytes() == b'keep'


def test_write_png(tmp_path):
    image = pytest.importorskip('PIL.Image')
    pixels = [(12, 34, 56), (78, 90, 12)]
    filename = tmp_path / 'rgb.png'
    write_png(str(filename), np.array([pixels], dtype=np.uint8))
    with image.open(filename) as saved:
        assert saved.mode == 'RGB'
        assert [saved.getpixel((x, 0)) for x in range(2)] == pixels
    bad = tmp_path / 'float.png'
    with pytest.raises(TypeError, match='uint8'):
        write_png(str(bad), np.zeros((1, 1, 3), dtype=np.float32))
    assert not bad.exists() or bad.stat().st_size == 0
