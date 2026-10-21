"""CPU-only topology synchronization of real mesh texture-coordinate buffers."""
from unittest.mock import patch

import numpy as np
import pytest

from vispy.visuals.filters import TextureFilter
from vispy.visuals.mesh import MeshVisual


def _texture_filter_mesh():
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0],
                         [1, 1, 0], [2, 1, 0]], dtype=np.float32)
    faces = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
    texcoords = np.array([[.1, .1], [.9, .1], [.1, .9],
                         [.9, .9], [.5, .5]], dtype=np.float32)
    mesh = MeshVisual(vertices=vertices, faces=faces)
    filt = TextureFilter(np.ones((2, 2, 3), dtype=np.uint8), texcoords)
    mesh.attach(filt)
    mesh._prepare_draw(None)
    return mesh, filt, vertices, faces, texcoords


def _take_texcoord_data(filt):
    buffer = filt._texcoords_buffer
    return [command[3][command[3].dtype.names[0]].reshape(-1, 2).copy()
            for command in buffer.glir.clear()
            if command[0] == 'DATA' and command[1] == buffer.id]


@pytest.mark.parametrize('kind', ['reorder', 'grow', 'shrink'])
def test_texture_filter_follows_replacement_faces(kind):
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    replacement = {'reorder': faces[::-1, ::-1].copy(),
                   'grow': np.array([[0, 1, 4], [1, 3, 2], [4, 3, 0]], dtype=np.uint32),
                   'shrink': faces[:1].copy()}[kind]
    mesh.set_data(vertices=vertices, faces=replacement)
    assert _take_texcoord_data(filt) == []
    mesh._prepare_draw(None)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], texcoords[replacement].reshape(-1, 2))
    assert filt._texcoords_buffer.size == mesh.mesh_data.get_vertices(indexed='faces').reshape(-1, 3).shape[0]
    mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []


def test_texture_filter_position_only_and_resident_reuse():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    initial = _take_texcoord_data(filt)
    assert len(initial) == 1
    np.testing.assert_array_equal(initial[0], texcoords[faces].reshape(-1, 2))
    mesh.set_data(vertices=vertices + 1, faces=faces.copy())
    mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []
    mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []


def test_texture_filter_public_uv_replacement_and_inplace_resubmission():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    replacement = texcoords.copy()
    replacement[:, 0] *= .5
    filt.texcoords = replacement
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], replacement[faces].reshape(-1, 2))
    replacement[:, 1] *= .5
    filt.texcoords = replacement
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], replacement[faces].reshape(-1, 2))
    filt.texcoords = replacement.copy()
    assert _take_texcoord_data(filt) == []


def test_texture_filter_detach_and_reattach_current_topology_once():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    mesh.detach(filt)
    replacement = faces[::-1].copy()
    mesh.set_data(vertices=vertices, faces=replacement)
    mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []
    mesh.attach(filt)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], texcoords[replacement].reshape(-1, 2))
    mesh.set_data(vertices=vertices, faces=faces)
    mesh._prepare_draw(None)
    assert len(_take_texcoord_data(filt)) == 1
    mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []


def test_texture_filter_failed_buffer_update_can_retry_same_uv_values():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    replacement = texcoords * .75
    with patch.object(filt._texcoords_buffer, 'set_data', side_effect=RuntimeError('queued upload refused')):
        with pytest.raises(RuntimeError, match='queued upload refused'):
            filt.texcoords = replacement
    assert _take_texcoord_data(filt) == []
    filt.texcoords = replacement
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], replacement[faces].reshape(-1, 2))


def test_texture_filter_invalid_uv_index_explicit_topology_retry():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    # Vertex 5 is legal mesh geometry but has no texture coordinate.
    bigger_vertices = np.concatenate((vertices, [[3, 2, 0]]), axis=0).astype(np.float32)
    bad_faces = np.array([[0, 1, 5]], dtype=np.uint32)
    mesh.events.data_updated.ignore_callback_errors = False
    mesh.set_data(vertices=bigger_vertices, faces=bad_faces)
    with pytest.raises(IndexError):
        mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []
    # Existing callback error policy is preserved; retry is a new public update.
    replacement = faces[::-1].copy()
    mesh.set_data(vertices=vertices, faces=replacement)
    mesh._prepare_draw(None)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], texcoords[replacement].reshape(-1, 2))


def test_texture_filter_two_pending_changes_prepare_only_final_faces():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    mesh.set_data(vertices=vertices, faces=faces[::-1].copy())
    final = np.array([[4, 2, 0]], dtype=np.uint32)
    mesh.set_data(vertices=vertices, faces=final)
    assert _take_texcoord_data(filt) == []
    mesh._prepare_draw(None)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], texcoords[final].reshape(-1, 2))


def test_texture_filter_inplace_faces_via_meshdata_setter():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    current_faces = mesh.mesh_data.get_faces()
    current_faces[:] = current_faces[::-1, ::-1].copy()
    # MeshData's public setter also invalidates its expanded-position cache.
    mesh.mesh_data.set_faces(current_faces)
    mesh.mesh_data_changed()
    mesh._prepare_draw(None)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], texcoords[current_faces].reshape(-1, 2))


def _texture_filter_callback_count(mesh, filt):
    return sum(isinstance(callback, tuple) and callback[0]() is filt
               for callback in mesh.events.data_updated.callbacks)


def test_texture_filter_one_subscription_per_attachment():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    assert _texture_filter_callback_count(mesh, filt) == 1
    mesh.detach(filt)
    assert _texture_filter_callback_count(mesh, filt) == 0
    mesh.attach(filt)
    assert _texture_filter_callback_count(mesh, filt) == 1
    mesh.detach(filt)
    assert _texture_filter_callback_count(mesh, filt) == 0


def test_texture_filter_color_only_change_reuses_uvs():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    mesh.color = 'red'
    mesh._prepare_draw(None)
    assert _take_texcoord_data(filt) == []


def test_texture_filter_new_vertex_and_uv_row_follow_geometry():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    bigger_vertices = np.concatenate((vertices, [[2, 2, 0]]), axis=0).astype(np.float32)
    bigger_uv = np.concatenate((texcoords, [[.2, .8]]), axis=0).astype(np.float32)
    filt.texcoords = bigger_uv
    _take_texcoord_data(filt)
    replacement = np.array([[0, 4, 5]], dtype=np.uint32)
    mesh.set_data(vertices=bigger_vertices, faces=replacement)
    mesh._prepare_draw(None)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], bigger_uv[replacement].reshape(-1, 2))


def test_texture_filter_ignored_callback_failure_explicit_retry():
    mesh, filt, vertices, faces, texcoords = _texture_filter_mesh()
    _take_texcoord_data(filt)
    replacement = faces[::-1].copy()
    mesh.set_data(vertices=vertices, faces=replacement)
    assert mesh.events.data_updated.ignore_callback_errors is True
    with patch.object(filt._texcoords_buffer, 'set_data', side_effect=RuntimeError('deferred UV failure')) as upload:
        mesh._prepare_draw(None)
    assert upload.call_count == 1
    assert _take_texcoord_data(filt) == []
    # Preserve the existing emitter policy; this is an explicit caller retry.
    mesh.mesh_data_changed()
    mesh._prepare_draw(None)
    updates = _take_texcoord_data(filt)
    assert len(updates) == 1
    np.testing.assert_array_equal(updates[0], texcoords[replacement].reshape(-1, 2))
