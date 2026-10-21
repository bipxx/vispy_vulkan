import numpy as np
from vispy import scene, use

from vispy.testing import (TestingCanvas, requires_application,
                           run_tests_if_main, requires_pyopengl)


def setup_module(module):
    use(gl='gl+')


def teardown_module(module):
    use(gl='gl2')


@requires_pyopengl()
@requires_application()
def test_mesh_with_vertex_values():
    size = (80, 60)
    with TestingCanvas(size=size) as c:
        use(gl='gl+')
        vert = np.array([[0, 0, 0], [0, 30, 0], [40, 0, 0]])
        faces = np.array([0, 1, 2])
        pos = np.array([[0, 0, 0], [80, 60, 0]])
        # identity and rotate 180
        trans = np.array([
            [
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
            ],
            [
                [-1, 0, 0],
                [0, -1, 0],
                [0, 0, 1],
            ],
        ])
        colors = ['red', 'blue']
        mesh = scene.visuals.InstancedMesh(
            vertices=vert, faces=faces, instance_positions=pos, instance_transforms=trans, instance_colors=colors
        )
        v = c.central_widget.add_view(border_width=0)
        v.add(mesh)
        render = c.render()
        assert np.allclose(render[10, 10], (127, 0, 0, 255), atol=1)
        assert np.allclose(render[-10, -10], (0, 0, 255, 255))
        assert np.allclose(render[30, 40], (0, 0, 0, 255))


@requires_pyopengl()
@requires_application()
def test_compute_bounds():
    size = (80, 60)
    with TestingCanvas(size=size) as c:
        use(gl='gl+')
        vert = np.array([[0, 0, 0], [1, 1, 1]], dtype=np.float32)
        faces = np.array([[0, 1, 0]])
        pos = np.array([[0, 0, 0], [10, 20, 30]], dtype=np.float32)
        trans = np.array([np.eye(3), np.eye(3)], dtype=np.float32)

        mesh = scene.visuals.InstancedMesh(
            vertices=vert, faces=faces,
            instance_positions=pos,
            instance_transforms=trans,
        )
        v = c.central_widget.add_view(border_width=0)
        v.add(mesh)

        assert mesh._compute_bounds(0, None) == (0.0, 11.0)
        assert mesh._compute_bounds(1, None) == (0.0, 21.0)
        assert mesh._compute_bounds(2, None) == (0.0, 31.0)


@requires_pyopengl()
@requires_application()
def test_compute_bounds_with_rotation():
    size = (80, 60)
    with TestingCanvas(size=size) as c:
        use(gl='gl+')
        vert = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]])
        # 90-degree rotation around Z: x -> y, y -> -x
        rot90z = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.float32)
        pos = np.array([[0, 0, 0], [5, 5, 0]], dtype=np.float32)
        trans = np.array([np.eye(3), rot90z], dtype=np.float32)

        mesh = scene.visuals.InstancedMesh(
            vertices=vert, faces=faces,
            instance_positions=pos,
            instance_transforms=trans,
        )
        v = c.central_widget.add_view(border_width=0)
        v.add(mesh)

        bx = mesh._compute_bounds(0, None)
        by = mesh._compute_bounds(1, None)
        bz = mesh._compute_bounds(2, None)

        # Instance 0 (identity): x=[0,1], y=[0,1], z=[0,0]
        # Instance 1 (rot90z at (5,5,0)):
        #   (0,0,0)->(5,5,0), (1,0,0)->(5,6,0), (0,1,0)->(4,5,0)
        assert bx == (0.0, 5.0)
        assert by == (0.0, 6.0)
        assert bz == (0.0, 0.0)


"""Provider-free public InstancedMesh bounds regressions."""
from unittest.mock import patch

import numpy as np
import pytest

from vispy.visuals import InstancedMeshVisual


def _bounds_mesh(dims=2, positions=None, transforms=None):
    vertices = np.array([[0, 0, 0], [2, 0, 0], [0, 3, 0]], dtype=np.float32)[:, :dims]
    if positions is None:
        positions = np.array([[10, 20, 30]], dtype=np.float32)
    if transforms is None:
        transforms = np.eye(3, dtype=np.float32)[None]
    return InstancedMeshVisual(vertices=vertices, faces=np.array([[0, 1, 2]], dtype=np.uint32),
                               instance_positions=positions, instance_transforms=transforms,
                               shading=None)


