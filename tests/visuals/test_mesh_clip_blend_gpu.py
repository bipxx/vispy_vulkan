# SPDX-License-Identifier: AGPL-3.0-only
"""Clipped alpha blending preserves background and three queued revisions."""
import gc
import os
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (32, 24)


@pytest.mark.parametrize('mutation', ['alpha', 'alpha_zero', 'invalid_alpha'])
def test_clipped_alpha_blending_preserves_queued_revisions(mutation):
    from vispy import _dawn, gloo, scene
    from vispy.visuals.filters import Alpha, ColorFilter, TextureFilter
    from vispy.visuals.filters.clipping_planes import PlanesClipper

    canvas = scene.SceneCanvas(app='dawn_headless', size=SIZE, show=False,
                               bgcolor='black', config={'samples': 0})
    targets, attachments = [], []
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, *SIZE), aspect=None,
                                                flip=(False, True, False))
        mesh = scene.visuals.Mesh(
            vertices=np.array([[0, 0, 0], [32, 0, 0], [0, 24, 0], [32, 24, 0]], np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], np.uint32),
            color='white', shading=None, parent=view.scene)
        texture = TextureFilter(np.array([[[240, 160, 80, 255]]], np.uint8),
                                np.array([[0, 0], [1, 0], [0, 1], [1, 1]], np.float32))
        planes = PlanesClipper(np.array([[[8, 0, 0], [1, 0, 0]]], np.float32),
                               coord_system='visual')
        alpha = Alpha(.4)
        tint = ColorFilter((.5, 1., .25, 1.))
        for item in (texture, planes, alpha, tint):
            mesh.attach(item)
        mesh.set_gl_state(blend=True, blend_func=('src_alpha', 'one_minus_src_alpha',
                                                'one', 'one_minus_src_alpha'),
                          depth_test=False, cull_face=False)
        attachments = [gloo.RenderBuffer(SIZE[::-1], format='color') for _ in range(3)]
        targets = [gloo.FrameBuffer(color=color) for color in attachments]

        def expected(rgba):
            result = np.zeros((24, 32, 4), np.uint8)
            result[:] = [0, 0, 255, 255]
            result[:, 8:] = rgba
            return result

        baseline = expected([48, 64, 161, 255])
        changed = baseline.copy()
        # Straight-alpha RGB: source * a + opaque blue * (1-a).
        # Separate alpha factors preserve opaque destination alpha.
        changed[:, 8:] = ([0, 0, 255, 255] if mutation == 'alpha_zero'
                          else [96, 128, 67, 255])

        def draw(target):
            canvas.push_fbo(target, (0, 0), SIZE)
            try:
                gloo.clear(color=(0., 0., 1., 1.), depth=False)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            return _dawn.probe()['pending_draws']

        pending = [draw(targets[0])]
        assert pending[0] > 0
        # No read, flush, event pump or presentation between these revisions.
        if mutation == 'invalid_alpha':
            with pytest.raises(ValueError):
                alpha.alpha = 'invalid-number'
            alpha.alpha = .8
        else:
            alpha.alpha = .8 if mutation == 'alpha' else 0.
        pending.append(draw(targets[1]))
        alpha.alpha = .4
        pending.append(draw(targets[2]))
        assert pending[0] < pending[1] < pending[2], 'All three revisions must remain queued'
        frames = []
        for target in targets:
            with target:
                frames.append(target.read())
        # Allow one UNORM rounding unit in blended channels; clipped pixels
        # and opaque destination alpha are exact. Restoration must be exact.
        for actual, expected_frame in zip(frames, (baseline, changed, baseline)):
            difference = np.abs(actual.astype(np.int16) - expected_frame.astype(np.int16))
            assert int(difference.max()) <= 1
            np.testing.assert_array_equal(actual[:, :8], expected_frame[:, :8])
            assert np.all(actual[..., 3] == 255)
        np.testing.assert_array_equal(frames[2], frames[0])
        assert np.count_nonzero(np.any(frames[1] != frames[0], axis=2)) == 24 * 24
        if directory := os.environ.get('VISPY_CLIP_BLEND_EVIDENCE'):
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(path / (mutation + '.npz'), before=frames[0],
                                changed=frames[1], restored=frames[2],
                                expected_before=baseline, expected_changed=changed,
                                pending=np.array(pending))
    finally:
        for target in targets:
            target.delete()
        for color in attachments:
            color.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()
