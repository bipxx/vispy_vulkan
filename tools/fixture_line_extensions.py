"""Additional fixed line clipping, depth and vertex-selection qualifications.

The original fifteen-case corpus is immutable. These inputs and landmarks are
authored independently before a candidate run. All dependent draws remain
pending until the single final color readback.
"""

from __future__ import annotations

import hashlib
import numpy as np

if __package__:
    from .fixture_gloo import Runner, SIZE
else:
    from fixture_gloo import Runner, SIZE

CASES = ("near_clip", "far_clip", "near_far_perspective_clip",
         "depth_gradient_color", "perspective_depth_color", "depth_occlusion",
         "indexed_uint8", "indexed_uint16", "indexed_uint32",
         "nonzero_first_vertex_id", "indexed_vertex_id", "loop_indexed_vertex_id")
BLACK, GREEN, RED, BLUE = [0, 0, 0, 255], [0, 255, 0, 255], [255, 0, 0, 255], [0, 0, 255, 255]


def clip_positions(pixels, z=None, w=None):
    pixels = np.asarray(pixels, np.float32)
    count = len(pixels)
    w = np.ones(count, np.float32) if w is None else np.asarray(w, np.float32)
    z = np.zeros(count, np.float32) if z is None else np.asarray(z, np.float32)
    ndc = pixels / np.asarray(SIZE, np.float32) * 2 - 1
    return np.column_stack((ndc * w[:, None], z, w)).astype(np.float32)


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    spec = {"primitive": "lines", "depth_test": False, "first": 0}
    if name in ("near_clip", "far_clip", "near_far_perspective_clip"):
        y = 6.5 if name == "near_clip" else 18.5 if name == "far_clip" else 12.5
        z, w = {"near_clip": ([-2, 0], [1, 1]),
                "far_clip": ([0, 2], [1, 1]),
                "near_far_perspective_clip": ([-2, 4], [1, 2])}[name]
        spec["vertices"] = clip_positions([[4.5, y], [28.5, y]], z, w)
        spec["shader"] = "solid"
    elif name in ("depth_gradient_color", "perspective_depth_color", "depth_occlusion"):
        w = [1, 2] if name == "perspective_depth_color" else [1, 1]
        spec["vertices"] = clip_positions([[4.5, 12.5], [28.5, 12.5]],
                                           np.asarray([-.75, .75]) * w, w)
        spec["shader"] = "depth-color" if name != "depth_occlusion" else "solid"
        spec["depth_test"] = name == "depth_occlusion"
    elif name.startswith("indexed_uint"):
        spec["vertices"] = clip_positions([[28.5, 6.5], [28.5, 18.5],
                                           [4.5, 6.5], [4.5, 18.5], [80, 80]])
        spec["indices"] = np.asarray([2, 0, 3, 1], getattr(np, name.removeprefix("indexed_")))
        spec["shader"] = "solid"
    elif name == "nonzero_first_vertex_id":
        spec["vertices"] = clip_positions([[4.5, 20.5], [28.5, 20.5],
                                           [4.5, 6.5], [28.5, 6.5]])
        spec.update(shader="first-id", first=2, count=2)
    elif name == "indexed_vertex_id":
        spec["vertices"] = clip_positions([[80, 80], [4.5, 6.5], [4.5, 18.5],
                                           [28.5, 6.5], [28.5, 18.5]])
        spec["indices"] = np.asarray([2, 4, 1, 3], np.uint16)
        spec["shader"] = "index-id"
    else:
        spec["vertices"] = clip_positions([[80, 80], [6.5, 5.5], [80, 80], [25.5, 5.5],
                                           [80, 80], [25.5, 18.5], [80, 80], [6.5, 18.5]])
        spec["indices"] = np.asarray([1, 3, 5, 7], np.uint32)
        spec.update(shader="loop-id", primitive="line_loop")
    return spec


def landmarks(name):
    marks = [([0, 0], BLACK), ([31, 23], BLACK)]
    if name == "near_clip":
        marks += [([8, 6], BLACK), ([15, 6], BLACK), ([20, 6], GREEN), ([27, 6], GREEN), ([29, 6], BLACK)]
    elif name == "far_clip":
        marks += [([5, 18], GREEN), ([12, 18], GREEN), ([20, 18], BLACK), ([27, 18], BLACK)]
    elif name == "near_far_perspective_clip":
        # Homogeneous near intersection t=1/7 -> window x=10.5;
        # far intersection t=3/5 -> window x=22.5. Test safe interiors.
        marks += [([8, 12], BLACK), ([12, 12], GREEN), ([20, 12], GREEN), ([25, 12], BLACK)]
    elif name in ("depth_gradient_color", "perspective_depth_color"):
        marks += [([5, 12], RED), ([12, 12], RED), ([20, 12], GREEN), ([27, 12], GREEN)]
    elif name == "depth_occlusion":
        marks += [([5, 12], GREEN), ([12, 12], GREEN), ([20, 12], RED), ([27, 12], RED)]
    elif name.startswith("indexed_uint"):
        marks += [([5, 6], GREEN), ([27, 6], GREEN), ([5, 18], GREEN), ([27, 18], GREEN),
                  ([28, 6], BLACK), ([28, 18], BLACK), ([16, 12], BLACK)]
    elif name == "nonzero_first_vertex_id":
        marks += [([5, 6], GREEN), ([27, 6], GREEN), ([16, 20], BLACK)]
    elif name == "indexed_vertex_id":
        marks += [([5, 6], BLUE), ([27, 6], BLUE), ([5, 18], GREEN), ([27, 18], GREEN)]
    else:
        marks += [([6, 5], GREEN), ([25, 5], GREEN), ([25, 18], GREEN), ([6, 18], GREEN),
                  ([16, 12], BLACK)]
    return marks


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert np.all(image[..., 3] == 255)
    for (x, y), color in landmarks(name):
        actual = image[SIZE[1] - 1 - y, x].tolist()
        assert actual == color, (name, "independent clipping/depth/ID landmark", [x, y], actual, color)
    if name in ("depth_gradient_color", "perspective_depth_color", "depth_occlusion"):
        colors = {tuple(color) for color in image.reshape(-1, 4)}
        assert colors == {tuple(BLACK), tuple(GREEN), tuple(RED)}


