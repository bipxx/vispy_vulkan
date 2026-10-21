"""Three-pixel GL lines and smoothing used by the unchanged plugin visuals.

Inputs and analytic interior/coverage landmarks are frozen before a candidate
run. Endpoint and fringe samples also remain subject to whole-frame equality.
All dependent state updates/draws precede one final color readback.
"""

from __future__ import annotations

import hashlib
import numpy as np

if __package__:
    from .fixture_gloo import Runner, SIZE
else:
    from fixture_gloo import Runner, SIZE

CASES = ("horizontal_aliased", "vertical_aliased", "diagonal_aliased",
         "horizontal_smooth", "vertical_smooth", "diagonal_smooth_forward", "diagonal_smooth_reverse",
         "strip_alpha_smooth", "loop_alpha_smooth", "endpoints_smooth",
         "color_smooth", "perspective_color_smooth", "flat_last_smooth",
         "depth_occlusion_smooth", "scissor_smooth", "ordered_width_smooth")
BLACK, GREEN, RED = [0, 0, 0, 255], [0, 255, 0, 255], [255, 0, 0, 255]
QUARTER_GREEN, DOUBLE_QUARTER_GREEN = [0, 64, 0, 255], [0, 112, 0, 255]


def clip_positions(points, z=0., w=None):
    points = np.asarray(points, np.float32)
    weights = np.ones(len(points), np.float32) if w is None else np.asarray(w, np.float32)
    ndc = points / np.asarray(SIZE, np.float32) * 2 - 1
    return np.column_stack((ndc * weights[:, None], np.full(len(points), z, np.float32) * weights, weights)).astype(np.float32)


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    spec = {"case": name, "size": list(SIZE), "primitive": "lines", "line_width": 3.,
            "line_smooth": not name.endswith("aliased"), "blend": True,
            "blend_rgb": ["src_alpha", "one_minus_src_alpha"], "blend_alpha": ["one", "one_minus_src_alpha"],
            "source_alpha": .25 if "alpha" in name else 1., "depth_test": False,
            "shader": "solid", "scissor": None, "ordered_widths": None,
            "readbacks": 1, "intermediate_finish": False,
            "comparison": "entire fixed driver frame exact; no masks, alignment or tolerance"}
    if name.startswith("vertical"):
        points = [[12.5, 4.5], [12.5, 20.5]]
    elif name.startswith("diagonal"):
        points = [[4.5, 4.5], [24.5, 18.5]]
        if name.endswith("reverse"):
            points.reverse()
    elif name == "strip_alpha_smooth":
        points = [[4.5, 6.5], [16.5, 6.5], [16.5, 18.5]]
        spec["primitive"] = "line_strip"
    elif name == "loop_alpha_smooth":
        points = [[4.5, 4.5], [26.5, 4.5], [26.5, 18.5], [4.5, 18.5]]
        spec["primitive"] = "line_loop"
    elif name == "endpoints_smooth":
        points = [[4.25, 6.25], [24.75, 6.25], [12.25, 12.25], [12.25, 20.75]]
    elif name == "depth_occlusion_smooth":
        points = [[16.5, 4.5], [16.5, 20.5]]
        spec["depth_test"] = True
    elif name == "scissor_smooth":
        points = [[-4.5, 12.5], [35.5, 12.5], [16.5, -4.5], [16.5, 29.5]]
        spec["scissor"] = [6, 5, 20, 14]
    else:
        points = [[4.5, 6.5], [28.5, 6.5]]
    if name in ("color_smooth", "perspective_color_smooth", "flat_last_smooth"):
        spec["shader"] = "flat-last" if name == "flat_last_smooth" else "color"
        spec["colors"] = [[1., 0., 0., 1.], [0., 1., 0., 1.]] if name == "flat_last_smooth" else [[1., 0., 0., 1.], [0., 0., 1., 1.]]
    else:
        spec["colors"] = None
    spec["points"] = points
    spec["weights"] = [1., 2.] if name == "perspective_color_smooth" else [1.] * len(points)
    if name == "ordered_width_smooth":
        spec["ordered_widths"] = [3., 1.]
    vertices = clip_positions(points, -.5 if name == "depth_occlusion_smooth" else 0., spec["weights"])
    spec["vertices_sha256"] = hashlib.sha256(vertices.tobytes()).hexdigest()
    return spec


