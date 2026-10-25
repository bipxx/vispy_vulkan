# SPDX-License-Identifier: AGPL-3.0-only
"""Actual instanced visual/filter comparisons with CPU-expanded geometry."""
from pathlib import Path
import hashlib


def instanced_mesh_checks(scene, np, evidence=None, strict=True, records=None):
    canvas = scene.SceneCanvas(app='dawn_headless', size=(96, 64), show=False,
                               bgcolor='black', config={'samples': 0})
    vertices = np.array([[-.36,-.28,-.20],[.36,-.28,.20],[0,.32,0]], np.float32)
    faces = np.array([[0,1,2]], np.uint32)
    positions = np.array([[-.7,0,0],[.7,0,0]], np.float32)
    matrices = np.array([np.diag([.7,1,1.6]), [[.8,.15,0],[0,1,0],[.2,0,1.2]]], np.float32)
    colors = np.array([[.9,.2,.1,1],[.1,.6,.9,1]], np.float32)
    cases = [] if records is None else records
    try:
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(rect=(-1.5,-1,3,2), aspect=1)
        actual = scene.visuals.InstancedMesh(vertices=vertices,faces=faces,
            instance_positions=positions, instance_transforms=matrices,
            instance_colors=colors, color='white', shading='smooth', parent=view.scene)
        reference = scene.visuals.Mesh(vertices=vertices,faces=faces,color='white',
                                       shading='smooth', parent=view.scene)
        for visual in (actual, reference):
            light = visual.shading_filter
            light.ambient_coefficient = 1
            light.diffuse_coefficient = 1
            light.specular_coefficient = 0
            light.shininess = 0
            light.ambient_light = (1,1,1,.15)
            light.diffuse_light = (1,1,1,.85)
            light.specular_light = 0
            light.light_dir = (0,0,-1)

        def compare(name, empty=False):
            world = np.concatenate([vertices @ matrix.T + position
                                    for matrix,position in zip(matrices,positions)])
            indices = np.concatenate([faces + index*len(vertices) for index in range(len(positions))])
            reference.set_data(vertices=world,faces=indices,
                               vertex_colors=np.repeat(colors,len(vertices),axis=0),color='white')
            actual.visible=False
            reference.visible=not empty
            expected=canvas.render(alpha=True)
            reference.visible=False
            actual.visible=True
            observed=canvas.render(alpha=True)
            mask=np.max(expected[...,:3],axis=2)>3
            observed_mask=np.max(observed[...,:3],axis=2)>3
            interior=np.zeros_like(mask)
            interior[1:-1,1:-1]=np.logical_and.reduce([
                mask[1+y:mask.shape[0]-1+y,1+x:mask.shape[1]-1+x]
                for y in (-1,0,1) for x in (-1,0,1)])
            coverage=int(np.count_nonzero(mask ^ observed_mask))
            delta=int(np.max(np.abs(expected[interior].astype(int)-observed[interior].astype(int)))) if interior.any() else 0
            samples=int(interior.sum())
            passed=coverage<=2 and delta<=2 and (empty or samples>=20)
            record=dict(case=name,passed=passed,interior_samples=samples,interior_max_delta=delta,
                        coverage_difference=coverage,reference_peak=int(expected[...,:3].max()),
                        filter_class=type(actual.shading_filter).__name__,
                        expected_sha256=hashlib.sha256(expected.tobytes()).hexdigest(),
                        actual_sha256=hashlib.sha256(observed.tobytes()).hexdigest())
            cases.append(record)
            if evidence is not None and not passed:
                output=Path(evidence);output.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(output/(name+'.npz'),expected=expected,actual=observed)
            if strict:
                assert passed,record

        for visual in (actual,reference):visual.shading_filter.enabled=False
        compare('unshaded_geometry')
        for visual in (actual,reference):visual.shading_filter.enabled=True
        compare('nonuniform_smooth')
        for visual in (actual,reference):visual.shading_filter.light_dir=(0,0,1)
        compare('reverse_light')
        for visual in (actual,reference):visual.shading_filter.light_dir=(0,0,-1)
        matrices=np.array([[[.9,.2,0],[0,.8,0],[-.25,0,1]],
                           [[.8,0,0],[0,.8,-.6],[0,.6,.8]]],np.float32)
        actual.instance_transforms=matrices
        compare('reassigned_transforms')
        colors=np.array([[.2,.9,.3,1],[.8,.3,.6,1]],np.float32)
        actual.instance_colors=colors
        compare('reassigned_colors')
        matrices=np.array([np.diag([-.8,1.1,1]),np.diag([.8,1,0])],np.float32)
        actual.instance_transforms=matrices
        compare('reflection_and_rank_two')
        for visual in (actual,reference):visual.shading='flat'
        compare('flat_shading')
        for visual in (actual,reference):visual.shading='smooth'
        compare('smooth_again')
        from vispy.visuals.filters import WireframeFilter
        overlays=[WireframeFilter(color='white',width=1) for _ in range(2)]
        for visual,overlay in zip((actual,reference),overlays):visual.attach(overlay)
        compare('wireframe_attached')
        original_overlay=cases[-1]['actual_sha256']
        for overlay in overlays:
            overlay.width=2.5
            overlay.color='red'
        compare('wireframe_style_changed')
        assert cases[-1]['actual_sha256']!=original_overlay, 'style update did not affect pixels'
        for visual,overlay in zip((actual,reference),overlays):visual.detach(overlay)
        compare('wireframe_detached')
        actual.instance_positions=np.empty((0,3),np.float32)
        actual.instance_transforms=np.empty((0,3,3),np.float32)
        compare('empty_instances',empty=True)
        actual.instance_positions=positions
        actual.instance_transforms=matrices
        compare('repopulated_instances')
        for visual in (actual,reference):
            light=visual.shading_filter
            visual.detach(light)
            visual.attach(light)
        compare('shading_reattached')
        return cases
    finally:
        canvas.close()