def render(name, backend="dawn_headless"):
    spec = specification(name)
    runner = Runner(backend, samples=0)
    canvas = runner.canvas()
    gloo = runner.gloo
    try:
        # This is an actual driver query upstream. Dawn's GL facade returns
        # canvas configuration; preserve that distinction as an observation.
        raw_samples = int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))
        assert raw_samples in (0, 1), ("single-sample target required", raw_samples)
        observations = {"samples_raw": raw_samples, "physical_samples": max(1, raw_samples),
                        "sample_api": "gloo.gl.glGetParameter(GL_SAMPLES)",
                        "sample_source": "OpenGL driver query" if backend == "pyqt6" else "Dawn GL facade configuration query"}
        gloo.set_line_width(1)
        if spec["depth_test"]:
            gloo.set_state(depth_test=True)
            gloo.set_depth_func("less")
            gloo.clear(color=False, depth=True, stencil=False)
        fragment = "void main() { gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }"
        if spec["shader"] == "depth-color":
            fragment = "void main() { gl_FragColor = gl_FragCoord.z < 0.5 ? vec4(1,0,0,1) : vec4(0,1,0,1); }"
        if spec["shader"] in ("first-id", "index-id", "loop-id"):
            expression = {"first-id": "gl_VertexID / 2 == 1 ? vec4(0,1,0,1) : vec4(1,0,0,1)",
                          "index-id": "gl_VertexID % 2 == 0 ? vec4(0,1,0,1) : vec4(0,0,1,1)",
                          "loop-id": "gl_VertexID % 2 == 1 ? vec4(0,1,0,1) : vec4(1,0,0,1)"}[spec["shader"]]
            vertex = "#version 130\nin vec4 a_position; out vec4 v_color;\nvoid main() { gl_Position = a_position; v_color = " + expression + "; }"
            fragment = "#version 130\nin vec4 v_color; void main() { gl_FragColor = v_color; }"
        else:
            vertex = "attribute vec4 a_position; void main() { gl_Position = a_position; }"
        program = gloo.Program(vertex, fragment)
        program["a_position"] = gloo.VertexBuffer(spec["vertices"])
        indices = gloo.IndexBuffer(spec["indices"]) if "indices" in spec else None
        program.draw(spec["primitive"], indices)
        if spec["first"]:
            runner.clear((0, 0, 0, 1))
            canvas.context.glir.command("DRAW", program.id, spec["primitive"], (spec["first"], spec["count"]), 1)
            canvas.context.flush_commands()
        if name == "depth_occlusion":
            nearer = gloo.Program(vertex, "void main() { gl_FragColor = vec4(1,0,0,1); }")
            nearer["a_position"] = gloo.VertexBuffer(clip_positions([[4.5, 12.5], [28.5, 12.5]]))
            nearer.draw("lines")
        image = runner.read()
        parameters = {"case": name, "size": list(SIZE), "vertices": spec["vertices"].tolist(),
                      "vertices_sha256": hashlib.sha256(spec["vertices"].tobytes()).hexdigest(),
                      "primitive": spec["primitive"], "shader": spec["shader"],
                      "depth_test": spec["depth_test"], "first": spec["first"],
                      "readbacks": 1, "line_width": 1, "intermediate_finish": False,
                      "comparison": "entire driver frame exact and fixed independent landmarks"}
        if "indices" in spec:
            parameters.update(indices=spec["indices"].tolist(), index_dtype=spec["indices"].dtype.str,
                              indices_sha256=hashlib.sha256(spec["indices"].tobytes()).hexdigest())
        if spec["first"]:
            parameters.update(count=spec["count"], setup_draw_discarded_by_ordered_clear=True,
                              selection_api="context.glir.command; public Program.draw always uses first=0")
        return image, runner.commands, runner.shaders, parameters, observations
    except Exception as error:
        error.fixture_commands = runner.commands
        error.fixture_shaders = runner.shaders
        raise
    finally:
        runner.close()
