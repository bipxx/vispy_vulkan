# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""Dawn QWidget support shared by PyQt5, PyQt6 and PySide6.

The binding wrappers select one toolkit per process. Resource sharing belongs
to Dawn; this module does not import Qt's OpenGL context or widget classes.

Windows defaults to Vulkan offscreen rendering with CPU readback into an owned
QImage, painted by an ordinary QWidget. This deliberately pays a GPU completion
wait and full-frame transfer to avoid Vulkan Win32 WSI drivers that resolve WGL
entry points. ``config['qt_presentation']='native'`` (or the
``VISPY_QT_PRESENTATION`` environment variable) explicitly opts into the native
surface fast path, which is outside strict Windows no-OpenGL qualification.
``auto`` selects readback on Windows and native presentation elsewhere.
"""

from __future__ import division

from time import sleep, time
import math
import os
import sys
from packaging.version import Version

from ...util import logger
from ..base import (BaseApplicationBackend, BaseCanvasBackend,
                    BaseTimerBackend)
from ...util import keys
from ... import config
from . import qt_lib

USE_EGL = False  # EGL/GL contexts are not a renderer path in this fork.

# Get platform
IS_LINUX = IS_OSX = IS_WIN = IS_RPI = False
if sys.platform.startswith('linux'):
    if os.uname()[4].startswith('arm'):
        IS_RPI = True
    else:
        IS_LINUX = True
elif sys.platform.startswith('darwin'):
    IS_OSX = True
elif sys.platform.startswith('win'):
    IS_WIN = True

# -------------------------------------------------------------------- init ---


def _check_imports(lib):
    # Make sure no conflicting libraries have been imported.
    libs = ['PyQt4', 'PyQt5', 'PyQt6', 'PySide', 'PySide2', 'PySide6']
    libs.remove(lib)
    for lib2 in libs:
        lib2 += '.QtCore'
        if lib2 in sys.modules:
            raise RuntimeError("Refusing to import %s because %s is already "
                               "imported." % (lib, lib2))


def _get_event_xy(ev):
    # QT6 (and the Python bindings like PyQt6, PySide6) report position differently from previous versions
    if hasattr(ev, 'pos'):
        posx, posy = ev.pos().x(), ev.pos().y()
    else:
        # Compatibility for PySide6 / PyQt6
        posx, posy = ev.position().x(), ev.position().y()

    return posx, posy


# Get what qt lib to try. This tells us wheter this module is imported
# via _pyside or _pyqt4 or _pyqt5
QT5_NEW_API = False
PYSIDE6_API = False
PYQT6_API = False
if qt_lib == 'pyqt5':
    _check_imports('PyQt5')
    from PyQt5 import QtGui, QtCore, QtWidgets, QtTest
    QT5_NEW_API = Version(QtCore.QT_VERSION_STR) >= Version('5.4.0')
elif qt_lib == 'pyqt6':
    _check_imports('PyQt6')
    from PyQt6 import QtGui, QtCore, QtWidgets, QtTest
    PYQT6_API = True
elif qt_lib == 'pyside6':
    _check_imports('PySide6')
    from PySide6 import QtGui, QtCore, QtWidgets, QtTest
    PYSIDE6_API = True
else:
    raise RuntimeError('The Dawn QWidget backend supports PyQt5, PyQt6 and '
                       'PySide6; requested binding: %r' % qt_lib)
QWidget, QApplication = QtWidgets.QWidget, QtWidgets.QApplication

# todo: add support for distinguishing left and right shift/ctrl/alt keys.
# Linux scan codes:  (left, right)
#   Shift  50, 62
#   Ctrl   37, 105
#   Alt    64, 108
qt_keys = QtCore.Qt.Key if qt_lib == 'pyqt6' else QtCore.Qt
KEYMAP = {
    qt_keys.Key_Shift: keys.SHIFT,
    qt_keys.Key_Control: keys.CONTROL,
    qt_keys.Key_Alt: keys.ALT,
    qt_keys.Key_AltGr: keys.ALT,
    qt_keys.Key_Meta: keys.META,

    qt_keys.Key_Left: keys.LEFT,
    qt_keys.Key_Up: keys.UP,
    qt_keys.Key_Right: keys.RIGHT,
    qt_keys.Key_Down: keys.DOWN,
    qt_keys.Key_PageUp: keys.PAGEUP,
    qt_keys.Key_PageDown: keys.PAGEDOWN,

    qt_keys.Key_Insert: keys.INSERT,
    qt_keys.Key_Delete: keys.DELETE,
    qt_keys.Key_Home: keys.HOME,
    qt_keys.Key_End: keys.END,

    qt_keys.Key_Escape: keys.ESCAPE,
    qt_keys.Key_Backspace: keys.BACKSPACE,

    qt_keys.Key_F1: keys.F1,
    qt_keys.Key_F2: keys.F2,
    qt_keys.Key_F3: keys.F3,
    qt_keys.Key_F4: keys.F4,
    qt_keys.Key_F5: keys.F5,
    qt_keys.Key_F6: keys.F6,
    qt_keys.Key_F7: keys.F7,
    qt_keys.Key_F8: keys.F8,
    qt_keys.Key_F9: keys.F9,
    qt_keys.Key_F10: keys.F10,
    qt_keys.Key_F11: keys.F11,
    qt_keys.Key_F12: keys.F12,

    qt_keys.Key_Space: keys.SPACE,
    qt_keys.Key_Enter: keys.ENTER,
    qt_keys.Key_Return: keys.ENTER,
    qt_keys.Key_Tab: keys.TAB,
}
if PYQT6_API or PYSIDE6_API:
    # VisPy buttons 1-5 are Left/Right/Middle/Back/Forward.
    # Qt 5.0+ also exposes ExtraButton1..24 (ExtraButton1/2 alias Back/Forward;
    # ExtraButton3 is TaskButton). They were not present in Qt 4. Map any
    # ExtraButton3..24 that exist on this Qt build to VisPy 6..27 so extra
    # buttons stay distinguishable instead of collapsing to 0.
    # Docs: https://doc.qt.io/qt-5/qt.html#MouseButton-enum
    #       https://doc.qt.io/qt-6/qt.html#MouseButton-enum
    BUTTONMAP = {
        QtCore.Qt.MouseButton.NoButton: 0,
        QtCore.Qt.MouseButton.LeftButton: 1,
        QtCore.Qt.MouseButton.RightButton: 2,
        QtCore.Qt.MouseButton.MiddleButton: 3,
        QtCore.Qt.MouseButton.BackButton: 4,
        QtCore.Qt.MouseButton.ForwardButton: 5,
    }
    for _extra_i in range(3, 25):
        _qt_btn = getattr(QtCore.Qt.MouseButton, f'ExtraButton{_extra_i}', None)
        if _qt_btn is not None:
            BUTTONMAP[_qt_btn] = _extra_i + 3
else:
    # Qt5 (and older) path uses integer button codes as keys. ExtraButton3..24
    # exist from Qt 5.0; Qt 4 only had XButton1/2. Add them only when present.
    BUTTONMAP = {0: 0, 1: 1, 2: 2, 4: 3, 8: 4, 16: 5}
    _mouse_button = getattr(QtCore.Qt, 'MouseButton', QtCore.Qt)
    for _extra_i in range(3, 25):
        _qt_btn = getattr(_mouse_button, f'ExtraButton{_extra_i}', None)
        if _qt_btn is None:
            _qt_btn = getattr(QtCore.Qt, f'ExtraButton{_extra_i}', None)
        if _qt_btn is not None:
            _code = int(getattr(_qt_btn, 'value', _qt_btn))
            BUTTONMAP[_code] = _extra_i + 3


# Properly log Qt messages
def message_handler(*args):

    if qt_lib in ("pyqt4", "pyside"):
        msg_type, msg = args
    elif qt_lib in ("pyqt5", "pyqt6", "pyside2", "pyside6"):  # Is this correct for pyside2?
        msg_type, context, msg = args
    elif qt_lib:
        raise RuntimeError("Invalid value for qt_lib %r." % qt_lib)
    else:
        raise RuntimeError("Module backends._qt ",
                           "should not be imported directly.")

    BLACKLIST = [
        # Ignore spam about tablet input
        'QCocoaView handleTabletEvent: This tablet device is unknown',
        # Not too sure why this warning is emitted when using
        #   Spyder + PyQt5 + Vispy
        #   https://github.com/vispy/vispy/issues/1787
        # In either case, it is really annoying. We should filter it away
        'QSocketNotifier: Multiple socket notifiers for same',
    ]
    for item in BLACKLIST:
        if msg.startswith(item):
            return

    msg = msg.decode() if not isinstance(msg, str) else msg
    logger.warning(msg)


def use_shared_contexts():
    """Enable context sharing for PyQt5 5.4+ API applications.

    This is disabled by default for PyQt5 5.4+ due to occasional segmentation
    faults and other issues when contexts are shared.

    """
    forced_env_var = os.getenv('VISPY_PYQT5_SHARE_CONTEXT', 'false').lower() == 'true'
    return not (QT5_NEW_API or PYSIDE6_API or PYQT6_API) or forced_env_var


try:
    QtCore.qInstallMsgHandler(message_handler)
except AttributeError:
    QtCore.qInstallMessageHandler(message_handler)  # PyQt5, PyQt6


# -------------------------------------------------------------- capability ---

capability = dict(  # things that can be set by the backend
    title=True,
    size=True,
    position=True,
    show=True,
    vsync=True,
    resizable=True,
    decorate=True,
    fullscreen=True,
    context=use_shared_contexts(),
    multi_window=True,
    scroll=True,
    parent=True,
    always_on_top=True,
)


# ------------------------------------------------------- set_configuration ---
def _set_config(c):
    """Retain the requested Dawn configuration without constructing GL formats."""
    return dict(c)


def _select_dawn_presentation(value, platform):
    """Choose an explicit presentation route; never fall back to OpenGL."""
    if value not in ('auto', 'readback', 'native'):
        raise ValueError('Dawn Qt presentation must be auto, readback or native')
    return ('readback' if platform == 'win32' else 'native') if value == 'auto' else value


# ------------------------------------------------------------- application ---

def _raise_dawn_callback_error(app):
    """Raise a callback failure after returning across Qt's C++ boundary."""
    error = getattr(app, '_vispy_dawn_callback_error', None)
    if error is not None:
        app._vispy_dawn_callback_error = None
        raise error


