"""Ordered triangle fans and closed line loops against independent OpenGL."""

from __future__ import annotations

import numpy as np

if __package__:
    from .fixture_gloo import Runner, SIZE
else:
    from fixture_gloo import Runner, SIZE


CASES = ("fan_winding", "fan_nonzero_first", "fan_indexed_uint8",
         "fan_indexed_uint16", "fan_indexed_uint32", "line_loop_closure")
GREEN = [0, 255, 0, 255]
BLACK = [0, 0, 0, 255]
QUAD = np.array([[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]], np.float32)


def render(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    runner = Runner(backend)
    canvas = runner.canvas()
    gloo = runner.gloo
    params = {"final_readbacks": 1, "intermediate_present": False,
              "intermediate_finish": False, "mode": "triangle_fan"}
    try:
        if name == "fan_winding":
            gloo.set_state(cull_face=True)
            gloo.set_cull_face("back")
            gloo.set_front_face("ccw")
            left = np.array([[-.875, -.75], [-.125, -.75],
                             [-.125, .75], [-.875, .75]], np.float32)
            right = left + np.array([1, 0], np.float32)
            right = right[[0, 3, 2, 1]]
            runner.solid(left, color=(0, 1, 0, 1)).draw("triangle_fan")
            runner.solid(right, color=(1, 0, 0, 1)).draw("triangle_fan")
            params.update(front_face="ccw", cull_face="back",
                          left_ccw=left.tolist(), right_cw=right.tolist())
        elif name == "fan_nonzero_first":
            vertices = np.concatenate((np.array([[0, 0], [0, 0]], np.float32), QUAD))
            program = runner.solid(vertices, color=(0, 1, 0, 1))
            # Pinned Program.draw has no first/count argument. Initialize its
            # public program/bindings, discard that setup draw with an ordered
            # clear, then exercise the unchanged GLIR selection boundary.
            program.draw("triangle_fan")
            runner.clear((0, 0, 0, 1))
            canvas.context.glir.command("DRAW", program.id, "triangle_fan", (2, 4), 1)
            canvas.context.flush_commands()
            params.update(vertices=vertices.tolist(), first=2, count=4,
                          selection_api="context.glir.command; public Program.draw always emits first=0",
                          setup_draw_discarded_by_ordered_clear=True)
        elif name.startswith("fan_indexed_"):
            dtype = getattr(np, name.removeprefix("fan_indexed_"))
            # Nonidentity indices exclude the offscreen sentinel and preserve
            # a CCW fan through all supported source index element widths.
            vertices = np.array([[-.5, .5], [-.5, -.5], [9, 9],
                                 [.5, .5], [.5, -.5]], np.float32)
            indices = np.array([1, 4, 3, 0], dtype)
            gloo.set_state(cull_face=True)
            gloo.set_cull_face("back")
            gloo.set_front_face("ccw")
            runner.solid(vertices, color=(0, 1, 0, 1)).draw(
                "triangle_fan", gloo.IndexBuffer(indices))
            params.update(vertices=vertices.tolist(), indices=indices.tolist(),
                          index_dtype=indices.dtype.str, count=4,
                          front_face="ccw", cull_face="back")
        else:
            # Pixel centers avoid a half-pixel choice for the aliased 1px line.
            pixels = np.array([[8.5, 6.5], [24.5, 6.5],
                               [24.5, 18.5], [8.5, 18.5]], np.float32)
            vertices = pixels / np.array(SIZE, np.float32) * 2 - 1
            gloo.set_line_width(1)
            runner.solid(vertices, color=(0, 1, 0, 1)).draw("line_loop")
            params.update(mode="line_loop", vertices=vertices.tolist(),
                          pixel_centers_bottom_left=pixels.tolist(), width=1,
                          closure_segment=[3, 0])
        image = runner.read()
        return image, runner.commands, runner.shaders, params, runner.readbacks
    finally:
        runner.close()


def expected_image(name):
    width, height = SIZE
    image = np.full((height, width, 4), BLACK, np.uint8)
    if name == "fan_winding":
        image[3:21, 2:14] = GREEN
    elif name == "fan_nonzero_first" or name.startswith("fan_indexed_"):
        image[6:18, 8:24] = GREEN
    elif name == "line_loop_closure":
        image[5, 8:25] = GREEN
        image[17, 8:25] = GREEN
        image[5:18, 8] = GREEN
        image[5:18, 24] = GREEN
    else:
        raise ValueError(name)
    return image


def assert_landmarks(name, image):
    assert image[2, 2].tolist() == BLACK
    if name == "fan_winding":
        assert image[12, 8].tolist() == GREEN
        assert image[12, 24].tolist() == BLACK
    elif name == "line_loop_closure":
        for row, col in ((11, 8), (11, 24), (5, 16), (17, 16)):
            assert image[row, col].tolist() == GREEN, (row, col, image[row, col])
        assert image[11, 16].tolist() == BLACK
    else:
        assert image[12, 16].tolist() == GREEN
        assert image[4, 16].tolist() == BLACK


def assert_expected(name, image):
    expected = expected_image(name)
    assert image.shape == expected.shape and image.dtype == np.uint8
    assert_landmarks(name, image)
    different = np.any(image != expected, axis=2)
    assert not np.any(different), (name, "exact analytic topology mismatch", int(different.sum()))


def assert_trace(name, commands):
    draws = [command for command in commands if command[0] == "DRAW"]
    expected_count = 2 if name in ("fan_winding", "fan_nonzero_first") else 1
    assert len(draws) == expected_count
    assert all(command[2] == ("line_loop" if name == "line_loop_closure" else "triangle_fan")
               for command in draws)
    if name == "fan_nonzero_first":
        assert draws[-1][3] == [2, 4]
    if name.startswith("fan_indexed_"):
        assert draws[0][3][1] == {"uint8": "UNSIGNED_BYTE", "uint16": "UNSIGNED_SHORT",
                                 "uint32": "UNSIGNED_INT"}[name.removeprefix("fan_indexed_")]
        assert draws[0][3][2] == 4
    last_draw = max(index for index, command in enumerate(commands) if command[0] == "DRAW")
    assert not any(command[0] == "FUNC" and command[1] == "glFinish"
                   for command in commands[:last_draw + 1])
