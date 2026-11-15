# SPDX-License-Identifier: AGPL-3.0-only
"""GPU acceptance for SCI-02, SCI-02-CLIP-ALPHA-BLEND, and SCI-05 (E03): mesh filter composition, order, picking, and MSAA."""
from __future__ import annotations

import gc
import struct

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (32, 24)


def test_mesh_clip_alpha_color_translucent_blend_queued_revisions():
    """Verify PlanesClipper + Clipper + ColorFilter + Alpha over translucent background across 3 queued revisions."""
    from vispy import _dawn, gloo, scene
    from vispy.visuals.filters import Alpha, Clipper, ColorFilter
    from vispy.visuals.filters.clipping_planes import PlanesClipper

    canvas = scene.SceneCanvas(
        app='dawn_headless', size=SIZE, show=False, bgcolor='black', config={'samples': 0}
    )
    attachments, targets = [], []
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(
            rect=(0, 0, *SIZE), aspect=None, flip=(False, True, False)
        )

        # Full-view opaque blue backdrop (RGBA = [0, 0, 200, 255]).
        bg_mesh = scene.visuals.Mesh(
            vertices=np.array([[0, 0, 0], [32, 0, 0], [0, 24, 0], [32, 24, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(0.0, 0.0, 200.0 / 255.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        bg_mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)
        bg_mesh.order = 0

        # Foreground white mesh filtered by PlanesClipper (x >= 8), Clipper (GL y in [4, 20]), ColorFilter, and Alpha.
        fg_mesh = scene.visuals.Mesh(
            vertices=np.array([[0, 0, 0], [32, 0, 0], [0, 24, 0], [32, 24, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color='white',
            shading=None,
            parent=view.scene,
        )
        fg_mesh.order = 1
        planes = PlanesClipper(
            np.array([[[8.0, 0.0, 0.0], [1.0, 0.0, 0.0]]], dtype=np.float32),
            coord_system='visual',
        )
        rect_clip = Clipper(bounds=(0, 4, 32, 16))
        tint = ColorFilter((1.0, 0.5, 0.0, 1.0))
        alpha = Alpha(0.5)
        for flt in (planes, rect_clip, tint, alpha):
            fg_mesh.attach(flt)
        fg_mesh.set_gl_state(
            blend=True,
            blend_func=('src_alpha', 'one_minus_src_alpha', 'one', 'one_minus_src_alpha'),
            depth_test=False,
            cull_face=False,
        )

        attachments = [gloo.RenderBuffer(SIZE[::-1], format='color') for _ in range(3)]
        targets = [gloo.FrameBuffer(color=c) for c in attachments]

        def draw_fbo(fbo):
            canvas.push_fbo(fbo, (0, 0), SIZE)
            try:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=False)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            return _dawn.probe()['pending_draws']

        p0 = draw_fbo(targets[0])
        # Revision 1: shift clip plane to x >= 16, update tint to green-cyan (0, 1, 0.5), alpha to 0.75.
        planes.clipping_planes = np.array([[[16.0, 0.0, 0.0], [1.0, 0.0, 0.0]]], dtype=np.float32)
        tint.filter = (0.0, 1.0, 0.5, 1.0)
        alpha.alpha = 0.75
        p1 = draw_fbo(targets[1])

        # Revision 2: restore initial clip plane, tint, and alpha before any readback!
        planes.clipping_planes = np.array([[[8.0, 0.0, 0.0], [1.0, 0.0, 0.0]]], dtype=np.float32)
        tint.filter = (1.0, 0.5, 0.0, 1.0)
        alpha.alpha = 0.5
        p2 = draw_fbo(targets[2])

        assert 0 < p0 < p1 < p2, 'All three clipped/blended revisions must remain queued'

        frames = []
        for fbo in targets:
            with fbo:
                frames.append(fbo.read())

        np.testing.assert_array_equal(frames[0], frames[2])
        # Unclipped left region (x=4, y=12) and top/bottom outside Clipper (x=20, y=1) remain pure backdrop [0, 0, 200, 255].
        np.testing.assert_allclose(frames[0][12, 4], [0, 0, 200, 255], atol=2)
        np.testing.assert_allclose(frames[0][1, 20], [0, 0, 200, 255], atol=2)
        # Frame 0 interior (x=12, y=12): 0.5 * (255, 127.5, 0) + 0.5 * (0, 0, 200) = (128, 64, 100, 255).
        np.testing.assert_allclose(frames[0][12, 12], [128, 64, 100, 255], atol=2)
        np.testing.assert_allclose(frames[0][12, 24], [128, 64, 100, 255], atol=2)
        # Frame 1: x=12 is now clipped out -> pure backdrop; x=24 is blended 0.75*(0, 255, 127.5) + 0.25*(0, 0, 200) = (0, 191, 146, 255).
        np.testing.assert_allclose(frames[1][12, 12], [0, 0, 200, 255], atol=2)
        np.testing.assert_allclose(frames[1][12, 24], [0, 191, 146, 255], atol=2)
    finally:
        for fbo in targets:
            fbo.delete()
        for rb in attachments:
            rb.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()


def test_filter_composition_order_sensitivity_detach_and_reattach():
    """Verify non-commutative post-fragment filter fpos ordering and exact detach/reattach restoration."""
    from vispy import _dawn, scene
    from vispy.visuals.filters import ColorFilter
    from vispy.visuals.filters.base_filter import Filter

    class AdditiveBiasFilter(Filter):
        def __init__(self, bias, fpos):
            super().__init__(
                fcode='void add_bias() { gl_FragColor.rgb = clamp(gl_FragColor.rgb + $bias, 0.0, 1.0); }',
                fhook='post',
                fpos=fpos,
            )
            self.fshader['bias'] = tuple(float(x) for x in bias)

    canvas = scene.SceneCanvas(
        app='dawn_headless', size=(16, 16), show=False, bgcolor='black', config={'samples': 0}
    )
    try:
        canvas.set_current()
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, 16, 16), aspect=None)
        mesh = scene.visuals.Mesh(
            vertices=np.array([[0, 0, 0], [16, 0, 0], [0, 16, 0], [16, 16, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(0.2, 0.4, 0.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)

        # ColorFilter uses default fpos=8:
        # Order A: bias_pre (fpos=3) runs BEFORE ColorFilter (fpos=8) -> ((0.2, 0.4, 0.0) + (0.4, 0.2, 0.5)) * 0.5 = (0.3, 0.3, 0.25) -> [77, 77, 64]
        # Order B: bias_post (fpos=12) runs AFTER ColorFilter (fpos=8) -> ((0.2, 0.4, 0.0) * 0.5) + (0.4, 0.2, 0.5) = (0.5, 0.4, 0.5) -> [128, 102, 128]
        tint = ColorFilter((0.5, 0.5, 0.5, 1.0))
        bias_pre = AdditiveBiasFilter((0.4, 0.2, 0.5), fpos=3)
        bias_post = AdditiveBiasFilter((0.4, 0.2, 0.5), fpos=12)

        mesh.attach(bias_pre)
        mesh.attach(tint)
        img_order_a = np.array(canvas.render(size=(16, 16), alpha=True), copy=True)
        np.testing.assert_allclose(img_order_a[8, 8], [77, 77, 64, 255], atol=2)

        mesh.detach(bias_pre)
        mesh.attach(bias_post)
        img_order_b = np.array(canvas.render(size=(16, 16), alpha=True), copy=True)
        np.testing.assert_allclose(img_order_b[8, 8], [128, 102, 128, 255], atol=2)

        # Restore Order A via detach/reattach and verify byte-exact restoration.
        mesh.detach(bias_post)
        mesh.attach(bias_pre)
        img_restored = np.array(canvas.render(size=(16, 16), alpha=True), copy=True)
        np.testing.assert_array_equal(img_restored, img_order_a)
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


@pytest.mark.parametrize('samples', [0, 4])
def test_mesh_picking_filter_id_decoding_and_msaa_visual_restoration(samples):
    """Verify VisualNode PickingFilter uint32 ID encoding on interactive meshes and MSAA visual restoration."""
    from vispy import _dawn, gloo, scene

    canvas = scene.SceneCanvas(
        app='dawn_headless',
        size=SIZE,
        show=False,
        bgcolor='black',
        config={'samples': samples},
    )
    pick_rb = pick_fbo = None
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(
            rect=(0, 0, *SIZE), aspect=None, flip=(False, True, False)
        )

        mesh_left = scene.visuals.Mesh(
            vertices=np.array([[2, 4, 0], [12, 4, 0], [2, 20, 0], [12, 20, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(1.0, 0.0, 0.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        mesh_left.interactive = True
        mesh_left.opacity = 0.5

        mesh_mid = scene.visuals.Mesh(
            vertices=np.array([[14, 4, 0], [22, 4, 0], [14, 20, 0], [22, 20, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(0.0, 1.0, 0.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        mesh_mid.interactive = True
        mesh_mid.opacity = 0.5

        # Non-interactive mesh must NOT emit a picking ID during picking pass.
        mesh_non_interactive = scene.visuals.Mesh(
            vertices=np.array([[24, 4, 0], [30, 4, 0], [24, 20, 0], [30, 20, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
            color=(0.0, 0.0, 1.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        mesh_non_interactive.interactive = False
        mesh_non_interactive.opacity = 0.5

        before_visual = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_allclose(before_visual[12, 7, :3], [128, 0, 0], atol=2)
        np.testing.assert_allclose(before_visual[12, 18, :3], [0, 128, 0], atol=2)
        np.testing.assert_allclose(before_visual[12, 27, :3], [0, 0, 128], atol=2)

        # Single-sample integer-decodable RGBA picking pass (blend suppressed automatically by mesh.picking = True).
        pick_rb = gloo.RenderBuffer(SIZE[::-1], format='color')
        pick_depth = gloo.RenderBuffer(SIZE[::-1], format='depth')
        pick_fbo = gloo.FrameBuffer(color=pick_rb, depth=pick_depth)
        canvas.scene.picking = True
        try:
            canvas.push_fbo(pick_fbo, (0, 0), SIZE)
            try:
                gloo.clear(color=(0.0, 0.0, 0.0, 0.0), depth=True)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            with pick_fbo:
                pick_img = pick_fbo.read(alpha=True)
        finally:
            canvas.scene.picking = False

        decode_id = lambda rgba: struct.unpack('<I', bytes(rgba))[0]
        assert decode_id(pick_img[12, 7]) == mesh_left._id
        assert decode_id(pick_img[12, 18]) == mesh_mid._id
        # Non-interactive mesh is skipped during picking pass, exposing interactive ViewBox widget ID underneath!
        assert decode_id(pick_img[12, 27]) == view._id != mesh_non_interactive._id
        assert decode_id(pick_img[1, 1]) == view._id

        # Normal translucent MSAA/1x rendering restores cleanly after picking=False.
        after_visual = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        np.testing.assert_array_equal(after_visual, before_visual)
    finally:
        if pick_fbo is not None:
            pick_fbo.delete()
        if pick_rb is not None:
            pick_rb.delete()
        if 'pick_depth' in locals() and pick_depth is not None:
            pick_depth.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()