def _assert_shared_bounds(mesh, first, peers, expected):
    # Query z first to catch a template-space result being cached before padding.
    for axis in (2, 0, 1):
        assert first.bounds(axis) == expected[axis]
    for visual in (mesh, *peers):
        assert [visual.bounds(axis) for axis in range(3)] == expected


def test_instanced_2d_bounds_translation_view_first():
    mesh = _bounds_mesh()
    existing = mesh.view()
    late = mesh.view()
    _assert_shared_bounds(mesh, existing, [late], [(10, 12), (20, 23), (30, 30)])


def test_instanced_2d_bounds_out_of_plane_and_shear():
    # The contract is a conservative transformed template AABB, including its
    # absent (2, 3) triangle corner, rather than only the triangle's vertices.
    transform = np.array([[1, 2, 0], [0, 0, -1], [3, -1, 0]], dtype=np.float32)
    mesh = _bounds_mesh(transforms=transform[None])
    _assert_shared_bounds(mesh, mesh.view(), [], [(10, 18), (20, 20), (27, 36)])


def test_instanced_3d_bounds_all_eight_template_corners():
    vertices = np.array([[-1, -3, 2], [2, 1, 5]], dtype=np.float32)
    transform = np.array([[1, -2, 3], [-1, 4, -2], [2, 1, -3]], dtype=np.float32)
    mesh = InstancedMeshVisual(vertices=vertices, faces=np.array([[0, 1, 0]]),
                               instance_positions=np.array([[10, -20, 30]], dtype=np.float32),
                               instance_transforms=transform[None], shading=None)
    _assert_shared_bounds(mesh, mesh.view(), [], [(13, 33), (-44, -19), (10, 29)])


def test_instanced_bounds_existing_translation_example_cpu():
    mesh = InstancedMeshVisual(vertices=np.array([[0, 0, 0], [1, 1, 1]], dtype=np.float32),
                               faces=np.array([[0, 1, 0]]),
                               instance_positions=np.array([[0, 0, 0], [10, 20, 30]], dtype=np.float32),
                               instance_transforms=np.array([np.eye(3), np.eye(3)], dtype=np.float32),
                               shading=None)
    assert [mesh.bounds(i) for i in range(3)] == [(0, 11), (0, 21), (0, 31)]


def test_instanced_bounds_existing_rotation_example_cpu():
    mesh = InstancedMeshVisual(vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
                               faces=np.array([[0, 1, 2]]),
                               instance_positions=np.array([[0, 0, 0], [5, 5, 0]], dtype=np.float32),
                               instance_transforms=np.array([np.eye(3), [[0, -1, 0], [1, 0, 0], [0, 0, 1]]], dtype=np.float32),
                               shading=None)
    assert [mesh.bounds(i) for i in range(3)] == [(0, 5), (0, 6), (0, 0)]


@pytest.mark.parametrize('dims', [2, 3])
@pytest.mark.parametrize('empty', ['positions', 'transforms', 'both'])
def test_instanced_empty_initial_bounds(dims, empty):
    positions = np.empty((0, 3), dtype=np.float32) if empty != 'transforms' else None
    transforms = np.empty((0, 3, 3), dtype=np.float32) if empty != 'positions' else None
    mesh = _bounds_mesh(dims=dims, positions=positions, transforms=transforms)
    _assert_shared_bounds(mesh, mesh.view(), [mesh.view()], [None, None, None])


@pytest.mark.parametrize('dims', [2, 3])
@pytest.mark.parametrize('empty', ['positions', 'transforms', 'both'])
def test_instanced_empty_and_repopulated_cache_transitions(dims, empty):
    mesh = _bounds_mesh(dims=dims)
    existing, peer = mesh.view(), mesh.view()
    full = [(10, 12), (20, 23), (30, 30)]
    _assert_shared_bounds(mesh, existing, [peer], full)
    if empty != 'transforms':
        mesh.instance_positions = np.empty((0, 3), dtype=np.float32)
    if empty != 'positions':
        mesh.instance_transforms = np.empty((0, 3, 3), dtype=np.float32)
    late = mesh.view()
    _assert_shared_bounds(mesh, late, [existing, peer], [None, None, None])
    mesh.instance_positions = np.array([[-10, -20, -30]], dtype=np.float32)
    mesh.instance_transforms = np.eye(3, dtype=np.float32)[None]
    _assert_shared_bounds(mesh, existing, [late, peer], [(-10, -8), (-20, -17), (-30, -30)])


