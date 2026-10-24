# SPDX-License-Identifier: AGPL-3.0-only
"""Independent Tk/display/capture expectations; needs Tk, a display and Vulkan."""
import gc
import os
from pathlib import Path
import time
import weakref

import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu


def wait(application, condition):
    deadline = time.monotonic() + 5
    while not condition():
        application.process_events()
        assert time.monotonic() < deadline, 'Tk capture condition timed out'
        time.sleep(.005)


@pytest.fixture
def application():
    import tkinter as tk
    initial_root = getattr(tk, '_default_root', None)
    value = app.Application('tkinter')
    yield value
    root = value._backend._root
    value.quit()
    if root is not None and root is not initial_root:
        try:
            alive = root.winfo_exists()
        except tk.TclError:
            alive = False
        if alive:
            root.update_idletasks()
            root.destroy()


def expected_frame(width, height):
    """Top-left image coordinates, independently authored from GL quadrants."""
    left, bottom = width // 2, height // 2
    image = np.empty((height, width, 4), dtype=np.uint8)
    image[:height - bottom, :left] = [0, 0, 255, 192]
    image[:height - bottom, left:] = [255, 255, 0, 255]
    image[height - bottom:, :left] = [255, 0, 0, 64]
    image[height - bottom:, left:] = [0, 255, 0, 128]
    return image


def connect_quadrants(canvas):
    @canvas.events.draw.connect
    def draw(event):
        width, height = canvas.physical_size
        left, bottom = width // 2, height // 2
        gloo.set_viewport(0, 0, width, height)
        gloo.set_state(scissor_test=False)
        gloo.clear(color='black')
        # GL scissor origin is bottom-left. Top-left capture must invert the
        # row ordering, including the asymmetric extra row at odd heights.
        for rect, color in (
            ((0, 0, left, bottom), (1, 0, 0, 64 / 255)),
            ((left, 0, width - left, bottom), (0, 1, 0, 128 / 255)),
            ((0, bottom, left, height - bottom), (0, 0, 1, 192 / 255)),
            ((left, bottom, width - left, height - bottom), (1, 1, 0, 1)),
        ):
            gloo.set_scissor(*rect)
            gloo.set_state(scissor_test=True)
            gloo.clear(color=color)
        # Deliberately leave a cropped viewport and enabled scissor. Display
        # readback must use the full client target without depending on them.
        gloo.set_viewport(3, 5, 7, 9)

    canvas.events.draw.ignore_callback_errors = False


def check_pixels(canvas):
    width, height = canvas.physical_size
    expected = expected_frame(width, height)
    canvas.set_current()
    actual = gloo.read_pixels((0, 0, width, height), alpha=True)
    if not np.array_equal(actual, expected) and os.environ.get('VISPY_TK_CAPTURE_EVIDENCE'):
        destination = Path(os.environ['VISPY_TK_CAPTURE_EVIDENCE'])
        stem = '%dx%d-samples%d' % (width, height, canvas._backend._samples)
        for suffix, data in (('actual', actual), ('expected', expected)):
            with (destination / (stem + '-' + suffix + '.npy')).open('xb') as stream:
                np.save(stream, data, allow_pickle=False)
    np.testing.assert_array_equal(actual, expected)
    photo = canvas._backend._photo
    assert (photo.width(), photo.height()) == (width, height)
    for x, y in ((2, 2), (width - 3, 2), (2, height - 3), (width - 3, height - 3)):
        assert tuple(photo.get(x, y)) == tuple(expected[y, x, :3])
    return actual


@pytest.mark.parametrize('samples', [0, 4])
def test_independent_odd_quadrants_survive_resize_and_device_loss(application, samples):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(257, 129), show=True, config={'samples': samples})
    connect_quadrants(canvas)
    canvas.update()
    wait(application, lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
    original = check_pixels(canvas)
    assert original.shape == (129, 257, 4)
    canvas.size = (301, 177)
    wait(application, lambda: canvas.physical_size == (301, 177) and
         canvas._backend._photo.width() == 301 and canvas._backend._photo.height() == 177)
    check_pixels(canvas)
    previous = canvas._backend._photo
    _dawn.lose_device()
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not previous)
    check_pixels(canvas)
    canvas.close()
    np.testing.assert_array_equal(original, expected_frame(257, 129))  # Owned capture survives close.


@pytest.mark.parametrize('floating', [False, True])
def test_cropped_capture_uses_gl_origin_and_preserves_alpha(application, floating):
    canvas = app.Canvas(app=application, size=(257, 129), show=True)
    connect_quadrants(canvas)
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    canvas.set_current()
    expected = expected_frame(*canvas.physical_size)
    x, y, width, height = 3, 4, 131, 69
    crop = expected[expected.shape[0] - y - height:expected.shape[0] - y, x:x + width]
    actual = gloo.read_pixels((x, y, width, height), alpha=True,
                              out_type='float' if floating else 'unsigned_byte')
    if floating:
        assert actual.dtype == np.float32
        np.testing.assert_allclose(actual, crop.astype(np.float32) / 255, atol=1e-6, rtol=0)
    else:
        np.testing.assert_array_equal(actual, crop)
    canvas.close()


