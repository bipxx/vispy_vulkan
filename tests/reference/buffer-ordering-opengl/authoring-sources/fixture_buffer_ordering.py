"""Independent pending middle-subdata and single-flush GLIR contracts.

U01 uses public Program.draw and buffer.set_subdata with both dependent draws
pending until one final read. U03 deliberately exercises the internal documented GLIR
queue boundary: Program.draw itself flushes, so it cannot produce that batch.
The installed queue's real filter, including removal across a DRAW, is retained.
"""
from __future__ import annotations

import hashlib
import numpy as np

try:
    from .fixture_gloo import Runner, SIZE, rectangle, freeze
except ImportError:
    from fixture_gloo import Runner, SIZE, rectangle, freeze

CASES = ("pending_middle_subdata", "single_flush_resize_filter")
COMPARISON = {"full_frame_exact": True, "analytic_full_frame_exact": True,
              "candidate_alignment_or_color_fit": False}
INTERLEAVED = np.dtype([("sentinel_left", "<u4"), ("a_position", "<f4", 2),
                        ("a_color", "<f4", 3), ("sentinel_right", "<u4")])
VERT = """
attribute vec2 a_position;
attribute vec3 a_color;
uniform vec2 u_offset;
varying vec3 v_color;
void main() {
    gl_Position = vec4(a_position + u_offset, 0.0, 1.0);
    v_color = a_color;
}
"""
FRAG = """
varying vec3 v_color;
void main() { gl_FragColor = vec4(v_color, 1.0); }
"""
SOLID_VERT = """
attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
"""
SOLID_FRAG = """
uniform vec4 u_color;
void main() { gl_FragColor = u_color; }
"""

def array_record(value):
    data = np.ascontiguousarray(value)
    record = {"sha256": hashlib.sha256(data.tobytes()).hexdigest(),
              "shape": list(data.shape), "dtype": data.dtype.str, "bytes": data.nbytes}
    if data.dtype.fields:
        record["fields"] = {name: {"offset": data.dtype.fields[name][1],
            "dtype": data.dtype.fields[name][0].base.str,
            "shape": list(data.dtype.fields[name][0].shape)} for name in data.dtype.names}
    return record

def input_arrays(name):
    if name == CASES[0]:
        initial = np.empty(18, INTERLEAVED)
        initial["sentinel_left"] = np.arange(18, dtype=np.uint32) + 0x13570000
        initial["sentinel_right"] = np.arange(18, dtype=np.uint32) + 0x24680000
        for index, (left, right, color) in enumerate((
                (-1, -.375, (1, 0, 0)), (-.375, .375, (0, 1, 0)), (.375, 1, (0, 0, 1)))):
            selection = slice(6 * index, 6 * (index + 1))
            initial["a_position"][selection] = rectangle(left, right, -1, 0)
            initial["a_color"][selection] = color
        patch = initial[6:12].copy()
        patch["a_color"] = (1, 1, 0)
        final = initial.copy()
        final[6:12] = patch
        return {"initial": initial, "middle_patch": patch, "final": final}
    if name == CASES[1]:
        # Partial writes are strictly smaller than capacity: they do not emit
        # the extra SIZE used by Buffer.set_subdata for a whole-capacity write.
        initial = np.concatenate([rectangle(-1, 0), np.full((3, 2), (2, 2), np.float32)])
        early = rectangle(-1, 0, 0, 1)
        late = np.concatenate([rectangle(0, 1), rectangle(0, 1)[:3]])
        return {"initial": initial, "early_partial": early, "late_partial": late}
    raise ValueError(name)

def expected_image(name):
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 3] = 255
    if name == CASES[0]:
        image[:, :10, :3] = (255, 0, 0)
        image[:, 22:, :3] = (0, 0, 255)
        image[12:, 10:22, :3] = (0, 255, 0)
        image[:12, 10:22, :3] = (255, 255, 0)
    elif name == CASES[1]:
        image[:, :16, :3] = (0, 0, 255)
        image[:, 16:, :3] = (0, 255, 0)
    else:
        raise ValueError(name)
    return image

