"""Frozen-design analytic ordinary inputs; no candidate-derived raster criteria.

Thirty active inputs exceed the pinned OpenGL driver's sixteen-input grant.
Full-capacity admission therefore uses analytic rectangles and identities;
any later upstream raster proof must label its smaller queried input count.
"""
from __future__ import annotations
import hashlib
import numpy as np

SIZE = (96, 256)
ACTIVE_COUNT = 30
CELL_COLUMNS = 8
INSTANCE_STEP = 24
PHASE_STEP = 128
SPARSE_BASE = ((2 ** 24) // 6 + 1) * 6
CASES = ("native_interleaved", "affine_nonzero_first", "indexed_uint8",
         "indexed_uint16_divisor1", "indexed_uint32_divisor2", "sparse_uint32_constants")
TOPOLOGIES = ("triangles", "triangle_strip", "triangle_fan", "lines", "line_strip", "line_loop")
OPEN_GATES = (
    "combined compact stride above the actual granted stride needs field partitioning",
    "combined payload above actual buffer/storage grants needs ordered batching",
    "unchanged records above 64MiB skip cache admission; universal warm reuse is unqualified",
    "128-record cache eviction and allocator bucket/header scope require separate pressure workloads",
)
CORNERS = np.array([[0, 0], [6, 0], [0, 4], [0, 4], [6, 0], [6, 4]], np.float32)
FRAGMENT = "#version 330\nflat in vec4 v_color; out vec4 frag_color; void main(){frag_color=v_color;}"


def specification(name, active_count=ACTIVE_COUNT):
    if name not in CASES or not 2 <= active_count <= ACTIVE_COUNT:
        raise ValueError((name, active_count))
    divisor = 1 if name in ("native_interleaved", "indexed_uint16_divisor1") else 2 if name == "indexed_uint32_divisor2" else 0
    return {"name": name, "active_count": active_count, "lanes": active_count - 1,
            "layout": "interleaved" if name == "native_interleaved" else "constant" if name == "sparse_uint32_constants" else "split",
            "route": "Native" if name == "native_interleaved" else "Affine" if name == "affine_nonzero_first" else "Indexed",
            "divisor": divisor, "instances": 2 * divisor if divisor else 1,
            "constant_lane": 1 if name in ("indexed_uint16_divisor1", "indexed_uint32_divisor2") else None,
            "first": 3 if name == "affine_nonzero_first" else 0,
            "index_dtype": "uint8" if name == "indexed_uint8" else "uint16" if name == "indexed_uint16_divisor1" else "uint32",
            "sparse": name == "sparse_uint32_constants",
            "api_scope": "internal GLIR first/count; public Program.draw has no first" if name == "affine_nonzero_first" else "public Program.draw",
            "comparison": "exact whole analytic RGBA array; no edge mask, tolerance or candidate fitting",
            "ordinary_max_physical_streams": 3 if name == "native_interleaved" else 2,
            "raw_independent_sources_exceed_eight": name != "native_interleaved"}


def cell_origin(cell):
    return np.array([2 + 10 * (cell % CELL_COLUMNS), 2 + 6 * (cell // CELL_COLUMNS)], np.float32)


def index_ids(spec):
    if spec["sparse"]:
        return np.arange(SPARSE_BASE, SPARSE_BASE + 6, dtype=np.uint32)
    cells = np.roll(np.arange(spec["lanes"])[::-1], 3)
    # Retain one duplicated primitive group in the actual selected sequence.
    cells = np.r_[cells, cells[0]]
    return np.concatenate([np.arange(6 * cell, 6 * cell + 6) for cell in cells]).astype(spec["index_dtype"])


def vertex_source(active_count=ACTIVE_COUNT):
    lanes = active_count - 1
    declarations = "\n".join(f"in float a_lane{lane};" for lane in range(lanes))
    choices = "\n".join(f"{'if' if lane == 0 else 'else if'} (lane == {lane}) energy = a_lane{lane};" for lane in range(lanes))
    return f"""#version 330
in vec2 a_position;
{declarations}
in float a_count;
uniform vec2 u_pixel_shift;
uniform float u_corner_scale;
uniform float u_phase;
uniform float u_flat_probe;
flat out vec4 v_color;
void main() {{
    int lane = (gl_VertexID / 6) % {lanes};
    float energy = 0.;
    {choices}
    vec2 corner = vec2(0.);
    int vertex = gl_VertexID % 6;
    if (vertex == 1 || vertex == 4) corner = vec2(6.,0.);
    else if (vertex == 2 || vertex == 3) corner = vec2(0.,4.);
    else if (vertex == 5) corner = vec2(6.,4.);
    vec2 pixel = a_position + u_corner_scale*corner + u_pixel_shift
               + vec2(0., {INSTANCE_STEP}*gl_InstanceID + {PHASE_STEP}*u_phase);
    gl_Position = vec4(pixel/vec2({SIZE[0]},{SIZE[1]})*2.-1.,0.,1.);
    gl_PointSize = 1.;
    bool original_cell_even = (gl_VertexID / 6) % 2 == 0;
    bool original_high_bit = gl_VertexID >= 16777217;
    v_color = vec4(energy > .5 ? 1. : 0.,
                   original_high_bit || original_cell_even ? 1. : 0.,
                   gl_InstanceID % 2 == 0 ? 1. : 0.,1.);
    if (u_flat_probe > .5) v_color.g = gl_VertexID % 3 == 2 ? 1. : 0.;
}}
"""


def make_program(gloo, name, active_count=ACTIVE_COUNT):
    spec = specification(name, active_count)
    program = gloo.Program(vertex_source(active_count), FRAGMENT)
    bindings = {}
    rows = 6 * spec["lanes"]
    positions = np.repeat(np.array([cell_origin(cell) for cell in range(spec["lanes"])]), 6, axis=0)
    if spec["sparse"]:
        program["a_position"] = tuple(float(value) for value in cell_origin(0))
        program["a_count"] = gloo.VertexBuffer(np.zeros(1, np.float32))
    else:
        dtype = np.dtype([("head", "u4"), ("position", "f4", 2), ("tail", "u4")])
        data = np.zeros(rows, dtype)
        data["head"], data["tail"] = 0x11223344, 0x55667788
        data["position"] = positions
        owner = gloo.VertexBuffer(data)
        program["a_position"] = owner["position"]
        bindings["position"] = {"owner": owner, "array": data.copy(), "field": "position", "constant": False}
    grouped = None
    if spec["layout"] == "interleaved":
        fields = [("head", "u4")] + [(f"lane{lane}", "f4") for lane in range(spec["lanes"])] + [("tail", "u4")]
        grouped = np.ones(rows, fields)
        grouped["head"], grouped["tail"] = 0x99AABBCC, 0xDDEEFF00
        grouped_owner = gloo.VertexBuffer(grouped)
    for lane in range(spec["lanes"]):
        key = f"a_lane{lane}"
        if spec["sparse"] or lane == spec["constant_lane"]:
            binding = 1.
            record = {"constant": True, "value": 1.}
        elif lane == 0 and spec["divisor"]:
            values = np.array([1., 0.], np.float32)
            binding = gloo.VertexBuffer(values, divisor=spec["divisor"])
            record = {"constant": False, "owner": binding, "array": values.copy(), "field": None}
        elif grouped is not None:
            binding = grouped_owner[f"lane{lane}"]
            record = {"constant": False, "owner": grouped_owner, "array": grouped.copy(), "field": f"lane{lane}"}
        else:
            values = np.ones(rows, np.float32)
            binding = gloo.VertexBuffer(values)
            record = {"constant": False, "owner": binding, "array": values.copy(), "field": None}
        program[key] = binding
        bindings[key] = record
    program["u_phase"], program["u_corner_scale"], program["u_pixel_shift"], program["u_flat_probe"] = 0., 1., (0., 0.), 0.
    indices = None if name in ("native_interleaved", "affine_nonzero_first") else gloo.IndexBuffer(index_ids(spec))
    return program, bindings, indices


def configure(gloo):
    gloo.set_viewport(0, 0, *SIZE)
    gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
    gloo.set_clear_color((0, 0, 0, 1))
    gloo.clear(color=True, depth=False, stencil=False)


def draw(canvas, gloo, program, indices, name, *, mode="triangles", phase=0, clear=True, read=True):
    spec = specification(name, len([key for key in program._code_variables if key.startswith("a_lane")]) + 1)
    if clear:
        configure(gloo)
    program["u_phase"] = float(phase)
    program["u_pixel_shift"] = (.5, .5) if mode == "points" else (0., 0.)
    if name == "affine_nonzero_first":
        canvas.context.glir.associate(program.glir)
        canvas.context.glir.command("DRAW", program.id, mode, (spec["first"], 6 * spec["lanes"] - spec["first"]), spec["instances"])
        canvas.context.flush_commands()
    else:
        program.draw(mode, indices)
    return gloo.read_pixels(alpha=True) if read else None


def set_lane(program, bindings, lane, value, *, selected_cell=None):
    key = f"a_lane{lane}"
    record = bindings[key]
    if record["constant"]:
        program[key] = float(value)
        return
    data = record["array"].copy()
    start, stop = (0, len(data)) if selected_cell is None else (6 * selected_cell, 6 * (selected_cell + 1))
    if record["field"]:
        data[record["field"]][start:stop] = value
    else:
        data[start:stop] = value
    record["owner"].set_subdata(data[start:stop], offset=start)
    record["array"] = data
    # Shared structured ownership must retain changes for subsequent fields.
    for other in bindings.values():
        if other.get("owner") is record["owner"]:
            other["array"] = data.copy()


def expected_image(name, *, active_count=ACTIVE_COUNT, phase=0, disabled_lanes=(), mode="triangles"):
    spec = specification(name, active_count)
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    cells = [0] if spec["sparse"] else range(spec["lanes"])
    sparse_lane = (SPARSE_BASE // 6) % spec["lanes"]
    for instance in range(spec["instances"]):
        for cell in cells:
            lane = sparse_lane if spec["sparse"] else cell
            energized = lane not in disabled_lanes and not (lane == 0 and spec["divisor"] and instance // spec["divisor"] == 1)
            color = (255 if energized else 0, 255 if spec["sparse"] or cell % 2 == 0 else 0, 255 if instance % 2 == 0 else 0, 255)
            x, y = cell_origin(cell).astype(int)
            y += INSTANCE_STEP * instance + PHASE_STEP * phase
            if mode == "triangles":
                if spec["first"] and cell == 0:
                    # First3 selects the upper-right triangle (source3,4,5).
                    # Pixel centers avoid equality on its diagonal: the exact
                    # half-plane is 2*dx+3*dy>=10 for integer pixel offsets.
                    for dy in range(4):
                        for dx in range(6):
                            if 2 * dx + 3 * dy >= 10:
                                image[SIZE[1] - 1 - (y + dy), x + dx] = color
                else:
                    image[SIZE[1] - y - 4:SIZE[1] - y, x:x + 6] = color
            elif mode == "points":
                corners = CORNERS[3:] if spec["first"] and cell == 0 else CORNERS
                for dx, dy in corners.astype(int):
                    image[SIZE[1] - 1 - (y + dy), x + dx] = color
            else:
                raise ValueError(mode)
    return image


def topology_data(mode):
    if mode not in TOPOLOGIES:
        raise ValueError(mode)
    positions = np.array([[10, 10], [22, 10], [10, 20], [10, 20], [22, 10], [22, 20]], np.float32)
    if mode.startswith("line"):
        positions += .5
    ids = {"triangles": [0, 1, 2, 3, 4, 5], "triangle_strip": [0, 1, 2, 5],
           "triangle_fan": [0, 1, 5, 2], "lines": [0, 1, 5, 2],
           "line_strip": [0, 1, 5], "line_loop": [0, 1, 5, 2]}[mode]
    return positions, np.array(ids, np.uint32)


def expected_topology(mode):
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    if mode.startswith("triangle"):
        image[SIZE[1] - 20:SIZE[1] - 10, 10:22] = 255
        return image
    pixels = {(x, 10) for x in range(10, 22)}
    if mode == "lines":
        pixels |= {(x, 20) for x in range(11, 23)}
    elif mode in ("line_strip", "line_loop"):
        pixels |= {(22, y) for y in range(10, 20)}
        if mode == "line_loop":
            pixels |= {(x, 20) for x in range(11, 23)} | {(10, y) for y in range(11, 21)}
    else:
        raise ValueError(mode)
    for x, y in pixels:
        image[SIZE[1] - 1 - y, x] = 255
    return image


def array_record(array):
    return {"shape": list(array.shape), "dtype": array.dtype.str,
            "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()}


def contract():
    return {"active_count": ACTIVE_COUNT, "size": list(SIZE), "cases": {name: specification(name) for name in CASES},
            "topologies": list(TOPOLOGIES), "expected_frames": {name: array_record(expected_image(name)) for name in CASES},
            "expected_topologies": {mode: array_record(expected_topology(mode)) for mode in TOPOLOGIES},
            "pending_update": "old lower draw -> middle six scalar rows subdata + separate constant revision -> new phase128 draw -> one final read",
            "lane_witnesses": "each of29 scalar lanes independently changes only its designated visible cell across original instances",
            "primitive_switch": "same Program indexed points -> ordinary triangles -> same points; independent point pixels and rectangle arrays",
            "flat_last": "source IDs2and5 last on both rectangle triangles; compact index rank3 must retain original source5",
            "warm_and_loss": "resident CPU conversion counters stay fixed; actual loss changes generation and reuploads GPU bytes without new CPU conversions",
            "oracle_scope": "full30 analytic; any unchanged pinned OpenGL capture must state its actual smaller input grant",
            "open_gates": list(OPEN_GATES), "candidate_seen": False, "GPU_used": False}
