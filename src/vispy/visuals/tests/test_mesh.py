# -*- coding: utf-8 -*-

from unittest.mock import patch

import numpy as np
from vispy import scene

from vispy.color import Color
from vispy.geometry import MeshData
from vispy.visuals import MeshVisual, SurfacePlotVisual, InstancedMeshVisual
from vispy.geometry import create_cube, create_sphere
from vispy.testing import (TestingCanvas, requires_application,
                           run_tests_if_main, requires_pyopengl)
from vispy.visuals.filters import ShadingFilter, WireframeFilter
from vispy.visuals.filters.mesh import _as_rgba

import pytest


@requires_pyopengl()
def test_mesh_color():
    # Create visual
    vertices, filled_indices, outline_indices = create_cube()
    axis = scene.visuals.Mesh(vertices['position'], outline_indices,
                              color='black', mode='lines')

    # Change color (regression test for a bug that caused this to reset
    # the vertex data to None)

    axis.color = (0.1, 0.3, 0.7, 0.9)

    new_vertices = axis.mesh_data.get_vertices()

    np.testing.assert_allclose(axis.color.rgba, (0.1, 0.3, 0.7, 0.9))
    np.testing.assert_allclose(vertices['position'], new_vertices)


@requires_pyopengl()
@requires_application()
def test_mesh_with_vertex_values():
    size = (45, 40)
    with TestingCanvas(size=size) as c:
        v = c.central_widget.add_view(border_width=0)
        vertices = np.array([(0, 0, 0), (0, 0, 1), (1, 0, 0)], dtype=float)
        faces = np.array([(0, 1, 2)])
        mesh = scene.visuals.Mesh(
            vertices=vertices,
            faces=faces,
            vertex_values=np.ones(len(vertices)),
        )
        v.add(mesh)
        c.render()


@requires_pyopengl()
@requires_application()
@pytest.mark.parametrize('shading', [None, 'flat', 'smooth'])
def test_mesh_shading_change_from_none(shading):
    # Regression test for #2041: exception raised when changing the shading
    # mode with shading=None initially.
    size = (45, 40)
    with TestingCanvas(size=size) as c:
        v = c.central_widget.add_view(border_width=0)
        vertices = np.array([(0, 0, 0), (0, 0, 1), (1, 0, 0)], dtype=float)
        faces = np.array([(0, 1, 2)])
        mesh = scene.visuals.Mesh(vertices=vertices, faces=faces, shading=None)
        v.add(mesh)
        c.render()
        # This below should not fail.
        mesh.shading = shading
        c.render()


@requires_pyopengl()
@requires_application()
@pytest.mark.parametrize('shading', [None, 'flat', 'smooth'])
def test_mesh_shading_filter(shading):
    size = (45, 40)
    with TestingCanvas(size=size, bgcolor="k") as c:
        v = c.central_widget.add_view(border_width=0)
        v.camera = 'arcball'
        mdata = create_sphere(20, 30, radius=1)
        mesh = scene.visuals.Mesh(meshdata=mdata,
                                  shading=shading,
                                  color=(0.2, 0.3, 0.7, 1.0))
        v.add(mesh)

        rendered = c.render()[..., 0]  # R channel only
        if shading in ("flat", "smooth"):
            # there should be a gradient, not solid colors
            assert np.unique(rendered).size >= 28
            # sphere/circle is "dark" on the right and gets brighter as you
            # move to the left, then hits a bright spot and decreases after
            invest_row = rendered[34].astype(np.float64)
            # overall, we should be increasing brightness up to a "bright spot"
            assert (np.diff(invest_row[34:60]) <= 0).all()
        else:
            assert np.unique(rendered).size == 2


def test_intensity_or_color_as_rgba():
    assert _as_rgba(0.3) == Color((1.0, 1.0, 1.0, 0.3))
    assert _as_rgba((0.3, 0.2, 0.1)) == Color((0.3, 0.2, 0.1, 1.0))
    assert _as_rgba((0.3, 0.2, 0.1, 0.5)) == Color((0.3, 0.2, 0.1, 0.5))


