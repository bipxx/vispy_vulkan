"""Pending public subdata and explicitly scoped real queue-filter parity."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_buffer_ordering import (CASES, COMPARISON, INTERLEAVED, actual_cpu_queue_transcript,
    array_record, assert_image, assert_trace, case_contract, expected_image,
    expected_single_flush_transcripts, input_arrays, render)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/buffer-ordering-opengl"
EVIDENCE = Path(os.environ.get("VISPY_BUFFER_ORDERING_EVIDENCE", str(ROOT / "build/evidence/buffer-ordering-candidate")))

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def test_middle_patch_preserves_sentinel_fields_positions_and_outside_vertices():
    data = input_arrays(CASES[0])
    assert INTERLEAVED.itemsize == 28
    assert INTERLEAVED.fields["a_position"][1] == 4
    assert INTERLEAVED.fields["a_color"][1] == 12
    outside = np.r_[0:6, 12:18]
    assert np.array_equal(data["initial"][outside], data["final"][outside])
    for field in ("a_position", "sentinel_left", "sentinel_right"):
        assert np.array_equal(data["initial"][field], data["final"][field])
    assert np.array_equal(data["initial"]["a_color"][6:12], np.tile((0, 1, 0), (6, 1)))
    assert np.array_equal(data["final"]["a_color"][6:12], np.tile((1, 1, 0), (6, 1)))
    image = expected_image(CASES[0])
    assert image[18, 15].tolist() == [0, 255, 0, 255]
    assert image[5, 15].tolist() == [255, 255, 0, 255]

def test_actual_installed_queue_filter_preserves_draw_and_drops_earlier_data():
    actual = actual_cpu_queue_transcript()
    assert actual["actual_installed_queue_flush"] and not actual["graphics_context_created"]
    assert actual["canonical"] == expected_single_flush_transcripts()
    assert [command[0] for command in actual["raw"]] == ["DATA", "DRAW", "SIZE", "DATA", "DRAW"]
    assert [command[0] for command in actual["filtered"]] == ["DRAW", "SIZE", "DATA", "DRAW"]
    arrays = input_arrays(CASES[1])
    assert arrays["early_partial"].nbytes < arrays["initial"].nbytes < 96
    assert arrays["late_partial"].nbytes < 96
    assert array_record(arrays["early_partial"])["sha256"] != array_record(arrays["initial"])["sha256"]

def test_buffer_ordering_authoring_and_upstream_filter_inputs_are_frozen():
    authoring = json.loads((REFERENCE / "authoring.json").read_text())
    assert authoring["candidate_seen"] is False and authoring["GPU_used"] is False
    assert authoring["comparison"] == COMPARISON
    assert authoring["cases"] == {name: case_contract(name) for name in CASES}
    for path, digest in authoring["sources_sha256"].items():
        assert _sha(ROOT / path) == digest

@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_pending_buffer_ordering_matches_independent_opengl(name):
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    assert manifest["provenance"]["kind"] == "upstream"
    assert manifest["comparison"] == COMPARISON
    assert manifest["processes"][name]["exit_code"] == 0
    record = manifest["fixtures"][name]
    for artifact in record["artifacts"].values():
        assert _sha(REFERENCE / artifact["file"]) == artifact["sha256"]
    reference = np.load(REFERENCE / record["artifacts"]["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, parameters, observations = render(name)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", np.abs(image.astype(np.int16) - reference.astype(np.int16)), allow_pickle=False)
    for suffix, value in (("filtered_glir", commands), ("expanded_shaders", shaders), ("parameters", parameters), ("observations", observations)):
        (EVIDENCE / f"{name}.{suffix}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    assert parameters == record["parameters"] == case_contract(name)
    assert commands and shaders
    assert_trace(name, commands, observations)
    assert_image(name, image)
    assert np.array_equal(image, reference)
