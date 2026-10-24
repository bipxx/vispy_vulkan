# SPDX-License-Identifier: AGPL-3.0-only
"""Tk widgets with Vulkan rendering and Tk raster presentation.

No pyopengltk, OpenGL context or native Vulkan window surface is used. Tk owns
the displayed RGB image; framebuffer capture retains the renderer's RGBA data.
"""
import sys
import threading
from functools import wraps
import time
import weakref

from ..base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend
from ...util import keys, logger

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
_KEYS.update(space=keys.SPACE, ISO_Left_Tab=keys.TAB, Super_L=keys.META,
             Super_R=keys.META, Win_L=keys.META, Win_R=keys.META)
_KEYS.update({'KP_' + name: _KEYS[name] for name in
              ('Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Insert', 'Delete', 'Prior', 'Next')})
_MODIFIER_KEYS = {name: key for name, key in _KEYS.items()
                  if key in (keys.SHIFT, keys.CONTROL, keys.ALT, keys.META)}


def _ui_thread_only(method):
    @wraps(method)
    def checked(self, *args, **kwargs):
        application = getattr(self, '_application', self)
        application._check_thread()
        return method(self, *args, **kwargs)
    return checked


def _validate_request(context, kwargs):
    config = context.config
    for key, maximum in (('red_size', 8), ('green_size', 8), ('blue_size', 8),
                         ('alpha_size', 8), ('depth_size', 24), ('stencil_size', 8)):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
            raise RuntimeError('Tk raster configuration %s=%r is unsupported; guaranteed range is 0..%d'
                               % (key, value, maximum))
    samples = config['samples']
    if isinstance(samples, bool) or not isinstance(samples, int) or samples not in (0, 1, 4):
        raise RuntimeError('Tk raster configuration samples=%r is unsupported; use 0, 1 or 4' % samples)
    if config['stereo']:
        raise RuntimeError('Tk raster configuration stereo=True is unsupported')
    # The upstream default is a legacy GL window hint. An explicit native
    # double-buffer request cannot be satisfied by Tk image presentation.
    if config['double_buffer'] and 'double_buffer' in context._requested_config:
        raise RuntimeError('Tk raster configuration double_buffer=True is unsupported; use False')
    if not isinstance(kwargs['fullscreen'], bool):
        raise RuntimeError('Tk fullscreen supports bool only; monitor-index selection is unsupported')
    if kwargs['vsync']:
        raise RuntimeError('Tk raster vsync is unsupported')
    if kwargs['parent'] is not None:
        for key, requested in (('position', kwargs['position'] is not None),
                               ('fullscreen', kwargs['fullscreen']),
                               ('resizable', not kwargs['resizable']),
                               ('decorate', not kwargs['decorate']),
                               ('always_on_top', kwargs['always_on_top'])):
            if requested:
                raise RuntimeError('Tk embedded %s is controlled by the host window' % key)


def _set_config(config):
    return config


def _exists(widget):
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


_root_states = {}


def _tcl_commands(root):
    """Include host commands in child namespaces, not only global commands."""
    pending = ['::']
    commands = set()
    while pending:
        namespace = pending.pop()
        pattern = '::*' if namespace == '::' else namespace + '::*'
        commands.update(str(name) for name in root.tk.splitlist(
            root.tk.call('info', 'commands', pattern)))
        pending.extend(str(name) for name in root.tk.splitlist(
            root.tk.call('namespace', 'children', namespace)))
    return commands


class _Cleanup:
    """Finish independent release steps; preserve the first failure and trace."""
    def __init__(self):
        self.error = None

    def run(self, callback, *args):
        try:
            callback(*args)
            return True
        except BaseException:
            if self.error is None:
                self.error = sys.exc_info()
            else:
                logger.error('Additional Tk teardown error', exc_info=True)
            return False

    def raise_error(self):
        if self.error is not None:
            _kind, error, traceback = self.error
            raise error.with_traceback(traceback)