@pytest.mark.parametrize('changed', ['positions', 'transforms', 'vertices'])
def test_instanced_2d_bounds_public_mutation_invalidates_shared_cache(changed):
    mesh = _bounds_mesh()
    existing, peer = mesh.view(), mesh.view()
    _assert_shared_bounds(mesh, existing, [peer], [(10, 12), (20, 23), (30, 30)])
    if changed == 'positions':
        mesh.instance_positions = np.array([[1, 2, 3]], dtype=np.float32)
        expected = [(1, 3), (2, 5), (3, 3)]
    elif changed == 'transforms':
        mesh.instance_transforms = np.array([[[0, -1, 0], [1, 0, 0], [0, 0, 1]]], dtype=np.float32)
        expected = [(7, 10), (20, 22), (30, 30)]
    else:
        mesh.set_data(vertices=np.array([[-1, -2], [4, -2], [-1, 1]], dtype=np.float32),
                      faces=np.array([[0, 1, 2]], dtype=np.uint32))
        expected = [(9, 14), (18, 21), (30, 30)]
    _assert_shared_bounds(mesh, peer, [existing, mesh.view()], expected)


@pytest.mark.parametrize('first_dims', [2, 3])
def test_instanced_bounds_template_dimension_replacement(first_dims):
    mesh = _bounds_mesh(dims=first_dims)
    existing, peer = mesh.view(), mesh.view()
    _assert_shared_bounds(mesh, existing, [peer], [(10, 12), (20, 23), (30, 30)])
    vertices = np.array([[-2, -1, 4], [1, -1, 4], [-2, 2, 7]], dtype=np.float32)
    final_dims = 5 - first_dims
    mesh.set_data(vertices=vertices[:, :final_dims], faces=np.array([[0, 1, 2]], dtype=np.uint32))
    expected_z = (34, 37) if final_dims == 3 else (30, 30)
    _assert_shared_bounds(mesh, peer, [existing, mesh.view()], [(8, 11), (19, 22), expected_z])


def test_instanced_bounds_resident_queries_reuse_all_axis_cache():
    mesh = _bounds_mesh()
    existing, peer = mesh.view(), mesh.view()
    with patch.object(mesh, '_compute_bounds', wraps=mesh._compute_bounds) as compute:
        _assert_shared_bounds(mesh, existing, [peer], [(10, 12), (20, 23), (30, 30)])
        _assert_shared_bounds(mesh, peer, [existing], [(10, 12), (20, 23), (30, 30)])
    assert compute.call_count == 1


def test_instanced_bounds_no_template_remains_none():
    mesh = InstancedMeshVisual(instance_positions=np.array([[0, 0, 0]], dtype=np.float32),
                               instance_transforms=np.eye(3, dtype=np.float32)[None], shading=None)
    _assert_shared_bounds(mesh, mesh.view(), [], [None, None, None])


def test_instanced_bounds_empty_above_spatial_axes_is_none():
    mesh = _bounds_mesh(dims=3, positions=np.empty((0, 3), dtype=np.float32))
    assert mesh.bounds(3) is None


def test_instanced_bounds_nonempty_above_spatial_axes_remains_zero():
    mesh = _bounds_mesh(dims=3)
    assert mesh.bounds(3) == (0, 0)


"""Provider-free draw admission and recovery; no renderer call is executed."""
from vispy.visuals.mesh import MeshVisual


def _assert_inherited_view(inherited, mesh, selected):
    inherited.assert_called_once()
    args, kwargs = inherited.call_args
    assert args[0] is mesh
    assert (args[1] if len(args) == 2 else kwargs['view']) is selected


def _empty_streams(mesh, empty):
    if empty in ('positions', 'both'):
        mesh.instance_positions = np.empty((0, 3), dtype=np.float32)
    if empty in ('transforms', 'both'):
        mesh.instance_transforms = np.empty((0, 3, 3), dtype=np.float32)


@pytest.mark.parametrize('dims', [2, 3])
@pytest.mark.parametrize('empty', ['positions', 'transforms', 'both'])
def test_instanced_empty_streams_skip_inherited_prepare(dims, empty):
    mesh = _bounds_mesh(dims=dims)
    existing = mesh.view()
    _empty_streams(mesh, empty)
    late = mesh.view()
    with patch.object(MeshVisual, '_prepare_draw', side_effect=AssertionError('empty must not prepare')) as prepare:
        for selected in (mesh, existing, late):
            assert selected._prepare_draw(view=selected) is False
    assert prepare.call_count == 0
    assert mesh._data_changed is True


