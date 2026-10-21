"""Analytic >64MiB ordinary converted payloads, authored without a candidate.

The workload has millions of selected vertices/instances but only six or 24
visible vertices. It qualifies current-record reuse after complete retirement;
it does not qualify partitioning or arbitrary alternating oversized histories.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import numpy as np

HISTORY_BYTES = 64 * 1024 * 1024
HISTORY_ENTRIES = 128
SIZE = (48, 24)
CASES = ("selection_sparse_uint32", "vertex_affine_first3", "instance_divisor2")
SPARSE_BASE = 16777218
CORNERS = ((0, 0), (8, 0), (0, 6), (0, 6), (8, 0), (8, 6))
SAMPLE_LIMITS = {
    "max_vertex_attributes": 30, "max_vertex_buffers": 8,
    "max_vertex_buffer_array_stride": 2048, "max_buffer_size": 256 * 1024 * 1024,
    "max_storage_buffers_per_shader_stage": 8,
    "max_storage_buffer_binding_size": 128 * 1024 * 1024,
}
FRAGMENT = "#version 330\nflat in vec4 v_color; out vec4 color; void main(){color=v_color;}"


@dataclass(frozen=True)
class Plan:
    name: str
    lanes: int
    stride: int
    first: int
    count: int
    instances: int
    source_rows: int
    visible_first: int
    target_bytes: int
    geometry_upload_bytes: int
    geometry_buffers: int
    route: str
    category: str
    history_bytes: int


def _rounded_over(budget, width, multiple):
    return (budget // (width * multiple) + 1) * multiple


def plan(name, limits, *, budget=HISTORY_BYTES):
    """Fail before any allocation when this single-stream workload is illegal."""
    if name not in CASES or type(budget) is not int or budget <= 0:
        raise ValueError((name, budget))
    lanes = int(limits["max_vertex_buffers"]) + 1
    stride = 4 * lanes
    if lanes < 2 or lanes > int(limits["max_vertex_attributes"]):
        raise ValueError("workload needs one more active scalar input than physical buffers")
    if stride > int(limits["max_vertex_buffer_array_stride"]):
        raise ValueError("combined stride exceeds grant; partitioning is outside this fixture")
    if int(limits["max_vertex_buffers"]) < 1 or int(limits["max_storage_buffers_per_shader_stage"]) < 1:
        raise ValueError("workload needs a vertex stream and exact-ID storage binding")
    if name == CASES[0]:
        count = _rounded_over(budget, 4, 6)
        # Sparse original IDs have no dense attribute allocation. Seven unique
        # IDs (one degenerate sentinel plus six final corners) are retained.
        result = Plan(name, lanes, stride, 0, count, 1, 1, SPARSE_BASE,
                      count * 4, count * 4 + 7 * (4 + stride), 3,
                      "Indexed", "Selection", budget)
        allocation_sizes = (count * 4, 7 * stride, 7 * 4)
        storage_size = 7 * 4
    elif name == CASES[1]:
        count = _rounded_over(budget, stride, 6)
        result = Plan(name, lanes, stride, 3, count, 1, count + 3, count - 3,
                      count * stride, count * stride + 4, 2,
                      "Affine", "Vertex", budget)
        allocation_sizes = (count * stride, (count + 3) * 4, 4)
        storage_size = 4
    else:
        instances = _rounded_over(budget, stride, 4)
        result = Plan(name, lanes, stride, 0, 6, instances, instances // 2, 0,
                      instances * stride, instances * stride + 4, 2,
                      "Affine", "Instance", budget)
        allocation_sizes = (instances * stride, (instances // 2) * 4, 4)
        storage_size = 4
    if max(result.count, result.instances, result.first + result.count) > 2 ** 31 - 1:
        raise ValueError("workload exceeds the native signed draw-count grant")
    if max(allocation_sizes) > int(limits["max_buffer_size"]):
        raise ValueError("combined payload exceeds allocation grant; batching is outside this fixture")
    if storage_size > int(limits["max_storage_buffer_binding_size"]):
        raise ValueError("exact-ID table exceeds granted storage binding size")
    assert result.target_bytes > budget
    return result


def tail_indices(p, *, revised=False):
    if p.name != CASES[0]:
        raise ValueError(p.name)
    offsets = (3, 5, 4, 0, 2, 1) if revised else (3, 4, 5, 0, 1, 2)
    return np.asarray([p.visible_first + value for value in offsets], np.uint32)


def vertex_source(p):
    declarations = "\n".join(f"in float a_lane{n};" for n in range(p.lanes))
    energy = "+".join(f"a_lane{n}" for n in range(p.lanes))
    instance = p.name == CASES[2]
    visible = (f"gl_InstanceID >= {p.instances - 4}" if instance else
               f"gl_VertexID >= {p.visible_first} && gl_VertexID < {p.visible_first + 6}")
    corner = "gl_VertexID" if instance else f"gl_VertexID - {p.visible_first}"
    expected = f"{p.lanes - 1}. + float((gl_InstanceID/2)%2)" if instance else f"{p.lanes}."
    cell = f"gl_InstanceID - {p.instances - 4}" if instance else "0"
    blue = "(gl_InstanceID%2)==1" if instance else "gl_VertexID >= 16777217"
    return f"""#version 330
{declarations}
in float a_count;
flat out vec4 v_color;
void main() {{
    float energy = {energy};
    float expected = {expected};
    v_color = vec4((gl_VertexID%2)==1 ? 1. : 0., abs(energy-expected)<.25 ? 1. : 0., {blue} ? 1. : 0., 1.);
    gl_Position = vec4(2.,2.,0.,1.);
    if ({visible}) {{
        int vertex = {corner};
        vec2 corner = vec2(0.);
        if (vertex == 1 || vertex == 4) corner = vec2(8.,0.);
        else if (vertex == 2 || vertex == 3) corner = vec2(0.,6.);
        else if (vertex == 5) corner = vec2(8.,6.);
        vec2 pixel = vec2(4.+10.*float({cell}),4.)+corner;
        gl_Position = vec4(pixel/vec2({SIZE[0]},{SIZE[1]})*2.-1.,0.,1.);
    }}
}}
"""


def expected_image(p, *, revised=False):
    """Pixel centers never tie on the 8:6 diagonal; full array is exact."""
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    for cell in range(4 if p.name == CASES[2] else 1):
        instance = p.instances - 4 + cell if p.name == CASES[2] else 0
        for dy in range(6):
            for dx in range(8):
                # lower-left triangle has source corner2 as its last vertex,
                # upper-right has corner5. Revision reverses each triangle's
                # last two index entries, preserving coverage but flipping red.
                corner = 2 if 3 * dx + 4 * dy <= 20 else 5
                if revised and p.name == CASES[0]:
                    corner = 1 if corner == 2 else 4
                vertex = p.visible_first + corner
                green = 0 if revised and p.name in CASES[1:] else 255
                blue = instance % 2 if p.name == CASES[2] else int(vertex >= 16777217)
                image[SIZE[1] - 1 - (4 + dy), 4 + 10 * cell + dx] = (
                    255 * (vertex % 2), green, 255 * blue, 255)
    return image


def make_program(gloo, p):
    program = gloo.Program(vertex_source(p), FRAGMENT)
    # Public Program.draw requires a non-instance DataBuffer to infer count.
    # a_count is unused and must be removed from the native active interface;
    # it never legitimizes an out-of-range active sparse fetch.
    count = p.source_rows if p.name == CASES[1] else 6 if p.name == CASES[2] else 1
    count_buffer = gloo.VertexBuffer(np.zeros(count, np.float32))
    program["a_count"] = count_buffer
    buffers = [count_buffer]
    for lane in range(p.lanes):
        if p.name == CASES[2]:
            values = np.ones(p.source_rows, np.float32)
            if lane == 0:
                values[::2], values[1::2] = 0., 1.
            buffer = gloo.VertexBuffer(values, divisor=2)
            program[f"a_lane{lane}"] = buffer
            buffers.append(buffer)
        else:
            program[f"a_lane{lane}"] = 1.
    indices = None
    if p.name == CASES[0]:
        values = np.full(p.count, p.visible_first + 18, np.uint32)
        values[-6:] = tail_indices(p)
        indices = gloo.IndexBuffer(values)
        buffers.append(indices)
    return program, buffers, indices


def configure(gloo):
    gloo.set_viewport(0, 0, *SIZE)
    gloo.set_state(blend=False, depth_test=False, stencil_test=False,
                   scissor_test=False, cull_face=False)
    gloo.set_clear_color((0., 0., 0., 1.))
    gloo.clear(color=True, depth=False, stencil=False)


def draw(canvas, gloo, program, indices, p):
    configure(gloo)
    if p.name == CASES[1]:
        # Program.draw has no public first/count argument. This case preserves
        # the renderer's actual GLIR queue boundary, without changing Python.
        canvas.context.glir.associate(program.glir)
        canvas.context.glir.command("DRAW", program.id, "triangles", (p.first, p.count), p.instances)
        canvas.context.flush_commands()
    else:
        program.draw("triangles", indices)


def revise(program, buffers, indices, p):
    if p.name == CASES[0]:
        indices.set_subdata(tail_indices(p, revised=True), offset=p.count - 6)
    elif p.name == CASES[1]:
        program["a_lane0"] = 0.
    else:
        # Final four instances consume exactly the last two divisor2 rows.
        rows = np.asarray([1 - (row % 2) for row in range(p.source_rows - 2, p.source_rows)], np.float32)
        buffers[1].set_subdata(rows, offset=p.source_rows - 2)


def array_record(value):
    return {"shape": list(value.shape), "dtype": value.dtype.str,
            "sha256": hashlib.sha256(value.tobytes()).hexdigest()}


def contract():
    plans = {name: plan(name, SAMPLE_LIMITS) for name in CASES}
    return {
        "schema": 1, "GPU_used": False, "candidate_seen": False,
        "history_bytes": HISTORY_BYTES, "history_entries": HISTORY_ENTRIES,
        "current_categories_per_program": 6, "size": list(SIZE),
        "plan_algorithm": "lanes=maxVertexBuffers+1; converted target alone strictly exceeds64MiB; check each allocation/stride/storage/draw-count grant before construction",
        "sample_grants_are_authoring_only": SAMPLE_LIMITS,
        "plans": {name: asdict(value) for name, value in plans.items()},
        "expected": {name: {"cold": array_record(expected_image(value)),
                            "revised": array_record(expected_image(value, revised=True))}
                     for name, value in plans.items()},
        "comparisons": "exact complete analytic RGBA arrays; no tolerance, edge mask or candidate-derived fitting",
        "identity_scope": "native original uint32 IDs / first3 / original instance IDs and divisor2; current child identity is inferred by zero downstream conversions, not exposed as a token",
        "retirement": "all pending draws, queued batches and actual Tickets zero via nonblocking polling before every warm baseline",
        "resident_scope": "submit and actual retirement counter deltas frozen before separate quality readback; zero conversion/upload/allocation/finish/completion-wait deltas; shaders have no uniforms or textures",
        "loss_scope": "same live Program, one upload per retained geometry child, zero CPU conversions; next retired warm draw zero uploads/allocations",
        "release_scope": "index/source DELETE where present, then Program DELETE; current/cache views and deduplicated CPU/GPU gauges recorded separately",
        "open_gates": ["combined stride/storage partitioning and ordered batching", "arbitrary alternating oversized-history reuse", "physical allocator/RSS measurement", "non-Vulkan independent hardware matrix"],
    }
