"""Independent SIZE/LINK snapshots of legal >64MiB ordinary inputs.

The immutable retired and pending families supply the original geometry. The
new arrays are declared before any candidate; public set_data/set_shaders emit
mutations, while affine first/count stays an explicitly internal GLIR boundary.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import numpy as np

from tools import fixture_ordinary_oversized as retired
from tools import fixture_ordinary_oversized_pending as pending

CASES = retired.CASES
MODES = ("size", "link")
LIFETIMES = ("survivor", "delete-before-present")
SIZE = retired.SIZE
SAMPLE_LIMITS = retired.SAMPLE_LIMITS
RESIDENT = pending.RESIDENT
LINK_FRAGMENT = "#version 330\nflat in vec4 v_color; out vec4 color; void main(){color=vec4(1.-v_color.r,v_color.g,v_color.b,v_color.a);}"
UNCHANGED_INPUTS = {
    "tools/fixture_ordinary_oversized.py": "515a10b5aa78ecec71fb026619faecc36e4fc0c097500782988b62af6c0ff828",
    "tools/fixture_ordinary_oversized_pending.py": "5b5cb0fc8373a52c18a292eba3725d16d8d470dc569ebf79306f8a056eb9f19b",
}


def plan(name, limits, *, budget=retired.HISTORY_BYTES):
    p = retired.plan(name, limits, budget=budget)
    resized_plan(p, limits)  # Check every new allocation before constructors.
    return p


def resized_plan(p, limits):
    if p.name == CASES[0]:
        q = replace(p, count=p.count + 6, target_bytes=p.target_bytes + 24,
                    geometry_upload_bytes=p.geometry_upload_bytes + 24)
        maximum_allocation = q.count * 4
    elif p.name == CASES[1]:
        # The active lane0 and inactive count witness both grow, but the affine
        # first/count selection is unchanged. The compact target keeps its size.
        q = replace(p, source_rows=p.source_rows + 6)
        maximum_allocation = max(q.target_bytes, q.source_rows * 4)
    elif p.name == CASES[2]:
        # All nine divisor2 sources must grow together for legal Program.draw.
        # The shader bounds visibility to the original last four instances;
        # additional valid instances are offscreen rather than extra geometry.
        q = replace(p, instances=p.instances + 4, source_rows=p.source_rows + 2,
                    target_bytes=p.target_bytes + 4 * p.stride,
                    geometry_upload_bytes=p.geometry_upload_bytes + 4 * p.stride)
        maximum_allocation = max(q.target_bytes, q.source_rows * 4)
    else:
        raise ValueError(p.name)
    if maximum_allocation > int(limits["max_buffer_size"]):
        raise ValueError("resized source/compact allocation exceeds actual grant")
    if max(q.first + q.count, q.instances) > 2 ** 31 - 1:
        raise ValueError("resized draw exceeds signed native draw-count grant")
    return q


def vertex_source(p):
    source = retired.vertex_source(p)
    if p.name == CASES[2]:
        original = f"if (gl_InstanceID >= {p.instances - 4})"
        bounded = f"if (gl_InstanceID >= {p.instances - 4} && gl_InstanceID < {p.instances})"
        assert source.count(original) == 1
        source = source.replace(original, bounded)
    return source


def make_program(gloo, p):
    program, buffers, indices = retired.make_program(gloo, p)
    # This fresh family deliberately admits a real active resized affine source,
    # rather than claiming unused a_count alone exercises immutable input data.
    if p.name == CASES[1]:
        lane0 = gloo.VertexBuffer(np.ones(p.source_rows, np.float32))
        program["a_lane0"] = lane0
        buffers.append(lane0)
    if p.name == CASES[2]:
        program.set_shaders(vertex_source(p), retired.FRAGMENT)
    return program, buffers, indices


def resized_arrays(p):
    """Exact public upload arrays; constructor/scale witnesses preserve dtypes."""
    if p.name == CASES[0]:
        values = np.full(p.count + 6, p.visible_first + 18, np.uint32)
        values[-6:] = retired.tail_indices(p, revised=True)
        return {"index": values}
    if p.name == CASES[1]:
        return {"count": np.zeros(p.source_rows + 6, np.float32),
                "lane0": np.zeros(p.source_rows + 6, np.float32)}
    if p.name == CASES[2]:
        result = {}
        for lane in range(p.lanes):
            values = np.ones(p.source_rows + 2, np.float32)
            if lane == 0:
                values[:p.source_rows:2], values[1:p.source_rows:2] = 0., 1.
                for row in range(p.source_rows - 2, p.source_rows):
                    values[row] = 1 - (row % 2)
            result[f"lane{lane}"] = values
        return result
    raise ValueError(p.name)


def mutate(program, buffers, indices, p, limits, mode):
    if mode == "link":
        # Public automatic replay passes stored constant ndarrays back through
        # __setitem__, where they become 1-row VBOs. Explicit documented replay
        # preserves the intended original constants and legal active sources.
        program.set_shaders(vertex_source(p), LINK_FRAGMENT, update_variables=False)
        program["a_count"] = buffers[0]
        for lane in range(p.lanes):
            if p.name == CASES[2]:
                value = buffers[lane + 1]
            elif p.name == CASES[1] and lane == 0:
                value = buffers[-1]
            else:
                value = 1.
            program[f"a_lane{lane}"] = value
        return p
    if mode != "size":
        raise ValueError(mode)
    q = resized_plan(p, limits)
    arrays = resized_arrays(p)
    if p.name == CASES[0]:
        indices.set_data(arrays["index"], copy=True)
    elif p.name == CASES[1]:
        buffers[0].set_data(arrays["count"], copy=True)
        buffers[-1].set_data(arrays["lane0"], copy=True)
    else:
        for lane in range(p.lanes):
            buffers[lane + 1].set_data(arrays[f"lane{lane}"], copy=True)
    return q


def expected_new(p, mode):
    if mode == "size":
        return retired.expected_image(p, revised=True)
    if mode == "link":
        result = retired.expected_image(p)
        # Fragment inversion applies only where original geometry covers the
        # quad. The opaque black clear is neither inverted nor recolored.
        for cell in range(4 if p.name == CASES[2] else 1):
            result[14:20, 4 + 10 * cell:12 + 10 * cell, 0] = 255 - result[14:20, 4 + 10 * cell:12 + 10 * cell, 0]
        return result
    raise ValueError(mode)


def expected_pair(p, mode):
    return pending.overlay(retired.expected_image(p), pending.shift_band(expected_new(p, mode), 12))


def draw(canvas, gloo, program, indices, p, *, clear=True, band=0):
    pending.draw_revision(canvas, gloo, program, indices, p, clear=clear, band=band)


def delete(program, buffers, indices):
    pending.delete_sources(program, buffers, indices)


def assert_pending(before, first, both):
    assert before["pending_draws"] == before["pending_tickets"] == before["queued_frames"] == 0
    assert first["pending_draws"] == 2 and both["pending_draws"] == 3
    for value in (first, both):
        for key in ("draw_calls", "dawn_queue_submits", "retired_tickets", "completion_waits", "finish_calls"):
            assert value[key] == before[key], (key, before[key], value[key])
        assert value["pending_tickets"] == value["queued_frames"] == 0


def assert_executed(before, after, *, draws):
    for key, delta in (("draw_calls", draws), ("dawn_queue_submits", 1), ("retired_tickets", 1)):
        assert after[key] - before[key] == delta, (key, before[key], after[key])
    assert all(after[key] == 0 for key in ("pending_draws", "pending_tickets", "queued_frames", "pending_timestamp_frames"))
    assert after["completion_waits"] == before["completion_waits"] and after["finish_calls"] == before["finish_calls"]


def expected_command_footprint(p, mode, sources, program_id):
    """Actual IDs bind SIZE to resized selected sources, not an unrelated VBO."""
    if mode == "link":
        return {"program": program_id, "LINK": 1, "ATTACH": 2,
                "vertex": vertex_source(p), "fragment": LINK_FRAGMENT}
    if mode != "size":
        raise ValueError(mode)
    arrays = resized_arrays(p)
    return {"program": program_id, "SIZE_DATA": {
        str(sources[name]): {"SIZE": value.nbytes, "DATA_offset": 0, "logical_array": pending.array_record(value)}
        for name, value in arrays.items()}}


def assert_mutation_commands(commands, expected, mode):
    if mode == "size":
        for source, data in expected["SIZE_DATA"].items():
            key = int(source)
            sizes = [c for c in commands if c[:2] == ["SIZE", key]]
            uploads = [c for c in commands if c[:2] == ["DATA", key]]
            assert len(sizes) == len(uploads) == 1
            assert sizes[0][2] == data["SIZE"] and uploads[0][2] == data["DATA_offset"]
            # Public VertexBuffer wraps scalar float32 into its unchanged
            # structured field. Byte hashes bind the exact source upload;
            # scaled upstream witnesses separately prove that field's dtype.
            assert uploads[0][3]["sha256"] == data["logical_array"]["sha256"]
            assert uploads[0][3]["shape"] == data["logical_array"]["shape"]
    elif mode == "link":
        program = expected["program"]
        live, attached, linked, link_count = {}, [], None, 0
        for command in commands:
            operation = command[0]
            if operation == "CREATE" and command[2] in ("VertexShader", "FragmentShader"):
                assert command[1] not in live
                live[command[1]] = {"id": command[1], "type": command[2], "source": None}
            elif operation == "DATA" and command[1] in live:
                assert command[2] == 0 and isinstance(command[3], str) and command[3]
                live[command[1]]["source"] = command[3]
            elif operation == "ATTACH" and command[1] == program:
                stage = live[command[2]]
                assert not any(value is stage for value in attached)
                attached.append(stage)
            elif operation == "LINK" and command[1] == program:
                assert len(attached) == 2 and all(live.get(value["id"]) is value for value in attached)
                assert {value["type"] for value in attached} == {"VertexShader", "FragmentShader"}
                # Immutable linked source image; DELETE or subsequent DATA must
                # never rewrite the shader that this new draw actually owns.
                linked = {value["type"]: value["source"] for value in attached}
                assert linked == {"VertexShader": expected["vertex"], "FragmentShader": expected["fragment"]}
                link_count += 1
            elif operation == "DELETE":
                live.pop(command[1], None)
            elif operation == "DRAW" and command[1] == program:
                assert link_count == 1 and linked == {"VertexShader": expected["vertex"], "FragmentShader": expected["fragment"]}
        assert link_count == 1
    else:
        raise ValueError(mode)


def source_ids(p, buffers, indices):
    if p.name == CASES[0]:
        return {"index": indices.id}
    if p.name == CASES[1]:
        return {"count": buffers[0].id, "lane0": buffers[-1].id}
    return {f"lane{lane}": buffers[lane + 1].id for lane in range(p.lanes)}


def contract():
    plans = {name: plan(name, SAMPLE_LIMITS) for name in CASES}
    return {
        "schema": 1, "GPU_used": False, "candidate_seen": False,
        "future_minimum_epoch": 31, "size": list(SIZE), "modes": list(MODES), "lifetimes": list(LIFETIMES),
        "unchanged_inputs_sha256": UNCHANGED_INPUTS,
        "plans": {name: asdict(p) for name, p in plans.items()},
        "resized_draw_plans": {name: asdict(resized_plan(p, SAMPLE_LIMITS)) for name, p in plans.items()},
        "expected": {name: {"old": pending.array_record(retired.expected_image(p)),
                            **{mode: {"new": pending.array_record(expected_new(p, mode)), "pair": pending.array_record(expected_pair(p, mode))} for mode in MODES}}
                     for name, p in plans.items()},
        "sequence": "prewarm old without read; CLEAR,DRAW old lower; public SIZE+DATA or public LINK; DRAW new upper; optional source+Program DELETE; one final present; actual retirement; full-target separate quality read",
        "SIZE_scope": "IndexBuffer full reset grows6 uint32 entries and reverses LAST indices; affine active lane0 and count grow6 float32 rows with zero lane0; every divisor2 source grows2 rows legally and lane0 tail flips. Geometry shader bounds new extra instances offscreen.",
        "LINK_scope": "public Program.set_shaders(update_variables=False) with same exact active vertex shader and fragment red inversion, followed by explicit same-source/scalar ATTRIBUTE bindings. This avoids default automatic constant-array replay into1-row VBOs; old DrawSnap retains prior link and input state. No assumption that unchanged geometry must duplicate physical CPU/GPU storage.",
        "comparison": "exact complete analytic RGBA; pixel-center 8:6 halfplanes, original uint32 IDs and flat LAST; no tolerances or candidate-derived fitting",
        "counter_scope": "exact pending CLEAR+two DRAW3, no intermediate submit/wait; final2 scene DRAW/1 submit/1 retired Ticket; surviving changed SIZE must rebuild converted input, surviving unchanged redraw zero resident costs",
        "deletion_scope": "pending DrawSnap logical source+Program ownership only; post-submit retirement and registry collection must release logical conversion/GPU resources. Shared immutable views overlap and are not physical memory.",
        "API_scope": "SIZE and LINK are unchanged public emitters. Sparse indexed and divisor draws use public Program.draw; affine first/count is a labeled internal GLIR boundary. Installed upstream CPU witness does not prove GPU rendering.",
        "resident_counters": list(RESIDENT),
        "open_gates": ["mixed DATA/SIZE/ATTRIBUTE/LINK queued snapshots", "mixed submitted-Ticket deletion/retirement", "mixed submitted loss and surviving Program recovery", "additional mutation backpressure/ordered queued frames", "arbitrary mutated-layout reuse", "partitioning/batching, physical allocator and other platform admission"],
    }
