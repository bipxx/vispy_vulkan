"""Line partitioning, workgroup-64 seams, topology/pool reuse, and SHD-04/05 boundaries (LIN-01).

Verifies generated wide-line continuity across compute workgroup-64 seams
(counts 64, 65, 129, 257), diagnostic endpoint capture with 0xD9 canary guard
verification, line_strip / lines / line_loop topology switches and uint16 0xFFFF
primitive-restart safety, dynamic vertex shrinkage/growth and NativeLinePool
idle-slot reuse, queued multi-draw revision ordering, multi-chunk resident-pool
budget refusal + same-canvas recovery, and explicit instanced-quad geometry
replacement across forced device loss (SHD-04 / SHD-05).
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@pytest.fixture(autouse=True, scope="module")
def _reset_line_pool_on_exit():
    yield
    from vispy import _dawn

    _dawn.shutdown()
    probe = _dawn.probe()
    for gauge in (
        "pending_tickets",
        "queued_frames",
        "pending_draws",
        "live_buffer_bytes",
        "live_cpu_buffer_bytes",
        "live_texture_bytes",
        "canvas_texture_bytes",
        "transient_buffer_bytes",
        "line_resource_pool_busy_slots",
        "line_resource_pool_bytes",
    ):
        assert probe[gauge] == 0, (gauge, probe[gauge])


@contextmanager
def _headless_canvas(size=(64, 16)):
    from vispy import _dawn, app, gloo

    canvas = app.Canvas(app="dawn_headless", size=size, show=False)
    canvas.set_current()
    objects = []
    try:
        gloo.set_viewport(0, 0, size[0], size[1])
        yield canvas, gloo, _dawn, objects
    finally:
        for obj in reversed(objects):
            try:
                obj.delete()
            except Exception:
                pass
        try:
            gloo.flush()
        except Exception:
            pass
        canvas.close()
        _dawn.process_events()


def test_workgroup64_seam_continuity_and_diagnostic_endpoint_capture():
    with _headless_canvas(size=(64, 16)) as (canvas, gloo, _dawn, objects):
        canvas_id = int(canvas._backend._dawn_canvas_id)
        _dawn.diagnostic_configure_line_endpoints(canvas_id, True, True)

        # 129 vertices span 3 workgroups of 64 (indices 0..63, 64..127, 128), testing seams 63->64 and 127->128!
        xs = np.linspace(-0.95, 0.95, 129, dtype=np.float32)
        pts = np.stack([xs, np.zeros_like(xs)], axis=1)
        vbo = gloo.VertexBuffer(pts)
        inst_y = gloo.VertexBuffer(np.array([-0.5, 0.5], dtype=np.float32), divisor=1)
        prog = gloo.Program(
            """
            attribute vec2 a_pos;
            attribute float a_yoff;
            varying vec4 v_color;
            void main() {
                v_color = (a_yoff < 0.0) ? vec4(1.0, 0.25, 0.0, 1.0) : vec4(0.0, 0.75, 1.0, 1.0);
                gl_Position = vec4(a_pos.x, a_pos.y + a_yoff, 0.0, 1.0);
            }
            """,
            "varying vec4 v_color; void main() { gl_FragColor = v_color; }",
        )
        objects.extend([vbo, inst_y, prog])
        prog["a_pos"] = vbo
        prog["a_yoff"] = inst_y

        gloo.set_state(blend=False, depth_test=False)
        gloo.set_line_width(4.0)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("line_strip")
        img = gloo.read_pixels((0, 0, 64, 16), alpha=True)

        # Upper instance (a_yoff=+0.5 -> row ~4) and lower instance (a_yoff=-0.5 -> row ~12) are continuous across all columns 4..59!
        assert np.all(img[4, 4:60, 2] > 200), "Gap detected in upper instanced 129-vertex wide line_strip"
        assert np.all(img[12, 4:60, 0] > 200), "Gap detected in lower instanced 129-vertex wide line_strip"

        records = _dawn.diagnostic_line_endpoints(canvas_id)
        assert len(records) >= 1
        rec = records[-1]
        assert rec["status"] == "completed" and rec["error"] == ""
        assert rec["rows"] == 129 * 2
        # Padded workgroup allocation ((258 + 63)//64)*64 = 320 rows plus 16-byte trailing 0xCD canary!
        padded_bytes = 320 * rec["row_bytes"]
        assert rec["raw_data"].size == padded_bytes + 16
        assert np.all(rec["raw_data"][rec["rows"] * rec["row_bytes"] :] == 0xCD)


def test_topology_switches_uint16_sentinel_dynamic_resizing_and_pool_reuse():
    with _headless_canvas(size=(48, 24)) as (_canvas, gloo, _dawn, objects):
        vbo = gloo.VertexBuffer(
            np.array(
                [[-0.8, -0.5], [-0.2, -0.5], [0.2, -0.5], [0.8, -0.5]], dtype=np.float32
            )
        )
        prog = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.extend([vbo, prog])
        prog["a_pos"] = vbo
        prog["u_color"] = (0.0, 1.0, 0.0, 1.0)

        gloo.set_state(blend=False, depth_test=False)
        gloo.set_line_width(4.0)

        # 1. line_strip connects vertex 1 (-0.2) to vertex 2 (+0.2) across center x=24 (row 18).
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("line_strip")
        strip_img = gloo.read_pixels((0, 0, 48, 24), alpha=True)
        assert strip_img[18, 24, 1] > 200

        # 2. Same Program & VBO with 'lines' leaves the gap between (-0.2) and (+0.2) unlit while lighting outer segments!
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("lines")
        lines_img = gloo.read_pixels((0, 0, 48, 24), alpha=True)
        assert lines_img[18, 24, 1] == 0
        assert lines_img[18, 12, 1] > 200 and lines_img[18, 36, 1] > 200

        # 3. Triangle vertices with 'line_loop' closes the final edge back to vertex 0!
        vbo.set_data(np.array([[-0.7, -0.6], [0.7, -0.6], [0.7, 0.6]], dtype=np.float32))
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("line_loop")
        loop_img = gloo.read_pixels((0, 0, 48, 24), alpha=True)
        # Closing diagonal from (0.7, 0.6) to (-0.7, -0.6) passes through center (row 12, col 24)!
        assert loop_img[12, 24, 1] > 200

        # 4. Dynamic vertex growth/shrinkage (257 -> 5 -> 513 -> 65) + NativeLinePool idle-slot reuse!
        hits_before = _dawn.probe()["line_resource_pool_hits"]
        for count in (257, 5, 513, 65):
            xs = np.linspace(-0.9, 0.9, count, dtype=np.float32)
            vbo.set_data(np.stack([xs, np.zeros_like(xs)], axis=1))
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            prog.draw("line_strip")
            out = gloo.read_pixels((0, 0, 48, 24), alpha=True)
            assert out[12, 24, 1] > 200
        # Redrawing the active 65-vertex line_strip reuses the exact affinity idle slot in NativeLinePool!
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("line_strip")
        out_reused = gloo.read_pixels((0, 0, 48, 24), alpha=True)
        assert out_reused[12, 24, 1] > 200
        probe_after = _dawn.probe()
        assert probe_after["line_resource_pool_hits"] > hits_before
        assert probe_after["line_resource_pool_busy_slots"] == 0

        # 5. Thin 1px line_strip with uint16 index 65535 (0xFFFF) does NOT trigger spurious strip restart!
        gloo.set_line_width(1.0)
        big_table = np.zeros((65536, 2), dtype=np.float32)
        big_table[0] = [-0.8, 0.0]
        big_table[65535] = [0.0, 0.0]
        big_table[1] = [0.8, 0.0]
        big_vbo = gloo.VertexBuffer(big_table)
        sentinel_ibo = gloo.IndexBuffer(np.array([0, 65535, 1], dtype=np.uint16))
        objects.extend([big_vbo, sentinel_ibo])
        prog["a_pos"] = big_vbo
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw("line_strip", sentinel_ibo)
        thin_img = gloo.read_pixels((0, 0, 48, 24), alpha=True)
        # Both left half (-0.8..0.0 -> col 12) and right half (0.0..0.8 -> col 36) are connected through vertex 65535!
        assert np.any(thin_img[11:14, 12, 1] > 200)
        assert np.any(thin_img[11:14, 36, 1] > 200)


def test_queued_revision_order_pool_budget_refusal_and_shd04_instanced_quad_recovery():
    with _headless_canvas(size=(32, 32)) as (_canvas, gloo, _dawn, objects):
        vbo = gloo.VertexBuffer(np.array([[-0.9, 0.0], [0.9, 0.0]], dtype=np.float32))
        prog = gloo.Program(
            "attribute vec2 a_pos; void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }",
            "uniform vec4 u_color; void main() { gl_FragColor = u_color; }",
        )
        objects.extend([vbo, prog])
        prog["a_pos"] = vbo

        # 1. Three back-to-back wide-line mutations before a single readback preserve exact painter's order!
        gloo.set_state(blend=False, depth_test=False)
        gloo.set_line_width(4.0)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))

        prog["u_color"] = (1.0, 0.0, 0.0, 1.0)
        prog.draw("lines")
        vbo.set_data(np.array([[-0.45, 0.0], [0.45, 0.0]], dtype=np.float32))
        prog["u_color"] = (0.0, 1.0, 0.0, 1.0)
        prog.draw("lines")
        vbo.set_data(np.array([[0.0, -0.5], [0.0, 0.5]], dtype=np.float32))
        prog["u_color"] = (0.0, 0.0, 1.0, 1.0)
        prog.draw("lines")

        layered = gloo.read_pixels((0, 0, 32, 32), alpha=True)
        np.testing.assert_allclose(layered[16, 4], [255, 0, 0, 255], atol=2)    # outer arm: red
        np.testing.assert_allclose(layered[16, 11], [0, 255, 0, 255], atol=2)   # middle arm: green
        np.testing.assert_allclose(layered[16, 16], [0, 0, 255, 255], atol=2)   # center cross: blue

        # 2. Multi-chunk prepare_line_chunks >64 MiB resident-pool ceiling refuses deterministically & recovers!
        oversized_prog = gloo.Program(
            "attribute float a_x; void main() { gl_Position = vec4(a_x, 0.0, 0.0, 1.0); }",
            "void main() { gl_FragColor = vec4(1.0, 1.0, 0.0, 1.0); }",
        )
        oversized_vbo = gloo.VertexBuffer(np.zeros(4_194_242, dtype=np.float32))
        objects.extend([oversized_prog, oversized_vbo])
        oversized_prog["a_x"] = oversized_vbo

        with pytest.raises((RuntimeError, ValueError), match="exceeds resident pool budget"):
            oversized_prog.draw("line_strip")

        # Same canvas & program recover immediately when shrunk within budget!
        oversized_vbo.set_data(np.linspace(-0.8, 0.8, 129, dtype=np.float32))
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        oversized_prog.draw("line_strip")
        np.testing.assert_allclose(
            gloo.read_pixels((0, 0, 32, 32), alpha=True)[16, 16], [255, 255, 0, 255], atol=2
        )

        # 3. SHD-04 / SHD-05: Explicit instanced 6-vertex quad geometry expansion + device-loss recovery!
        gloo.set_line_width(1.0)
        quad_corners = gloo.VertexBuffer(
            np.array(
                [
                    [0.0, -1.0],
                    [1.0, -1.0],
                    [1.0, 1.0],
                    [0.0, -1.0],
                    [1.0, 1.0],
                    [0.0, 1.0],
                ],
                dtype=np.float32,
            )
        )
        seg_p0 = gloo.VertexBuffer(
            np.array([[-0.75, -0.25], [-0.75, 0.25]], dtype=np.float32), divisor=1
        )
        seg_p1 = gloo.VertexBuffer(
            np.array([[0.75, -0.25], [0.75, 0.25]], dtype=np.float32), divisor=1
        )
        seg_color = gloo.VertexBuffer(
            np.array([[1.0, 0.5, 0.0, 1.0], [0.0, 1.0, 0.5, 1.0]], dtype=np.float32),
            divisor=1,
        )
        inst_quad_prog = gloo.Program(
            """
            attribute vec2 a_corner;
            attribute vec2 a_p0;
            attribute vec2 a_p1;
            attribute vec4 a_color;
            uniform vec2 u_viewport;
            uniform float u_half_width_px;
            varying vec4 v_color;
            void main() {
                vec2 dir = normalize(a_p1 - a_p0);
                vec2 normal_ndc = vec2(-dir.y, dir.x) * (2.0 * u_half_width_px / u_viewport);
                vec2 base = mix(a_p0, a_p1, a_corner.x);
                v_color = a_color;
                gl_Position = vec4(base + normal_ndc * a_corner.y, 0.0, 1.0);
            }
            """,
            "varying vec4 v_color; void main() { gl_FragColor = v_color; }",
        )
        objects.extend([quad_corners, seg_p0, seg_p1, seg_color, inst_quad_prog])
        inst_quad_prog["a_corner"] = quad_corners
        inst_quad_prog["a_p0"] = seg_p0
        inst_quad_prog["a_p1"] = seg_p1
        inst_quad_prog["a_color"] = seg_color
        inst_quad_prog["u_viewport"] = (32.0, 32.0)
        inst_quad_prog["u_half_width_px"] = 2.0

        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        inst_quad_prog.draw("triangles")
        before_loss = gloo.read_pixels((0, 0, 32, 32), alpha=True)
        np.testing.assert_allclose(before_loss[12, 16], [0, 255, 128, 255], atol=3)
        np.testing.assert_allclose(before_loss[20, 16], [255, 128, 0, 255], atol=3)

        # Force device loss and prove the instanced geometry consumer rebuilds & renders identically!
        _dawn.lose_device()
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        inst_quad_prog.draw("triangles")
        after_loss = gloo.read_pixels((0, 0, 32, 32), alpha=True)
        np.testing.assert_allclose(after_loss[12, 16], [0, 255, 128, 255], atol=3)
        np.testing.assert_allclose(after_loss[20, 16], [255, 128, 0, 255], atol=3)
