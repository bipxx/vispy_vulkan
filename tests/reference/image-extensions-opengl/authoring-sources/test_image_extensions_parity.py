"""Required image/label workflows against separately installed pinned OpenGL."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.fixture_image_extensions import (CASES, COMPARISON, HIGH_A, HIGH_B,
    array_record, assert_landmarks, case_contract, final_arrays, input_arrays, paint_mask, render)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "tests/reference/image-extensions-opengl"
EVIDENCE = ROOT / "build/evidence/image-extensions-candidate"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_frozen_authoring_data_and_criteria_are_independent():
    authoring = json.loads((REFERENCE / "authoring.json").read_text(encoding="utf-8"))
    assert authoring["candidate_seen"] is False and authoring["GPU_used"] is False
    assert authoring["comparison"] == COMPARISON == {
        "full_frame_exact": True, "landmark_max_abs_u8": 1, "candidate_alignment_or_color_fit": False}
    assert authoring["cases"] == {name: case_contract(name) for name in CASES}
    for source, sha in authoring["sources_sha256"].items():
        assert _sha(ROOT / source) == sha


def test_label_and_level_revisions_have_distinct_analytic_sentinels():
    labels = input_arrays("labels_signed_remap")[0]
    assert labels.dtype == np.int32
    assert np.unique(labels).tolist() == [-7, 0, HIGH_A, HIGH_B]
    assert np.float32(HIGH_A) == np.float32(HIGH_B), "fixture must detect accidental float-ID aliasing"
    before, after = input_arrays("labels_paint_tile")[0], final_arrays("labels_paint_tile")[0]
    mask = paint_mask()
    assert mask.sum() == 21 and not mask[4, 8]
    assert np.array_equal(after[~mask], before[~mask])
    levels = input_arrays("multiscale_level1_edit")
    updated = final_arrays("multiscale_level1_edit")
    assert len({array_record(a)["sha256"] for a in levels}) == 3
    assert array_record(levels[0]) == array_record(updated[0])
    assert array_record(levels[2]) == array_record(updated[2])
    assert array_record(levels[1]) != array_record(updated[1])
    slices = input_arrays("slice_change")[0]
    edited = final_arrays("slice_change")[0]
    assert np.array_equal(slices[0], edited[0]) and np.array_equal(slices[2], edited[2])
    assert not np.array_equal(slices[1], edited[1])


def test_nan_scaling_landmarks_distinguish_transparency_from_low_clim():
    cpu = case_contract("cpu_scalar_nan")["landmarks"][-1]
    gpu = case_contract("gpu_scalar_nan")["landmarks"][-1]
    assert (cpu["row"], cpu["column"]) == (gpu["row"], gpu["column"]) == (20, 16)
    assert cpu["rgba"] == [0, 0, 0, 255]
    assert gpu["rgba"] == [32, 64, 128, 255]
    assert np.array_equal(input_arrays("cpu_scalar_nan")[0], input_arrays("gpu_scalar_nan")[0], equal_nan=True)


def test_pinned_public_host_models_admit_paint_and_multiscale_without_graphics():
    from napari.layers import Image, Labels
    from napari.utils.colormaps import DirectLabelColormap

    cmap = DirectLabelColormap(color_dict={0: (0, 0, 0, 0), -7: (1, 0, 0, 1),
        HIGH_A: (0, 1, 0, 1), HIGH_B: (0, 0, 1, 1), None: (1, 1, 0, 1)})
    label = Labels(input_arrays("labels_paint_tile")[0], colormap=cmap)
    observed = []
    label.events.labels_update.connect(lambda event: observed.append(
        ([int(v) for v in event.offset], list(event.data.shape), event.data.dtype.str)))
    label.brush_size = 5
    label.paint((6, 10), HIGH_B)
    assert np.array_equal(label.data, final_arrays("labels_paint_tile")[0])
    assert observed == [([4, 8], [5, 5], "|u1")]
    assert np.array_equal(cmap.map(np.array([-7, 0, HIGH_A, HIGH_B], np.int32)),
        np.array([[1, 0, 0, 1], [0, 0, 0, 0], [0, 1, 0, 1], [0, 0, 1, 1]], np.float32))
    levels = input_arrays("multiscale_level1_edit")
    model = Image(levels, multiscale=True, locked_data_level=0, contrast_limits=(0, 255))
    model.locked_data_level = 1
    levels[1][2:4, 5:7] = 255
    model.refresh()
    model.locked_data_level = 0
    assert model.data_level == model.locked_data_level == 0
    assert [array_record(a) for a in model.data] == [array_record(a) for a in final_arrays("multiscale_level1_edit")]


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_public_image_extension_matches_independent_opengl(name):
    # Missing dependencies/references remain required failures, never skips.
    import napari
    import numba
    from vispy import _dawn

    assert napari.__version__ == "0.9.2" and numba.__version__ == "0.68.0"
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["comparison"] == COMPARISON
    assert manifest["provenance"]["kind"] == "upstream"
    record = manifest["fixtures"][name]
    assert manifest["processes"][name]["exit_code"] == 0
    assert _sha(REFERENCE / record["rgba"]["file"]) == record["rgba"]["sha256"]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    assert image.shape == reference.shape == (96, 128, 4)
    contract = case_contract(name)
    for key, expected in contract.items():
        assert params[key] == record["parameters"][key] == expected
    for key in ("actual_label_remap", "partial_labels_events", "source_revisions",
                "selected_level_sequence", "selected_slice_sequence", "initial_slice_records"):
        if key in record["parameters"]:
            assert params[key] == record["parameters"][key], (name, key)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    np.save(EVIDENCE / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(EVIDENCE / f"{name}.difference.npy", difference, allow_pickle=False)
    (EVIDENCE / f"{name}.parameters.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    assert np.array_equal(image, reference), (name, int(difference.max()), int(np.count_nonzero(np.any(difference, axis=2))))
    assert_landmarks(name, image)
    assert _dawn.device_info()["ok"]
