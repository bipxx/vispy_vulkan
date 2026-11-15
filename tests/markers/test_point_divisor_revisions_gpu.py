# SPDX-License-Identifier: AGPL-3.0-only
"""GPU acceptance for SCI-01 and SCI-05 (U05): indexed/instanced point IDs, divisors, constants, and queued revisions."""
from __future__ import annotations

from contextlib import contextmanager
import gc

import numpy as np
import pytest

pytestmark = pytest.mark.gpu

INDEXED_VERTEX_330 = """#version 330
in vec2 a_base;
in vec3 a_tint;
in float a_size;
uniform vec2 u_viewport;
flat out vec3 v_color;
void main() {
    vec2 p = a_base;
    p.y += (gl_VertexID % 2 == 1) ? 4.0 : 0.0;
    int cid = gl_VertexID % 4;
    vec3 pal = (cid == 0) ? vec3(1.0, 0.0, 0.0) :
               (cid == 1) ? vec3(0.0, 1.0, 0.0) :
               (cid == 2) ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 1.0, 0.0);
    v_color = pal * a_tint;
    gl_Position = vec4(p / u_viewport * 2.0 - 1.0, 0.0, 1.0);
    gl_PointSize = a_size;
}
"""

INDEXED_FRAGMENT_330 = """#version 330
flat in vec3 v_color;
uniform float u_alpha;
out vec4 frag_color;
void main() {
    frag_color = vec4(v_color, u_alpha);
}
"""


@contextmanager
def _headless_canvas(size=(32, 24)):
    from vispy import _dawn, app, gloo

    canvas = app.Canvas(app='dawn_headless', size=size, show=False)
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
        gc.collect()
        _dawn.process_events()


def _expected_point_frame(width, height, ops):
    image = np.zeros((height, width, 4), dtype=np.uint8)
    image[..., 3] = 255
    for x, y, size, rgb, alpha in ops:
        r = size // 2
        region = image[height - 1 - y - r : height - y + r, x - r : x + r + 1, :3]
        assert region.shape == (size, size, 3)
        region[:] = np.floor(
            region.astype(np.float64) * (1.0 - alpha) + np.asarray(rgb, np.float64) * alpha + 0.5
        ).astype(np.uint8)
    return image


def test_indexed_point_source_ids_uint8_uint16_uint32_and_large_constant_id():
    rec_dtype = np.dtype(
        [('pad0', '<f4'), ('a_base', '<f4', (2,)), ('pad1', '<f4'), ('a_tint', '<f4', (3,))]
    )
    data = np.zeros(8, dtype=rec_dtype)
    data['pad0'] = 91.0
    data['pad1'] = -73.0
    data['a_base'] = [
        [2.5, 4.5],
        [8.5, 4.5],
        [12.5, 4.5],
        [4.5, 4.5],
        [16.5, 4.5],
        [28.5, 4.5],
        [24.5, 4.5],
        [30.5, 4.5],
    ]
    data['a_tint'] = 1.0
    palette = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
    indices_list = [6, 1, 4, 1]
    expected_ops = [
        (int(data['a_base'][idx][0]), int(data['a_base'][idx][1]) + 4 * (idx % 2), 3, palette[idx % 4], 0.25)
        for idx in indices_list
    ]
    expected = _expected_point_frame(32, 24, expected_ops)

    with _headless_canvas(size=(32, 24)) as (_canvas, gloo, _dawn, objects):
        vbo = gloo.VertexBuffer(data)
        prog = gloo.Program(INDEXED_VERTEX_330, INDEXED_FRAGMENT_330)
        objects.extend([vbo, prog])
        prog['a_base'] = vbo['a_base']
        prog['a_tint'] = vbo['a_tint']
        prog['a_size'] = 3.0
        prog['u_viewport'] = (32.0, 24.0)
        prog['u_alpha'] = 0.25

        frames = {}
        for idx_dtype in (np.uint8, np.uint16, np.uint32):
            ibo = gloo.IndexBuffer(np.array(indices_list, dtype=idx_dtype))
            objects.append(ibo)
            gloo.set_state(
                blend=True,
                blend_func=('src_alpha', 'one_minus_src_alpha', 'zero', 'one'),
                depth_test=False,
                cull_face=False,
            )
            gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
            prog.draw('points', ibo)
            img = gloo.read_pixels((0, 0, 32, 24), alpha=True)
            np.testing.assert_array_equal(img, expected)
            frames[idx_dtype.__name__] = img
        np.testing.assert_array_equal(frames['uint8'], frames['uint16'])
        np.testing.assert_array_equal(frames['uint16'], frames['uint32'])

        # Large uint32 vertex ID (2**24 + 1 == 16777217, cid == 1 -> green) with constant geometry & inactive count input.
        large_id = 2**24 + 1
        prog_large = gloo.Program(
            INDEXED_VERTEX_330.replace('in vec2 a_base;', 'in vec2 a_base;\nin float a_unused_count;'),
            INDEXED_FRAGMENT_330,
        )
        dummy_count = gloo.VertexBuffer(np.zeros(1, dtype=np.float32))
        ibo_large = gloo.IndexBuffer(np.array([large_id], dtype=np.uint32))
        objects.extend([prog_large, dummy_count, ibo_large])
        prog_large['a_unused_count'] = dummy_count
        prog_large['a_base'] = (16.5, 8.5)
        prog_large['a_tint'] = (1.0, 1.0, 1.0)
        prog_large['a_size'] = 3.0
        prog_large['u_viewport'] = (32.0, 24.0)
        prog_large['u_alpha'] = 0.25
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog_large.draw('points', ibo_large)
        large_img = gloo.read_pixels((0, 0, 32, 24), alpha=True)
        expected_large = _expected_point_frame(32, 24, [(16, 12, 3, palette[large_id % 4], 0.25)])
        np.testing.assert_array_equal(large_img, expected_large)


