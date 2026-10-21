"""Independent endpoint-isolation and clipped-interpolation line witnesses.

Criteria and inputs precede candidate implementation. Full reference RGBA is
compared exactly; analytic landmarks establish invocation/qualifier meaning.
"""
from __future__ import annotations

import hashlib
import numpy as np

if __package__:
    from .fixture_gloo import Runner, SIZE
else:
    from fixture_gloo import Runner, SIZE

CASES = tuple(f"{kind}_{raster}" for kind in
              ("private_state", "clipped_noperspective", "clipped_perspective")
              for raster in ("aliased", "smooth"))
SPEC_URL = "https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf"


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    private = name.startswith("private_state")
    return {
        "case": name, "size": list(SIZE), "primitive": "lines",
        "line_width": 3., "line_smooth": name.endswith("_smooth"),
        "blend": True, "depth_test": False, "stencil_test": False,
        "cull_face": False, "samples": 1, "readbacks": 1,
        "intermediate_finish": False,
        "points": [[4.5, 6.5], [28.5, 6.5]] if private else [[-16., 12.5], [48., 12.5]],
        "weights": [1., 1.] if private else [1., 3.],
        "colors": None if private else [[1., 0., 0., 1.], [0., 0., 1., 1.]],
        "qualifier": "flat" if private else "noperspective" if "noperspective" in name else "smooth",
        "private_state": "per-invocation initialized zero; one helper increments to one and leaves original position unchanged" if private else None,
        "comparison": "exact entire independently captured RGBA frame, no mask/alignment/tolerance",
        "clip_derivation": None if private else {
            "homogeneous_first_parameter_at_left_and_right": [.1, .5],
            "screen_first_parameter_at_left_and_right": [.25, .75],
            "screen_fraction": "q=t*w1/((1-t)*w0+t*w1)",
            "source": SPEC_URL, "sections": ["13.7.1", "14.5.1"],
        },
    }


def vertices(name):
    spec = specification(name)
    points = np.asarray(spec["points"], np.float32)
    weights = np.asarray(spec["weights"], np.float32)
    ndc = points / np.asarray(SIZE, np.float32) * 2 - 1
    return np.column_stack((ndc * weights[:, None], np.zeros(2, np.float32), weights)).astype(np.float32)


def shaders(name):
    spec = specification(name)
    qualifier = spec["qualifier"]
    if name.startswith("private_state"):
        vertex = """#version 330
in vec4 a_position;
flat out vec4 v_color;
float private_state = 0.;
vec4 evaluate_endpoint(vec4 position) {
    private_state += 1.;
    position.y += (private_state - 1.) * (16./24.) * position.w;
    return position;
}
void main() {
    gl_Position = evaluate_endpoint(a_position);
    v_color = vec4(0., private_state == 1. ? 1. : 0., private_state > 1. ? 1. : 0., 1.);
}
"""
    else:
        vertex = f"""#version 330
in vec4 a_position;
in vec4 a_color;
{qualifier} out vec4 v_color;
void main() {{ gl_Position = a_position; v_color = a_color; }}
"""
    fragment = f"""#version 330
{qualifier} in vec4 v_color;
out vec4 out_color;
void main() {{ out_color = v_color; }}
"""
    return vertex, fragment


