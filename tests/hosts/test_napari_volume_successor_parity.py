# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30) of test_napari_volume_parity.py: categorical volumes through unmodified napari versus the installed
napari's packet.

The comparison is the retained test's. tests/contract/test_napari_successor_references.py binds every packet to the
successor fixture.
"""
import json

import numpy as np
import pytest

from tools.fixture_napari_volume_successor import CASES, assert_landmarks, render
from tools.napari_host_packets import evidence_dir, installed_packet

pytestmark = pytest.mark.gpu
BASE = "napari-volume-opengl"


@pytest.mark.parametrize("name", CASES)
def test_napari_categorical_volume_matches_independent_opengl(name):
    import napari
    import numba
    from napari._qt.qt_event_loop import get_qapp

    packet = installed_packet(BASE)
    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    assert napari.__version__ == manifest["provenance"]["napari_version"]
    assert numba.__version__ == "0.68.0"
    evidence = evidence_dir("napari-volume-successor-candidate", napari.__version__)
    get_qapp().setQuitOnLastWindowClosed(False)
    record = manifest["fixtures"][name]
    reference = np.load(packet / record["rgba"]["file"], allow_pickle=False)
    image, commands, shaders, params = render(name)
    assert image.shape == reference.shape == (96, 96, 4)
    assert commands and shaders
    expected = dict(record["parameters"])
    actual = dict(params)
    assert "QOpenGLWidget" in expected.pop("native_mro")
    assert "QOpenGLWidget" not in actual.pop("native_mro")
    assert actual == expected
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    evidence.mkdir(parents=True, exist_ok=True)
    np.save(evidence / f"{name}.candidate.npy", image, allow_pickle=False)
    np.save(evidence / f"{name}.difference.npy", difference, allow_pickle=False)
    (evidence / f"{name}.parameters.json").write_text(json.dumps(params, indent=2))
    assert np.array_equal(image, reference), (name, "exact categorical image mismatch", int(difference.max()))
    assert_landmarks(name, image)
    print("napari categorical volume independent oracle", name, "maxabs", int(difference.max()))
