"""Evidence gates for isolated installed plugin consumers; no GPU construction."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "compat/host-environments"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_candidate_uses_exact_installed_wheels_and_one_binding():
    proof = load(DIRECTORY / "napari-threedee-candidate-provenance-w5.json")
    registration = load(DIRECTORY / "napari-threedee-candidate-registration-w5.json")
    upstream = load(DIRECTORY / "napari-threedee-registration.json")
    for path, expected in proof["evidence_sha256"].items():
        assert digest(ROOT / path) == expected, path
    assert not registration["errors"]
    assert proof["vispy_wheel_sha256"] == registration["vispy_wheel_sha256"] == (
        "e94ab51c4d3ad37333506af3c1b99ea3ce05cccd34bb4ea682e63ad70f2c1c3c"
    )
    assert registration["native_module"]["sha256"] == (
        "c3296e22d49a3f94953797b04bf8144b128cdb8e44c132d58370443120404ff9"
    )
    assert registration["wheel_sha256"] == upstream["wheel_sha256"]
    versions = lambda record: {item["name"].lower(): item["version"]
                               for item in record["distributions"]}
    original, installed = versions(upstream), versions(registration)
    assert original.keys() == installed.keys()
    assert {key for key in original if original[key] != installed[key]} == {"vispy"}
    assert installed["vispy"] == "0.17.0+vulkan.1"
    assert {key for key in installed if key in {"pyqt5", "pyqt6", "pyside2", "pyside6"}} == {"pyqt6"}
    assert proof["installed_distribution_count"] == len(installed) == 118


def test_candidate_discovery_does_not_claim_graphics_admission():
    proof = load(DIRECTORY / "napari-threedee-candidate-provenance-w5.json")
    registration = load(DIRECTORY / "napari-threedee-candidate-registration-w5.json")
    assert len(registration["widgets"]) == 11
    assert len(registration["resolved_commands"]) == 12
    assert len(registration["vispy_wheel_files_verified"]) > 250
    assert registration["installed_source_files"] == load(
        DIRECTORY / "napari-threedee-registration.json"
    )["installed_source_files"]
    assert registration["dawn_modules"] == ["vispy._dawn"]
    assert not registration["qapplication_created"]
    assert not registration["current_opengl_context"]
    assert not registration["other_qt_bindings"]
    assert proof["graphics_qualified"] is registration["rendering_qualified"] is False
    failed = load(DIRECTORY / "napari-threedee-candidate-registration-probe-failure-1.json")
    assert len(failed["errors"]) == 1 and "FileNotFoundError" in failed["errors"][0]


def test_cp310_is_a_real_built_leaf_with_pending_consumer_gates():
    proof = load(ROOT / "compat/native-sdk/w5-cp310-build-provenance.json")
    assert proof["build_exit_code"] == 0 and proof["source_native_artifacts_unchanged"]
    for path, expected in proof["evidence_sha256"].items():
        assert digest(ROOT / path) == expected, path
    assert proof["wheel_sha256"] == "6a1b9f74f7eac4e8fcd665fa78302b2018b71e3929576dfd1571ff53b3857e34"
    assert set(proof["wheel_native_sha256"]) == {
        "vispy/_dawn.cp310-win_amd64.pyd",
        "vispy/visuals/text/_sdf_cpu.cp310-win_amd64.pyd",
        "vispy/VkLayer_vispy_submit.dll",
    }
    assert not proof["external_consumer_qualified"] and not proof["graphics_qualified"]
    assert "NumPy2.2.6 build versus NumPy1.26.4 runtime compiled SDF proof" in proof["remaining"]


def test_numpy246_pair_changes_only_the_recorded_dependency():
    proof = load(DIRECTORY / "napari-threedee-numpy246-paired-provenance-w5.json")
    assert proof["original_numpy253_environments_preserved"]
    assert proof["graphics_qualified"] is False
    for path, expected in proof["evidence_sha256"].items():
        assert digest(ROOT / path) == expected, path
    for kind, original in (("upstream", "napari-threedee-registration.json"),
                           ("candidate", "napari-threedee-candidate-registration-w5.json")):
        registration = load(ROOT / proof["environments"][kind]["registration"])
        first = load(DIRECTORY / original)
        versions = lambda value: {item["name"].lower(): item["version"]
                                  for item in value["distributions"]}
        before, after = versions(first), versions(registration)
        assert before.keys() == after.keys()
        assert {key for key in before if before[key] != after[key]} == {"numpy"}
        assert after["numpy"] == "2.4.6"
        assert registration["installed_source_files"] == first["installed_source_files"]
        assert not registration["errors"]
        assert len(registration["widgets"]) == 11
        assert len(registration["resolved_commands"]) == 12
        cpu = load(DIRECTORY / f"napari-threedee-{kind}-numpy246-cpu-w5.json")
        assert cpu["public_row_stack_result"] == [[1.25, -2.5, 7.0], [9.0, 0.125, -4.75]]
        assert cpu["numpy_version"] == "2.4.6" and cpu["plugin_version"] == "0.0.29"
        assert not cpu["qapplication_created"] and not cpu["graphics_context_created"]
        assert not cpu["graphics_device_created"] and not cpu["rendering_qualified"]
