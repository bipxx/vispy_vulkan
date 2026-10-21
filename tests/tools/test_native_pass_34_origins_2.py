"""Temporary-file origin controls. No renderer, native module or process launch."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "build/pass34-no-wait-work/origin_projection_1.py"


class BlockGraphics:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"vispy", "_dawn", "PyQt5", "PyQt6", "PySide2", "PySide6", "OpenGL", "napari"}:
            raise AssertionError("Native/graphics import forbidden in origin tests: " + fullname)


sys.dont_write_bytecode = True
sys.meta_path.insert(0, BlockGraphics())
spec = importlib.util.spec_from_file_location("pass34_origins_pure", MODULE_PATH)
origins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(origins)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha(data)


def put(root, name, value):
    return write(root, name, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))


@pytest.fixture
def context(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    old, new, stable = b"reviewed old runtime\n", b"reviewed new runtime\n", b"unchanged input\n"
    original = {"cpp/runtime.cpp": sha(old), "CMakeLists.txt": sha(stable),
                "tools/unchanged.py": sha(stable), "build/old-dataset.bin": sha(b"dataset")}
    for name in original:
        write(root, name, new if name == "cpp/runtime.cpp" else (b"dataset" if name.endswith(".bin") else stable))
    archive = "build/evidence/native-pass-33/activation-inputs"
    for data in (old, stable, b"dataset"):
        write(root, archive + "/blobs/" + sha(data), data)
    mapping = {"schema": 1, "layout": "sha256-flat-v1",
               "inputs": {name: {"sha256": digest, "blob": "blobs/" + digest} for name, digest in original.items()}}
    mapping_sha = put(root, archive + "/mapping.json", mapping)
    activation_path = "build/evidence/native-pass-33/activation.json"
    activation = {"epoch": 33, "python_inputs": original,
                  "activation_input_archive": {"layout": "sha256-flat-v1", "mapping_file": "mapping.json", "mapping_sha256": mapping_sha}}
    activation_sha = put(root, activation_path, activation)
    packet_path = "build/evidence/current-runtime-packet"
    packet_files = {"source/cpp/runtime.cpp": write(root, packet_path + "/source/cpp/runtime.cpp", new),
                    "proof.json": put(root, packet_path + "/proof.json", {"source_reviewed": True, "runtime_compiled": False})}
    sources = {"cpp/runtime.cpp": sha(new), "CMakeLists.txt": sha(stable)}
    ack_path = "build/evidence/current-owner-ack/ack.json"
    ack = {"epoch": 34, "schema": 1, "source_stability_acknowledged": True, "source_files": dict(sources),
           "owner_source_holds": {"root_runtime": True, "implement_packaging": True},
           "owners": {"root_runtime": ["cpp/runtime.cpp"], "implement_packaging": ["CMakeLists.txt"]}}
    ack_sha = put(root, ack_path, ack)
    packet = {"name": "line-query-cancel-no-wait", "archive": packet_path, "sealed": True,
              "files": packet_files, "files_tree_sha256": origins.tree_digest(packet_files),
              "owned_files": {"cpp/runtime.cpp": "source/cpp/runtime.cpp"},
              "source_tree_sha256": origins.tree_digest({"cpp/runtime.cpp": sha(new)})}
    manifest_path = "compat/native-epochs/pass34-w20-ownership.json"
    manifest = {"epoch": 34, "schema": 1, "sealed": True, "source_files": sources,
                "source_tree_sha256": origins.tree_digest(sources), "packets": [packet],
                "harness_inputs": {"cpp/runtime.cpp": {"path": packet_path + "/source/cpp/runtime.cpp", "sha256": sha(new)}},
                "paths": {"snapshot": "build/w20/source"}}
    bindings = {"owner_ack_path": ack_path, "owner_ack_sha256": ack_sha,
                "ownership_manifest_path": manifest_path, "ownership_manifest_sha256": put(root, manifest_path, manifest)}
    return {"root": root, "old": old, "new": new, "original": original,
            "activation_path": activation_path, "activation": activation, "activation_sha": activation_sha,
            "archive": archive, "mapping": mapping, "packet": packet, "manifest": manifest, "ack": ack,
            "bindings": bindings,
            "authorized": {"cpp/runtime.cpp": {"old_sha256": sha(old), "new_sha256": sha(new)}},
            "replacements": {"cpp/runtime.cpp": {"old_sha256": sha(old), "new_sha256": sha(new),
                              "new_source_origin": packet_path + "/source/cpp/runtime.cpp", "owner_packet_name": packet["name"]}}}


def parent(c):
    return origins.verify_parent_archive(c["root"], c["activation_path"], c["activation_sha"])


def project(c, **kwargs):
    return origins.project_origins(c["root"], parent(c), c["replacements"], c["authorized"], bindings=c["bindings"], **kwargs)


def repin(c, which):
    path_key = {"ack": "owner_ack", "manifest": "ownership_manifest"}[which]
    c["bindings"][path_key + "_sha256"] = put(c["root"], c["bindings"][path_key + "_path"], c[which])


def repin_parent(c):
    c["activation"]["activation_input_archive"]["mapping_sha256"] = put(c["root"], c["archive"] + "/mapping.json", c["mapping"])
    c["activation_sha"] = put(c["root"], c["activation_path"], c["activation"])


def add_frozen(c):
    path = "build/evidence/native-pass-34/frozen-inputs.json"
    frozen = {"epoch": 34, "source_files": dict(c["manifest"]["source_files"]),
              "harness_files": {"cpp/runtime.cpp": sha(c["new"])}}
    for name in frozen["source_files"]:
        write(c["root"], "build/w20/source/" + name, (c["root"] / name).read_bytes())
    c["bindings"].update({"frozen_inputs_path": path, "frozen_inputs_sha256": put(c["root"], path, frozen)})
    return frozen


def test_real_file_projection_replaces_live_identity_and_retains_every_old_blob(context):
    c = context
    ledger = project(c)
    assert ledger["current_input_hashes"]["cpp/runtime.cpp"] == sha(c["new"])
    old_origin = c["archive"] + "/blobs/" + sha(c["old"])
    assert ledger["current_input_hashes"][old_origin] == sha(c["old"])
    assert (c["root"] / old_origin).read_bytes() == c["old"]
    assert set(ledger["unchanged_parent_input_hashes"]) | set(ledger["replaced_inputs"]) == set(c["original"])
    assert not (set(ledger["unchanged_parent_input_hashes"]) & set(ledger["replaced_inputs"]))
    for name in set(c["original"]) - {"cpp/runtime.cpp"}:
        assert ledger["current_input_hashes"][name] == c["original"][name]
    assert ledger["parent_logical_input_count"] == 4
    assert ledger["parent_distinct_blob_count"] == 3  # Two logical names share one immutable payload.
    assert ledger["parent_physical_file_count"] == 4
    assert origins.validate_projection(c["root"], ledger, c["authorized"]) == ledger


def test_archive_admission_does_not_read_old_live_runtime_or_other_originals(context):
    (context["root"] / "CMakeLists.txt").unlink()
    assert parent(context)["parent_original_input_hashes"] == context["original"]
    with pytest.raises(ValueError, match="Missing"):
        project(context)


def test_recomputed_receipt_has_no_write_side_effects(context):
    c = context
    before = {p.relative_to(c["root"]).as_posix(): sha(p.read_bytes()) for p in c["root"].rglob("*") if p.is_file()}
    ledger = project(c)
    origins.validate_projection(c["root"], ledger, c["authorized"])
    after = {p.relative_to(c["root"]).as_posix(): sha(p.read_bytes()) for p in c["root"].rglob("*") if p.is_file()}
    assert before == after
    assert not (c["root"] / "build/evidence/native-pass-34/activation-approval.json").exists()


@pytest.mark.parametrize("damage", ["missing", "extra", "altered", "renamed", "empty_directory"])
def test_parent_physical_inventory_refusals(context, damage):
    c = context
    path = c["root"] / c["archive"] / "blobs" / sha(c["old"])
    if damage == "missing":
        path.unlink()
    elif damage == "extra":
        write(c["root"], c["archive"] + "/blobs/" + sha(b"foreign"), b"foreign")
    elif damage == "altered":
        path.write_bytes(b"corrupt")
    elif damage == "renamed":
        path.rename(path.with_name("wrong-name"))
    else:
        (c["root"] / c["archive"] / "extra-empty").mkdir()
    with pytest.raises(ValueError, match="inventory"):
        parent(c)


@pytest.mark.parametrize("damage", ["missing_key", "extra_key", "wrong_blob", "extra_row_field", "bool_schema", "wrong_layout"])
def test_parent_mapping_semantic_refusals_even_with_fresh_digest(context, damage):
    c = context
    rows = c["mapping"]["inputs"]
    if damage == "missing_key":
        del rows["tools/unchanged.py"]
    elif damage == "extra_key":
        rows["tools/unrelated.py"] = dict(rows["tools/unchanged.py"])
    elif damage == "wrong_blob":
        rows["cpp/runtime.cpp"]["blob"] = "blobs/" + sha(c["new"])
    elif damage == "extra_row_field":
        rows["cpp/runtime.cpp"]["scope"] = "unapproved"
    elif damage == "bool_schema":
        c["mapping"]["schema"] = True
    else:
        c["mapping"]["layout"] = "nested"
    repin_parent(c)
    with pytest.raises(ValueError):
        parent(c)


@pytest.mark.parametrize("field", ["epoch", "python_inputs"])
def test_duplicate_json_keys_are_refused(context, field):
    c = context
    source = json.dumps(c["activation"])
    value = "33" if field == "epoch" else json.dumps(c["original"])
    data = (source[:-1] + ', "' + field + '": ' + value + "}").encode()
    c["activation_sha"] = write(c["root"], c["activation_path"], data)
    with pytest.raises(ValueError, match="Duplicate JSON"):
        parent(c)


@pytest.mark.parametrize("name", ["../cpp/runtime.cpp", "/cpp/runtime.cpp", "cpp//runtime.cpp", "cpp/./runtime.cpp", "cpp\\runtime.cpp", "cpp/runtime.cpp:stream", "cpp/runtime.cpp.", "cpp/ runtime.cpp", "cpp/NUL.hpp"])
def test_windows_traversal_and_alias_names_refused(name):
    with pytest.raises(ValueError):
        origins.relative_path(name)


def test_case_alias_in_parent_original_map_refused(context):
    c = context
    c["activation"]["python_inputs"]["CPP/runtime.cpp"] = sha(c["old"])
    repin_parent(c)
    with pytest.raises(ValueError, match="Case-aliased"):
        parent(c)


def test_reparse_origin_refused_before_hash(context, monkeypatch):
    c = context
    blocked = c["root"] / c["archive"] / "blobs" / sha(c["old"])
    original = origins._unsafe_node
    monkeypatch.setattr(origins, "_unsafe_node", lambda p: p == blocked or original(p))
    with pytest.raises(ValueError, match="reparse"):
        parent(c)


@pytest.mark.parametrize("damage", ["missing", "unrelated", "prefix", "native", "same_digest", "wrong_old", "wrong_new", "extra_intent", "wrong_blob_intent"])
def test_explicit_replacement_authorization_refusals(context, damage):
    c = context
    row = c["replacements"]["cpp/runtime.cpp"]
    if damage == "missing":
        c["replacements"].clear()
    elif damage in {"unrelated", "prefix", "native"}:
        name = {"unrelated": "tools/unchanged.py", "prefix": "cpp/", "native": "src/vispy/_dawn.pyd"}[damage]
        c["replacements"][name] = dict(row)
        c["authorized"][name] = {"old_sha256": sha(c["old"]), "new_sha256": sha(c["new"])}
    elif damage == "same_digest":
        row["new_sha256"] = c["authorized"]["cpp/runtime.cpp"]["new_sha256"] = sha(c["old"])
    elif damage == "wrong_old":
        row["old_sha256"] = c["authorized"]["cpp/runtime.cpp"]["old_sha256"] = sha(b"wrong")
    elif damage == "wrong_new":
        row["new_sha256"] = sha(b"unreviewed")
    elif damage == "extra_intent":
        row["unapproved"] = True
    else:
        row["parent_blob_path"] = c["archive"] + "/blobs/" + sha(c["new"])
    with pytest.raises(ValueError):
        project(c)


@pytest.mark.parametrize("name", ["cpp/runtime.cpp", "tools/unchanged.py", "build/old-dataset.bin", "CMakeLists.txt"])
def test_changed_live_origins_refused(context, name):
    (context["root"] / name).write_bytes(b"unreviewed current change")
    with pytest.raises(ValueError):
        project(context)


@pytest.mark.parametrize("damage", ["unstable_ack", "wrong_ack_sha", "ack_overlap", "ack_omission", "wrong_manifest_sha", "wrong_epoch", "bool_epoch", "unsealed", "wrong_source_tree", "no_owner", "double_owner", "wrong_packet_name", "wrong_source_origin", "wrong_harness_path", "wrong_harness_sha", "packet_unsealed", "packet_tree", "owned_tree", "packet_extra_file"])
def test_ack_packet_manifest_refusals(context, damage):
    c = context
    digest = sha(b"wrong")
    if damage == "unstable_ack":
        c["ack"]["source_stability_acknowledged"] = False
    elif damage == "wrong_ack_sha":
        c["ack"]["source_files"]["cpp/runtime.cpp"] = digest
    elif damage == "ack_overlap":
        c["ack"]["owners"]["implement_packaging"].append("cpp/runtime.cpp")
    elif damage == "ack_omission":
        c["ack"]["owners"]["root_runtime"].clear()
    elif damage == "wrong_manifest_sha":
        c["manifest"]["source_files"]["cpp/runtime.cpp"] = digest
        c["manifest"]["source_tree_sha256"] = origins.tree_digest(c["manifest"]["source_files"])
    elif damage in {"wrong_epoch", "bool_epoch"}:
        c["manifest"]["epoch"] = 33 if damage == "wrong_epoch" else True
    elif damage == "unsealed":
        c["manifest"]["sealed"] = False
    elif damage == "wrong_source_tree":
        c["manifest"]["source_tree_sha256"] = digest
    elif damage == "no_owner":
        c["packet"]["owned_files"].clear()
    elif damage == "double_owner":
        c["manifest"]["packets"].append(copy.deepcopy(c["packet"]))
    elif damage == "wrong_packet_name":
        c["replacements"]["cpp/runtime.cpp"]["owner_packet_name"] = "unrelated"
    elif damage == "wrong_source_origin":
        c["replacements"]["cpp/runtime.cpp"]["new_source_origin"] = "cpp/runtime.cpp"
    elif damage == "wrong_harness_path":
        c["manifest"]["harness_inputs"]["cpp/runtime.cpp"]["path"] = "cpp/runtime.cpp"
    elif damage == "wrong_harness_sha":
        c["manifest"]["harness_inputs"]["cpp/runtime.cpp"]["sha256"] = digest
    elif damage == "packet_unsealed":
        c["packet"]["sealed"] = False
    elif damage == "packet_tree":
        c["packet"]["files_tree_sha256"] = digest
    elif damage == "owned_tree":
        c["packet"]["source_tree_sha256"] = digest
    else:
        write(c["root"], c["packet"]["archive"] + "/unlisted.bin", b"extra")
    repin(c, "ack")
    repin(c, "manifest")
    with pytest.raises(ValueError):
        project(c)


def test_frozen_binding_requires_actual_matching_source_and_recomputes(context):
    c = context
    add_frozen(c)
    ledger = project(c)
    assert origins.validate_projection(c["root"], ledger, c["authorized"], require_frozen=True) == ledger
    assert ledger["current_input_hashes"]["build/w20/source/cpp/runtime.cpp"] == sha(c["new"])


@pytest.mark.parametrize("damage", ["absent", "partial", "wrong_epoch", "source", "harness", "physical"])
def test_frozen_source_refusals(context, damage):
    c = context
    if damage == "absent":
        ledger = project(c)
        with pytest.raises(ValueError, match="Frozen|frozen"):
            origins.validate_projection(c["root"], ledger, c["authorized"], require_frozen=True)
        return
    frozen = add_frozen(c)
    if damage == "partial":
        del c["bindings"]["frozen_inputs_sha256"]
    elif damage == "physical":
        (c["root"] / "build/w20/source/cpp/runtime.cpp").write_bytes(b"wrong")
    else:
        if damage == "wrong_epoch":
            frozen["epoch"] = 33
        elif damage == "source":
            frozen["source_files"]["cpp/runtime.cpp"] = sha(c["old"])
        else:
            frozen["harness_files"]["cpp/runtime.cpp"] = sha(c["old"])
        c["bindings"]["frozen_inputs_sha256"] = put(c["root"], c["bindings"]["frozen_inputs_path"], frozen)
    with pytest.raises(ValueError):
        project(c)


@pytest.mark.parametrize("damage", ["stale_live_sha", "omit_unchanged", "omit_old_blob", "wrong_parent_origin", "wrong_old_row", "wrong_current_count", "extra_field", "unapproved_added_input"])
def test_serialized_ledger_cannot_bypass_recomputation(context, damage):
    c = context
    ledger = project(c)
    if damage == "stale_live_sha":
        ledger["current_input_hashes"]["cpp/runtime.cpp"] = sha(c["old"])
    elif damage == "omit_unchanged":
        del ledger["unchanged_parent_input_hashes"]["tools/unchanged.py"]
    elif damage == "omit_old_blob":
        del ledger["current_input_hashes"][c["archive"] + "/blobs/" + sha(c["old"])]
    elif damage == "wrong_parent_origin":
        ledger["parent_input_origins"]["cpp/runtime.cpp"] = "cpp/runtime.cpp"
    elif damage == "wrong_old_row":
        ledger["replaced_inputs"]["cpp/runtime.cpp"]["parent_blob_path"] = "cpp/runtime.cpp"
    elif damage == "wrong_current_count":
        ledger["current_input_count"] += 1
    elif damage == "extra_field":
        ledger["blanket_cpp_exemption"] = True
    else:
        name = "build/unapproved-proof.bin"
        checksum = write(c["root"], name, b"unapproved")
        ledger["added_inputs"][name] = ledger["current_input_hashes"][name] = checksum
    with pytest.raises(ValueError, match="ledger"):
        origins.validate_projection(c["root"], ledger, c["authorized"])


def test_added_input_is_explicit_physically_verified_and_bound_on_readmission(context):
    c = context
    additions = {"build/current-independent-review.json": put(c["root"], "build/current-independent-review.json", {"status": "source-only"})}
    ledger = project(c, added_inputs=additions)
    assert origins.validate_projection(c["root"], ledger, c["authorized"], added_inputs=additions) == ledger
    with pytest.raises(ValueError, match="ledger"):
        origins.validate_projection(c["root"], ledger, c["authorized"])


@pytest.mark.parametrize("name,checksum", [("cpp/runtime.cpp", sha(b"old")), ("CPP/runtime.cpp", sha(b"new")), ("tools/unchanged.py", sha(b"changed"))])
def test_current_input_merge_conflict_has_no_partial_publication(context, name, checksum):
    c = context
    inputs = {"cpp/runtime.cpp": sha(c["new"]), "tools/unchanged.py": c["original"]["tools/unchanged.py"]}
    before = dict(inputs)
    with pytest.raises(ValueError):
        origins.merge_inputs(inputs, {"build/unrelated-new.bin": sha(b"other"), name: checksum})
    assert inputs == before


def test_altered_parent_receipt_refused_before_current_projection(context):
    c = context
    receipt = parent(c)
    receipt["parent_input_origins"]["cpp/runtime.cpp"] = "cpp/runtime.cpp"
    with pytest.raises(ValueError, match="Parent receipt"):
        origins.project_origins(c["root"], receipt, c["replacements"], c["authorized"], bindings=c["bindings"])


def add_ack_contract(c):
    name = "tests/lines/line_ownership_contract.cpp"
    data = b"reviewed unchanged standalone contract\n"
    digest = write(c["root"], name, data)
    origin = "build/evidence/old-contract-packet/source/" + name
    write(c["root"], origin, data)
    c["ack"]["source_files"][name] = digest
    c["ack"]["owners"]["root_runtime"].append(name)
    c["manifest"]["harness_inputs"][name] = {"path": origin, "sha256": digest}
    repin(c, "ack")
    repin(c, "manifest")
    return name, origin, digest


def test_real_ack_contract_route_uses_harness_and_current_live_source(context):
    c = context
    name, origin, digest = add_ack_contract(c)
    assert name not in c["manifest"]["source_files"]
    ledger = project(c)
    assert ledger["current_input_hashes"][name] == digest
    assert ledger["current_input_hashes"][origin] == digest
    assert origins.validate_projection(c["root"], ledger, c["authorized"]) == ledger


@pytest.mark.parametrize("damage", ["old_harness_sha", "missing_harness", "changed_harness_origin", "changed_live_contract", "wrong_project_route"])
def test_ack_contract_harness_refusals(context, damage):
    c = context
    name, origin, digest = add_ack_contract(c)
    if damage == "old_harness_sha":
        c["manifest"]["harness_inputs"][name]["sha256"] = sha(b"old contract")
    elif damage == "missing_harness":
        del c["manifest"]["harness_inputs"][name]
    elif damage == "changed_harness_origin":
        (c["root"] / origin).write_bytes(b"changed archived contract")
    elif damage == "changed_live_contract":
        (c["root"] / name).write_bytes(b"changed live contract")
    else:
        c["manifest"]["source_files"][name] = digest
        c["manifest"]["source_tree_sha256"] = origins.tree_digest(c["manifest"]["source_files"])
    repin(c, "manifest")
    with pytest.raises(ValueError):
        project(c)


@pytest.mark.parametrize("damage", ["bool_schema", "old_epoch", "missing_owner_hold", "released_owner_hold"])
def test_ack_current_schema_and_holds_refusals(context, damage):
    c = context
    if damage == "bool_schema":
        c["ack"]["schema"] = True
    elif damage == "old_epoch":
        c["ack"]["epoch"] = 33
    elif damage == "missing_owner_hold":
        del c["ack"]["owner_source_holds"]["root_runtime"]
    else:
        c["ack"]["owner_source_holds"]["root_runtime"] = False
    repin(c, "ack")
    with pytest.raises(ValueError):
        project(c)


def test_actual_parent33_archive_is_admitted_without_old_live_cpp_equivalence():
    receipt = origins.verify_parent_archive(
        ROOT, "build/evidence/native-pass-33/activation.json",
        "bec786d2040e269c6221803e15162e53125af3d2c988368adc90adadac32f43c")
    assert receipt["parent_mapping_sha256"] == "7e21f3a7ee053aa40c9ea92ae82619241da466f6d38e00de1dd0554db54357af"
    assert receipt["parent_logical_input_count"] == 3225
    assert receipt["parent_distinct_blob_count"] == 1508
    assert receipt["parent_physical_file_count"] == 1509
    assert receipt["parent_original_input_tree_sha256"] == "f8a701a915793baa18dfc61f632f2fa0ba2dd872b15ddddaa7ce0102d3697f55"
    assert receipt["parent_original_input_hashes"]["cpp/runtime.cpp"] == origins.REVIEWED_CHANGES["cpp/runtime.cpp"]["old_sha256"]
    old = ROOT / receipt["parent_input_origins"]["cpp/runtime.cpp"]
    assert sha(old.read_bytes()) == origins.REVIEWED_CHANGES["cpp/runtime.cpp"]["old_sha256"]