def case_contract(name):
    data = input_arrays(name)
    return {"case": name, "size": list(SIZE), "comparison": COMPARISON,
        "inputs": {key: array_record(value) for key, value in data.items()},
        "expected_rgba": array_record(expected_image(name)),
        "scope": ("U01 public Program.draw / VertexBuffer.set_subdata, middle structured patch"
            if name == CASES[0] else "U03 internal documented GLIR queue boundary, not a public Program.draw batch"),
        "prewarm": "one public draw and swap_buffers before dependent window; no readback",
        "dependent_window": "no capture, finish, swap or GPU wait between dependent draws/updates",
        "readbacks": 1,
        "landmarks": [{"row": y, "column": x, "rgba": expected_image(name)[y, x].tolist()}
            for y in (5, 18) for x in (4, 15, 27)],
        **({"patch_element_offset": 6, "patch_byte_offset": 6 * INTERLEAVED.itemsize,
            "patch_byte_size": 6 * INTERLEAVED.itemsize,
            "attribute_stride": INTERLEAVED.itemsize,
            "outside_patch_vertices": [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17],
            "first_draw_middle": "green", "second_draw_middle": "yellow"}
           if name == CASES[0] else {"initial_capacity_bytes": 72, "new_capacity_bytes": 96,
            "raw_buffer_draw_ops": ["DATA", "DRAW", "SIZE", "DATA", "DRAW"],
            "filtered_buffer_draw_ops": ["DRAW", "SIZE", "DATA", "DRAW"],
            "filter_semantics": "later SIZE removes earlier DATA across DRAW; first DRAW uses already uploaded initial bytes",
            "dependent_explicit_flushes": 1})}

def assert_image(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4)
    assert np.array_equal(image, expected_image(name)), (
        name, int(np.count_nonzero(np.any(image != expected_image(name), axis=2))))

def _target_commands(commands, buffer_id, program_id):
    return [command for command in commands if
            (command[0] in ("DATA", "SIZE") and command[1] == buffer_id) or
            (command[0] == "DRAW" and command[1] == program_id)]

def _canonical(commands, buffer_id, program_id):
    result = []
    for command in _target_commands(commands, buffer_id, program_id):
        if command[0] == "DATA":
            payload = command[3]["array"] if isinstance(command[3], dict) else array_record(command[3])
            result.append(["DATA", "buffer", command[2], {key: payload[key] for key in ("sha256", "bytes")}])
        elif command[0] == "SIZE":
            result.append(["SIZE", "buffer", command[2]])
        else:
            result.append(["DRAW", "program", *freeze(command[2:])])
    return result

def expected_single_flush_transcripts():
    arrays = input_arrays(CASES[1])
    payload = lambda array: {key: array_record(array)[key] for key in ("sha256", "bytes")}
    raw = [["DATA", "buffer", 0, payload(arrays["early_partial"])],
           ["DRAW", "program", "triangles", [0, 6], 1],
           ["SIZE", "buffer", 96],
           ["DATA", "buffer", 0, payload(arrays["late_partial"])],
           ["DRAW", "program", "triangles", [0, 9], 1]]
    return {"raw": raw, "filtered": raw[1:]}

def actual_cpu_queue_transcript():
    """Invoke the installed real GlirQueue.flush without a graphics context."""
    from vispy.gloo.glir import GlirQueue
    arrays = input_arrays(CASES[1])
    queue, buffer_id, program_id = GlirQueue(), 11, 21
    queue.command("DATA", buffer_id, 0, arrays["early_partial"])
    queue.command("DRAW", program_id, "triangles", (0, 6), 1)
    queue.command("SIZE", buffer_id, 96)
    queue.command("DATA", buffer_id, 0, arrays["late_partial"])
    queue.command("DRAW", program_id, "triangles", (0, 9), 1)
    raw = [freeze(command) for command in queue._shared._commands]
    class Observer:
        def __init__(self):
            self.batches = []
        def parse(self, commands):
            self.batches.append([freeze(command) for command in commands])
    observer = Observer()
    queue.flush(observer)
    assert len(observer.batches) == 1
    result = {"raw": _canonical(raw, buffer_id, program_id),
              "filtered": _canonical(observer.batches[0], buffer_id, program_id)}
    assert result == expected_single_flush_transcripts()
    return {"graphics_context_created": False, "actual_installed_queue_flush": True,
            "parser_calls": 1, "raw": raw, "filtered": observer.batches[0], "canonical": result}

