"""Fixed public point identity/instancing inputs authored before candidate runs.

All draws and dependent updates precede one final readback. Seven workflows
use unchanged Program.draw; nonzero_first is explicitly a GLIR queue contract.
The large identity case has constant active geometry and verifies upstream's
unused count input is inactive, so no large or out-of-range vertex fetch occurs.
"""

from __future__ import annotations

import hashlib
import numpy as np

if __package__:
    from .fixture_gloo import Runner, SIZE
else:
    from fixture_gloo import Runner, SIZE

CASES = ("indexed_uint8", "indexed_uint16", "indexed_uint32",
         "instanced_divisor1", "instanced_divisor2", "ordered_revisions",
         "nonzero_first_queue", "large_uint32_constant_geometry")
PALETTE = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
LARGE_ID = 2 ** 24 + 1
DTYPE = np.dtype([("padding", "<f4"), ("a_base", "<f4", (2,)),
                  ("padding2", "<f4"), ("a_tint", "<f4", (3,))])
VERTEX = """#version 330
in vec2 a_base;
in vec3 a_tint;
in float a_size;
in vec2 a_offset;
uniform vec2 u_viewport;
uniform bool u_instanced;
uniform int u_divisor;
flat out vec3 v_color;
void main() {
    vec2 p = a_base + a_offset;
    if (u_instanced) {
        p += vec2(2 * gl_InstanceID, 2 * gl_VertexID);
        if (u_divisor == 2) p.y += float(4 * (gl_InstanceID % 2));
        v_color = gl_InstanceID % 2 == 0 ? a_tint : a_tint.bgr;
    } else {
        p.y += gl_VertexID % 2 == 1 ? 4.0 : 0.0;
        int color = gl_VertexID % 4;
        v_color = (color == 0 ? vec3(1, 0, 0) :
                   color == 1 ? vec3(0, 1, 0) :
                   color == 2 ? vec3(0, 0, 1) : vec3(1, 1, 0)) * a_tint;
    }
    gl_Position = vec4(p / u_viewport * 2.0 - 1.0, 0, 1);
    gl_PointSize = a_size;
}
"""
FRAGMENT = """#version 330
flat in vec3 v_color;
uniform float u_alpha;
out vec4 frag_color;
void main() { frag_color = vec4(v_color, u_alpha); }
"""


def vertex_data():
    data = np.zeros(8, DTYPE)
    data["padding"], data["padding2"] = 91, -73
    data["a_base"] = [[2.5, 4.5], [8.5, 4.5], [12.5, 4.5], [4.5, 4.5],
                      [16.5, 4.5], [28.5, 4.5], [24.5, 4.5], [30.5, 4.5]]
    data["a_tint"] = 1
    return data


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    spec = {"case": name, "size": list(SIZE), "point_size": 3., "alpha": .25,
            "primitive": "points", "readbacks": 1, "intermediate_finish": False,
            "intermediate_present": False, "api_scope": "public gloo.Program.draw",
            "comparison": "entire frame equals fixed analytic pixels and independent OpenGL exactly",
            "data": vertex_data(), "indices": None, "divisor": 0,
            "first": 0, "count": None, "offsets": None}
    if name.startswith("indexed_uint"):
        spec["indices"] = np.array([6, 1, 4, 1], getattr(np, name.removeprefix("indexed_")))
    elif name.startswith("instanced_divisor"):
        spec["data"] = vertex_data()[:2].copy()
        spec["data"]["a_base"] = [[6.5, 4.5], [16.5, 4.5]]
        spec["data"]["a_tint"] = [[1, 0, 0], [0, 0, 1]]
        spec["divisor"] = int(name[-1])
        spec["offsets"] = np.array([[0, 4 * i] for i in range(4)], np.float32) if spec["divisor"] == 1 else np.array([[0, 0], [0, 8]], np.float32)
        spec["alpha"] = 1.
    elif name == "ordered_revisions":
        spec["indices"] = np.array([6, 1, 4], np.uint16)
        spec["updated_data"] = spec["data"].copy()
        spec["updated_data"]["a_base"][:, 1] += 12
        spec["updated_indices"] = np.array([4, 6, 4], np.uint16)
        spec["updated_point_size"] = 1.
    elif name == "nonzero_first_queue":
        spec.update(first=3, count=3,
                    api_scope="explicit GLIR queue boundary; not public Program.draw first admission",
                    discarded_setup_draw=True)
    else:
        spec["data"] = None
        spec["indices"] = np.array([LARGE_ID], np.uint32)
        spec["constant_base"] = [16.5, 8.5]
        spec["inactive_count_input_required"] = True
    return spec