@requires_pyopengl()
@requires_application()
@pytest.mark.parametrize('shading', [None, 'flat', 'smooth'])
def test_mesh_shading_filter_enabled(shading):
    size = (45, 40)
    with TestingCanvas(size=size, bgcolor="k") as c:
        v = c.central_widget.add_view(border_width=0)
        v.camera = 'arcball'
        mdata = create_sphere(20, 30, radius=1)
        mesh = scene.visuals.Mesh(meshdata=mdata,
                                  shading=None,
                                  color=(0.2, 0.3, 0.7, 1.0))
        shading_filter = ShadingFilter(shading=shading)
        mesh.attach(shading_filter)
        v.add(mesh)

        shading_filter.enabled = False
        rendered_without_shading = c.render()

        shading_filter.enabled = True
        rendered_with_shading = c.render()

        if shading is None:
            # There should be no shading applied, regardless of the value of
            # `enabled`.
            assert np.allclose(rendered_without_shading, rendered_with_shading)
        else:
            # The result should be different with shading applied.
            assert not np.allclose(rendered_without_shading,
                                   rendered_with_shading)


@requires_pyopengl()
@requires_application()
@pytest.mark.parametrize('attribute', ['ambient_coefficient',
                                       'diffuse_coefficient',
                                       'specular_coefficient',
                                       'ambient_light',
                                       'diffuse_light',
                                       'specular_light'])
def test_mesh_shading_filter_colors(attribute):
    size = (45, 40)
    with TestingCanvas(size=size, bgcolor="k") as c:
        base_color_white = (1.0, 1.0, 1.0, 1.0)
        overlay_color_red = (1.0, 0.0, 0.0, 1.0)

        v = c.central_widget.add_view(border_width=0)
        v.camera = 'arcball'
        mdata = create_sphere(20, 30, radius=1)
        mesh = scene.visuals.Mesh(meshdata=mdata, color=base_color_white)
        v.add(mesh)

        shading_filter = ShadingFilter(shading='smooth',
                                       # Set the light source on the side of
                                       # and around the camera to get a clearly
                                       # visible reflection.
                                       light_dir=(-5, -5, 5),
                                       # Activate all illumination types as
                                       # white light but reduce the intensity
                                       # to prevent saturation.
                                       ambient_light=0.3,
                                       diffuse_light=0.3,
                                       specular_light=0.3,
                                       # Get a wide highlight.
                                       shininess=4)
        mesh.attach(shading_filter)

        rendered_white = c.render()

        setattr(shading_filter, attribute, overlay_color_red)
        rendered_red = c.render()

        # The results should be different.
        assert not np.allclose(rendered_white, rendered_red)

        # There should be an equal amount of all colors in the white rendering.
        color_count_white = rendered_white.sum(axis=(0, 1))
        r, g, b, _ = color_count_white
        assert r == g and r == b

        color_count_red = rendered_red.sum(axis=(0, 1))
        # There should be more red in the red-colored rendering.
        r, g, b, _ = color_count_red
        assert r > g and r > b


@requires_pyopengl()
def test_mesh_bounds():
    # Create 3D visual
    vertices, filled_indices, outline_indices = create_cube()
    axis = scene.visuals.Mesh(vertices['position'], outline_indices,
                              color='black', mode='lines')

    # Test bounds for all 3 axes
    for i in range(3):
        np.testing.assert_allclose(axis.bounds(i), (-1.0, 1.0))

    # Create 2D visual using projection of cube
    axis = scene.visuals.Mesh(vertices['position'][:, :2], outline_indices,
                              color='black', mode='lines')

    # Test bounds for first 2 axes
    for i in range(2):
        np.testing.assert_allclose(axis.bounds(i), (-1.0, 1.0))
    # Test bounds for 3rd axis
    np.testing.assert_allclose(axis.bounds(2), (0.0, 0.0))


