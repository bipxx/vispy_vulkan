"""CPU acceptance contracts for collection storage and recovery."""
import numpy as np
import pytest
from numpy.testing import assert_array_equal

from vispy.visuals.collections import (
    PathCollection, PointCollection, PolygonCollection, SegmentCollection, TriangleCollection,
)
from vispy.visuals.collections.agg_fast_path_collection import AggFastPathCollection
from vispy.visuals.collections.agg_path_collection import AggPathCollection
from vispy.visuals.collections.agg_point_collection import AggPointCollection
from vispy.visuals.collections.agg_segment_collection import AggSegmentCollection
from vispy.visuals.collections.base_collection import BaseCollection
from vispy.visuals.collections.collection import Collection
from vispy.visuals.collections.raw_path_collection import RawPathCollection
from vispy.visuals.collections.raw_point_collection import RawPointCollection
from vispy.visuals.collections.raw_polygon_collection import RawPolygonCollection
from vispy.visuals.collections.raw_segment_collection import RawSegmentCollection
from vispy.visuals.collections.raw_triangle_collection import RawTriangleCollection
from vispy.visuals.collections.util import dtype_reduce, fetchcode

POINT = np.zeros((1, 3), dtype=np.float32)
PATH = np.array([[-0.6, -0.4, 0], [0, 0.5, 0], [0.6, -0.4, 0]], dtype=np.float32)
SEGMENT = (np.array([[-0.7, 0, 0]], dtype=np.float32), np.array([[0.7, 0, 0]], dtype=np.float32))
TRIANGLE = np.array([[-0.6, -0.6, 0], [0.6, -0.6, 0], [0, 0.7, 0]], dtype=np.float32)
FACES = np.array([[0, 1, 2]], dtype=np.uint32)
QUAD = np.array([[-0.5, -0.5, 0], [0.5, -0.5, 0], [0.5, 0.5, 0], [-0.5, 0.5, 0]], dtype=np.float32)
RED = (1, 0, 0, 1)

CUSTOM_SHADERS = dict(
    dtype=[('position', (np.float32, 3), 'local', 0)], itype=None, mode='triangles',
    vertex='void main() { gl_Position = vec4(position, 1.0); }',
    fragment='void main() { gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0); }',
)


@pytest.mark.parametrize(
    'factory, options, arguments, append_options',
    [
        (AggFastPathCollection, {}, (PATH,), {'closed': False}),
        (AggPathCollection, {}, (PATH,), {'closed': False}),
        (AggPointCollection, {}, (POINT,), {}),
        (AggSegmentCollection, {}, SEGMENT, {}),
        (PathCollection, {'mode': 'raw'}, (PATH,), {'closed': False}),
        (PointCollection, {'mode': 'raw'}, (POINT,), {}),
        (PolygonCollection, {}, (QUAD,), {}),
        (RawPathCollection, {}, (PATH,), {'closed': False}),
        (RawPointCollection, {}, (POINT,), {}),
        (RawPolygonCollection, {}, (QUAD,), {}),
        (RawSegmentCollection, {}, SEGMENT, {}),
        (RawTriangleCollection, {}, (TRIANGLE, FACES), {}),
        (SegmentCollection, {'mode': 'raw'}, SEGMENT, {}),
        (TriangleCollection, {}, (TRIANGLE, FACES), {}),
    ],
    ids=lambda value: value.__name__ if callable(value) else None,
)
def test_failed_deletion_preserves_item(factory, options, arguments, append_options):
    collection = factory(**options)
    collection.append(*arguments, **append_options)
    vertices = collection[0].vertices.copy()
    with pytest.raises(IndexError, match='out of range'):
        del collection[99]
    assert len(collection) == 1
    assert_array_equal(collection[0].vertices, vertices)
    del collection[0]
    assert len(collection) == 0


