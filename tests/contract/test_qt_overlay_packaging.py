"""Guard the actual packaging witness without promoting CPU checks to graphics."""

import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proof():
    record = json.loads((ROOT / "compat/native-sdk/w10-qt-overlay-packaging-provenance.json").read_text())
    for relative, expected in record["artifact_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    return record


def test_w10_overlay_preserves_every_other_frozen_project_input():
    record = proof()
    before = json.loads((ROOT / "build/w9/source/wheel-source-manifest.json").read_text())
    after = json.loads((ROOT / "build/w10/source/wheel-source-manifest.json").read_text())
    assert before["source_files"].keys() == after["source_files"].keys()
    assert {key for key in after["source_files"] if before["source_files"][key] != after["source_files"][key]} == {"src/vispy/app/backends/_qt.py"}
    digest = hashlib.sha256()
    for relative, expected in sorted(after["source_files"].items()):
        assert sha(ROOT / "build/w10/source" / relative) == expected
        digest.update(relative.encode() + b"\0" + bytes.fromhex(expected))
    assert digest.hexdigest() == after["source_tree_sha256"] == record["source_tree_sha256"]
    assert not after["live_cpp_read"]


def test_actual_both_abi_wheels_have_matching_overlay_and_protected_activation():
    record = proof()
    assert set(record["leaves"]) == {"cp310", "cp312"}
    for abi, leaf in record["leaves"].items():
        assert leaf["process_exit"] == 0 and not leaf["graphics_qualified"]
        wheel = Path(leaf["wheel"])
        assert sha(wheel) == leaf["wheel_sha256"]
        with zipfile.ZipFile(wheel) as archive:
            assert hashlib.sha256(archive.read("vispy/app/backends/_qt.py")).hexdigest() == record["only_overlay"]["snapshot_sha256"]
            assert f"vispy/_dawn.{abi}-win_amd64.pyd" in archive.namelist()
            assert f"vispy/visuals/text/_sdf_cpu.{abi}-win_amd64.pyd" in archive.namelist()
        evidence = ROOT / leaf["evidence"]
        build = json.loads((evidence / "provenance.json").read_text())
        assert build["protected_before"] == build["protected_after"]
        assert build["CL_MPCount"] == "3" and not build["vendor_rebuilt"]
        assert all(value["cpp_items"] >= 0 for value in build["cpp_policy"].values())


def test_host_locks_change_only_wheel_and_remain_graphics_pending():
    record = proof()
    baseline = (ROOT / "tools/oracle_glue_requirements.txt").read_text()
    pattern = r"(?m)^vispy==0\.17\.0 \\\n(?:    --hash=sha256:[a-f0-9]+(?: \\)?\n)+"
    glue = (ROOT / record["hosts"]["glue"]["requirements"]).read_text()
    assert re.sub(pattern, "VISPY_WHEEL\n", baseline) == re.sub(r"(?m)^vispy @ .+\n", "VISPY_WHEEL\n", glue)
    dive_before = (ROOT / "compat/host-environments/dive-pyside2-candidate-w5-windows-cpython310.txt").read_text()
    dive_after = (ROOT / record["hosts"]["dive"]["requirements"]).read_text()
    assert re.sub(r"(?m)^vispy @ .+$", "VISPY_WHEEL", dive_before) == re.sub(r"(?m)^vispy @ .+$", "VISPY_WHEEL", dive_after)
    for host in record["hosts"].values():
        assert host["cpu_preflight"] == "passed" and not host["graphics_qualified"]
    assert not record["host_full_frame_parity_qualified"]
    assert not record["installed_core_graphics_and_rollback_qualified"]
