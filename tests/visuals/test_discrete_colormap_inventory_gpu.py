"""Source acceptance for discrete colormap sampling on Dawn."""

import numpy as np
import pytest
from numpy.testing import assert_allclose


@pytest.mark.gpu
def test_colormap_discrete_image():
    from vispy import scene
    from vispy.color import Colormap

    canvas = scene.SceneCanvas(app='dawn_headless', size=(32, 16), show=False,
                               bgcolor='black', config={'samples': 0})
    try:
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(rect=(0, 0, 2, 1))
        cmap = Colormap(['red', 'blue'], controls=[0, .5, 1],
                        interpolation='zero')
        scene.visuals.Image(np.array([[.25, .75]], dtype=np.float32),
                            cmap=cmap, clim=(0, 1), interpolation='nearest',
                            parent=view.scene)
        frame = canvas.render()
        assert frame.shape == (16, 32, 4)
        assert_allclose(frame[8, [8, 24], :3], [[255, 0, 0], [0, 0, 255]],
                        atol=1, rtol=0)
    finally:
        canvas.close()
