"""Installed plugin packaging evidence is distinct from graphics admission."""

import hashlib
import json
from pathlib import Path
try:
    import tomllib
except ImportError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "compat/host-environments"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records():
    proof = json.loads((DIRECTORY / "napari-threedee-packaging-provenance.json").read_text())
    registration = json.loads((ROOT / proof["registration"]).read_text())
    content = json.loads((ROOT / proof["wheel_content"]).read_text())
    source = json.loads((ROOT / proof["source_inventory"]).read_text())["source"]
    return proof, registration, content, source


def test_genuine_version_tag_and_recorded_dependencies():
    proof, _, _, source = records()
    pin = tomllib.loads((ROOT / "compat/hosts.lock.toml").read_text())["napari_threedee"]
    assert digest(ROOT / pin["packaging"]["provenance"]) == pin["packaging"]["provenance_sha256"]
    assert proof["commit"] == proof["tag_commit"] == pin["commit"]
    assert proof["tag"] == "v0.0.29" and proof["version"] == "0.0.29"
    assert proof["tag_object"] == pin["packaging"]["source_tag_object"]
    assert "object " + pin["commit"] in proof["tag_object_content"]
    assert proof["source_before_build_sha256"] == source["sha256"] == pin["source_tree_sha256"]
    assert proof["original_source_file_count"] == len(source["files"]) == 174
    assert proof["all_original_source_files_identical"] and not proof["tracked_source_changes"]
    assert not proof["version_override_environment"]
    for field in ("source_inventory", "prior_import_inventory", "runtime_requirements",
                  "runtime_build_requirements", "package_build_requirements",
                  "wheel_installation_requirements", "wheel_content", "generated_version",
                  "registration", "registration_tool", "first_probe_failure"):
        assert digest(ROOT / proof[field]) == proof[field + "_sha256"], field
    assert proof["runtime_dependency_versions_unchanged"]
    assert proof["runtime_distribution_count"] == 118
    assert len(proof["build_environment"]["packages"]) == 10


def test_original_package_sources_and_declared_manifest_are_unchanged():
    proof, registration, content, source = records()
    prefix = "src/napari_threedee/"
    expected = {item["path"].removeprefix(prefix): item["sha256"]
                for item in source["files"] if item["path"].startswith(prefix)}
    installed = registration["installed_source_files"]
    assert set(installed) - set(expected) == {"_version.py"}
    assert all(installed[name] == value for name, value in expected.items())
    assert proof["generated_source_files"] == ["src/napari_threedee/_version.py"]
    assert installed["_version.py"] == content["generated_version_sha256"]
    assert digest(ROOT / proof["generated_version"]) == installed["_version.py"]
    assert digest(DIRECTORY / "napari-threedee-pinned-manifest.yaml") == expected["napari.yaml"]
    assert content["manifest_sha256"] == registration["installed_manifest"]["sha256"] == expected["napari.yaml"]
    pyproject_sha = next(item["sha256"] for item in source["files"] if item["path"] == "pyproject.toml")
    metadata_path = DIRECTORY / "napari-threedee-pinned-pyproject.toml"
    assert digest(metadata_path) == pyproject_sha
    declared = tomllib.loads(metadata_path.read_text())
    assert declared["tool"]["hatch"]["version"]["source"] == "vcs"
    assert declared["project"]["entry-points"]["napari.manifest"] == {
        "napari-threedee": "napari_threedee:napari.yaml"}
    assert proof["wheel_build_count"] == 2 and proof["repeat_wheels_byte_identical"]
    assert proof["wheel_sha256"] == content["wheel_sha256"] == registration["wheel_sha256"]


def test_public_discovery_and_command_resolution_without_graphics():
    _, registration, _, _ = records()
    assert not registration["errors"]
    assert registration["version"] == registration["entry_point"]["version"] == "0.0.29"
    assert registration["entry_point"]["group"] == "napari.manifest"
    assert registration["entry_point"]["value"] == "napari_threedee:napari.yaml"
    assert "napari-threedee" in registration["registered_manifest_names"]
    assert len(registration["widgets"]) == 11
    assert len(registration["resolved_commands"]) == 12
    declared = {command["id"]: command["python_name"]
                for command in registration["manifest"]["contributions"]["commands"]}
    resolved = {command["id"]: command["python_name"] for command in registration["resolved_commands"]}
    assert resolved == declared
    assert all(command["executed"] is False for command in registration["resolved_commands"])
    assert len(registration["wheel_files_verified_against_installation"]) == 121
    assert all("site-packages" in module["origin"] for module in registration["modules"])
    assert not registration["qapplication_created"] and not registration["current_opengl_context"]
    assert not registration["dawn_modules"] and not registration["other_qt_bindings"]
    assert registration["viewer_constructed"] is registration["widget_constructed"] is False
    assert registration["rendering_qualified"] is False


def test_registration_does_not_admit_a_plugin_graphics_fixture():
    proof, registration, _, _ = records()
    assert proof["graphics_qualification"] == "pending"
    assert proof["rendering_qualified"] is registration["rendering_qualified"] is False
    assert "Plugin picking/dragging and callback lifecycle" in proof["remaining_qualification"]
    assert proof["original_import_only_environment_preserved"].endswith("napari-threedee-cpython312-pyqt6")
