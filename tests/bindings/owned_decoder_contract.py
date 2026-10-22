# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

binary = Path(sys.argv[1]).resolve()
if sys.flags.optimize:
    raise RuntimeError("Ownership contracts require assertions")
spec = importlib.util.spec_from_file_location("_owned_upload_contract", binary)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
checks = []

def check(label, condition):
    assert condition, label
    checks.append(label)

def fails(label, func):
    try:
        func()
    except (ValueError, TypeError, RuntimeError, IndexError):
        checks.append(label)
    else:
        raise AssertionError(label)

def payload(raw=b"abcdefgh", dtype="|u1", shape=None):
    capsule = native.capture(memoryview(raw))
    return {"__owned_blob__": capsule, "dtype": dtype, "shape": shape or [len(raw)]}

source = bytearray(b"abcdefgh")
owned = payload(source)
address = native.address(owned["__owned_blob__"])
source[:] = b"XXXXXXXX"
del source
decoded, count = native.decode([("DATA", 7, [0], owned)])
result = decoded[0][2]
check("snapshot_survives_source_mutation_and_release", result["bytes"] == b"abcdefgh")
check("decoder_moves_same_allocation", result["address"] == address)
check("logical_decoded_bytes", count == 8)
check("decoded_metadata", result["shape"] == [8] and result["dtype"] == "u8")
fails("single_consume", lambda: native.decode([("DATA", owned)]))

legacy = {"__bytes__": b"abcdefgh", "dtype": "|u1", "shape": [8]}
first = native.decode([("DATA", legacy)])
second = native.decode([("DATA", legacy)])
check("legacy_replayable", first[0][0][0]["bytes"] == second[0][0][0]["bytes"] == b"abcdefgh")

early, late = payload(), payload()
broken = {"__owned_blob__": early["__owned_blob__"], "dtype": "|u1", "shape": [object()]}
fails("malformed_metadata_rejected", lambda: native.decode([("DATA", broken), ("DATA", late)]))
for label, item in (("bad_metadata_snapshot_discarded", early), ("later_snapshot_discarded", late)):
    fails(label, lambda item=item: native.address(item["__owned_blob__"]))

duplicate, tail = payload(), payload()
fails("duplicate_snapshot_rejected", lambda: native.decode([("DATA", duplicate, duplicate), ("DATA", tail)]))
for label, item in (("duplicate_discarded", duplicate), ("duplicate_tail_discarded", tail)):
    fails(label, lambda item=item: native.address(item["__owned_blob__"]))

tail = payload()
fails("invalid_capsule_rejected", lambda: native.decode([("DATA", {"__owned_blob__": object()}), ("DATA", tail)]))
fails("invalid_capsule_tail_discarded", lambda: native.address(tail["__owned_blob__"]))

tail = payload()
fails("bad_command_operation_rejected", lambda: native.decode([(None,), ("DATA", tail)]))
fails("bad_command_tail_discarded", lambda: native.address(tail["__owned_blob__"]))

owned = payload()
both = dict(legacy, __owned_blob__=owned["__owned_blob__"])
result, count = native.decode([("DATA", both)])
check("bytes_branch_precedence", result[0][0]["bytes"] == b"abcdefgh" and count == 8)
check("ignored_capsule_stays_available", native.address(owned["__owned_blob__"]) != 0)
native.decode([("DATA", owned)])

owned = payload()
result, count = native.decode([("DATA", [[owned]])])
check("nested_lists_owned", result[0][0][0][0]["bytes"] == b"abcdefgh" and count == 8)

empty = payload(b"", shape=[0])
result, count = native.decode([("DATA", empty)])
check("empty_snapshot", result[0][0]["bytes"] == b"" and count == 0)

for dtype in ("<f4", ">f4", "<f2", "<f8", "<i4", "|u1", "<u2", "<i2", "<u4", "|i1", "|b1", "<i8", "|V8"):
    raw = bytes(range(8))
    owned = payload(raw, dtype)
    old = {"__bytes__": raw, "dtype": dtype, "shape": [1]}
    left, lc = native.decode([("DATA", owned)])
    right, rc = native.decode([("DATA", old)])
    check("legacy_dtype_mapping_" + dtype, left[0][0]["dtype"] == right[0][0]["dtype"] and left[0][0]["bytes"] == right[0][0]["bytes"] and lc == rc == 8)

large = bytearray(64 * 1024 * 1024)
large[0], large[-1] = 17, 91
owned = payload(large)
address = native.address(owned["__owned_blob__"])
large[0], large[-1] = 0, 0
del large
result, count = native.decode([("DATA", owned)])
blob = result[0][0]
check("64MiB_move_and_snapshot", blob["address"] == address and count == 64 * 1024 * 1024 and blob["bytes"][0] == 17 and blob["bytes"][-1] == 91)

# Actual C++ bad_alloc during collection, validation, and command conversion.
for after in range(8):
    group = [payload(), payload(), payload()]
    commands = [("DATA", item) for item in group]
    try:
        native.allocation_failure(commands, after)
    except MemoryError:
        checks.append(f"allocation_failure_translated_{after}")
    else:
        raise AssertionError(f"No allocation failure at position {after}")
    for index, item in enumerate(group):
        fails(f"allocation_failure_discards_entire_batch_{after}_{index}", lambda item=item: native.address(item["__owned_blob__"]))

from collections import UserList
owned, tail = payload(), payload()
fails("owned_rejects_custom_command_sequence", lambda: native.decode([UserList(["DATA", owned]), ("DATA", tail)]))
fails("rejected_sequence_discards_valid_tail", lambda: native.address(tail["__owned_blob__"]))
check("legacy_custom_sequence_preserved", native.legacy_decode([UserList(["DATA", legacy])]) == 1)
owned = payload()
address = native.address(owned["__owned_blob__"])
check("legacy_unknown_owned_dict_preserved", native.legacy_decode([("DATA", owned)]) == 1 and native.address(owned["__owned_blob__"]) == address)
native.decode([("DATA", owned)])

report = {"status": "PASS_ACTUAL_NANOBIND_CPU_DECODER_CONTRACTS", "checks": checks,
          "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
          "python": sys.version, "GPU_used": False, "native_epoch_built": False,
          "release_qualified": False}
print(json.dumps({"status": report["status"], "checks": len(checks)}), flush=True)
