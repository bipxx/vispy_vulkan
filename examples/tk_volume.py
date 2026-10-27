# SPDX-License-Identifier: AGPL-3.0-only
"""A scalar volume on Vulkan/Tk; drag to orbit and use the wheel to zoom.

Use the environment described in docs/install-tk-cp312.md.
"""
import time

import numpy as np

from vispy import app, scene


def volume_data():
    """Two separated bright blocks in a zero-valued float32 Z/Y/X volume."""
    data = np.zeros((32, 32, 32), dtype=np.float32)
    data[20:26, 12:20, 6:12] = 1
    data[6:12, 12:20, 20:26] = 1
    return data


def create_scene(application):
    """Return the canvas, view and volume for ordinary set_data updates."""
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               title='VisPy Vulkan: scalar volume',
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.camera = scene.cameras.TurntableCamera(
            fov=0, azimuth=0, elevation=0, distance=100,
            center=(15.5, 15.5, 15.5), scale_factor=40, up='+z')
        volume = scene.visuals.Volume(
            volume_data(), clim=(0, 1), method='mip', cmap='grays',
            interpolation='nearest', relative_step_size=.5,
            texture_format='r32f', parent=view.scene)
        view.camera.center = (15.5, 15.5, 15.5)
        view.camera.scale_factor = 40
        return canvas, view, volume
    except BaseException:
        canvas.close()
        raise


def main():
    application = app.Application('tkinter')
    canvas = None
    try:
        canvas, _, _ = create_scene(application)
        closed = []
        canvas.events.close.connect(lambda event: closed.append(True))
        while not closed:
            application.process_events()
            time.sleep(.01)
    finally:
        if canvas is not None:
            canvas.close()
        application.quit()


if __name__ == '__main__':
    main()
