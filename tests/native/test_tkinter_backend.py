# SPDX-License-Identifier: AGPL-3.0-only
"""Real Tk/raster/Vulkan integration; requires a display and Tk, no pyopengltk."""
import sys
import time
from types import SimpleNamespace

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


def _quit_before_watchdog(root, job):
    # Tcl may service more than one ready timer before mainloop sees quit.
    root.after_cancel(job)
    root.quit()


@pytest.fixture
def application():
    import tkinter as tk
    initial_root = getattr(tk, '_default_root', None)
    application = app.Application('tkinter')
    yield application
    root = application._backend._root
    application.quit()
    # An embedding test is the host of its explicitly adopted root. Release
    # that test-owned interpreter after assertions, without touching a root
    # supplied by an outer fixture or hiding a failed VisPy quit.
    if root is not None and root is not initial_root:
        try:
            alive = root.winfo_exists()
        except tk.TclError:
            alive = False
        if alive:
            root.update_idletasks()
            root.destroy()


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


def input_canvas(application):
    canvas = app.Canvas(app=application, size=(80, 60), show=True)
    wait(application, lambda: canvas.native.winfo_viewable())
    canvas.native.focus_force()
    application.process_events()
    return canvas


def test_double_click_keeps_trigger_metadata_and_ordinary_clicks(application, monkeypatch):
    from vispy.app import canvas as canvas_module
    from vispy.util import keys
    canvas = input_canvas(application)
    seen = []
    for name in ('mouse_press', 'mouse_release', 'mouse_double_click'):
        getattr(canvas.events, name).connect(seen.append)
    clock = [10.0]
    monkeypatch.setattr(canvas_module, 'time', lambda: clock[0])
    for timestamp in (10.0, 10.25):
        clock[0] = timestamp
        canvas.native.event_generate('<ButtonPress-1>', x=17, y=23, state=1)
        canvas.native.event_generate('<ButtonRelease-1>', x=17, y=23, state=1)
    assert [event.type for event in seen] == [
        'mouse_press', 'mouse_release', 'mouse_press', 'mouse_double_click', 'mouse_release']
    double = seen[3]
    assert tuple(double.pos) == (17, 23) and double.button == 1
    assert double.buttons == [1] and double.modifiers == (keys.SHIFT,)
    assert double.native is seen[2].native and double.native.widget is canvas.native
    canvas.close()


def test_focus_loss_breaks_double_click_history(application, monkeypatch):
    from vispy.app import canvas as canvas_module
    canvas = input_canvas(application)
    doubles = []
    canvas.events.mouse_double_click.connect(doubles.append)
    monkeypatch.setattr(canvas_module, 'time', lambda: 10.0)
    for sequence in ('<ButtonPress-1>', '<ButtonRelease-1>', '<FocusOut>',
                     '<ButtonPress-1>', '<ButtonRelease-1>'):
        canvas.native.event_generate(sequence, **({} if sequence == '<FocusOut>' else dict(x=17, y=23)))
    assert doubles == []
    canvas.close()


def test_focus_loss_finishes_cancellation_after_release_callback_failure(application):
    canvas = input_canvas(application)
    seen = []
    canvas.events.mouse_release.ignore_callback_errors = False

    def release(event):
        seen.append(event.button)
        if event.button == 1:
            raise ValueError('intentional focus cancellation callback failure')

    canvas.events.mouse_release.connect(release)
    canvas.native.event_generate('<ButtonPress-1>', x=17, y=23)
    canvas.native.event_generate('<ButtonPress-3>', x=17, y=23)
    canvas.native.after(0, lambda: canvas.native.event_generate('<FocusOut>'))
    with pytest.raises(ValueError, match='intentional focus cancellation callback failure'):
        wait(application, lambda: False)
    assert seen == [1, 2]
    moves = []
    canvas.events.mouse_move.connect(moves.append)
    time.sleep(.012)
    canvas.native.event_generate('<Motion>', x=20, y=25)
    assert moves[-1].buttons == [] and not moves[-1].is_dragging
    canvas.close()


@pytest.mark.parametrize('interval,position,button,expected', [
    (.3, (17, 23), 1, 1), (.3001, (17, 23), 1, 0),
    (.1, (18, 23), 1, 0), (.1, (17, 23), 3, 0),
])
def test_double_click_threshold_position_and_button(application, monkeypatch, interval, position, button, expected):
    from vispy.app import canvas as canvas_module
    canvas = input_canvas(application)
    doubles = []
    canvas.events.mouse_double_click.connect(doubles.append)
    clock = [0.0]
    monkeypatch.setattr(canvas_module, 'time', lambda: clock[0])
    canvas.native.event_generate('<ButtonPress-1>', x=17, y=23)
    canvas.native.event_generate('<ButtonRelease-1>', x=17, y=23)
    clock[0] = interval
    canvas.native.event_generate('<ButtonPress-%d>' % button, x=position[0], y=position[1])
    canvas.native.event_generate('<ButtonRelease-%d>' % button, x=position[0], y=position[1])
    assert len(doubles) == expected
    canvas.close()