def landmarks(name):
    marks = [([0, 0], BLACK), ([31, 23], BLACK)]
    if name.startswith("horizontal"):
        marks += [([10, y], GREEN) for y in (5, 6, 7)]
        marks += [([10, 4], BLACK), ([10, 8], BLACK), ([2, 6], BLACK), ([30, 6], BLACK)]
    elif name.startswith("vertical"):
        marks += [([x, 10], GREEN) for x in (11, 12, 13)]
        marks += [([10, 10], BLACK), ([14, 10], BLACK)]
    elif name.startswith("diagonal"):
        marks += [([14, 11], GREEN), ([14, 5], BLACK), ([14, 17], BLACK)]
    elif name == "strip_alpha_smooth":
        marks += [([8, 6], QUARTER_GREEN), ([16, 12], QUARTER_GREEN), ([15, 7], DOUBLE_QUARTER_GREEN)]
    elif name == "loop_alpha_smooth":
        marks += [([12, 4], QUARTER_GREEN), ([26, 12], QUARTER_GREEN), ([12, 12], BLACK)]
    elif name == "endpoints_smooth":
        marks += [([8, 6], GREEN), ([12, 15], GREEN), ([3, 6], BLACK), ([26, 6], BLACK)]
    elif name == "flat_last_smooth":
        marks += [([8, 6], GREEN), ([20, 6], GREEN), ([20, 5], GREEN), ([20, 7], GREEN)]
    elif name == "depth_occlusion_smooth":
        marks += [([16, 12], RED), ([16, 6], RED), ([8, 12], GREEN), ([24, 12], GREEN)]
    elif name == "scissor_smooth":
        marks += [([8, 12], GREEN), ([16, 8], GREEN), ([5, 12], BLACK), ([26, 12], BLACK), ([16, 4], BLACK), ([16, 19], BLACK)]
    elif name == "ordered_width_smooth":
        marks += [([12, y], GREEN) for y in (5, 6, 7)]
        marks += [([12, 18], RED), ([12, 17], BLACK), ([12, 19], BLACK)]
    return marks


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert np.all(image[..., 3] == 255)
    for (x, y), expected in landmarks(name):
        assert image[SIZE[1] - 1 - y, x].tolist() == expected, (name, "fixed wide-line landmark", [x, y],
                                                               image[SIZE[1] - 1 - y, x].tolist(), expected)
    if name in ("color_smooth", "perspective_color_smooth"):
        first, last = (image[SIZE[1] - 1 - 6, x].astype(int) for x in (8, 24))
        assert first[0] > first[2] > 0 and last[2] > last[0] > 0, (name, first, last)
        assert not np.any(image[..., 1])
    if name == "endpoints_smooth":
        fringe = image[SIZE[1] - 1 - 6, 4]
        assert fringe[0] == fringe[2] == 0 and 0 < fringe[1] < 255, (name, "analytic partial endpoint coverage", fringe)