@pytest.mark.parametrize('selected_name', ['original', 'existing', 'late'])
@pytest.mark.parametrize('empty', ['positions', 'transforms', 'both'])
def test_instanced_empty_public_draw_never_configures_or_draws(selected_name, empty):
    mesh = _bounds_mesh()
    existing = mesh.view()
    # Warm real preparation only: no Canvas, shader configure, program draw or flush.
    assert mesh._prepare_draw(view=mesh) is None
    assert mesh._data_changed is False
    _empty_streams(mesh, empty)
    selected = {'original': mesh, 'existing': existing, 'late': mesh.view()}[selected_name]
    with patch.object(selected, '_configure_gl_state') as configure, \
            patch.object(selected._program, 'draw') as program_draw:
        selected.draw()
    assert configure.call_count == program_draw.call_count == 0
    assert mesh._data_changed is True


@pytest.mark.parametrize('dims', [2, 3])
@pytest.mark.parametrize('result', [False, None, True])
def test_instanced_populated_prepare_forwards_exact_view_and_return(dims, result):
    mesh = _bounds_mesh(dims=dims)
    for selected in (mesh, mesh.view()):
        with patch.object(MeshVisual, '_prepare_draw', autospec=True, return_value=result) as inherited:
            assert selected._prepare_draw(view=selected) is result
        _assert_inherited_view(inherited, mesh, selected)


@pytest.mark.parametrize('dims', [2, 3])
@pytest.mark.parametrize('empty', ['positions', 'transforms', 'both'])
def test_instanced_empty_repopulate_real_prepare_and_shared_bounds(dims, empty):
    mesh = _bounds_mesh(dims=dims)
    existing, peer = mesh.view(), mesh.view()
    assert mesh._prepare_draw(view=mesh) is None
    _assert_shared_bounds(mesh, existing, [peer], [(10, 12), (20, 23), (30, 30)])
    _empty_streams(mesh, empty)
    _assert_shared_bounds(mesh, peer, [existing], [None, None, None])
    assert existing._prepare_draw(view=existing) is False
    assert mesh._data_changed is True
    mesh.instance_positions = np.array([[-10, -20, -30]], dtype=np.float32)
    mesh.instance_transforms = np.eye(3, dtype=np.float32)[None]
    _assert_shared_bounds(mesh, existing, [peer, mesh.view()], [(-10, -8), (-20, -17), (-30, -30)])
    with patch.object(mesh, '_update_data', wraps=mesh._update_data) as prepare:
        assert peer._prepare_draw(view=peer) is None
        assert prepare.call_count == 1
        assert mesh._data_changed is False
        assert existing._prepare_draw(view=existing) is None
        assert prepare.call_count == 1


def test_instanced_populated_missing_template_propagates_inherited_skip():
    mesh = InstancedMeshVisual(instance_positions=np.zeros((1, 3), dtype=np.float32),
                               instance_transforms=np.eye(3, dtype=np.float32)[None], shading=None)
    original = MeshVisual._prepare_draw
    with patch.object(MeshVisual, '_prepare_draw', autospec=True, side_effect=original) as inherited:
        assert mesh._prepare_draw(view=mesh) is False
    _assert_inherited_view(inherited, mesh, mesh)
    assert mesh._data_changed is True


@pytest.mark.parametrize('dims', [2, 3])
def test_instanced_missing_template_public_draw_and_set_data_recovery(dims):
    mesh = InstancedMeshVisual(instance_positions=np.zeros((1, 3), dtype=np.float32),
                               instance_transforms=np.eye(3, dtype=np.float32)[None], shading=None)
    existing = mesh.view()
    with patch.object(existing, '_configure_gl_state') as configure, \
            patch.object(existing._program, 'draw') as program_draw:
        existing.draw()
    assert configure.call_count == program_draw.call_count == 0
    assert mesh._data_changed is True
    vertices = np.array([[0, 0, 0], [2, 0, 0], [0, 3, 0]], dtype=np.float32)[:, :dims]
    mesh.set_data(vertices=vertices, faces=np.array([[0, 1, 2]], dtype=np.uint32))
    _assert_shared_bounds(mesh, existing, [mesh.view()], [(0, 2), (0, 3), (0, 0)])
    with patch.object(mesh, '_update_data', wraps=mesh._update_data) as prepare:
        assert existing._prepare_draw(view=existing) is None
        assert prepare.call_count == 1 and mesh._data_changed is False
        assert mesh._prepare_draw(view=mesh) is None
        assert prepare.call_count == 1