def test_modifier_aliases_dual_keys_release_state_and_native_provenance(application):
    """Synthetic adapter vectors; not a claim about physical keyboard delivery."""
    from vispy.util import keys
    canvas = input_canvas(application)
    seen = []
    wheels = []
    canvas.events.key_press.connect(seen.append)
    canvas.events.key_release.connect(seen.append)
    canvas.events.mouse_wheel.connect(wheels.append)
    vectors = [
        ('Shift_L', 1, True, 0, (keys.SHIFT,)),
        ('Shift_R', 2, True, 1, (keys.SHIFT,)),
        ('Shift_L', 1, False, 1, (keys.SHIFT,)),
        ('Win_L', 3, True, 1, (keys.SHIFT, keys.META)),
        ('Shift_R', 2, False, 1, (keys.META,)),
        ('Win_L', 3, False, 0, ()),
    ]
    for symbol, code, pressed, state, expected in vectors:
        native = SimpleNamespace(keysym=symbol, keycode=code, char='', state=state)
        canvas._backend._on_key(native, pressed)
        event = seen[-1]
        assert event.key == (keys.META if symbol.startswith('Win') else keys.SHIFT)
        assert event.modifiers == expected and event.native is native and event.text == ''
        pointer = SimpleNamespace(x=11, y=13, state=0, delta=120, num='??')
        canvas._backend._on_wheel(pointer)
        assert wheels[-1].modifiers == expected and wheels[-1].native is pointer
    # Focus loss cancels both sides and printable key-release caches.
    canvas._backend._on_key(SimpleNamespace(keysym='Super_R', keycode=4, char='', state=0), True)
    canvas.native.event_generate('<FocusOut>')
    canvas._backend._on_key(SimpleNamespace(keysym='a', keycode=5, char='a', state=0), True)
    assert seen[-1].modifiers == ()
    canvas.close()


@pytest.mark.parametrize('platform,state,expected', [
    ('win32', 8, ()), ('win32', 0x20000, ('Alt',)), ('win32', 0x10005, ('Shift', 'Control', 'Meta')),
    ('linux', 8, ('Alt',)), ('linux', 64, ('Meta',)), ('linux', 128, ()),
    ('linux', 0x30000, ('Alt', 'Meta')), ('darwin', 8, ('Meta',)), ('darwin', 16, ('Alt',)),
])
def test_synthetic_platform_modifier_masks(application, monkeypatch, platform, state, expected):
    """Translation only: Darwin and remapped X11 layouts remain unqualified."""
    from vispy.app.backends import _dawn_tk
    canvas = input_canvas(application)
    with monkeypatch.context() as patch:
        patch.setattr(_dawn_tk, 'sys', SimpleNamespace(platform=platform))
        modifiers = canvas._backend._modifiers(SimpleNamespace(state=state))
    assert tuple(key.name for key in modifiers) == expected
    canvas.close()


@pytest.mark.parametrize('symbol,text,expected_key,expected_text', [
    ('exclam', '!', '!', '!'), ('U03bb', '\u03bb', '\u03bb', '\u03bb'),
    ('KP_7', '7', '7', '7'), ('KP_Left', '', 'Left', ''),
    ('ISO_Left_Tab', '\t', 'Tab', ''), ('F12', '', 'F12', ''),
    ('UnmappedSymbol', '', None, ''), ('a', '\x01', 'A', ''),
    ('Return', '\r', 'Enter', ''), ('space', ' ', 'Space', ' '),
])
def test_synthetic_key_identity_text_and_release_after_modifier_change(
        application, symbol, text, expected_key, expected_text):
    canvas = input_canvas(application)
    seen = []
    canvas.events.key_press.connect(seen.append)
    canvas.events.key_release.connect(seen.append)
    native = SimpleNamespace(keysym=symbol, keycode=42, char=text, state=0)
    canvas._backend._on_key(native, True)
    release = SimpleNamespace(keysym='UnmappedOnRelease', keycode=42, char='', state=0)
    canvas._backend._on_key(release, False)
    assert len(seen) == 2
    for event, origin in zip(seen, (native, release)):
        assert event.key == expected_key and event.text == expected_text and event.native is origin
    canvas.close()


def test_live_key_events_retain_native_widget_and_printable_text(application):
    canvas = input_canvas(application)
    seen = []
    canvas.events.key_press.connect(seen.append)
    canvas.events.key_release.connect(seen.append)
    canvas.native.event_generate('<KeyPress-a>')
    canvas.native.event_generate('<KeyRelease-a>')
    assert [event.type for event in seen] == ['key_press', 'key_release']
    assert all(event.key == 'A' and event.text == 'a' and event.native.widget is canvas.native for event in seen)
    canvas.close()


