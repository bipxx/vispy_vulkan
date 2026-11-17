import asyncio
import warnings

from ..base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend
from ...app import Timer
from ...gloo.context import forget_canvas
from ...util import keys
from ._offscreen_util import OffscreenContext, FrameBufferHelper


def _get_or_create_event_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop


try:
    from jupyter_rfb import RemoteFrameBuffer
except Exception:
    RemoteFrameBuffer = object
    _msg = 'The jupyter_rfb backend relies on a the jupyter_rfb library: ``pip install jupyter_rfb``'
    available, testable, why_not, which = False, False, _msg, None
else:
    available, testable, why_not = True, False, None
    which = "jupyter_rfb"


# -------------------------------------------------------------- capability ---

capability = dict(
    title=True,
    size=True,
    position=False,
    show=False,
    vsync=False,
    resizable=True,
    decorate=False,
    fullscreen=False,
    context=False,  # Could work, but not implemented
    multi_window=True,
    scroll=True,
    parent=False,  # ipywidgets has layouts, but has no concept of parents
    always_on_top=False,
)


# ------------------------------------------------------- set_configuration ---

# The configuration mostly applies to the framebuffer. So if we'd want
# to implement some of that, we'd probably have to apply it to the FBO.


# ------------------------------------------------------------- application ---


class ApplicationBackend(BaseApplicationBackend):

    def __init__(self):
        super().__init__()

    def _vispy_get_backend_name(self):
        return 'jupyter_rfb'

    def _vispy_process_events(self):
        raise RuntimeError("Cannot process events while asyncio event-loop is running.")

    def _vispy_run(self):
        pass  # We're in IPython; don't enter a mainloop or we'll block!

    def _vispy_quit(self):
        pass

    def _vispy_get_native_app(self):
        return asyncio


# ------------------------------------------------------------------ canvas ---

