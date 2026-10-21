"""Original vertex outputs, with logical criteria independent of native storage.

The future OpenGL oracle compiles these exact vertex sources and selects named
outputs using transform feedback. POINTS with rasterizer discard is an isolated
invocation transport, not a qualification of original line rasterization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import numpy as np

SPEC = "https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf"
GLSL_SPEC = "https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.4.60.html"
GL_INTERLEAVED_ATTRIBS = 0x8C8C
CASES = ("raw_high_ids", "indexed_u8", "indexed_u16", "indexed_u32",
         "interleaved_divisors", "globals_early_return", "matrices_arrays", "logical_count65")
TYPES = {
    "float": ("<f4", (), 0x1406), "vec2": ("<f4", (2,), 0x8B50),
    "vec4": ("<f4", (4,), 0x8B52), "mat3": ("<f4", (3, 3), 0x8B5B),
    "int": ("<i4", (), 0x1404), "ivec2": ("<i4", (2,), 0x8B53),
    "uint": ("<u4", (), 0x1405), "uvec2": ("<u4", (2,), 0x8DC6),
}


@dataclass(frozen=True)
class Field:
    name: str
    glsl_type: str
    qualifier: str = "smooth"
    array_length: int = 1

    def __post_init__(self):
        if self.glsl_type not in TYPES or self.qualifier not in ("flat", "smooth", "noperspective"):
            raise ValueError("Only declared float/int/uint output types and qualifiers are legal")
        if type(self.array_length) is not int or self.array_length < 1:
            raise ValueError("Exact positive array length required")
        if TYPES[self.glsl_type][0] != "<f4" and self.qualifier != "flat":
            raise ValueError("Integer vertex-to-fragment interfaces must be flat")

    @property
    def shape(self):
        tail = TYPES[self.glsl_type][1]
        return ((self.array_length,) + tail) if self.array_length > 1 else tail

    @property
    def components(self):
        return int(np.prod(self.shape, dtype=np.int64)) if self.shape else 1

    @property
    def dtype(self):
        return np.dtype(TYPES[self.glsl_type][0])


CLIP = Field("gl_Position", "vec4")
IDS = Field("v_ids", "uvec2", "flat")


def array_record(value):
    value = np.asarray(value)
    return {"dtype": value.dtype.str, "dtype_descriptor": repr(value.dtype.descr),
            "shape": list(value.shape), "sha256": hashlib.sha256(value.tobytes()).hexdigest()}


def _positions(count):
    q = np.arange(count, dtype=np.float32)
    return np.column_stack((q * .5, np.where(q.astype(np.int32) % 2, -.25, .25),
                            q * .125, 1. + q * .25)).astype(np.float32)


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    spec = {"name": name, "first": 0, "count": 4, "instances": 2,
            "index": None, "buffers": {}, "attributes": {}, "uniforms": {},
            "original_primitive": "line_strip", "oracle_primitive": "points", "rasterizer_discard": True}
    basic = [CLIP, IDS, Field("v_signed", "ivec2", "flat"),
             Field("v_unsigned", "uvec2", "flat"), Field("v_raw", "vec4")]
    if name == "raw_high_ids":
        spec["first"] = 16777217
        spec["attributes"] = {
            "a_position": {"constant": np.asarray([-.0, -.25, .5, 1.], np.float32)},
            "a_signed": {"constant": np.asarray([-2147483648, 2147483647], np.int32)},
            "a_unsigned": {"constant": np.asarray([16777217, 4294967295], np.uint32)},
        }
        spec["fields"] = basic
    elif name.startswith("indexed_") or name == "interleaved_divisors":
        count = 8 if name.startswith("indexed_") else 7
        data = np.empty(count, dtype=[("position", "<f4", (4,)), ("signed", "<i4", (2,)),
                                     ("unsigned", "<u4", (2,))])
        q = np.arange(count, dtype=np.int64)
        data["position"] = _positions(count)
        data["signed"] = np.column_stack((q - 4, 2147483647 - q)).astype(np.int32)
        data["unsigned"] = np.column_stack((16777217 + q, 4294967295 - q)).astype(np.uint32)
        spec["buffers"]["vertex"] = data
        spec["attributes"] = {"a_" + key: {"buffer": "vertex", "field": key, "divisor": 0}
                              for key in ("position", "signed", "unsigned")}
        spec["fields"] = basic
        if name.startswith("indexed_"):
            dtype = {"indexed_u8": np.uint8, "indexed_u16": np.uint16, "indexed_u32": np.uint32}[name]
            spec["index"] = np.asarray([3, 1, 3, 0], dtype=dtype)
        else:
            spec.update(first=3, instances=3)
            instance = np.empty(3, dtype=[("one", "<f4", (2,)), ("two", "<i4", (2,))])
            instance["one"] = [[1., .25], [2., .5], [3., .75]]
            instance["two"] = [[-9, 11], [-8, 12], [-7, 13]]
            spec["buffers"]["instance"] = instance
            spec["attributes"].update(a_one={"buffer": "instance", "field": "one", "divisor": 1},
                                      a_two={"buffer": "instance", "field": "two", "divisor": 2},
                                      a_constant={"constant": np.asarray([7, 4294967294], np.uint32)})
            spec["fields"] += [Field("v_one", "vec2", "noperspective"),
                               Field("v_two", "ivec2", "flat"), Field("v_constant", "uvec2", "flat")]
    elif name == "globals_early_return":
        q = np.arange(6, dtype=np.float32)
        position = np.column_stack((q * .25, np.where(q.astype(np.int32) % 2, -.5, .5),
                                    np.full(6, -.25), np.ones(6))).astype(np.float32)
        spec.update(first=2, instances=3)
        spec["buffers"]["vertex"] = position
        spec["attributes"] = {"a_position": {"buffer": "vertex", "divisor": 0}}
        spec["fields"] = [CLIP, IDS, Field("v_values", "vec4"), Field("v_tail", "float", "flat")]
    elif name == "matrices_arrays":
        spec.update(first=1, count=3)
        spec["buffers"]["vertex"] = _positions(4)
        spec["attributes"] = {"a_position": {"buffer": "vertex", "divisor": 0}}
        spec["uniforms"] = {
            "u_transform": ("mat4", np.asarray([[2, 0, 0, .25], [0, .5, 0, -.5],
                                                [0, 0, 1, .125], [0, 0, 0, 1]], np.float32)),
            "u_basis": ("mat3", np.asarray([[1, .5, .25], [-.5, 2, .125], [4, -.25, 3]], np.float32)),
            "u_offsets": ("vec2[2]", np.asarray([[.125, .25], [-.5, 1.]], np.float32)),
            "u_flip": ("bool", True), "u_flags": ("uint", 17),
        }
        spec["fields"] = [CLIP, IDS, Field("v_basis", "mat3", "flat"),
                          Field("v_array", "vec2", "noperspective", 2), Field("v_codes", "ivec2", "flat", 2)]
    else:
        spec.update(count=65, instances=1)
        spec["attributes"] = {"a_position": {"constant": np.asarray([.125, -.25, .5, 1.], np.float32)}}
        spec["fields"] = [CLIP, IDS, Field("v_visits", "uint", "flat")]
    return spec


def rows(name):
    spec = specification(name)
    selected = spec["index"] if spec["index"] is not None else np.arange(spec["first"], spec["first"] + spec["count"], dtype=np.uint32)
    return np.tile(selected.astype(np.uint32), spec["instances"]), np.repeat(np.arange(spec["instances"], dtype=np.uint32), spec["count"])


def attribute_rows(spec, name):
    vertex, instance = rows(spec["name"])
    attribute = spec["attributes"][name]
    if "constant" in attribute:
        return np.repeat(attribute["constant"][None], len(vertex), axis=0)
    value = spec["buffers"][attribute["buffer"]]
    if "field" in attribute:
        value = value[attribute["field"]]
    indices = instance // attribute["divisor"] if attribute["divisor"] else vertex
    return value[indices].copy()


def expected(name):
    spec = specification(name)
    vertex, instance = rows(name)
    p = attribute_rows(spec, "a_position")
    result = {"gl_Position": p.copy(), "v_ids": np.column_stack((vertex, instance)).astype(np.uint32)}
    if name in ("raw_high_ids", "indexed_u8", "indexed_u16", "indexed_u32", "interleaved_divisors"):
        result.update(v_signed=attribute_rows(spec, "a_signed"), v_unsigned=attribute_rows(spec, "a_unsigned"), v_raw=p.copy())
        if name == "interleaved_divisors":
            one = attribute_rows(spec, "a_one")
            result["gl_Position"][:, :2] += one * np.float32(.25)
            result.update(v_one=one, v_two=attribute_rows(spec, "a_two"), v_constant=attribute_rows(spec, "a_constant"))
    elif name == "globals_early_return":
        direct = (p[:, 0] + vertex.astype(np.float32)).astype(np.float32)
        helper = (direct + (vertex % 13).astype(np.float32) + (instance % 7).astype(np.float32)).astype(np.float32)
        conditional = np.where(p[:, 1] > 0, helper, -direct).astype(np.float32)
        result.update(v_values=np.column_stack((direct, helper, conditional, np.full(len(vertex), 3, np.float32))).astype(np.float32),
                      v_tail=np.where(instance % 2, 3., 10.).astype(np.float32))
    elif name == "matrices_arrays":
        uniform = spec["uniforms"]
        result["gl_Position"] = (p @ uniform["u_transform"][1].T).astype(np.float32)
        result["v_basis"] = np.repeat(uniform["u_basis"][1][None], len(vertex), axis=0)
        result["v_basis"] += vertex[:, None, None].astype(np.float32) * np.float32(.5) * np.eye(3, dtype=np.float32)[None]
        result["v_array"] = np.stack((p[:, :2] + uniform["u_offsets"][1][0], p[:, 2:] + uniform["u_offsets"][1][1]), axis=1).astype(np.float32)
        result["v_codes"] = np.stack((np.column_stack((vertex, instance)).astype(np.int32),
                                       np.column_stack((-vertex.astype(np.int32), np.full(len(vertex), 17, np.int32)))), axis=1)
    else:
        result["gl_Position"][:, 0] += vertex.astype(np.float32) * np.float32(.125)
        result["v_visits"] = np.ones(len(vertex), np.uint32)
    return result


def shaders(name):
    spec = specification(name)
    outputs = "\n".join(f"{field.qualifier} out {field.glsl_type} {field.name}" +
                        (f"[{field.array_length}]" if field.array_length > 1 else "") + ";"
                        for field in spec["fields"] if field.name != "gl_Position")
    if name in ("raw_high_ids", "indexed_u8", "indexed_u16", "indexed_u32", "interleaved_divisors"):
        inputs = "in vec4 a_position; in ivec2 a_signed; in uvec2 a_unsigned;"
        body = "gl_Position=a_position; v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID)); v_signed=a_signed; v_unsigned=a_unsigned; v_raw=a_position;"
        if name == "interleaved_divisors":
            inputs += " in vec2 a_one; in ivec2 a_two; in uvec2 a_constant;"
            body += " gl_Position.xy+=a_one*.25; v_one=a_one; v_two=a_two; v_constant=a_constant;"
        vertex = f"#version 330\n{inputs}\n{outputs}\nvoid main(){{{body}}}\n"
    elif name == "globals_early_return":
        vertex = f"""#version 330
