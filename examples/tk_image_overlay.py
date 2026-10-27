# SPDX-License-Identifier: AGPL-3.0-only
"""A Vulkan image and line overlay; drag to pan and use the wheel to zoom.

Run with the Tk CPython 3.12 environment described in docs/install-tk-cp312.md.
The example uses the existing public VisPy scene API and manual event pumping.
"""
import time

import numpy as np

from vispy import app, scene
from vispy.visuals.transforms import STTransform


def create_scene(application):
    """Return the canvas, view, image and overlay for further data updates."""
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               title='VisPy Vulkan: image and line',
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view()
        view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, 4, 3), aspect=None)
        view.camera.flip = (False, True, False)
        data = np.array([[[255, 0, 0, 255], [0, 255, 0, 255]],
                         [[0, 0, 255, 255], [255, 255, 0, 255]]], dtype=np.uint8)
        image = scene.visuals.Image(data, interpolation='nearest', method='subdivide',
                                    parent=view.scene)
        image.transform = STTransform(scale=(2, 1.5))
        line = scene.visuals.Line(pos=np.array([[.5, 1.75], [3.5, 1.75]], dtype=np.float32),
                                 color='white', width=7, method='agg', parent=view.scene)
        line.order = 1
        view.camera.rect = (0, 0, 4, 3)
        return canvas, view, image, line
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