def test_live_wheel_units_held_buttons_and_native_metadata(application):
    import tkinter as tk
    from vispy.util import keys
    canvas = input_canvas(application)
    seen, presses = [], []
    canvas.events.mouse_wheel.connect(seen.append)
    canvas.events.mouse_press.connect(presses.append)
    canvas.native.event_generate('<ButtonPress-1>', x=11, y=13)
    for delta in (60, -240):
        canvas.native.event_generate('<MouseWheel>', delta=delta, x=11, y=13, state=1)
    assert [tuple(event.delta) for event in seen] == [(0, .5), (0, -2)]
    assert all(event.buttons == [1] and tuple(event.pos) == (11, 13)
               and event.modifiers == (keys.SHIFT,)
               and event.native.widget is canvas.native for event in seen)
    if sys.platform.startswith('linux') and tk.TkVersion < 8.7:
        for button in (4, 5):
            canvas.native.event_generate('<ButtonPress-%d>' % button, x=11, y=13)
            canvas.native.event_generate('<ButtonRelease-%d>' % button, x=11, y=13)
        assert [tuple(event.delta) for event in seen[2:]] == [(0, 1), (0, -1)]
        assert len(presses) == 1 and canvas._backend._pressed_buttons == {1}
    else:
        if sys.platform.startswith('linux'):
            for delta in (120, -120):
                canvas.native.event_generate('<MouseWheel>', delta=delta, x=11, y=13)
            assert [tuple(event.delta) for event in seen[2:]] == [(0, 1), (0, -1)]
        # Tk9 script button4 is an extra button; pre-fix Tk9.0.3 reports its
        # raw X11 number8. Public nonprimary buttons retain native metadata.
        wheel_count = len(seen)
        canvas.native.event_generate('<ButtonPress-4>', x=11, y=13)
        expected = presses[-1].native.num if sys.platform.startswith('linux') else 4
        assert presses[-1].button == expected and len(seen) == wheel_count
        canvas.native.event_generate('<ButtonRelease-4>', x=11, y=13)
    canvas.native.event_generate('<ButtonRelease-1>', x=11, y=13)
    assert not canvas._backend._pressed_buttons
    canvas.close()


def test_embedded_input_routes_once_and_preserves_host_binding(application):
    import tkinter as tk
    parent = tk.Toplevel(application.native)
    canvases = [app.Canvas(app=application, parent=parent, size=(80, 60)) for _ in range(2)]
    deliveries = [[], []]
    host = []
    parent.bind('<ButtonPress-1>', lambda event: host.append(event.widget), add='+')
    for canvas, seen in zip(canvases, deliveries):
        canvas.native.pack(side='left')
        canvas.events.mouse_press.connect(seen.append)
    wait(application, lambda: all(canvas.native.winfo_viewable() for canvas in canvases))
    for canvas in canvases:
        canvas.native.event_generate('<ButtonPress-1>', x=11, y=13)
        canvas.native.event_generate('<ButtonRelease-1>', x=11, y=13)
    assert [len(seen) for seen in deliveries] == [1, 1]
    assert host == [canvas.native for canvas in canvases]
    canvases[0].close()
    canvases[1].native.event_generate('<ButtonPress-1>', x=11, y=13)
    canvases[1].native.event_generate('<ButtonRelease-1>', x=11, y=13)
    assert [len(seen) for seen in deliveries] == [1, 2] and len(host) == 3
    assert host[-1] is canvases[1].native and parent.winfo_exists()
    parent.destroy()


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


@pytest.mark.parametrize('resource', ['timer', 'idle', 'binding', 'destroy-binding',
                                    'command', 'variable-trace', 'tcl-command',
                                    'namespaced-command', 'image'])
def test_root_without_children_preserves_host_work_on_quit(resource):
    import tkinter as tk
    from vispy.app.backends import _dawn_tk
    application = app.Application('tkinter')
    root = application.native
    state = application._backend._root_state
    assert state.owned
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    wait(application, lambda: canvas._backend._photo is not None)
    canvas.close()
    assert not root.winfo_children()
    assert canvas._backend._photo is None and canvas._backend._dawn_canvas_id == 0
    timer = app.Timer(app=application, interval=60, start=True)
    seen = []
    host_job = None
    sequence = None
    binding = None
    command = None
    variable = None
    image = None
    if resource == 'timer':
        host_job = root.after(60000, lambda: seen.append('host'))
    elif resource == 'idle':
        host_job = root.after_idle(lambda: seen.append('host'))
    elif resource in ('binding', 'destroy-binding'):
        sequence = '<<HostRootPing>>' if resource == 'binding' else '<Destroy>'
        binding = root.bind(sequence, lambda event: seen.append('host'), add='+')
    elif resource == 'command':
        command = root.register(lambda: seen.append('host'))
    elif resource == 'variable-trace':
        variable = tk.StringVar(master=root, value='before')
        variable.trace_add('write', lambda *args: seen.append('host'))
    elif resource == 'image':
        image = tk.PhotoImage(master=root, width=1, height=1)
        image.put('#ff0000', to=(0, 0, 1, 1))
    elif resource == 'namespaced-command':
        command = 'host::owned_command'
        root.tk.eval('namespace eval host {proc owned_command {} {return host}}')
    else:
        command = 'host_owned_command'
        root.tk.eval('proc host_owned_command {} {return host}')
    try:
        application.quit()
        assert root.winfo_exists(), 'VisPy destroyed host work with no child windows'
        assert application._backend._root is None
        assert not state.owned
        assert root not in _dawn_tk._root_states and state.progress_job is None
        assert not timer.running and timer._backend._job is None
        assert not seen, 'quit must not dispatch unrelated host callbacks'
        pending = set(root.tk.call('after', 'info'))
        assert pending == ({host_job} if host_job else set())
        if resource == 'timer':
            script = root.tk.call('after', 'info', host_job)[0]
            root.tk.eval(script)
            root.after_cancel(host_job)
        elif resource == 'idle':
            root.update_idletasks()
        elif resource == 'binding':
            root.deiconify()
            root.update()
            root.event_generate(sequence)
        elif resource == 'destroy-binding':
            assert binding in root.bind(sequence)
            # The host now owns teardown. Drain its idle work before destroying
            # the interpreter; VisPy quit must not dispatch host callbacks.
            root.update_idletasks()
            root.destroy()
        elif resource == 'variable-trace':
            variable.set('after')
        elif resource == 'image':
            assert image.get(0, 0) == (255, 0, 0)
            seen.append('host')
        elif resource in ('tcl-command', 'namespaced-command'):
            seen.append(root.tk.call(command))
        else:
            root.tk.call(command)
        assert seen == ['host']
    finally:
        application.quit()
        try:
            if root.winfo_exists():
                root.update_idletasks()
                root.destroy()  # Host explicitly releases its adopted root.
        except tk.TclError:
            pass


