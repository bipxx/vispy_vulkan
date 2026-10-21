import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu


def test_clear_exact_rgba_and_array_outlives_canvas():
    color = (64 / 255, 128 / 255, 192 / 255, 1.0)
    canvas = app.Canvas(app="dawn_headless", size=(3, 2), show=False)
    with canvas:
        gloo.set_viewport(0, 0, 3, 2)
        gloo.set_clear_color(color)
        gloo.clear(color=True, depth=False, stencil=False)
        image = gloo.read_pixels(viewport=(0, 0, 3, 2))
    canvas.close()
    expected = np.array([64, 128, 192, 255], dtype=np.uint8)
    print("clear", image.reshape(-1, 4)[0].tolist(), "shape", image.shape)
    assert image.shape == (2, 3, 4)
    assert image.dtype == np.uint8
    assert np.all(image == expected)
    # The returned array owns its bytes after the canvas is gone.
    assert image[1, 2].tolist() == expected.tolist()
