# SPDX-License-Identifier: AGPL-3.0-only
"""Simulate mixed-DPI monitor moves with a real offscreen Dawn drawable."""

import numpy as np
import pytest

from vispy import app, gloo, scene
from vispy.gloo import gl

pytestmark = pytest.mark.gpu

RED = [255, 0, 0, 255]
BLACK = [0, 0, 0, 255]
LOGICAL = (13, 11)


@pytest.mark.parametrize(
    'ratio, physical, resized',
    [(1.25, (16, 14), (11, 9)), (1.5, (20, 16), (14, 10)),
     (1.75, (23, 19), (16, 12)), (2.0, (26, 22), (18, 14))],
)
def test_fractional_drawable_and_scene_coordinates(ratio, physical, resized):
    canvas = scene.SceneCanvas(
        app='dawn_headless', size=LOGICAL, autoswap=False, create_native=False,
        backend_kwargs={'device_pixel_ratio': ratio},
    )
    sizes = []
    canvas.events.resize.connect(lambda event: sizes.append(
        (event.size, event.physical_size, canvas.size, canvas.physical_size)
    ))
    canvas.create_native()
    try:
        canvas.set_current()
        rect = scene.visuals.Rectangle(
            center=(3, 2.5), width=6, height=5, color='red', parent=canvas.scene,
        )
        rect.interactive = True
        clicks = []
        rect.events.mouse_press.connect(lambda event: clicks.append(tuple(event.pos[:2])))

        def assert_clicks():
            pos = (2.25, 1.75)
            press = canvas.native._vispy_mouse_press(pos=pos, button=1)
            canvas.native._vispy_mouse_release(pos=pos, button=1)
            assert tuple(press.pos) == pos
            assert clicks[-1] == pytest.approx(pos)
            count = len(clicks)
            canvas.native._vispy_mouse_press(pos=(8, 6), button=1)
            canvas.native._vispy_mouse_release(pos=(8, 6), button=1)
            assert len(clicks) == count

        def assert_frame(logical, expected):
            w, h = expected
            assert canvas.size == logical
            assert canvas.physical_size == expected
            assert sizes[-1] == (logical, expected, logical, expected)
            assert canvas.pixel_scale == pytest.approx(w / logical[0])
            canvas.events.draw()
            image = gloo.read_pixels()
            assert tuple(gl.glGetParameter(gl.GL_VIEWPORT)) == (0, 0, w, h)
            assert image.shape == (h, w, 4)
            np.testing.assert_array_equal(image[1, 1], RED)
            np.testing.assert_array_equal(image[-1, -1], BLACK)
            np.testing.assert_array_equal(gloo.read_pixels((1, h - 2, 1, 1))[0, 0], RED)
            np.testing.assert_array_equal(canvas.render(), image)
            transform = canvas.transforms.get_transform('canvas', 'framebuffer')
            np.testing.assert_allclose(
                transform.map([(0, 0), logical, (logical[0] / 2, logical[1] / 2)])[:, :2],
                [(0, h), (w, 0), (w / 2, h / 2)], atol=1e-6,
            )

        assert sizes == [(LOGICAL, physical, LOGICAL, physical)]
        assert_frame(LOGICAL, physical)
        assert_clicks()
        # An explicitly sized, vertically offset logical region inside red.
        crop = canvas.render(region=(1, 8, 3, 2), size=(7, 3))
        assert crop.shape == (3, 7, 4)
        assert np.all(crop == RED)

        for invalid in (0, -1, float('nan'), float('inf')):
            with pytest.raises(ValueError, match='finite and positive'):
                canvas.native.set_device_pixel_ratio(invalid)
        canvas.native.set_device_pixel_ratio(ratio)
        assert len(sizes) == 1
        assert canvas.physical_size == physical

        canvas.native.set_device_pixel_ratio(1)
        assert_frame(LOGICAL, LOGICAL)
        with pytest.raises(RuntimeError, match='exceeds target bounds'):
            gloo.read_pixels((0, 0, *physical))
        assert_clicks()
        canvas.native.set_device_pixel_ratio(ratio)
        assert_frame(LOGICAL, physical)
        assert_clicks()

        canvas.size = (9, 7)
        assert_frame((9, 7), resized)
        assert_clicks()
        assert len(sizes) == 4
    finally:
        canvas.close()


def test_headless_default_scale_and_invalid_initial_scale():
    with pytest.raises(ValueError, match='finite and positive'):
        app.Canvas(app='dawn_headless', backend_kwargs={'device_pixel_ratio': 0})
    canvas = app.Canvas(app='dawn_headless', size=(9, 7))
    try:
        canvas.set_current()
        gloo.clear(color='red')
        image = gloo.read_pixels()
        assert canvas.size == canvas.physical_size == (9, 7)
        assert image.shape == (7, 9, 4)
        assert np.all(image == RED)

        canvas.native.set_device_pixel_ratio(1.5)
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color='red')
        image = gloo.read_pixels()
        assert canvas.size == (9, 7)
        assert canvas.physical_size == (14, 10)
        assert image.shape == (10, 14, 4)
        assert np.all(image == RED)
    finally:
        canvas.close()