def test_owned_root_still_retires_when_old_vispy_image_has_an_external_reference():
    from vispy.app.backends import _dawn_tk
    application = app.Application('tkinter')
    root = application.native
    state = application._backend._root_state
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    wait(application, lambda: canvas._backend._photo is not None)
    held_image = canvas._backend._photo
    try:
        canvas.close()
        application.quit()
        assert state.owned and not _dawn_tk._exists(root)
        assert application._backend._root is None and state.progress_job is None
        assert held_image is not None  # A traceback/local may retain this wrapper.
        assert application.native is not root
    finally:
        application.quit()


def test_root_adoption_query_failure_preserves_owner_until_explicit_retry(monkeypatch):
    from vispy.app.backends import _dawn_tk
    application = app.Application('tkinter')
    root = application.native
    state = application._backend._root_state
    job = root.after(60000, lambda: None)
    original = _dawn_tk._tcl_commands
    attempts = []

    def fail(target):
        attempts.append(target)
        raise RuntimeError('intentional ownership query failure')

    monkeypatch.setattr(_dawn_tk, '_tcl_commands', fail)
    try:
        with pytest.raises(RuntimeError, match='intentional ownership query failure'):
            application.quit()
        assert attempts == [root]
        assert application._backend._root_state is state
        assert application._backend in state.apps and state.progress_job is None
        assert set(root.tk.call('after', 'info')) == {job}
        monkeypatch.setattr(_dawn_tk, '_tcl_commands', original)
        application.quit()
        assert root.winfo_exists() and application._backend._root is None
        assert set(root.tk.call('after', 'info')) == {job}
    finally:
        monkeypatch.setattr(_dawn_tk, '_tcl_commands', original)
        application.quit()
        root.after_cancel(job)
        root.update_idletasks()
        root.destroy()


def test_adopted_root_reentry_retires_only_vispy_jobs():
    from vispy.app.backends import _dawn_tk
    application = app.Application('tkinter')
    root = application.native
    host_job = root.after(60000, lambda: None)
    try:
        application.quit()
        assert root.winfo_exists() and root not in _dawn_tk._root_states
        canvas = app.Canvas(app=application, size=(192, 128))
        state = application._backend._root_state
        assert application.native is root and not state.owned
        assert state.progress_job is not None
        application.quit()
        assert canvas._closed and canvas._backend._dawn_canvas_id == 0
        assert root not in _dawn_tk._root_states and state.progress_job is None
        assert set(root.tk.call('after', 'info')) == {host_job}
    finally:
        application.quit()
        root.after_cancel(host_job)
        root.update_idletasks()
        root.destroy()


def test_explicit_parent_adopts_created_root_with_opaque_tcl_state():
    from vispy.app.backends import _dawn_tk
    application = app.Application('tkinter')
    root = application.native
    state = application._backend._root_state
    assert state.owned
    root.tk.call('set', 'host_state_without_a_callback', 'preserved')
    try:
        canvas = app.Canvas(app=application, parent=root, size=(192, 128))
        assert not state.owned and not application._backend._owns_root
        application.quit()
        assert canvas._closed and canvas._backend._dawn_canvas_id == 0
        assert root.winfo_exists() and not root.winfo_children()
        assert root.tk.call('set', 'host_state_without_a_callback') == 'preserved'
        assert root not in _dawn_tk._root_states
    finally:
        application.quit()
        root.update_idletasks()
        root.destroy()


def test_shared_root_final_release_preserves_host_work_without_children():
    from vispy.app.backends import _dawn_tk
    first, second = app.Application('tkinter'), app.Application('tkinter')
    root = first.native
    state = first._backend._root_state
    assert second.native is root
    host_job = root.after(60000, lambda: None)
    try:
        assert not root.winfo_children()
        first.quit()
        assert root.winfo_exists() and second._backend in state.apps
        assert state.progress_job is not None
        second.quit()
        assert root.winfo_exists() and root not in _dawn_tk._root_states
        assert first._backend._root is second._backend._root is None
        assert set(root.tk.call('after', 'info')) == {host_job}
    finally:
        first.quit()
        second.quit()
        root.after_cancel(host_job)
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


@pytest.mark.parametrize('mode', ['manual', 'run', 'external'])
@pytest.mark.parametrize('failure', ['draw', 'readiness', 'progress', 'resize', 'input', 'timer',
                                   'presentation', 'image'])
