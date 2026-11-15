# -*- coding: utf-8 -*-
"""Pure-CPU contract tests for API-05/API-06 remaining public subpackages.

Covers exports, signatures, and pure-CPU runtime contracts for:
- vispy.color
- vispy.geometry
- vispy.io
- vispy.glsl and vispy.testing
- vispy.util (keys, ptime, Quaternion, transforms, event, SimpleBunch, Frozen, svg)
- vispy.visuals.transforms
- vispy.visuals.filters (under pure-CPU FakeCanvas + _RecordingParser)
- vispy.visuals.collections and vispy.plot (exports, CPU buffer layout, documented bounds)

Portable across CPython 3.10 through 3.14 on Windows, Linux, and macOS without
GPU/backend initialization or local machine path assumptions.
"""

from contextlib import contextmanager
import gzip
import inspect
import io
import math
import struct
import warnings
import zlib

import numpy as np
import pytest

import vispy.color as vcolor
import vispy.geometry as vgeom
import vispy.glsl as vglsl
from vispy.gloo.context import (
    FakeCanvas,
    forget_canvas,
    get_current_canvas,
    set_current_canvas,
)
from vispy.gloo.glir import BaseGlirParser
import vispy.io as vio
from vispy.io.stl import HeaderError, load_stl_ascii
import vispy.plot as vplot
import vispy.testing as vtesting
import vispy.util as vutil
from vispy.util import keys as vkeys
from vispy.util import ptime as vptime
from vispy.util import svg as vsvg
from vispy.util import transforms as vutransforms
from vispy.util.bunch import SimpleBunch
from vispy.util.event import EmitterGroup, Event, EventEmitter
from vispy.util.frozen import Frozen
from vispy.util.quaternion import Quaternion
import vispy.visuals.collections as vcollections
from vispy.visuals.collections.util import dtype_reduce, fetchcode
import vispy.visuals.filters as vfilters
from vispy.visuals.filters.clipping_planes import PlanesClipper
from vispy.visuals.mesh import MeshVisual
import vispy.visuals.transforms as vtransforms
from vispy.visuals.transforms.base_transform import InverseTransform


class _RecordingParser(BaseGlirParser):
    """Pure-CPU GLIR parser recording command batches without touching Dawn."""

    def __init__(self):
        super().__init__()
        self.canvas_id = 0
        self.batches = []
        self.capabilities = dict(gl_version='CPU Contract Stub', max_texture_size=4096)

    @property
    def shader_compatibility(self):
        return 'desktop'

    def is_remote(self):
        return False

    def parse(self, commands):
        self.batches.append(list(commands))


@contextmanager
def _cpu_recording_canvas(size=(128, 96)):
    """Provide an isolated pure-CPU FakeCanvas backed by _RecordingParser."""
    prev = get_current_canvas()
    canvas = FakeCanvas()
    canvas.size = tuple(int(v) for v in size)
    canvas.physical_size = tuple(int(v) for v in size)
    parser = _RecordingParser()
    canvas.context.shared._parser = parser
    set_current_canvas(canvas)
    try:
        yield canvas, parser
    finally:
        forget_canvas(canvas)
        if prev is not None and prev is not canvas:
            set_current_canvas(prev)


# ---------------------------------------------------------------------------
# 1. vispy.color
# ---------------------------------------------------------------------------


def test_api05_subpkg_color_exports_and_signatures():
    expected = {
        'Color',
        'ColorArray',
        'Colormap',
        'BaseColormap',
        'get_colormap',
        'get_colormaps',
        'get_color_names',
        'get_color_dict',
    }
    assert expected.issubset(set(vcolor.__all__))
    for sym in expected:
        assert hasattr(vcolor, sym)

    sig_ca = inspect.signature(vcolor.ColorArray.__init__)
    assert list(sig_ca.parameters)[1:] == ['color', 'alpha', 'clip', 'color_space']
    sig_c = inspect.signature(vcolor.Color.__init__)
    assert list(sig_c.parameters)[1:] == ['color', 'alpha', 'clip']
    sig_cm = inspect.signature(vcolor.Colormap.__init__)
    assert ['colors', 'controls', 'interpolation'] == list(sig_cm.parameters)[1:4]


def test_api05_subpkg_color_spaces_lightness_and_array_ops():
    names = vcolor.get_color_names()
    cdict = vcolor.get_color_dict()
    assert isinstance(names, list) and 'red' in names and 'cornflowerblue' in names
    assert isinstance(cdict, dict) and cdict['red'].lower() == '#ff0000'

    c_red = vcolor.Color('red', alpha=0.5)
    np.testing.assert_allclose(c_red.rgba, [1.0, 0.0, 0.0, 0.5], atol=1e-6)
    np.testing.assert_allclose(c_red.rgb, [1.0, 0.0, 0.0], atol=1e-6)
    assert tuple(c_red.RGBA) == (255, 0, 0, 127)
    assert tuple(c_red.RGB) == (255, 0, 0)
    assert c_red.hex.lower() == '#ff0000'
    assert not c_red.is_blank
    assert vcolor.Color((0.2, 0.3, 0.4, 0.0)).is_blank

    # Short & 8-digit hex parsing, out-of-range validation, and clip=True.
    c_short = vcolor.Color('#0f0')
    np.testing.assert_allclose(c_short.rgba, [0.0, 1.0, 0.0, 1.0], atol=1e-6)
    c_hex8 = vcolor.Color('#ff800080')
    np.testing.assert_allclose(c_hex8.rgba, [1.0, 128.0 / 255.0, 0.0, 128.0 / 255.0], atol=1e-5)
    with pytest.raises(ValueError):
        vcolor.Color((1.5, -0.2, 0.0), clip=False)
    c_clipped = vcolor.Color((1.5, -0.2, 0.25), clip=True)
    np.testing.assert_allclose(c_clipped.rgb, [1.0, 0.0, 0.25], atol=1e-6)

    # HSV and CIE Lab roundtrips + darker/lighter copy vs in-place semantics.
    arr = vcolor.ColorArray(['#cc3366', (0.2, 0.7, 0.4, 0.8), 'royalblue'])
    assert len(arr) == 3
    orig_rgb = arr.rgb.copy()
    hsv = arr.hsv
    re_hsv = vcolor.ColorArray(hsv, color_space='hsv')
    np.testing.assert_allclose(re_hsv.rgb, orig_rgb, atol=1e-5)

    lab = arr.lab
    re_lab = arr.copy()
    re_lab.lab = lab
    np.testing.assert_allclose(re_lab.rgb, orig_rgb, atol=1e-4)

    mid = vcolor.Color((0.4, 0.2, 0.5))
    lighter = mid.lighter(0.2, copy=True)
    darker = mid.darker(0.2, copy=True)
    assert lighter is not mid and darker is not mid
    assert lighter.value > mid.value > darker.value
    in_place = mid.copy()
    ret = in_place.lighter(0.1, copy=False)
    assert ret is in_place
    assert np.isclose(in_place.value, mid.value + 0.1, atol=1e-5)

    # Indexing, extend, and 2D tuple index rejection.
    ext = arr.copy().extend(['white'])
    assert len(ext) == 4
    assert ext[3] == vcolor.ColorArray('white')
    with pytest.raises(ValueError):
        _ = ext[0, 1]