@pytest.mark.parametrize('bad_colors', [[], np.empty((0, 3)), np.empty((0, 4))])
def test_instanced_empty_colors_rejected_before_existing_state_commit(bad_colors):
    mesh = _bounds_mesh()
    mesh.instance_colors = ['red']
    previous_colors = mesh.instance_colors
    previous_buffer = mesh._instance_colors_vbo
    assert mesh._prepare_draw(view=mesh) is None
    with pytest.raises(ValueError):
        mesh.instance_colors = bad_colors
    assert mesh.instance_colors is previous_colors
    assert mesh._instance_colors_vbo is previous_buffer
    assert mesh._data_changed is False
    mesh.instance_colors = None
    assert mesh.instance_colors is None
    assert mesh._instance_colors_vbo == (1, 1, 1, 1)
    with patch.object(MeshVisual, '_prepare_draw', autospec=True, return_value=None) as inherited:
        assert mesh._prepare_draw(view=mesh) is None
    _assert_inherited_view(inherited, mesh, mesh)


def test_instanced_nonempty_instance_count_mismatch_is_not_repaired():
    mesh = _bounds_mesh()
    mesh.instance_transforms = np.repeat(np.eye(3, dtype=np.float32)[None], 2, axis=0)
    before = (mesh.instance_positions.copy(), mesh.instance_transforms.copy())
    with patch.object(MeshVisual, '_prepare_draw', autospec=True, return_value=None) as inherited:
        assert mesh._prepare_draw(view=mesh) is None
    _assert_inherited_view(inherited, mesh, mesh)
    np.testing.assert_array_equal(mesh.instance_positions, before[0])
    np.testing.assert_array_equal(mesh.instance_transforms, before[1])


@pytest.mark.parametrize('dims', [2, 3])
@pytest.mark.parametrize('attribute', ['positions', 'transforms', 'colors'])
def test_instanced_attribute_updates_preserve_warmed_template_bounds(dims, attribute):
    mesh = _bounds_mesh(dims=dims)
    existing, peer = mesh.view(), mesh.view()
    assert mesh._prepare_draw(view=mesh) is None
    assert mesh.mesh_data._vertices_indexed_by_faces is not None
    original_vertices = mesh.mesh_data.get_vertices().copy()
    original_template_bounds = list(mesh._bounds)
    with patch.object(mesh.mesh_data, 'get_bounds', wraps=mesh.mesh_data.get_bounds) as scan:
        if attribute == 'positions':
            mesh.instance_positions = np.array([[1, 2, 3]], dtype=np.float32)
            expected = [(1, 3), (2, 5), (3, 3)]
        elif attribute == 'transforms':
            mesh.instance_transforms = np.array([[[0, -1, 0], [1, 0, 0], [2, -1, 1]]], dtype=np.float32)
            expected = [(7, 10), (20, 22), (27, 34)]
        else:
            mesh.instance_colors = ['red']
            expected = [(10, 12), (20, 23), (30, 30)]
        assert scan.call_count == 0
    assert mesh._bounds == original_template_bounds
    np.testing.assert_array_equal(mesh.mesh_data.get_vertices(), original_vertices)
    _assert_shared_bounds(mesh, existing, [peer, mesh.view()], expected)
    assert mesh._data_changed is True


@pytest.mark.parametrize('dims', [2, 3])
def test_instanced_explicit_meshdata_notification_still_refreshes_template(dims):
    mesh = _bounds_mesh(dims=dims)
    existing = mesh.view()
    assert mesh._prepare_draw(view=mesh) is None
    vertices = np.array([[-1, -2, 0], [4, -2, 0], [-1, 1, 2]], dtype=np.float32)[:, :dims]
    mesh.mesh_data.set_vertices(vertices)
    with patch.object(mesh.mesh_data, 'get_bounds', wraps=mesh.mesh_data.get_bounds) as scan:
        mesh.mesh_data_changed()
    assert scan.call_count == 1
    expected_z = (30, 32) if dims == 3 else (30, 30)
    _assert_shared_bounds(mesh, existing, [mesh.view()], [(9, 14), (18, 21), expected_z])
    assert mesh._data_changed is True

run_tests_if_main()