def test_callback_errors_follow_driving_loop(application, monkeypatch, mode, failure):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    wait(application, lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
    root = application.native
    received = []
    original_handler = root.report_callback_exception
    timer = None

    def fail(*args, **kwargs):
        raise ValueError('intentional ' + failure)

    if failure in ('presentation', 'image'):
        import tkinter as tk
        canvas.events.draw.ignore_callback_errors = False
        monkeypatch.setattr(_dawn if failure == 'presentation' else tk,
                            'present' if failure == 'presentation' else 'PhotoImage', fail)
        trigger = canvas.update
    elif failure == 'draw':
        canvas.events.draw.ignore_callback_errors = False
        canvas.events.draw.connect(fail, position='first')
        trigger = canvas.update
    elif failure == 'readiness':
        monkeypatch.setattr(_dawn, 'frame_ready', fail)
        trigger = canvas.update
    elif failure == 'progress':
        monkeypatch.setattr(_dawn, 'process_events', fail)
        trigger = lambda: None  # Idle native progress must work without a draw.
    elif failure == 'resize':
        monkeypatch.setattr(_dawn, 'configure_canvas', fail)
        trigger = lambda: canvas.native.event_generate('<Configure>', width=200, height=130)
    elif failure == 'input':
        canvas.events.mouse_press.ignore_callback_errors = False
        canvas.events.mouse_press.connect(fail)
        trigger = lambda: canvas.native.event_generate('<ButtonPress-1>', x=10, y=10)
    else:
        timer = app.Timer(app=application, interval=.001, connect=fail)
        timer.events.timeout.ignore_callback_errors = False
        trigger = timer.start

    watchdog_fired = []

    def watchdog():
        watchdog_fired.append(True)
        root.quit()

    watchdog_job = root.after(1000, watchdog)
    trigger_job = root.after(0, trigger)
    try:
        if mode == 'external':
            def report(kind, value, traceback):
                received.append((kind, value, traceback))
                root.quit()
            monkeypatch.setattr(root, 'report_callback_exception', report)
            root.mainloop()
            assert len(received) == 1
            assert received[0][0] is ValueError
            assert str(received[0][1]) == 'intentional ' + failure
            assert received[0][2] is not None
            assert root.report_callback_exception is report
        else:
            with pytest.raises(ValueError, match='intentional ' + failure):
                if mode == 'run':
                    application.run(allow_interactive=False)
                else:
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        application.process_events()
                        time.sleep(.001)
                    pytest.fail('manual loop did not propagate callback error')
            assert root.report_callback_exception == original_handler
        assert not watchdog_fired
        if timer is not None:
            assert not timer.running and timer._backend._job is None
        # Correcting the failure and explicitly redrawing must recover, rather
        # than retaining a stale error or a permanently failed scheduled job.
        monkeypatch.undo()
        if failure == 'draw':
            canvas.events.draw.disconnect(fail)
        elif failure == 'input':
            canvas.events.mouse_press.disconnect(fail)
        previous = canvas._backend._photo
        canvas.update()
        wait(application, lambda: canvas._backend._photo is not previous)
    finally:
        root.after_cancel(trigger_job)
        root.after_cancel(watchdog_job)
        if timer is not None:
            timer.stop()
        canvas.close()


@pytest.mark.parametrize('mode', ['run', 'external'])
def test_idle_mainloop_polls_native_progress(application, monkeypatch, mode):
    from vispy import _dawn
    root = application.native
    calls = []
    original = _dawn.process_events

    def progress():
        calls.append(True)
        return original()

    monkeypatch.setattr(_dawn, 'process_events', progress)
    root.after(30, root.quit)
    if mode == 'run':
        application.run(allow_interactive=False)
    else:
        root.mainloop()
    assert calls  # No draw, timer, or manual process_events drove the device.


@pytest.mark.parametrize('mode', ['manual', 'run'])
@pytest.mark.parametrize('error_kind', [KeyboardInterrupt, SystemExit])
def test_base_exceptions_escape_owned_event_drivers(application, mode, error_kind):
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    wait(application, lambda: canvas.native.winfo_viewable())
    canvas.events.draw.ignore_callback_errors = False

    def fail(event):
        raise error_kind('intentional base exception')

    canvas.events.draw.connect(fail)
    root = application.native
    watchdog = root.after(1000, root.quit)
    previous = canvas._backend._photo
    canvas.update()
    try:
        with pytest.raises(error_kind, match='intentional base exception'):
            if mode == 'run':
                application.run(allow_interactive=False)
            else:
                wait(application, lambda: canvas._backend._photo is not previous)
    finally:
        root.after_cancel(watchdog)
        canvas.close()


@pytest.mark.parametrize('mode', ['run', 'external'])
def test_mainloop_device_recovery_and_timer_progress(application, mode):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    canvas.events.draw.ignore_callback_errors = False
    canvas.update()
    wait(application, lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
    previous = canvas._backend._photo
    generation = _dawn.probe()['device_generation']
    root = application.native
    ticks = []

    def tick(event):
        ticks.append(event.iteration)
        if event.iteration == 0:
            _dawn.lose_device()
            canvas.update()
        elif canvas._backend._photo is not previous:
            _quit_before_watchdog(root, job)

    timer = app.Timer(app=application, interval=.01, connect=tick, start=True)
    watchdog_fired = []

    def watchdog():
        watchdog_fired.append(True)
        root.quit()

    job = root.after(1000, watchdog)
    try:
        if mode == 'run':
            application.run(allow_interactive=False)
        else:
            root.mainloop()
        assert not watchdog_fired
        assert len(ticks) >= 2
        assert _dawn.probe()['device_generation'] > generation
        assert canvas._backend._photo is not previous
    finally:
        root.after_cancel(job)
        timer.stop()
        canvas.close()


@pytest.mark.parametrize('mode', ['manual', 'run'])
def test_first_callback_error_survives_later_error_and_other_canvas_recovers(application, mode):
    one = app.Canvas(app=application, size=(192, 128), show=True)
    two = app.Canvas(app=application, size=(192, 128), show=True)
    paint(two)
    wait(application, lambda: one.native.winfo_viewable() and two.native.winfo_viewable())
    one.events.mouse_press.ignore_callback_errors = False
    two.events.mouse_press.ignore_callback_errors = False

    def first(event):
        raise ValueError('first callback error')

    def later(event):
        raise RuntimeError('later callback error')

    one.events.mouse_press.connect(first)
    two.events.mouse_press.connect(later)
    root = application.native

    def batch():
        one.native.event_generate('<ButtonPress-1>', x=10, y=10)
        two.native.event_generate('<ButtonPress-1>', x=10, y=10)

    job = root.after(0, batch)
    watchdog = root.after(1000, root.quit)
    try:
        with pytest.raises(ValueError, match='first callback error'):
            if mode == 'run':
                application.run(allow_interactive=False)
            else:
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    application.process_events()
                pytest.fail('first error was lost')
        two.events.mouse_press.disconnect(later)
        previous = two._backend._photo
        two.update()
        wait(application, lambda: two._backend._photo is not previous)
    finally:
        root.after_cancel(job)
        root.after_cancel(watchdog)
        one.close()
        two.close()


def test_event_emitter_ignore_policy_is_not_overridden(application):
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)

    def fail(event):
        raise ValueError('intentionally ignored by EventEmitter policy')

    assert canvas.events.draw.ignore_callback_errors
    canvas.events.draw.print_callback_errors = 'never'
    canvas.events.draw.connect(fail, position='first')
    canvas.update()
    wait(application, lambda: canvas._backend._photo is not None)
    assert application._backend._pending_error is None
    canvas.close()


def test_timer_restart_inside_callback_has_only_one_scheduled_generation(application):
    root = application.native
    ticks = []
    timeout = []
    timer = app.Timer(app=application, interval=0)

    def tick(event):
        ticks.append(True)
        if len(ticks) == 1:
            timer.stop()
            timer.start(interval=.005)
        elif len(ticks) == 3:
            timer.stop()
            root.after(20, root.quit)

    timer.connect(tick)
    timer.start()

    def watchdog():
        timeout.append(True)
        root.quit()

    job = root.after(1000, watchdog)
    try:
        application.run(allow_interactive=False)
        assert len(ticks) == 3 and not timeout
        assert not timer.running and timer._backend._job is None
    finally:
        root.after_cancel(job)
        timer.stop()


def test_close_callback_failure_still_releases_canvas(application):
    from vispy.gloo.context import get_current_canvas
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    canvas.events.close.ignore_callback_errors = False

    def fail(event):
        raise ValueError('intentional close callback failure')

    canvas.events.close.connect(fail)
    with pytest.raises(ValueError, match='intentional close callback failure'):
        canvas.close()
    assert canvas._backend._dawn_canvas_id == 0
    assert not canvas.native.winfo_exists()
    assert get_current_canvas() is not canvas
    canvas.close()


def test_quit_drains_other_resources_after_stop_and_close_callback_failures():
    application = app.Application('tkinter')
    one = app.Canvas(app=application, size=(192, 128))
    two = app.Canvas(app=application, size=(192, 128))
    timer = app.Timer(app=application, interval=10, start=True)
    timer.events.stop.ignore_callback_errors = False
    one.events.close.ignore_callback_errors = False

    def stop_failure(event):
        raise ValueError('first timer stop failure')

    def close_failure(event):
        raise RuntimeError('secondary close failure')

    timer.events.stop.connect(stop_failure)
    one.events.close.connect(close_failure)
    try:
        with pytest.raises(ValueError, match='first timer stop failure'):
            application.quit()
        assert not timer.running and timer._backend._job is None
        assert one._closed and two._closed
        assert one._backend._dawn_canvas_id == two._backend._dawn_canvas_id == 0
        assert application._backend._root is None
    finally:
        timer.events.stop.disconnect(stop_failure)
        one.events.close.disconnect(close_failure)
        application.quit()


def test_native_close_failure_releases_widgets_and_remains_explicitly_retryable(application, monkeypatch):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    native_id = canvas._backend._dawn_canvas_id
    original = _dawn.destroy_canvas

    def fail(canvas_id):
        if canvas_id == native_id:
            raise RuntimeError('intentional native retirement failure')
        original(canvas_id)

    monkeypatch.setattr(_dawn, 'destroy_canvas', fail)
    with pytest.raises(RuntimeError, match='intentional native retirement failure'):
        canvas.close()
    assert not canvas.native.winfo_exists()
    assert canvas._backend._dawn_canvas_id == native_id  # Never falsely report release.
    monkeypatch.setattr(_dawn, 'destroy_canvas', original)
    application.quit()  # Explicit re-entry retires the remaining native owner.
    assert canvas._backend._dawn_canvas_id == 0


def test_failed_draw_cancellation_keeps_handle_until_explicit_cleanup(application, monkeypatch):
    canvas = app.Canvas(app=application, size=(192, 128))
    canvas.update()
    job = canvas._backend._draw_job
    root = application.native
    original = root.after_cancel

    def fail(handle):
        if handle == job:
            raise RuntimeError('intentional draw cancellation failure')
        return original(handle)

    monkeypatch.setattr(root, 'after_cancel', fail)
    with pytest.raises(RuntimeError, match='intentional draw cancellation failure'):
        canvas.close()
    assert canvas._backend._draw_job == job
    assert canvas._backend._dawn_canvas_id == 0
    assert not canvas.native.winfo_exists()
    monkeypatch.setattr(root, 'after_cancel', original)
    application.quit()
    assert canvas._backend._draw_job is None


def test_timer_cancellation_failure_has_stopped_public_state_and_can_retry(application, monkeypatch):
    timer = app.Timer(app=application, interval=10, start=True)
    job = timer._backend._job
    root = application.native
    original = root.after_cancel

    def fail(handle):
        if handle == job:
            raise RuntimeError('intentional timer cancellation failure')
        return original(handle)

    monkeypatch.setattr(root, 'after_cancel', fail)
    with pytest.raises(RuntimeError, match='intentional timer cancellation failure'):
        timer.stop()
    assert not timer.running
    assert timer._backend._job == job
    monkeypatch.setattr(root, 'after_cancel', original)
    timer.stop()
    assert timer._backend._job is None


def test_progress_cancellation_failure_retains_interpreter_owner_for_retry(application, monkeypatch):
    root = application.native
    state = application._backend._root_state
    job = state.progress_job
    original = root.after_cancel
    attempts = []

    def fail(handle):
        if handle == job:
            attempts.append(handle)
            raise RuntimeError('intentional progress cancellation failure')
        return original(handle)

    monkeypatch.setattr(root, 'after_cancel', fail)
    with pytest.raises(RuntimeError, match='intentional progress cancellation failure'):
        application.quit()
    assert state.progress_job == job and not state.progress_enabled
    assert attempts == [job]  # No automatic retry of the failed release step.
    assert application._backend in state.apps
    assert application._backend._root_state is state and root.winfo_exists()
    monkeypatch.setattr(root, 'after_cancel', original)
    application.quit()
    assert application._backend._root is None and state.progress_job is None


def test_external_destroy_finishes_teardown_before_reporting_stop_error(monkeypatch):
    import tkinter as tk
    root = tk.Tk()
    application = app.Application('tkinter')
    canvas = app.Canvas(app=application, parent=root, size=(192, 128))
    one = app.Timer(app=application, interval=10, start=True)
    two = app.Timer(app=application, interval=10, start=True)
    one.events.stop.ignore_callback_errors = False
    received = []

    def fail(event):
        raise ValueError('external destruction stop failure')

    def report(kind, value, traceback):
        received.append((kind, value))

    monkeypatch.setattr(root, 'report_callback_exception', report)
    one.events.stop.connect(fail)
    root.update_idletasks()
    root.destroy()
    assert canvas._backend._dawn_canvas_id == 0
    assert not one.running and not two.running
    assert one._backend._job is None and two._backend._job is None
    assert application._backend._root is None
    assert len(received) == 1 and received[0][0] is ValueError
    one.events.stop.disconnect(fail)
    application.quit()


def test_stop_callback_cannot_resurrect_timer_during_quit(application):
    timer = app.Timer(app=application, interval=10, start=True)
    timer.events.stop.ignore_callback_errors = False

    def restart(event):
        timer.start()

    timer.events.stop.connect(restart)
    try:
        with pytest.raises(RuntimeError, match='Cannot start a Tk timer while quitting'):
            application.quit()
        assert not timer.running and timer._backend._job is None
        assert application._backend._root is None
    finally:
        timer.events.stop.disconnect(restart)


def test_close_callback_error_survives_native_cleanup_error(application, monkeypatch):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128))
    native_id = canvas._backend._dawn_canvas_id
    original = _dawn.destroy_canvas
    canvas.events.close.ignore_callback_errors = False

    def callback_failure(event):
        raise ValueError('originating close event error')

    def native_failure(canvas_id):
        if canvas_id == native_id:
            raise RuntimeError('secondary native close error')
        return original(canvas_id)

    canvas.events.close.connect(callback_failure)
    monkeypatch.setattr(_dawn, 'destroy_canvas', native_failure)
    with pytest.raises(ValueError, match='originating close event error'):
        canvas.close()
    assert not canvas.native.winfo_exists()
    assert canvas._backend._dawn_canvas_id == native_id
    monkeypatch.setattr(_dawn, 'destroy_canvas', original)
    application.quit()
    assert canvas._backend._dawn_canvas_id == 0