def test_instanced_point_divisors_1_2_3_and_scalar_constants():
    vert = """#version 330
    in vec2 a_base;
    in float a_xstep;
    in float a_green_div2;
    in float a_blue_div3;
    in vec2 a_const_bias;
    in float a_size;
    uniform vec2 u_viewport;
    flat out vec3 v_color;
    void main() {
        vec2 p = a_base + a_const_bias + vec2(a_xstep, 0.0);
        float red = (gl_VertexID == 0) ? 0.25 : 1.0;
        v_color = vec3(red, a_green_div2, a_blue_div3);
        gl_Position = vec4(p / u_viewport * 2.0 - 1.0, 0.0, 1.0);
        gl_PointSize = a_size;
    }
    """
    frag = """#version 330
    flat in vec3 v_color;
    out vec4 frag_color;
    void main() { frag_color = vec4(v_color, 1.0); }
    """
    with _headless_canvas(size=(48, 16)) as (_canvas, gloo, _dawn, objects):
        # 2 vertices per instance (bottom y=4.0 and top y=12.0), 6 instances horizontally (x = 4, 12, 20, 28, 36, 44).
        v_base = gloo.VertexBuffer(np.array([[0.0, 4.0], [0.0, 12.0]], dtype=np.float32))
        i_xstep = gloo.VertexBuffer(
            np.array([i * 8.0 for i in range(6)], dtype=np.float32), divisor=1
        )
        i_g_div2 = gloo.VertexBuffer(np.array([0.25, 0.50, 1.00], dtype=np.float32), divisor=2)
        i_b_div3 = gloo.VertexBuffer(np.array([0.25, 0.75], dtype=np.float32), divisor=3)
        prog = gloo.Program(vert, frag)
        objects.extend([v_base, i_xstep, i_g_div2, i_b_div3, prog])

        prog['a_base'] = v_base
        prog['a_xstep'] = i_xstep
        prog['a_green_div2'] = i_g_div2
        prog['a_blue_div3'] = i_b_div3
        prog['a_const_bias'] = (4.0, 0.0)
        prog['a_size'] = 4.0
        prog['u_viewport'] = (48.0, 16.0)

        gloo.set_state(blend=False, depth_test=False, cull_face=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw('points')
        img = gloo.read_pixels((0, 0, 48, 16), alpha=True)

        greens = [64, 64, 128, 128, 255, 255]
        blues = [64, 64, 64, 191, 191, 191]
        for inst in range(6):
            cx = 4 + inst * 8
            # Vertex 0 is at GL y=4 -> image row 16 - 4 = 12 (4x4 quad spans rows 10..13, cols cx-2..cx+1)
            np.testing.assert_allclose(img[11, cx], [64, greens[inst], blues[inst], 255], atol=2)
            # Vertex 1 is at GL y=12 -> image row 16 - 12 = 4 (4x4 quad spans rows 2..5)
            np.testing.assert_allclose(img[3, cx], [255, greens[inst], blues[inst], 255], atol=2)
        # Gap between columns stays black.
        np.testing.assert_array_equal(img[8, 8], [0, 0, 0, 255])


def test_queued_point_buffer_and_index_revisions_before_single_readback():
    with _headless_canvas(size=(32, 24)) as (_canvas, gloo, _dawn, objects):
        rec_dtype = np.dtype([('a_base', '<f4', (2,)), ('a_tint', '<f4', (3,))])
        data = np.zeros(4, dtype=rec_dtype)
        data['a_base'] = [[6.5, 4.5], [14.5, 4.5], [22.5, 4.5], [28.5, 4.5]]
        data['a_tint'] = 1.0
        vbo = gloo.VertexBuffer(data)
        ibo = gloo.IndexBuffer(np.array([0, 2], dtype=np.uint16))
        prog = gloo.Program(INDEXED_VERTEX_330, INDEXED_FRAGMENT_330)
        objects.extend([vbo, ibo, prog])

        prog['a_base'] = vbo['a_base']
        prog['a_tint'] = vbo['a_tint']
        prog['a_size'] = 3.0
        prog['u_viewport'] = (32.0, 24.0)
        prog['u_alpha'] = 1.0

        gloo.set_state(blend=False, depth_test=False, cull_face=False)
        gloo.clear(color=(0.0, 0.0, 0.0, 1.0))
        prog.draw('points', ibo)
        p1 = _dawn.probe()['pending_draws']
        assert p1 >= 1

        # Mutate both VertexBuffer data, IndexBuffer indices, and constant point size BEFORE any readback/flush!
        updated = data.copy()
        updated['a_base'][:, 1] += 10.0
        vbo.set_data(updated)
        ibo.set_data(np.array([1, 3], dtype=np.uint16))
        prog['a_size'] = 1.0
        prog.draw('points', ibo)
        p2 = _dawn.probe()['pending_draws']
        assert p2 > p1, 'Both point revisions must remain queued before single readback'

        img = gloo.read_pixels((0, 0, 32, 24), alpha=True)
        palette = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
        expected = _expected_point_frame(
            32,
            24,
            [
                (6, 4, 3, palette[0], 1.0),
                (22, 4, 3, palette[2], 1.0),
                (14, 18, 1, palette[1], 1.0),
                (28, 18, 1, palette[3], 1.0),
            ],
        )
        np.testing.assert_array_equal(img, expected)


@pytest.mark.parametrize('method', ['points', 'instanced'])
def test_markers_visual_points_and_instanced_queued_revisions(method):
    from vispy import _dawn, gloo, scene

    size = (32, 24)
    canvas = scene.SceneCanvas(
        app='dawn_headless', size=size, show=False, bgcolor='black', config={'samples': 0}
    )
    attachments, depth_attachments, targets = [], [], []
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(
            rect=(0, 0, *size), aspect=None, flip=(False, True, False)
        )
        markers = scene.visuals.Markers(
            method=method, scaling='fixed', antialias=0.0, spherical=False, parent=view.scene
        )
        pos_initial = np.array([[8.0, 12.0], [24.0, 12.0]], dtype=np.float32)
        col_initial = np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0]], dtype=np.float32)
        markers.set_data(
            pos=pos_initial,
            size=6.0,
            edge_width=0.0,
            face_color=col_initial,
            symbol='square',
        )

        attachments = [gloo.RenderBuffer(size[::-1], format='color') for _ in range(3)]
        depth_attachments = [gloo.RenderBuffer(size[::-1], format='depth') for _ in range(3)]
        targets = [gloo.FrameBuffer(color=c, depth=d) for c, d in zip(attachments, depth_attachments)]

        def draw_fbo(fbo):
            canvas.push_fbo(fbo, (0, 0), size)
            try:
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=True)
                canvas.draw_visual(canvas.scene)
            finally:
                canvas.pop_fbo()
            return _dawn.probe()['pending_draws']

        p0 = draw_fbo(targets[0])
        markers.set_data(
            pos=np.array([[16.0, 12.0]], dtype=np.float32),
            size=8.0,
            edge_width=0.0,
            face_color=np.array([[0.0, 1.0, 0.0, 1.0]], dtype=np.float32),
            symbol='square',
        )
        p1 = draw_fbo(targets[1])
        markers.set_data(
            pos=pos_initial,
            size=6.0,
            edge_width=0.0,
            face_color=col_initial,
            symbol='square',
        )
        p2 = draw_fbo(targets[2])
        assert 0 < p0 < p1 < p2

        frames = []
        for fbo in targets:
            with fbo:
                frames.append(fbo.read())

        # Frame 0 & Frame 2: red at (y=12, x=8), blue at (y=12, x=24), black at center (y=12, x=16).
        np.testing.assert_array_equal(frames[0], frames[2])
        np.testing.assert_allclose(frames[0][12, 8], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(frames[0][12, 24], [0, 0, 255, 255], atol=2)
        np.testing.assert_array_equal(frames[0][12, 16], [0, 0, 0, 255])

        # Frame 1: green at center (y=12, x=16), black at x=8 and x=24.
        np.testing.assert_allclose(frames[1][12, 16], [0, 255, 0, 255], atol=2)
        np.testing.assert_array_equal(frames[1][12, 8], [0, 0, 0, 255])
        np.testing.assert_array_equal(frames[1][12, 24], [0, 0, 0, 255])
    finally:
        for fbo in targets:
            fbo.delete()
        for rb in attachments + depth_attachments:
            rb.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()
