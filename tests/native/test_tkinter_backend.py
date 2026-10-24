# SPDX-License-Identifier: AGPL-3.0-only
"""Real Tk/raster/Vulkan integration; requires a display and Tk, no pyopengltk."""
import sys
import time

import numpy as np
import pytest

from vispy import app, gloo

pytestmark = pytest.mark.gpu


def wait(application, condition):
    deadline = time.monotonic() + 5
    while not condition():
        application.process_events()
        assert time.monotonic() < deadline, 'Tk event did not complete'
        time.sleep(.005)


@pytest.fixture
def application():
    application = app.Application('tkinter')
    yield application
    application.quit()


def paint(canvas):
    @canvas.events.draw.connect
    def draw(event):
        width, height = canvas.physical_size
        gloo.set_viewport(0, 0, width, height)
        gloo.set_state(scissor_test=False)
        gloo.clear(color=(0, 1, 0, 1))
        gloo.set_scissor(0, 0, width, height // 2)
        gloo.set_state(scissor_test=True)
        gloo.clear(color=(1, 0, 0, 1))
        gloo.set_state(scissor_test=False)


def test_real_frame_presentation_and_resize(application):
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    canvas.set_current()
    rgba = gloo.read_pixels((0, 0, *canvas.physical_size), alpha=True)
    photo = canvas._backend._photo
    assert photo.width() == 192 and photo.height() == 128
    for x, y in ((12, 4), (12, 120)):
        assert tuple(photo.get(x, y)) == tuple(rgba[y, x, :3])
    assert not np.array_equal(rgba[4, 12], rgba[120, 12])
    assert 'pyopengltk' not in sys.modules
    assert not any(n == 'OpenGL' or n.startswith('OpenGL.') for n in sys.modules)
    previous = photo
    canvas.size = (224, 160)
    wait(application, lambda: canvas.physical_size == (224, 160) and
         canvas._backend._photo is not previous)
    assert canvas._backend._photo.width() == 224
    assert canvas._backend._photo.height() == 160
    canvas.close()
    canvas.close()
    assert canvas._backend._dawn_canvas_id == 0


def test_embedding_and_external_widget_destruction(application):
    import tkinter as tk
    root = application.native
    parent = tk.Toplevel(root)
    canvas = app.Canvas(app=application, parent=parent, size=(32, 24))
    canvas.native.pack(fill='both', expand=True)
    paint(canvas)
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    parent.destroy()
    assert canvas._closed
    assert canvas._backend._dawn_canvas_id == 0
    assert root.winfo_exists()


def test_multiple_canvases_keep_distinct_targets(application):
    canvases = [app.Canvas(app=application, size=(24, 24), show=True) for _ in range(2)]
    for canvas, color in zip(canvases, ('red', 'blue')):
        canvas.events.draw.connect(lambda event, c=canvas, value=color:
                                   (gloo.set_viewport(0, 0, *c.physical_size),
                                    gloo.clear(color=value)))
        canvas.update()
    wait(application, lambda: all(c._backend._photo is not None for c in canvases))
    assert canvases[0]._backend._photo.get(12, 12) == (255, 0, 0)
    assert canvases[1]._backend._photo.get(12, 12) == (0, 0, 255)
    canvases[0].close()
    canvases[1].update()
    previous = canvases[1]._backend._photo
    wait(application, lambda: canvases[1]._backend._photo is not previous)
    canvases[1].close()


def test_real_tk_input_and_stopped_timer(application):
    canvas = app.Canvas(app=application, size=(32, 24), show=True)
    seen = []
    canvas.events.mouse_press.connect(lambda event: seen.append(('press', event.button, tuple(event.pos))))
    canvas.events.mouse_release.connect(lambda event: seen.append(('release', event.button)))
    canvas.events.mouse_wheel.connect(lambda event: seen.append(('wheel', tuple(event.delta))))
    canvas.events.key_press.connect(lambda event: seen.append(('key', event.key.name)))
    wait(application, lambda: canvas.native.winfo_viewable())
    canvas.native.event_generate('<ButtonPress-1>', x=7, y=9)
    canvas.native.event_generate('<ButtonRelease-1>', x=7, y=9)
    canvas.native.event_generate('<MouseWheel>', delta=120, x=7, y=9)
    canvas.native.focus_force()
    application.process_events()
    canvas.native.event_generate('<KeyPress-a>')
    wait(application, lambda: len(seen) == 4)
    assert seen[:3] == [('press', 1, (7, 9)), ('release', 1), ('wheel', (0, 1))]
    assert seen[3][0] == 'key' and seen[3][1].lower() == 'a'
    ticks = []
    timer = app.Timer(interval=.001, iterations=1, app=application,
                      connect=lambda event: ticks.append(event.iteration), start=True)
    wait(application, lambda: len(ticks) == 1)
    for _ in range(3):
        time.sleep(.005)
        application.process_events()
    assert ticks == [0] and timer._backend._job is None
    canvas.close()


def test_external_tk_application_survives_vispy_quit():
    import tkinter as tk
    root = tk.Tk()
    try:
        application = app.Application('tkinter')
        canvas = app.Canvas(app=application, size=(16, 16))
        application.quit()
        assert canvas._closed and root.winfo_exists()
    finally:
        root.update_idletasks()
        root.destroy()


def test_animation_pump_returns_and_pending_draw_is_cancelled(application):
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    frames = []

    @canvas.events.draw.connect
    def draw(event):
        frames.append(len(frames))
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.clear(color='green')
        canvas.update()

    canvas.update()
    wait(application, lambda: len(frames) >= 5)
    assert canvas._backend._draw_job is not None
    canvas.close()
    assert canvas._backend._draw_job is None
    count = len(frames)
    application.process_events()
    assert len(frames) == count


def test_draw_failure_is_reported_and_next_frame_can_recover(application):
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    canvas.events.draw.ignore_callback_errors = False

    def fail(event):
        raise ValueError('intentional draw failure')

    canvas.events.draw.connect(fail)
    canvas.update()
    with pytest.raises(ValueError, match='intentional draw failure'):
        wait(application, lambda: canvas._backend._photo is not None)
    canvas.events.draw.disconnect(fail)
    paint(canvas)
    canvas.update()
    previous = canvas._backend._photo
    wait(application, lambda: canvas._backend._photo is not previous)
    canvas.close()


def test_device_loss_recreates_frame_and_keeps_tk_widget(application):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128), show=True, config={'samples': 4})
    paint(canvas)
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    widget = canvas.native
    before = _dawn.probe()['device_generation']
    _dawn.lose_device()
    previous = canvas._backend._photo
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not previous)
    assert canvas.native is widget and widget.winfo_exists()
    assert _dawn.probe()['device_generation'] > before
    assert canvas._backend._photo.get(10, 4) in ((255, 0, 0), (0, 255, 0))
    canvas.close()


def test_failed_registration_destroys_owned_widgets(application, monkeypatch):
    from vispy import _dawn
    root = application.native
    children = set(root.winfo_children())

    def fail(*args):
        raise RuntimeError('intentional registration failure')

    monkeypatch.setattr(_dawn, 'register_canvas', fail)
    with pytest.raises(RuntimeError, match='intentional registration failure'):
        app.Canvas(app=application, size=(192, 128), show=True)
    assert set(root.winfo_children()) == children
    assert not application._backend._canvases