class ApplicationBackend(BaseApplicationBackend):

    def __init__(self):
        BaseApplicationBackend.__init__(self)
        # Dawn owns resource sharing. Do not request Qt GL context sharing.

    def _vispy_get_backend_name(self):
        name = QtCore.__name__.split('.')[0]
        return name

    def _vispy_process_events(self):
        app = self._vispy_get_native_app()
        _raise_dawn_callback_error(app)
        # sendPostedEvents replaces flush which has been removed from Qt6.0+
        # This should be compatible with Qt4.x and Qt5.x
        app.sendPostedEvents()
        app.processEvents()
        _raise_dawn_callback_error(app)
        from vispy import _dawn
        _dawn.process_events()

    def _vispy_run(self):
        app = self._vispy_get_native_app()
        _raise_dawn_callback_error(app)
        if hasattr(app, '_in_event_loop') and app._in_event_loop:
            pass  # Already in event loop
        else:
            # app.exec_() for PyQt <=5 and app.exec() for PyQt >=5
            exec_func = app.exec if hasattr(app, "exec") else app.exec_
            result = exec_func()
            _raise_dawn_callback_error(app)
            return result

    def _vispy_quit(self):
        return self._vispy_get_native_app().quit()

    def _vispy_get_native_app(self):
        # Get native app in save way. Taken from guisupport.py
        app = QApplication.instance()
        if app is None:
            app = QApplication([''])
        # Store so it won't be deleted, but not on a vispy object,
        # or an application may produce error when closed.
        QtGui._qApp = app
        # Return
        return app

    def _vispy_sleep(self, duration_sec):
        QtTest.QTest.qWait(duration_sec * 1000)  # in ms