def test_agg_path_batched_closing_segments():
    collection = AggPathCollection()
    offset = np.array([0, 1, 0], dtype=np.float32)
    collection.append(np.concatenate((PATH, PATH + offset)), itemsize=3, closed=True)
    assert len(collection) == 2
    for index, points in enumerate((PATH, PATH + offset)):
        item = collection[index]
        assert item.vertices.size == 8
        assert item.indices.size == 18
        assert item.indices.dtype == np.dtype(np.uint32)
        local_indices = item.indices - index * 8
        assert_array_equal(local_indices,
                           [0, 1, 2, 1, 2, 3, 4, 5, 6, 5, 6, 7, 6, 7, 0, 7, 0, 1])
        assert_array_equal(item.vertices['p0'][0], points[-1])
        assert_array_equal(item.vertices['p3'][-1], points[0])


def test_agg_segment():
    collection = AggSegmentCollection()
    collection.append(*SEGMENT, linewidth=6)
    assert len(collection) == 1
    assert collection[0].vertices.size == 4
    assert collection[0].uniforms['linewidth'].item() == 6


def test_base_collection():
    dtype = np.dtype([('x', np.float32)])
    collection = BaseCollection(dtype)
    collection.append(np.array([(1,), (2,)], dtype=dtype), itemsize=1)
    assert len(collection) == 2
    assert collection[1].vertices['x'].item() == 2
    with pytest.raises(ValueError, match='structured dtype'):
        BaseCollection(np.float32)
    recovered = BaseCollection(dtype)
    recovered.append(np.array([(3,)], dtype=dtype), itemsize=1)
    assert len(recovered) == 1
    assert recovered[0].vertices['x'].item() == 3


def test_collection_constructor():
    with pytest.raises(NameError, match='bogus'):
        Collection(**CUSTOM_SHADERS, bogus=True)
    collection = Collection(**CUSTOM_SHADERS)
    assert 'position' in collection.vtype.names


def test_item():
    triangles = RawTriangleCollection()
    triangles.append(TRIANGLE, FACES)
    item = triangles[0]
    assert item.vertices.size == 3
    assert item.indices.size == 3
    triangles.append(TRIANGLE, FACES)
    second = triangles[1]
    second.indices = np.array([2, 1, 0], dtype=np.uint32)
    assert_array_equal(triangles[1].indices, [5, 4, 3])
    replacement = second.vertices.copy()
    replacement['position'] *= 0.5
    second.vertices = replacement
    assert_array_equal(triangles[1].vertices['position'], TRIANGLE * 0.5)
    second.vertices['position'][:] = TRIANGLE
    second['position'][:] *= 0.25
    second.indices[:] = [3, 4, 5]
    assert_array_equal(triangles[1].vertices['position'], TRIANGLE * 0.25)
    assert_array_equal(triangles[1].indices, [3, 4, 5])
    assert_array_equal(triangles[0].vertices['position'], TRIANGLE)
    assert_array_equal(triangles[0].indices, [0, 1, 2])

    points = RawPointCollection()
    points.append(POINT)
    item = points[0]
    with pytest.raises(ValueError, match='no indices'):
        item.indices = np.array([0], dtype=np.uint32)
    assert item.vertices.size == 1
    assert_array_equal(item.vertices['position'], POINT)
    with pytest.raises(ValueError, match='no associated uniform'):
        item.uniforms = np.zeros(1)


def test_raw_path():
    collection = RawPathCollection()
    points = np.array([[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0]], dtype=np.float32)
    collection.append(points, closed=True)
    item = collection[0]
    assert item.vertices.size == 6
    assert_array_equal(item.vertices['position'], points[[0, 0, 1, 2, 0, 0]])


def test_raw_point():
    collection = RawPointCollection(color='local', size='local')
    collection.append(np.array([[-0.5, 0, 0], [0.5, 0, 0]], dtype=np.float32), size=9)
    assert len(collection) == 2
    assert collection[0].vertices.size == 1
    assert_array_equal(collection[0].vertices['position'], [[-0.5, 0, 0]])
    assert_array_equal(collection[1].vertices['position'], [[0.5, 0, 0]])
    assert collection[1].vertices['size'].item() == 9


