"""Independent oversized snapshots and unchanged-selection working sets.

The original retired-frame fixtures are imported without changing their bytes.
The affine first/count cases are explicitly internal GLIR boundary contracts;
Program.draw has no public first/count argument. CPU construction uses no Canvas.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import numpy as np

from tools import fixture_ordinary_oversized as retired

CASES = retired.CASES
SIZE = retired.SIZE
HISTORY_BYTES = retired.HISTORY_BYTES
WORKING_ENTRIES = 8
WORKING_BYTES = 256 * 1024 * 1024
SAMPLE_LIMITS = retired.SAMPLE_LIMITS
RESIDENT = (
    "vertex_input_conversion_builds", "vertex_input_conversion_bytes",
    "point_conversion_builds", "point_conversion_bytes", "buffer_uploads",
    "geometry_upload_bytes", "texture_uploads", "texture_upload_bytes",
    "buffer_allocations", "texture_allocations", "pipeline_misses",
    "portable_shader_misses", "uniform_upload_bytes", "completion_waits", "finish_calls",
)


def array_record(value):
    return {"shape": list(value.shape), "dtype": value.dtype.str,
            "sha256": hashlib.sha256(value.tobytes()).hexdigest()}


def overlay(background, foreground):
    """Opaque quads; independent expected array composition in draw order."""
    result = background.copy()
    selected = np.any(foreground[..., :3] != 0, axis=2)
    result[selected] = foreground[selected]
    return result


def shift_band(image, band):
    if type(band) is not int or not 0 <= band <= 12:
        raise ValueError("band must retain every visible pixel in the canvas")
    result = np.zeros_like(image)
    result[..., 3] = 255
    if band:
        result[:-band] = image[band:]
    else:
        result[:] = image
    return result


def expected_pending(p):
    return overlay(retired.expected_image(p),
                   shift_band(retired.expected_image(p, revised=True), 12))


def configure(gloo, *, clear, band=0):
    gloo.set_viewport(0, band, *SIZE)
    gloo.set_state(blend=False, depth_test=False, stencil_test=False,
                   scissor_test=False, cull_face=False)
    if clear:
        gloo.clear(color=(0., 0., 0., 1.), depth=False, stencil=False)


def queue_affine(canvas, program, first, count, instances=1):
    canvas.context.glir.associate(program.glir)
    canvas.context.glir.command("DRAW", program.id, "triangles", (first, count), instances)
    canvas.context.flush_commands()


def draw_revision(canvas, gloo, program, indices, p, *, clear=True, band=0):
    configure(gloo, clear=clear, band=band)
    if p.name == CASES[1]:
        queue_affine(canvas, program, p.first, p.count, p.instances)
    else:
        program.draw("triangles", indices)


def delete_sources(program, buffers, indices):
    seen = set()
    for source in [*buffers, indices]:
        if source is not None and source.id not in seen:
            seen.add(source.id)
            source.delete()
    program.delete()


@dataclass(frozen=True)
class WorkingPlan:
    base: retired.Plan
    layouts: int
    source_rows: int
    payload_bytes_per_layout: int
    minimum_payload_graph_bytes: int


def working_plan(limits, *, layouts=2, budget=HISTORY_BYTES):
    if type(layouts) is not int or layouts not in (2, 5):
        raise ValueError("working fixture admits exactly two or five selections")
    p = retired.plan(CASES[1], limits, budget=budget)
    rows = p.first + layouts * p.count
    if rows > 2 ** 31 - 1 or rows * 4 > int(limits["max_buffer_size"]):
        raise ValueError("unchanged count source exceeds actual allocation/draw grant")
    # Each affine layout owns the full compact vertex payload and a uint32 first
    # child. Actual runtime bookkeeping/full-graph charges are checked separately.
    return WorkingPlan(p, layouts, rows, p.target_bytes, layouts * (p.target_bytes + 4))


def working_vertex_source(w):
    p = w.base
    inputs = "\n".join(f"in float a_lane{lane};" for lane in range(p.lanes))
    energy = "+".join(f"a_lane{lane}" for lane in range(p.lanes))
    return f"""#version 330
{inputs}
in float a_count;
flat out vec4 v_color;
void main() {{
    int original = gl_VertexID - {p.first};
    int selection = original / {p.count};
    int local = original % {p.count};
    float energy = {energy};
    v_color = vec4((gl_VertexID%2)==1 ? 1. : 0., abs(energy-{p.lanes}.)<.25 ? 1. : 0., (selection%2)==1 ? 1. : 0., 1.);
    gl_Position = vec4(2.,2.,0.,1.);
    if (local >= {p.count - 6} && local < {p.count}) {{
        int vertex = local - {p.count - 6};
        vec2 corner = vec2(0.);
        if (vertex == 1 || vertex == 4) corner = vec2(8.,0.);
        else if (vertex == 2 || vertex == 3) corner = vec2(0.,6.);
        else if (vertex == 5) corner = vec2(8.,6.);
        vec2 pixel = vec2(4.+2.*float(selection),4.)+corner;
        gl_Position = vec4(pixel/vec2({SIZE[0]},{SIZE[1]})*2.-1.,0.,1.);
    }}
}}
"""


def make_working_program(gloo, w):
    p = w.base
    program = gloo.Program(working_vertex_source(w), retired.FRAGMENT)
    count = gloo.VertexBuffer(np.zeros(w.source_rows, np.float32))
    program["a_count"] = count
    for lane in range(p.lanes):
        program[f"a_lane{lane}"] = 1.
    return program, [count], None


def expected_working(w, layout, *, band=0):
    if type(layout) is not int or not 0 <= layout < w.layouts:
        raise ValueError("unadmitted unchanged selection")
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    first = w.base.first + (layout + 1) * w.base.count - 6
    for dy in range(6):
        for dx in range(8):
            # Pixel-center halfplanes for (0,0),(8,0),(0,6) never tie.
            corner = 2 if 6 * (dx + .5) + 8 * (dy + .5) < 48 else 5
            vertex = first + corner
            image[SIZE[1] - 1 - (4 + dy), 4 + 2 * layout + dx] = (
                255 * (vertex % 2), 255, 255 * (layout % 2), 255)
    return shift_band(image, band)


def draw_working(canvas, gloo, program, w, layout, *, clear=True, band=0, repeats=1):
    if type(repeats) is not int or repeats < 1:
        raise ValueError("positive actual draw count required")
    expected_working(w, layout, band=band)  # Validate selection before encoding.
    configure(gloo, clear=clear, band=band)
    for _ in range(repeats):
        queue_affine(canvas, program, w.base.first + layout * w.base.count, w.base.count)


def assert_resident(before, after):
    for name in RESIDENT:
        assert after[name] == before[name], (name, before[name], after[name])


def assert_working_bounds(baseline, value):
    assert value["vertex_input_oversized_entry_limit"] == WORKING_ENTRIES
    assert value["vertex_input_oversized_byte_limit"] == WORKING_BYTES
    assert 0 <= value["vertex_input_oversized_entries"] - baseline["vertex_input_oversized_entries"] <= WORKING_ENTRIES
    assert 0 <= value["vertex_input_oversized_bytes"] - baseline["vertex_input_oversized_bytes"] <= WORKING_BYTES
    assert 0 <= value["vertex_input_current_entries"] - baseline["vertex_input_current_entries"] <= 6
    assert 0 <= value["vertex_input_cache_entries"] - baseline["vertex_input_cache_entries"] <= 128
    assert 0 <= value["vertex_input_cache_bytes"] - baseline["vertex_input_cache_bytes"] <= HISTORY_BYTES


def value_record(value):
    if isinstance(value, np.ndarray):
        return {**array_record(value), "dtype_descriptor": repr(value.dtype.descr)}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (tuple, list)):
        return [value_record(part) for part in value]
    if isinstance(value, dict):
        return {key: value_record(part) for key, part in value.items()}
    return value


def command_record(command):
    return value_record(command)


def contract():
    plans = {name: retired.plan(name, SAMPLE_LIMITS) for name in CASES}
    w = working_plan(SAMPLE_LIMITS, layouts=5)
    return {
        "schema": 1, "GPU_used": False, "candidate_seen": False,
        "future_exact_epoch": 30, "size": list(SIZE),
        "unchanged_retired_fixture_sha256": "515a10b5aa78ecec71fb026619faecc36e4fc0c097500782988b62af6c0ff828",
        "pending_plans": {name: asdict(p) for name, p in plans.items()},
        "pending_expected": {name: array_record(expected_pending(p)) for name, p in plans.items()},
        "pending_sequence": "CLEAR,DRAW(old lower),revision,DRAW(new upper),optional source+Program DELETE; one final present and separate read; no intermediate present/read",
        "revision_scope": "index middle/tail DATA, constant ATTRIBUTE and divisor2 middle/tail DATA retain old/new immutable snapshots; other SIZE/LINK variants remain open",
        "submission_scope": "nonzero actual submitted Tickets observed before deletion/loss; logical retirement is not physical GPU completion on device loss",
        "loss_scope": "open test-owned paint, actual headless submission, temporary source+Program DELETE, real device loss, failed/device_lost/cancelled terminal; surviving prewarmed Program reuploads once with zero CPU conversions",
        "working_plan": asdict(w), "working_entries": WORKING_ENTRIES, "working_bytes": WORKING_BYTES,
        "working_expected": {str(layout): array_record(expected_working(w, layout)) for layout in range(5)},
        "working_selection": "same Program/source/index/ATTRIBUTE revisions; only GLIR DRAW first/count selectors change; each payload alone >64MiB; two payload graphs fit256MiB, five exceed256MiB before bookkeeping",
        "working_graph_charge": "reported key/record/child full-graph budget; current/history/working views overlap and are never added as physical bytes",
        "backpressure": "three cached batches A@0,B@3,A@6, four identical opaque DRAWs per batch, one initial clear; actual queued/deferred witness, exact12 draw/3 submit deltas and final composited frame; nonblocking events only",
        "comparison": "exact full analytic uint8 RGBA, pixel-center halfplanes, original integer IDs/flat-LAST; no edge mask/tolerance/candidate fitting",
        "resident_counters": list(RESIDENT),
        "API_scope": "selection and divisor cases use public Program.draw; affine first/count are actual internal GLIR queue-boundary contracts; scaled installed upstream CPU construction proves emitters/dtypes only, not rasterization",
        "open_gates": ["pending SIZE/LINK and multi-source mixed mutations", "arbitrary mutated-layout or cross-index-owner working reuse", "stride/storage partitioning and ordered batches", "physical allocator/RSS", "other bindings/backends/drivers", "actual attached-surface acquisition failure and scanout"],
    }
