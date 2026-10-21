"""GL-spec stencil oracle, distinct from VisPy0.17's broken stencil wrapper.

Upstream draws remain public gloo. A real external PyOpenGL stencil read proves
GL semantics; the candidate uses its public gloo stencil capture implementation.
Neither path changes installed upstream code or pretends its wrapper works.
"""

from __future__ import annotations

import numpy as np

if __package__:
    from .fixture_gloo import Runner
    from .fixture_depth_capture import SIZE, PACKED_DEPTH_STENCIL, specification as depth_specification
    from .fixture_depth_capture import assert_expected, expected_image
else:
    from fixture_gloo import Runner
    from fixture_depth_capture import SIZE, PACKED_DEPTH_STENCIL, specification as depth_specification
    from fixture_depth_capture import assert_expected, expected_image

CASES = ("stencil_float", "stencil_u8", "stencil_crop_float", "stencil_noalpha_u8")


def specification(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    spec = depth_specification(name)
    spec["capture_api"] = "PyOpenGL.GL.glReadPixels(GL_STENCIL_INDEX)" if backend == "pyqt6" else "gloo.read_pixels(mode='stencil')"
    spec["explicit_gloo_finish_calls"] = 1 if backend == "pyqt6" else 0
    spec["oracle_scope"] = "GL stencil semantics; upstream VisPy wrapper remains unadmitted"
    spec["output_units"] = "unnormalized stencil integer values"
    return spec


def render(name, backend="dawn_headless"):
    spec = specification(name, backend)
    runner = Runner(backend)
    gloo = runner.gloo
    runner.canvas()
    try:
        color = gloo.Texture2D(np.zeros((SIZE[1], SIZE[0], 4), np.uint8))
        packed = gloo.RenderBuffer((SIZE[1], SIZE[0]), format=PACKED_DEPTH_STENCIL)
        target = gloo.FrameBuffer(color=color, depth=packed, stencil=packed)
        with target:
            gloo.set_viewport(0, 0, *SIZE)
            gloo.set_state(scissor_test=False, depth_test=True, stencil_test=True)
            gloo.set_depth_mask(True)
            gloo.set_stencil_mask(255)
            gloo.set_clear_depth(1)
            gloo.set_clear_stencil(3)
            gloo.set_clear_color((0, 0, 0, 1))
            gloo.clear(color=True, depth=True, stencil=True)
            gloo.set_state(scissor_test=True)
            gloo.set_scissor(4, 3, 3, 2)
            gloo.set_clear_depth(.75)
            gloo.set_clear_stencil(203)
            gloo.clear(color=False, depth=True, stencil=True)
            gloo.set_scissor(1, 1, 3, 2)
            gloo.set_depth_func("always")
            gloo.set_stencil_func("always", 37, 255)
            gloo.set_stencil_op("keep", "keep", "replace")
            runner.solid(color=(0, 1, 0, 1), vert="""
                attribute vec2 a_position;
                void main() { gl_Position = vec4(a_position, -0.5, 1.0); }
            """).draw("triangles")
            gloo.set_state(scissor_test=False)
            if backend == "pyqt6":
                from OpenGL import GL
                gloo.finish()
                x, y, width, height = spec["crop"]
                out_type = GL.GL_FLOAT if spec["out_type"] == "float" else GL.GL_UNSIGNED_BYTE
                GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
                try:
                    raw = GL.glReadPixels(x, y, width, height, GL.GL_STENCIL_INDEX, out_type)
                    image = raw if isinstance(raw, np.ndarray) else np.frombuffer(raw, np.float32 if spec["out_type"] == "float" else np.uint8)
                    image = image.reshape(height, width, 1)[::-1]
                finally:
                    GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 4)
            else:
                image = gloo.read_pixels(spec["crop"], alpha=spec["alpha"], mode="stencil", out_type=spec["out_type"])
        return image, runner.commands, runner.shaders, spec
    except Exception as error:
        error.fixture_commands = runner.commands
        error.fixture_shaders = runner.shaders
        error.fixture_parameters = spec
        raise
    finally:
        runner.close()
