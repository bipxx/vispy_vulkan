# SPDX-License-Identifier: AGPL-3.0-only
"""Test actual candidate pack functions with actual nanobind snapshot/decoder."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

binary = Path(sys.argv[1]).resolve()
source = Path(sys.argv[2]).resolve()
if sys.flags.optimize:
    raise RuntimeError("Packing contracts require assertions")
spec = importlib.util.spec_from_file_location("_owned_upload_contract", binary)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
source_text = source.read_text(encoding="utf-8")
tree = ast.parse(source_text)
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("_freeze", "_freeze_owned", "pack_commands")]
assert len(functions) == 3
# AST dump fields vary across Python releases. Pin the unchanged function's
# exact source instead; read_text normalizes platform line endings.
legacy_source = ast.get_source_segment(source_text, functions[0])
assert legacy_source is not None and hashlib.sha256(legacy_source.encode()).hexdigest() == "51f69590e0dc52c8e871400a283a4a1a4931028b49f340330f17a0418aa887b8", "legacy freezer changed"
namespace = {"np": np}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
pack = namespace["pack_commands"]
checks = []

def check(label, condition):
    assert condition, label
    checks.append(label)

def stats():
    return dict(captures=0, bytes=0, fallback_dtypes=0, fallback_exports=0)

numeric = [np.bool_, np.int8, np.uint8, np.int16, np.uint16, np.int32, np.uint32, np.float16, np.float32, np.float64]
arrays = []
for dtype in numeric:
    raw = np.arange(48).reshape(4, 4, 3).astype(dtype)
    arrays.extend([raw, raw[:, ::-1], np.asfortranarray(raw), raw.transpose(1, 0, 2)])
arrays.extend([np.arange(24, dtype=">f4").reshape(2, 3, 4), np.arange(24, dtype=">i2").reshape(2, 3, 4), np.empty((0, 3), dtype=np.float32), np.array(17, dtype=np.float32)])
for index, array in enumerate(arrays):
    wanted = np.ascontiguousarray(array).tobytes()
    commands = [("DATA", 7, [0], array)]
    default, side = pack(commands)
    check(f"default_bytes_{index}", default[0][3] == {"__bytes__": wanted, "shape": list(np.ascontiguousarray(array).shape), "dtype": array.dtype.str} and side == [])
    counters = stats()
    owned, side = pack(commands, native_capture=native.capture, capture_stats=counters)
    capsule = owned[0][3]["__owned_blob__"]
    address = native.address(capsule)
    left, count = native.decode(owned)
    right, old_count = native.decode(default)
    check(f"owned_payload_{index}", left[0][2]["bytes"] == right[0][2]["bytes"] == wanted and left[0][2]["dtype"] == right[0][2]["dtype"] and left[0][2]["shape"] == right[0][2]["shape"] and count == old_count == len(wanted))
    check(f"owned_address_and_counts_{index}", (not wanted or address == left[0][2]["address"]) and side == [] and counters == dict(captures=1, bytes=len(wanted), fallback_dtypes=0, fallback_exports=0))

unsupported = [np.zeros(2, dtype=dtype) for dtype in ("M8[D]", "m8[ns]", "V8", "U3", "S3", "O", "c8", "i8", "u8")]
unsupported.append(np.zeros(2, dtype=[("x", "<f4"), ("y", "<i2")]))
for index, array in enumerate(unsupported):
    commands = [("DATA", 7, [0], array)]
    counters = stats()
    owned, side = pack(commands, native_capture=native.capture, capture_stats=counters)
    default, _ = pack(commands)
    check(f"unsupported_legacy_bytes_{index}", owned == default and side == [] and counters == dict(captures=0, bytes=0, fallback_dtypes=1, fallback_exports=0))

for error in (BufferError, TypeError, ValueError):
    def rejected(_buffer, error=error):
        raise error("test exporter rejection")
    commands = [("DATA", 7, [0], np.arange(12, dtype=np.float32))]
    counters = stats()
    owned, _ = pack(commands, native_capture=rejected, capture_stats=counters)
    default, _ = pack(commands)
    check("export_fallback_" + error.__name__, owned == default and counters == dict(captures=0, bytes=0, fallback_dtypes=0, fallback_exports=1))

def out_of_memory(_buffer):
    raise MemoryError("test allocation failure")
try:
    pack(commands, native_capture=out_of_memory, capture_stats=stats())
except MemoryError:
    checks.append("allocation_failure_propagates")
else:
    raise AssertionError("MemoryError swallowed")

array = np.arange(32, dtype=np.float32)
wanted = array.tobytes()
class Enum:
    def __int__(self):
        array.fill(-17)
        return 7
owned, _ = pack([("DATA", 7, [0], array), ("FUNC", Enum())], native_capture=native.capture, capture_stats=stats())
result, count = native.decode(owned)
check("later_enum_mutation_cannot_change_snapshot", result[0][2]["bytes"] == wanted and np.all(array == -17))

# Scalar and nested-container conversions must retain the legacy behavior.
values = [None, True, False, 7, 2.5, "text", np.int16(-3), np.uint64(9),
          np.float32(1.25), np.bool_(True), [Enum(), (1, None)]]
counters = stats()
default, old_side = pack([("FUNC", values)])
owned, side = pack([("FUNC", values)], native_capture=native.capture, capture_stats=counters)
check("scalar_and_nested_legacy_equivalence", owned == default and side == old_side == [] and counters == stats())

report = {"status": "PASS_CANDIDATE_PACKING_WITH_ACTUAL_NANOBIND_DECODER", "checks": checks,
          "array_layouts": len(arrays), "unsupported_dtypes": len(unsupported),
          "numpy": np.__version__, "python": sys.version,
          "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
          "GPU_used": False, "release_qualified": False}
print(json.dumps({"status": report["status"], "checks": len(checks)}), flush=True)