class _RootState:
    """Ownership belongs to a Tcl interpreter, not its first VisPy app."""
    def __init__(self, root, owned):
        self.root = root
        self.ui_thread = threading.get_ident()
        self.owned = owned
        self.apps = weakref.WeakSet()
        self.driver = None
        self.progress_job = None
        self.progress_enabled = False
        # Later Tcl commands can belong to the host, including StringVar
        # trace callbacks that are not tracked by root._tclCommands.
        self._initial_commands = frozenset(_tcl_commands(root))
        self._owned_images = weakref.WeakSet()
        self.binding = root.bind('<Destroy>', self._destroyed, add='+')
        _root_states[root] = self

    def report_error(self, error_info):
        if self.driver is not None:
            if self.driver._pending_error is None:
                self.driver._pending_error = error_info
            else:
                logger.error('Additional Tk callback error', exc_info=error_info)
            if self.driver._running and _exists(self.root):
                self.root.quit()
        else:
            # A borrowed mainloop keeps its user's error policy. Do not replace
            # report_callback_exception globally or consume an exception here.
            self.root.report_callback_exception(*error_info)

    def poll(self):
        if not self.progress_enabled:
            return False
        from vispy import _dawn
        try:
            _dawn.process_events()
            return True
        except BaseException:
            error = sys.exc_info()
            # Timer and draw callbacks may already be ready in the same Tcl
            # event. Stop both routes before reporting a native failure; only
            # an explicit update/event-loop re-entry should retry progress.
            try:
                self.cancel_progress()
            except BaseException:
                logger.error('Additional Tk native progress cancellation error', exc_info=True)
            self.report_error(error)
            return False

    def ensure_progress(self):
        self.progress_enabled = True
        self._schedule_progress()

    def _schedule_progress(self):
        if self.progress_enabled and self.progress_job is None and self.apps and _exists(self.root):
            self.progress_job = self.root.after(5, self._progress)

    def _progress(self):
        self.progress_job = None
        if self.progress_enabled and self.apps:
            if self.poll():
                self._schedule_progress()
            else:
                self.progress_enabled = False
        # A failed poll needs explicit re-entry/redraw to retry, not an endless
        # stream of error reports from a permanently broken device.

    def cancel_progress(self):
        self.progress_enabled = False
        if self.progress_job is not None:
            try:
                self.root.after_cancel(self.progress_job)
            except tk.TclError:
                if _exists(self.root):
                    raise
            self.progress_job = None

    def _destroyed(self, event):
        if event.widget is not self.root:
            return
        _root_states.pop(self.root, None)
        cleanup = _Cleanup()
        cleanup.run(self.cancel_progress)
        for application in list(self.apps):
            application._root = None
            application._root_state = None
            application._owns_root = False
            application._quitting = True
            try:
                for timer in list(application._timers):
                    cleanup.run(timer._vispy_timer.stop)
                for canvas in list(application._canvases):
                    cleanup.run(canvas._vispy_canvas.close)
            finally:
                application._quitting = False
        self.apps.clear()
        if cleanup.error is not None:
            self.report_error(cleanup.error)

    def release(self, application):
        if set(self.apps) - {application}:
            self.apps.discard(application)
            return
        self.cancel_progress()
        if _exists(self.root):
            if self.binding is not None:
                self.root.unbind('<Destroy>', self.binding)
                self.binding = None
            if self.owned:
                # Owned jobs and our binding have already retired. Remaining
                # widgets, after jobs, instance bindings or new Tcl
                # commands make this a host-adopted root. Do not pump its idle
                # callbacks as part of deciding ownership or shutting down.
                commands = _tcl_commands(self.root)
                owned_images = {'::' + str(image).lstrip(':') for image in self._owned_images}
                external = (self.root.winfo_children() or
                            self.root.tk.call('after', 'info') or
                            self.root.bind() or commands - self._initial_commands - owned_images)
                if external:
                    self.owned = False
                else:
                    self.root.update_idletasks()
                    self.root.destroy()
        self.apps.discard(application)
        _root_states.pop(self.root, None)