def test_raw_polygon():
    collection = RawPolygonCollection()
    corners = QUAD + [0.5, 0.5, 0]
    collection.append(corners)
    item = collection[0]
    assert item.indices.size == 6
    assert set(map(tuple, item.vertices['position'][item.indices])) == set(map(tuple, corners))


def test_raw_segment():
    collection = RawSegmentCollection(color='shared')
    collection.append(*SEGMENT, color=RED)
    assert collection[0].vertices.size == 2
    assert_array_equal(collection['color'][0], RED)


def test_raw_triangle():
    collection = RawTriangleCollection()
    collection.append(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32), FACES)
    assert len(collection) == 1
    assert_array_equal(collection[0].indices, [0, 1, 2])


def test_uniform_helpers():
    dtype = np.dtype([('color', np.float32, 4)])
    assert dtype_reduce(dtype, level=1) == [['color', 4, 'float32']]
    assert 'varying vec4 color;' in ' '.join(fetchcode(dtype).split())
    with pytest.raises(KeyError) as caught:
        fetchcode(np.dtype([('bad', np.float32, 5)]))
    assert caught.value.args == (5,)
    assert 'void fetch_uniforms()' in fetchcode(dtype)


@pytest.fixture
def render_collection():
    from vispy import app, gloo

    size = 96
    with app.Canvas(app='dawn_headless', size=(size, size), show=False) as canvas:
        canvas.set_current()
        color = gloo.RenderBuffer((size, size), format='color')
        framebuffer = gloo.FrameBuffer(color=color)
        collections = []

        def render(collection, view=None):
            collections.append(collection)
            with framebuffer:
                gloo.set_viewport(0, 0, size, size)
                gloo.set_state(
                    blend=True, depth_test=False, cull_face=False,
                    blend_func=('src_alpha', 'one_minus_src_alpha', 'one', 'one_minus_src_alpha'),
                )
                gloo.clear(color=(0, 0, 0, 1), depth=False)
                (collection if view is None else view).draw()
                return framebuffer.read(alpha=False).copy()

        try:
            yield render
        finally:
            for collection in dict.fromkeys(collections):
                for program in collection._programs:
                    program.delete()
                for resource in (collection._vertices_buffer, collection._indices_buffer,
                                 collection._uniforms_texture):
                    if resource is not None:
                        resource.delete()
            framebuffer.delete()
            color.delete()


@pytest.mark.gpu
@pytest.mark.parametrize('factory', [AggFastPathCollection, AggPathCollection], ids=lambda cls: cls.__name__)
def test_agg_paths(factory, render_collection):
    collection = factory()
    collection.append(PATH)
    assert len(collection) == 1
    collection['viewport'] = (0, 0, 96, 96)
    collection['linewidth'] = 5
    collection['color'] = (1, 1, 1, 1)
    pixels = render_collection(collection)
    assert np.count_nonzero(np.any(pixels > 20, axis=-1)) >= 150
    assert np.any(pixels[23:30, 45:52] > 20)
    assert not np.any(pixels[65:70, 45:52])


@pytest.mark.gpu
def test_agg_point(render_collection):
    collection = AggPointCollection(color='local', size='local')
    collection.append(POINT, color=(0, 1, 1, 1), size=16)
    pixels = render_collection(collection)
    assert pixels[48, 48, 0] <= 5
    assert np.all(pixels[48, 48, 1:] >= 240)
    assert_array_equal(pixels[32, 48], [0, 0, 0])


@pytest.mark.gpu
def test_custom_collection(render_collection):
    collection = Collection(**CUSTOM_SHADERS)
    vertices = np.empty(3, dtype=collection.vtype)
    vertices['position'] = TRIANGLE
    collection.append(vertices, itemsize=3)
    pixels = render_collection(collection)
    assert_array_equal(pixels[48, 48], [255, 0, 0])
    assert_array_equal(pixels[5, 5], [0, 0, 0])


