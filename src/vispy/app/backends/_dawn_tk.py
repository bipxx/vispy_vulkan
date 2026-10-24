# SPDX-License-Identifier: AGPL-3.0-only
"""Tk widgets with Vulkan rendering and Tk raster presentation.

No pyopengltk, OpenGL context or native Vulkan window surface is used. Tk owns
the displayed RGB image; framebuffer capture retains the renderer's RGBA data.
"""
import sys
import time
import weakref

from ..base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend
from ...util import keys

try:
    import tkinter as tk
except ImportError as error:
    tk = None
    available, testable, why_not = False, False, str(error)
else:
    available, testable, why_not = True, True, None
which = 'Tkinter raster' if tk is None else 'Tkinter %s raster' % tk.TkVersion

capability = dict(title=True, size=True, position=True, show=True, vsync=False,
                  resizable=True, decorate=True, fullscreen=True, context=True,
                  multi_window=True, scroll=True, parent=True, always_on_top=True)
_KEYS = {name: getattr(keys, name.upper()) for name in
         ('Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Insert', 'Delete',
          'Escape', 'Backspace', 'Tab', 'Space')}
_KEYS.update(Return=keys.ENTER, KP_Enter=keys.ENTER, Prior=keys.PAGEUP,
             Next=keys.PAGEDOWN, Shift_L=keys.SHIFT, Shift_R=keys.SHIFT,
             Control_L=keys.CONTROL, Control_R=keys.CONTROL,
             Alt_L=keys.ALT, Alt_R=keys.ALT, Meta_L=keys.META, Meta_R=keys.META)
_KEYS.update({('F%d' % n): getattr(keys, 'F%d' % n) for n in range(1, 13)})
_KEYS.update(space=keys.SPACE, Super_L=keys.META, Super_R=keys.META)


def _set_config(config):
    return config


class ApplicationBackend(BaseApplicationBackend):
    def __init__(self):
        self._root = None
        self._owns_root = False
        self._canvases = weakref.WeakSet()
        self._timers = weakref.WeakSet()

    def _vispy_get_backend_name(self):
        return 'Tkinter'

    def _vispy_get_native_app(self):
        if self._root is None:
            self._root = tk._default_root
            if self._root is None:
                self._root = tk.Tk()
                self._root.withdraw()
                self._owns_root = True
        return self._root

    def _vispy_process_events(self):
        from vispy import _dawn
        _dawn.process_events()
        if self._root is not None:
            # A draw handler may request another frame. Bound manual pumping
            # so an animation cannot keep update() inside Tcl indefinitely.
            deadline = time.monotonic() + .01
            for _ in range(100):
                if not self._root.tk.dooneevent(tk._tkinter.DONT_WAIT):
                    break
                if time.monotonic() >= deadline:
                    break
        for canvas in list(self._canvases):
            if canvas._callback_error is not None:
                error, canvas._callback_error = canvas._callback_error, None
                raise error

    def _vispy_run(self):
        self._vispy_get_native_app().mainloop()

    def _vispy_quit(self):
        for timer in list(self._timers):
            timer._vispy_stop()
        for backend in list(self._canvases):
            backend._vispy_canvas.close()
        if self._root is not None and self._owns_root:
            self._root.update_idletasks()
            self._root.destroy()
            self._root = None
            self._owns_root = False


