"""Source acceptance for the reviewed geometry inventory cases."""

from itertools import product

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from vispy.geometry import (
    MeshData, PolygonData, Rect, TorusKnot, Triangulation, create_arrow,
    create_box, create_cone, create_cube, create_cylinder, create_grid_mesh,
    create_plane, create_sphere, resize, triangulate,
)
from vispy.geometry.curves import curve3_bezier, curve4_bezier
from vispy.geometry.isocurve import isocurve
from vispy.geometry.isosurface import isosurface
from vispy.geometry.normals import compact, normals
from vispy.geometry.parametric import surface


def _area_xy(vertices, faces):
    triangles = vertices[faces, :2]
    a = triangles[:, 1] - triangles[:, 0]
    b = triangles[:, 2] - triangles[:, 0]
    return np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum() / 2


def test_bezier():
    for curve in (curve3_bezier((0, 0), (1, 1), (2, 0)),
                  curve4_bezier((0, 0), (.5, 1), (1.5, 1), (2, 0))):
        points = np.asarray(curve)
        assert_array_equal(points[[0, -1]], [[0, 0], [2, 0]])
        assert np.any(points[1:-1, 1] > 0)
    with pytest.raises(ValueError):
        curve3_bezier((0, 0), (1,), (2, 0))


def test_compact():
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]])
    unique, faces, _ = compact(vertices, np.array([[3, 1, 2]]))
    assert unique.shape == (3, 3)
    assert_array_equal(unique[faces], [vertices[:3]])
    with pytest.raises(IndexError):
        compact(vertices[:3], np.array([[0, 1, 3]]))


def test_create_arrow():
    arrow = create_arrow(3, 8, radius=.2, length=3, cone_length=1)
    assert (arrow.n_vertices, arrow.n_faces) == (41, 56)
    z = arrow.get_vertices()[:, 2]
    assert_allclose([z.min(), z.max()], [0, 3])

    cone = create_arrow(3, 8, radius=.2, length=3, cone_length=4)
    assert (cone.n_vertices, cone.n_faces) == (9, 8)
    assert cone.get_vertices()[:, 2].max() == 3


def test_create_box():
    vertices, faces, _ = create_box(2, 4, 6, planes=['+x'])
    assert vertices.shape == (4,)
    assert_array_equal(vertices['position'][:, 0], [1] * 4)
    assert_array_equal(vertices['normal'], [[1, 0, 0]] * 4)
    assert faces.shape == (2, 3)
    with pytest.raises(ValueError):
        create_box(planes=['north'])


def test_create_cone():
    vertices = create_cone(4, radius=1.5, length=2).get_vertices()
    assert vertices.shape == (5, 3)
    assert_array_equal(vertices[:4, 2], [0] * 4)
    assert_allclose(np.linalg.norm(vertices[:4, :2], axis=1), [1.5] * 4)
    assert_array_equal(vertices[4], [0, 0, 2])
    with pytest.raises(IndexError):
        create_cone(0)


def test_create_cube():
    vertices, faces, _ = create_cube()
    positions = vertices['position']
    assert set(map(tuple, positions)) == set(product((-1, 1), repeat=3))
    triangles = positions[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0],
                     triangles[:, 2] - triangles[:, 0])
    face_normals = cross / np.linalg.norm(cross, axis=1, keepdims=True)
    assert_array_equal(vertices['normal'][faces],
                       np.repeat(face_normals[:, None, :], 3, axis=1))

    positions[0] = 0
    faces[0, 0] = 7
    fresh_vertices, fresh_faces, _ = create_cube()
    assert_array_equal(fresh_vertices['position'][0], [1, 1, 1])
    assert_array_equal(fresh_faces[0], [0, 1, 2])


def test_create_cylinder():
    mesh = create_cylinder(2, 8, radius=[1, .5], length=3, offset=True)
    x, y, z = mesh.get_vertices()[8]
    assert_allclose([z, np.hypot(x, y), np.arctan2(y, x)],
                    [1.5, .75, np.pi / 8], atol=1e-6, rtol=0)
    with pytest.raises(IndexError):
        create_cylinder(2, 8, radius=[1])


def test_create_grid_mesh():
    xs, ys = np.meshgrid([0, 1], [0, 1])
    zs = xs + 2 * ys
    vertices, faces = create_grid_mesh(xs, ys, zs)
    assert_array_equal(vertices,
                       [[0, 0, 0], [1, 0, 1], [0, 1, 2], [1, 1, 3]])
    assert_array_equal(faces, [[0, 1, 3], [0, 2, 3]])
    with pytest.raises(ValueError):
        create_grid_mesh(xs, np.zeros((2, 3)), zs)


def test_create_plane():
    vertices, _, _ = create_plane(2, 4, 1, 1, direction='-x')
    assert_array_equal(vertices['position'][:, 0], [0] * 4)
    assert_array_equal(vertices['normal'], [[-1, 0, 0]] * 4)
    assert set(map(tuple, vertices['texcoord'])) == set(product((0, 1), repeat=2))
    with pytest.raises(ValueError, match="direction must be one of"):
        create_plane(direction='north')
    assert create_plane(direction='+z')[1].shape == (2, 3)


