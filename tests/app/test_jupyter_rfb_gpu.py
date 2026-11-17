# SPDX-License-Identifier: AGPL-3.0-only
"""GPU acceptance tests for the jupyter_rfb backend on Dawn Vulkan."""
from __future__ import annotations

import asyncio
import gc
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def test_jupyter_rfb_canvas_gloo_hidpi_events_and_idempotent_cleanup():
    """Verify Canvas(app='jupyter_rfb') gloo rendering, HiDPI resize, input events, and 0-byte Dawn teardown."""
    pytest.importorskip("jupyter_rfb")
    from vispy import _dawn, gloo
    from vispy.app import Canvas
    from vispy.app.backends import _jupyter_rfb

    gc.collect()
    _dawn.process_events()
    probe_before = _dawn.probe()

    canvas = Canvas(app="jupyter_rfb", size=(80, 60))
    prog = None
    try:
        assert canvas.app.backend_name == "jupyter_rfb"
        assert isinstance(canvas.native, _jupyter_rfb.CanvasBackend)
        assert canvas.native.css_width == "80px"
        assert canvas.native.css_height == "60px"
        assert canvas.native._dawn_canvas_id > 0
        # Before initial browser resize event, physical_size is (1, 1) -> get_frame() returns None.
        assert canvas.native.get_frame() is None

        prog = gloo.Program(
            """
            attribute vec2 a_position;
            void main() {
                gl_Position = vec4(a_position, 0.0, 1.0);
            }
            """,
            """
            void main() {
                gl_FragColor = vec4(1.0, 0.25, 0.0, 1.0);
            }
            """,
        )
        prog["a_position"] = np.array(
            [[-0.75, -0.75], [0.75, -0.75], [0.0, 0.75]], dtype=np.float32
        )

        @canvas.connect
        def on_resize(event):
            gloo.set_viewport(0, 0, *event.physical_size)

        @canvas.connect
        def on_draw(event):
            gloo.set_viewport(0, 0, *canvas.physical_size)
            gloo.clear(color=(0.05, 0.10, 0.45, 1.0), depth=True)
            prog.draw("triangles")

        # 1. Standard DPI (pixel_ratio=1.0)
        canvas.native.handle_event({"type": "resize", "width": 80, "height": 60, "ratio": 1.0})
        assert canvas.size == (80, 60)
        assert canvas.physical_size == (80, 60)
        assert canvas.pixel_scale == 1.0

        frame_1x = np.array(canvas.native.get_frame(), copy=True)
        assert frame_1x.shape == (60, 80, 4) and frame_1x.dtype == np.uint8
        # Triangle center is bright orange; top-left corner is dark blue clear color.
        assert frame_1x[35, 40, 0] > 220 and frame_1x[35, 40, 2] < 30 and frame_1x[35, 40, 3] == 255
        assert frame_1x[4, 4, 2] > 90 and frame_1x[4, 4, 0] < 30 and frame_1x[4, 4, 3] == 255
        lit_1x = int((frame_1x[..., 0] > 200).sum())
        assert lit_1x >= 400

        # 2. HiDPI (pixel_ratio=2.0)
        canvas.native.handle_event({"type": "resize", "width": 80, "height": 60, "ratio": 2.0})
        assert canvas.size == (80, 60)
        assert canvas.physical_size == (160, 120)
        assert canvas.pixel_scale == 2.0

        frame_2x = np.array(canvas.native.get_frame(), copy=True)
        assert frame_2x.shape == (120, 160, 4) and frame_2x.dtype == np.uint8
        assert frame_2x[70, 80, 0] > 220 and frame_2x[70, 80, 2] < 30 and frame_2x[70, 80, 3] == 255
        assert frame_2x[6, 6, 2] > 90 and frame_2x[6, 6, 0] < 30 and frame_2x[6, 6, 3] == 255
        lit_2x = int((frame_2x[..., 0] > 200).sum())
        assert lit_2x >= 3 * lit_1x

        # 3. Pointer, wheel, and keyboard events
        seen: list[tuple] = []
        canvas.events.mouse_press.connect(
            lambda e: seen.append(("press", tuple(e.pos), e.button, tuple(m.name for m in e.modifiers)))
        )
        canvas.events.mouse_move.connect(
            lambda e: seen.append(("move", tuple(e.pos), e.button, tuple(e.buttons)))
        )
        canvas.events.mouse_release.connect(
            lambda e: seen.append(("release", tuple(e.pos), e.button, tuple(e.buttons)))
        )
        canvas.events.mouse_double_click.connect(
            lambda e: seen.append(("dblclick", tuple(e.pos), e.button))
        )
        canvas.events.mouse_wheel.connect(
            lambda e: seen.append(("wheel", tuple(e.pos), tuple(round(v, 3) for v in e.delta)))
        )
        canvas.events.key_press.connect(
            lambda e: seen.append(("keydown", e.key.name, e.text, tuple(m.name for m in e.modifiers)))
        )
        canvas.events.key_release.connect(
            lambda e: seen.append(("keyup", e.key.name, e.text))
        )

        canvas.native.handle_event(
            {"type": "pointer_down", "x": 20, "y": 15, "button": 1, "modifiers": ["Shift"]}
        )
        time.sleep(0.015)
        canvas.native.handle_event(
            {"type": "pointer_move", "x": 35, "y": 25, "button": 1, "modifiers": ["Shift"]}
        )
        canvas.native.handle_event(
            {"type": "pointer_up", "x": 35, "y": 25, "button": 1, "modifiers": []}
        )
        canvas.native.handle_event(
            {"type": "double_click", "x": 20, "y": 15, "button": 1, "modifiers": []}
        )
        canvas.native.handle_event(
            {"type": "wheel", "x": 40, "y": 30, "dx": 0.0, "dy": -120.0, "modifiers": []}
        )
        canvas.native.handle_event(
            {"type": "key_down", "key": "a", "modifiers": ["Control"]}
        )
        canvas.native.handle_event(
            {"type": "key_up", "key": "a", "modifiers": []}
        )

        event_kinds = [row[0] for row in seen]
        assert event_kinds == ["press", "move", "release", "dblclick", "wheel", "keydown", "keyup"]
        assert seen[0] == ("press", (20, 15), 1, ("Shift",))
        assert seen[1] == ("move", (35, 25), 1, (1,))
        assert seen[2] == ("release", (35, 25), 1, ())
        assert seen[3] == ("dblclick", (20, 15), 1)
        assert seen[4] == ("wheel", (40, 30), (0.0, 1.2))
        assert seen[5] == ("keydown", "a", "a", ("Control",))
        assert seen[6] == ("keyup", "a", "a")
    finally:
        if prog is not None:
            prog.delete()
            prog = None
        canvas.close()

    # 4. Idempotent Dawn teardown across canvas.close(), _cleanup_dawn_resources(), and close event
    assert canvas.native._lifecycle == 2
    assert canvas.native._helper._fbo is None
    assert canvas.native._dawn_canvas_id == 0
    assert canvas.native.get_frame() is None
    canvas.native._cleanup_dawn_resources()
    canvas.native.handle_event({"type": "close"})
    canvas.close()

    gc.collect()
    _dawn.process_events()
    probe_after = _dawn.probe()
    assert probe_after["canvas_texture_bytes"] == probe_before["canvas_texture_bytes"]
    assert probe_after["live_texture_bytes"] == probe_before["live_texture_bytes"]


