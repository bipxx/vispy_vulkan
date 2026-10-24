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


def test_drag_button_state_and_focus_loss(application):
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    seen = []
    for name in ('mouse_press', 'mouse_move', 'mouse_release'):
        getattr(canvas.events, name).connect(
            lambda event: seen.append((event.type, event.button, tuple(event.buttons))))
    wait(application, lambda: canvas.native.winfo_viewable())
    widget = canvas.native
    widget.event_generate('<ButtonPress-1>', x=20, y=20)
    widget.event_generate('<ButtonPress-3>', x=20, y=20, state=0x100)
    widget.event_generate('<Motion>', x=50, y=40, state=0x500)
    assert seen[:3] == [('mouse_press', 1, (1,)), ('mouse_press', 2, (1, 2)),
                       ('mouse_move', 1, (1, 2))]
    # Tk's implicit pointer grab delivers a physical release outside the widget
    # to this handler as well; negative widget coordinates must not discard it.
    widget.event_generate('<ButtonRelease-1>', x=-5, y=-5, state=0x500)
    assert seen[-1] == ('mouse_release', 1, (2,))
    widget.event_generate('<FocusOut>')
    assert seen[-1] == ('mouse_release', 2, ())
    time.sleep(.012)  # Base backend coalesces motion within 10 ms.
    widget.event_generate('<Motion>', x=30, y=30)
    assert seen[-1] == ('mouse_move', None, ())
    canvas.close()


@pytest.mark.parametrize('camera_kind', ['panzoom', 'turntable'])
def test_scene_camera_drag_changes_view_and_render(application, camera_kind):
    from vispy import scene
    canvas = scene.SceneCanvas(app=application, size=(240, 180), show=True,
                               bgcolor='black')
    view = canvas.central_widget.add_view()
    view.bgcolor = '#101010'
    view.camera = camera_kind
    scene.visuals.Markers(pos=np.array([[0, 0, 0], [1, .25, .5], [-.5, .75, -.25]],
                                      dtype=np.float32),
                          size=20, face_color='red', parent=view.scene)
    view.camera.set_range(x=(-1, 1.5), y=(-1, 1.5), z=(-1, 1))
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None and canvas.native.winfo_viewable())
    before_pixels = canvas.render(alpha=True)
    assert canvas.visual_at((90, 70)) is not None, 'Scene picking must route the drag to a view'
    before = (view.camera.rect.pos + view.camera.rect.size if camera_kind == 'panzoom' else
              (view.camera.azimuth, view.camera.elevation))
    canvas.native.event_generate('<ButtonPress-1>', x=90, y=70)
    time.sleep(.012)
    canvas.native.event_generate('<Motion>', x=140, y=100, state=0x100)
    canvas.native.event_generate('<ButtonRelease-1>', x=140, y=100, state=0x100)
    after = (view.camera.rect.pos + view.camera.rect.size if camera_kind == 'panzoom' else
             (view.camera.azimuth, view.camera.elevation))
    assert before != after
    after_pixels = canvas.render(alpha=True)
    assert not np.array_equal(before_pixels, after_pixels)
    canvas.close()


def test_explicit_parent_without_default_root(monkeypatch):
    import tkinter as tk
    monkeypatch.setattr(tk, '_support_default_root', False)
    monkeypatch.delattr(tk, '_default_root', raising=False)
    root = tk.Tk()
    application = app.Application('tkinter')
    try:
        canvas = app.Canvas(app=application, parent=root, size=(192, 128))
        assert application.native is root
        canvas.native.pack()
        paint(canvas)
        canvas.update()
        wait(application, lambda: canvas._backend._photo is not None)
        application.quit()
        assert root.winfo_exists()
        assert not root.winfo_children()
    finally:
        application.quit()
        root.update_idletasks()
        root.destroy()


def test_shared_root_survives_first_application_quit():
    first = app.Application('tkinter')
    second = app.Application('tkinter')
    root = first.native
    one = app.Canvas(app=first, size=(192, 128))
    two = app.Canvas(app=second, size=(192, 128), show=True)
    try:
        assert second.native is root
        paint(two)
        first.quit()
        assert one._closed and not two._closed
        assert root.winfo_exists()
        two.update()
        wait(second, lambda: two._backend._photo is not None)
    finally:
        first.quit()
        second.quit()