def point_operations(name):
    """Integer pixel centers, sizes and source colors from frozen inputs only."""
    spec = specification(name)
    if spec["divisor"]:
        return [(6 + 2 * instance + 10 * vertex, 4 + 4 * instance + 2 * vertex,
                 3, PALETTE[0 if (vertex + instance) % 2 == 0 else 2], 1.)
                for instance in range(4) for vertex in range(2)]
    if name == "large_uint32_constant_geometry":
        return [(16, 12, 3, PALETTE[LARGE_ID % 4], .25)]
    indices = range(spec["first"], spec["first"] + spec["count"]) if spec["first"] else spec["indices"]
    operations = []
    for index in indices:
        x, y = spec["data"]["a_base"][index]
        operations.append((int(x), int(y) + 4 * (int(index) % 2), 3, PALETTE[int(index) % 4], .25))
    if name == "ordered_revisions":
        for index in spec["updated_indices"]:
            x, y = spec["updated_data"]["a_base"][index]
            operations.append((int(x), int(y) + 4 * (int(index) % 2), 1, PALETTE[int(index) % 4], .25))
    return operations


def expected_image(name):
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    for x, y, size, color, alpha in point_operations(name):
        radius = size // 2
        region = image[SIZE[1] - 1 - y - radius:SIZE[1] - y + radius,
                       x - radius:x + radius + 1, :3]
        assert region.shape == (size, size, 3)
        region[:] = np.floor(region.astype(np.float64) * (1 - alpha) + np.array(color) * alpha + .5).astype(np.uint8)
    return image


def assert_expected(name, image):
    expected = expected_image(name)
    assert image.dtype == np.uint8 and image.shape == expected.shape
    difference = np.abs(image.astype(np.int16) - expected.astype(np.int16))
    assert np.array_equal(image, expected), (name, "fixed analytic point pixels", int(difference.max()),
                                            int(np.any(difference, axis=2).sum()))


def parameters(name):
    spec = specification(name)
    result = {key: value for key, value in spec.items() if not isinstance(value, np.ndarray)}
    for key, value in spec.items():
        if isinstance(value, np.ndarray):
            result[key] = {"values": value.tolist(), "dtype": value.dtype.descr if value.dtype.fields else value.dtype.str,
                           "shape": list(value.shape), "sha256": hashlib.sha256(value.tobytes()).hexdigest()}
    vertex = VERTEX.replace("in vec2 a_base;", "in vec2 a_base;\nin float a_count;") if spec["data"] is None else VERTEX
    result.update(operations=point_operations(name), vertex_shader_sha256=hashlib.sha256(vertex.encode()).hexdigest(),
                  fragment_shader_sha256=hashlib.sha256(FRAGMENT.encode()).hexdigest(),
                  analytic_rgba_sha256=hashlib.sha256(expected_image(name).tobytes()).hexdigest())
    # JSON normalization preserves exact equality between live and saved params.
    import json
    return json.loads(json.dumps(result, default=lambda value: value.tolist() if isinstance(value, np.ndarray) else value.item()))


def assert_trace(name, commands):
    draws = [i for i, command in enumerate(commands) if command[0] == "DRAW"]
    finishes = [i for i, command in enumerate(commands) if command[:2] == ["FUNC", "glFinish"]]
    assert len(draws) == (2 if name in ("ordered_revisions", "nonzero_first_queue") else 1)
    assert len(finishes) == 1 and finishes[0] > max(draws)
    assert all(commands[i][2] == "points" for i in draws)
    spec = specification(name)
    assert commands[draws[-1]][4] == (4 if spec["divisor"] else 1)
    if spec["divisor"]:
        assert any(command[0] == "ATTRIBUTE" and command[2] == "a_offset" and command[-1] == spec["divisor"] for command in commands)
    if name == "ordered_revisions":
        window = commands[draws[0] + 1:draws[1]]
        assert sum(command[0] == "DATA" for command in window) >= 2
        assert any(command[0] == "ATTRIBUTE" and command[2] == "a_size" and command[4] == [0, 1.] for command in window)
    if name == "nonzero_first_queue":
        assert commands[draws[-1]][3] == [3, 3]


