"""Frozen evidence for standard CPython 3.13/3.14 build preparation."""

import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import pytest
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
try:
    import tomllib
except ImportError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(params=[("313", "3.13.8"), ("314", "3.14.0")])
def preparation(request):
    suffix, version = request.param
    evidence = ROOT / f"compat/cp{suffix}-candidate/preparation.json"
    record = json.loads(evidence.read_text())
    assert record["interpreter_pin"] == version
    return record


def test_observed_standard_interpreter_and_isolated_imports(preparation):
    observed = preparation["installed_environment"]
    abi = preparation["abi"]
    assert observed["python"] == preparation["interpreter_pin"]
    assert observed["extension_suffix"] == f".{abi}-win_amd64.pyd"
    assert observed["pointer_bytes"] == 8
    assert observed["gil_enabled"] and not observed["py_gil_disabled"]
    assert not preparation["free_threaded"]
    environment = PureWindowsPath(preparation["environment"])
    assert PureWindowsPath(observed["executable"]).is_relative_to(environment)
    for module in observed["modules"]:
        assert PureWindowsPath(module["origin"]).is_relative_to(environment)
        assert re.fullmatch(r"[0-9a-f]{64}", module["sha256"])
    assert preparation["cmake"]["version"] == "cmake version 4.4.4"
    assert PureWindowsPath(preparation["cmake"]["origin"]).is_relative_to(environment)


def test_hash_lock_matches_original_uv_wheels_and_installed_closure(preparation):
    assert digest(ROOT / "cmake/prepare_newer_candidates.py") == preparation["preparation_script_sha256"]
    assert digest(ROOT / "uv.lock") == preparation["root_lock_sha256"]
    assert digest(ROOT / "pyproject.toml") == preparation["pyproject_sha256"]
    requirements = ROOT / preparation["requirements"]
    assert digest(requirements) == preparation["requirements_sha256"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    target = tuple(map(int, preparation["interpreter_pin"].split(".")[:2]))
    supported = set(cpython_tags(target, [preparation["abi"]], ["win_amd64"]))
    supported.update(compatible_tags(target, preparation["abi"], ["win_amd64"]))
    expected = {}
    for package in preparation["packages"]:
        expected[package["name"]] = package["version"]
        original = next(item for item in lock["package"]
                        if item["name"] == package["name"] and item["version"] == package["version"])
        assert package["wheels"]
        for wheel in package["wheels"]:
            assert wheel in original["wheels"]
            assert parse_wheel_filename(wheel["url"].split("/")[-1])[3] & supported
            assert "--hash=" + wheel["hash"] in requirements.read_text()
    actual = {canonicalize_name(item["name"]): item["version"]
              for item in preparation["installed_environment"]["packages"]}
    assert actual == expected
    assert actual["numpy"] == "2.5.3" and len(actual) == 7


def test_preparation_preserves_historical_native_evidence_without_admitting_wheel(preparation):
    assert preparation["qualification"] == "build_preparation_only"
    assert not preparation["wheel_built"] and not preparation["native_graphics_qualified"]
    assert preparation["root_protected_binary_inventory_unchanged"]
    assert preparation["root_protected_binaries_before"] == preparation["root_protected_binaries_after"]
    assert preparation["root_protected_binaries_before"]
    assert preparation["toolchain"]["generator_toolset"].startswith("v143,version=")
    assert preparation["toolchain"]["windows_sdk"] == "10.0.22621.0"
    assert preparation["toolchain"]["windows_sdk_verified_from_generated_project"]
    assert preparation["remaining_gates"]


def test_frozen_source_script_has_separate_build_and_live_binary_guard(preparation):
    path = ROOT / preparation["frozen_source_build_script"]
    assert digest(path) == preparation["frozen_source_build_script_sha256"]
    text = path.read_text()
    assert "wheel-source-manifest.json" in text
    assert "Snapshot packaging inputs differ" in text
    assert "cmake.define.VISPY_INPLACE=OFF" in text
    assert "cmake.define.VISPY_VERIFY_DEPENDENCIES=ON" in text
    assert "$before = Get-ProtectedBinaries" in text and "$after = Get-ProtectedBinaries" in text
    assert "root_protected_binaries_before" not in text
    assert "build/n" + preparation["abi"][3:] in text
    assert "--no-build-isolation" in text
    assert preparation["build_script_qualification"] == "PowerShell parser only; not executed"
