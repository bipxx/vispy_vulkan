"""Public packed depth/stencil readback; pinned wrapper failures stay visible."""

from __future__ import annotations

import numpy as np

if __package__:
    from .fixture_gloo import Runner
else:
    from fixture_gloo import Runner

SIZE = (8, 6)
PACKED_DEPTH_STENCIL = 0x88F0  # GL_DEPTH24_STENCIL8, RenderBuffer's public integer format.
STENCIL_INDEX = 0x1901        # ReadPixels' actual stencil format; distinct from storage's INDEX8.
CASES = ("depth_float", "depth_u8", "depth_crop_float", "depth_noalpha_float",
         "stencil_float", "stencil_u8", "stencil_crop_float", "stencil_noalpha_u8",
         "stencil_gl_float", "stencil_gl_u8", "stencil_gl_crop_float", "stencil_gl_noalpha_u8")


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    return {"mode": "depth" if name.startswith("depth") else "stencil",
            "out_type": "unsigned_byte" if name.endswith("u8") else "float",
            "alpha": "noalpha" not in name,
            "crop": [2, 1, 4, 3] if "crop" in name else [0, 0, *SIZE],
            "attachment_size": list(SIZE), "logical_depth_bits": 24, "stencil_bits": 8,
            "renderbuffer_internalformat": PACKED_DEPTH_STENCIL, "physical_samples": 1,
            "readbacks": 1, "explicit_gloo_finish_calls": 1 if "_gl_" in name else 0,
            "capture_api": "gloo.gl.glReadPixels(GL_STENCIL_INDEX)" if "_gl_" in name else "gloo.read_pixels",
            "regions": [{"viewport": [1, 1, 3, 2], "depth": .25, "stencil": 37, "operation": "draw"},
                        {"viewport": [4, 3, 3, 2], "depth": .75, "stencil": 203, "operation": "scissor clear"}],
            "background": {"depth": 1, "stencil": 3},
            "orientation": "top-left array, bottom-left viewport crop"}


def expected_image(name):
    spec = specification(name)
    depth = spec["mode"] == "depth"
    image = np.full((SIZE[1], SIZE[0], 1), 1 if depth else 3, np.float32)
    image[3:5, 1:4] = np.float32(4194304 / 16777215) if depth else 37
    image[1:3, 4:7] = np.float32(12582911 / 16777215) if depth else 203
    x, y, width, height = spec["crop"]
    image = image[SIZE[1] - y - height:SIZE[1] - y, x:x + width]
    if spec["out_type"] == "unsigned_byte":
        image = np.floor(image.astype(np.float64) * 255 + .5).astype(np.uint8) if depth else image.astype(np.uint8)
    return np.ascontiguousarray(image)


def assert_expected(name, image):
    expected = expected_image(name)
    assert image.shape == expected.shape and image.dtype == expected.dtype
    assert np.array_equal(image, expected), (name, "exact depth/stencil values", image.tolist(), expected.tolist())


def render(name, backend="dawn_headless"):
    spec = specification(name)
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
            program = runner.solid(color=(0, 1, 0, 1), vert="""
                attribute vec2 a_position;
                void main() { gl_Position = vec4(a_position, -0.5, 1.0); }
            """)
            program.draw("triangles")
            gloo.set_state(scissor_test=False)
            if "_gl_" in name:
                # This public lower-level GL boundary is reported explicitly.
                # The pinned read_pixels wrapper uses the storage enum INDEX8,
                # whose upstream failure is captured in separate cases.
                gloo.finish()
                x, y, width, height = spec["crop"]
                out_type = gloo.gl.GL_FLOAT if spec["out_type"] == "float" else gloo.gl.GL_UNSIGNED_BYTE
                gloo.gl.glPixelStorei(gloo.gl.GL_PACK_ALIGNMENT, 1)
                try:
                    raw = gloo.gl.glReadPixels(x, y, width, height, STENCIL_INDEX, out_type)
                    image = raw if isinstance(raw, np.ndarray) else np.frombuffer(raw, np.float32 if spec["out_type"] == "float" else np.uint8)
                    image = image.reshape(height, width, 1)[::-1]
                finally:
                    gloo.gl.glPixelStorei(gloo.gl.GL_PACK_ALIGNMENT, 4)
            else:
                image = gloo.read_pixels(spec["crop"], alpha=spec["alpha"], mode=spec["mode"], out_type=spec["out_type"])
        return image, runner.commands, runner.shaders, spec
    except Exception as error:
        error.fixture_commands = runner.commands
        error.fixture_shaders = runner.shaders
        error.fixture_parameters = spec
        raise
    finally:
        runner.close()
