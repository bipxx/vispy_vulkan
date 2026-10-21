"""Exact-driver line oracle with fixed geometry and analytic landmarks."""

from __future__ import annotations

import hashlib

import numpy as np

if __package__:
    from .fixture_gloo import Runner, SIZE
else:
    from fixture_gloo import Runner, SIZE

CASES = ("octants_forward", "octants_reverse", "slopes_forward", "slopes_reverse",
         "half_open_endpoints", "loop_alpha", "join_straight_alpha", "join_orthogonal_alpha",
         "join_acute_alpha", "degenerate_equal", "two_vertex_loop_alpha", "clipped_segment",
         "scissor_lines", "perspective_color", "flat_provoking_color")
BLACK, GREEN, QUARTER_GREEN = [0, 0, 0, 255], [0, 255, 0, 255], [0, 64, 0, 255]
OCTANTS = ((10, 4), (4, 10), (-4, 10), (-10, 4), (-10, -4), (-4, -10), (4, -10), (10, -4))


def geometry(name):
    if name not in CASES:
        raise ValueError(name)
    primitive = "lines"
    if name.startswith("octants"):
        center = np.array([16.375, 12.375])
        points = np.array([[center, center + delta] for delta in np.array(OCTANTS)], np.float32)
        if name.endswith("reverse"):
            points = points[:, ::-1]
        points = points.reshape(-1, 2)
    elif name.startswith("slopes"):
        points = np.array([[[3.375, 3.375], [13.375, 8.375]],
                           [[18.375, 3.375], [23.375, 13.375]],
                           [[3.375, 13.375], [11.375, 21.375]]], np.float32)
        if name.endswith("reverse"):
            points = points[:, ::-1]
        points = points.reshape(-1, 2)
    elif name == "half_open_endpoints":
        points = [[4.5, 6.5], [24.5, 6.5], [4.5, 10.5], [4.5, 20.5]]
    elif name == "loop_alpha":
        points, primitive = [[4.5, 4.5], [26.5, 4.5], [26.5, 18.5], [4.5, 18.5]], "line_loop"
    elif name == "join_straight_alpha":
        points, primitive = [[4.5, 6.5], [16.5, 6.5], [26.5, 6.5]], "line_strip"
    elif name == "join_orthogonal_alpha":
        points, primitive = [[4.5, 6.5], [16.5, 6.5], [16.5, 18.5]], "line_strip"
    elif name == "join_acute_alpha":
        points, primitive = [[4.375, 4.375], [16.375, 12.375], [24.375, 6.375]], "line_strip"
    elif name == "degenerate_equal":
        points = [[10.375, 10.375], [10.375, 10.375]]
    elif name == "two_vertex_loop_alpha":
        points, primitive = [[5.375, 7.375], [25.375, 7.375]], "line_loop"
    elif name in ("clipped_segment", "scissor_lines"):
        points = [[-5.375, 12.375], [35.375, 12.375]]
        if name == "scissor_lines":
            points += [[16.375, -4.375], [16.375, 29.375]]
    elif name == "perspective_color":
        points = [[4.5, 6.5], [26.5, 18.5]]
    else:
        points = [[5.5, 6.5], [26.5, 6.5]]
    return np.asarray(points, np.float32), primitive