def assert_trace(name, commands, observations):
    window = commands[observations["window_start"]:observations["window_end"]]
    selected = _target_commands(window, observations["buffer_id"], observations["program_id"])
    if name == CASES[0]:
        assert [item[0] for item in selected] == ["DRAW", "DATA", "DRAW"]
        assert selected[1][2] == 6 * INTERLEAVED.itemsize
        assert selected[1][3]["array"]["sha256"] == array_record(input_arrays(name)["middle_patch"])["sha256"]
        assert selected[1][3]["array"]["bytes"] == 6 * INTERLEAVED.itemsize
    else:
        canonical = {"raw": _canonical(observations["raw_dependent_queue"], observations["buffer_id"], observations["program_id"]),
                     "filtered": _canonical(window, observations["buffer_id"], observations["program_id"])}
        assert canonical == expected_single_flush_transcripts()
        assert observations["dependent_explicit_flushes"] == 1
        assert observations["dependent_parser_calls_with_target_commands"] == 1
    assert observations["readbacks"] == 1
    assert observations["prewarm_swaps"] == 1

def render(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    runner = Runner(backend)
    canvas = runner.canvas()
    gloo = runner.gloo
    parser = canvas.context.shared.parser
    original = parser.parse
    batches = []
    def parse(commands):
        batches.append([freeze(command) for command in commands])
        return original(commands)
    parser.parse = parse
    arrays = input_arrays(name)
    observations = {"prewarm_swaps": 1, "dependent_explicit_flushes": 0}
    try:
        if name == CASES[0]:
            buffer = gloo.VertexBuffer(arrays["initial"])
            program = gloo.Program(VERT, FRAG)
            program["a_position"] = buffer["a_position"]
            program["a_color"] = buffer["a_color"]
            program["u_offset"] = (0, 0)
        else:
            buffer = gloo.VertexBuffer(arrays["initial"])
            program = gloo.Program(SOLID_VERT, SOLID_FRAG)
            program["a_position"] = buffer
            program["u_color"] = (1, 0, 0, 1)
        program.draw("triangles")
        canvas.swap_buffers()
        runner.clear((0, 0, 0, 1))
        observations.update(window_start=len(runner.commands), buffer_id=buffer.id, program_id=program.id)
        if name == CASES[0]:
            program.draw("triangles")
            buffer.set_subdata(arrays["middle_patch"], offset=6, copy=True)
            program["u_offset"] = (0, 1)
            program.draw("triangles")
        else:
            program["u_color"] = (0, 0, 1, 1)
            buffer.set_subdata(arrays["early_partial"], offset=0, copy=True)
            canvas.context.glir.command("DRAW", program.id, "triangles", (0, 6), 1)
            buffer.resize_bytes(96)
            buffer.set_subdata(arrays["late_partial"], offset=0, copy=True)
            program["u_color"] = (0, 1, 0, 1)
            canvas.context.glir.command("DRAW", program.id, "triangles", (0, 9), 1)
            observations["raw_dependent_queue"] = [freeze(command) for command in canvas.context.glir._shared._commands]
            batch_start = len(batches)
            canvas.context.flush_commands()
            observations["dependent_explicit_flushes"] = 1
            observations["dependent_parser_calls_with_target_commands"] = sum(
                bool(_target_commands(batch, buffer.id, program.id)) for batch in batches[batch_start:])
        observations["window_end"] = len(runner.commands)
        samples = int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))
        observations.update(physical_samples=max(1, samples),
            sample_source="OpenGL driver GL_SAMPLES" if backend == "pyqt6" else "candidate GL facade/configuration")
        image = runner.read()
        observations.update(readbacks=runner.readbacks, actual_parser_batches=batches)
        return image, runner.commands, runner.shaders, case_contract(name), observations
    finally:
        parser.parse = original
        runner.close()