def test_quit_updates_timer_state_and_restart_rebinds_root():
    application = app.Application('tkinter')
    ticks = []
    timer = app.Timer(app=application, interval=.001,
                      connect=lambda event: ticks.append(event.iteration), start=True)
    old_root = application.native
    application.quit()
    assert not timer.running and timer._backend._job is None
    try:
        timer.start(iterations=1)
        assert application.native is not old_root
        wait(application, lambda: len(ticks) == 1 and not timer.running)
    finally:
        application.quit()


def test_external_root_destruction_stops_native_canvas_and_timer():
    import tkinter as tk
    root = tk.Tk()
    application = app.Application('tkinter')
    canvas = app.Canvas(app=application, parent=root, size=(192, 128))
    timer = app.Timer(app=application, interval=10, start=True)
    root.update_idletasks()
    root.destroy()
    assert canvas._closed and canvas._backend._dawn_canvas_id == 0
    assert not timer.running and timer._backend._job is None
    application.quit()  # Idempotent after externally initiated destruction.


@pytest.mark.parametrize('stage', ['widget', 'image', 'binding'])
def test_early_widget_construction_failure_unwinds(application, monkeypatch, stage):
    import tkinter as tk
    root = application.native
    before = set(root.winfo_children())

    def fail(*args, **kwargs):
        raise ValueError('intentional early ' + stage)

    if stage == 'widget':
        monkeypatch.setattr(tk, 'Canvas', fail)
    elif stage == 'image':
        monkeypatch.setattr(tk.Canvas, 'create_image', fail)
    else:
        monkeypatch.setattr(tk.Canvas, 'bind', fail)
    with pytest.raises(ValueError, match='intentional early ' + stage):
        app.Canvas(app=application, size=(192, 128))
    assert set(root.winfo_children()) == before
    assert not application._backend._canvases


def test_unrelated_tk_window_survives_owning_application_quit():
    import tkinter as tk
    application = app.Application('tkinter')
    root = application.native
    unrelated = tk.Toplevel(root)
    canvas = app.Canvas(app=application, size=(192, 128))
    application.quit()
    try:
        assert canvas._closed
        assert root.winfo_exists() and unrelated.winfo_exists()
        assert application._backend._root is None
        root.update()
    finally:
        root.update_idletasks()
        root.destroy()


def test_live_application_refuses_second_interpreter_without_touching_it():
    import tkinter as tk
    first = tk.Tk()
    second = tk.Tk()
    application = app.Application('tkinter')
    try:
        canvas = app.Canvas(app=application, parent=first, size=(192, 128))
        with pytest.raises(RuntimeError, match='multiple live Tcl interpreters'):
            app.Canvas(app=application, parent=second, size=(192, 128))
        assert application.native is first
        assert not second.winfo_children()
        assert not canvas._closed
    finally:
        application.quit()
        first.update_idletasks()
        first.destroy()
        second.update_idletasks()
        second.destroy()


def test_root_recreated_after_external_destruction():
    import tkinter as tk
    root = tk.Tk()
    application = app.Application('tkinter')
    canvas = app.Canvas(app=application, parent=root, size=(192, 128))
    root.update_idletasks()
    root.destroy()
    try:
        next_canvas = app.Canvas(app=application, size=(192, 128), show=True)
        assert next_canvas._backend._dawn_canvas_id and canvas._closed
        assert application.native is not root
        paint(next_canvas)
        next_canvas.update()
        wait(application, lambda: next_canvas._backend._photo is not None)
    finally:
        application.quit()


def test_constructor_preserves_originating_error_when_cleanup_also_fails(application, monkeypatch):
    from vispy import _dawn
    from vispy.app.backends import _dawn_tk
    root = application.native
    before = set(root.winfo_children())
    original = _dawn_tk.CanvasBackend._vispy_close

    def register_failure(*args):
        raise ValueError('originating allocation error')

    def cleanup_failure(self):
        original(self)
        raise RuntimeError('secondary cleanup error')

    monkeypatch.setattr(_dawn, 'register_canvas', register_failure)
    monkeypatch.setattr(_dawn_tk.CanvasBackend, '_vispy_close', cleanup_failure)
    with pytest.raises(ValueError, match='originating allocation error'):
        app.Canvas(app=application, size=(192, 128))
    assert set(root.winfo_children()) == before
