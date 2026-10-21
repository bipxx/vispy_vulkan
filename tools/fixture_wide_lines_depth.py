"""Same fixed wide-line depth case with a defined public depth attachment.

The original color-only setup and its failed admission remain immutable. This
variant adds an explicit depth clear before the unchanged near/far draws.
"""

from __future__ import annotations

import numpy as np

if __package__:
    from .fixture_gloo import Runner
    from .fixture_wide_lines import assert_landmarks, clip_positions, specification as original_specification
else:
    from fixture_gloo import Runner
    from fixture_wide_lines import assert_landmarks, clip_positions, specification as original_specification

CASES = ("depth_occlusion_smooth",)


def specification(name):
    assert name in CASES
    return {**original_specification(name), "public_initial_depth_clear": 1., "explicit_depth_func": "less"}


def render(name, backend="dawn_headless"):
    params = specification(name)
    runner = Runner(backend, samples=0)
    gloo = runner.gloo
    runner.canvas()
    try:
        raw_samples = int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))
        assert raw_samples in (0, 1)
        observations = {"samples_raw": raw_samples, "physical_samples": max(1, raw_samples),
                        "sample_query_kind": "actual OpenGL target" if backend == "pyqt6" else "candidate configured-target facade"}
        gloo.set_clear_depth(1)
        gloo.clear(color=False, depth=True, stencil=False)
        gloo.set_state(blend=True, depth_test=True, line_smooth=True)
        gloo.set_depth_func("less")
        gloo.set_blend_func(*params["blend_rgb"], *params["blend_alpha"])
        gloo.set_line_width(3)
        program = gloo.Program("attribute vec4 a_position; void main() { gl_Position = a_position; }",
                               "uniform vec4 u_color; void main() { gl_FragColor = u_color; }")
        program["a_position"] = gloo.VertexBuffer(clip_positions(params["points"], -.5, params["weights"]))
        program["u_color"] = (1, 0, 0, 1)
        program.draw("lines")
        program["a_position"] = gloo.VertexBuffer(clip_positions([[4.5, 12.5], [28.5, 12.5]], .5))
        program["u_color"] = (0, 1, 0, 1)
        program.draw("lines")
        image = runner.read()
        if backend == "pyqt6":
            from OpenGL import GL

            def values(enum):
                return np.asarray(gloo.gl.glGetParameter(enum), np.float64).reshape(-1).tolist()

            def float_values(enum):
                return np.asarray(GL.glGetFloatv(enum), np.float64).reshape(-1).tolist()

            observations.update({"state_query_kind": "actual OpenGL driver after final readback",
                "depth_func": int(values(0x0B74)[0]),
                "line_width": values(0x0B21)[0], "line_smooth_enabled": bool(values(0x0B20)[0]),
                "aliased_line_width_range": values(0x846E),
                "smooth_range_query_api": "PyOpenGL.GL.glGetFloatv; pinned generic gloo getter would round these float-only observations",
                "smooth_line_width_range": float_values(0x0B22), "smooth_line_width_granularity": float_values(0x0B23)[0]})
            assert observations["line_width"] == 3 and observations["line_smooth_enabled"]
            assert observations["depth_func"] == 0x0201
        else:
            observations["state_query_kind"] = "candidate has no OpenGL driver; fixed state is tested by native output"
        return image, runner.commands, runner.shaders, params, observations
    except Exception as error:
        error.fixture_commands, error.fixture_shaders, error.fixture_parameters = runner.commands, runner.shaders, params
        raise
    finally:
        runner.close()