@requires_pyopengl()
@requires_application()
def test_mesh_wireframe_filter():
    size = (45, 40)
    with TestingCanvas(size=size, bgcolor="k") as c:
        v = c.central_widget.add_view(border_width=0)
        # Create visual
        mdata = create_sphere(20, 40, radius=20)
        mesh = scene.visuals.Mesh(meshdata=mdata,
                                  shading=None,
                                  color=(0.1, 0.3, 0.7, 0.9))
        wireframe_filter = WireframeFilter(color='red')
        mesh.attach(wireframe_filter)
        v.add(mesh)
        from vispy.visuals.transforms import STTransform
        mesh.transform = STTransform(translate=(20, 20))
        mesh.transforms.scene_transform = STTransform(scale=(1, 1, 0.01))

        rendered_with_wf = c.render()
        assert np.unique(rendered_with_wf[..., 0]).size >= 50

        wireframe_filter.enabled = False
        rendered_wo_wf = c.render()
        # the result should be completely different
        # assert not allclose
        pytest.raises(AssertionError, np.testing.assert_allclose,
                      rendered_with_wf, rendered_wo_wf)

        wireframe_filter.enabled = True
        wireframe_filter.wireframe_only = True
        rendered_with_wf_only = c.render()
        # the result should be different from the two cases above
        pytest.raises(AssertionError, np.testing.assert_allclose,
                      rendered_with_wf_only, rendered_with_wf)
        pytest.raises(AssertionError, np.testing.assert_allclose,
                      rendered_with_wf_only, rendered_wo_wf)

        wireframe_filter.enabled = True
        wireframe_filter.wireframe_only = False
        wireframe_filter.faces_only = True
        rendered_with_faces_only = c.render()
        # the result should be different from the cases above
        pytest.raises(AssertionError, np.testing.assert_allclose,
                      rendered_with_faces_only, rendered_with_wf)
        pytest.raises(AssertionError, np.testing.assert_allclose,
                      rendered_with_faces_only, rendered_wo_wf)
        pytest.raises(AssertionError, np.testing.assert_allclose,
                      rendered_with_faces_only, rendered_with_wf_only)


def _mesh_update_data(dims=3):
    vertices = np.array([[-1, 0, 0], [1, 0, 0], [0, 1, 2]], dtype=np.float32)
    return vertices[:, :dims], np.array([[0, 1, 2]], dtype=np.uint32)


@pytest.mark.parametrize('use_meshdata', [False, True])
def test_mesh_set_data_refreshes_warm_bounds(use_meshdata):
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    assert [mesh.bounds(i) for i in range(3)] == [(-1, 1), (0, 1), (0, 2)]
    replacement = vertices * 2 + (10, 20, 30)
    if use_meshdata:
        mesh.set_data(meshdata=MeshData(vertices=replacement, faces=faces))
    else:
        mesh.set_data(vertices=replacement, faces=faces)
    assert [mesh.bounds(i) for i in range(3)] == [(8, 12), (20, 22), (30, 34)]


def test_mesh_empty_populated_empty_bounds():
    mesh = MeshVisual()
    other = mesh.view()
    assert other.bounds(0) is mesh.bounds(0) is None
    vertices, faces = _mesh_update_data()
    mesh.set_data(vertices=vertices, faces=faces)
    assert other.bounds(0) == mesh.bounds(0) == (-1, 1)
    mesh.set_data(meshdata=MeshData())
    assert all(other.bounds(i) is mesh.bounds(i) is None for i in range(3))


@pytest.mark.parametrize('initial_dims,final_dims', [(2, 3), (3, 2)])
@pytest.mark.parametrize('query_first', ['existing', 'late'])
def test_mesh_dimension_replacement_bounds(initial_dims, final_dims, query_first):
    initial, faces = _mesh_update_data(initial_dims)
    final, _ = _mesh_update_data(final_dims)
    mesh = MeshVisual(vertices=initial, faces=faces)
    existing = mesh.view()
    peer = mesh.view()
    assert existing.bounds(2) == ((0, 0) if initial_dims == 2 else (0, 2))
    mesh.set_data(vertices=final, faces=faces)
    late = mesh.view()
    first = existing if query_first == 'existing' else late
    expected = [(-1, 1), (0, 1), (0, 0) if final_dims == 2 else (0, 2)]
    for axis in range(3):
        assert first.bounds(axis) == expected[axis]
        assert mesh.bounds(axis) == peer.bounds(axis) == late.bounds(axis) == expected[axis]


def test_mesh_existing_and_late_view_first_bounds():
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    existing = mesh.view()
    assert existing.bounds(0) == (-1, 1)
    assert mesh.bounds(0) == (-1, 1)
    mesh.set_data(vertices=vertices + (10, 0, 0), faces=faces)
    assert existing.bounds(0) == (9, 11)
    assert mesh.bounds(0) == (9, 11)
    late = mesh.view()
    mesh.set_data(vertices=vertices + (20, 0, 0), faces=faces)
    assert late.bounds(0) == (19, 21)
    assert existing.bounds(0) == mesh.bounds(0) == (19, 21)


