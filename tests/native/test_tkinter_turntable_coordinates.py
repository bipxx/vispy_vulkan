# SPDX-License-Identifier: AGPL-3.0-only
"""Cardinal Turntable yaw must have expected angles and landmark coordinates."""
import numpy as np
import pytest

from vispy import scene
from test_tkinter_panzoom_coordinates import application, assert_landmarks, motion, wait

pytestmark = pytest.mark.gpu


def assert_pose(camera, azimuth):
    np.testing.assert_allclose((camera.azimuth, camera.elevation, camera.roll,
                                camera.scale_factor, camera.fov),
                               (azimuth, 0, 0, 2, 0), rtol=0, atol=1e-6)
    np.testing.assert_allclose(camera.center, (0, 0, 0), rtol=0, atol=1e-6)


def test_turntable_quarter_yaw_cancel_and_reverse(application):
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.bgcolor = '#101010'
        view.camera = scene.cameras.TurntableCamera(fov=0, elevation=0, azimuth=0,
            roll=0, center=(0, 0, 0), scale_factor=2, up='+z')
        scene.visuals.Markers(pos=np.array([[-2/3, -1/3, 1/3], [1/3, 2/3, -1/3]],
                                          dtype=np.float32), size=14,
                              face_color=np.array([[1, 0, 0, 1], [0, 1, 0, 1]],
                                                  dtype=np.float32), parent=view.scene)
        camera = view.camera
        camera.center = (0, 0, 0)
        camera.scale_factor = 2
        camera.azimuth = camera.elevation = camera.roll = 0
        canvas.update()
        wait(application, lambda: canvas._backend._photo is not None and
             canvas.native.winfo_viewable())
        assert tuple(view.size) == (240, 180)
        assert_pose(camera, 0)
        # Upstream's documented azimuth/elevation0 looks along +Y with +Z up.
        # Orthographic height2 gives90pixels/world unit: x=120+90X,y=90-90Z.
        assert_landmarks(application, canvas, (240, 180), (60, 60), (150, 120))
        assert canvas.visual_at((30, 90)) is not None
        widget = canvas.native
        widget.event_generate('<ButtonPress-1>', x=30, y=90)
        motion(widget, 210, 90)
        widget.event_generate('<ButtonRelease-1>', x=210, y=90, state=0x100)
        assert_pose(camera, -90)
        # Rightward180pixel drag gives -90degree yaw. Screen-right is now -Y;
        # the literal landmark positions swap horizontally, not vertically.
        assert_landmarks(application, canvas, (240, 180), (150, 60), (60, 120))
        motion(widget, 220, 100, state=0x100)
        assert_pose(camera, -90)

        widget.event_generate('<ButtonPress-1>', x=210, y=90)
        widget.event_generate('<FocusOut>')
        motion(widget, 30, 90, state=0x100)
        assert_pose(camera, -90)
        assert_landmarks(application, canvas, (240, 180), (150, 60), (60, 120))

        # A fresh opposite drag restores the exact original view after cancel.
        widget.event_generate('<ButtonPress-1>', x=210, y=90)
        motion(widget, 30, 90)
        widget.event_generate('<ButtonRelease-1>', x=-5, y=-5, state=0x100)
        assert_pose(camera, 0)
        assert_landmarks(application, canvas, (240, 180), (60, 60), (150, 120))
        motion(widget, 80, 120, state=0x100)
        assert_pose(camera, 0)
    finally:
        canvas.close()