in vec4 a_position;
{outputs}
float private_state=2.;
float seed(float value) {{ private_state+=1.; return value+float(gl_VertexID%13)+float(gl_InstanceID%7); }}
float direct=a_position.x+float(gl_VertexID);
float from_helper=seed(direct);
float conditional=a_position.y>0.?from_helper:-direct;
void main() {{
    gl_Position=a_position; v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID));
    v_values=vec4(direct,from_helper,conditional,private_state); v_tail=private_state;
    if(gl_InstanceID%2==1) return;
    private_state+=7.; v_tail=private_state;
}}
"""
    elif name == "matrices_arrays":
        vertex = f"""#version 330
in vec4 a_position;
uniform mat4 u_transform; uniform mat3 u_basis; uniform vec2 u_offsets[2];
uniform bool u_flip; uniform uint u_flags;
{outputs}
void main() {{
    gl_Position=u_transform*a_position; v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID));
    v_basis=u_basis+mat3(float(gl_VertexID)*.5);
    v_array[0]=a_position.xy+u_offsets[0]; v_array[1]=a_position.zw+u_offsets[1];
    v_codes[0]=ivec2(gl_VertexID,gl_InstanceID);
    v_codes[1]=ivec2(u_flip?-gl_VertexID:gl_VertexID,int(u_flags));
}}
"""
    else:
        vertex = f"""#version 330
