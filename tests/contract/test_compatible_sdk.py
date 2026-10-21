"""Actual compatible SDK evidence must preserve failed host parity separately."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_actual_compatible_sdk_leaves_and_core_consumer_have_immutable_origins():
    proof = load(ROOT / "compat/native-sdk/w8b-compatible-windows-provenance.json")
    for name, expected in proof["evidence_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert proof["full_vendor_compatibility_rebuild_completed"]
    assert not proof["old_default_archives_reused"] and not proof["python_abi_objects_reused"]
    assert proof["source_native_artifacts_unchanged"]
    assert proof["compiler_policy"] == "msvc-stl-init-in-situ-v1"
    assert set(proof["leaves"]) == {"cp310", "cp312"}
    consumer = proof["cp312_clean_core_consumer"]
    assert consumer["exit_code"] == consumer["skipped"] == 0 and consumer["passed"] == 1
    assert consumer["native_text_sdf_assets_notices_and_rollback_verified"]
    assert consumer["evidence"]["device"]["ok"] and not consumer["evidence"]["device"]["software"]
    assert not proof["compatible_five_abi_matrix_qualified"]
    assert not proof["full_binding_host_platform_matrix_qualified"]


def test_actual_sdk3_verifies_and_old_default_sdk_cannot_mix_with_new_policy():
    sdk = module("compatible_sdk_policy", ROOT / "cmake/native_sdk.py")
    proof = load(ROOT / "compat/native-sdk/w8b-compatible-windows-provenance.json")
    prefix = ROOT / proof["sdk"]
    manifest = load(prefix / "manifest.json")
    assert len(sdk.verify(prefix, proof["sdk_manifest_sha256"], ROOT / "cmake/dependencies.lock.json", manifest["producer"])["files"]) == 224
    earlier = ROOT / "build/native-sdk/windows-x64-release-2"
    with pytest.raises(sdk.SDKError, match="Unsupported SDK format"):
        sdk.verify(earlier, sdk.sha256(earlier / "manifest.json"), ROOT / "cmake/dependencies.lock.json", manifest["producer"])


def test_old_crt_init_pass_does_not_admit_inexact_dive_pixels_or_ordinary_host():
    compare = module("compatible_dive_compare", ROOT / "tools/compare_dive_installed.py")
    result = compare.compare(ROOT / "tests/reference/dive-pyside2-style-opengl",
                             ROOT / "build/evidence/dive-pyside2-style-candidate-w8b-pass-1")
    assert result["legacy_init_render_and_clean_exit_verified"]
    assert not result["scoped_pixel_parity_qualified"]
    assert not result["ordinary_host_teardown_qualified"] and not result["scatter_qualified"]
    for item in result["results"].values():
        assert item["process_exit_code"] == 0 and not item["full_frame_exact"]
        assert set(item["parameter_differences"]) == {"native_mro"}
        for frame in item["frames"].values():
            assert not frame["exact"] and not frame["file_bytes_exact"]
            assert frame["pixels_differing"] == 2178 and frame["channel_max_abs"] == [1, 1, 1, 64]
        assert not any(item["png_bytes_exact"].values())
    cpu = load(ROOT / "build/evidence/w8b-dive-pyside2-cpu-preflight/cpu.json")
    assert cpu["qt_imported_before_native"] and cpu["native_shutdown_mutex_verified"]
    assert cpu["loaded_msvc_runtime_sha256"] == "f87819ae8c6f7c90d3237a1abb9809e8cba9dcd0c80ac3f0969a5e68ef652ca4"
    assert not cpu["graphics_device_created"] and not cpu["qapplication_created"]
