"""Pure pass34 ownership-transfer controls; no producer main/native/backend.

The actual immutable parent metadata supplies all inherited ownership/gates.
New runtime packets use temporary files and native_epoch's real check_packet.
No canonical proposal, freeze, compiler or activation is executed.
"""

import copy
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


class NoGraphics(importlib.abc.MetaPathFinder):
    attempts = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"vispy", "numpy", "PyQt5", "PyQt6", "PySide2", "PySide6", "OpenGL", "glfw"}:
            self.attempts.append(fullname)
            raise ImportError("Graphics/project import forbidden in ownership controls: " + fullname)


sys.meta_path.insert(0, NoGraphics())


def read_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = read_module("pure_pass34_preparer", ROOT / "build/prepare_pass34_ownership_1.py")
epoch = read_module("pure_native_epoch", ROOT / "tools/native_epoch.py")


class Pass34Ownership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (ROOT / p.PARENT).read_bytes()
        if hashlib.sha256(raw).hexdigest() != p.PARENT_SHA:
            raise AssertionError("Actual immutable33 parent pin differs")
        cls.parent = json.loads(raw)
        cls.old = p.parent_owned(cls.parent)
        cls.new_digest = hashlib.sha256(b"independent new runtime source\n").hexdigest()
        cls.native = {"src/vispy/" + name: hashlib.sha256(name.encode()).hexdigest()
                      for name in ("_dawn.test.pyd", "_sdf.test.pyd", "VkLayer.dll", "VkLayer.json")}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = copy.deepcopy(self.parent["source_files"])
        self.source["cpp/runtime.cpp"] = self.new_digest
        self.held = {name: self.new_digest if name == "cpp/runtime.cpp" else
                     p.CMAKE_SHA if name == "CMakeLists.txt" else self.old[name] for name in p.SOURCE_CONTEXT}
        self.ack = {"schema": 1, "source_stability_acknowledged": True, "GPU_used": False,
                    "native_imported": False, "source_files": self.held,
                    "owners": {"runtime": sorted(p.SOURCE_CONTEXT - {"CMakeLists.txt"}), "packaging": ["CMakeLists.txt"]},
                    "owner_source_holds": {"runtime": True, "packaging": True},
                    "baseline": {"epoch": 33, "activation_sha256": p.ACTIVE_SHA,
                                 "ownership_manifest_sha256": p.PARENT_SHA, "protected_native": self.native}}
        self.proof = {**p.PROOF_ASSERTIONS, "source_files": self.held,
                      "protected_before": self.native, "protected_after": self.native}
        self.packet = {"name": p.PACKET_NAME, "archive": "build/evidence/temporary-runtime-packet", "sealed": True,
                       "files": {"source/cpp/runtime.cpp": self.new_digest, "proof.json": "a" * 64,
                                 "source/CMakeLists.txt": p.CMAKE_SHA, "retained/failed-job.bin": "b" * 64},
                       "files_tree_sha256": "c" * 64, "proof_file": "proof.json",
                       "proof_assertions": copy.deepcopy(p.PROOF_ASSERTIONS),
                       "owned_files": {"cpp/runtime.cpp": "source/cpp/runtime.cpp"},
                       "source_tree_sha256": epoch.tree_digest({"cpp/runtime.cpp": self.new_digest})}
        self.recipe = {"schema": 1, "epoch": 34, "snapshot_epoch": 20, "proposal_only": True,
                       "parent_manifest": p.PARENT, "parent_manifest_sha256": p.PARENT_SHA,
                       "activation_manifest": p.ACTIVE, "activation_manifest_sha256": p.ACTIVE_SHA,
                       "owner_ack_path": "build/temporary-source-ack.json", "owner_ack_sha256": "d" * 64,
                       "runtime_source_review": {"path": "build/temporary-source-review.json", "sha256": "e" * 64},
                       "checked_inputs": {**p.PARENT_BUILD_PINS, "build/temporary-source-review.json": "e" * 64},
                       "CMake_owner_acknowledged": True, "GPU_harness_included_in_ABI_inputs": False}

    def derive(self, parent=None, packet=None, source=None, recipe=None):
        return p.derive_record(epoch, self.parent if parent is None else parent,
                               self.packet if packet is None else packet,
                               self.source if source is None else source, self.native,
                               self.recipe if recipe is None else recipe, "build/temporary-recipe.json", "f" * 64, self.ack)

    def write_packet(self):
        archive = self.directory / "archive"
        (archive / "source/cpp").mkdir(parents=True)
        (archive / "source/cpp/runtime.cpp").write_bytes(b"independent new runtime source\n")
        (archive / "proof.json").write_bytes(json.dumps(self.proof, sort_keys=True).encode())
        packet = copy.deepcopy(self.packet)
        packet["files"] = epoch.inventory(archive)
        packet["files_tree_sha256"] = epoch.tree_digest(packet["files"])
        return archive, packet

    def test_actual_parent_full_gate_is_used(self):
        self.assertEqual((len(self.parent["source_files"]), len(self.parent["harness_inputs"]), len(self.old)), (590, 1677, 31))
        self.assertEqual((len(self.parent["targets"]), len(self.parent["ctest_expected_names"])), (18, 20))
        self.assertEqual([len(packet["files"]) for packet in self.parent["packets"]], [95, 91, 176])

    def test_exact_one_key_transfer_preserves_other_thirty(self):
        result = self.derive()
        owned = p.parent_owned(result)
        self.assertEqual(set(owned), set(self.old))
        self.assertEqual(owned["cpp/runtime.cpp"], self.new_digest)
        self.assertEqual({name: value for name, value in owned.items() if name != "cpp/runtime.cpp"},
                         {name: value for name, value in self.old.items() if name != "cpp/runtime.cpp"})

    def test_observer_keeps_six_owners_and_entire_ninety_five_members(self):
        old = self.parent["packets"][0]
        remaining = self.derive()["packets"][1]
        self.assertEqual(remaining["files"], old["files"])
        self.assertEqual(remaining["owned_files"], {k: v for k, v in old["owned_files"].items() if k != "cpp/runtime.cpp"})
        self.assertEqual(len(remaining["owned_files"]), 6)
        for field in old:
            if field not in {"owned_files", "source_tree_sha256"}:
                self.assertEqual(remaining[field], old[field])

    def test_full_parent_histories_and_unaffected_packets_survive(self):
        result = self.derive()
        self.assertEqual(result["packets"][2:], self.parent["packets"][1:])
        self.assertEqual(result["historical_pass33_current_packets"], self.parent["packets"])
        for name in self.parent:
            if "historical" in name or "supplementary" in name:
                self.assertEqual(result[name], self.parent[name], name)

    def test_all_1677_inherited_harness_rows_survive_except_runtime(self):
        result = self.derive()
        for name, value in self.parent["harness_inputs"].items():
            if name != "cpp/runtime.cpp":
                self.assertEqual(result["harness_inputs"][name], value, name)
        self.assertEqual(result["harness_inputs"]["cpp/runtime.cpp"],
                         {"path": self.packet["archive"] + "/source/cpp/runtime.cpp", "sha256": self.new_digest})

    def test_all_new_packet_members_are_provenance_including_failure_blob(self):
        result = self.derive()
        for member, value in self.packet["files"].items():
            logical = "datasets/provenance/" + p.PACKET_NAME + "/" + member
            self.assertEqual(result["harness_inputs"][logical], {"path": self.packet["archive"] + "/" + member, "sha256": value})

    def test_target_ctest_order_and_paths_are_preserved_or_advanced_exactly(self):
        result = self.derive()
        self.assertEqual(result["targets"], self.parent["targets"])
        self.assertEqual(result["ctest_expected_names"], self.parent["ctest_expected_names"])
        self.assertEqual(result["paths"]["snapshot"], "build/w20/source")
        self.assertEqual(result["paths"]["evidence"], "build/evidence/native-pass-34")
        self.assertEqual(result["paths"]["activation"], p.ACTIVE)

    def test_source_only_scope_cannot_borrow_historical_compile(self):
        result = self.derive()
        identity = result["integrated_cpu_source_identity"]
        self.assertIs(identity["Engine_runtime_compiled"], False)
        self.assertIs(identity["Engine_device_qualified"], False)
        self.assertEqual(identity["standalone_completed_contract_names"], [])
        self.assertEqual(result["historical_pass33_full_native_build"]["checked_inputs"], p.PARENT_BUILD_PINS)
        self.assertIs(result["native_built"], False)
        self.assertIs(result["gpu_qualified"], False)

    def test_derive_is_nonmutating_and_results_do_not_alias_parent(self):
        original = copy.deepcopy(self.parent)
        packet = copy.deepcopy(self.packet)
        result = self.derive()
        result["historical_pass33_current_packets"][0]["files"].clear()
        result["packets"][0]["files"].clear()
        self.assertEqual(self.parent, original)
        self.assertEqual(self.packet, packet)

    def test_no_added_removed_or_other_changed_project_key(self):
        variants = []
        added = copy.deepcopy(self.source); added["cpp/foreign.hpp"] = "a" * 64; variants.append(added)
        removed = copy.deepcopy(self.source); del removed["cpp/runtime.hpp"]; variants.append(removed)
        other = copy.deepcopy(self.source); other["cpp/runtime.hpp"] = "a" * 64; variants.append(other)
        unchanged = copy.deepcopy(self.parent["source_files"]); variants.append(unchanged)
        for source in variants:
            with self.subTest(source_count=len(source)), self.assertRaises(ValueError):
                self.derive(source=source)

    def test_parent_overlap_missing_runtime_and_packet_alias_refuse(self):
        overlapping = copy.deepcopy(self.parent)
        overlapping["packets"][1]["owned_files"]["cpp/runtime.cpp"] = "source/cpp/runtime.cpp"
        missing = copy.deepcopy(self.parent)
        del missing["packets"][0]["owned_files"]["cpp/runtime.cpp"]
        for parent in (overlapping, missing):
            with self.subTest(parent=parent["packets"][0]["name"]), self.assertRaises(ValueError):
                self.derive(parent=parent)
        packet = copy.deepcopy(self.packet); packet["name"] = self.parent["packets"][0]["name"]
        with self.assertRaises(ValueError): self.derive(packet=packet)

    def test_packet_cannot_take_unchanged_observer_key_or_reparent_source(self):
        for change in ("extra", "path", "digest"):
            packet = copy.deepcopy(self.packet)
            if change == "extra": packet["owned_files"]["cpp/runtime.hpp"] = "source/cpp/runtime.hpp"
            elif change == "path": packet["owned_files"]["cpp/runtime.cpp"] = "retained/runtime.cpp"
            else: packet["files"]["source/cpp/runtime.cpp"] = "a" * 64
            with self.subTest(change=change), self.assertRaises(ValueError): self.derive(packet=packet)

    def test_new_packet_provenance_collision_refuses_before_publication(self):
        parent = copy.deepcopy(self.parent)
        parent["harness_inputs"]["datasets/provenance/" + p.PACKET_NAME + "/proof.json"] = {"path": "old/proof.json", "sha256": "a" * 64}
        with self.assertRaises(ValueError): self.derive(parent=parent)

    def test_review_provenance_collision_refuses(self):
        parent = copy.deepcopy(self.parent)
        value = next(iter(self.recipe["checked_inputs"].values()))
        parent["harness_inputs"]["datasets/provenance/pass34-reviewed-inputs/" + value + ".bin"] = {"path": "old/proof", "sha256": value}
        with self.assertRaises(ValueError): self.derive(parent=parent)

    def test_recipe_requires_actual33_and_typed_source_only_scope(self):
        p.recipe_contract(self.recipe)
        changes = (("schema", True), ("epoch", 33), ("snapshot_epoch", 19), ("proposal_only", False),
                   ("parent_manifest_sha256", "a" * 64), ("activation_manifest_sha256", "a" * 64),
                   ("GPU_harness_included_in_ABI_inputs", True), ("CMake_owner_acknowledged", False))
        for name, value in changes:
            recipe = copy.deepcopy(self.recipe); recipe[name] = value
            with self.subTest(name=name), self.assertRaises(ValueError): p.recipe_contract(recipe)

    def test_missing_historical_build_pin_refuses(self):
        for name in p.PARENT_BUILD_PINS:
            recipe = copy.deepcopy(self.recipe); del recipe["checked_inputs"][name]
            with self.subTest(name=name), self.assertRaises(ValueError): p.recipe_contract(recipe)

    def test_ack_exact_context_and_disjoint_owner_holds(self):
        self.assertEqual(p.ack_contract(self.ack, self.parent, {"cpp/runtime.cpp": self.new_digest}, self.native), self.held)
        for change in ("missing", "changed", "overlap", "hold", "baseline"):
            ack = copy.deepcopy(self.ack)
            if change == "missing": del ack["source_files"]["CMakeLists.txt"]
            elif change == "changed": ack["source_files"]["cpp/runtime.hpp"] = "a" * 64
            elif change == "overlap": ack["owners"]["runtime"].append("CMakeLists.txt")
            elif change == "hold": ack["owner_source_holds"]["runtime"] = False
            else: ack["baseline"]["epoch"] = 32
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.ack_contract(ack, self.parent, {"cpp/runtime.cpp": self.new_digest}, self.native)

    def test_source_proof_typed_scope_and_native_identity(self):
        p.proof_contract(self.proof, self.packet, self.held, self.native)
        for key, expected in p.PROOF_ASSERTIONS.items():
            proof = copy.deepcopy(self.proof)
            proof[key] = True if type(expected) is int else not expected
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.proof_contract(proof, self.packet, self.held, self.native)
        proof = copy.deepcopy(self.proof); proof["protected_after"] = {}
        with self.assertRaises(ValueError): p.proof_contract(proof, self.packet, self.held, self.native)

    def test_packet_scope_assertions_cannot_omit_source_only_claim(self):
        for key in p.PROOF_ASSERTIONS:
            packet = copy.deepcopy(self.packet); del packet["proof_assertions"][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.proof_contract(self.proof, packet, self.held, self.native)

    def test_review_must_bind_current_ack_and_source(self):
        pins = {**self.held, self.recipe["owner_ack_path"]: self.recipe["owner_ack_sha256"]}
        review = {"status": "CLEAR_WITH_SCOPE", "process_exit": 0, "material_findings": [],
                  "GPU_used": False, "native_imported": False, "checked_inputs": pins}
        p.review_contract(review, pins)
        for change in ("old-runtime", "missing-ack", "not-clear", "bool-exit", "finding"):
            wrong = copy.deepcopy(review)
            if change == "old-runtime": wrong["checked_inputs"]["cpp/runtime.cpp"] = self.old["cpp/runtime.cpp"]
            elif change == "missing-ack": del wrong["checked_inputs"][self.recipe["owner_ack_path"]]
            elif change == "not-clear": wrong["status"] = "pending"
            elif change == "bool-exit": wrong["process_exit"] = True
            else: wrong["material_findings"] = ["material"]
            with self.subTest(change=change), self.assertRaises(ValueError): p.review_contract(wrong, pins)

    def test_real_check_packet_accepts_source_only_exit_without_compile(self):
        archive, packet = self.write_packet()
        self.assertNotIn("compile_exit", packet["proof_assertions"])
        self.assertEqual(epoch.check_packet(archive, packet), {"cpp/runtime.cpp": self.new_digest})

    def test_real_check_packet_refuses_extra_missing_tampered_and_false_proof(self):
        for change in ("extra", "missing", "tamper", "proof"):
            with tempfile.TemporaryDirectory() as directory:
                self.directory = Path(directory)
                archive, packet = self.write_packet()
                if change == "extra": (archive / "foreign.bin").write_bytes(b"unexpected")
                elif change == "missing": (archive / "proof.json").unlink()
                elif change == "tamper": (archive / "source/cpp/runtime.cpp").write_bytes(b"different")
                else:
                    bad = copy.deepcopy(self.proof); bad["Engine_runtime_compiled"] = True
                    (archive / "proof.json").write_bytes(json.dumps(bad, sort_keys=True).encode())
                    packet["files"] = epoch.inventory(archive); packet["files_tree_sha256"] = epoch.tree_digest(packet["files"])
                with self.subTest(change=change), self.assertRaises(epoch.EpochError): epoch.check_packet(archive, packet)

    def test_no_graphics_or_project_import_attempted(self):
        self.assertEqual(NoGraphics.attempts, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