@pytest.mark.parametrize('scale', [1.25, 1.5, 2.0])
def test_tk_local_scale_does_not_double_scale_client_pixels(application, scale):
    root = application.native
    original_scale = float(root.tk.call('tk', 'scaling'))
    canvas = None
    try:
        root.tk.call('tk', 'scaling', original_scale * scale)
        canvas = app.Canvas(app=application, size=(257, 129), show=True)
        connect_quadrants(canvas)
        seen = []
        canvas.events.mouse_press.connect(lambda event: seen.append(tuple(event.pos)))
        canvas.update()
        wait(application, lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
        assert canvas.size == canvas.physical_size == (257, 129)
        assert (canvas.native.winfo_width(), canvas.native.winfo_height()) == (257, 129)
        assert canvas.pixel_scale == 1
        canvas.native.event_generate('<ButtonPress-1>', x=202, y=101)
        canvas.native.event_generate('<ButtonRelease-1>', x=202, y=101, state=0x100)
        assert seen == [(202, 101)]
        check_pixels(canvas)
    finally:
        if canvas is not None:
            canvas.close()
        root.tk.call('tk', 'scaling', original_scale)


def test_tcl_images_retire_after_replacement_and_close(application):
    root = application.native
    before = set(root.tk.call('image', 'names'))
    canvas = app.Canvas(app=application, size=(257, 129), show=True)
    connect_quadrants(canvas)
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    reference = weakref.ref(canvas._backend._photo)
    name = str(canvas._backend._photo)
    for _ in range(3):
        previous = str(canvas._backend._photo)
        canvas.update()
        wait(application, lambda: str(canvas._backend._photo) != previous)
    gc.collect()
    assert reference() is None
    assert name not in root.tk.call('image', 'names')
    assert len(set(root.tk.call('image', 'names')) - before) == 1
    canvas.close()
    gc.collect()
    assert set(root.tk.call('image', 'names')) == before


def test_hide_zero_configure_and_show_resize(application, monkeypatch):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(257, 129), show=True)
    connect_quadrants(canvas)
    canvas.update()
    wait(application, lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
    configurations = []
    original = _dawn.configure_canvas

    def configure(*args):
        configurations.append(args)
        return original(*args)

    monkeypatch.setattr(_dawn, 'configure_canvas', configure)
    canvas.native.event_generate('<Configure>', width=0, height=0)
    assert not configurations and canvas.physical_size == (257, 129)
    canvas.show(False)
    wait(application, lambda: not canvas.native.winfo_viewable())
    canvas.size = (301, 177)
    canvas.show()
    wait(application, lambda: canvas.native.winfo_viewable() and canvas.physical_size == (301, 177)
         and canvas._backend._photo.width() == 301 and canvas._backend._photo.height() == 177)
    assert all(args[1] > 0 and args[2] > 0 for args in configurations)
    check_pixels(canvas)
    canvas.close()


def test_embedded_render_captures_own_target_without_parent_widgets(application):
    import tkinter as tk
    root = application.native
    parent = tk.Toplevel(root)
    tk.Label(parent, text='outside canvas capture', bg='magenta').pack()
    canvas = app.Canvas(app=application, parent=parent, size=(257, 129))
    canvas.native.pack()
    connect_quadrants(canvas)
    canvas.update()
    try:
        wait(application, lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
        np.testing.assert_array_equal(canvas.render(alpha=True), expected_frame(257, 129))
        np.testing.assert_array_equal(canvas.render(alpha=False), expected_frame(257, 129)[..., :3])
        assert parent.winfo_exists()
    finally:
        canvas.close()
        parent.destroy()


def test_loss_before_first_presentation_preserves_expected_orientation(application):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(257, 129), show=True)
    connect_quadrants(canvas)
    assert canvas._backend._photo is None
    _dawn.lose_device()
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    check_pixels(canvas)
    canvas.close()


def test_close_during_deferred_readiness_does_not_present_to_dead_widget(application, monkeypatch):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(257, 129), show=True)
    connect_quadrants(canvas)
    native_id = canvas._backend._dawn_canvas_id
    calls = []
    original_ready = _dawn.frame_ready

    def defer(canvas_id):
        if canvas_id == native_id:
            calls.append(canvas_id)
            return False
        return original_ready(canvas_id)

    monkeypatch.setattr(_dawn, 'frame_ready', defer)
    canvas.update()
    wait(application, lambda: bool(calls))
    job = canvas._backend._draw_job
    assert job is not None and canvas._backend._photo is None
    canvas.close()
    assert canvas._backend._draw_job is None
    assert job not in application.native.tk.call('after', 'info')
    time.sleep(.01)
    application.process_events()
    assert canvas._backend._photo is None
    assert canvas._backend._dawn_canvas_id == 0


@pytest.mark.parametrize('monitor', [0, 1])
def test_monitor_fullscreen_request_is_refused_without_changing_state(application, monitor):
    root = application.native
    children = set(root.winfo_children())
    with pytest.raises(RuntimeError, match='monitor-index selection is unsupported'):
        app.Canvas(app=application, fullscreen=monitor)
    assert set(root.winfo_children()) == children
    canvas = app.Canvas(app=application, size=(257, 129))
    try:
        assert canvas.fullscreen is False
        with pytest.raises(RuntimeError, match='monitor-index selection is unsupported'):
            canvas.fullscreen = monitor
        assert canvas.fullscreen is False
    finally:
        canvas.close()
