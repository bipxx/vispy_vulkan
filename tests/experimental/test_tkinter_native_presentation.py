# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in Tk native-surface prototype; existing raster mode remains default."""
import time
from types import SimpleNamespace

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu


def pump(application, condition):
    deadline = time.monotonic() + 8
    while not condition():
        application.process_events()
        assert time.monotonic() < deadline, 'Tk native presentation timed out'
        time.sleep(.005)


@pytest.fixture
def application():
    import tkinter as tk
    application = app.Application('tkinter')
    yield application
    root = application._backend._root
    application.quit()
    if root is not None:
        try:
            if root.winfo_exists():
                root.destroy()
        except tk.TclError:
            pass


def opened(application, vsync=False, **kwargs):
    canvas = app.Canvas(app=application, size=(160, 96), show=False, vsync=vsync,
                        backend_kwargs={'presentation': 'native'}, **kwargs)
    frames = [0]

    @canvas.events.draw.connect
    def draw(event):
        frames[0] += 1
        _dawn.benchmark_begin_frame(canvas._backend._dawn_canvas_id, frames[0])
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.set_state(scissor_test=False, blend=False)
        gloo.clear(color=(0, 1, 0, 1))

    canvas.show()
    if kwargs.get('parent') is not None:
        canvas.native.pack(fill='both', expand=True)
    pump(application, lambda: bool(_dawn.benchmark_surface_info(canvas._backend._dawn_canvas_id)['attached']))
    return canvas


def rendered(application, canvas):
    frames = []

    def capture():
        canvas.set_current()
        try:
            image = gloo.read_pixels((0, 0, *canvas.physical_size), alpha=True)
        except RuntimeError:
            return False
        if np.array_equal(image[image.shape[0] // 2, image.shape[1] // 2], [0, 255, 0, 255]):
            frames.append(image)
            return True
        return False

    canvas.update()
    pump(application, capture)
    return frames[0]


@pytest.mark.parametrize('vsync', [False, True])
def test_native_surface_renders_without_tk_image(application, monkeypatch, vsync):
    from vispy.app.backends import _dawn_tk

    def no_photo(*args, **kwargs):
        raise AssertionError('Native mode must not allocate a Tk image')

    monkeypatch.setattr(_dawn_tk.tk, 'PhotoImage', no_photo)
    canvas = opened(application, vsync=vsync)
    try:
        image = rendered(application, canvas)
        assert image.shape == (96, 160, 4)
        assert canvas._backend._photo is None
        info = _dawn.benchmark_surface_info(canvas._backend._dawn_canvas_id)
        assert info['attached'] and info['vsync_requested'] is vsync
        pump(application, lambda: any(r['presented'] and r['present_count'] == 1
                                     for r in _dawn.benchmark_completions(canvas._backend._dawn_canvas_id)))
    finally:
        canvas.close()


def test_native_resize_hide_restore_and_input(application):
    canvas = opened(application)
    try:
        rendered(application, canvas)
        canvas.size = (128, 80)
        pump(application, lambda: tuple(canvas.physical_size) == (128, 80))
        assert rendered(application, canvas).shape == (80, 128, 4)
        canvas.show(False)
        identifier = canvas._backend._dawn_canvas_id
        pump(application, lambda: not _dawn.benchmark_surface_info(identifier)['attached'])
        canvas.show()
        pump(application, lambda: _dawn.benchmark_surface_info(identifier)['attached'])
        rendered(application, canvas)
        seen = []
        canvas.events.mouse_press.connect(seen.append)
        canvas.native.event_generate('<ButtonPress-1>', x=11, y=9)
        assert len(seen) == 1 and tuple(seen[0].pos) == (11, 9)
    finally:
        canvas.close()


def test_native_widget_destroy_retires_surface_before_window(application):
    canvas = opened(application)
    rendered(application, canvas)
    widget = canvas.native
    widget.destroy()
    assert canvas._backend._dawn_canvas_id == 0
    assert not widget.winfo_exists()


def test_native_failed_retirement_preserves_live_window_for_retry(application, monkeypatch):
    canvas = opened(application)
    rendered(application, canvas)
    widget = canvas.native

    def fail(identifier):
        raise RuntimeError('injected native retirement failure')

    with monkeypatch.context() as patch:
        patch.setattr(_dawn, 'destroy_canvas', fail)
        with pytest.raises(RuntimeError, match='injected native retirement failure'):
            widget.destroy()
    assert widget.winfo_exists() and canvas._backend._dawn_canvas_id
    assert canvas._backend in application._backend._pending_closes
    widget.destroy()
    assert canvas._backend._dawn_canvas_id == 0 and not widget.winfo_exists()


def test_native_device_loss_keeps_widget_and_recovers(application):
    canvas = opened(application)
    try:
        rendered(application, canvas)
        widget = canvas.native
        before = _dawn.probe()['device_generation']
        _dawn.lose_device()
        canvas.update()
        rendered(application, canvas)
        assert canvas.native is widget and widget.winfo_exists()
        assert _dawn.probe()['device_generation'] > before
        assert _dawn.benchmark_surface_info(canvas._backend._dawn_canvas_id)['attached']
    finally:
        canvas.close()


def test_invalid_presentation_refuses_before_tk_root(application, monkeypatch):
    from vispy.app.backends import _dawn_tk

    def no_root(*args, **kwargs):
        raise AssertionError('Invalid mode must fail before creating Tk')

    monkeypatch.setattr(_dawn_tk.tk, 'Tk', no_root)
    with pytest.raises(ValueError, match='Tk presentation'):
        app.Canvas(app=application, backend_kwargs={'presentation': 'invalid'})


def test_x11_idle_close_prevents_stale_surface_attachment(application, monkeypatch):
    from vispy.app.backends import _dawn_tk
    canvas = opened(application)
    rendered(application, canvas)
    backend = canvas._backend
    backend._surface_window = 0

    def forbidden_attach(*args):
        raise AssertionError('A closed widget must not reach X11 attachment')

    # Exercise the X11 idle boundary on either test host, while retaining the
    # real platform's already-attached surface and teardown implementation.
    with monkeypatch.context() as patch:
        patch.setattr(_dawn_tk, 'sys', SimpleNamespace(platform='linux', exc_info=_dawn_tk.sys.exc_info))
        patch.setattr(canvas.native, 'update_idletasks', canvas.close)
        patch.setattr(_dawn, 'set_surface_x11', forbidden_attach)
        assert backend._native_surface() is False
    assert backend._dawn_canvas_id == 0
