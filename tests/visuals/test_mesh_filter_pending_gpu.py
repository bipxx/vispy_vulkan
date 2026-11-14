# SPDX-License-Identifier: AGPL-3.0-only
"""Queued mesh draws retain filter revisions until their dependent captures."""
import gc
import os
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (32, 24)


@pytest.fixture
def mesh_canvas():
    from vispy import _dawn, scene
    canvas = scene.SceneCanvas(app='dawn_headless', size=SIZE, show=False,
                               bgcolor='black', config={'samples': 0})
    try:
        yield canvas
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


@pytest.mark.parametrize('mutation', ['texture', 'enabled', 'planes', 'detach'])
def test_mesh_filter_revision_preserves_earlier_target(mutation, mesh_canvas):
    from vispy import _dawn, gloo, scene
    from vispy.visuals.filters import TextureFilter
    from vispy.visuals.filters.clipping_planes import PlanesClipper

    canvas = mesh_canvas
    canvas.set_current()
    view = canvas.central_widget.add_view(border_width=0)
    canvas.central_widget.border_width = 0
    view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, *SIZE), aspect=None,
                                            flip=(False, True, False))
    vertices = np.array([[0, 0, 0], [32, 0, 0], [0, 24, 0], [32, 24, 0]], np.float32)
    mesh = scene.visuals.Mesh(vertices=vertices,
                              faces=np.array([[0, 1, 2], [1, 3, 2]], np.uint32),
                              color='white', shading=None, parent=view.scene)
    texture = TextureFilter(np.array([[[255, 0, 0, 255]]], np.uint8),
                            np.array([[0, 0], [1, 0], [0, 1], [1, 1]], np.float32))
    planes = PlanesClipper(np.array([[[8, 0, 0], [1, 0, 0]]], np.float32),
                           coord_system='visual')
    mesh.attach(texture)
    mesh.attach(planes)
    mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)
    attachments = [gloo.RenderBuffer(SIZE[::-1], format='color') for _ in range(2)]
    targets = [gloo.FrameBuffer(color=color) for color in attachments]
    expected_before = np.zeros((24, 32, 4), np.uint8)
    expected_before[..., 3] = 255
    expected_before[:, 8:] = [255, 0, 0, 255]
    expected_after = expected_before.copy()
    if mutation == 'texture':
        expected_after[:, 8:] = [0, 255, 0, 255]
    elif mutation == 'enabled':
        expected_after[:, 8:] = [255, 255, 255, 255]
    elif mutation == 'planes':
        expected_after[..., :3] = 0
        expected_after[:12, 16:] = [255, 0, 0, 255]
    else:
        expected_after[:] = [255, 255, 255, 255]

    def draw(target):
        canvas.push_fbo(target, (0, 0), SIZE)
        try:
            gloo.clear(color=(0., 0., 0., 1.), depth=False)
            canvas.draw_visual(canvas.scene)
        finally:
            canvas.pop_fbo()

    try:
        draw(targets[0])
        pending_before = _dawn.probe()['pending_draws']
        assert pending_before > 0, 'The earlier draw must actually remain pending'
        # No read, finish, event pump or presentation before the revision.
        if mutation == 'texture':
            texture.texture = np.array([[[0, 255, 0, 255]]], np.uint8)
        elif mutation == 'enabled':
            texture.enabled = False
        elif mutation == 'planes':
            planes.clipping_planes = np.array([[[16, 0, 0], [1, 0, 0]],
                                               [[0, 12, 0], [0, -1, 0]]], np.float32)
        else:
            mesh.detach(planes)
            mesh.detach(texture)
        draw(targets[1])
        pending_after = _dawn.probe()['pending_draws']
        assert pending_after > pending_before, 'Both filter revisions must be pending'
        with targets[0]:
            before = targets[0].read()
        with targets[1]:
            after = targets[1].read()
        if directory := os.environ.get('VISPY_MESH_PENDING_EVIDENCE'):
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(path / (mutation + '.npz'), before=before,
                                after=after, expected_before=expected_before,
                                expected_after=expected_after,
                                pending_before=pending_before, pending_after=pending_after)
        np.testing.assert_array_equal(before, expected_before)
        np.testing.assert_array_equal(after, expected_after)
        print('mesh pending filter revision exact before/after:', mutation,
              'native pending draws:', pending_before, pending_after)
    finally:
        for target in targets:
            target.delete()
        for color in attachments:
            color.delete()