@pytest.mark.gpu
def test_collectionview(render_collection):
    from vispy.visuals.transforms import NullTransform, STTransform

    collection = TriangleCollection()
    left = np.array([[-0.8, -0.6, 0], [-0.2, -0.6, 0], [-0.5, 0.7, 0]], dtype=np.float32)
    collection.append(left, FACES, color=RED)
    view = collection.view(STTransform(translate=(1, 0, 0)))
    shifted = render_collection(collection, view)
    assert_array_equal(shifted[48, 72], [255, 0, 0])
    assert not shifted[:, :48].any()
    original = render_collection(collection)
    assert_array_equal(original[48, 24], [255, 0, 0])
    assert not original[:, 48:].any()

    centered = TriangleCollection()
    centered.append(TRIANGLE, FACES, color=RED)
    with pytest.raises(TypeError, match='transform'):
        centered.view()
    recovered = centered.view(NullTransform())
    assert_array_equal(render_collection(centered, recovered)[48, 48], [255, 0, 0])

    # Updating the source after the view's first draw rebinds its vertex data.
    centered[0]['position'] = left
    updated = render_collection(centered, recovered)
    assert_array_equal(updated[48, 24], [255, 0, 0])
    assert_array_equal(updated[48, 48], [0, 0, 0])
    centered[0]['position'][:] = TRIANGLE
    restored = render_collection(centered, recovered)
    assert_array_equal(restored[48, 48], [255, 0, 0])
    assert_array_equal(restored[48, 24], [0, 0, 0])


@pytest.mark.gpu
def test_path_collection(render_collection):
    collection = PathCollection(mode='agg+')
    collection.append(PATH, closed=True)
    collection['color'] = (1, 1, 1, 1)
    collection['linewidth'] = 5
    collection['viewport'] = (0, 0, 96, 96)
    pixels = render_collection(collection)
    assert np.any(pixels[65:70, 46:51] > 20)


@pytest.mark.gpu
def test_point_collection(render_collection):
    collection = PointCollection(mode='agg', color='shared', size='shared')
    collection.append(POINT, color=RED, size=16)
    pixels = render_collection(collection)
    assert pixels[48, 48, 0] >= 200
    assert pixels[48, 48, 1] <= 5
    assert_array_equal(pixels[32, 48], [0, 0, 0])


@pytest.mark.gpu
def test_polygon_collection(render_collection):
    collection = PolygonCollection(mode='raw')
    vertices = np.array(
        [[-0.6, -0.6, 0], [0.6, -0.6, 0], [0.6, 0, 0], [0, 0, 0], [0, 0.6, 0], [-0.6, 0.6, 0]],
        dtype=np.float32,
    )
    collection.append(vertices, color=RED)
    pixels = render_collection(collection)
    assert_array_equal(pixels[32, 32], [255, 0, 0])
    assert_array_equal(pixels[32, 64], [0, 0, 0])


@pytest.mark.gpu
def test_segment_collection(render_collection):
    collection = SegmentCollection(mode='raw', color='shared')
    collection.append(*SEGMENT, color=RED)
    pixels = render_collection(collection)
    assert np.any(np.all(pixels[47:50, 48] == [255, 0, 0], axis=-1))
    assert_array_equal(pixels[48, 5], [0, 0, 0])


@pytest.mark.gpu
def test_triangle_collection(render_collection):
    collection = TriangleCollection(mode='raw')
    collection.append(TRIANGLE, FACES, color=RED)
    pixels = render_collection(collection)
    np.testing.assert_allclose(pixels[48, 48], [255, 0, 0], atol=1)
    np.testing.assert_allclose(pixels[5, 5], [0, 0, 0], atol=1)