class ApplicationBackend(BaseApplicationBackend):
    def __init__(self):
        self._ui_thread = threading.get_ident()
        self._root = None
        self._owns_root = False
        self._root_state = None
        self._running = False
        self._quitting = False
        self._pending_error = None
        self._canvases = weakref.WeakSet()
        self._pending_closes = set()  # Failed native/job releases keep an owner.
        self._timers = weakref.WeakSet()

    def _check_thread(self):
        if threading.get_ident() != self._ui_thread:
            raise RuntimeError('Tk operation requires its Application UI thread')

    def _vispy_get_backend_name(self):
        return 'Tkinter'

    @_ui_thread_only
    def _vispy_get_native_app(self):
        if self._root is None:
            if self._quitting:
                raise RuntimeError('Cannot create a Tk interpreter while quitting')
            root = getattr(tk, '_default_root', None)
            owned = root is None
            if owned:
                root = tk.Tk()
                root.withdraw()
            self._attach_root(root, owned)
        return self._root

    @_ui_thread_only
    def _attach_root(self, root, owned=False):
        if root is self._root:
            return
        if self._root_state is not None:
            if self._canvases or any(timer._job is not None for timer in self._timers):
                raise RuntimeError('One Tk Application cannot use multiple live Tcl interpreters')
            self._root_state.release(self)
        state = _root_states.get(root)
        if state is None:
            state = _RootState(root, owned)
        if state.ui_thread != self._ui_thread:
            raise RuntimeError('Tk interpreter belongs to another UI thread')
        state.apps.add(self)
        self._root_state = state
        self._root = root
        self._owns_root = state.owned
        state.ensure_progress()

    @_ui_thread_only
    def _vispy_validate_canvas(self, kwargs):
        _validate_request(kwargs['context'], kwargs)

    @_ui_thread_only
    def _vispy_prepare_canvas(self, parent):
        if self._quitting:
            raise RuntimeError('Cannot create a Tk canvas while quitting')
        if parent is not None:
            if not _exists(parent):
                raise RuntimeError('Tk canvas parent has been destroyed')
            self._attach_root(parent._root())
            # Supplying an explicit parent is the host's ownership declaration,
            # even if this interpreter was originally created by VisPy. Unlike
            # observation at release, this also covers opaque Tcl state.
            self._root_state.owned = False
            for application in self._root_state.apps:
                application._owns_root = False

    @_ui_thread_only
    def _vispy_process_events(self):
        state = self._root_state
        if state is None:
            self._raise_pending_error()
            return
        previous_driver = state.driver
        state.driver = self if previous_driver is None else previous_driver
        try:
            state.ensure_progress()
            state.poll()
            # A draw handler may request another frame. Bound manual pumping
            # so an animation cannot keep update() inside Tcl indefinitely.
            deadline = time.monotonic() + .01
            for _ in range(100):
                if state.driver._pending_error is not None or not _exists(state.root):
                    break
                if not state.root.tk.dooneevent(tk._tkinter.DONT_WAIT):
                    break
                if time.monotonic() >= deadline:
                    break
        finally:
            state.driver = previous_driver
        if previous_driver is None:
            self._raise_pending_error()

    def _raise_pending_error(self):
        if self._pending_error is not None:
            _kind, error, traceback = self._pending_error
            self._pending_error = None
            raise error.with_traceback(traceback)

    def _callback(self, callback):
        state = self._root_state

        def invoke(*args):
            try:
                return callback(*args)
            except BaseException:
                state.report_error(sys.exc_info())
        return invoke

    @_ui_thread_only
    def _vispy_run(self):
        self._raise_pending_error()
        root = self._vispy_get_native_app()
        state = self._root_state
        if state.driver is not None:
            raise RuntimeError('Cannot nest a Tk Application.run event loop')
        state.driver = self
        self._running = True
        try:
            state.ensure_progress()
            root.mainloop()
            self._raise_pending_error()
        finally:
            self._running = False
            state.driver = None

    @_ui_thread_only
    def _vispy_quit(self):
        if self._quitting:
            return
        self._quitting = True
        cleanup = _Cleanup()
        try:
            for timer in list(self._timers):
                cleanup.run(timer._vispy_timer.stop)
            for backend in set(self._canvases) | self._pending_closes.copy():
                cleanup.run(backend._vispy_close if backend._vispy_canvas._closed else
                            backend._vispy_canvas.close)
            if self._running and _exists(self._root):
                cleanup.run(self._root.quit)
            pending = self._pending_closes or any(timer._job is not None for timer in self._timers)
            state = self._root_state
            if not pending:
                if state is None or cleanup.run(state.release, self):
                    self._root_state = None
                    self._root = None
                    self._owns_root = False
            elif state is not None and not (set(state.apps) - {self}):
                cleanup.run(state.cancel_progress)
        finally:
            self._quitting = False
        cleanup.raise_error()


