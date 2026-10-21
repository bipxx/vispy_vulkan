"""Exact public upload/copy gates from the preserved OpenGL numeric corpus.

Integer input arrays stay integer through Texture2D.  An attached framebuffer
and typed read_pixels copy expose the storage conversion without a shader.
Importing this module or sealing its inputs does not import VisPy/create a GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "build/texture-numeric-work/corpus-2"
CORPUS_SHA256 = "6dcec4e1ff70ecfe662d470c9de2aaaf26100f467d97f64247fee715d6e884e0"
WIDTH = 256
DTYPES = {"u8": "|u1", "i8": "|i1", "u16": "<u2", "i16": "<i2",
          "u32": "<u4", "i32": "<i4"}
CASES = tuple(storage + "_" + dtype for dtype in
              ("uint8", "int8", "uint16", "int16", "uint32", "int32")
              for storage in ("unsized_red", "r32f"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bytes_sha256(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verified_corpus():
    assert sha256(CORPUS / "authoring.json") == CORPUS_SHA256
    manifest = _json(CORPUS / "authoring.json")
    assert len(manifest["cases"]) == 12
    assert {case["name"] for case in manifest["cases"]} == set(CASES)
    assert manifest["GPU_used"] is False and manifest["candidate_seen"] is False
    for case in manifest["cases"]:
        for key in ("input", "expected"):
            assert sha256(CORPUS / case[key]) == manifest["files"][case[key]]
        for key in ("upstream_input", "upstream_actual"):
            assert sha256(ROOT / case[key]) == case[key + "_sha256"]
    return manifest


def load_case(name):
    manifest = verified_corpus()
    case = next(case for case in manifest["cases"] if case["name"] == name)
    source = np.fromfile(CORPUS / case["input"], dtype=DTYPES[case["dtype"]])
    expected_dtype = np.dtype("<f4" if case["internal"] == "r32f" else "|u1")
    expected = np.fromfile(CORPUS / case["expected"], dtype=expected_dtype)
    assert source.size == expected.size == case["count"]
    # These .bin files are the logical prefix of the actual retained upstream
    # arrays; neither conversion nor expected generation occurs here.
    original = np.load(ROOT / case["upstream_input"], allow_pickle=False)
    actual = np.load(ROOT / case["upstream_actual"], allow_pickle=False)
    assert source.tobytes() == original.reshape(-1)[:source.size].tobytes()
    assert expected.tobytes() == actual.reshape(-1)[:expected.size].tobytes()
    height = math.ceil(source.size / WIDTH)
    padded = np.full(height * WIDTH, source[-1], dtype=source.dtype)
    padded[:source.size] = source
    return case, padded.reshape(height, WIDTH, 1), expected


def specification(name):
    case, source, expected = load_case(name)
    return {"name": name, "source_dtype": source.dtype.str,
            "source_shape": list(source.shape), "logical_count": case["count"],
            "padding_count": source.size - case["count"],
            "padding": "repeat final source value; excluded from comparison",
            "format": "red", "internalformat": "r32f" if case["internal"] == "r32f" else None,
            "out_type": "float" if expected.dtype.kind == "f" else "unsigned_byte",
            "expected_dtype": expected.dtype.str,
            "source_sha256": bytes_sha256(source),
            "logical_input_sha256": sha256(CORPUS / case["input"]),
            "expected_sha256": sha256(CORPUS / case["expected"]),
            "corpus_sha256": CORPUS_SHA256,
            "operation": "integer Texture2D -> attached FrameBuffer -> typed read_pixels; no draw/shader",
            "orientation": "reverse read_pixels top-left rows to original upload row order",
            "comparison": "exact logical red bytes; float32 compared as uint32 bits",
            "readbacks": 1, "explicit_finish_calls": 0}


def logical_red(capture, name):
    spec = specification(name)
    height, width, _ = spec["source_shape"]
    assert capture.shape == (height, width, 4)
    assert capture.dtype == np.dtype(spec["expected_dtype"])
    return np.ascontiguousarray(capture[::-1, :, 0]).reshape(-1)[:spec["logical_count"]]


def assert_exact(name, actual):
    _, _, expected = load_case(name)
    assert actual.shape == expected.shape and actual.dtype == expected.dtype
    left, right = (actual.view(np.uint32), expected.view(np.uint32)) if expected.dtype.kind == "f" else (actual, expected)
    mismatches = np.flatnonzero(left != right)
    assert not mismatches.size, (name, "exact stored red byte/float-bit mismatch",
                                 int(mismatches.size), mismatches[:12].tolist())


def contract():
    return {"schema": 1, "GPU_used": False,
            "matching_native28_hardware_seen": False,
            "expected_origin": "unchanged upstream glGetTexImage arrays retained before numeric implementation",
            "cases": [specification(name) for name in CASES],
            "scope_limits": ["Observed R8/R32F storage pairs and driver only.",
                             "8/16-bit domains exhaustive; 32-bit boundary/seeded samples are finite.",
                             "No shader sampling, mixed-revision or other-format/driver claim."]}


def require_matching_activation():
    """Reject an implicit/old candidate before importing its native module."""
    digest = os.environ.get("VISPY_NUMERIC_TRANSFER_EXPECTED_ACTIVATION_SHA256", "")
    path = Path(os.environ.get("VISPY_NUMERIC_TRANSFER_ACTIVATION",
                              ROOT / "build/evidence/native-pass-28/activation.json")).resolve()
    if len(digest) != 64 or path.name != "activation.json" or path.parent.name != "native-pass-28":
        raise RuntimeError("numeric transfer requires explicitly pinned active28 activation")
    assert sha256(path) == digest, "numeric transfer activation identity changed"
    activation = _json(path)
    paths = {"_dawn.cp312-win_amd64.pyd": ROOT / "src/vispy/_dawn.cp312-win_amd64.pyd",
             "_sdf_cpu.cp312-win_amd64.pyd": ROOT / "src/vispy/visuals/text/_sdf_cpu.cp312-win_amd64.pyd",
             "VkLayer_vispy_submit.dll": ROOT / "src/vispy/VkLayer_vispy_submit.dll",
             "VkLayer_vispy_submit.json": ROOT / "src/vispy/VkLayer_vispy_submit.json"}
    for name, target in paths.items():
        assert sha256(target) == activation["activated"][name], name
    return {"path": str(path), "sha256": digest, "activation": activation,
            "native_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in paths.values()}}


def capture_transfer(name, witness):
    """Only this hardware path imports VisPy; the caller guards its epoch."""
    from vispy import app, gloo, _dawn
    import vispy
    from .fixture_gloo import freeze

    spec = specification(name)
    _, source, _ = load_case(name)
    witness.update(parameters=spec, vispy_origin=str(Path(vispy.__file__).resolve()),
                   native_origin=str(Path(_dawn.__file__).resolve()),
                   native_sha256=sha256(_dawn.__file__), device=dict(_dawn.device_info()),
                   filtered_glir=[], GPU_used=True)
    canvas = None
    parser = None
    original = None
    try:
        canvas = app.Canvas(app="dawn_headless", size=(WIDTH, source.shape[0]),
                            show=False, autoswap=False, config={"samples": 0})
        canvas.set_current()
        parser = canvas.context.shared.parser
        original = parser.parse

        def parse(commands):
            witness["filtered_glir"].extend(freeze(command) for command in commands)
            return original(commands)

        parser.parse = parse
        witness["before"] = dict(_dawn.probe())
        texture = gloo.Texture2D(source, format="red", internalformat=spec["internalformat"],
                                 interpolation="nearest", wrapping="clamp_to_edge")
        witness["texture"] = {"id": texture.id, "shape": list(texture.shape),
                              "format": texture.format, "internalformat": texture.internalformat}
        with gloo.FrameBuffer(color=texture):
            capture = gloo.read_pixels((0, 0, WIDTH, source.shape[0]), alpha=True,
                                       out_type=spec["out_type"])
        witness["after_read"] = dict(_dawn.probe())
        return capture
    finally:
        if canvas is not None:
            canvas.close()
        if parser is not None and original is not None:
            parser.parse = original
        witness["after_cleanup"] = dict(_dawn.probe())


def seal_authoring(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    value = contract()
    value["sources"] = {}
    for relative in ("tools/fixture_texture_numeric.py", "tests/textures/test_numeric_transfer.py"):
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        value["sources"][relative] = sha256(target)
    value["corpus_authoring_sha256"] = CORPUS_SHA256
    shutil.copyfile(CORPUS / "authoring.json", output / "corpus-authoring.json")
    value["arrays"] = {}
    for name in CASES:
        _, source, expected = load_case(name)
        for key, array in (("input", source), ("expected", expected)):
            path = output / (name + "." + key + ".npy")
            np.save(path, array, allow_pickle=False)
            value["arrays"][path.name] = sha256(path)
    value["hardware_command"] = {
        "command": [".venv/Scripts/python.exe", "-m", "pytest", "tests/textures/test_numeric_transfer.py", "-m", "gpu", "-q"],
        "required_environment": {"VISPY_NUMERIC_TRANSFER_EXPECTED_ACTIVATION_SHA256": "explicit reviewed native28 activation SHA256",
                                 "VISPY_NUMERIC_TRANSFER_EVIDENCE": "new per-job output directory"},
        "authorization": "explicit exclusive GPU reservation required; no hardware job performed by sealing"}
    path = output / "authoring.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"authoring": str(path), "sha256": sha256(path), "cases": len(CASES), "GPU_used": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", type=Path, required=True)
    args = parser.parse_args()
    seal_authoring(args.seal)
