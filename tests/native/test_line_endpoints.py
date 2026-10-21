"""Independent logical endpoint criteria and future upstream-only TF admission.

No candidate endpoint API is assumed. Native dispatch, output inspection and
padding/lifetime gates will be bound to a real reviewed interface separately.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools import fixture_line_endpoints as f

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = ROOT / "build/evidence/line-endpoints-authoring-3/authoring.json"


def _queried(name):
    return [{"name": row["name"], "gl_type": row["gl_type"], "array_length": row["array_length"]}
            for row in f.tf_layout(name)["fields"]]


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_typed_logical_values_and_TF_transport_round_trip(name):
    values = f.expected(name)
    spec = f.specification(name)
    count = spec["count"] * spec["instances"]
    for field in spec["fields"]:
        assert values[field.name].shape == (count, *field.shape)
        assert values[field.name].dtype == field.dtype
    encoded = f.encode_tf_for_CPU(name, values)
    assert len(encoded) == count * f.tf_layout(name)["stride"]
    actual = f.decode_tf(name, encoded, _queried(name))
    f.assert_outputs(name, actual)
    assert all(value.flags.owndata for value in actual.values())


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_independent_first_last_and_instance_landmarks(name):
    value = f.expected(name)
    if name == "raw_high_ids":
        np.testing.assert_array_equal(value["v_ids"][[0, 3, 4, 7]],
                                      [[16777217, 0], [16777220, 0], [16777217, 1], [16777220, 1]])
        np.testing.assert_array_equal(value["v_signed"][[0, -1]], [[-2147483648, 2147483647]] * 2)
        np.testing.assert_array_equal(value["v_unsigned"][0], [16777217, 4294967295])
        assert value["gl_Position"][0, 0].view(np.uint32) == 0x80000000
    elif name.startswith("indexed_"):
        np.testing.assert_array_equal(value["v_ids"][:, 0], [3, 1, 3, 0, 3, 1, 3, 0])
        np.testing.assert_array_equal(value["v_ids"][:, 1], [0, 0, 0, 0, 1, 1, 1, 1])
        np.testing.assert_array_equal(value["gl_Position"][0], [1.5, -.25, .375, 1.75])
        np.testing.assert_array_equal(value["v_signed"][0], [-1, 2147483644])
        np.testing.assert_array_equal(value["v_unsigned"][0], [16777220, 4294967292])
    elif name == "interleaved_divisors":
        np.testing.assert_array_equal(value["gl_Position"][0], [1.75, -.1875, .375, 1.75])
        np.testing.assert_array_equal(value["v_ids"][[0, 4, 8]], [[3, 0], [3, 1], [3, 2]])
        np.testing.assert_array_equal(value["v_one"][[0, 4, 8]], [[1, .25], [2, .5], [3, .75]])
        np.testing.assert_array_equal(value["v_two"][[0, 4, 8]], [[-9, 11], [-9, 11], [-8, 12]])
        np.testing.assert_array_equal(value["v_constant"][-1], [7, 4294967294])
    elif name == "globals_early_return":
        np.testing.assert_array_equal(value["v_values"][[0, 4, 11]],
                                      [[2.5, 4.5, 4.5, 3], [2.5, 5.5, 5.5, 3], [6.25, 13.25, -6.25, 3]])
        np.testing.assert_array_equal(value["v_tail"], [10] * 4 + [3] * 4 + [10] * 4)
    elif name == "matrices_arrays":
        np.testing.assert_array_equal(value["gl_Position"][0], [1.3125, -.75, .28125, 1.25])
        np.testing.assert_array_equal(value["v_basis"][0], [[1.5, .5, .25], [-.5, 2.5, .125], [4, -.25, 3.5]])
        np.testing.assert_array_equal(value["v_array"][0], [[.625, 0.], [-.375, 2.25]])
        np.testing.assert_array_equal(value["v_codes"][[0, 3]], [[[1, 0], [-1, 17]], [[1, 1], [-1, 17]]])
    else:
        np.testing.assert_array_equal(value["v_ids"][[0, 63, 64]], [[0, 0], [63, 0], [64, 0]])
        np.testing.assert_array_equal(value["gl_Position"][-1], [8.125, -.25, .5, 1.])
        np.testing.assert_array_equal(value["v_visits"], np.ones(65, np.uint32))


def test_cpu_raw_high_integer_and_signed_zero_require_exact_bits():
    good = f.expected("raw_high_ids")
    for field in ("v_ids", "v_unsigned", "gl_Position"):
        bad = {key: value.copy() for key, value in good.items()}
        if field == "gl_Position": bad[field][0, 0] = 0.
        else: bad[field][:, 0] = bad[field][:, 0].astype(np.float32).astype(np.uint32)
        with pytest.raises(AssertionError):
            f.assert_outputs("raw_high_ids", bad)
    bad = {key: value.copy() for key, value in good.items()}
    bad["v_signed"] = bad["v_signed"].astype(np.int64)
    with pytest.raises(AssertionError): f.assert_outputs("raw_high_ids", bad)


def test_cpu_matrix_transport_is_column_major_and_logical_shape_is_not_native_padding():
    name = "matrices_arrays"
    values, layout = f.expected(name), f.tf_layout(name)
    record = next(row for row in layout["fields"] if row["name"] == "v_basis")
    encoded = f.encode_tf_for_CPU(name, values)
    first_column = np.frombuffer(encoded[record["offset"]:record["offset"] + 12], np.float32)
    np.testing.assert_array_equal(first_column, [1.5, -.5, 4.])
    bad = {key: value.copy() for key, value in values.items()}
    bad["v_basis"] = np.swapaxes(bad["v_basis"], -1, -2).copy()
    with pytest.raises(AssertionError): f.assert_outputs(name, bad)
    assert layout["native_layout"] is False and record["bytes"] == 36


def test_cpu_TF_query_identity_wrong_type_array_size_order_and_truncation_rejected():
    name = "matrices_arrays"
    raw = f.encode_tf_for_CPU(name, f.expected(name))
    for change in ("type", "size", "order"):
        query = _queried(name)
        if change == "type": query[1]["gl_type"] = f.TYPES["vec2"][2]
        elif change == "size": query[-1]["array_length"] = 1
        else: query.reverse()
        with pytest.raises(AssertionError): f.decode_tf(name, raw, query)
    with pytest.raises(AssertionError): f.decode_tf(name, raw[:-4], _queried(name))


def test_cpu_typed_metadata_qualifiers_and_illegal_bool_output_are_explicit():
    spec = f.specification("matrices_arrays")
    fields = {field.name: field for field in spec["fields"]}
    assert fields["v_basis"].glsl_type == "mat3" and fields["v_basis"].qualifier == "flat"
    assert fields["v_array"].array_length == 2 and fields["v_array"].qualifier == "noperspective"
    assert fields["v_codes"].dtype == np.int32 and fields["v_codes"].array_length == 2
    assert spec["uniforms"]["u_flip"] == ("bool", True)
    for args in (("bad", "bool", "flat"), ("bad", "uint", "smooth"), ("bad", "vec2", "smooth", True)):
        with pytest.raises(ValueError): f.Field(*args)


@pytest.mark.parametrize("mode", ("lines", "line_strip", "line_loop"))
def test_cpu_original_segment_references_keep_duplicate_occurrences_and_flat_LAST(mode):
    rows = f.segment_rows("indexed_u8", mode)
    first = {"lines": [[0, 1, 1], [2, 3, 3]],
             "line_strip": [[0, 1, 1], [1, 2, 2], [2, 3, 3]],
             "line_loop": [[0, 1, 1], [1, 2, 2], [2, 3, 3], [3, 0, 0]]}[mode]
    np.testing.assert_array_equal(rows, np.asarray(first + [[a + 4, b + 4, c + 4] for a, b, c in first], np.uint32))
    ids = f.expected("indexed_u8")["v_ids"]
    assert np.all(ids[rows[:, 0], 1] == ids[rows[:, 1], 1])
    np.testing.assert_array_equal(rows[:, 2], rows[:, 1])
    if mode == "line_loop": np.testing.assert_array_equal(ids[rows[3, 2]], [3, 0])


def test_cpu_count65_and_private_initialization_do_not_claim_native_padding_execution():
    spec = f.specification("logical_count65")
    assert spec["original_primitive"] == "line_strip" and spec["count"] == 65
    assert len(f.segment_rows("logical_count65", "line_strip")) == 64
    scope = f.contract()["padded_scope"]
    assert "separate" in scope and "65 logical outputs" in scope
    vertex, fragment = f.shaders("globals_early_return")
    assert "float direct=a_position.x+float(gl_VertexID);" in vertex
    assert "float from_helper=seed(direct);" in vertex
    assert "if(gl_InstanceID%2==1) return;" in vertex
    assert "#define gl_VertexID" not in vertex and "xfb_" not in vertex
    assert "v_values" in fragment and "v_tail" in fragment


def test_cpu_actual_TF_layout_query_rejects_offset_buffer_stride_mode_and_false_types():
    name = "matrices_arrays"
    layout = f.tf_layout(name)
    queried = [{"actual_name": row["name"] + ("[0]" if row["array_length"] > 1 else ""),
                "array_length": row["array_length"], "gl_type": row["gl_type"],
                "offset": row["offset"], "buffer_index": 0} for row in layout["fields"]]
    assert f.validate_tf_query(name, queried, layout["stride"], f.GL_INTERLEAVED_ATTRIBS) == _queried(name)
    for key, value in (("offset", 4), ("buffer_index", 1), ("array_length", True),
                       ("gl_type", f.TYPES["uint"][2]), ("actual_name", "v_basis[0]")):
        bad = [dict(row) for row in queried]
        bad[0][key] = value
        with pytest.raises(AssertionError): f.validate_tf_query(name, bad, layout["stride"], f.GL_INTERLEAVED_ATTRIBS)
    for stride, mode in ((layout["stride"] + 4, f.GL_INTERLEAVED_ATTRIBS),
                         (True, f.GL_INTERLEAVED_ATTRIBS), (layout["stride"], 0)):
        with pytest.raises(AssertionError): f.validate_tf_query(name, queried, stride, mode)


def test_cpu_TF_guard_rejects_extra_missing_or_written_transport_rows():
    name = "logical_count65"
    logical = f.encode_tf_for_CPU(name, f.expected(name))
    tail = b"\xcd" * (4 * f.tf_layout(name)["stride"])
    assert f.validate_tf_bytes(name, logical + tail) == logical
    for bad in (logical + tail[:-1], logical + tail + b"\xcd", logical + b"\x00" + tail[1:]):
        with pytest.raises(AssertionError): f.validate_tf_bytes(name, bad)


def test_cpu_raw_integer_constant_oracle_has_no_public_gloo_admission_claim():
    raw = f.admission_scope("raw_high_ids")
    assert raw["internal_integer_constant_attributes"] == ["a_signed", "a_unsigned"]
    assert f.admission_scope("interleaved_divisors")["internal_integer_constant_attributes"] == ["a_constant"]
    assert f.admission_scope("indexed_u16")["internal_integer_constant_attributes"] == []
    tree = ast.parse((ROOT / "build/oracle-opengl/Lib/site-packages/vispy/gloo/glir.py").read_text(encoding="utf-8"))
    program = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GlirProgram")
    types = next(ast.literal_eval(node.value) for node in program.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "ATYPEMAP" for target in node.targets))
    assert sorted(types) == sorted(raw["public_GLIR_constant_types"])
    assert "not unchanged public gloo DRAW admission" in f.contract()["public_API_scope"]


def test_cpu_oracle_raw_query_API_shapes_and_data_source_are_independent():
    files = {"GL_3_0.py": {"glTransformFeedbackVaryings": ("program", "count", "varyings", "bufferMode"),
                            "glGetTransformFeedbackVarying": ("program", "index", "bufSize", "length", "size", "type", "name")},
             "GL_4_3.py": {"glGetProgramResourceiv": ("program", "programInterface", "index", "propCount", "props", "count", "length", "params")}}
    for filename, wanted in files.items():
        path = ROOT / "build/oracle-opengl/Lib/site-packages/OpenGL/raw/GL/VERSION" / filename
        functions = {node.name: tuple(arg.arg for arg in node.args.args)
                     for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef)}
        assert all(functions[name] == signature for name, signature in wanted.items())
    capture = next(node for node in ast.parse((ROOT / "tools/fixture_line_endpoints.py").read_text(encoding="utf-8")).body
                   if isinstance(node, ast.FunctionDef) and node.name == "capture_upstream")
    calls = {ast.unparse(node.func) for node in ast.walk(capture) if isinstance(node, ast.Call)}
    assert "GL.glGetBufferSubData" in calls and "glGetProgramResourceiv" in calls
    assert "expected" not in calls and "encode_tf_for_CPU" not in calls


def test_cpu_generated_GL_IDs_preserve_exact_single_uint32_scalars_and_arrays():
    for value in (1, 16777217, 4294967295, np.uint32(16777217), np.int64(7),
                  np.asarray(16777217, np.uint32), np.asarray([16777217], np.uint32)):
        expected = int(value[0]) if isinstance(value, np.ndarray) and value.ndim == 1 else int(value)
        assert f.generated_gluint(value, "glGenQueries") == expected


def test_cpu_generated_GL_ID_array_reproduces_pinned_numpy_scalar_failure():
    value = np.asarray([16777217], np.uint32)
    with pytest.raises(TypeError, match="0-dimensional arrays"):
        int(value)
    assert f.generated_gluint(value, "glGenQueries") == 16777217


def test_cpu_generated_GL_IDs_reject_malformed_shapes_types_and_ranges():
    for value in (True, np.bool_(True), 1., "1", [1], (1,), {}, 0, -1, 4294967296,
                  np.asarray([], np.uint32), np.asarray([1, 2], np.uint32),
                  np.asarray([[1]], np.uint32), np.asarray([1.], np.float32),
                  np.asarray([True]), np.asarray([1], object), np.asarray([-1], np.int32),
                  np.asarray([4294967296], np.uint64)):
        with pytest.raises(ValueError, match="glGenQueries"):
            f.generated_gluint(value, "glGenQueries")


def test_cpu_all_generated_GL_object_names_use_validated_single_ID_extraction():
    source = (ROOT / "tools/fixture_line_endpoints.py").read_text(encoding="utf-8")
    capture = next(node for node in ast.parse(source).body
                   if isinstance(node, ast.FunctionDef) and node.name == "capture_upstream")
    parents = {child: node for node in ast.walk(capture) for child in ast.iter_child_nodes(node)}
    calls = [node for node in ast.walk(capture) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
             and node.func.value.id == "GL" and node.func.attr.startswith("glGen")]
    assert sorted(node.func.attr for node in calls) == ["glGenBuffers"] * 3 + [
        "glGenQueries", "glGenTransformFeedbacks", "glGenVertexArrays"]
    assert all(isinstance(parents[node], ast.Call) and ast.unparse(parents[node].func) == "generated"
               and ast.literal_eval(parents[node].args[1]) == node.func.attr for node in calls)


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
def test_upstream_original_vertex_outputs_match_exact_logical_criteria(name):
    authoring = json.loads(AUTHORING.read_text(encoding="utf-8"))
    assert authoring["contract"] == f.contract() and authoring["candidate_seen"] is False
    for path, digest in authoring["sources_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    folder = Path(os.environ["VISPY_LINE_ENDPOINT_EVIDENCE"]) / name
    folder.mkdir(parents=True, exist_ok=False)
    record = {"candidate_seen": False, "GPU_used": False, "case": name}
    vertex, fragment = f.shaders(name)
    (folder / "original.vert").write_text(vertex, encoding="utf-8")
    (folder / "original.frag").write_text(fragment, encoding="utf-8")
    try:
        actual, raw, observed = f.capture_upstream(name, ROOT)
        record.update(observations=observed, GPU_used=True)
        (folder / "actual-TF.bin").write_bytes(raw)
        for key, value in actual.items(): np.save(folder / (key + ".npy"), value, allow_pickle=False)
        f.assert_outputs(name, actual)
        record["exact_logical_outputs"] = True
    except BaseException as error:
        if getattr(error, "endpoint_raw_tf", None) is not None:
            (folder / "actual-TF.bin").write_bytes(error.endpoint_raw_tf)
        record.update(error_type=type(error).__name__, error=str(error),
                      observations=getattr(error, "endpoint_observations", record.get("observations")))
        record["GPU_used"] = (record["observations"] or {}).get("GPU_used", record["GPU_used"])
        raise
    finally:
        (folder / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
