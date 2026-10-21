# -*- coding: utf-8 -*-
"""Offscreen Dawn canvas. No Qt and no OpenGL context."""

import time
import weakref

from ..base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend


_canvases = weakref.WeakSet()
_timers = weakref.WeakSet()


available = True
testable = True
why_not = None

capability = dict(
    title=True,
    size=True,
    position=True,
    show=True,
    vsync=False,
    resizable=True,
    decorate=True,
    fullscreen=False,
    context=True,
    multi_window=True,
    scroll=False,
    parent=False,
    always_on_top=False,
)


def _set_config(c):
    return c


class ApplicationBackend(BaseApplicationBackend):
    def __init__(self):
        BaseApplicationBackend.__init__(self)
        self._closed = False

    def _vispy_get_backend_name(self):
        return "dawn_headless"

    def _vispy_process_events(self):
        from vispy import _dawn

        _dawn.process_events()
        now = time.monotonic()
        for timer in list(_timers):
            if timer._deadline is not None and now >= timer._deadline:
                timer._deadline = now + timer._interval
                timer._vispy_timer._timeout()
        for backend in list(_canvases):
            if (not backend._closed and backend._draw_pending and
                    _dawn.frame_ready(backend._dawn_canvas_id)):
                backend._draw_pending = False
                backend._vispy_canvas.set_current()
                backend._vispy_canvas.events.draw(region=None)

    def _vispy_run(self):
        self._closed = False
        while not self._closed and any(not backend._closed for backend in _canvases):
            self._vispy_process_events()
            time.sleep(0.001)

    def _vispy_quit(self):
        self._closed = True

    def _vispy_get_native_app(self):
        return self


class TimerBackend(BaseTimerBackend):
    def __init__(self, vispy_timer):
        BaseTimerBackend.__init__(self, vispy_timer)
        self._deadline = None
        self._interval = 0.0
        _timers.add(self)

    def _vispy_start(self, interval):
        self._interval = max(0.0, float(interval))
        self._deadline = time.monotonic() + self._interval

    def _vispy_stop(self):
        self._deadline = None


class CanvasBackend(BaseCanvasBackend):
    def __init__(self, vispy_canvas, **kwargs):
        BaseCanvasBackend.__init__(self, vispy_canvas)
        p = self._process_backend_kwargs(kwargs)
        self._closed = False
        self._draw_pending = False
        _canvases.add(self)
        self._size = (int(p.size[0]), int(p.size[1]))
        self._physical_size = self._size
        self._position = (0, 0)
        self._title = p.title
        self._visible = bool(p.show)
        self._fullscreen = False
        p.context.shared.add_ref("dawn-headless", self)
        from vispy import _dawn

        samples = int(p.context.config.get("samples", 0) or 0)
        self._samples = samples
        self._dawn_canvas_id = int(_dawn.register_canvas(self._size[0], self._size[1], samples, bool(p.vsync)))
        from ...gloo.dawn_parser import install_gl_queries

        install_gl_queries()
        self._vispy_canvas.events.initialize()
        self._vispy_canvas.events.resize(
            size=self._size, physical_size=self._physical_size
        )

    def _vispy_warmup(self):
        return

    def _vispy_set_current(self):
        return

    def _vispy_swap_buffers(self):
        from vispy import _dawn

        _dawn.present(int(self._dawn_canvas_id))

    def _vispy_set_title(self, title):
        self._title = title

    def _vispy_set_size(self, w, h):
        self._size = (int(w), int(h))
        self._physical_size = self._size
        from vispy import _dawn

        _dawn.configure_canvas(int(self._dawn_canvas_id), int(w), int(h), self._samples)

    def _vispy_set_position(self, x, y):
        self._position = (int(x), int(y))

    def _vispy_set_visible(self, visible):
        self._visible = bool(visible)

    def _vispy_set_fullscreen(self, fullscreen):
        self._fullscreen = bool(fullscreen)

    def _vispy_update(self):
        self._draw_pending = True

    def _vispy_close(self):
        if self._closed:
            return
        self._closed = True
        from vispy import _dawn

        _dawn.destroy_canvas(int(self._dawn_canvas_id))

    def _vispy_get_size(self):
        return self._size

    def _vispy_get_physical_size(self):
        return self._physical_size

    def _vispy_get_position(self):
        return self._position

    def _vispy_get_fullscreen(self):
        return self._fullscreen

    def _vispy_get_native_canvas(self):
        return self

    def _vispy_get_fb_bind_location(self):
        return 0