# ------------------------------------------------------------------ canvas ---

def _get_qpoint_pos(pos):
    """Return the coordinates of a QPointF object."""
    return pos.x(), pos.y()


def _buttonmap_to_list(buttons) -> list[int]:
    """Map Qt mouse button flags to VisPy button ids.

    Module-level (no ``self``) so tests can call it without a backend
    instance. Preserves BUTTONMAP order: standard 1-5, then
    ExtraButton3..24 as 6-27 when present on this Qt build.
    """
    if buttons == QtCore.Qt.MouseButton.NoButton:
        return []

    mouse_buttons = []
    if PYQT6_API or PYSIDE6_API:
        for qt_button, vispy_button in BUTTONMAP.items():
            if vispy_button and qt_button in buttons:
                mouse_buttons.append(vispy_button)
    else:
        for qt_button, vispy_button in BUTTONMAP.items():
            if vispy_button and (buttons & qt_button) != QtCore.Qt.MouseButton.NoButton:
                mouse_buttons.append(vispy_button)

    return mouse_buttons


class QtBaseCanvasBackend(BaseCanvasBackend):
    """Base functionality of Qt backend. No OpenGL Stuff."""

    def __init__(self, vispy_canvas, **kwargs):
        BaseCanvasBackend.__init__(self, vispy_canvas)
        # Maybe to ensure that exactly all arguments are passed?
        p = self._process_backend_kwargs(kwargs)
        self._initialized = False

        # Init in desktop GL or EGL way
        self._init_specific(p, kwargs)
        assert self._initialized

        self.setMouseTracking(True)
        self._vispy_set_title(p.title)
        self._vispy_set_size(*p.size)
        if p.fullscreen is not False:
            if p.fullscreen is not True:
                logger.warning('Cannot specify monitor number for Qt '
                               'fullscreen, using default')
            self._fullscreen = True
        else:
            self._fullscreen = False

        # must set physical size before setting visible or fullscreen
        # operations may make the size invalid
        if hasattr(self, 'devicePixelRatioF'):
            # handle high DPI displays in PyQt5
            ratio = self.devicePixelRatioF()
        else:
            ratio = 1
        self._physical_size = (p.size[0] * ratio, p.size[1] * ratio)

        if not p.resizable:
            self.setFixedSize(self.size())
        if p.position is not None:
            self._vispy_set_position(*p.position)
        if p.show:
            self._vispy_set_visible(True)

        # Qt supports OS double-click events, so we set this here to
        # avoid double events
        self._double_click_supported = True

        try:
            # see screen_changed docstring for more details
            self.window().windowHandle().screenChanged.connect(self.screen_changed)
        except AttributeError:
            # either not PyQt5 backend or no parent window available
            pass

        # QNativeGestureEvent does not keep track of last or total
        # values like QGestureEvent does
        self._native_gesture_scale_values = []
        self._native_gesture_rotation_values = []

    def screen_changed(self, new_screen):
        """Window moved from one display to another, resize canvas.

        If display resolutions are the same this is essentially a no-op except for the redraw.
        If the display resolutions differ (HiDPI versus regular displays) the canvas needs to
        be redrawn to reset the physical size based on the current `devicePixelRatioF()` and
        redrawn with that new size.

        """
        self.resizeGL(*self._vispy_get_size())

    def _vispy_warmup(self):
        etime = time() + 0.25
        while time() < etime:
            sleep(0.01)
            self._vispy_canvas.set_current()
            self._vispy_canvas.app.process_events()

    def _vispy_set_title(self, title):
        # Set the window title. Has no effect for widgets
        if self._vispy_canvas is None:
            return
        self.setWindowTitle(title)

    def _vispy_set_size(self, w, h):
        # Set size of the widget or window
        self.resize(w, h)

    def _vispy_set_physical_size(self, w, h):
        self._physical_size = (w, h)

    def _vispy_get_physical_size(self):
        if self._vispy_canvas is None:
            return
        return self._physical_size

    def _vispy_set_position(self, x, y):
        # Set location of the widget or window. May have no effect for widgets
        self.move(x, y)

    def _vispy_set_visible(self, visible):
        # Show or hide the window or widget
        if visible:
            if self._fullscreen:
                self.showFullScreen()
            else:
                self.showNormal()
        else:
            self.hide()

    def _vispy_set_fullscreen(self, fullscreen):
        self._fullscreen = bool(fullscreen)
        self._vispy_set_visible(True)

    def _vispy_get_fullscreen(self):
        return self._fullscreen

    def _vispy_update(self):
        if self._vispy_canvas is None:
            return
        # Invoke a redraw
        self.update()

    def _vispy_get_position(self):
        g = self.geometry()
        return g.x(), g.y()

    def _vispy_get_size(self):
        g = self.geometry()
        return g.width(), g.height()

    def sizeHint(self):
        return self.size()

    def mousePressEvent(self, ev):
        if self._vispy_canvas is None:
            return

        vispy_event = self._vispy_mouse_press(
            native=ev,
            pos=_get_event_xy(ev),
            button=BUTTONMAP.get(ev.button(), 0),
            buttons=_buttonmap_to_list(ev.buttons()),
            modifiers=self._modifiers(ev),
        )
        # If vispy did not handle the event, clear the accept parameter of the qt event
        if not vispy_event.handled:
            ev.ignore()

    def mouseReleaseEvent(self, ev):
        if self._vispy_canvas is None:
            return
        vispy_event = self._vispy_mouse_release(
            native=ev,
            pos=_get_event_xy(ev),
            button=BUTTONMAP.get(ev.button(), 0),
            buttons=_buttonmap_to_list(ev.buttons()),
            modifiers=self._modifiers(ev),
        )
        # If vispy did not handle the event, clear the accept parameter of the qt event
        if not vispy_event.handled:
            ev.ignore()

    def mouseDoubleClickEvent(self, ev):
        if self._vispy_canvas is None:
            return
        vispy_event = self._vispy_mouse_double_click(
            native=ev,
            pos=_get_event_xy(ev),
            button=BUTTONMAP.get(ev.button(), 0),
            buttons=_buttonmap_to_list(ev.buttons()),
            modifiers=self._modifiers(ev),
        )
        # If vispy did not handle the event, clear the accept parameter of the qt event
        if not vispy_event.handled:
            ev.ignore()

    def mouseMoveEvent(self, ev):
        if self._vispy_canvas is None:
            return
        # NB ignores events, returns None for events in quick succession
        vispy_event = self._vispy_mouse_move(
            native=ev,
            pos=_get_event_xy(ev),
            buttons=_buttonmap_to_list(ev.buttons()),
            modifiers=self._modifiers(ev),
        )
        # If vispy did not handle the event, clear the accept parameter of the qt event
        # Note that the handler can return None, this is equivalent to not handling the event
        if vispy_event is None or not vispy_event.handled:
            # Theoretically, a parent widget might want to listen to all of
            # the mouse move events, including those that VisPy ignores
            ev.ignore()

    def wheelEvent(self, ev):
        if self._vispy_canvas is None:
            return
        # Get scrolling
        deltax, deltay = 0.0, 0.0
        if hasattr(ev, 'orientation'):
            if ev.orientation == QtCore.Qt.Horizontal:
                deltax = ev.delta() / 120.0
            else:
                deltay = ev.delta() / 120.0
        else:
            # PyQt5 / PyQt6
            delta = ev.angleDelta()
            deltax, deltay = delta.x() / 120.0, delta.y() / 120.0
        # Emit event
        vispy_event = self._vispy_canvas.events.mouse_wheel(
            native=ev,
            delta=(deltax, deltay),
            pos=_get_event_xy(ev),
            buttons=_buttonmap_to_list(ev.buttons()),
            modifiers=self._modifiers(ev),
        )
        # If vispy did not handle the event, clear the accept parameter of the qt event
        if not vispy_event.handled:
            ev.ignore()

    def keyPressEvent(self, ev):
        self._keyEvent(self._vispy_canvas.events.key_press, ev)

    def keyReleaseEvent(self, ev):
        self._keyEvent(self._vispy_canvas.events.key_release, ev)

    def _handle_native_gesture_event(self, ev):
        if self._vispy_canvas is None:
            return
        t = ev.gestureType()
        # this is a workaround for what looks like a Qt bug where
        # QNativeGestureEvent gives the wrong local position.
        # See: https://bugreports.qt.io/browse/QTBUG-59595
        try:
            pos = self.mapFromGlobal(ev.globalPosition().toPoint())
        except AttributeError:
            # globalPos is deprecated in Qt6
            pos = self.mapFromGlobal(ev.globalPos())
        pos = pos.x(), pos.y()

        vispy_event = None
        if t == QtCore.Qt.NativeGestureType.BeginNativeGesture:
            vispy_event = self._vispy_canvas.events.touch(
                type='gesture_begin',
                pos=_get_event_xy(ev),
                modifiers=self._modifiers(ev),
            )
        elif t == QtCore.Qt.NativeGestureType.EndNativeGesture:
            self._native_touch_total_rotation = []
            self._native_touch_total_scale = []
            vispy_event = self._vispy_canvas.events.touch(
                type='gesture_end',
                pos=_get_event_xy(ev),
                modifiers=self._modifiers(ev),
            )
        elif t == QtCore.Qt.NativeGestureType.RotateNativeGesture:
            angle = ev.value()
            last_angle = (
                self._native_gesture_rotation_values[-1]
                if self._native_gesture_rotation_values
                else None
            )
            self._native_gesture_rotation_values.append(angle)
            total_rotation_angle = math.fsum(self._native_gesture_rotation_values)
            vispy_event = self._vispy_canvas.events.touch(
                type="gesture_rotate",
                pos=pos,
                rotation=angle,
                last_rotation=last_angle,
                total_rotation_angle=total_rotation_angle,
                modifiers=self._modifiers(ev),
            )
        elif t == QtCore.Qt.NativeGestureType.ZoomNativeGesture:
            scale = ev.value()
            last_scale = (
                self._native_gesture_scale_values[-1]
                if self._native_gesture_scale_values
                else None
            )
            self._native_gesture_scale_values.append(scale)
            total_scale_factor = math.fsum(self._native_gesture_scale_values)
            vispy_event = self._vispy_canvas.events.touch(
                type="gesture_zoom",
                pos=pos,
                last_scale=last_scale,
                scale=scale,
                total_scale_factor=total_scale_factor,
                modifiers=self._modifiers(ev),
            )
        # QtCore.Qt.NativeGestureType.PanNativeGesture
        # Qt6 docs seem to imply this is only supported on Wayland but I have
        # not been able to test it.
        # Two finger pan events are anyway converted to scroll/wheel events.
        # On macOS, more fingers are usually swallowed by the OS (by spaces,
        # mission control, etc.).

        # If vispy did not handle the event, clear the accept parameter of the qt event
        # Note that some handlers return None, this is equivalent to not handling the event
        if vispy_event is None or not vispy_event.handled:
            ev.ignore()

    def event(self, ev):
        out = super(QtBaseCanvasBackend, self).event(ev)

        # QNativeGestureEvent is Qt 5+
        if (
            (QT5_NEW_API or PYSIDE6_API or PYQT6_API)
            and isinstance(ev, QtGui.QNativeGestureEvent)
        ):
            self._handle_native_gesture_event(ev)

        return out

    def _keyEvent(self, func, ev):
        # evaluates the keycode of qt, and transform to vispy key.
        key = int(ev.key())
        if key in KEYMAP:
            key = KEYMAP[key]
        elif 32 <= key <= 127:
            key = keys.Key(chr(key))
        else:
            key = None
        mod = self._modifiers(ev)
        vispy_event = func(native=ev, key=key, text=str(ev.text()), modifiers=mod)
        # If vispy did not handle the event, clear the accept parameter of the qt event
        if not vispy_event.handled:
            ev.ignore()

    def _modifiers(self, event):
        # Convert the QT modifier state into a tuple of active modifier keys.
        mod = ()
        qtmod = event.modifiers()
        qt_keyboard_modifiers = QtCore.Qt.KeyboardModifier if PYQT6_API else QtCore.Qt
        for q, v in ([qt_keyboard_modifiers.ShiftModifier, keys.SHIFT],
                     [qt_keyboard_modifiers.ControlModifier, keys.CONTROL],
                     [qt_keyboard_modifiers.AltModifier, keys.ALT],
                     [qt_keyboard_modifiers.MetaModifier, keys.META]):
            if qtmod & q:
                mod += (v,)
        return mod