def test_jupyter_rfb_scenecanvas_visuals_camera_interaction_and_close_event():
    """Verify SceneCanvas(app='jupyter_rfb') with PanZoomCamera, Line, Markers, Text (_sdf_cpu), wheel/drag, and close event."""
    pytest.importorskip("jupyter_rfb")
    from vispy import _dawn, scene
    from vispy.visuals.text import _sdf_cpu

    assert callable(_sdf_cpu._calc_distance_field)

    gc.collect()
    _dawn.process_events()
    probe_before = _dawn.probe()

    sc = scene.SceneCanvas(app="jupyter_rfb", size=(160, 120), bgcolor="black")
    try:
        sc.native.handle_event({"type": "resize", "width": 160, "height": 120, "ratio": 1.0})
        view = sc.central_widget.add_view()
        view.camera = scene.cameras.PanZoomCamera(rect=(-1.0, -1.0, 2.0, 2.0))

        line_vis = scene.visuals.Line(
            pos=np.array([[-0.8, -0.6], [0.0, 0.7], [0.8, -0.6]], dtype=np.float32),
            color=(0.0, 1.0, 0.25, 1.0),
            width=3.0,
            parent=view.scene,
        )
        markers_vis = scene.visuals.Markers(
            pos=np.array([[-0.4, 0.0], [0.4, 0.0]], dtype=np.float32),
            face_color=(1.0, 0.2, 0.4, 1.0),
            edge_color="white",
            size=14.0,
            parent=view.scene,
        )
        text_vis = scene.visuals.Text(
            "RFB",
            pos=(0.0, -0.35),
            color="white",
            font_size=16,
            method="cpu",
            parent=view.scene,
        )
        assert line_vis is not None and markers_vis is not None and text_vis is not None

        frame_before = np.array(sc.native.get_frame(), copy=True)
        assert frame_before.shape == (120, 160, 4) and frame_before.dtype == np.uint8
        assert int(np.any(frame_before[..., :3] > 20, axis=-1).sum()) >= 200
        # Verify distinct green Line pixels and warm Markers pixels rendered.
        green_px = (frame_before[..., 1] > 180) & (frame_before[..., 0] < 80)
        warm_px = (frame_before[..., 0] > 180) & (frame_before[..., 1] < 100)
        assert int(green_px.sum()) >= 20
        assert int(warm_px.sum()) >= 15

        rect_initial = (
            float(view.camera.rect.left),
            float(view.camera.rect.bottom),
            float(view.camera.rect.width),
            float(view.camera.rect.height),
        )

        # Mouse wheel zoom in on PanZoomCamera
        sc.native.handle_event(
            {"type": "wheel", "x": 80, "y": 60, "dx": 0.0, "dy": -120.0, "modifiers": []}
        )
        assert float(view.camera.rect.width) < rect_initial[2]
        assert float(view.camera.rect.height) < rect_initial[3]
        pos_after_zoom = (float(view.camera.rect.left), float(view.camera.rect.bottom))

        # Mouse drag pan on PanZoomCamera
        sc.native.handle_event(
            {"type": "pointer_down", "x": 80, "y": 60, "button": 1, "modifiers": []}
        )
        time.sleep(0.015)
        sc.native.handle_event(
            {"type": "pointer_move", "x": 112, "y": 78, "button": 1, "modifiers": []}
        )
        sc.native.handle_event(
            {"type": "pointer_up", "x": 112, "y": 78, "button": 1, "modifiers": []}
        )
        pos_after_drag = (float(view.camera.rect.left), float(view.camera.rect.bottom))
        assert pos_after_drag != pos_after_zoom

        frame_after = np.array(sc.native.get_frame(), copy=True)
        assert frame_after.shape == (120, 160, 4)
        assert int(np.any(frame_after[..., :3] > 20, axis=-1).sum()) >= 100
        assert not np.array_equal(frame_after, frame_before)

        # Teardown initiated via browser handle_event({'type': 'close'}), followed by idempotent sc.close()
        sc.native.handle_event({"type": "close"})
        assert sc.native._lifecycle == 2
        assert sc.native._helper._fbo is None
        assert sc.native._dawn_canvas_id == 0
        assert sc.native.get_frame() is None
    finally:
        sc.close()

    del sc, view, line_vis, markers_vis, text_vis
    gc.collect()
    _dawn.process_events()
    probe_after = _dawn.probe()
    assert probe_after["canvas_texture_bytes"] == probe_before["canvas_texture_bytes"]


def test_jupyter_rfb_asyncio_timer_iterations_and_repeatable_stop():
    """Verify Timer(app='jupyter_rfb') fires inside asyncio loop and supports repeatable stop()."""
    pytest.importorskip("jupyter_rfb")
    from vispy.app import Timer

    async def _run_timer_checks():
        idle_timer = Timer(interval=0.02, app="jupyter_rfb", start=False)
        # Stopping an unstarted timer must not fail when _task is None.
        idle_timer.stop()
        idle_timer.stop()
        assert not idle_timer.running

        ticks: list[int] = []
        timer = Timer(
            interval=0.01,
            app="jupyter_rfb",
            iterations=2,
            start=True,
            connect=lambda ev: ticks.append(int(ev.count)),
        )
        assert timer.running

        deadline = time.monotonic() + 2.0
        while timer.running and time.monotonic() < deadline:
            await asyncio.sleep(0.01)

        assert ticks == [0, 1]
        assert timer.iter_count == 2
        assert not timer.running
        assert timer._backend._task is None

        # Repeatable stop() calls must be safe no-ops.
        timer.stop()
        timer.stop()
        assert not timer.running

    asyncio.run(_run_timer_checks())