class CanvasBackend(BaseCanvasBackend):
    def __init__(self, vispy_canvas, **kwargs):
        _validate_request(kwargs['context'], kwargs)
        super().__init__(vispy_canvas)
        p = self._process_backend_kwargs(kwargs)
        self._application = vispy_canvas.app._backend
        root = self._application._vispy_get_native_app()
        self._root = root
        self._closed = False
        self._closing = False
        self._draw_job = None
        self._drawing = False
        self._pressed_buttons = set()
        self._pressed_modifiers = set()
        self._pressed_keys = {}
        self._last_pointer = (0, 0)
        self._photo = None
        self._hidden_layout = None
        self._size = tuple(map(int, p.size))
        self._position = (0, 0)
        self._fullscreen = p.fullscreen
        self._samples = int(p.context.config.get('samples', 0) or 0)
        self._top = None
        self._widget = None
        self._dawn_canvas_id = 0
        from vispy import _dawn
        try:
            self._top = tk.Toplevel(root) if p.parent is None else None
            if self._top is not None:
                self._top.withdraw()
            parent = self._top if self._top is not None else p.parent
            self._widget = tk.Canvas(parent, width=self._size[0], height=self._size[1],
                                     highlightthickness=0, borderwidth=0, takefocus=True)
            self._image_item = self._widget.create_image(0, 0, anchor='nw')
            self._bind('<Destroy>', self._on_destroy, add='+')
            self._bind('<Configure>', self._on_resize, add='+')
            self._bind('<Expose>', lambda event: self._vispy_update(), add='+')
            self._bind('<Motion>', self._on_motion)
            self._bind('<ButtonPress>', self._on_press)
            self._bind('<ButtonRelease>', self._on_release)
            self._bind('<FocusOut>', self._on_focus_out)
            self._bind('<MouseWheel>', self._on_wheel)
            self._bind('<KeyPress>', lambda event: self._on_key(event, True))
            self._bind('<KeyRelease>', lambda event: self._on_key(event, False))
            self._dawn_canvas_id = int(_dawn.register_canvas(*self._size, self._samples, False))
            p.context.shared.add_ref('dawn-tk', self)
            from ...gloo.dawn_parser import install_gl_queries
            install_gl_queries()
            self._application._canvases.add(self)
            if self._top is not None:
                self._top.protocol('WM_DELETE_WINDOW', self._application._callback(vispy_canvas.close))
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
            try:
                self._vispy_close()
            except Exception:
                logger.error('Tk canvas construction cleanup failed', exc_info=True)
            raise

    def _bind(self, sequence, callback, **kwargs):
        self._widget.bind(sequence, self._application._callback(callback), **kwargs)

    def _vispy_check_thread(self):
        self._application._check_thread()

    @_ui_thread_only
    def _vispy_set_current(self):
        pass  # Canvas.set_current selects the GLIR target; there is no GL context.

    @_ui_thread_only
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
        self._application._root_state._owned_images.add(photo)
        self._widget.itemconfigure(self._image_item, image=photo)
        self._photo = photo  # Keep the Tcl image alive until it is replaced.

    @_ui_thread_only
    def _vispy_update(self):
        if not self._closed and self._draw_job is None:
            self._application._root_state.ensure_progress()
            # Timer callbacks are dispatched in bounded generations. Replacing
            # this with after_idle lets a self-updating draw monopolize one
            # Tcl idle event and prevents process_events() from returning.
            self._draw_job = self._root.after(0, self._application._callback(self._draw))

    def _draw(self):
        self._draw_job = None
        if self._closed or self._drawing:
            return
        from vispy import _dawn
        state = self._application._root_state
        if state is None or not state.poll():
            return
        if not _dawn.frame_ready(self._dawn_canvas_id):
            self._draw_job = self._root.after(1, self._application._callback(self._draw))
            return
        self._drawing = True
        try:
            self._vispy_canvas.set_current()
            self._vispy_canvas.events.draw(region=None)
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

    def _modifiers(self, event, released=None):
        # Tk's floating Meta/Alt bits are distinct from platform Mod1..5.
        # Windows Mod1 is NumLock, not Alt. X11 uses the default Mod1 Alt /
        # Mod4 Super layout here; arbitrary remappings need their own profile.
        alt, meta = 0x20000, 0x10000
        if sys.platform == 'darwin':
            alt |= 16  # Option
            meta |= 8  # Command
        elif sys.platform.startswith('linux'):
            alt |= 8
            meta |= 64
        held = {_MODIFIER_KEYS[name] for name in self._pressed_modifiers}
        state = getattr(event, 'state', 0)
        return tuple(key for mask, key in ((1, keys.SHIFT), (4, keys.CONTROL),
                                          (alt, keys.ALT), (meta, keys.META))
                     if (key in held or state & mask) and (key != released or key in held))

    def _mouse(self, event):
        self._last_pointer = (event.x, event.y)
        return dict(pos=self._last_pointer, modifiers=self._modifiers(event),
                    buttons=sorted(self._pressed_buttons), native=event)

    def _vispy_detect_double_click(self, event):
        # Retain the pinned base detector's 0.3-second / exact-position policy.
        # Base invokes this with only the press event; forward its metadata so
        # the derived event does not acquire default position/button values.
        super()._vispy_detect_double_click(
            event, pos=event.pos, button=event.button, buttons=event.buttons,
            modifiers=event.modifiers, native=event.native)

    def _on_motion(self, event):
        self._vispy_mouse_move(**self._mouse(event))

    def _on_press(self, event):
        if event.num in (4, 5) and sys.platform.startswith('linux'):
            self._on_wheel(event)
            return
        self._widget.focus_set()
        button = {1: 1, 2: 3, 3: 2}.get(event.num, event.num)
        self._pressed_buttons.add(button)
        self._vispy_mouse_press(button=button, **self._mouse(event))

    def _on_release(self, event):
        if event.num not in (4, 5) or not sys.platform.startswith('linux'):
            button = {1: 1, 2: 3, 3: 2}.get(event.num, event.num)
            self._pressed_buttons.discard(button)
            self._vispy_mouse_release(button=button, **self._mouse(event))

    def _on_focus_out(self, event):
        # Tk's implicit pointer grab handles physical releases outside the
        # widget. Losing focus can instead leave the gesture without a release;
        # cancel it explicitly so camera interactions never retain stale input.
        self._pressed_modifiers.clear()
        self._pressed_keys.clear()
        cleanup = _Cleanup()
        for button in sorted(self._pressed_buttons):
            self._pressed_buttons.discard(button)
            cleanup.run(lambda button=button: self._vispy_mouse_release(
                button=button, pos=self._last_pointer, buttons=sorted(self._pressed_buttons),
                modifiers=(), native=event))
        for name in self._vispy_mouse_data:
            self._vispy_mouse_data[name] = None
        cleanup.raise_error()

    def _on_wheel(self, event):
        num = getattr(event, 'num', None)
        delta = (1 if num == 4 else -1) if sys.platform.startswith('linux') and num in (4, 5) else event.delta / (
            1 if sys.platform == 'darwin' else 120)
        self._vispy_canvas.events.mouse_wheel(delta=(0, delta), **self._mouse(event))

    def _on_key(self, event, pressed):
        modifier = _MODIFIER_KEYS.get(event.keysym)
        if modifier is not None:
            if pressed:
                self._pressed_modifiers.add(event.keysym)
            else:
                self._pressed_modifiers.discard(event.keysym)
        key = _KEYS.get(event.keysym)
        text = event.char if event.char and event.char.isprintable() else ''
        if key is None and len(event.keysym) == 1:
            key = keys.Key(event.keysym)
        if key is None and text:
            key = keys.Key(text)
        if key is not None and key != keys.SPACE and event.keysym in _KEYS:
            text = ''  # Navigation/modifier/function keys carry no printable text.
        code = getattr(event, 'keycode', None)
        if code is not None:
            if pressed:
                self._pressed_keys[code] = (key, text)
            else:
                key, text = self._pressed_keys.pop(code, (key, text))
        emitter = self._vispy_canvas.events.key_press if pressed else self._vispy_canvas.events.key_release
        emitter(key=key, text=text, modifiers=self._modifiers(event, None if pressed else modifier), native=event)

    @_ui_thread_only
    def _vispy_set_title(self, title):
        if self._top is not None:
            self._top.title(title)

    @_ui_thread_only
    def _vispy_set_size(self, width, height):
        if self._top is not None:
            self._top.geometry('%dx%d' % (width, height))
        else:
            self._widget.configure(width=width, height=height)

    @_ui_thread_only
    def _vispy_get_size(self):
        return self._size

    _vispy_get_physical_size = _vispy_get_size

    @_ui_thread_only
    def _vispy_set_position(self, x, y):
        if self._top is None:
            raise RuntimeError('Tk embedded position is controlled by the host window')
        self._position = (int(x), int(y))
        if self._top is not None:
            self._top.geometry('%+d%+d' % self._position)

    @_ui_thread_only
    def _vispy_get_position(self):
        widget = self._top if self._top is not None else self._widget
        return widget.winfo_x(), widget.winfo_y()

    @_ui_thread_only
    def _vispy_set_visible(self, visible):
        if self._top is not None:
            if visible:
                self._top.deiconify()
                self._top.attributes('-fullscreen', self._fullscreen)
            else:
                self._top.withdraw()
        else:
            self._set_embedded_visible(bool(visible))
        if visible:
            self._vispy_update()

    def _set_embedded_visible(self, visible):
        widget = self._widget
        manager = widget.winfo_manager()
        if visible:
            if manager:
                # The host has already placed/repositioned the widget.
                self._hidden_layout = None
            elif self._hidden_layout is not None:
                manager, options, following = self._hidden_layout
                options = dict(options)
                if manager == 'pack' and _exists(following) and following.winfo_manager() == 'pack':
                    options['before'] = following
                getattr(widget, manager)(**options)
                self._hidden_layout = None
        elif manager:
            if manager not in ('pack', 'grid', 'place'):
                raise RuntimeError('Tk embedded visibility requires host control for manager %s' % manager)
            options = getattr(widget, manager + '_info')()
            following = None
            if manager == 'pack':
                siblings = options['in'].pack_slaves()
                index = siblings.index(widget) + 1
                following = siblings[index] if index < len(siblings) else None
            getattr(widget, 'grid_remove' if manager == 'grid' else manager + '_forget')()
            self._hidden_layout = (manager, options, following)

    @_ui_thread_only
    def _vispy_set_fullscreen(self, fullscreen):
        if not isinstance(fullscreen, bool):
            raise RuntimeError('Tk fullscreen supports bool only; monitor-index selection is unsupported')
        if self._top is None and fullscreen:
            raise RuntimeError('Tk embedded fullscreen is controlled by the host window')
        if self._top is not None:
            self._top.attributes('-fullscreen', fullscreen)
        self._fullscreen = fullscreen

    @_ui_thread_only
    def _vispy_get_fullscreen(self):
        if self._top is None:
            return False
        return self._top.tk.getboolean(self._top.attributes('-fullscreen'))

    @_ui_thread_only
    def _vispy_get_native_canvas(self):
        return self._widget

    def _on_destroy(self, event):
        if event.widget is self._widget and not self._closed:
            self._vispy_canvas.close()

    @_ui_thread_only
    def _vispy_close(self):
        if self._closing or (self._closed and self not in self._application._pending_closes):
            return
        self._closing = True
        self._closed = True
        self._hidden_layout = None
        self._pressed_buttons.clear()
        self._pressed_modifiers.clear()
        self._pressed_keys.clear()
        for name in self._vispy_mouse_data:
            self._vispy_mouse_data[name] = None
        cleanup = _Cleanup()

        def cancel_draw():
            try:
                self._root.after_cancel(self._draw_job)
            except tk.TclError:
                if _exists(self._root):
                    raise
            self._draw_job = None

        def retire_native():
            from vispy import _dawn
            _dawn.destroy_canvas(self._dawn_canvas_id)
            self._dawn_canvas_id = 0

        try:
            if self._draw_job is not None:
                cleanup.run(cancel_draw)
            if self._dawn_canvas_id:
                cleanup.run(retire_native)
            self._photo = None
            self._application._canvases.discard(self)
            if _exists(self._widget):
                cleanup.run(self._widget.destroy)
            if _exists(self._top):
                cleanup.run(self._top.destroy)
            if self._dawn_canvas_id or self._draw_job is not None or _exists(self._widget) or _exists(self._top):
                self._application._pending_closes.add(self)
            else:
                self._application._pending_closes.discard(self)
            if (not self._application._canvases and self._application._running
                    and _exists(self._application._root)):
                cleanup.run(self._application._root.quit)
        finally:
            self._closing = False
        cleanup.raise_error()


