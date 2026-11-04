# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30) of test_napari_layer_controls_parity.py: napari layer-control changes versus the installed napari's
OpenGL packet.

The comparison is the retained test's (decisions D13 and D14). tests/contract/test_napari_successor_references.py binds
every packet to the successor fixture and its fixed criteria.
"""
import json

import numpy as np
import pytest

from tools.fixture_napari_layer_controls_successor import CASES, CRITERIA, assert_landmarks, render
from tools.napari_host_packets import evidence_dir, installed_packet
from tools.napari_layer_controls_comparison import COMPARED_PARAMETERS, layer_control_difference

BASE = "napari-layer-controls-opengl"
FIXED = ("case", "size", "camera", "controls", "background", "criterion", "inputs_sha256")


@pytest.mark.gpu
@pytest.mark.parametrize("name", CASES)
def test_napari_layer_control_change_matches_opengl(name):
    import napari
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn

    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert napari.__version__ == manifest["provenance"]["napari_version"]
    evidence = evidence_dir("napari-layer-controls-successor-candidate", napari.__version__)
    get_qapp().setQuitOnLastWindowClosed(False)
    record = manifest["fixtures"][name]
    reference = np.load(packet / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert commands and shaders
    assert "QOpenGLWidget" not in params["native_mro"]
    assert image.shape == reference.shape, (name, image.shape, reference.shape)
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    # Decision D13: the finish counts are evidence, not compared. Every mismatch is reported together with the frame.
    problems = [(key, params[key], record["parameters"][key])
                for key in (*FIXED, *COMPARED_PARAMETERS) if params[key] != record["parameters"][key]]
    assert CRITERIA[name] == "exact"
    reason = layer_control_difference(name, image, reference)  # exact, except decision D14 for volume_iso
    if reason is not None:
        problems.append(("frame", reason))
    assert not problems, (name, problems)
    assert_landmarks(name, image)
    print("finish commands", name, "candidate", params["finish_commands"], "opengl",
          record["parameters"]["finish_commands"])
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("napari layer controls", name, CRITERIA[name], "maxabs", int(difference.max()))