def test_api05_subpkg_colormaps_lookup_interpolation_and_bounds():
    cmaps = vcolor.get_colormaps()
    assert isinstance(cmaps, dict)
    for preset in ('viridis', 'coolwarm', 'fire', 'grays', 'cubehelix', 'hsl', 'husl', 'diverging'):
        assert preset in cmaps
        cm = vcolor.get_colormap(preset)
        assert isinstance(cm, vcolor.BaseColormap)
        assert vcolor.get_colormap(cm) is cm

    with pytest.raises(TypeError):
        vcolor.get_colormap(12345)
    with pytest.raises(KeyError):
        vcolor.get_colormap('__definitely_not_a_vispy_colormap__')

    # Linear vs zero-order step Colormap + NaN/low/high colors + LUT/GLSL generation.
    # Note: Colormap.map() checks exact x == 0 / x == 1 / isnan(x), while Colormap[x] clips to [0, 1] first.
    linear_cm = vcolor.Colormap(
        ['black', 'red', 'white'],
        controls=[0.0, 0.5, 1.0],
        interpolation='linear',
        bad_color=(0.0, 1.0, 0.0, 0.25),
        low_color=(0.0, 0.0, 1.0, 1.0),
        high_color=(1.0, 1.0, 0.0, 1.0),
    )
    probe = np.array([0.0, 0.25, 0.5, 1.0, np.nan], dtype=np.float32)
    mapped = linear_cm.map(probe)
    assert mapped.shape == (5, 4)
    np.testing.assert_allclose(mapped[0], [0.0, 0.0, 1.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(mapped[1], [0.5, 0.0, 0.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(mapped[2], [1.0, 0.0, 0.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(mapped[3], [1.0, 1.0, 0.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(mapped[4], [0.0, 1.0, 0.0, 0.25], atol=1e-5)
    clipped_arr = linear_cm[[-0.5, 1.5]]
    np.testing.assert_allclose(clipped_arr.rgba[0], [0.0, 0.0, 1.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(clipped_arr.rgba[1], [1.0, 1.0, 0.0, 1.0], atol=1e-5)
    assert 'vec4 colormap(float t)' in linear_cm.glsl_map
    with _cpu_recording_canvas():
        lut = linear_cm.texture_lut()
        assert lut is not None and len(lut.shape) >= 2 and lut.shape[0] > 0

    step_cm = vcolor.Colormap(
        [(1.0, 0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0)],
        controls=[0.0, 0.5, 1.0],
        interpolation='zero',
    )
    step_out = step_cm.map(np.array([0.2, 0.8], dtype=np.float32))
    np.testing.assert_allclose(step_out[0], [1.0, 0.0, 0.0, 1.0], atol=1e-6)
    np.testing.assert_allclose(step_out[1], [0.0, 0.0, 1.0, 1.0], atol=1e-6)


# ---------------------------------------------------------------------------
# 2. vispy.geometry
# ---------------------------------------------------------------------------


def test_api05_subpkg_geometry_exports_rect_and_triangulation():
    expected = {
        'MeshData',
        'PolygonData',
        'Rect',
        'Triangulation',
        'triangulate',
        'create_arrow',
        'create_box',
        'create_cone',
        'create_cube',
        'create_cylinder',
        'create_grid_mesh',
        'create_plane',
        'create_sphere',
        'resize',
    }
    assert expected == set(vgeom.__all__)

    # Rect constructors, transforms, normalization, padding, flipping, containment.
    r0 = vgeom.Rect(10, 20, 30, 40)
    assert r0 == vgeom.Rect((10, 20), (30, 40))
    assert r0 == vgeom.Rect([10, 20, 30, 40])
    assert r0 == vgeom.Rect(r0)
    assert (r0.left, r0.bottom, r0.right, r0.top) == (10, 20, 40, 60)
    assert r0.center == (25.0, 40.0)
    assert r0.contains(25, 40) and not r0.contains(5, 40)
    assert r0.padded(5) == vgeom.Rect(15, 25, 20, 30)
    flipped = r0.flipped(x=True, y=True)
    assert flipped.normalized() == r0
    shifted = r0 + (3, -4)
    assert shifted == vgeom.Rect(13, 16, 30, 40)

    # Concave L-polygon triangulation via triangulate() (3D vertices), Triangulation (2D), and PolygonData (2D).
    l_poly_2d = np.array(
        [[0.0, 0.0], [4.0, 0.0], [4.0, 1.0], [1.0, 1.0], [1.0, 3.0], [0.0, 3.0]],
        dtype=np.float32,
    )
    l_poly_3d = np.column_stack([l_poly_2d, np.zeros(len(l_poly_2d), dtype=np.float32)])
    pts, tris = vgeom.triangulate(l_poly_3d)
    assert pts.ndim == 2 and pts.shape[1] == 3
    assert tris.ndim == 1 and len(tris) >= 12 and len(tris) % 3 == 0
    assert int(tris.min()) >= 0 and int(tris.max()) < len(pts)

    edges = np.array([[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0]], dtype=np.int32)
    tri_obj = vgeom.Triangulation(l_poly_2d, edges)
    tri_obj.triangulate()
    assert tri_obj.tris.ndim == 2 and tri_obj.tris.shape[1] == 3 and len(tri_obj.tris) >= 4

    pd = vgeom.PolygonData(vertices=l_poly_2d)
    pd_pts, pd_tris = pd.triangulate()
    assert pd_tris.shape[1] == 3 and len(pd_pts) >= 6
    with pytest.raises(NotImplementedError):
        pd.add_vertex([2.0, 2.0])


def test_api05_subpkg_geometry_meshdata_generators_and_resize():
    # MeshData roundtrip, normals, edges, bounds, colors/values.
    verts = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float32,
    )
    faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.uint32)
    md = vgeom.MeshData(vertices=verts, faces=faces)
    assert not md.is_empty()
    assert md.get_vertices().shape == (4, 3)
    assert md.get_vertices(indexed='faces').shape == (4, 3, 3)
    assert md.get_faces().shape == (4, 3)
    assert md.get_edges().shape == (6, 2)
    assert md.get_face_normals().shape == (4, 3)
    assert md.get_vertex_normals().shape == (4, 3)
    bounds = md.get_bounds()
    assert len(bounds) == 3 and bounds[0] == (0.0, 1.0)

    md.set_vertex_colors(np.ones((4, 3), dtype=np.float32) * 0.5)
    assert md.get_vertex_colors().shape == (4, 4)  # auto-padded alpha=1
    md.set_face_colors(np.ones((4, 4), dtype=np.float32) * 0.25)
    assert md.get_face_colors().shape == (4, 4)
    md.set_vertex_values(np.arange(4, dtype=np.float32))
    np.testing.assert_allclose(md.get_vertex_values(), [0.0, 1.0, 2.0, 3.0])

    state = md.save()
    restored = vgeom.MeshData()
    restored.restore(state)
    np.testing.assert_allclose(restored.get_vertices(), md.get_vertices())
    np.testing.assert_array_equal(restored.get_faces(), md.get_faces())

    # Mesh generators.
    v_box, f_box, o_box = vgeom.create_box(2.0, 3.0, 4.0, 2, 2, 2)
    assert v_box['position'].shape[1] == 3 and f_box.shape[1] == 3 and o_box.shape[1] == 2
    v_plane, f_plane, o_plane = vgeom.create_plane(2.0, 4.0, 2, 3, direction='+y')
    assert len(v_plane) == 12 and len(f_plane) == 12 and o_plane.shape[1] == 2
    v_cube, f_cube, o_cube = vgeom.create_cube()
    assert len(v_cube) == 24 and f_cube.shape == (12, 3) and len(o_cube) == 48

    for method in ('latitude', 'ico', 'cube'):
        sph = vgeom.create_sphere(rows=6, cols=8, depth=4, radius=2.5, subdivisions=1, method=method)
        radii = np.linalg.norm(sph.get_vertices(), axis=1)
        np.testing.assert_allclose(radii, 2.5, atol=1e-4)

    cyl = vgeom.create_cylinder(4, 8, radius=[1.0, 0.5], length=3.0)
    assert cyl.get_vertices().shape == (40, 3) and cyl.get_faces().shape == (64, 3)
    cone = vgeom.create_cone(8, radius=1.5, length=2.0)
    assert cone.get_vertices().shape == (9, 3) and cone.get_faces().shape == (8, 3)
    arrow = vgeom.create_arrow(3, 8, radius=0.2, length=3.0)
    assert arrow.get_vertices().shape[1] == 3 and arrow.get_faces().shape[1] == 3

    xs, ys = np.meshgrid(np.linspace(0.0, 1.0, 4), np.linspace(0.0, 2.0, 3))
    zs = xs + ys
    gv, gi = vgeom.create_grid_mesh(xs, ys, zs)
    assert gv.shape == (12, 3) and gi.shape == (12, 3)

    img = np.arange(4 * 6 * 3, dtype=np.uint8).reshape(4, 6, 3)
    resized = vgeom.resize(img, (8, 12))
    assert resized.shape == (8, 12, 3) and np.issubdtype(resized.dtype, np.floating)
    np.testing.assert_allclose(resized[0, 0], img[0, 0], atol=1e-6)
    np.testing.assert_allclose(resized[-1, -1], img[-1, -1], atol=1e-6)


# ---------------------------------------------------------------------------
# 3. vispy.io
# ---------------------------------------------------------------------------


def _parse_png_chunks(raw_bytes):
    assert raw_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    chunks = []
    while pos < len(raw_bytes):
        length = struct.unpack('>I', raw_bytes[pos : pos + 4])[0]
        ctype = raw_bytes[pos + 4 : pos + 8]
        cdata = raw_bytes[pos + 8 : pos + 8 + length]
        crc = struct.unpack('>I', raw_bytes[pos + 8 + length : pos + 12 + length])[0]
        expected_crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        assert crc == expected_crc
        chunks.append((ctype, cdata))
        pos += 12 + length
    return chunks


def test_api05_subpkg_io_png_image_mesh_and_offline_bounds(tmp_path):
    expected = {
        'imread',
        'imsave',
        'load_iris',
        'load_crate',
        'load_spatial_filters',
        'load_data_file',
        'read_mesh',
        'read_png',
        'write_mesh',
        'write_png',
    }
    assert expected == set(vio.__all__)
    # Internal pure-Python PNG encoder is exposed as _make_png (no public make_png alias).
    assert hasattr(vio, '_make_png') and callable(vio._make_png)
    assert not hasattr(vio, 'make_png')

    # _make_png requires 3D (H, W, 3 | 4) uint8 arrays; 2D raises IndexError.
    for shape in ((6, 8, 3), (6, 8, 4)):
        arr = np.arange(int(np.prod(shape)), dtype=np.uint8).reshape(shape)
        png_bytes = vio._make_png(arr).tobytes()
        chunks = _parse_png_chunks(png_bytes)
        assert [c[0] for c in chunks] == [b'IHDR', b'IDAT', b'IEND']

    with pytest.raises(IndexError):
        vio._make_png(np.zeros((6, 8), dtype=np.uint8))
    with pytest.raises(TypeError):
        vio._make_png(np.zeros((4, 4, 2), dtype=np.uint8))
    with pytest.raises(TypeError):
        vio._make_png(np.zeros((4, 4, 3), dtype=np.float32))

    # Lossless RGBA & RGB PNG file roundtrip via write_png/read_png and imsave/imread.
    rgba = np.zeros((10, 12, 4), dtype=np.uint8)
    rgba[..., 0] = np.arange(10, dtype=np.uint8)[:, None] * 20
    rgba[..., 1] = np.arange(12, dtype=np.uint8)[None, :] * 15
    rgba[..., 2] = 173
    rgba[..., 3] = 251
    png_path = tmp_path / 'roundtrip_rgba.png'
    vio.write_png(str(png_path), rgba)
    loaded_rgba = vio.read_png(str(png_path))
    np.testing.assert_array_equal(loaded_rgba, rgba)

    rgb = rgba[..., :3].copy()
    imsave_path = tmp_path / 'roundtrip_rgb.png'
    vio.imsave(str(imsave_path), rgb, format='png')
    loaded_rgb = vio.imread(str(imsave_path))
    np.testing.assert_array_equal(loaded_rgb[..., :3], rgb)

    # Wavefront OBJ and OBJ.GZ roundtrips in tmp_path.
    m_verts = np.array(
        [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 4.0]],
        dtype=np.float32,
    )
    m_faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    m_normals = np.array(
        [[0.0, 0.0, 1.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    m_tex = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)

    obj_path = tmp_path / 'mesh.obj'
    vio.write_mesh(str(obj_path), m_verts, m_faces, m_normals, m_tex, name='tetra_part', format='obj')
    rv, rf, rn, rt = vio.read_mesh(str(obj_path))
    np.testing.assert_allclose(rv, m_verts, atol=1e-5)
    np.testing.assert_array_equal(rf, m_faces)
    assert rn.shape == (4, 3)
    np.testing.assert_allclose(rt, m_tex, atol=1e-5)

    obj_gz_path = tmp_path / 'mesh.obj.gz'
    with gzip.open(obj_gz_path, 'wb') as gz_f:
        gz_f.write(obj_path.read_bytes())
    gz_v, gz_f_idx, _, _ = vio.read_mesh(str(obj_gz_path))
    np.testing.assert_allclose(gz_v, m_verts, atol=1e-5)
    np.testing.assert_array_equal(gz_f_idx, m_faces)

    # STL reader/writer truthful bounds:
    # 1. load_stl_ascii parses valid ASCII STL facets directly.
    ascii_stl = (
        b'solid tri\n'
        b'facet normal 0 0 1\n'
        b'  outer loop\n'
        b'    vertex 0 0 0\n'
        b'    vertex 1 0 0\n'
        b'    vertex 0 1 0\n'
        b'  endloop\n'
        b'endfacet\n'
        b'endsolid tri\n'
    )
    stl_dict = load_stl_ascii(io.BytesIO(ascii_stl))
    np.testing.assert_allclose(stl_dict['vertices'], [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    np.testing.assert_array_equal(stl_dict['faces'], [[0, 1, 2]])
    # Compact (<84-byte) ASCII STL bypasses binary 84-byte header unpack in load_stl() across all NumPy versions!
    compact_stl = b'solid s\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 2 0 0\nvertex 0 2 0\nendloop\nendfacet\nendsolid s\n'
    assert len(compact_stl) > 84
    short_stl_file = tmp_path / 'short.stl'
    # A <84-byte malformed STL raises HeaderError cleanly without calling removed np.fromstring binary mode.
    short_stl_file.write_bytes(b'solid tiny\ninvalid\nendsolid tiny\n')
    with pytest.raises(HeaderError):
        vio.read_mesh(str(short_stl_file))

    # Full >=84-byte binary STL hits np.fromstring(bytes, dtype=...) in upstream stl.py:
    # on NumPy >= 2.3 this raises ValueError; on NumPy < 2.3 (e.g. 2.2.x on Python 3.10) it warns and returns the mesh.
    bin_stl_path = tmp_path / 'single_tri.stl'
    bin_header = b'vispy binary stl'.ljust(80, b'\x00') + struct.pack('<I', 1)
    bin_tri = struct.pack(
        '<12fH',
        0.0, 0.0, 1.0,
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0,
    )
    bin_stl_path.write_bytes(bin_header + bin_tri)
    np_ver = tuple(
        int(''.join(ch for ch in part if ch.isdigit()) or '0')
        for part in np.__version__.split('.')[:2]
    )
    if np_ver >= (2, 3):
        with pytest.raises(ValueError, match='fromstring'):
            vio.read_mesh(str(bin_stl_path))
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            bv, bf, bn, _ = vio.read_mesh(str(bin_stl_path))
        np.testing.assert_allclose(bv, [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        np.testing.assert_array_equal(bf, [[0, 1, 2]])
        assert bn.shape == (1, 3)

    # Bundled offline dataset works without network; uncached load_data_file fails closed offline.
    kernels, filter_names = vio.load_spatial_filters()
    assert kernels.shape == (16, 1024, 4) and len(filter_names) == 17 and 'Nearest' in filter_names

    local_npy = tmp_path / 'local_probe.npy'
    np.save(local_npy, np.array([3, 1, 4], dtype=np.int32))
    resolved = vio.load_data_file('local_probe.npy', directory=str(tmp_path), force_download=False)
    np.testing.assert_array_equal(np.load(resolved), [3, 1, 4])

    with pytest.raises(RuntimeError):
        vio.load_data_file(
            '__missing_untracked_vispy_demo_file__.npy',
            directory=str(tmp_path),
            force_download=False,
        )


# ---------------------------------------------------------------------------
# 4. vispy.glsl & vispy.testing
# ---------------------------------------------------------------------------


def test_api05_subpkg_glsl_and_testing_contracts():
    assert not hasattr(vglsl, '__all__')
    assert callable(vglsl.get) and callable(vglsl.find)
    found = vglsl.find('collections/raw-triangle.vert')
    assert found is not None and found.endswith('raw-triangle.vert')
    assert vglsl.find('nonexistent/does-not-exist.glsl') is None

    agg_frag = vglsl.get('collections/agg-point.frag')
    # #include directives ("markers/disc.glsl", "antialias/filled.glsl") must be expanded inline.
    assert 'marker_disc' in agg_frag and 'filled(' in agg_frag
    with pytest.raises(RuntimeError):
        vglsl.get('nonexistent/does-not-exist.glsl')

    # vispy.testing assertion helpers and environment predicates.
    marker = object()
    vtesting.assert_is(marker, marker)
    vtesting.assert_in('b', ['a', 'b', 'c'])
    vtesting.assert_not_in('z', ['a', 'b', 'c'])
    vtesting.assert_equal(42, 42)
    vtesting.assert_not_equal(42, 43)
    vtesting.assert_true(True)
    vtesting.assert_raises(ZeroDivisionError, lambda: 1 / 0)
    with vtesting.raises(KeyError):
        _ = {}['missing']
    with pytest.raises(AssertionError):
        vtesting.assert_equal(1, 2)

    from vispy.testing._testing import nottest

    @nottest
    def _helper_not_a_test():
        return 7

    assert _helper_not_a_test.__test__ is False
    assert _helper_not_a_test() == 7
    assert callable(vtesting.test)
    assert isinstance(vtesting.IS_CI, bool)
    assert isinstance(vtesting.has_pyopengl(), bool)
    with pytest.raises(BaseException):
        raise vtesting.SkipTest('contract skip check')


# ---------------------------------------------------------------------------
# 5. vispy.util
# ---------------------------------------------------------------------------


def test_api05_subpkg_util_keys_ptime_quaternion_and_transforms():
    # keys
    assert vkeys.SPACE == 'space' and vkeys.SPACE == ' ' and vkeys.SPACE == 32
    assert vkeys.ENTER == 'Return' and vkeys.ENTER == '\n'
    assert vkeys.ESCAPE == 'escape' and vkeys.ESCAPE != None  # noqa: E711
    key_a = vkeys.Key('A')
    assert key_a == 'a' and key_a == 65
    with pytest.raises(ValueError):
        _ = vkeys.SHIFT == 3.14

    # ptime
    t0 = vptime.time()
    t1 = vptime.time()
    assert isinstance(t0, float) and t1 >= t0

    # Quaternion
    with pytest.raises(ValueError):
        Quaternion(0, 0, 0, 0, normalize=True)
    q_z90 = Quaternion.create_from_axis_angle(90.0, 0.0, 0.0, 1.0, degrees=True)
    assert math.isclose(q_z90.norm(), 1.0, rel_tol=1e-6)
    rx, ry, rz = q_z90.rotate_point((1.0, 0.0, 0.0))
    np.testing.assert_allclose([rx, ry, rz], [0.0, 1.0, 0.0], atol=1e-6)
    angle, ax, ay, az = q_z90.get_axis_angle()
    np.testing.assert_allclose([angle, ax, ay, az], [math.pi / 2.0, 0.0, 0.0, 1.0], atol=1e-6)
    q_id = q_z90 * q_z90.inverse()
    np.testing.assert_allclose([q_id.w, q_id.x, q_id.y, q_id.z], [1.0, 0.0, 0.0, 0.0], atol=1e-6)
    q_mat = q_z90.get_matrix()
    assert q_mat.shape == (4, 4)
    q_euler = Quaternion.create_from_euler_angles(0.0, 0.0, 90.0, degrees=True)
    assert math.isclose(q_euler.norm(), 1.0, rel_tol=1e-6)

    # util.transforms (row-vector convention used by VisPy examples/cameras)
    m_tr = vutransforms.translate((2.0, -3.0, 5.0), dtype=np.float32)
    np.testing.assert_allclose(np.array([1.0, 2.0, 3.0, 1.0]) @ m_tr, [3.0, -1.0, 8.0, 1.0], atol=1e-6)
    m_sc = vutransforms.scale((2.0, 3.0, 4.0), dtype=np.float32)
    np.testing.assert_allclose(np.diag(m_sc), [2.0, 3.0, 4.0, 1.0], atol=1e-6)
    m_rot = vutransforms.rotate(90.0, np.array([0.0, 0.0, 1.0]), dtype=np.float32)
    np.testing.assert_allclose(np.array([1.0, 0.0, 0.0, 1.0]) @ m_rot, [0.0, 1.0, 0.0, 1.0], atol=1e-6)
    m_ortho = vutransforms.ortho(-1.0, 1.0, -1.0, 1.0, 1.0, 10.0)
    m_persp = vutransforms.perspective(45.0, 4.0 / 3.0, 0.1, 100.0)
    assert m_ortho.shape == (4, 4) and m_persp.shape == (4, 4)

    p1 = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
    p2 = p1 * 2.0 + np.array([5.0, -2.0, 1.0])
    aff = vutransforms.affine_map(p1, p2)
    mapped_h = (aff @ np.hstack([p1, np.ones((4, 1))]).T).T
    np.testing.assert_allclose(mapped_h[:, :3], p2, atol=1e-6)


def test_api05_subpkg_util_events_bunch_frozen_and_svg(tmp_path):
    # Event / EventEmitter / EmitterGroup (source uses weakref.ref when non-None)
    class _SourceObj:
        pass

    src_obj = _SourceObj()
    with pytest.raises(TypeError):
        EmitterGroup(source='non_weakrefable_str', alpha=Event)

    log = []
    group = EmitterGroup(source=src_obj, alpha=Event, beta=Event)
    group.alpha.connect(lambda ev: log.append(('alpha', ev.type, ev.source)))
    group.beta.connect(lambda ev: log.append(('beta', getattr(ev, 'value', None))))
    group.alpha()
    group.beta(value=99)
    with group.alpha.blocker():
        group.alpha()
    assert log == [('alpha', 'alpha', src_obj), ('beta', 99)]

    em = EventEmitter(type='tick')
    cb = lambda ev: log.append(ev.type)  # noqa: E731
    em.connect(cb)
    em()
    em.disconnect(cb)
    em()
    assert log[-1] == 'tick' and len(log) == 3

    # SimpleBunch & Frozen
    bunch = SimpleBunch(x=10, label='demo')
    assert bunch.x == 10 and bunch['label'] == 'demo'
    bunch.y = 20
    assert bunch['y'] == 20

    class _LockedConfig(Frozen):
        def __init__(self):
            self.allowed = 1
            self.freeze()

    locked = _LockedConfig()
    locked.allowed = 2
    assert locked.allowed == 2
    with pytest.raises(AttributeError):
        locked.forbidden = 3

    assert hasattr(vutil, 'use_log_level')

    # SVG Document parser & XML roundtrip (two <path> elements inside a transformed <g>)
    svg_file = tmp_path / 'sample.svg'
    svg_file.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="200px" height="100px" viewBox="0 0 200 100">\n'
        '  <g id="layer1" transform="translate(10, 20)">\n'
        '    <path id="p1" d="M 0 0 L 50 0 L 50 40 Z" style="fill:#ff0000;stroke:#000000"/>\n'
        '    <path id="p2" d="M 5 10 L 35 10 L 35 30 L 5 30 Z" style="fill:#00ff00"/>\n'
        '  </g>\n'
        '</svg>\n',
        encoding='utf-8',
    )
    doc = vsvg.Document(str(svg_file))
    assert isinstance(doc, vsvg.SVG)
    assert len(doc.paths) >= 2
    assert '<svg ' in doc.xml

    bad_xml = tmp_path / 'not_svg.xml'
    bad_xml.write_text('<html/>', encoding='utf-8')
    with pytest.raises(TypeError):
        vsvg.Document(str(bad_xml))


# ---------------------------------------------------------------------------
# 6. vispy.visuals.transforms
# ---------------------------------------------------------------------------


def test_api05_subpkg_transforms_cpu_map_imap_shaders_and_system():
    expected = {
        'NullTransform',
        'STTransform',
        'MatrixTransform',
        'LogTransform',
        'PolarTransform',
        'ChainTransform',
        'TransformSystem',
        'PanZoomTransform',
    }
    assert expected == set(vtransforms.__all__)
    # Reconcile naming: VisPy provides arg_to_array / arg_to_vec4 decorators and
    # _transform_in / _transform_out Rect protocol rather than an "ArgTransform" class.
    assert not hasattr(vtransforms, 'ArgTransform')
    assert callable(vtransforms.arg_to_array) and callable(vtransforms.arg_to_vec4)
    assert isinstance(vtransforms.NullTransform().inverse, InverseTransform)

    pts = np.array([[2.0, 4.0, 1.0], [8.0, 16.0, 2.0]], dtype=np.float64)

    # NullTransform
    nt = vtransforms.NullTransform()
    np.testing.assert_allclose(nt.map(pts)[:, :3], pts)
    np.testing.assert_allclose(nt.imap(pts)[:, :3], pts)

    # STTransform (including Rect mapping via _transform_in/_transform_out)
    st = vtransforms.STTransform(scale=(2.0, 0.5, 3.0), translate=(10.0, -4.0, 1.0))
    st_mapped = st.map(pts)
    np.testing.assert_allclose(st_mapped[:, :3], [[14.0, -2.0, 4.0], [26.0, 4.0, 7.0]])
    np.testing.assert_allclose(st.imap(st_mapped)[:, :3], pts, atol=1e-6)
    rect_mapped = st.map(vgeom.Rect(0, 0, 10, 20))
    assert isinstance(rect_mapped, vgeom.Rect) and rect_mapped == vgeom.Rect(10, -4, 20, 10)
    assert 'st_transform_map' in st.shader_map().compile()

    # MatrixTransform
    mt = vtransforms.MatrixTransform()
    mt.scale((2.0, 3.0, 1.0))
    mt.translate((5.0, -1.0, 0.0))
    mt_mapped = mt.map(pts)
    np.testing.assert_allclose(mt.imap(mt_mapped)[:, :3], pts, atol=1e-5)
    assert 'affine_transform_map' in mt.shader_map().compile()

    # PolarTransform: map((theta, r, z)) -> (r*cos(theta), r*sin(theta), z)
    # Note upstream PolarTransform.imap uses arctan2(x, y); verify exact map + shader_map!
    polar = vtransforms.PolarTransform()
    polar_in = np.array([[0.0, 5.0, 2.0], [math.pi / 2.0, 3.0, -1.0]], dtype=np.float64)
    polar_out = polar.map(polar_in)
    np.testing.assert_allclose(polar_out, [[5.0, 0.0, 2.0], [0.0, 3.0, -1.0]], atol=1e-6)
    assert 'polar_transform_map' in polar.shader_map().compile()

    # LogTransform: forward CPU map + GLSL shader_map/shader_imap uniform sign inversion.
    # Note upstream LogTransform._map(..., base=-self.base) evaluates `-base[i] ** coords[..., i]`
    # (`(-10.0) ** float_array`), producing NaN in NumPy float power on CPU imap when base > 1;
    # GPU shader_imap passes `-base` into GLSL `pow(-$base.x, pos.x)` cleanly.
    log_tr = vtransforms.LogTransform(base=(10.0, 2.0, 0.0))
    log_in = np.array([[100.0, 8.0, 7.0], [1000.0, 16.0, -3.0]], dtype=np.float64)
    log_out = log_tr.map(log_in)
    np.testing.assert_allclose(log_out, [[2.0, 3.0, 7.0], [3.0, 4.0, -3.0]], atol=1e-6)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        imap_probe = log_tr.imap(log_out)
    assert np.isnan(imap_probe[:, :2]).all()
    np.testing.assert_allclose(imap_probe[:, 2], [7.0, -3.0], atol=1e-6)
    assert 'LogTransform_map' in log_tr.shader_map().compile()
    assert 'LogTransform_map' in log_tr.shader_imap().compile()

    # ChainTransform: chain = ChainTransform([st, log_tr]) maps log_tr first, then st;
    # invertible linear ChainTransform([st, mt]) roundtrips both .map and .imap cleanly.
    chain = vtransforms.ChainTransform([st, log_tr])
    np.testing.assert_allclose(chain.map(log_in), st.map(log_tr.map(log_in)), atol=1e-6)
    assert 'transform_map_chain' in chain.shader_map().compile()
    chain_lin = vtransforms.ChainTransform([st, mt])
    np.testing.assert_allclose(chain_lin.map(pts), st.map(mt.map(pts)), atol=1e-6)
    np.testing.assert_allclose(chain_lin.imap(chain_lin.map(pts))[:, :3], pts, atol=1e-5)

    # TransformSystem on pure-CPU stub canvas
    with _cpu_recording_canvas(size=(200, 100)) as (canvas, _parser):
        ts = vtransforms.TransformSystem(canvas=canvas, dpi=96.0)
        ts.configure()
        assert ts.dpi == 96.0
        full = ts.get_transform('visual', 'render')
        # Top-left (0, 0) maps to NDC (-1, +1); bottom-right (200, 100) maps to (+1, -1).
        corners = full.map(np.array([[0.0, 0.0], [200.0, 100.0]], dtype=np.float32))
        np.testing.assert_allclose(corners[:, :2], [[-1.0, 1.0], [1.0, -1.0]], atol=1e-5)


# ---------------------------------------------------------------------------
# 7. vispy.visuals.filters
# ---------------------------------------------------------------------------


def test_api05_subpkg_filters_exports_and_cpu_attach_detach():
    expected = {
        'Filter',
        'PrimitivePickingFilter',
        'Clipper',
        'Alpha',
        'ColorFilter',
        'IsolineFilter',
        'ZColormapFilter',
        'PickingFilter',
        'MarkerPickingFilter',
        'TextureFilter',
        'ShadingFilter',
        'InstancedShadingFilter',
        'WireframeFilter',
        'FacePickingFilter',
    }
    assert expected.issubset(set(dir(vfilters)))
    # Reconcile naming: VisPy exports ZColormapFilter (not "ZBufferFilter"), and PlanesClipper
    # lives in vispy.visuals.filters.clipping_planes.
    assert not hasattr(vfilters, 'ZBufferFilter')
    assert issubclass(PlanesClipper, vfilters.Filter)

    with _cpu_recording_canvas(size=(64, 64)):
        verts = np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 1.0]],
            dtype=np.float32,
        )
        faces = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
        mesh = MeshVisual(vertices=verts, faces=faces, color='white', shading=None)

        f_alpha = vfilters.Alpha(0.35)
        f_color = vfilters.ColorFilter((0.2, 0.4, 0.8, 1.0))
        f_clip = vfilters.Clipper(bounds=(4, 8, 32, 24))
        f_planes = PlanesClipper(
            np.array([[[0.25, 0.0, 0.0], [1.0, 0.0, 0.0]]], dtype=np.float32),
            coord_system='visual',
        )
        f_pick = vfilters.PickingFilter(id_=0x01020304)
        f_wire = vfilters.WireframeFilter(color='red', width=2.0, wireframe_only=False)
        f_iso = vfilters.IsolineFilter(level=4.0, width=1.5, color='yellow')
        f_tex = vfilters.TextureFilter(
            texture=np.ones((4, 4, 4), dtype=np.float32),
            texcoords=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32),
            enabled=True,
        )
        f_shade = vfilters.ShadingFilter(shading='smooth', shininess=32.0)

        with pytest.raises(ValueError):
            f_pick.id = 0
        with pytest.raises(ValueError):
            f_wire.width = -1.0
        # Upstream IsolineFilter.level clamps non-positive values to 0 rather than raising.
        f_iso.level = -2.0
        assert f_iso.level == 0
        f_iso.level = 4.0

        all_filters = [f_alpha, f_color, f_clip, f_planes, f_pick, f_wire, f_iso, f_tex, f_shade]
        for flt in all_filters:
            assert not flt.attached
            mesh.attach(flt)
            assert flt.attached

        # Mutate properties while attached and verify state updates cleanly on CPU.
        f_alpha.alpha = 0.75
        assert f_alpha.alpha == 0.75
        f_color.filter = (1.0, 0.5, 0.25, 1.0)
        assert f_color.filter == (1.0, 0.5, 0.25, 1.0)
        f_clip.bounds = (0, 0, 16, 16)
        assert f_clip.bounds == vgeom.Rect(0, 0, 16, 16)
        f_pick.enabled = True
        assert f_pick.enabled is True and f_pick.color == (4, 3, 2, 1)
        f_wire.wireframe_only = True
        assert f_wire.wireframe_only is True and f_wire._bc_face_count == 2
        f_iso.level = 8.0
        assert f_iso.level == 8.0
        f_tex.enabled = False
        assert f_tex.enabled is False
        f_shade.shading = 'flat'
        assert f_shade.shading == 'flat'

        for flt in reversed(all_filters):
            mesh.detach(flt)
            assert not flt.attached


# ---------------------------------------------------------------------------
# 8. vispy.visuals.collections & vispy.plot
# ---------------------------------------------------------------------------


def test_api05_subpkg_collections_and_plot_cpu_contracts():
    expected_collections = {
        'PointCollection',
        'PathCollection',
        'PolygonCollection',
        'SegmentCollection',
        'TriangleCollection',
    }
    assert not hasattr(vcollections, '__all__')
    for cls_name in expected_collections:
        assert callable(getattr(vcollections, cls_name, None)), cls_name

    # dtype_reduce & fetchcode pure-CPU GLSL uniform fetcher generation.
    utype = np.dtype([('color', np.float32, 4), ('linewidth', np.float32, 1)])
    reduced = dtype_reduce(utype, level=1)
    assert ['color', 4, 'float32'] in reduced
    glsl_fetch = fetchcode(utype)
    assert 'void fetch_uniforms()' in glsl_fetch
    assert 'uniform   sampler2D uniforms;' in glsl_fetch

    with _cpu_recording_canvas(size=(128, 128)):
        # PointCollection (raw: itemsize=1 -> 1 item per point; agg: 4-vertex quad per point -> 1 item per append)
        pc_raw = vcollections.PointCollection(mode='raw', color='local')
        pc_raw.append(
            np.array([[-0.5, 0.0, 0.0], [0.5, 0.0, 0.0]], dtype=np.float32),
            color=(1.0, 1.0, 0.0, 1.0),
            size=6.0,
        )
        assert len(pc_raw) == 2 and pc_raw[0].vertices.size == 1

        pc_agg = vcollections.PointCollection(mode='agg', color='shared')
        pc_agg.append(np.zeros((3, 3), dtype=np.float32), color=(1.0, 0.0, 0.0, 1.0), size=8.0)
        assert len(pc_agg) == 3 and pc_agg.utype is not None

        # SegmentCollection: mode='agg' constructs & appends 4-vertex quad segments cleanly;
        # upstream RawSegmentCollection.append (mode='raw') hits Python 3 float division
        # `itemcount = len(P0) / itemsize` passed to `np.empty(itemcount * itemsize, ...)`.
        sc_raw = vcollections.SegmentCollection(mode='raw')
        with pytest.raises(TypeError):
            sc_raw.append(
                np.array([[-0.5, -0.5, 0.0]], dtype=np.float32),
                np.array([[0.5, 0.5, 0.0]], dtype=np.float32),
            )

        sc_agg = vcollections.SegmentCollection(mode='agg')
        sc_agg.append(
            np.array([[-0.8, 0.0, 0.0]], dtype=np.float32),
            np.array([[0.8, 0.0, 0.0]], dtype=np.float32),
            linewidth=4.0,
        )
        assert len(sc_agg) == 1 and sc_agg[0].vertices.size == 4

        # TriangleCollection & PolygonCollection
        tc = vcollections.TriangleCollection(mode='raw')
        tc.append(
            np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [0.0, 0.5, 0.0]], dtype=np.float32),
            np.array([[0, 1, 2]], dtype=np.uint32),
        )
        assert len(tc) == 1 and tc[0].indices.size == 3

        poly_c = vcollections.PolygonCollection(mode='raw')
        poly_c.append(
            np.array([[-0.5, -0.5, 0.0], [0.5, -0.5, 0.0], [0.5, 0.5, 0.0], [-0.5, 0.5, 0.0]], dtype=np.float32),
            color=(0.0, 1.0, 0.0, 1.0),
        )
        assert len(poly_c) == 1 and poly_c[0].indices.size >= 6

        # PathCollection: 'agg' (default) and 'agg+' construct, append, and delete items cleanly;
        # upstream RawPathCollection (mode='raw') fails in __init__ (`NullTransform() + str`).
        with pytest.raises(TypeError):
            vcollections.PathCollection(mode='raw')
        path_pts = np.array([[-0.6, -0.2, 0.0], [0.0, 0.4, 0.0], [0.6, -0.2, 0.0]], dtype=np.float32)
        for mode in ('agg', 'agg+'):
            path_c = vcollections.PathCollection(mode=mode)
            path_c.append(path_pts, closed=False)
            assert len(path_c) == 1
            del path_c[0]
            assert len(path_c) == 0

    # vispy.plot exports and method reconciliation (without opening a GPU SceneCanvas):
    # - Fig and PlotWidget are the primary plot classes; there is NO class named "SubPlot"
    #   (Fig[row, col] indexes self._grid whose _default_class is PlotWidget).
    # - PlotWidget provides histogram, image, mesh, plot, spectrogram, volume, surface, colorbar;
    #   there is NO PlotWidget.scatter method (scatter plots use PlotWidget.plot(..., width=0, symbol='o')
    #   or scene.Markers in widget.view).
    assert not hasattr(vplot, '__all__')
    assert callable(vplot.Fig) and callable(vplot.PlotWidget)
    assert not hasattr(vplot, 'SubPlot')
    assert not hasattr(vplot.PlotWidget, 'scatter')

    for method_name in ('histogram', 'image', 'mesh', 'plot', 'spectrogram', 'volume', 'surface', 'colorbar'):
        method = getattr(vplot.PlotWidget, method_name, None)
        assert callable(method), method_name

    fig_sig = inspect.signature(vplot.Fig.__init__)
    assert ['bgcolor', 'size', 'show'] == list(fig_sig.parameters)[1:4]
    plot_sig = inspect.signature(vplot.PlotWidget.plot)
    for param in ('data', 'color', 'symbol', 'line_kind', 'width', 'marker_size', 'title', 'xlabel', 'ylabel'):
        assert param in plot_sig.parameters


__all__ = [name for name in dir() if name.startswith('test_')]
