"""Analytic full-user-input point fixtures, independent of candidate pixels."""
from __future__ import annotations

import numpy as np

SIZE = (48, 32)
LARGE_ID = 2 ** 24 + 1
CASES = ("uint8", "uint16_divisor1", "uint32_divisor2", "nonzero_first", "sparse_constants")
FRAGMENT = "#version 330\nflat in vec4 v_color; out vec4 frag_color; void main(){frag_color=v_color;}"


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    divisor = 1 if name == "uint16_divisor1" else 2 if name in ("uint32_divisor2", "nonzero_first") else 0
    ids = [3, 4, 5] if name == "nonzero_first" else [LARGE_ID] if name == "sparse_constants" else [6, 1, 4, 1]
    dtype = "uint8" if name == "uint8" else "uint16" if name == "uint16_divisor1" else "uint32"
    return {"name": name, "ids": ids, "index_dtype": dtype, "divisor": divisor,
            "instances": 2 * divisor if divisor else 1, "first": 3 if name == "nonzero_first" else None,
            "api_scope": "explicit GLIR first/count" if name == "nonzero_first" else "public Program.draw"}


def vertex_source(active_count, *, sparse=False):
    if active_count < 2:
        raise ValueError("Fixture requires a position and at least one scalar lane")
    declarations = "\n".join(f"in float a_lane{n};" for n in range(active_count - 1))
    energy = " + ".join(f"a_lane{n}" for n in range(active_count - 1))
    inactive = "in float a_count;" if sparse else ""
    return f"""#version 330
in vec2 a_position;
{declarations}
{inactive}
flat out vec4 v_color;
void main() {{
    vec2 pixel = a_position + vec2(3 * (gl_VertexID % 8), 6 * gl_InstanceID);
    gl_Position = vec4(pixel / vec2(48, 32) * 2.0 - 1.0, 0, 1);
    gl_PointSize = 1.0;
    float energy = {energy};
    v_color = vec4(energy > 0.0 ? 1.0 : 0.25,
                   gl_VertexID % 2 == 0 ? 1.0 : 0.0,
                   gl_InstanceID % 2 == 0 ? 1.0 : 0.0, 1.0);
}}
"""


def expected_image(name, *, energized=False, position_shift=0):
    spec = specification(name)
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    for instance in range(spec["instances"]):
        for source_id in spec["ids"]:
            column = 2 + 3 * (source_id % 8) + position_shift
            row = SIZE[1] - 1 - (4 + 6 * instance)
            image[row, column] = (255 if energized else 64,
                                  255 if source_id % 2 == 0 else 0,
                                  255 if instance % 2 == 0 else 0, 255)
    return image


def make_program(gloo, name, active_count):
    spec = specification(name)
    sparse = name == "sparse_constants"
    program = gloo.Program(vertex_source(active_count, sparse=sparse), FRAGMENT)
    bindings = {}
    if sparse:
        program["a_position"] = (2.5, 4.5)
        # This inactive input supplies the public Program.draw vertex count,
        # without a fetched row at the sparse large index.
        program["a_count"] = gloo.VertexBuffer(np.zeros(1, np.float32))
    else:
        positions = np.tile(np.array([2.5, 4.5], np.float32), (8, 1))
        program["a_position"] = gloo.VertexBuffer(positions)
    interleaved = gloo.VertexBuffer(np.zeros(8, dtype=[("padding", "f4"), ("lane", "f4"), ("tail", "f4")]))
    for lane in range(active_count - 1):
        key = f"a_lane{lane}"
        if sparse or lane == 2:
            binding = 0.0
        elif lane == 0 and spec["divisor"]:
            binding = gloo.VertexBuffer(np.zeros(2, np.float32), divisor=spec["divisor"])
        elif lane == 1:
            binding = interleaved["lane"]
        else:
            binding = gloo.VertexBuffer(np.zeros(8, np.float32))
        program[key] = binding
        bindings[key] = binding
    indices = None if spec["first"] is not None else gloo.IndexBuffer(np.asarray(spec["ids"], dtype=spec["index_dtype"]))
    return program, bindings, indices


def draw(canvas, gloo, program, indices, name):
    spec = specification(name)
    gloo.set_viewport(0, 0, *SIZE)
    gloo.set_clear_color((0, 0, 0, 1))
    gloo.clear()
    gloo.set_state(blend=False, depth_test=False)
    if spec["first"] is None:
        program.draw("points", indices)
    else:
        canvas.context.glir.associate(program.glir)
        canvas.context.glir.command("DRAW", program.id, "points", (spec["first"], len(spec["ids"])), spec["instances"])
        canvas.context.flush_commands()
    return gloo.read_pixels(alpha=True)


def update_lane(program, bindings, lane, value):
    key = f"a_lane{lane}"
    binding = bindings[key]
    if isinstance(binding, float):
        program[key] = float(value)
    elif getattr(binding, "base", None) is not None:
        # Public buffer views are immutable. Update the owning structured
        # buffer while preserving the view's offset/stride and padding.
        data = np.zeros(binding.base.size, binding.base.dtype)
        data["lane"] = value
        binding.base.set_subdata(data, offset=0)
    else:
        binding.set_data(np.full(binding.size, value, np.float32))