def test_create_sphere():
    mesh = create_sphere(radius=2.5, method='ico', subdivisions=1)
    assert mesh.n_faces == 80
    assert_allclose(np.linalg.norm(mesh.get_vertices(indexed='faces'), axis=2),
                    2.5, atol=1e-5, rtol=0)
    with pytest.raises(Exception, match='Invalid method'):
        create_sphere(method='invalid')


def test_isocurve():
    segments = isocurve(np.array([[0, 0], [1, 1]]), .5,
                        connected=False, extend_to_edge=False)
    assert len(segments) == 1
    assert set(map(tuple, segments[0])) == {(1, .5), (1, 1.5)}
    assert isocurve(np.zeros((2, 2)), 1, connected=True, extend_to_edge=True) == []


@pytest.mark.filterwarnings('error:overflow encountered:RuntimeWarning')
def test_isosurface():
    vertices, faces = isosurface(np.indices((2, 2, 2))[0], .5)
    assert vertices.shape == (4, 3)
    assert_array_equal(vertices[:, 0], [.5] * 4)
    assert set(map(tuple, vertices[:, 1:])) == set(product((0, 1), repeat=2))
    assert faces.shape == (2, 3)
    assert _area_xy(vertices[:, [1, 2, 0]], faces) == 1

    vertices, faces = isosurface(np.zeros((2, 2, 2)), 1)
    assert vertices.shape == faces.shape == (0, 3)


def test_meshdata():
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    mesh = MeshData(points, np.array([[0, 1, 2]]))
    assert_array_equal(mesh.get_face_normals(), [[0, 0, 1]])
    mesh.set_faces(np.array([[0, 2, 1]]))
    assert_array_equal(mesh.get_face_normals(), [[0, 0, -1]])
    with pytest.raises(ValueError):
        mesh.get_vertices(indexed='edges')
    assert_array_equal(mesh.get_vertices(indexed='faces'), [points[[0, 2, 1]]])


def test_normals():
    faces = np.array([[0, 1, 2]])
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    assert_array_equal(normals(vertices, faces), [[0, 0, 1]] * 3)
    vertices[2] = [2, 0, 0]
    assert_array_equal(normals(vertices, faces), np.zeros((3, 3)))


def test_parametric_surface():
    vertices, indices = surface(lambda u, v: (u, v, 0), umax=1, vmax=1,
                                ucount=1, vcount=1, urepeat=2)
    assert_array_equal(vertices['position'],
                       [[0, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0]])
    assert vertices['texcoord'][:, 0].max() == 2
    assert indices.shape == (6,)
    with pytest.raises(ValueError):
        surface(lambda u, v: (u, v), ucount=1, vcount=1)


def test_polygondata():
    polygon = PolygonData(vertices=np.array([[0, 0], [2, 0], [2, 2], [0, 2]]))
    vertices, faces = polygon.triangulate()
    assert faces.shape == (2, 3)
    assert _area_xy(vertices, faces) == 4
    with pytest.raises(NotImplementedError):
        polygon.add_vertex([1, 1])
    vertices, faces = polygon.triangulate()
    assert _area_xy(vertices, faces) == 4


def test_rect():
    rect = Rect(0, 0, 10, 6)
    rect.center = (8, 5)
    assert rect.pos == (3, 2)
    assert rect.size == (10, 6)
    assert rect.contains(13, 8) is True
    with pytest.raises(ValueError, match='2 elements'):
        Rect(pos=(1, 2, 3), size=(4, 5))


def test_resize():
    result = resize(np.array([[0, 2], [10, 12]]), (3, 5), kind='linear')
    assert result.shape == (3, 5)
    assert result[1, 1] == 5.5
    with pytest.raises(ValueError, match='nearest.*linear'):
        resize(np.zeros((2, 2)), (3, 3), kind='cubic')


def test_torusknot():
    knot = TorusKnot(p=4, q=2, num_points=16, major_radius=10, minor_radius=2)
    assert [component.shape for component in knot.components] == [(16, 3)] * 2
    assert_allclose(knot.first_component[[0, -1]], [[12, 0, 0]] * 2,
                    atol=1e-6, rtol=0)
    with pytest.raises(ValueError):
        TorusKnot(p=3, q=2, num_points=-1)


def test_triangulate():
    points = [(0, 0, 1), (4, 0, 3), (4, 1, 5), (1, 1, 7), (1, 3, 9), (0, 3, 11)]
    vertices, indices = triangulate(points)
    assert _area_xy(vertices, indices.reshape(-1, 3)) == 6
    assert_array_equal(vertices[:, 2], np.full(len(vertices), 6))
    with pytest.raises(IndexError):
        triangulate([(0, 0), (2, 0), (0, 2)])


def test_triangulation():
    points = np.array([[0, 0], [2, 0], [2, 2], [0, 2]])
    edges = np.array([[0, 1], [1, 2], [2, 3], [3, 0], [1, 3]])
    tri = Triangulation(points, edges)
    tri.triangulate()
    assert tri.tris.shape == (2, 3)
    assert _area_xy(tri.pts, tri.tris) == 4
    first, second = (set(map(tuple, triangle)) for triangle in tri.pts[tri.tris])
    assert first & second == {(2, 0), (0, 2)}
    with pytest.raises(TypeError):
        Triangulation(points, np.array([[0, 1, 2]]))