def test_surface_plot_replacement_refreshes_mesh_bounds():
    z = np.arange(6, dtype=np.float32).reshape(2, 3)
    surface = SurfacePlotVisual(z=z, shading=None)
    assert [surface.bounds(i) for i in range(3)] == [(0, 1), (0, 2), (0, 5)]
    surface.set_data(z=z + 10)
    assert [surface.bounds(i) for i in range(3)] == [(0, 1), (0, 2), (10, 15)]


def test_mesh_bounds_are_ready_when_update_is_emitted():
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    assert mesh.bounds(0) == (-1, 1)
    observed = []
    mesh.events.update.connect(lambda event: observed.append(mesh.bounds(0)))
    mesh.set_data(vertices=vertices + (5, 0, 0), faces=faces)
    assert observed == [(4, 6)]


def test_mesh_color_only_update_preserves_geometry_bounds():
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    expected = [mesh.bounds(i) for i in range(3)]
    mesh.color = 'red'
    assert [mesh.bounds(i) for i in range(3)] == expected
    np.testing.assert_array_equal(mesh.mesh_data.get_vertices(), vertices)


def test_mesh_invalid_color_keeps_bounds_consistent_with_committed_geometry():
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    assert mesh.bounds(0) == (-1, 1)
    events = []
    mesh.events.update.connect(lambda event: events.append(event))
    # Existing API commits geometry before parsing color. Do not claim rollback.
    with pytest.raises(ValueError):
        mesh.set_data(vertices=vertices + (7, 0, 0), faces=faces, color='not-a-color')
    np.testing.assert_array_equal(mesh.mesh_data.get_vertices(), vertices + (7, 0, 0))
    assert mesh.bounds(0) == (6, 8)
    assert events == []


@pytest.mark.parametrize('entrypoint', ['prepare', 'draw'])
def test_mesh_empty_view_skips_renderer_work(entrypoint):
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    other = mesh.view()
    mesh._prepare_draw(None)
    mesh.set_data(meshdata=MeshData())
    if entrypoint == 'prepare':
        assert other._prepare_draw(other) is False
    else:
        with patch.object(other, '_configure_gl_state', side_effect=AssertionError('empty view configured GL')) as configure, \
                patch.object(other.view_program, 'draw', side_effect=AssertionError('empty view drew')) as draw:
            other.draw()
        assert configure.call_count == draw.call_count == 0


def test_meshdata_vertex_notification_refreshes_view_first_bounds():
    vertices, faces = _mesh_update_data()
    meshdata = MeshData(vertices=vertices, faces=faces)
    mesh = MeshVisual(meshdata=meshdata)
    other = mesh.view()
    assert other.bounds(0) == (-1, 1)
    meshdata.set_vertices(vertices + (9, 0, 0))
    mesh.mesh_data_changed()
    assert other.bounds(0) == mesh.bounds(0) == (8, 10)


@pytest.mark.parametrize('attribute,value', [('color', 'red'), ('cmap', 'grays'), ('clim', (0, 2))])
def test_mesh_non_geometry_notifications_do_not_scan_bounds(attribute, value):
    vertices, faces = _mesh_update_data()
    mesh = MeshVisual(vertices=vertices, faces=faces)
    assert mesh.bounds(0) == (-1, 1)
    with patch.object(mesh.mesh_data, 'get_bounds', wraps=mesh.mesh_data.get_bounds) as get_bounds:
        setattr(mesh, attribute, value)
    assert get_bounds.call_count == 0
    assert mesh.bounds(0) == (-1, 1)


def test_instanced_mesh_bounds_survive_base_notifications():
    vertices, faces = _mesh_update_data()
    mesh = InstancedMeshVisual(vertices=vertices, faces=faces,
                               instance_positions=np.array([[10, 0, 0]], dtype=np.float32),
                               instance_transforms=np.eye(3, dtype=np.float32)[None],
                               instance_colors=np.ones((1, 4), dtype=np.float32))
    assert mesh.bounds(0) == (9, 11)
    mesh.color = 'red'
    assert mesh.bounds(0) == (9, 11)
    mesh.mesh_data.set_vertices(vertices + (3, 0, 0))
    mesh.mesh_data_changed()
    assert mesh.bounds(0) == (12, 14)


run_tests_if_main()