def test_shared_canvas_close_contract_also_cleans_headless_backend():
    from vispy import _dawn
    from vispy.gloo.context import get_current_canvas
    canvas = app.Canvas(app='dawn_headless', size=(8, 8))
    native_id = canvas._backend._dawn_canvas_id
    canvas.events.close.ignore_callback_errors = False

    def fail(event):
        raise ValueError('headless close event failure')

    canvas.events.close.connect(fail)
    with pytest.raises(ValueError, match='headless close event failure'):
        canvas.close()
    assert canvas._backend._closed
    assert get_current_canvas() is not canvas
    with pytest.raises(RuntimeError, match='missing canvas'):
        _dawn.viewport(native_id)
    canvas.close()


@pytest.mark.parametrize('first', ['poll', 'draw'])
def test_native_progress_failure_stops_duplicate_polling_until_explicit_retry(application, monkeypatch, first):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    wait(application, lambda: canvas._backend._photo is not None)
    root = application.native
    state = application._backend._root_state
    assert canvas._backend._draw_job is None
    calls, received = [], []
    host_job = root.after(60000, lambda: None)

    def fail():
        calls.append('poll')
        raise ValueError('single native progress failure')

    def report(kind, value, traceback):
        received.append((kind, value, traceback))

    monkeypatch.setattr(_dawn, 'process_events', fail)
    monkeypatch.setattr(root, 'report_callback_exception', report)
    draw = application._backend._callback(canvas._backend._draw)
    try:
        # Simulate both ready callback orders without relying on wall-clock
        # timer ordering. The second route must not poll a failed device again.
        callbacks = [state.poll, draw, state.poll] if first == 'poll' else [draw, state.poll, draw]
        for callback in callbacks:
            callback()
        assert len(received) == 1 and calls == ['poll']
        assert received[0][0] is ValueError
        assert str(received[0][1]) == 'single native progress failure'
        assert received[0][2] is not None
        assert not state.progress_enabled and state.progress_job is None
        assert host_job in root.tk.call('after', 'info')
    finally:
        monkeypatch.undo()
        root.after_cancel(host_job)
    previous = canvas._backend._photo
    canvas.update()  # Explicit redraw retries both progress and pending drawing.
    wait(application, lambda: canvas._backend._photo is not previous)
    assert state.progress_enabled



