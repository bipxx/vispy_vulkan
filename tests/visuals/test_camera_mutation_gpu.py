# SPDX-License-Identifier: AGPL-3.0-only
"""Finite public TurntableCamera mutation and restoration acceptance."""
import os
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_mesh_layout_extensions import BACKGROUND, SIZE, compare, inputs
from tools.mesh_layout_reference import load_case

pytestmark = pytest.mark.gpu
INITIAL = dict(fov=45, elevation=25, azimuth=35, distance=4, center=(0, 0, 0))


def make_scene(values):
    from vispy import scene
    canvas = scene.SceneCanvas(app='dawn_headless', size=SIZE, dpi=96,
                               bgcolor=tuple(v / 255 for v in BACKGROUND),
                               show=False, decorate=False, config={'samples': 0})
    view = canvas.central_widget.add_view()
    camera = scene.cameras.TurntableCamera(**values)
    view.camera = camera
    data = inputs()
    vertices = (data['vertices'] - [112, 80, 16]) / [88, 56, 64]
    scene.visuals.Mesh(vertices=vertices.astype(np.float32), faces=data['faces'],
                       face_colors=np.array([[1, 0, 0, 1], [0, 1, 0, 1]], np.float32),
                       shading=None, parent=view.scene)
    return canvas, camera


def frame(canvas):
    return np.array(canvas.render(size=SIZE, alpha=True), copy=True)


@pytest.mark.parametrize('property,value', [('azimuth', 80), ('center', (.3, -.2, 0))])
def test_public_camera_mutation_matches_fresh_scene_and_restores(property, value):
    # Only the initial/restored pose has an independent frozen upstream oracle.
    # The changed pose additionally checks mutation versus fresh construction;
    # it is not represented as an independent upstream changed-pose reference.
    reference, _, _ = load_case('mesh_perspective')
    canvas, camera = make_scene(INITIAL)
    fresh = None
    try:
        before = frame(canvas)
        compare('mesh_perspective', before, reference)
        setattr(camera, property, value)
        changed = frame(canvas)
        assert np.count_nonzero(np.any(changed != before, axis=2)) > 100
        assert np.all(changed[..., 3] == 255)
        foreground = np.any(changed[..., :3] != BACKGROUND[:3], axis=2)
        assert np.count_nonzero(foreground) > 100, 'Mutation produced a blank scene'
        fresh, _ = make_scene(dict(INITIAL, **{property: value}))
        expected_changed = frame(fresh)
        assert int(np.abs(changed.astype(np.int16) - expected_changed).max()) <= 1
        fresh.close()
        fresh = None
        # Closing the independent comparison scene must not invalidate this one.
        np.testing.assert_array_equal(frame(canvas), changed)
        setattr(camera, property, INITIAL[property])
        restored = frame(canvas)
        compare('mesh_perspective', restored, reference)
        np.testing.assert_array_equal(restored, before)
        if directory := os.environ.get('VISPY_CAMERA_MUTATION_EVIDENCE'):
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(path / (property + '.npz'), before=before,
                                changed=changed, expected_changed=expected_changed,
                                restored=restored, reference=reference)
    finally:
        if fresh is not None:
            fresh.close()
        canvas.close()
