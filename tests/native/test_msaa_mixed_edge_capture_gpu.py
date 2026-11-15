# -*- coding: utf-8 -*-
"""GPU capture tests for LIF-05: samples=1 vs samples=4 offscreen/onscreen edge resolve & crop."""

import gc
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu

TEN_GAUGES = (
    'pending_tickets',
    'queued_frames',
    'live_buffer_bytes',
    'live_cpu_buffer_bytes',
    'live_texture_bytes',
    'canvas_texture_bytes',
    'transient_buffer_bytes',
    'line_resource_pool_busy_slots',
    'line_resource_pool_bytes',
    'host_import_pinned_bytes',
)

VERT_DIAG_SRC = """
attribute vec2 a_position;
uniform float u_depth;
void main() {
    gl_Position = vec4(a_position, u_depth, 1.0);
}
"""

FRAG_DIAG_SRC = """
uniform vec4 u_color;
void main() {
    gl_FragColor = u_color;
}
"""

# Tilted diagonal edge from (-0.75, -1.0) to (+0.75, +1.0), covering right half-plane.
# Non-45-degree slope (dx/dy = 0.75) avoids exact sample-position tie breaks.
TILTED_HALF_PLANE = np.array(
    [[-0.75, -1.0], [1.0, -1.0], [0.75, 1.0], [-0.75, -1.0], [1.0, -1.0], [1.0, 1.0]],
    dtype=np.float32,
)


def _ten_gauges(_dawn):
    probe = _dawn.probe()
    return {name: int(probe[name]) for name in TEN_GAUGES}


def _count_blended_red_green_pixels(rgba):
    r = rgba[..., 0].astype(np.int32)
    g = rgba[..., 1].astype(np.int32)
    b = rgba[..., 2].astype(np.int32)
    a = rgba[..., 3].astype(np.int32)
    mask = (r > 16) & (r < 239) & (g > 16) & (g < 239) & (b <= 2) & (a >= 253)
    if np.any(mask):
        # Every resolved MSAA pixel blends red (255,0,0) and green (0,255,0) linearly -> R + G ~= 255.
        sums = r[mask] + g[mask]
        assert np.all(np.abs(sums - 255) <= 3), f'unexpected non-conservative MSAA resolve sums: {sums[:10]}'
    return int(np.count_nonzero(mask))


