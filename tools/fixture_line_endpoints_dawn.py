"""Independent decoding and internal command transport for admitted D1 outputs.

This module imports no renderer. Expected logical arrays and original shaders
come from the immutable, upstream-admitted D1 packet. Native reflected offsets
are transport metadata, never expected-value oracles. Raw integer constants
exercise the private typed ABI, not upstream public gloo constant setters.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "build/evidence/line-endpoints-authoring-3"
REFERENCE = ROOT / "tests/reference/line-endpoints-opengl-2"
AUTHOR_SHA = "ab49cb8b6c323cfc2c20e09ade811117a6704f42aa0942725535f911d75479ac"
REFERENCE_SHA = "4f7ca3b0bee93c6c3c71d63bb3ada64e2f21716ef6691870c5182ce4c1d6712d"
CASES = ("raw_high_ids", "indexed_u8", "indexed_u16", "indexed_u32",
         "interleaved_divisors", "globals_early_return", "matrices_arrays", "logical_count65")
WORKGROUP = 64
CANARY = 0xCD
TYPES = {"float": ("<f4", ()), "vec2": ("<f4", (2,)), "vec4": ("<f4", (4,)),
         "mat3": ("<f4", (3, 3)), "int": ("<i4", ()), "ivec2": ("<i4", (2,)),
         "uint": ("<u4", ()), "uvec2": ("<u4", (2,))}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _int(value, label, minimum=0):
    assert type(value) is int and value >= minimum, label
    return value


def load_case(name):
    """Verify fixed authoring, successful upstream outputs and exact inputs."""
    assert name in CASES
    assert sha(AUTHOR / "authoring.json") == AUTHOR_SHA
    author = read(AUTHOR / "authoring.json")
    assert sha(REFERENCE / "terminal.json") == REFERENCE_SHA
    terminal = read(REFERENCE / "terminal.json")
    assert terminal["process_exit"] == 0 and terminal["admitted"] == 8 and terminal["unresolved"] == 0
    contract = author["contract"]["cases"][name]
    checked = {str(AUTHOR / "authoring.json"): AUTHOR_SHA,
               str(REFERENCE / "terminal.json"): REFERENCE_SHA}
    arrays = {}
    for key, metadata in author["expected_and_input_arrays"].items():
        if not key.startswith(name + "/"):
            continue
        path = AUTHOR / key
        assert sha(path) == metadata["file_sha256"]
        value = np.load(path, allow_pickle=False)
        assert list(value.shape) == metadata["shape"] and value.dtype.str == metadata["dtype"]
        assert repr(value.dtype.descr) == metadata["dtype_descriptor"]
        assert hashlib.sha256(value.tobytes()).hexdigest() == metadata["sha256"]
        value.flags.writeable = False
        arrays[Path(key).stem] = value
        checked[str(path)] = metadata["file_sha256"]
    shaders = []
    for suffix in ("vert", "frag"):
        key = name + "/original." + suffix
        path = AUTHOR / key
        assert sha(path) == author["original_shader_files"][key]
        shaders.append(path.read_text(encoding="utf-8"))
        checked[str(path)] = sha(path)
    record_key = name + "/record.json"
    record_path = REFERENCE / record_key
    assert sha(record_path) == terminal["artifacts"][record_key]
    record = read(record_path)
    assert record["process_exit"] == 0 and record["exact_logical_outputs"] is True
    assert record["GPU_used"] is True and record["native_imported"] is False
    assert record["observations"]["cleanup_errors"] == []
    checked[str(record_path)] = terminal["artifacts"][record_key]
    expected = {}
    for key in contract["logical_outputs"]:
        expected[key] = arrays["expected-" + key]
        path_key = name + "/" + key + ".npy"
        path = REFERENCE / path_key
        assert sha(path) == terminal["artifacts"][path_key]
        upstream = np.load(path, allow_pickle=False)
        exact(expected[key], upstream)
        checked[str(path)] = terminal["artifacts"][path_key]
    return {"name": name, "contract": contract, "arrays": arrays, "expected": expected,
            "vertex": shaders[0], "fragment": shaders[1], "checked_inputs": checked}


def exact(wanted, actual):
    """Compare every typed bit, including negative zero and high integer IDs."""
    assert isinstance(actual, np.ndarray) and actual.dtype == wanted.dtype
    assert actual.shape == wanted.shape
    assert np.ascontiguousarray(actual).tobytes() == np.ascontiguousarray(wanted).tobytes(), "exact typed bits"


def blob(value):
    value = np.ascontiguousarray(value)
    return {"__bytes__": value.tobytes(), "shape": list(value.shape), "dtype": value.dtype.str}


def _attribute_type(value):
    value = np.asarray(value)
    scalar = {"f": "float", "i": "int", "u": "uint"}[value.dtype.kind]
    assert value.dtype.itemsize == 4
    width = int(np.prod(value.shape[1:])) if value.ndim > 1 else 1
    assert 1 <= width <= 4
    return scalar if width == 1 else {"float": "vec", "int": "ivec", "uint": "uvec"}[scalar] + str(width)


def commands(case, first_id):
    """Actual private execute() syntax, with original typed payloads unchanged.

    Matrix uniform transport is column-major; the admitted logical matrix is
    still row,column. Raw integer ATTRIBUTE constants remain Python integers.
    """
    _int(first_id, "positive object ID", 1)
    c, arrays = case["contract"], case["arrays"]
    program, vert, frag = first_id, first_id + 1, first_id + 2
    result = [("CREATE", program, "Program"), ("CREATE", vert, "VertexShader"),
              ("CREATE", frag, "FragmentShader"), ("DATA", vert, 0, case["vertex"]),
              ("DATA", frag, 0, case["fragment"]), ("ATTACH", program, vert),
              ("ATTACH", program, frag), ("LINK", program)]
    owners = [program, vert, frag]
    buffers = {}
    for key in c["buffers"]:
        owner = first_id + len(owners)
        owners.append(owner)
        buffers[key] = owner
        value = arrays["input-buffer-" + key]
        result.extend([("CREATE", owner, "VertexBuffer"), ("SIZE", owner, value.nbytes),
                       ("DATA", owner, 0, blob(value))])
    for key, attribute in c["attributes"].items():
        if "constant" in attribute:
            value = arrays["input-constant-" + key]
            dtype = _attribute_type(value[None])
            carrier = [0, *(float(v) if value.dtype.kind == "f" else int(v) for v in value)]
            result.append(("ATTRIBUTE", program, key, dtype, carrier, 0))
        else:
            value = arrays["input-buffer-" + attribute["buffer"]]
            if "field" in attribute:
                field = attribute["field"]
                offset = value.dtype.fields[field][1]
                field_value = value[field]
            else:
                offset, field_value = 0, value
            stride = value.strides[0]
            result.append(("ATTRIBUTE", program, key, _attribute_type(field_value),
                           [buffers[attribute["buffer"]], stride, offset], attribute["divisor"]))
    for key, uniform in c["uniforms"].items():
        kind = uniform["type"]
        if isinstance(uniform["value"], dict):
            value = arrays["input-uniform-" + key]
            if kind.startswith("mat"):
                value = value.T.copy()
        else:
            dtype = np.bool_ if kind == "bool" else np.uint32 if kind == "uint" else np.int32
            value = np.asarray([uniform["value"]], dtype=dtype)
        result.append(("UNIFORM", program, key, kind, blob(value)))
    selection = c["selection"]
    if c["index"] is not None:
        owner = first_id + len(owners)
        owners.append(owner)
        index = arrays["input-indices"]
        result.extend([("CREATE", owner, "IndexBuffer"), ("SIZE", owner, index.nbytes),
                       ("DATA", owner, 0, blob(index))])
        draw_selection = [owner, {1: "unsigned_byte", 2: "unsigned_short", 4: "unsigned_int"}[index.dtype.itemsize], selection["count"]]
    else:
        draw_selection = [selection["first"], selection["count"]]
    draw = ("DRAW", program, selection["original_primitive"], draw_selection, selection["instances"])
    return result, draw, [("DELETE", owner) for owner in reversed(owners)]


def decode(record, case):
    """Read typed logical fields from supplied reflection; no native layout fit."""
    assert record["status"] == "completed" and record["error"] == ""
    for key in ("capture_id", "ticket_id", "device_generation"):
        _int(record[key], key, 1)
    assert isinstance(record["evaluator_key"], str) and record["evaluator_key"]
    rows = _int(record["rows"], "rows", 1)
    width = _int(record["row_bytes"], "row_bytes", 16)
    assert width % 4 == 0
    selection = case["contract"]["selection"]
    selected_rows = selection["count"]
    if "chunks" in record and selection["original_primitive"] == "lines":
        selected_rows = selected_rows // 2 * 2
    assert rows == selected_rows * selection["instances"]
    data, raw = record["data"], record["raw_data"]
    assert isinstance(data, np.ndarray) and data.dtype == np.uint8 and data.shape == (rows, width)
    assert data.flags.c_contiguous
    assert isinstance(raw, np.ndarray) and raw.dtype == np.uint8 and raw.ndim == 1 and raw.flags.c_contiguous
    if "chunks" in record:
        _chunk_allocations(record, rows, width, data, raw)
    else:
        padded = ((rows + WORKGROUP - 1) // WORKGROUP) * WORKGROUP
        assert raw.size == padded * width + 16, "complete padded allocation and canary"
        assert np.array_equal(raw[:rows * width], data.reshape(-1))
        assert np.all(raw[rows * width:] == CANARY), "inactive rows and trailing canary"
    assert not np.shares_memory(data, raw), "logical/raw storage independently retained"
    wanted = {field["name"]: field for field in case["contract"]["GL_TF_transport_only"]["fields"]}
    fields = record["fields"]
    assert isinstance(fields, list) and len(fields) == len(wanted)
    names = [field["name"] for field in fields]
    assert len(set(names)) == len(names) and set(names) == set(wanted)
    occupied, result = [], {}
    for field in fields:
        declared = wanted[field["name"]]
        assert field["type"] == declared["glsl_type"]
        assert field["interpolation"] == ("" if field["name"] == "gl_Position" else declared["qualifier"])
        offset = _int(field["offset"], "field offset")
        size = _int(field["size"], "field size", 4)
        astride = _int(field["array_stride"], "array stride")
        mstride = _int(field["matrix_stride"], "matrix stride")
        array_size = _int(field["array_size"], "array size")
        length = declared["array_length"]
        assert array_size == (length if length > 1 else 0)
        assert offset % 4 == size % 4 == astride % 4 == mstride % 4 == 0
        assert offset + size <= width
        assert all(offset + size <= a or b <= offset for a, b in occupied), "overlapping fields"
        occupied.append((offset, offset + size))
        dtype, tail = TYPES[field["type"]]
        matrix = len(tail) == 2
        components = tail[0] if tail else 1
        if matrix:
            assert mstride >= components * 4
            element = mstride * tail[1]
        else:
            assert mstride == 0
            element = components * 4
        if length > 1:
            assert astride >= element and size == astride * length
        else:
            assert astride == 0 and size == element
        if field["name"] == "gl_Position":
            assert offset == 0 and size == 16
        logical = np.empty((rows, *declared["shape"]), dtype=np.dtype(dtype))
        for row in range(rows):
            for element_index in range(length):
                start = offset + element_index * astride
                target = logical[row, element_index] if length > 1 else logical[row]
                if matrix:
                    for column in range(tail[1]):
                        target[:, column] = np.frombuffer(data[row, start + column * mstride:start + column * mstride + components * 4], dtype=dtype)
                elif tail:
                    target[...] = np.frombuffer(data[row, start:start + components * 4], dtype=dtype)
                elif length > 1:
                    logical[row, element_index] = np.frombuffer(data[row, start:start + 4], dtype=dtype)[0]
                else:
                    logical[row] = np.frombuffer(data[row, start:start + 4], dtype=dtype)[0]
        exact(case["expected"][field["name"]], logical)
        result[field["name"]] = logical
    return result


def _chunk_allocations(record, rows, width, data, raw):
    """Validate actual per-dispatch captures before endpoint carry copies.

    Fresh evaluated prefixes supply the logical rows. Shared endpoint slots are
    still canaries at this capture phase, even when the later render table is
    larger than the fresh prefix. A closing-only loop chunk maps no allocation.
    """
    assert record.get("capture_phase") == "evaluated_before_carry", "chunk capture phase"
    chunks = record["chunks"]
    assert isinstance(chunks, list) and chunks, "nonempty chunk descriptors"
    u32, u64 = (1 << 32) - 1, (1 << 64) - 1
    assert rows <= u32 and width <= u32, "chunk dimensions fit the native ABI"
    next_row, next_raw = 0, 0
    keys = {"first_row", "rows", "output_rows", "raw_offset", "raw_bytes"}
    for chunk in chunks:
        assert isinstance(chunk, dict) and set(chunk) == keys, "complete chunk descriptor"
        first = _int(chunk["first_row"], "chunk first row")
        count = _int(chunk["rows"], "chunk rows")
        output = _int(chunk["output_rows"], "chunk output rows")
        offset = _int(chunk["raw_offset"], "chunk raw offset")
        extent = _int(chunk["raw_bytes"], "chunk raw bytes")
        assert first <= u32 and count <= u32 and output <= u32
        assert offset <= u64 and extent <= u64
        assert first == next_row and count <= rows - next_row, "ordered logical coverage"
        assert offset == next_raw and extent <= u64 - offset, "ordered raw allocations"
        assert count <= output <= count + 2, "render output contains only its evaluated prefix and endpoint carries"
        if count:
            padded = ((count + WORKGROUP - 1) // WORKGROUP) * WORKGROUP
            expected = max(padded * width + 16, output * width)
            assert expected <= u64 and extent == expected, "complete chunk allocation"
            assert extent <= raw.size - offset, "mapped chunk allocation bounds"
            prefix = count * width
            assert np.array_equal(raw[offset:offset + prefix], data[first:first + count].reshape(-1)), "chunk evaluated prefix"
            assert np.all(raw[offset + prefix:offset + extent] == CANARY), "inactive chunk rows and trailing canary"
        else:
            assert output == 2 and extent == 0, "closing-only loop chunk has no mapped allocation"
        next_row += count
        next_raw += extent
    assert next_row == rows and next_raw == raw.size, "complete logical and raw coverage"


def rejected(record):
    """A terminal failure cannot expose successful logical data."""
    assert record["status"] not in {"completed", "pending", "encoded", "submitted", "retired", "empty"}
    assert isinstance(record["error"], str) and record["error"]
    data, raw = record["data"], record["raw_data"]
    assert isinstance(data, np.ndarray) and data.dtype == np.uint8 and data.shape == (0,)
    assert isinstance(raw, np.ndarray) and raw.dtype == np.uint8 and raw.ndim == 1


def context_header(path, expected, checksum, activation, epoch):
    assert type(epoch) is int and epoch >= 31, "matching future epoch before native import"
    assert Path(path).resolve() == ROOT / f"build/evidence/native-pass-{epoch}/activation.json"
    assert isinstance(expected, str) and len(expected) == 64 and set(expected) <= set("0123456789abcdef")
    assert checksum == expected
    assert type(activation.get("epoch")) is int and activation["epoch"] == epoch


def activation_before_native(env):
    raw = env.get("VISPY_LINE_ENDPOINTS_EPOCH", "")
    assert raw.isdecimal() and str(int(raw)) == raw
    epoch = int(raw)
    path = Path(env.get("VISPY_LINE_ENDPOINTS_ACTIVATION", "")).resolve()
    expected = env.get("VISPY_LINE_ENDPOINTS_ACTIVATION_SHA256", "")
    # Canonical path/epoch rejection occurs before any project or native import.
    assert epoch >= 31 and path == ROOT / f"build/evidence/native-pass-{epoch}/activation.json"
    activation = read(path)
    context_header(path, expected, sha(path), activation, epoch)
    handoff_path = ROOT / f"build/evidence/native-pass-{epoch}-build-handoff-1/result.json"
    handoff_sha = env.get("VISPY_LINE_ENDPOINTS_HANDOFF_SHA256", "")
    assert len(handoff_sha) == 64 and set(handoff_sha) <= set("0123456789abcdef")
    assert sha(handoff_path) == handoff_sha
    handoff = read(handoff_path)
    assert handoff["status"] == "passed_read_only_terminal_build_handoff"
    assert type(handoff["process_exit"]) is int and handoff["process_exit"] == 0
    assert handoff["native_binary_hashes"] == activation["activated"]
    assert handoff["source_tree_sha256"] == activation["native_source_tree_sha256"]
    assert handoff["proof_input_hashes"] == activation["proof_input_hashes"]
    for name, digest in activation["proof_input_hashes"].items():
        assert sha(path.parent / name) == digest
    frozen = read(path.parent / "frozen-inputs.json")
    assert type(frozen["epoch"]) is int and frozen["epoch"] == epoch
    assert frozen["source_tree_sha256"] == handoff["source_tree_sha256"]
    assert len(activation["activated"]) == 4
    for name, digest in activation["activated"].items():
        base = ROOT / ("src/vispy/visuals/text" if name.startswith("_sdf_cpu.") else "src/vispy")
        assert sha(base / name) == digest
    return {"epoch": epoch, "path": str(path), "sha256": expected,
            "handoff_sha256": handoff_sha, "activation": activation}