class CanvasBackend(BaseCanvasBackend, RemoteFrameBuffer):

    _double_click_supported = True

    # Set jupyter_rfb bitmask to accept new style events with 'type' 'timestamp' and 'ratio'
    _event_compatibility = 2

    def __init__(self, vispy_canvas, **kwargs):
        BaseCanvasBackend.__init__(self, vispy_canvas)
        RemoteFrameBuffer.__init__(self)
        # Use a Dawn offscreen context per canvas so canvas state remains isolated.
        self._context = OffscreenContext()
        self._helper = FrameBufferHelper()
        self._loop = _get_or_create_event_loop()
        self._logical_size = 1, 1
        self._physical_size = 1, 1
        self._pending_resize = False
        self._lifecycle = 0  # 0: not initialized, 1: initialized, 2: closed
        self._buttons = []
        # Init more based on kwargs (could maybe handle, title, show, context)
        self._vispy_set_size(*kwargs["size"])
        self.resizable = kwargs["resizable"]
        # Need a first update
        self._vispy_update()

    def handle_event(self, ev):
        # From jupyter_rfb 1.0 it uses the renderview event spec wich was
        # changed a tiny bit from the 0.x jupyter event spec.
        # (event_type -> type, time_stamp -> timestamp, pixel_ratio -> ratio).
        # We use ev.get() where necessary to make it backwards compatible.
        # These could be removed when we pin jupyter_rfb to 1.x
        type = ev.get("type", None) or ev["event_type"]
        assert type
        if type == "resize":
            # Note that jupyter_rfb already throttles this event
            w, h = ev["width"], ev["height"],
            r = ev.get("ratio", None) or ev["pixel_ratio"]
            self._logical_size = w, h
            self._physical_size = int(w * r), int(h * r)
            self._helper.set_physical_size(*self._physical_size)
            self._pending_resize = True
            self._loop.call_soon(self._flush_pending_resize)
            self._vispy_update()  # make sure to schedule a new draw
        elif type == "pointer_down":
            button = ev["button"]
            if button not in self._buttons:
                self._buttons.append(button)

            self._vispy_mouse_press(
                native=ev,
                pos=(ev["x"], ev["y"]),
                button=button,
                buttons=self._buttons,
                modifiers=self._modifiers(ev),
            )
        elif type == "pointer_up":
            button = ev["button"]
            if button in self._buttons:
                self._buttons.remove(button)

            self._vispy_mouse_release(
                native=ev,
                pos=(ev["x"], ev["y"]),
                button=button,
                buttons=self._buttons,
                modifiers=self._modifiers(ev),
            )
        elif type == "pointer_move":
            self._vispy_mouse_move(
                native=ev,
                pos=(ev["x"], ev["y"]),
                button=ev["button"],
                buttons=self._buttons,
                modifiers=self._modifiers(ev),
            )
        elif type == "double_click":
            self._vispy_mouse_double_click(
                native=ev,
                pos=(ev["x"], ev["y"]),
                button=ev["button"],
                buttons=self._buttons,
                modifiers=self._modifiers(ev),
            )
        elif type == "wheel":
            self._vispy_canvas.events.mouse_wheel(
                native=ev,
                pos=(ev["x"], ev["y"]),
                delta=(ev["dx"] / 100, - ev["dy"] / 100),
                buttons=self._buttons,
                modifiers=self._modifiers(ev),
            )
        elif type == "key_down":
            # The special key names are all (most?) the same
            # But the key is actually more like tex, e.g. shift + 3 becomes "#"
            self._vispy_canvas.events.key_press(
                native=ev,
                key=keys.Key(ev["key"]),
                modifiers=self._modifiers(ev),
                text=ev["key"],
            )
        elif type == "key_up":
            self._vispy_canvas.events.key_release(
                native=ev,
                key=keys.Key(ev["key"]),
                modifiers=self._modifiers(ev),
                text=ev["key"],
            )
        elif type == "close":
            self._cleanup_dawn_resources()
        else:
            pass  # event ignored / unknown

    def _modifiers(self, ev):
        return tuple(getattr(keys, m.upper()) for m in ev["modifiers"])

    @property
    def _dawn_canvas_id(self):
        ctx = getattr(self, "_context", None)
        if ctx is None or getattr(ctx, "_is_closed", True):
            return 0
        canvas = getattr(ctx, "_canvas", None)
        backend = getattr(canvas, "_backend", None) if canvas is not None else None
        if canvas is None or getattr(canvas, "_closed", True):
            return 0
        return int(getattr(backend, "_dawn_canvas_id", 0) or 0)

    def _cleanup_dawn_resources(self):
        if getattr(self, "_lifecycle", 2) == 2:
            return
        self._lifecycle = 2
        self._pending_resize = False
        vispy_canvas = getattr(self, "_vispy_canvas", None)
        if vispy_canvas is not None:
            _stop_timers(vispy_canvas)
        ctx = getattr(self, "_context", None)
        helper = getattr(self, "_helper", None)
        try:
            if ctx is not None and not getattr(ctx, "_is_closed", True):
                ctx.make_current()
            if helper is not None:
                helper.close()
            if vispy_canvas is not None:
                try:
                    vispy_canvas.context.flush_commands()
                except Exception:
                    pass
            if ctx is not None and getattr(ctx, "_canvas", None) is not None and not getattr(ctx, "_is_closed", True):
                try:
                    ctx._canvas.context.flush_commands()
                except Exception:
                    pass
        finally:
            if ctx is not None:
                ctx.close()
            if vispy_canvas is not None:
                forget_canvas(vispy_canvas)

    def _flush_pending_resize(self):
        if self._pending_resize and self._lifecycle != 2:
            self._emit_resize_event()

    def _emit_resize_event(self):
        self._pending_resize = False
        self._vispy_canvas.events.resize(
            size=self._logical_size,
            physical_size=self._physical_size,
        )

    def get_frame(self):
        # This gets automatically called by the RFB widget

        # Only draw if open and the draw region is not null
        if self._lifecycle == 2 or self._physical_size[0] <= 1 or self._physical_size[1] <= 1:
            return None

        # Handle initialization
        if not self._lifecycle:
            self._lifecycle = 1
            self._vispy_canvas.set_current()
            self._vispy_canvas.events.initialize()
            self._emit_resize_event()
        elif self._pending_resize:
            self._vispy_canvas.set_current()
            self._emit_resize_event()

        # Draw and obtain result
        self._vispy_canvas.set_current()
        with self._helper:
            self._vispy_canvas.events.draw(region=None)
            array = self._helper.get_frame()

        # Flush commands here to clean up - otherwise we get errors related to
        # framebuffers not existin.
        self._vispy_canvas.context.flush_commands()

        return array

    def _vispy_warmup(self):
        self._vispy_canvas.set_current()

    def _vispy_set_current(self):
        self._context.make_current()

    def _vispy_swap_buffers(self):
        pass

    def _vispy_set_title(self, title):
        self.title = title
        self.has_titlebar = bool(title)  # show titlebar when a title is set

    def _vispy_set_size(self, w, h):
        self.css_width = f"{w}px"
        self.css_height = f"{h}px"

    def _vispy_set_position(self, x, y):
        pass

    def _vispy_set_visible(self, visible):
        if not visible:
            raise NotImplementedError("Cannot hide the RFB widget")

    def _vispy_set_fullscreen(self, fullscreen):
        raise NotImplementedError()

    def _vispy_update(self):
        self.request_draw()

    def _vispy_close(self):
        self._cleanup_dawn_resources()
        # ipywidget.Widget.close()  ->  closes the comm and removes all views
        if hasattr(self, "close"):
            try:
                self.close()
            except Exception:
                pass

    def __del__(self):
        try:
            self._cleanup_dawn_resources()
        except Exception:
            pass
        super_del = getattr(super(), "__del__", None)
        if callable(super_del):
            try:
                super_del()
            except Exception:
                pass

    def _vispy_get_size(self):
        return self._logical_size

    def _vispy_get_physical_size(self):
        return self._physical_size

    def _vispy_get_position(self):
        return 0, 0

    def _vispy_get_fullscreen(self):
        return False


# ------------------------------------------------------------------- timer ---

class TimerBackend(BaseTimerBackend):

    def __init__(self, vispy_timer):
        super().__init__(vispy_timer)
        self._loop = _get_or_create_event_loop()
        self._task = None

    async def _timer_coro(self, interval):
        while True:
            await asyncio.sleep(interval)
            self._vispy_timeout()

    def _vispy_start(self, interval):
        if self._task is not None:
            self._task.cancel()
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        self._task = self._loop.create_task(self._timer_coro(interval))

    def _vispy_stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def _vispy_timeout(self):
        self._loop.call_soon(self._vispy_timer._timeout)


def _stop_timers(canvas):
    """Stop all timers associated with a canvas."""
    # This is nice and all, but the Canvas object is frozen, so this is never actually used
    for attr in dir(canvas):
        try:
            attr_obj = getattr(canvas, attr)
        except NotImplementedError:
            continue  # prevent error due to props that we don't implement
        else:
            if isinstance(attr_obj, Timer):
                attr_obj.stop()