def render(name, backend="dawn_headless"):
    spec = specification(name)
    runner = Runner(backend, samples=0)
    canvas = runner.canvas()
    gloo = runner.gloo
    try:
        observations = {"sample_source": "OpenGL driver" if backend == "pyqt6" else "Dawn facade configuration",
                        "samples_raw": int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))}
        observations["physical_samples"] = max(1, observations["samples_raw"])
        assert observations["physical_samples"] == 1
        if backend == "pyqt6":
            from OpenGL import GL
            observations.update(gl_version=GL.glGetString(GL.GL_VERSION).decode(),
                                point_smooth=bool(GL.glIsEnabled(GL.GL_POINT_SMOOTH)),
                                program_point_size=bool(GL.glIsEnabled(GL.GL_PROGRAM_POINT_SIZE)))
            assert observations["gl_version"].startswith("4.6")
            assert not observations["point_smooth"]
        gloo.set_state(blend=True)
        gloo.set_blend_func("src_alpha", "one_minus_src_alpha", "one", "one_minus_src_alpha")
        vertex = VERTEX.replace("in vec2 a_base;", "in vec2 a_base;\nin float a_count;") if spec["data"] is None else VERTEX
        program = gloo.Program(vertex, FRAGMENT)
        program["u_viewport"], program["u_instanced"] = SIZE, bool(spec["divisor"])
        program["u_divisor"], program["u_alpha"] = spec["divisor"], spec["alpha"]
        program["a_size"] = spec["point_size"]
        if spec["data"] is None:
            program["a_base"], program["a_tint"] = tuple(spec["constant_base"]), (1., 1., 1.)
            program["a_count"] = gloo.VertexBuffer(np.array([0.], np.float32))
        else:
            vertices = gloo.VertexBuffer(spec["data"])
            program["a_base"], program["a_tint"] = vertices["a_base"], vertices["a_tint"]
        program["a_offset"] = gloo.VertexBuffer(spec["offsets"], divisor=spec["divisor"]) if spec["divisor"] else (0., 0.)
        indices = gloo.IndexBuffer(spec["indices"]) if spec["indices"] is not None else None
        program.draw("points", indices)
        if name == "ordered_revisions":
            vertices.set_subdata(spec["updated_data"], offset=0)
            indices.set_subdata(spec["updated_indices"], offset=0)
            program["a_size"] = spec["updated_point_size"]
            program.draw("points", indices)
        elif name == "nonzero_first_queue":
            runner.clear((0, 0, 0, 1))
            canvas.context.glir.command("DRAW", program.id, "points", (spec["first"], spec["count"]), 1)
            canvas.context.flush_commands()
        if backend == "pyqt6":
            from OpenGL import GL
            observations["program_point_size_after_draw"] = bool(GL.glIsEnabled(GL.GL_PROGRAM_POINT_SIZE))
            assert observations["program_point_size_after_draw"]
        if spec.get("inactive_count_input_required") and backend == "pyqt6":
            from OpenGL import GL
            active_program = int(GL.glGetIntegerv(GL.GL_CURRENT_PROGRAM))
            observations["count_attribute_location"] = int(GL.glGetAttribLocation(active_program, "a_count"))
            assert active_program > 0 and observations["count_attribute_location"] == -1
            observations["count_input_query"] = "canonical GL_CURRENT_PROGRAM/glGetAttribLocation; inactive input has no enabled vertex fetch"
        image = runner.read()
        assert runner.readbacks == 1
        if backend == "dawn_headless":
            from vispy import _dawn
            observations.update(device_info=_dawn.device_info(), native_probe=_dawn.probe())
        return image, runner.commands, runner.shaders, parameters(name), observations
    except Exception as error:
        error.fixture_commands, error.fixture_shaders = runner.commands, runner.shaders
        raise
    finally:
        runner.close()