class CanvasBackend(BaseCanvasBackend):
    def __init__(self, vispy_canvas, **kwargs):
        super().__init__(vispy_canvas)
        p = self._process_backend_kwargs(kwargs)
        self._application = vispy_canvas.app._backend
        root = self._application._vispy_get_native_app()
        self._closed = False
        self._draw_job = None
        self._drawing = False
        self._callback_error = None
        self._photo = None
        self._size = tuple(map(int, p.size))
        self._position = (0, 0)
        self._fullscreen = bool(p.fullscreen)
        self._samples = int(p.context.config.get('samples', 0) or 0)
        self._top = tk.Toplevel(root) if p.parent is None else None
        if self._top is not None:
            self._top.withdraw()
        parent = self._top if self._top is not None else p.parent
        self._widget = tk.Canvas(parent, width=self._size[0], height=self._size[1],
                                 highlightthickness=0, borderwidth=0, takefocus=True)
        self._image_item = self._widget.create_image(0, 0, anchor='nw')
        self._widget.bind('<Destroy>', self._on_destroy, add='+')
        self._widget.bind('<Configure>', self._on_resize, add='+')
        self._widget.bind('<Expose>', lambda event: self._vispy_update(), add='+')
        self._widget.bind('<Motion>', self._on_motion)
        self._widget.bind('<ButtonPress>', self._on_press)
        self._widget.bind('<ButtonRelease>', self._on_release)
        self._widget.bind('<MouseWheel>', self._on_wheel)
        self._widget.bind('<KeyPress>', lambda event: self._on_key(event, True))
        self._widget.bind('<KeyRelease>', lambda event: self._on_key(event, False))
        from vispy import _dawn
        try:
            self._dawn_canvas_id = int(_dawn.register_canvas(*self._size, self._samples, False))
            p.context.shared.add_ref('dawn-tk', self)
            from ...gloo.dawn_parser import install_gl_queries
            install_gl_queries()
            self._application._canvases.add(self)
            if self._top is not None:
                self._top.protocol('WM_DELETE_WINDOW', vispy_canvas.close)
                self._top.resizable(p.resizable, p.resizable)
                self._top.overrideredirect(not p.decorate)
                self._top.attributes('-topmost', bool(p.always_on_top))
                self._vispy_set_title(p.title)
                self._vispy_set_size(*self._size)
                if p.position is not None:
                    self._vispy_set_position(*p.position)
                self._widget.pack(fill='both', expand=True)
            vispy_canvas.set_current()
            vispy_canvas.events.initialize()
            vispy_canvas.events.resize(size=self._size, physical_size=self._size)
            self._vispy_set_visible(p.show)
        except BaseException:
            self._vispy_close()
            raise

    def _vispy_set_current(self):
        pass  # Canvas.set_current selects the GLIR target; there is no GL context.

    def _vispy_swap_buffers(self):
        if self._closed:
            return
        from vispy import _dawn, gloo
        self._vispy_canvas.set_current()
        _dawn.present(self._dawn_canvas_id)
        # Explicit viewport makes capture independent of the application's last
        # viewport/scissor selection. PPM uses top-down RGB, as read_pixels does.
        image = gloo.read_pixels((0, 0, *self._size), alpha=False)
        height, width, _ = image.shape
        data = ('P6\n%d %d\n255\n' % (width, height)).encode('ascii') + image.tobytes()
        photo = tk.PhotoImage(master=self._widget, data=data, format='PPM')
        self._widget.itemconfigure(self._image_item, image=photo)
        self._photo = photo  # Keep the Tcl image alive until it is replaced.

    def _vispy_update(self):
        if not self._closed and self._draw_job is None:
            # Timer callbacks are dispatched in bounded generations. Replacing
            # this with after_idle lets a self-updating draw monopolize one
            # Tcl idle event and prevents process_events() from returning.
            self._draw_job = self._widget.after(0, self._draw)

    def _draw(self):
        self._draw_job = None
        if self._closed or self._drawing:
            return
        from vispy import _dawn
        _dawn.process_events()
        if not _dawn.frame_ready(self._dawn_canvas_id):
            self._draw_job = self._widget.after(1, self._draw)
            return
        self._drawing = True
        try:
            self._vispy_canvas.set_current()
            self._vispy_canvas.events.draw(region=None)
        except Exception as error:
            self._callback_error = error
        finally:
            self._drawing = False

    def _on_resize(self, event):
        if self._closed or event.width <= 0 or event.height <= 0:
            return
        size = (event.width, event.height)
        if size != self._size:
            from vispy import _dawn
            _dawn.configure_canvas(self._dawn_canvas_id, *size, self._samples)
            self._size = size
            self._vispy_canvas.events.resize(size=size, physical_size=size)
            self._vispy_update()

    @staticmethod
    def _modifiers(event):
        return tuple(key for mask, key in ((1, keys.SHIFT), (4, keys.CONTROL),
                     (0x20000 if sys.platform == 'win32' else 8, keys.ALT)) if event.state & mask)

    def _mouse(self, event):
        return dict(pos=(event.x, event.y), modifiers=self._modifiers(event))

    def _on_motion(self, event):
        self._vispy_mouse_move(**self._mouse(event))

    def _on_press(self, event):
        if event.num in (4, 5) and sys.platform.startswith('linux'):
            self._on_wheel(event)
            return
        self._widget.focus_set()
        self._vispy_mouse_press(button={1: 1, 2: 3, 3: 2}.get(event.num, event.num),
                                **self._mouse(event))

    def _on_release(self, event):
        if event.num not in (4, 5) or not sys.platform.startswith('linux'):
            self._vispy_mouse_release(button={1: 1, 2: 3, 3: 2}.get(event.num, event.num),
                                      **self._mouse(event))

    def _on_wheel(self, event):
        num = getattr(event, 'num', None)
        delta = (1 if num == 4 else -1) if num in (4, 5) else event.delta / (
            1 if sys.platform == 'darwin' else 120)
        self._vispy_canvas.events.mouse_wheel(delta=(0, delta), **self._mouse(event))

    def _on_key(self, event, pressed):
        key = _KEYS.get(event.keysym)
        if key is None and len(event.keysym) == 1:
            key = keys.Key(event.keysym)
        emitter = self._vispy_canvas.events.key_press if pressed else self._vispy_canvas.events.key_release
        emitter(key=key, text=event.char, modifiers=self._modifiers(event))

    def _vispy_set_title(self, title):
        if self._top is not None:
            self._top.title(title)

    def _vispy_set_size(self, width, height):
        if self._top is not None:
            self._top.geometry('%dx%d' % (width, height))
        else:
            self._widget.configure(width=width, height=height)

    def _vispy_get_size(self):
        return self._size

    _vispy_get_physical_size = _vispy_get_size

    def _vispy_set_position(self, x, y):
        self._position = (int(x), int(y))
        if self._top is not None:
            self._top.geometry('%+d%+d' % self._position)

    def _vispy_get_position(self):
        widget = self._top if self._top is not None else self._widget
        return widget.winfo_x(), widget.winfo_y()

    def _vispy_set_visible(self, visible):
        if self._top is not None:
            if visible:
                self._top.deiconify()
                self._top.attributes('-fullscreen', self._fullscreen)
            else:
                self._top.withdraw()
        if visible:
            self._vispy_update()

    def _vispy_set_fullscreen(self, fullscreen):
        self._fullscreen = bool(fullscreen)
        if self._top is not None:
            self._top.attributes('-fullscreen', self._fullscreen)

    def _vispy_get_fullscreen(self):
        return self._fullscreen

    def _vispy_get_native_canvas(self):
        return self._widget

    def _on_destroy(self, event):
        if event.widget is self._widget and not self._closed:
            self._vispy_canvas.close()

    def _vispy_close(self):
        if self._closed:
            return
        self._closed = True
        if self._draw_job is not None:
            self._widget.after_cancel(self._draw_job)
            self._draw_job = None
        from vispy import _dawn
        canvas_id = getattr(self, '_dawn_canvas_id', 0)
        if canvas_id:
            _dawn.destroy_canvas(canvas_id)
            self._dawn_canvas_id = 0
        self._photo = None
        self._application._canvases.discard(self)
        if self._widget.winfo_exists():
            self._widget.destroy()
        if self._top is not None and self._top.winfo_exists():
            self._top.destroy()
        if not self._application._canvases and self._application._owns_root:
            self._application._root.quit()


class TimerBackend(BaseTimerBackend):
    def __init__(self, vispy_timer):
        super().__init__(vispy_timer)
        self._application = vispy_timer.app._backend
        self._root = self._application._vispy_get_native_app()
        self._application._timers.add(self)
        self._job = None
        self._generation = 0

    def _vispy_start(self, interval):
        self._vispy_stop()
        self._interval = max(1, round(interval * 1000))
        self._schedule(self._generation)

    def _schedule(self, generation):
        self._job = self._root.after(self._interval, lambda: self._timeout(generation))

    def _vispy_stop(self):
        self._generation += 1
        if self._job is not None:
            self._root.after_cancel(self._job)
            self._job = None

    def _timeout(self, generation):
        self._job = None
        self._vispy_timer._timeout()
        if self._generation == generation:
            self._schedule(generation)
