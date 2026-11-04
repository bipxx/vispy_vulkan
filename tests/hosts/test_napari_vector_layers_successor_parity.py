# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30) of test_napari_vector_layers_parity.py: napari vector layers versus the installed napari's OpenGL
packet.

The comparison is the retained test's (decision D10). tests/contract/test_napari_successor_references.py binds every
packet to the successor fixture and its fixed criteria.
"""
import json

import numpy as np
import pytest

from tools.fixture_napari_vector_layers_successor import CASES, CRITERIA, assert_landmarks, render
from tools.napari_host_packets import evidence_dir, installed_packet
from tools.napari_vector_layers_comparison import smooth_line_case_difference

BASE = "napari-vector-layers-opengl"
FIXED = ("case", "size", "camera_center", "camera_zoom", "background", "criterion", "inputs_sha256")


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_napari_vector_layer_matches_opengl(name):
    import napari
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn

    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert napari.__version__ == manifest["provenance"]["napari_version"]
    evidence = evidence_dir("napari-vector-layers-successor-candidate", napari.__version__)
    get_qapp().setQuitOnLastWindowClosed(False)
    record = manifest["fixtures"][name]
    reference = np.load(packet / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    for key in (*FIXED, "camera_rect", "layer_types"):
        assert params[key] == record["parameters"][key], (name, key)
    assert "QOpenGLWidget" not in params["native_mro"]
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    if CRITERIA[name] == "exact":
        assert np.array_equal(image, reference), (name, int(difference.max()), int(np.any(difference, axis=2).sum()))
    else:
        # Decision D10: tracks and shapes_selected drop only the frame cap, and alpha must match exactly.
        reason = smooth_line_case_difference(name, image, reference)
        assert reason is None, (name, reason)
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("napari vector layers", name, CRITERIA[name], "maxabs", int(difference.max()))
