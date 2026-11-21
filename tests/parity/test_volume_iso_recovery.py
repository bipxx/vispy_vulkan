# SPDX-License-Identifier: AGPL-3.0-only
"""Headless Dawn ISO landmarks before and after device loss."""

from pathlib import Path

import numpy as np
import pytest

from tools.fixture_volume import SIZE, render


pytestmark = pytest.mark.gpu
REFERENCE = Path(__file__).resolve().parents[1] / "reference" / "volume-opengl" / "iso.npy"
CENTER = (SIZE[1] // 2, SIZE[0] // 2)


def test_headless_iso_matches_upstream_center():
    from vispy import _dawn

    frame, _, _, _ = render("iso", backend="dawn_headless")
    assert _dawn.device_info()["backend"] == "Vulkan"
    reference = np.load(REFERENCE, allow_pickle=False)
    np.testing.assert_allclose(frame[CENTER], reference[CENTER], atol=2, rtol=0)


def test_headless_cube_switches_to_iso_after_device_loss():
    from vispy import _dawn, scene

    data = np.full((32, 32, 32), .2, np.float32)
    data[9:23, 9:23, 9:23] = 1
    with scene.SceneCanvas(app="dawn_headless", size=SIZE, show=False) as canvas:
        view = canvas.central_widget.add_view()
        view.camera = scene.cameras.TurntableCamera(
            fov=0, azimuth=0, elevation=0, distance=100,
            center=(15.5, 15.5, 15.5), scale_factor=40, up="+z",
        )
        volume = scene.visuals.Volume(
            data, parent=view.scene, method="mip", clim=(0, 1), cmap="grays",
            relative_step_size=.5, interpolation="nearest", texture_format="r32f",
        )
        before = canvas.render()
        np.testing.assert_array_equal(before[CENTER][:3], [255, 255, 255])
        # This ray crosses the background-value shell and misses the bright cube.
        np.testing.assert_allclose(before[48, 20, :3], [51, 51, 51], atol=2, rtol=0)
        assert _dawn.device_info()["backend"] == "Vulkan"

        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device()
        volume.method = "iso"
        volume.threshold = .5
        recovered = canvas.render()

        assert _dawn.probe()["device_generation"] > generation
        reference = np.load(REFERENCE, allow_pickle=False)
        np.testing.assert_allclose(recovered[CENTER][:3], reference[CENTER][:3], atol=2, rtol=0)
        np.testing.assert_array_equal(recovered[48, 20, :3], [0, 0, 0])