def test_native_progress_failure_preserves_original_error_and_failed_cancel_owner(application, monkeypatch):
    from vispy import _dawn
    canvas = app.Canvas(app=application, size=(192, 128), show=True)
    paint(canvas)
    wait(application, lambda: canvas._backend._photo is not None)
    state = application._backend._root_state
    root = application.native
    job = state.progress_job
    assert job is not None
    received = []

    def fail_progress():
        raise ValueError('original native progress failure')

    def fail_cancel(handle):
        assert handle == job
        raise RuntimeError('secondary progress cancellation failure')

    monkeypatch.setattr(_dawn, 'process_events', fail_progress)
    monkeypatch.setattr(root, 'after_cancel', fail_cancel)
    monkeypatch.setattr(root, 'report_callback_exception', lambda *error: received.append(error))
    try:
        assert not state.poll()
        assert len(received) == 1 and received[0][0] is ValueError
        assert str(received[0][1]) == 'original native progress failure'
        assert received[0][2] is not None
        assert not state.progress_enabled and state.progress_job == job
        assert job in root.tk.call('after', 'info')
    finally:
        monkeypatch.undo()  # Owner can now retry the retained cancellation.
    state.cancel_progress()
    assert state.progress_job is None and job not in root.tk.call('after', 'info')


@pytest.mark.parametrize('mode', ['run', 'external'])
def test_successful_loop_exit_retires_already_ready_watchdog(application, mode):
    root = application.native
    seen = []

    def success():
        seen.append('success')
        _quit_before_watchdog(root, watchdog_job)

    def watchdog():
        seen.append('watchdog')
        root.quit()

    success_job = root.after(0, success)
    watchdog_job = root.after(0, watchdog)
    try:
        if mode == 'run':
            application.run(allow_interactive=False)
        else:
            root.mainloop()
        assert seen == ['success']
    finally:
        root.after_cancel(success_job)
        root.after_cancel(watchdog_job)


