# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30) of test_image_extensions_parity.py: required image/label workflows versus the installed napari's
OpenGL packet.

The comparison is the retained test's. tests/contract/test_napari_successor_references.py binds every packet to its
authoring freeze, which fixed these sources, the data and the criteria before any capture.
"""

import hashlib
import json

import numpy as np
import pytest

from tools.fixture_image_extensions_successor import (CASES, COMPARISON, HIGH_A, HIGH_B,
    array_record, assert_landmarks, case_contract, final_arrays, input_arrays, render)
from tools.napari_host_packets import evidence_dir, installed_packet

BASE = "image-extensions-opengl"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_public_host_models_admit_paint_and_multiscale_without_graphics():
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

    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert napari.__version__ == manifest["provenance"]["napari_version"] and numba.__version__ == "0.68.0"
    assert manifest["comparison"] == COMPARISON
    assert manifest["provenance"]["kind"] == "upstream"
    record = manifest["fixtures"][name]
    assert manifest["processes"][name]["exit_code"] == 0
    assert _sha(packet / record["rgba"]["file"]) == record["rgba"]["sha256"]
    reference = np.load(packet / record["rgba"]["file"], allow_pickle=False)
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
    evidence = evidence_dir("image-extensions-successor-candidate", napari.__version__)
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    (evidence / f"{name}.parameters.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    assert np.array_equal(image, reference), (name, int(difference.max()), int(np.count_nonzero(np.any(difference, axis=2))))
    assert_landmarks(name, image)
    assert _dawn.device_info()["ok"]
