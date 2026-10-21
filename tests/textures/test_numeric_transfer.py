"""Exact storage-transfer acceptance; CPU tests never import the renderer."""
import json
import os
from pathlib import Path
import traceback

import numpy as np
import pytest

from tools.fixture_texture_numeric import (
    CASES, ROOT, WIDTH, assert_exact, bytes_sha256, capture_transfer, contract,
    load_case, logical_red, require_matching_activation, sha256, specification,
    verified_corpus,
)


def test_cpu_all_twelve_pairs_preserve_actual_upstream_input_and_storage_bytes():
    corpus = verified_corpus()
    assert len(corpus["cases"]) == len(CASES) == 12
    counts = {case["dtype"]: case["count"] for case in corpus["cases"]}
    assert counts == {"u8": 256, "i8": 256, "u16": 65536, "i16": 65536,
                      "u32": 70568, "i32": 69675}
    for name in CASES:
        case, source, expected = load_case(name)
        spec = specification(name)
        assert source.dtype.kind in "ui" and source.shape[1:] == (WIDTH, 1)
        assert spec["logical_count"] == case["count"] == expected.size
        assert bytes_sha256(source) == spec["source_sha256"]
        assert spec["internalformat"] == ("r32f" if expected.dtype.kind == "f" else None)
        assert_exact(name, expected)
    assert contract()["GPU_used"] is False
    assert contract()["matching_native28_hardware_seen"] is False


def test_cpu_row_orientation_padding_and_float_bits_cannot_be_silently_changed():
    for name in CASES:
        case, source, expected = load_case(name)
        padded = np.full(source.shape[:2], expected[-1], dtype=expected.dtype)
        padded.reshape(-1)[:expected.size] = expected
        capture = np.zeros((*source.shape[:2], 4), dtype=expected.dtype)
        capture[..., 0] = padded[::-1]
        actual = logical_red(capture, name)
        assert actual.tobytes() == expected.tobytes()
        assert_exact(name, actual)
        altered = actual.copy()
        if altered.dtype.kind == "f":
            altered.view(np.uint32)[expected.size // 2] ^= np.uint32(1)
        else:
            altered[expected.size // 2] ^= np.uint8(1)
        with pytest.raises(AssertionError, match="exact stored red byte/float-bit mismatch"):
            assert_exact(name, altered)
        assert source.size - case["count"] < WIDTH
        if source.size > case["count"]:
            assert np.all(source.reshape(-1)[case["count"]:] == source.reshape(-1)[case["count"] - 1])
        if source.shape[0] > 1:
            wrong_rows = capture[..., 0].reshape(-1)[:case["count"]]
            assert wrong_rows.tobytes() != expected.tobytes(), "orientation witness is required"


def test_cpu_hardware_requires_explicit_matching_activation_before_any_canvas(monkeypatch):
    monkeypatch.delenv("VISPY_NUMERIC_TRANSFER_EXPECTED_ACTIVATION_SHA256", raising=False)
    with pytest.raises(RuntimeError, match="explicitly pinned active28"):
        require_matching_activation()


@pytest.fixture(scope="module")
def hardware_job():
    proof = require_matching_activation()
    output = os.environ.get("VISPY_NUMERIC_TRANSFER_EVIDENCE")
    assert output, "numeric hardware evidence must use an explicit fresh per-job directory"
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    pinned = {str(path.relative_to(ROOT)): sha256(path) for path in
              (ROOT / "tools/fixture_texture_numeric.py", Path(__file__))}
    proof.update(sources=pinned, PID=os.getpid())
    (directory / "inputs.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    try:
        yield directory
    finally:
        after = require_matching_activation()
        current = {path: sha256(ROOT / path) for path in pinned}
        result = {"native_unchanged": after["native_hashes"] == proof["native_hashes"],
                  "sources_unchanged": current == pinned, "sources_after": current}
        (directory / "protected-after.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        assert result["native_unchanged"] and result["sources_unchanged"]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_numeric_integer_upload_typed_copy_matches_actual_opengl_bits(name, hardware_job):
    evidence = hardware_job / name
    evidence.mkdir(exist_ok=False)
    witness = {"case": name, "GPU_used": False, "outcome": "started"}
    try:
        capture = capture_transfer(name, witness)
        np.save(evidence / "capture.npy", capture, allow_pickle=False)
        actual = logical_red(capture, name)
        _, _, expected = load_case(name)
        np.save(evidence / "logical-red.npy", actual, allow_pickle=False)
        left, right = (actual.view(np.uint32), expected.view(np.uint32)) if expected.dtype.kind == "f" else (actual, expected)
        differences = np.flatnonzero(left != right)
        np.save(evidence / "mismatch-indices.npy", differences, allow_pickle=False)
        witness["comparison"] = {"logical_count": expected.size, "mismatches": int(differences.size),
                                 "actual_sha256": bytes_sha256(actual), "expected_sha256": bytes_sha256(expected),
                                 "first_indices": differences[:12].tolist()}
        commands = witness["filtered_glir"]
        assert not any(command[0] == "DRAW" for command in commands), "no shader/draw may mediate conversion"
        upload = [command for command in commands if command[0] == "DATA" and command[1] == witness["texture"]["id"]]
        assert len(upload) == 1 and upload[0][3]["array"]["sha256"] == witness["parameters"]["source_sha256"]
        assert_exact(name, actual)
        witness["outcome"] = "passed"
    except BaseException:
        witness.update(outcome="failed", traceback=traceback.format_exc())
        raise
    finally:
        witness["artifacts"] = {path.name: sha256(path) for path in evidence.glob("*.npy")}
        (evidence / "observations.json").write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")