in vec4 a_position;
{outputs}
float private_state=0.;
void main() {{ private_state+=1.; gl_Position=a_position+vec4(float(gl_VertexID)*.125,0.,0.,0.);
v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID)); v_visits=uint(private_state); }}
"""
    fragment_inputs = outputs.replace(" out ", " in ")
    terms = []
    for field in spec["fields"]:
        if field.name == "gl_Position": continue
        expr = field.name + ("[0]" if field.array_length > 1 else "")
        tail = TYPES[field.glsl_type][1]
        expr += "[0][0]" if len(tail) == 2 else ".x" if tail else ""
        terms.append(f"float({expr})")
    fragment = "#version 330\n" + fragment_inputs + "\nout vec4 color;\nvoid main(){float value=" + "+".join(terms) + "; color=vec4(value*.00001,0.,0.,1.);}\n"
    return vertex, fragment


def tf_layout(name):
    """GL transform feedback transport: packed 32-bit scalar components only."""
    offset, fields = 0, []
    for field in specification(name)["fields"]:
        fields.append({**asdict(field), "dtype": field.dtype.str, "shape": list(field.shape),
                       "gl_type": TYPES[field.glsl_type][2], "offset": offset, "bytes": field.components * 4})
        offset += field.components * 4
    return {"fields": fields, "stride": offset, "native_layout": False,
            "matrix_transport": "columns contiguous; decoded logical arrays use row,column"}


def encode_tf_for_CPU(name, values):
    """CPU transport regression helper, never a replacement for actual GL data."""
    layout = tf_layout(name)
    count = len(rows(name)[0])
    packed = np.empty((count, layout["stride"]), np.uint8)
    for field in specification(name)["fields"]:
        value = values[field.name]
        if field.glsl_type == "mat3": value = np.swapaxes(value, -1, -2)
        raw = np.ascontiguousarray(value).view(np.uint8).reshape(count, -1)
        record = next(row for row in layout["fields"] if row["name"] == field.name)
        packed[:, record["offset"]:record["offset"] + record["bytes"]] = raw
    return packed.tobytes()


def decode_tf(name, raw, queried):
    layout = tf_layout(name)
    assert queried == [{"name": row["name"], "array_length": row["array_length"], "gl_type": row["gl_type"]}
                       for row in layout["fields"]], "Exact queried TF outputs required"
    count = len(rows(name)[0])
    assert len(raw) == count * layout["stride"]
    packed = np.frombuffer(raw, np.uint8).reshape(count, layout["stride"])
    result = {}
    for row in layout["fields"]:
        value = np.ascontiguousarray(packed[:, row["offset"]:row["offset"] + row["bytes"]])
        value = value.view(np.dtype(row["dtype"])).reshape((count, *row["shape"]))
        if row["glsl_type"] == "mat3": value = np.swapaxes(value, -1, -2)
        result[row["name"]] = value.copy()
    return result


def validate_tf_query(name, queried, stride, mode):
    """Validate actual API query data for GL transport, never native padding."""
    layout = tf_layout(name)
    assert type(stride) is int and stride == layout["stride"]
    assert type(mode) is int and mode == GL_INTERLEAVED_ATTRIBS
    assert len(queried) == len(layout["fields"])
    normalized = []
    for actual, wanted in zip(queried, layout["fields"]):
        assert all(type(actual[key]) is int for key in ("array_length", "gl_type", "offset", "buffer_index"))
        actual_name = actual["actual_name"]
        allowed_names = {wanted["name"]}
        if wanted["array_length"] > 1:
            allowed_names.add(wanted["name"] + "[0]")
        assert actual_name in allowed_names
        assert actual["array_length"] == wanted["array_length"] and actual["gl_type"] == wanted["gl_type"]
        assert actual["offset"] == wanted["offset"] and actual["buffer_index"] == 0
        normalized.append({"name": wanted["name"], "array_length": actual["array_length"], "gl_type": actual["gl_type"]})
    return normalized


def validate_tf_bytes(name, raw, guard_rows=4):
    """The rawGL transport has exactly logical rows followed by a byte canary."""
    assert type(guard_rows) is int and guard_rows > 0
    stride = tf_layout(name)["stride"]
    logical_bytes = len(rows(name)[0]) * stride
    assert len(raw) == logical_bytes + guard_rows * stride
    assert raw[logical_bytes:] == b"\xcd" * (guard_rows * stride), "Actual GL TF tail sentinel changed"
    return raw[:logical_bytes]


def admission_scope(name):
    integer_constants = [label for label, binding in specification(name)["attributes"].items()
                         if "constant" in binding and binding["constant"].dtype.kind in "iu"]
    return {"transport": "original shader/raw GL transform feedback; no public Program.draw admission",
            "internal_integer_constant_attributes": integer_constants,
            "integer_constant_scope": "internal typed compiler/evaluator ABI probe; public upstream GLIR constant setters support float/vec only",
            "public_GLIR_constant_types": ["float", "vec2", "vec3", "vec4"],
            "logical_criteria_independent_of_native_padding": True}


def assert_outputs(name, actual):
    wanted = expected(name)
    assert set(actual) == set(wanted)
    for key, value in wanted.items():
        found = actual[key]
        assert found.dtype == value.dtype and found.shape == value.shape, (name, key)
        # Original finite values are binary-exact; preserve -0 and integer bits.
        np.testing.assert_array_equal(found.view(np.uint32), value.view(np.uint32), err_msg=f"{name}: {key}")


def segment_rows(name, primitive):
    spec = specification(name)
    if primitive not in ("lines", "line_strip", "line_loop"):
        raise ValueError(primitive)
    count = spec["count"]
    result = []
    for instance in range(spec["instances"]):
        base = instance * count
        pairs = range(0, count - 1, 2) if primitive == "lines" else range(count - 1)
        result.extend((base + row, base + row + 1, base + row + 1) for row in pairs)
        if primitive == "line_loop" and count > 1:
            result.append((base + count - 1, base, base))
    return np.asarray(result, dtype=np.uint32).reshape(-1, 3)


def contract():
    cases = {}
    for name in CASES:
        spec = specification(name)
        vertex, fragment = shaders(name)
        cases[name] = {
            "admission_scope": admission_scope(name),
            "selection": {key: spec[key] for key in ("first", "count", "instances", "original_primitive", "oracle_primitive", "rasterizer_discard")},
            "index": None if spec["index"] is None else array_record(spec["index"]),
            "buffers": {key: array_record(value) for key, value in spec["buffers"].items()},
            "attributes": {key: {**{k: v for k, v in value.items() if k != "constant"},
                                  **({"constant": array_record(value["constant"])} if "constant" in value else {})}
                           for key, value in spec["attributes"].items()},
            "uniforms": {key: {"type": kind, "value": array_record(value) if isinstance(value, np.ndarray) else value}
                         for key, (kind, value) in spec["uniforms"].items()},
            "vertex_sha256": hashlib.sha256(vertex.encode()).hexdigest(),
            "fragment_sha256": hashlib.sha256(fragment.encode()).hexdigest(),
            "logical_outputs": {key: array_record(value) for key, value in expected(name).items()},
            "GL_TF_transport_only": tf_layout(name),
            "segment_rows": {mode: array_record(segment_rows(name, mode)) for mode in ("lines", "line_strip", "line_loop")},
        }
    return {"schema": 1, "candidate_seen": False, "GPU_used": False, "cases": cases,
            "criteria": "Exact named logical clip/typed varying float32 or int32/uint32 bits, original instance-major selections and original flat-LAST references; no candidate ABI layout/padding expectation.",
            "oracle": "Unchanged original GLSL vertex source plus API-selected GL transform-feedback outputs; actual GL_POINTS with rasterizer discard isolates invocations before clipping. No geometry/tessellation stage, source rewriting or compute shader.",
            "padded_scope": "GL proves 65 logical outputs and per-invocation state only. Native workgroup padding/canary and no padded initialization remain separate actual-dispatch/CPU-AST gates.",
            "bool_scope": "Bool uniform/internal branch only; boolean vertex outputs are illegal and absent.",
            "public_API_scope": "Raw GL transform feedback proves original shader logical outputs, not unchanged public gloo DRAW admission. Integer constants are internal compiler/evaluator ABI probes; public GLIR supports only float/vec constant setters.",
            "sources": {"GL": SPEC, "GLSL": GLSL_SPEC},
            "open_gates": ["actual pinned upstream compilation/link/TF admission", "actual native ordered dispatch/output inspection",
                           "native storage/granted limits/padding/canary", "pending DrawSnap/Ticket lifetime, cache and recovery",
                           "actual line clipping/expansion/rasterization and all original references"]}


def generated_gluint(value, operation):
    """Extract one generated GL object name without ndarray scalar coercion."""
    if type(value) is not int and not isinstance(value, (np.integer, np.ndarray)):
        raise ValueError(operation + ": expected one integer GLuint scalar or one-element ndarray")
    array = np.asarray(value)
    if array.shape not in ((), (1,)) or array.dtype.kind not in "iu":
        raise ValueError(operation + ": expected one integer GLuint scalar or one-element ndarray")
    handle = int(array[()] if array.ndim == 0 else array[0])
    if not 0 < handle <= 0xFFFFFFFF:
        raise ValueError(operation + ": generated GLuint is zero or outside uint32 range")
    return handle


def capture_upstream(name, root):
    """Future reserved upstream-only GL job; calling this initializes a GPU.

    Imports and context creation stay inside this function. CPU authoring never
    calls it. Every output is read from actual GL transform feedback, not the CPU
    encode helper or expected-value formulas.
    """
    import ctypes
    import importlib.metadata
    from pathlib import Path
    import sys
    import vispy
    root = Path(root).resolve()
    expected_origin = root / "build/oracle-opengl/Lib/site-packages/vispy"
    assert Path(vispy.__file__).resolve().parent == expected_origin
    assert vispy.__version__ == "0.17.0"
    assert not any(module.startswith("vispy._dawn") for module in sys.modules)
    vispy.use(gl="gl+")
    from vispy import app
    from OpenGL import GL
    from OpenGL.raw.GL.VERSION.GL_3_0 import glGetTransformFeedbackVarying, glTransformFeedbackVaryings
    from OpenGL.raw.GL.VERSION.GL_4_3 import glGetProgramResourceiv

    spec = specification(name)
    layout = tf_layout(name)
    vertex, fragment = shaders(name)
    observed = {
        "kind": "upstream", "package_origin": vispy.__file__, "candidate_seen": False, "GPU_used": False,
        "packages": {package: importlib.metadata.version(package)
                     for package in ("vispy", "numpy", "PyOpenGL", "PyQt6", "PyQt6-Qt6")},
        "source_sha256": {"vertex": hashlib.sha256(vertex.encode()).hexdigest(),
                          "fragment": hashlib.sha256(fragment.encode()).hexdigest()},
        "transport": "actual API-configured GL transform feedback; unchanged vertex source; GL_POINTS/rasterizer discard",
        "original_primitive": spec["original_primitive"], "TF_shader_layout_is_native_layout": False,
        "admission_scope": admission_scope(name),
        "compile": [], "calls": [], "generated_IDs": [],
    }

    def generated(value, operation):
        handle = generated_gluint(value, operation)
        array = np.asarray(value)
        observed["generated_IDs"].append({"operation": operation, "return_shape": list(array.shape),
                                          "return_dtype": array.dtype.str, "GLuint": handle})
        return handle
    canvas, program, vao, query, feedback_object = None, 0, 0, 0, 0
    buffers, shader_ids = [], []
    tf_active = query_active = False
    raw = None
    try:
        observed["context_creation_attempted"] = True
        canvas = app.Canvas(app="pyqt6", size=(8, 8), show=False, config={"samples": 0})
        canvas.set_current()
        observed["context"] = {key: GL.glGetString(token).decode("utf-8", "replace")
                               for key, token in (("version", GL.GL_VERSION), ("vendor", GL.GL_VENDOR),
                                                  ("renderer", GL.GL_RENDERER), ("GLSL", GL.GL_SHADING_LANGUAGE_VERSION))}
        observed["GPU_used"] = True
        version = observed["context"]["version"].split()[0].split(".")
        assert tuple(map(int, version[:2])) >= (4, 6), "Actual GL4.6 required for queried TF buffer layout"
        assert not any(text in observed["context"]["renderer"].lower()
                       for text in ("llvmpipe", "swiftshader", "software", "softpipe"))
        observed["limits"] = {"TF_interleaved_components": int(GL.glGetIntegerv(GL.GL_MAX_TRANSFORM_FEEDBACK_INTERLEAVED_COMPONENTS)),
                              "TF_buffers": int(GL.glGetIntegerv(GL.GL_MAX_TRANSFORM_FEEDBACK_BUFFERS)),
                              "vertex_attributes": int(GL.glGetIntegerv(GL.GL_MAX_VERTEX_ATTRIBS)),
                              "samples": int(GL.glGetIntegerv(GL.GL_SAMPLES)),
                              "context_profile_mask": int(GL.glGetIntegerv(GL.GL_CONTEXT_PROFILE_MASK))}
        assert layout["stride"] // 4 <= observed["limits"]["TF_interleaved_components"]
        assert observed["limits"]["samples"] == 0 and observed["limits"]["TF_buffers"] >= 1
        assert len(spec["attributes"]) <= observed["limits"]["vertex_attributes"]
        program = int(GL.glCreateProgram())
        for stage, source in ((GL.GL_VERTEX_SHADER, vertex), (GL.GL_FRAGMENT_SHADER, fragment)):
            shader = int(GL.glCreateShader(stage)); shader_ids.append(shader)
            GL.glShaderSource(shader, source)
            GL.glCompileShader(shader)
            status = int(GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS))
            log = GL.glGetShaderInfoLog(shader)
            observed["compile"].append({"stage": int(stage), "status": status, "log": log.decode("utf-8", "replace") if isinstance(log, bytes) else str(log)})
            assert status == 1, observed["compile"][-1]
            GL.glAttachShader(program, shader)
        names = (ctypes.c_char_p * len(layout["fields"]))(*(row["name"].encode("ascii") for row in layout["fields"]))
        glTransformFeedbackVaryings(program, len(names), ctypes.cast(names, ctypes.POINTER(ctypes.POINTER(ctypes.c_char))), GL.GL_INTERLEAVED_ATTRIBS)
        GL.glLinkProgram(program)
        link_log = GL.glGetProgramInfoLog(program)
        observed["link"] = {"status": int(GL.glGetProgramiv(program, GL.GL_LINK_STATUS)),
                            "log": link_log.decode("utf-8", "replace") if isinstance(link_log, bytes) else str(link_log)}
        assert observed["link"]["status"] == 1, observed["link"]
        assert int(GL.glGetProgramiv(program, GL.GL_TRANSFORM_FEEDBACK_VARYINGS)) == len(layout["fields"])

        def resource(interface, index, properties):
            props = (ctypes.c_uint * len(properties))(*properties)
            values = (ctypes.c_int * len(properties))()
            count = ctypes.c_int()
            glGetProgramResourceiv(program, interface, index, len(properties), props, len(properties), ctypes.byref(count), values)
            assert count.value == len(properties)
            return list(values)

        queried_full = []
        for index, row in enumerate(layout["fields"]):
            length, size, kind = ctypes.c_int(), ctypes.c_int(), ctypes.c_uint()
            output_name = ctypes.create_string_buffer(256)
            glGetTransformFeedbackVarying(program, index, 256, ctypes.byref(length), ctypes.byref(size), ctypes.byref(kind), output_name)
            actual_name = output_name.value.decode("ascii")
            offset, buffer_index = resource(GL.GL_TRANSFORM_FEEDBACK_VARYING, index,
                                            (GL.GL_OFFSET, GL.GL_TRANSFORM_FEEDBACK_BUFFER_INDEX))
            queried_full.append({"actual_name": actual_name, "array_length": size.value,
                                 "gl_type": kind.value, "offset": offset, "buffer_index": buffer_index})
        actual_stride = resource(GL.GL_TRANSFORM_FEEDBACK_BUFFER, 0, (GL.GL_TRANSFORM_FEEDBACK_BUFFER_STRIDE,))[0]
        observed["TF_queried"] = {"varyings": queried_full, "stride": actual_stride, "mode": int(GL.GL_INTERLEAVED_ATTRIBS)}
        queried = validate_tf_query(name, queried_full, actual_stride, int(GL.GL_INTERLEAVED_ATTRIBS))
        GL.glUseProgram(program)
        vao = generated(GL.glGenVertexArrays(1), "glGenVertexArrays"); GL.glBindVertexArray(vao)
        source_buffers = {}
        for label, data in spec["buffers"].items():
            handle = generated(GL.glGenBuffers(1), "glGenBuffers"); buffers.append(handle); source_buffers[label] = handle
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, handle)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_STATIC_DRAW)
        observed["input_binding_layout"] = {}
        for label, binding in spec["attributes"].items():
            location = int(GL.glGetAttribLocation(program, label))
            assert location >= 0, label
            if "constant" in binding:
                value = binding["constant"]
                full = np.asarray([0, 0, 0, 1], dtype=value.dtype); full[:value.size] = value
                GL.glDisableVertexAttribArray(location)
                if value.dtype.kind == "f": GL.glVertexAttrib4fv(location, full)
                elif value.dtype.kind == "i": GL.glVertexAttribI4iv(location, full)
                else: GL.glVertexAttribI4uiv(location, full)
                observed["input_binding_layout"][label] = {"location": location, "constant": array_record(value)}
            else:
                data = spec["buffers"][binding["buffer"]]
                view = data[binding["field"]] if "field" in binding else data
                offset = data.dtype.fields[binding["field"]][1] if "field" in binding else 0
                components = int(np.prod(view.shape[1:]))
                kind = {"f": GL.GL_FLOAT, "i": GL.GL_INT, "u": GL.GL_UNSIGNED_INT}[view.dtype.kind]
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, source_buffers[binding["buffer"]])
                GL.glEnableVertexAttribArray(location)
                if view.dtype.kind == "f": GL.glVertexAttribPointer(location, components, kind, False, data.strides[0], ctypes.c_void_p(offset))
                else: GL.glVertexAttribIPointer(location, components, kind, data.strides[0], ctypes.c_void_p(offset))
                GL.glVertexAttribDivisor(location, binding["divisor"])
                observed["input_binding_layout"][label] = {"location": location, "buffer": binding["buffer"], "offset": offset,
                                                            "stride": data.strides[0], "components": components, "gl_type": int(kind),
                                                            "divisor": binding["divisor"], "normalized": False}
        for label, (kind, value) in spec["uniforms"].items():
            location = int(GL.glGetUniformLocation(program, label))
            assert location >= 0, label
            if kind == "mat4": GL.glUniformMatrix4fv(location, 1, False, np.ascontiguousarray(value.T))
            elif kind == "mat3": GL.glUniformMatrix3fv(location, 1, False, np.ascontiguousarray(value.T))
            elif kind == "vec2[2]": GL.glUniform2fv(location, 2, value)
            elif kind == "bool": GL.glUniform1i(location, int(value))
            else: GL.glUniform1ui(location, value)
        if spec["index"] is not None:
            index_buffer = generated(GL.glGenBuffers(1), "glGenBuffers"); buffers.append(index_buffer)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, index_buffer)
            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, spec["index"].nbytes, spec["index"], GL.GL_STATIC_DRAW)
        count = spec["count"] * spec["instances"]
        logical_bytes = count * actual_stride
        initial = np.full(logical_bytes + 4 * actual_stride, 0xCD, np.uint8)
        feedback = generated(GL.glGenBuffers(1), "glGenBuffers"); buffers.append(feedback)
        GL.glBindBuffer(GL.GL_TRANSFORM_FEEDBACK_BUFFER, feedback)
        GL.glBufferData(GL.GL_TRANSFORM_FEEDBACK_BUFFER, initial.nbytes, initial, GL.GL_STREAM_READ)
        feedback_object = generated(GL.glGenTransformFeedbacks(1), "glGenTransformFeedbacks")
        GL.glBindTransformFeedback(GL.GL_TRANSFORM_FEEDBACK, feedback_object)
        GL.glBindBufferBase(GL.GL_TRANSFORM_FEEDBACK_BUFFER, 0, feedback)
        query = generated(GL.glGenQueries(1), "glGenQueries")
        GL.glEnable(GL.GL_RASTERIZER_DISCARD)
        GL.glBeginQuery(GL.GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN, query); query_active = True
        GL.glBeginTransformFeedback(GL.GL_POINTS); tf_active = True
        if spec["index"] is None:
            GL.glDrawArraysInstanced(GL.GL_POINTS, spec["first"], spec["count"], spec["instances"])
            observed["calls"].append({"name": "glDrawArraysInstanced", "first": spec["first"], "count": spec["count"], "instances": spec["instances"]})
        else:
            kind = {1: GL.GL_UNSIGNED_BYTE, 2: GL.GL_UNSIGNED_SHORT, 4: GL.GL_UNSIGNED_INT}[spec["index"].dtype.itemsize]
            GL.glDrawElementsInstanced(GL.GL_POINTS, spec["count"], kind, ctypes.c_void_p(0), spec["instances"])
            observed["calls"].append({"name": "glDrawElementsInstanced", "count": spec["count"], "index_type": int(kind), "instances": spec["instances"]})
        GL.glEndTransformFeedback(); tf_active = False
        GL.glEndQuery(GL.GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN); query_active = False
        GL.glDisable(GL.GL_RASTERIZER_DISCARD)
        observed["primitives_written"] = int(GL.glGetQueryObjectuiv(query, GL.GL_QUERY_RESULT))
        assert observed["primitives_written"] == count
        GL.glBindBuffer(GL.GL_TRANSFORM_FEEDBACK_BUFFER, feedback)
        raw = bytes(GL.glGetBufferSubData(GL.GL_TRANSFORM_FEEDBACK_BUFFER, 0, initial.nbytes))
        observed.update(output_count=count, raw_bytes=len(raw), logical_bytes=logical_bytes,
                        raw_sha256=hashlib.sha256(raw).hexdigest())
        logical_raw = validate_tf_bytes(name, raw)
        observed.update(output_count=count, raw_bytes=len(raw), logical_bytes=logical_bytes,
                        tail_guard_rows=4, tail_guard_unchanged=True, gl_error=int(GL.glGetError()),
                        native_imported=any(module.startswith("vispy._dawn") for module in sys.modules))
        assert observed["gl_error"] == int(GL.GL_NO_ERROR) and observed["native_imported"] is False
        values = decode_tf(name, logical_raw, queried)
        return values, raw, observed
    except BaseException as error:
        error.endpoint_observations = observed
        error.endpoint_raw_tf = raw
        raise
    finally:
        if canvas is not None:
            original_error = sys.exc_info()[1]
            cleanup_errors = []

            def cleanup(label, operation):
                try:
                    operation()
                except BaseException as cleanup_error:
                    cleanup_errors.append({"operation": label, "type": type(cleanup_error).__name__, "error": str(cleanup_error)})

            if tf_active: cleanup("end TF", GL.glEndTransformFeedback)
            if query_active: cleanup("end query", lambda: GL.glEndQuery(GL.GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN))
            cleanup("disable rasterizer discard", lambda: GL.glDisable(GL.GL_RASTERIZER_DISCARD))
            cleanup("unbind program", lambda: GL.glUseProgram(0))
            if query: cleanup("delete query", lambda: GL.glDeleteQueries(1, [query]))
            if feedback_object:
                cleanup("unbind TF object", lambda: GL.glBindTransformFeedback(GL.GL_TRANSFORM_FEEDBACK, 0))
                cleanup("delete TF object", lambda: GL.glDeleteTransformFeedbacks(1, [feedback_object]))
            if buffers: cleanup("delete buffers", lambda: GL.glDeleteBuffers(len(buffers), buffers))
            if vao: cleanup("delete VAO", lambda: GL.glDeleteVertexArrays(1, [vao]))
            if program: cleanup("delete program", lambda: GL.glDeleteProgram(program))
            for shader in shader_ids: cleanup("delete shader", lambda shader=shader: GL.glDeleteShader(shader))
            cleanup("close Canvas", canvas.close)
            observed["cleanup_errors"] = cleanup_errors
            observed["owned_resources_cleanup_completed"] = not cleanup_errors
            if cleanup_errors and original_error is None:
                error = RuntimeError("Actual upstream cleanup failed")
                error.endpoint_observations, error.endpoint_raw_tf = observed, raw
                raise error