class CanvasBackendEgl:
    """Compatibility name that refuses the removed EGL context path."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError('EGL canvases are unavailable in the Dawn renderer; '
                           'use a supported Qt backend or dawn_headless.')


_QtSignal = getattr(QtCore, "pyqtSignal", None) or QtCore.Signal


class CanvasBackendDesktop(QtBaseCanvasBackend, QWidget):
    """Parentable QWidget. This is not a QOpenGLWidget."""

    resized = _QtSignal()

    def _init_specific(self, p, kwargs):
        p.context.shared.add_ref('qt', self)
        qt_window_types = QtCore.Qt.WindowType if PYQT6_API else QtCore.Qt
        if p.always_on_top or not p.decorate:
            hint = 0
            hint |= 0 if p.decorate else qt_window_types.FramelessWindowHint
            hint |= qt_window_types.WindowStaysOnTopHint if p.always_on_top else 0
        else:
            hint = qt_window_types.Widget

        self._dawn_presentation = _select_dawn_presentation(
            os.environ.get('VISPY_QT_PRESENTATION', config['qt_presentation']), sys.platform)
        QWidget.__init__(self, p.parent, hint)
        self._secondary_context = None
        self._surface = None
        self.setAutoFillBackground(False)
        native_presentation = self._dawn_presentation == 'native'
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow if PYQT6_API else QtCore.Qt.WA_NativeWindow, native_presentation)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_PaintOnScreen if PYQT6_API else QtCore.Qt.WA_PaintOnScreen, native_presentation)
        self.setMouseTracking(True)
        qt_focus_policies = QtCore.Qt.FocusPolicy if PYQT6_API else QtCore.Qt
        self.setFocusPolicy(qt_focus_policies.WheelFocus)
        from vispy import _dawn
        samples = int(p.context.config.get('samples', 0) or 0)
        width, height = int(p.size[0]), int(p.size[1])
        self._dawn_canvas_id = int(_dawn.register_canvas(width, height, samples, bool(p.vsync)))
        self.destroyed.connect(
            lambda _obj=None, canvas_id=self._dawn_canvas_id: _dawn.destroy_canvas(canvas_id)
        )
        from ...gloo.dawn_parser import install_gl_queries
        install_gl_queries()
        self._initialized = True
        self._dawn_closed = False
        self._dawn_paint_deferred = False
        self._dawn_paint_token = None
        self._dawn_callback_failed = False
        self._dawn_ratio_override = None
        self._dawn_last_image = None

    def _ratio(self):
        if self._dawn_ratio_override is not None:
            return float(self._dawn_ratio_override)
        if hasattr(self, 'devicePixelRatioF'):
            return float(self.devicePixelRatioF())
        return 1.0

    def _dawn_surface(self):
        if getattr(self, '_dawn_closed', False):
            return
        from vispy import _dawn
        canvas_id = int(self._dawn_canvas_id)
        if self._dawn_presentation == 'readback':
            # In particular, never enter Vulkan Win32 WSI for this profile.
            _dawn.clear_surface(canvas_id)
            _dawn.update_surface_scale(canvas_id, self._ratio())
            return
        hwnd = int(self.effectiveWinId() or 0)
        if not hwnd:
            _dawn.clear_surface(canvas_id)
            return
        elif sys.platform == 'win32':
            _dawn.set_surface_win32(canvas_id, hwnd, 0)
        elif sys.platform == 'darwin':
            _dawn.set_surface_metal_view(canvas_id, hwnd)
        elif sys.platform.startswith('linux'):
            if QtGui.QGuiApplication.platformName().lower() != 'xcb':
                raise RuntimeError('Dawn Qt surfaces require X11/xcb on Linux')
            _dawn.set_surface_x11(canvas_id, 0, hwnd, True)
        else:
            raise RuntimeError('unsupported Dawn native Qt platform %s' % sys.platform)
        _dawn.update_surface_scale(canvas_id, self._ratio())

    def _vispy_close(self):
        if getattr(self, '_dawn_closed', False):
            return
        self._dawn_closed = True
        self._dawn_paint_deferred = False
        if getattr(self, '_dawn_poll_timer', None) is not None:
            self._dawn_poll_timer.stop()
        from vispy import _dawn
        _dawn.destroy_canvas(int(self._dawn_canvas_id))
        self.close()
        if self._vispy_canvas is not None:
            self._vispy_canvas.app.process_events()

    def _vispy_set_current(self):
        return

    def _vispy_swap_buffers(self):
        if self._vispy_canvas is None or self._dawn_closed:
            return
        if getattr(self, '_dawn_paint_token', None) is not None:
            # Qt owns the whole paint, including its alpha-clear tail. Keep
            # this swap callback, but present its final contents only once.
            return
        from vispy import _dawn
        _dawn.present(int(self._dawn_canvas_id))
        self._start_dawn_pump()

    def _start_dawn_pump(self):
        if getattr(self, '_dawn_poll_timer', None) is None:
            self._dawn_poll_timer = QtCore.QTimer(self)
            self._dawn_poll_timer.setInterval(1)
            self._dawn_poll_timer.timeout.connect(self._poll_dawn)
        self._dawn_poll_timer.start()

    def _poll_dawn(self):
        if self._dawn_closed or self._dawn_callback_failed:
            self._dawn_poll_timer.stop()
            return
        from vispy import _dawn
        try:
            pending = _dawn.process_events()
            if (getattr(self, '_dawn_paint_deferred', False) and
                    _dawn.frame_ready(int(self._dawn_canvas_id))):
                self._dawn_paint_deferred = False
                self.update()
            if not pending:
                self._dawn_poll_timer.stop()
        except Exception as error:
            self._record_dawn_callback_error(error, 'completion timer')

    def _record_dawn_callback_error(self, error, callback):
        # Exceptions escaping PyQt virtual methods can abort the process.
        # Keep the first application error, stop this canvas and raise from
        # process_events()/run() after leaving Qt. Native host loops receive
        # a diagnostic and a nonzero exit request as well.
        self._dawn_callback_failed = True
        self._dawn_paint_deferred = False
        timer = getattr(self, '_dawn_poll_timer', None)
        if timer is not None:
            timer.stop()
        application = QApplication.instance()
        if getattr(application, '_vispy_dawn_callback_error', None) is None:
            application._vispy_dawn_callback_error = error
        logger.error('Dawn Qt %s failed on canvas %s: %s', callback,
                     self._dawn_canvas_id, error,
                     exc_info=(type(error), error, error.__traceback__))
        application.exit(1)

    def _vispy_get_fb_bind_location(self):
        return 0

    def event(self, ev):
        kind = ev.type()
        winid_change = getattr(getattr(QtCore.QEvent, 'Type', QtCore.QEvent), 'WinIdChange', None)
        if winid_change is None:
            winid_change = QtCore.QEvent.WinIdChange
        if kind == winid_change and getattr(self, '_initialized', False):
            self._dawn_surface()
        return QtBaseCanvasBackend.event(self, ev)

    def showEvent(self, event):
        QWidget.showEvent(self, event)
        if self._vispy_canvas is not None and not getattr(self, '_dawn_shown', False):
            self._dawn_shown = True
            self._dawn_surface()
            self._vispy_canvas.events.initialize()
            self.resizeGL(self.width(), self.height())

    def resizeEvent(self, event):
        self.resizeGL(event.size().width(), event.size().height())
        self.resized.emit()
        return QWidget.resizeEvent(self, event)

    def resizeGL(self, w, h):
        if self._vispy_canvas is None or getattr(self, '_dawn_closed', False):
            return
        ratio = self._ratio()
        physical_w = int(round(w * ratio))
        physical_h = int(round(h * ratio))
        self._vispy_set_physical_size(physical_w, physical_h)
        from vispy import _dawn
        _dawn.update_surface_scale(int(self._dawn_canvas_id), ratio)
        if self.isMinimized() or physical_w <= 0 or physical_h <= 0:
            _dawn.configure_canvas(int(self._dawn_canvas_id), 0, 0, 0)
        else:
            _dawn.configure_canvas(int(self._dawn_canvas_id), physical_w, physical_h,
                                   int(self._vispy_canvas.context.config.get('samples', 0) or 0))
        self._vispy_canvas.events.resize(size=(self.width(), self.height()),
                                         physical_size=(physical_w, physical_h))

    def paintEvent(self, event):
        if (self._vispy_canvas is None or getattr(self, '_dawn_closed', False) or
                self._dawn_callback_failed):
            return
        if self.isMinimized() or self.width() <= 0 or self.height() <= 0:
            return
        from vispy import _dawn
        paint_token = None
        paint_api = None
        previous_paint_token = getattr(self, '_dawn_paint_token', None)
        try:
            if not _dawn.frame_ready(int(self._dawn_canvas_id)):
                self._dawn_paint_deferred = True
                self._start_dawn_pump()
                if (getattr(self, '_dawn_presentation', 'native') == 'readback' and
                        self._dawn_last_image is not None):
                    self._paint_dawn_image(self._dawn_last_image)
                return
            self._dawn_paint_deferred = False
            paint_api = tuple(getattr(_dawn, name, None) for name in
                              ('begin_canvas_paint', 'end_canvas_paint', 'abort_canvas_paint'))
            if any(function is not None for function in paint_api):
                if not all(callable(function) for function in paint_api):
                    raise RuntimeError('Dawn native Qt paint scope API is incomplete')
                paint_token = paint_api[0](int(self._dawn_canvas_id))
                if type(paint_token) is not int or paint_token <= 0:
                    raise RuntimeError('Dawn native Qt paint scope returned an invalid token')
                self._dawn_paint_token = paint_token
            self._draw_dawn_scene()
            _dawn.present(int(self._dawn_canvas_id))
            self._start_dawn_pump()
            if getattr(self, '_dawn_presentation', 'native') == 'readback':
                # Readback drains pending/deferred GPU work while the native
                # Qt paint token still owns its submission and completion.
                image = self._read_dawn_framebuffer()
                self._paint_dawn_image(image)
                self._dawn_last_image = image
            if paint_token is not None:
                paint_api[1](int(self._dawn_canvas_id), paint_token)
                paint_token = None
        except Exception as error:
            if type(paint_token) is int and paint_token > 0:
                try:
                    paint_api[2](int(self._dawn_canvas_id), paint_token, str(error))
                except Exception:
                    # Preserve the application error if cleanup also fails.
                    logger.error('Dawn Qt paint scope abort failed on canvas %s',
                                 self._dawn_canvas_id, exc_info=True)
            self._record_dawn_callback_error(error, 'paintEvent')
        finally:
            self._dawn_paint_token = previous_paint_token

    def paintEngine(self):
        if getattr(self, '_dawn_presentation', 'native') == 'readback':
            return QWidget.paintEngine(self)
        return None

    def _paint_dawn_image(self, image):
        """Present through Qt's raster QWidget path, inside a paint event."""
        painter = QtGui.QPainter(self)
        try:
            if not painter.isActive():
                raise RuntimeError('Dawn Qt readback presentation could not begin QWidget painting')
            modes = getattr(QtGui.QPainter, 'CompositionMode', QtGui.QPainter)
            painter.setCompositionMode(modes.CompositionMode_Source)
            painter.drawImage(self.rect(), image)
        finally:
            painter.end()

    def context(self):
        """Return the canvas context when its rendering device is available."""
        from vispy import _dawn
        if self._vispy_canvas is None or self._dawn_closed or not _dawn.device_info()["ok"]:
            return None
        return self._vispy_canvas.context

    def _draw_dawn_scene(self):
        self._vispy_canvas.set_current()
        self._vispy_canvas.events.draw(region=None)
        # Preserve the pinned QOpenGLWidget paintGL operation: widget frames
        # clear only alpha to the current clear color after scene drawing.
        # Direct gloo readback and offscreen rendering keep their own alpha.
        if QT5_NEW_API or PYSIDE6_API or PYQT6_API:
            context = self._vispy_canvas.context
            context.set_color_mask(False, False, False, True)
            context.clear(color=True, depth=False, stencil=False)
            context.set_color_mask(True, True, True, True)
            context.flush()

    def grabFramebuffer(self):
        """Capture the current scene. Child overlays are not included."""
        # QOpenGLWidget::grabFramebuffer renders before reading its target.
        self._draw_dawn_scene()
        return self._read_dawn_framebuffer()

    def _read_dawn_framebuffer(self):
        """Read an independently owned QImage without triggering another draw."""
        from ...gloo import read_pixels
        image = read_pixels(alpha=True)
        height, width, _channels = image.shape
        data = bytes(image.tobytes())
        formats = QtGui.QImage.Format if PYQT6_API else QtGui.QImage
        alpha = self._vispy_canvas.context.config.get('alpha_size', 0) > 0
        # Match Qt's framebuffer image interpretation while keeping the
        # renderer's byte-ordered RGBA readback and independent ownership.
        fmt = formats.Format_RGBA8888_Premultiplied if alpha else formats.Format_RGBX8888
        qimage = QtGui.QImage(data, width, height, width * 4, fmt)
        qimage.setDevicePixelRatio(self._ratio())
        return qimage.copy()


# Select CanvasBackend
CanvasBackend = CanvasBackendDesktop


# ------------------------------------------------------------------- timer ---

class TimerBackend(BaseTimerBackend, QtCore.QTimer):

    def __init__(self, vispy_timer):
        # Make sure there is an app
        app = ApplicationBackend()
        app._vispy_get_native_app()
        # Init
        BaseTimerBackend.__init__(self, vispy_timer)
        QtCore.QTimer.__init__(self)
        self.timeout.connect(self._vispy_timeout)

    def _vispy_start(self, interval):
        self.start(int(interval * 1000))

    def _vispy_stop(self):
        self.stop()

    def _vispy_timeout(self):
        self._vispy_timer._timeout()