def landmarks(name):
    result = [([0, 0], BLACK), ([31, 23], BLACK)]
    if name.startswith("octants"):
        reverse = name.endswith("reverse")
        result += [([16, 12], BLACK if reverse else GREEN)]
        for dx, dy in OCTANTS:
            result += [([16 + dx // 2, 12 + dy // 2], GREEN),
                       ([16 + dx, 12 + dy], GREEN if reverse else BLACK)]
    elif name.startswith("slopes"):
        result += [([7, 5], GREEN), ([20, 7], GREEN), ([7, 17], GREEN)]
    elif name == "half_open_endpoints":
        result += [([4, 6], GREEN), ([23, 6], GREEN), ([24, 6], BLACK),
                   ([4, 10], GREEN), ([4, 19], GREEN), ([4, 20], BLACK)]
    elif name == "loop_alpha":
        result += [(point, QUARTER_GREEN) for point in ([4, 4], [26, 4], [26, 18], [4, 18], [16, 4])]
    elif name in ("join_straight_alpha", "join_orthogonal_alpha"):
        result += [([16, 6], QUARTER_GREEN), ([5, 6], QUARTER_GREEN)]
    elif name == "join_acute_alpha":
        result += [([16, 12], QUARTER_GREEN)]
    elif name == "two_vertex_loop_alpha":
        result += [([5, 7], QUARTER_GREEN), ([25, 7], QUARTER_GREEN), ([16, 7], [0, 112, 0, 255])]
    elif name == "clipped_segment":
        result += [([0, 12], GREEN), ([16, 12], GREEN), ([31, 12], GREEN)]
    elif name == "scissor_lines":
        result += [([5, 12], GREEN), ([3, 12], BLACK), ([16, 4], GREEN), ([16, 19], BLACK)]
    elif name == "flat_provoking_color":
        result += [([6, 6], GREEN), ([16, 6], GREEN), ([25, 6], GREEN)]
    return result


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert np.all(image[..., 3] == 255)
    for (x, y), rgba in landmarks(name):
        assert image[SIZE[1] - 1 - y, x].tolist() == rgba, (name, "fixed line landmark", [x, y],
                                                             image[SIZE[1] - 1 - y, x].tolist(), rgba)
    if name == "degenerate_equal":
        assert np.all(image == BLACK), "a zero-length half-open GL line emits no fragments"
    if name == "perspective_color":
        assert np.all(image[..., 1] == 0)
        first = image[SIZE[1] - 1 - 8, 7]
        last = image[SIZE[1] - 1 - 16, 22]
        assert first[0] > first[2] > 0 and last[2] > last[0] > 0, (first.tolist(), last.tolist())
    if name.endswith("alpha") and name != "two_vertex_loop_alpha":
        assert set(np.unique(image[..., 1]).tolist()) == {0, 64}, "one fragment per covered join pixel"


def render(name, backend="dawn_headless"):
    points, primitive = geometry(name)
    runner = Runner(backend)
    gloo = runner.gloo
    runner.canvas()
    try:
        positions = points / np.array(SIZE, np.float32) * 2 - 1
        alpha = name.endswith("alpha")
        if alpha:
            gloo.set_state(blend=True)
            gloo.set_blend_func("src_alpha", "one_minus_src_alpha", "one", "one_minus_src_alpha")
        gloo.set_line_width(1)
        if name == "scissor_lines":
            gloo.set_state(scissor_test=True)
            gloo.set_scissor(4, 3, 19, 16)
        if name == "perspective_color":
            w = np.array([1, 2], np.float32)
            clip = np.column_stack([positions * w[:, None], np.zeros(2, np.float32), w]).astype(np.float32)
            program = gloo.Program("""
                attribute vec4 a_position; attribute vec4 a_color; varying vec4 v_color;
                void main() { gl_Position = a_position; v_color = a_color; }
            """, "varying vec4 v_color; void main() { gl_FragColor = v_color; }")
            program["a_position"] = gloo.VertexBuffer(clip)
            program["a_color"] = gloo.VertexBuffer(np.array([[1, 0, 0, 1], [0, 0, 1, 1]], np.float32))
        elif name == "flat_provoking_color":
            program = gloo.Program("""#version 130
                in vec2 a_position; in vec4 a_color; flat out vec4 v_color;
                void main() { gl_Position = vec4(a_position, 0.0, 1.0); v_color = a_color; }
            """, """#version 130
                flat in vec4 v_color; out vec4 out_color;
                void main() { out_color = v_color; }
            """)
            program["a_position"] = gloo.VertexBuffer(positions)
            program["a_color"] = gloo.VertexBuffer(np.array([[1, 0, 0, 1], [0, 1, 0, 1]], np.float32))
        else:
            program = runner.solid(positions, color=(0, 1, 0, .25 if alpha else 1))
        program.draw(primitive)
        image = runner.read()
        params = {"case": name, "size": list(SIZE), "primitive": primitive, "points": points.tolist(),
                  "points_sha256": hashlib.sha256(points.tobytes()).hexdigest(), "line_width": 1,
                  "blending": alpha, "source_alpha": .25 if alpha else 1,
                  "readbacks": 1, "intermediate_finish": False, "physical_samples": 1,
                  "comparison": "entire fixed driver frame exact; fixed independent landmarks",
                  "varying": "perspective" if name == "perspective_color" else "flat-last-provoking" if name == "flat_provoking_color" else "constant"}
        return image, runner.commands, runner.shaders, params
    except Exception as error:
        error.fixture_commands = runner.commands
        error.fixture_shaders = runner.shaders
        raise
    finally:
        runner.close()
