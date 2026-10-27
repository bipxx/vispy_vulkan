# SPDX-License-Identifier: AGPL-3.0-only
"""Two public Mesh visuals on Tk; drag to orbit and use the wheel to zoom.

Use the Vulkan/Tk environment described in docs/install-tk-cp312.md.
"""
import time

import numpy as np

from vispy import app, scene


def cube_data(center):
    """Return independent float32 vertices and uint32 triangles for a cube."""
    vertices = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                         [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]],
                        dtype=np.float32) * .15
    vertices += np.asarray(center, dtype=np.float32)
    faces = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                      [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2],
                      [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5]],
                     dtype=np.uint32)
    return vertices, faces


def create_scene(application):
    """Return canvas, view and two meshes for ordinary set_data updates."""
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               title='VisPy Vulkan: meshes', bgcolor='black',
                               config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.camera = scene.cameras.TurntableCamera(
            fov=0, elevation=0, azimuth=0, roll=0, center=(0, 0, 0),
            scale_factor=2, up='+z')
        meshes = []
        for center, color in [((-2/3, -1/3, 1/3), 'red'),
                              ((1/3, 2/3, -1/3), 'lime')]:
            vertices, faces = cube_data(center)
            meshes.append(scene.visuals.Mesh(vertices=vertices, faces=faces,
                                               color=color, shading=None,
                                               parent=view.scene))
        view.camera.center = (0, 0, 0)
        view.camera.scale_factor = 2
        return canvas, view, *meshes
    except BaseException:
        canvas.close()
        raise


def main():
    application = app.Application('tkinter')
    canvas = None
    try:
        canvas, _, _, _ = create_scene(application)
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