def center_fraction(name, x):
    """Original endpoint weight at pixel center, before UNORM quantization."""
    spec = specification(name)
    if spec["colors"] is None:
        raise ValueError("Private-state output is flat")
    q = (x + .5 + 16.) / 64.
    if spec["qualifier"] == "noperspective":
        return q
    return (q / 3.) / ((1. - q) + q / 3.)


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    assert np.all(image[..., 3] == 255)
    for x, y in ((0, 0), (31, 23)):
        assert image[SIZE[1] - 1 - y, x].tolist() == [0, 0, 0, 255]
    if name.startswith("private_state"):
        for x in (8, 16, 24):
            for y in (5, 6, 7):
                assert image[SIZE[1] - 1 - y, x].tolist() == [0, 255, 0, 255], (name, x, y)
        assert not np.any(image[..., 0]) and not np.any(image[..., 2]), name
    else:
        row = image[SIZE[1] - 1 - 12]
        assert not np.any(image[..., 1]), name
        assert np.all(row[:, 0] > 0) and np.all(row[:, 2] > 0), name
        assert np.all(np.diff(row[:, 0].astype(int)) < 0), name
        assert np.all(np.diff(row[:, 2].astype(int)) > 0), name
        if "noperspective" in name:
            assert row[4, 0] > row[4, 2] and row[28, 2] > row[28, 0], name
            # The independently derived half-way crossing must be in this
            # adjacent pair; no byte threshold is fitted to a captured frame.
            assert row[15, 0] > row[15, 2] and row[16, 2] > row[16, 0], name
        else:
            # Perspective weighting moves the crossing to original screen q=.75,
            # at x=32; every viewport center lies before that crossing.
            assert np.all(row[:, 0] > row[:, 2]), name


def array_record(value):
    return {"dtype": value.dtype.str, "shape": list(value.shape),
            "sha256": hashlib.sha256(value.tobytes()).hexdigest()}


def contract():
    return {
        "schema": 1, "GPU_used": False, "candidate_seen": False,
        "cases": {name: {"specification": specification(name),
                         "vertices": array_record(vertices(name)),
                         "shader_sha256": [hashlib.sha256(s.encode()).hexdigest() for s in shaders(name)]}
                  for name in CASES},
        "private_state_model": {"isolated_invocations": [1., 1.], "shared_two_calls": [1., 2.],
                                "bad_second_endpoint_displacement_pixels": 8.},
        "clipped_interpolation_model": {"clip_t": [.1, .5], "screen_q": [.25, .75],
                                       "noperspective_crossing_pixel_boundary": 16.,
                                       "perspective_crossing_pixel_boundary": 32.},
        "quality": "entire reference RGBA exact; analytic state/gradient invariants frozen before any capture",
        "open_scope": "future native evaluator/expansion/clipping/coverage/depth/lifetime and sixteen original wide-line references",
    }


def render(name, backend="dawn_headless"):
    spec = specification(name)
    runner = Runner(backend, samples=0)
    runner.canvas()
    gloo = runner.gloo
    try:
        gloo.set_state(blend=True, depth_test=False, stencil_test=False,
                       scissor_test=False, cull_face=False, line_smooth=spec["line_smooth"])
        gloo.set_blend_func("src_alpha", "one_minus_src_alpha", "one", "one_minus_src_alpha")
        gloo.set_line_width(3.)
        vertex, fragment = shaders(name)
        program = gloo.Program(vertex, fragment)
        program["a_position"] = gloo.VertexBuffer(vertices(name))
        if spec["colors"] is not None:
            program["a_color"] = gloo.VertexBuffer(np.asarray(spec["colors"], np.float32))
        program.draw("lines")
        image = runner.read()
        observations = {"samples_raw": int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES)),
                        "readbacks": runner.readbacks,
                        "candidate_seen": backend != "pyqt6"}
        if backend == "pyqt6":
            observations.update(line_width=float(gloo.gl.glGetParameter(0x0B21)),
                                line_smooth_enabled=bool(gloo.gl.glGetParameter(0x0B20)),
                                state_query_kind="actual upstream OpenGL after one final readback")
            assert observations["line_width"] == 3.
            assert observations["line_smooth_enabled"] == spec["line_smooth"]
        assert observations["samples_raw"] in (0, 1) and runner.readbacks == 1
        return image, runner.commands, runner.shaders, spec, observations
    except Exception as error:
        error.fixture_commands, error.fixture_shaders = runner.commands, runner.shaders
        error.fixture_parameters = spec
        raise
    finally:
        runner.close()