class TimerBackend(BaseTimerBackend):
    def __init__(self, vispy_timer):
        super().__init__(vispy_timer)
        self._application = vispy_timer.app._backend
        self._root = self._application._vispy_get_native_app()
        self._application._timers.add(self)
        self._job = None
        self._generation = 0

    def _vispy_check_thread(self):
        self._application._check_thread()

    @_ui_thread_only
    def _vispy_start(self, interval):
        if self._application._quitting:
            raise RuntimeError('Cannot start a Tk timer while quitting')
        self._vispy_stop()
        self._root = self._application._vispy_get_native_app()
        self._application._root_state.ensure_progress()
        self._interval = max(1, round(interval * 1000))
        self._schedule(self._generation)

    def _schedule(self, generation):
        self._job = self._root.after(self._interval,
                                    self._application._callback(lambda: self._timeout(generation)))

    @_ui_thread_only
    def _vispy_stop(self):
        self._generation += 1
        if self._job is not None:
            try:
                self._root.after_cancel(self._job)
            except tk.TclError:
                if _exists(self._root):
                    raise
            self._job = None

    def _timeout(self, generation):
        if generation != self._generation:
            return
        self._job = None
        try:
            self._vispy_timer._timeout()
        except BaseException:
            try:
                self._vispy_timer.stop()
            except BaseException:
                logger.error('Tk timer stop after callback failure failed', exc_info=True)
            raise
        if self._generation == generation:
            self._schedule(generation)