def render(name, backend="dawn_headless"):
    spec = specification(name)
    runner = Runner(backend, samples=0)
    gloo = runner.gloo
    runner.canvas()
    try:
        raw_samples = int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))
        assert raw_samples in (0, 1)
        observations = {"samples_raw": raw_samples, "physical_samples": max(1, raw_samples),
                        "sample_query_kind": "actual OpenGL target" if backend == "pyqt6" else "candidate configured-target facade"}
        gloo.set_state(blend=True, depth_test=spec["depth_test"], line_smooth=spec["line_smooth"])
        gloo.set_blend_func(*spec["blend_rgb"], *spec["blend_alpha"])
        gloo.set_line_width(3)
        if name == "depth_occlusion_smooth":
            gloo.set_depth_mask(True)
            gloo.set_depth_func("less")
            gloo.set_depth_range(0, 1)
            gloo.set_clear_depth(1)
            gloo.clear(color=False, depth=True, stencil=False)
        if spec["scissor"]:
            gloo.set_state(scissor_test=True)
            gloo.set_scissor(*spec["scissor"])
        vertices = clip_positions(spec["points"], -.5 if name == "depth_occlusion_smooth" else 0., spec["weights"])
        if spec["shader"] in ("color", "flat-last"):
            if spec["shader"] == "flat-last":
                vertex = """#version 130
                in vec4 a_position; in vec4 a_color; flat out vec4 v_color;
                void main() { gl_Position = a_position; v_color = a_color; }
                """
                fragment = """#version 130
                flat in vec4 v_color; out vec4 out_color;
                void main() { out_color = v_color; }
                """
            else:
                vertex = "attribute vec4 a_position; attribute vec4 a_color; varying vec4 v_color; void main() { gl_Position = a_position; v_color = a_color; }"
                fragment = "varying vec4 v_color; void main() { gl_FragColor = v_color; }"
            program = gloo.Program(vertex, fragment)
            program["a_color"] = gloo.VertexBuffer(np.asarray(spec["colors"], np.float32))
        else:
            program = gloo.Program("attribute vec4 a_position; void main() { gl_Position = a_position; }",
                                   "uniform vec4 u_color; void main() { gl_FragColor = u_color; }")
            program["u_color"] = (1, 0, 0, 1) if name == "depth_occlusion_smooth" else (0, 1, 0, spec["source_alpha"])
        program["a_position"] = gloo.VertexBuffer(vertices)
        program.draw(spec["primitive"])
        if name == "depth_occlusion_smooth":
            program["a_position"] = gloo.VertexBuffer(clip_positions([[4.5, 12.5], [28.5, 12.5]], .5))
            program["u_color"] = (0, 1, 0, 1)
            program.draw("lines")
        elif name == "ordered_width_smooth":
            gloo.set_line_width(1)
            program["a_position"] = gloo.VertexBuffer(clip_positions([[4.5, 18.5], [28.5, 18.5]]))
            program["u_color"] = (1, 0, 0, 1)
            program.draw("lines")
        image = runner.read()
        if backend == "pyqt6":
            from OpenGL import GL

            def values(enum):
                return np.asarray(gloo.gl.glGetParameter(enum), np.float64).reshape(-1).tolist()

            def float_values(enum):
                # Pinned VisPy's generic getter uses glGetIntegerv for the two
                # smooth-only enums. Use their actual GL float query so driver
                # granularity/range fractions are preserved in diagnostics.
                return np.asarray(GL.glGetFloatv(enum), np.float64).reshape(-1).tolist()

            # Query after the final read flushes every dependent draw/state.
            # These are real OpenGL values, not configured-input metadata.
            observations.update({"state_query_kind": "actual OpenGL driver after final readback",
                "line_width": values(0x0B21)[0], "line_smooth_enabled": bool(values(0x0B20)[0]),
                "aliased_line_width_range": values(0x846E),
                "smooth_range_query_api": "PyOpenGL.GL.glGetFloatv; pinned generic gloo getter would round these float-only observations",
                "smooth_line_width_range": float_values(0x0B22), "smooth_line_width_granularity": float_values(0x0B23)[0]})
            assert observations["line_width"] == (1 if name == "ordered_width_smooth" else 3)
            assert observations["line_smooth_enabled"] == spec["line_smooth"]
            assert observations["smooth_line_width_range"][1] >= 3
        else:
            observations["state_query_kind"] = "candidate has no OpenGL driver; fixed state is tested by native output"
        return image, runner.commands, runner.shaders, spec, observations
    except Exception as error:
        error.fixture_commands = runner.commands
        error.fixture_shaders = runner.shaders
        error.fixture_parameters = spec
        raise
    finally:
        runner.close()
