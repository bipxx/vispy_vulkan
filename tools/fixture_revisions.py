"""Public gloo texture revisions with one final readback per reproduction.

These cases exercise sampler changes followed by data changes, and a partial
CPU update of a texture whose current contents were produced by an FBO draw.
One earlier warmup submit establishes resident sampler-case allocations; all
dependent draws and updates remain pending until the single final readback.
Expected pixels are analytic; the OpenGL oracle is captured before candidate
execution. The existing, finalized gloo fixture corpus is left independent.
"""

from __future__ import annotations

import numpy as np

if __package__:
    from .fixture_gloo import FULL, LEFT, RIGHT, SIZE, Runner
else:
    from fixture_gloo import FULL, LEFT, RIGHT, SIZE, Runner


CASES = ("sampler_wrapping_partial", "sampler_wrapping_full", "rendered_texture_partial")
RED = [255, 0, 0, 255]
GREEN = [0, 255, 0, 255]
BLUE = [0, 0, 255, 255]


def render(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    runner = Runner(backend)
    gloo = runner.gloo
    canvas = runner.canvas()
    parameters = {"texture_shape": [4, 4, 4], "interpolation": "nearest",
                  "final_readbacks": 1, "intermediate_finish": False,
                  "intermediate_present": False, "prewarm_presents": 0}
    try:
        if name.startswith("sampler_wrapping_"):
            texture = gloo.Texture2D(np.full((4, 4, 4), RED, np.uint8),
                                     interpolation="nearest", wrapping="clamp_to_edge")
            program = runner.textured(texture, FULL)
            # Dawn allocates resident textures when a frame is submitted.
            # Establish that allocation before the dependent reproduction:
            # an entirely fresh texture could hide sampler-allocation aliasing.
            program.draw("triangles")
            canvas.swap_buffers()
            parameters["prewarm_presents"] = 1
            runner.clear((0, 0, 0, 1))
            program["a_position"].set_data(LEFT)
            program.draw("triangles")
            # Changing only the sampler must retain the old draw's texture
            # allocation when a following DATA command replaces its contents.
            texture.wrapping = "repeat"
            if name.endswith("partial"):
                texture.set_data(np.array([[BLUE]], np.uint8), offset=(0, 0))
                parameters.update({"update": "partial", "offset": [0, 0],
                                   "update_shape": [1, 1, 4]})
            else:
                # Upstream's public full-update API emits identical SIZE plus
                # full DATA. Preserve this trace rather than bypass that API.
                texture.set_data(np.full((4, 4, 4), BLUE, np.uint8))
                parameters.update({"update": "full", "offset": [0, 0],
                                   "update_shape": [4, 4, 4]})
            program["a_position"].set_data(RIGHT)
            program.draw("triangles")
            parameters["wrapping_change"] = ["clamp_to_edge", "repeat"]
        else:
            texture = gloo.Texture2D(np.zeros((4, 4, 4), np.uint8),
                                     interpolation="nearest")
            framebuffer = gloo.FrameBuffer(color=texture)
            with framebuffer:
                gloo.set_viewport(0, 0, 4, 4)
                runner.clear((0, 0, 0, 1))
                runner.solid(color=(0, 1, 0, 1)).draw("triangles")
            gloo.set_viewport(0, 0, *SIZE)
            # The untouched pixels must come from the pending green GPU draw,
            # rather than from the zero-filled original CPU upload.
            texture.set_data(np.array([[BLUE]], np.uint8), offset=(0, 0))
            runner.textured(texture).draw("triangles")
            parameters.update({"update": "partial", "offset": [0, 0],
                               "update_shape": [1, 1, 4],
                               "previous_contents": "pending green FBO draw"})
        image = runner.read()
        return image, runner.commands, runner.shaders, parameters, runner.readbacks
    finally:
        runner.close()


def expected_image(name):
    width, height = SIZE
    expected = np.empty((height, width, 4), np.uint8)
    if name == "sampler_wrapping_full":
        expected[:, :16], expected[:, 16:] = RED, BLUE
    elif name == "sampler_wrapping_partial":
        expected[:] = RED
        expected[18:, 16:20] = BLUE
    elif name == "rendered_texture_partial":
        expected[:] = GREEN
        expected[18:, :8] = BLUE
    else:
        raise ValueError(name)
    return expected


def assert_expected(name, image):
    expected = expected_image(name)
    assert image.dtype == np.uint8 and image.shape == expected.shape
    assert np.array_equal(image, expected), (name, "exact analytic texture revision mismatch",
        np.unique(image.reshape(-1, 4), axis=0).tolist())


def assert_trace(name, commands):
    """Require the dependent draw/update ordering in the actual filtered GLIR."""
    draws = [index for index, command in enumerate(commands) if command[0] == "DRAW"]
    assert len(draws) == (3 if name.startswith("sampler_wrapping_") else 2), (name, draws)
    draws = draws[-2:]
    between = commands[draws[0] + 1:draws[1]]
    assert any(command[0] == "DATA" and isinstance(command[3], dict)
               and command[3].get("array", {}).get("shape") in ([1, 1, 4], [4, 4, 4])
               for command in between), (name, "texture update must follow old draw")
    if name.startswith("sampler_wrapping_"):
        wrapping = next(index for index, command in enumerate(between)
                        if command[0] == "WRAPPING" and command[2] == ["repeat", "repeat"])
        assert any(command[0] == "DATA" for command in between[wrapping + 1:]), name
    # Public read_pixels inserts its final glFinish. Only a finish preceding
    # the last dependent draw would invalidate this pending-work reproduction.
    assert not any(command[0] == "FUNC" and command[1] == "glFinish"
                   for command in commands[:draws[-1] + 1])
