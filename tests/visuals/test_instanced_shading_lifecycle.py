# SPDX-License-Identifier: AGPL-3.0-only
"""Provider-free shading factory, source rebinding and late-filter lifecycle."""
import numpy as np
import pytest
from vispy.visuals import MeshVisual, InstancedMeshVisual
from vispy.visuals.filters import ShadingFilter, InstancedShadingFilter, WireframeFilter


def mesh(shading='smooth', populated=True, transforms=None):
    return InstancedMeshVisual(
        vertices=np.array([[0,0,0],[1,0,.3],[0,1,0]],np.float32) if populated else None,
        faces=np.array([[0,1,2]],np.uint32) if populated else None,
        instance_positions=np.zeros((2,3),np.float32),
        instance_transforms=np.repeat(np.eye(3,dtype=np.float32)[None],2,axis=0)
            if transforms is None else transforms,
        shading=shading)


@pytest.mark.parametrize('mode',[None,'flat','smooth'])
def test_factory_waits_for_instance_inputs_and_selects_correct_filter(mode):
    value=mesh(shading=mode)
    if mode is None:
        assert value.shading_filter is None
        value.shading='smooth'
    assert isinstance(value.shading_filter,InstancedShadingFilter)
    for axis,buffer in zip('xyz',value._instance_transforms_vbos):
        assert value.shading_filter.vshader['instance_transform_'+axis].value is buffer


def test_regular_mesh_keeps_standard_filter():
    value=MeshVisual(vertices=np.array([[0,0,0],[1,0,0],[0,1,0]],np.float32),
                     faces=np.array([[0,1,2]],np.uint32),shading='smooth')
    assert type(value.shading_filter) is ShadingFilter


def test_deferred_template_recovers_with_requested_shading():
    value=mesh(populated=False)
    assert value.shading=='smooth' and value.shading_filter is None
    assert value._prepare_draw(view=value) is False
    value.set_data(vertices=np.array([[0,0,0],[1,0,0],[0,1,0]],np.float32),
                   faces=np.array([[0,1,2]],np.uint32))
    assert value._prepare_draw(view=value) is None
    assert isinstance(value.shading_filter,InstancedShadingFilter)


def test_transform_reassignment_rebinds_normals_without_uniform_churn():
    value=mesh();value._prepare_draw(view=value)
    shader=value.shading_filter.vshader
    variables=[shader['instance_transform_'+axis] for axis in 'xyz']
    states=[variable.state_id for variable in variables]
    value.shading_filter.light_dir=(1,2,-3)
    assert [variable.state_id for variable in variables]==states
    old=value._instance_transforms_vbos
    value.instance_transforms=np.repeat(np.diag([2.,3.,4.]).astype(np.float32)[None],2,axis=0)
    assert value._instance_transforms_vbos is not old
    value._prepare_draw(view=value)
    for variable,buffer in zip(variables,value._instance_transforms_vbos):
        assert variable.value is buffer
    assert [variable.state_id for variable in variables]!=states


def test_subclass_filter_factory_remains_overridable():
    class CustomFilter(InstancedShadingFilter):
        pass
    class CustomMesh(InstancedMeshVisual):
        _shading_filter_class=CustomFilter
    value=CustomMesh(vertices=np.array([[0,0,0],[1,0,0],[0,1,0]],np.float32),
                     faces=np.array([[0,1,2]],np.uint32),instance_positions=np.zeros((1,3),np.float32),
                     instance_transforms=np.eye(3,dtype=np.float32)[None],shading='smooth')
    assert type(value.shading_filter) is CustomFilter


def test_late_wireframe_attachment_populates_without_geometry_update():
    value=mesh();value._prepare_draw(view=value)
    assert value._data_changed is False
    overlay=WireframeFilter()
    assert overlay._bc.size==0
    value.attach(overlay)
    assert overlay._bc.size==3 and value._data_changed is False
    value.detach(overlay)
    value.attach(overlay)
    assert overlay._bc.size==3


def test_empty_instance_stream_filter_is_valid_until_repopulated():
    value=mesh(transforms=np.empty((0,3,3),np.float32))
    assert isinstance(value.shading_filter,InstancedShadingFilter)
    assert value._prepare_draw(view=value) is False
    value.instance_transforms=np.repeat(np.eye(3,dtype=np.float32)[None],2,axis=0)
    assert value._prepare_draw(view=value) is None
    for axis,buffer in zip('xyz',value._instance_transforms_vbos):
        assert value.shading_filter.vshader['instance_transform_'+axis].value is buffer


def test_wireframe_style_updates_reuse_barycentric_payload():
    value=mesh();value._prepare_draw(view=value)
    overlay=WireframeFilter();value.attach(overlay)
    overlay._bc.glir.clear()
    overlay.color='red'
    overlay.width=2.5
    assert overlay._bc.glir.clear()==[] and overlay._bc.size==3
    value.set_data(vertices=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],np.float32),
                   faces=np.array([[0,1,2],[0,2,3]],np.uint32))
    value._prepare_draw(view=value)
    commands=overlay._bc.glir.clear()
    assert overlay._bc.size==6 and any(c[0]=='DATA' for c in commands)
