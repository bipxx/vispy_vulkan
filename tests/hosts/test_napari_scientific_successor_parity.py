# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30) of test_napari_scientific_parity.py: unmodified napari workflows versus the installed napari's packet.

The comparison is the retained test's. The packet is the one captured with the installed napari release, and
tests/contract/test_napari_successor_references.py binds it to the successor fixture.
"""
import json

import numpy as np
import pytest

from tools.fixture_napari_successor import CASES, EXACT, assert_landmarks, masks, render
from tools.napari_host_packets import evidence_dir, installed_packet

pytestmark = pytest.mark.gpu
BASE = "napari-opengl"


@pytest.mark.parametrize("name", CASES)
def test_unmodified_napari_scientific_workflow_matches_opengl(name):
    # Required dependencies deliberately import/fail rather than skip admission.
    import napari
    import numba
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn

    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert napari.__version__ == manifest["provenance"]["napari_version"]
    assert numba.__version__ == "0.68.0"
    evidence = evidence_dir("napari-successor-candidate", napari.__version__)
    get_qapp().setQuitOnLastWindowClosed(False)
    record = manifest["fixtures"][name]
    reference = np.load(packet / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert image.shape == reference.shape == (96, 128, 4)
    assert commands and shaders
    assert params["inputs"] == record["parameters"]["inputs"]
    assert params["camera_rect"] == record["parameters"]["camera_rect"]
    assert "QWidget" in params["native_mro"]
    assert "QOpenGLWidget" not in params["native_mro"]
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    (evidence / f"{name}.parameters.json").write_text(json.dumps(params, indent=2))
    if name in EXACT:
        assert np.array_equal(image, reference), (name, int(difference.max()))
    else:
        interior, edge = masks(name, image.shape)
        assert difference[interior].max() <= 2, (name, int(difference[interior].max()))
        differing = np.any(difference != 0, axis=2)
        assert np.count_nonzero(differing & edge) <= np.count_nonzero(edge) * .001
    assert_landmarks(name, image)
    assert _dawn.device_info()["backend"] == "Vulkan"
    print("napari independent oracle", name, "maxabs", int(difference.max()))