@pytest.mark.parametrize('want_objects', [True, False])
def test_host_namespace_command_inventory_returns_plain_names(want_objects):
    import tkinter as tk
    from vispy.app.backends import _dawn_tk
    root = tk.Tk()
    root.withdraw()
    try:
        root.tk.eval('namespace eval ::host::nested {proc ping {} {return alive}}')
        root.tk.wantobjects(want_objects)
        commands = _dawn_tk._tcl_commands(root)
        assert all(type(name) is str for name in commands)
        assert '::host::nested::ping' in commands
        assert root.tk.call('::host::nested::ping') == 'alive'
    finally:
        root.tk.call('namespace', 'delete', '::host')
        root.update_idletasks()
        root.destroy()


@pytest.mark.parametrize('button', [4, 5])
def test_legacy_wheel_buttons_are_distinct_from_tk9_extra_buttons(application, button):
    import tkinter as tk
    canvas = input_canvas(application)
    wheels, presses = [], []
    canvas.events.mouse_wheel.connect(wheels.append)
    canvas.events.mouse_press.connect(presses.append)
    event = tk.Event()
    event.num, event.x, event.y, event.state = button, 11, 13, 0
    event.widget, event.delta = canvas.native, 0
    canvas._backend._on_press(event)
    if sys.platform.startswith('linux') and tk.TkVersion < 8.7:
        assert not presses
        assert [tuple(value.delta) for value in wheels] == [(0, 1 if button == 4 else -1)]
    else:
        assert not wheels
        assert len(presses) == 1 and presses[0].button == button
    canvas._backend._on_release(event)
    assert not canvas._backend._pressed_buttons
    canvas.close()