def test_lif05_samples1_vs_samples4_diagonal_edge_resolve_and_cropped_capture():
    from vispy import _dawn, app, gloo

    size = (64, 64)
    crop = (18, 12, 28, 36)  # bottom-left viewport coords: x=18, y=12, w=28, h=36

    results = {}
    for samples in (0, 4):
        canvas = app.Canvas(app='dawn_headless', size=size, show=False, config={'samples': samples})
        cid = int(canvas._backend._dawn_canvas_id)
        vbo = gloo.VertexBuffer(TILTED_HALF_PLANE)
        prog = gloo.Program(VERT_DIAG_SRC, FRAG_DIAG_SRC)
        prog['a_position'] = vbo
        prog['u_depth'] = -0.5  # NDC z=-0.5 -> window depth 0.25
        prog['u_color'] = (1.0, 0.0, 0.0, 1.0)
        try:
            canvas.set_current()
            cfg = _dawn.framebuffer_config(cid)
            assert cfg['sample_count'] == (1 if samples == 0 else 4)

            gloo.set_viewport(0, 0, *size)
            gloo.set_state(
                blend=False,
                cull_face=False,
                depth_test=True,
                stencil_test=True,
                scissor_test=False,
            )
            gloo.set_depth_mask(True)
            gloo.set_depth_func('always')
            gloo.set_stencil_mask(255)
            gloo.set_stencil_func('always', 41, 255)
            gloo.set_stencil_op('keep', 'keep', 'replace')

            gloo.clear(color=(0.0, 1.0, 0.0, 1.0), depth=0.75, stencil=7)
            prog.draw('triangles')

            full_rgba = gloo.read_pixels((0, 0, *size), alpha=True, out_type='unsigned_byte')
            assert full_rgba.shape == (64, 64, 4)
            # Far-left interior is pure green; far-right interior is pure red.
            np.testing.assert_array_equal(full_rgba[32, 6], [0, 255, 0, 255])
            np.testing.assert_array_equal(full_rgba[32, 58], [255, 0, 0, 255])

            blended_count = _count_blended_red_green_pixels(full_rgba)
            results[samples] = blended_count

            # Cropped RGBA, RGB, and float32 captures across the diagonal edge must match the exact sub-slice.
            x, y, w, h = crop
            expected_slice = full_rgba[size[1] - y - h : size[1] - y, x : x + w]

            crop_rgba = gloo.read_pixels(crop, alpha=True, out_type='unsigned_byte')
            np.testing.assert_array_equal(crop_rgba, expected_slice)

            crop_rgb = gloo.read_pixels(crop, alpha=False, out_type='unsigned_byte')
            np.testing.assert_array_equal(crop_rgb, expected_slice[..., :3])

            crop_float = gloo.read_pixels(crop, alpha=True, out_type='float')
            assert crop_float.dtype == np.float32
            np.testing.assert_allclose(crop_float, expected_slice.astype(np.float32) / 255.0, atol=1.0 / 255.0 + 1e-5)

            # Depth and stencil reads across an MSAA diagonal edge must sample a discrete sample (never averaged!)
            # and must not disturb the resolved color buffer.
            depth_crop = gloo.read_pixels(crop, mode='depth', out_type='float', alpha=False)
            assert depth_crop.shape == (h, w, 1)
            on_025 = np.isclose(depth_crop, 0.25, atol=1e-4)
            on_075 = np.isclose(depth_crop, 0.75, atol=1e-4)
            assert np.all(on_025 | on_075), 'MSAA depth capture must be sample-discrete, never averaged'
            assert np.any(on_025) and np.any(on_075)

            stencil_crop = gloo.read_pixels(crop, mode='stencil', out_type='unsigned_byte', alpha=False)
            assert stencil_crop.shape == (h, w, 1)
            assert set(np.unique(stencil_crop)).issubset({7, 41})
            assert {7, 41}.issubset(set(np.unique(stencil_crop)))

            # Invalid crops must fail cleanly without corrupting subsequent color capture.
            for bad_crop in ((-1, 0, 8, 8), (0, -2, 8, 8), (0, 0, 0, 8), (50, 50, 20, 20)):
                with pytest.raises(RuntimeError):
                    gloo.read_pixels(bad_crop, alpha=True)

            crop_rgba_after = gloo.read_pixels(crop, alpha=True, out_type='unsigned_byte')
            np.testing.assert_array_equal(crop_rgba_after, expected_slice)
        finally:
            prog.delete()
            vbo.delete()
            canvas.context.flush_commands()
            canvas.close()
            gc.collect()
            _dawn.process_events()

    assert results[0] == 0, f'samples=1 must not blend diagonal edge pixels, got {results[0]}'
    assert results[4] >= 32, f'samples=4 must resolve blended diagonal edge pixels, got {results[4]}'

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges


def test_lif05_interleaved_offscreen_fbo_samples1_and_canvas_samples4_mixed_edges():
    from vispy import _dawn, app, gloo

    w, h = 64, 48
    crop = (16, 8, 32, 32)
    canvas = app.Canvas(app='dawn_headless', size=(w, h), show=False, config={'samples': 4})
    cid = int(canvas._backend._dawn_canvas_id)

    vbo = gloo.VertexBuffer(TILTED_HALF_PLANE)
    prog = gloo.Program(VERT_DIAG_SRC, FRAG_DIAG_SRC)
    prog['a_position'] = vbo
    prog['u_depth'] = 0.0

    color_rb = gloo.RenderBuffer((h, w), format='color')
    depth_rb = gloo.RenderBuffer((h, w), format='depth')
    fbo = gloo.FrameBuffer(color=color_rb, depth=depth_rb)

    try:
        canvas.set_current()
        assert _dawn.framebuffer_config(cid)['sample_count'] == 4

        # Step 1: Offscreen FBO is single-sample (sample_count == 1).
        with fbo:
            gloo.set_viewport(0, 0, w, h)
            gloo.set_state(blend=False, depth_test=True, stencil_test=False, scissor_test=False)
            gloo.clear(color=(0.0, 1.0, 0.0, 1.0), depth=1.0)
            prog['u_color'] = (1.0, 0.0, 0.0, 1.0)
            prog.draw('triangles')

            cfg_fbo = _dawn.framebuffer_config(cid)
            assert cfg_fbo['framebuffer_id'] != 0
            assert cfg_fbo['sample_count'] == 1

            fbo_full = fbo.read(mode='color', alpha=True)
            fbo_crop = fbo.read(mode='color', alpha=True, crop=crop)

        assert fbo_full.shape == (h, w, 4)
        assert _count_blended_red_green_pixels(fbo_full) == 0
        x, y, cw, ch = crop
        np.testing.assert_array_equal(fbo_crop, fbo_full[h - y - ch : h - y, x : x + cw])

        # Step 2: Exiting FBO restores samples=4 default canvas target with full MSAA resolve.
        canvas.context.flush_commands()
        assert _dawn.framebuffer_config(cid)['framebuffer_id'] == 0
        assert _dawn.framebuffer_config(cid)['sample_count'] == 4

        gloo.set_viewport(0, 0, w, h)
        gloo.clear(color=(0.0, 1.0, 0.0, 1.0), depth=1.0)
        prog['u_color'] = (1.0, 0.0, 0.0, 1.0)
        prog.draw('triangles')

        canvas_full = gloo.read_pixels((0, 0, w, h), alpha=True)
        canvas_crop = gloo.read_pixels(crop, alpha=True)
        assert _count_blended_red_green_pixels(canvas_full) >= 24
        np.testing.assert_array_equal(canvas_crop, canvas_full[h - y - ch : h - y, x : x + cw])
    finally:
        fbo.delete()
        color_rb.delete()
        depth_rb.delete()
        prog.delete()
        vbo.delete()
        canvas.context.flush_commands()
        canvas.close()
        gc.collect()
        _dawn.process_events()

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges


