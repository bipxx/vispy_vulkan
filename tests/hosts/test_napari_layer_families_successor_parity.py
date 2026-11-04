# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30) of test_napari_layer_families_parity.py: napari layer families versus the installed napari's OpenGL
packet.

The comparison is the retained test's (decisions D11 and D12). tests/contract/test_napari_successor_references.py binds
every packet to the successor fixture and its fixed criteria.
"""
import json

import numpy as np
import pytest

from tools.fixture_napari_layer_families_successor import CASES, CRITERIA, assert_landmarks, render
from tools.napari_host_packets import evidence_dir, installed_packet
from tools.napari_layer_families_comparison import layer_family_difference

BASE = "napari-layer-families-opengl"
FIXED = ("case", "size", "camera", "background", "criterion", "inputs_sha256")


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_napari_layer_family_matches_opengl(name):
    import napari
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn

    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert napari.__version__ == manifest["provenance"]["napari_version"]
    evidence = evidence_dir("napari-layer-families-successor-candidate", napari.__version__)
    get_qapp().setQuitOnLastWindowClosed(False)
    record = manifest["fixtures"][name]
    reference = np.load(packet / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    for key in (*FIXED, "layer_types", "ndisplay"):
        assert params[key] == record["parameters"][key], (name, key)
    assert "QOpenGLWidget" not in params["native_mro"]
    assert image.shape == reference.shape, (name, image.shape, reference.shape)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    # The fixture's criteria, with decisions D11 (colorbar, histogram) and D12 (surface_shaded).
    reason = layer_family_difference(name, image, reference)
    assert reason is None, (name, reason)
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("napari layer families", name, CRITERIA[name], "maxabs", int(difference.max()))