def test_lif05_qt_onscreen_samples4_vs_samples1_readback_and_crop(monkeypatch):
    PyQt6 = pytest.importorskip('PyQt6')
    from PyQt6 import QtCore, QtGui
    from vispy import _dawn, app, gloo

    assert PyQt6 is not None
    monkeypatch.setenv('VISPY_QT_PRESENTATION', 'readback')
    application = app.use_app('pyqt6')

    w, h = 64, 48
    crop = (16, 8, 32, 32)
    counts = {}

    for samples in (0, 4):
        draws = []
        canvas = app.Canvas(
            app='pyqt6', size=(w, h), show=False, vsync=False, config={'samples': samples}
        )
        vbo = gloo.VertexBuffer(TILTED_HALF_PLANE)
        prog = gloo.Program(VERT_DIAG_SRC, FRAG_DIAG_SRC)
        prog['a_position'] = vbo
        prog['u_depth'] = 0.0
        prog['u_color'] = (1.0, 0.0, 0.0, 1.0)

        @canvas.connect
        def on_draw(event):
            pw, ph = canvas.physical_size
            gloo.set_viewport(0, 0, pw, ph)
            gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False)
            gloo.clear(color=(0.0, 1.0, 0.0, 1.0))
            prog.draw('triangles')
            draws.append((pw, ph))

        try:
            canvas.show()
            deadline = time.monotonic() + 5.0
            while not draws:
                application.process_events()
                _dawn.process_events()
                assert time.monotonic() < deadline, 'Qt MSAA paint timed out'
                time.sleep(0.002)
            while any(_dawn.probe()[k] for k in ('pending_tickets', 'queued_frames')):
                application.process_events()
                _dawn.process_events()
                time.sleep(0.002)

            cid = int(canvas.native._dawn_canvas_id)
            assert _dawn.framebuffer_config(cid)['sample_count'] == (1 if samples == 0 else 4)

            canvas.set_current()
            pw, ph = canvas.physical_size
            full_px = gloo.read_pixels((0, 0, pw, ph), alpha=True)
            crop_px = gloo.read_pixels(crop, alpha=True)
            x, y, cw, ch = crop
            np.testing.assert_array_equal(crop_px, full_px[ph - y - ch : ph - y, x : x + cw])
            counts[samples] = _count_blended_red_green_pixels(full_px)

            # QWidget raster presentation buffer must also preserve the resolved MSAA vs binary edge distinction.
            qimg = canvas.native.grab().toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            ptr = qimg.bits()
            ptr.setsize(qimg.sizeInBytes())
            qarr = np.frombuffer(ptr, dtype=np.uint8).reshape((qimg.height(), qimg.bytesPerLine()))
            qrgba = qarr[:, : qimg.width() * 4].reshape((qimg.height(), qimg.width(), 4)).copy()
            if samples == 0 and (qimg.width(), qimg.height()) == (pw, ph):
                assert _count_blended_red_green_pixels(qrgba) == 0
            elif samples == 4:
                assert _count_blended_red_green_pixels(qrgba) >= 20
        finally:
            prog.delete()
            vbo.delete()
            if not canvas._closed:
                canvas.context.flush_commands()
                canvas.close()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            application.process_events()
            gc.collect()
            _dawn.process_events()

    assert counts[0] == 0
    assert counts[4] >= 24

    gauges = _ten_gauges(_dawn)
    for k in ('pending_tickets', 'queued_frames', 'canvas_texture_bytes', 'transient_buffer_bytes'):
        assert gauges[k] == 0, gauges
