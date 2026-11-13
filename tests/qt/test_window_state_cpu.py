"""Qt state transitions must configure drawable size without needing a resize."""

from types import SimpleNamespace

import pytest

import vispy
from vispy.app.backends import _pyqt6


QT = _pyqt6._qt


@pytest.fixture
def state_backend(monkeypatch):
    calls, errors = [], []
    state = {'minimized': False, 'width': 40, 'height': 30}
    native = SimpleNamespace(
        update_surface_scale=lambda *args: calls.append(('scale', *args)),
        configure_canvas=lambda *args: calls.append(('configure', *args)))
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    monkeypatch.setattr(QT.QtBaseCanvasBackend, 'event', lambda self, ev: 'qt-result')
    backend = SimpleNamespace(
        _initialized=True, _dawn_shown=True, _dawn_closed=False, _dawn_callback_failed=False,
        _dawn_canvas_id=7, _ratio=lambda: 1.5,
        _vispy_canvas=SimpleNamespace(
            context=SimpleNamespace(config={'samples': 4}),
            events=SimpleNamespace(resize=lambda **kw: calls.append(('resize', kw)))),
        isMinimized=lambda: state['minimized'], width=lambda: state['width'],
        height=lambda: state['height'],
        _vispy_set_physical_size=lambda *size: calls.append(('physical', *size)),
        update=lambda: calls.append(('update',)),
        _record_dawn_callback_error=lambda error, callback: errors.append((error, callback)))
    backend.resizeGL = lambda w, h: QT.CanvasBackendDesktop.resizeGL(backend, w, h)
    backend._configure_dawn_drawable = lambda w, h: QT.CanvasBackendDesktop._configure_dawn_drawable(backend, w, h)
    return backend, native, state, calls, errors


def change(backend):
    event = SimpleNamespace(type=lambda: QT.QtCore.QEvent.Type.WindowStateChange)
    return QT.CanvasBackendDesktop.event(backend, event)


def test_minimize_and_restore_same_size_reconfigures_without_a_resize_event(state_backend):
    backend, _, state, calls, errors = state_backend
    state['minimized'] = True
    assert change(backend) == 'qt-result'
    assert ('configure', 7, 0, 0, 0) in calls
    assert ('update',) not in calls
    calls.clear()
    state['minimized'] = False
    assert change(backend) == 'qt-result'
    assert ('configure', 7, 60, 45, 4) in calls
    assert calls[-1] == ('update',)
    assert not errors


@pytest.mark.parametrize('width,height', [(0, 30), (40, 0), (0, 0)])
def test_zero_drawable_state_change_stays_suspended(state_backend, width, height):
    backend, _, state, calls, _ = state_backend
    state.update(width=width, height=height)
    change(backend)
    assert ('configure', 7, 0, 0, 0) in calls
    assert ('update',) not in calls


def test_state_only_changes_do_not_emit_user_resize_callbacks(state_backend):
    backend, _, state, calls, errors = state_backend
    for minimized in (True, False):
        state['minimized'] = minimized
        change(backend)
    # Maximize/fullscreen can deliver a state change before the actual size.
    change(backend)
    assert not [c for c in calls if c[0] == 'resize']
    state.update(width=80, height=60)
    backend.resizeGL(80, 60)
    assert [c for c in calls if c[0] == 'resize'] == [
        ('resize', dict(size=(80, 60), physical_size=(120, 90)))]
    assert not errors


@pytest.mark.parametrize('attribute,value', [('_initialized', False), ('_dawn_closed', True),
                                           ('_dawn_callback_failed', True), ('_vispy_canvas', None),
                                           ('_dawn_shown', False)])
def test_state_events_before_initialization_or_after_shutdown_do_not_touch_native(
        state_backend, attribute, value):
    backend, _, _, calls, errors = state_backend
    setattr(backend, attribute, value)
    assert change(backend) == 'qt-result'
    assert calls == [] and errors == []


def test_configuration_failure_is_contained_at_qt_event_boundary(state_backend):
    backend, native, _, calls, errors = state_backend
    original = RuntimeError('state configuration failed')

    def fail(*args):
        raise original

    native.configure_canvas = fail
    assert change(backend) == 'qt-result'
    assert errors == [(original, 'window state change')]
    assert ('update',) not in calls


def test_unrelated_event_does_not_reconfigure(state_backend):
    backend, _, _, calls, errors = state_backend
    event = SimpleNamespace(type=lambda: QT.QtCore.QEvent.Type.PaletteChange)
    assert QT.CanvasBackendDesktop.event(backend, event) == 'qt-result'
    assert calls == [] and errors == []


@pytest.mark.parametrize('size,minimized', [((40, 30), True), ((0, 30), False),
                                           ((40, 0), False)])
def test_suspended_drawable_never_enters_native_paint(state_backend, size, minimized):
    backend, _, state, calls, errors = state_backend
    state.update(width=size[0], height=size[1], minimized=minimized)
    # The native double deliberately has no frame_ready/begin/present: any
    # attempt to submit a suspended canvas would fail this test.
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert calls == [] and errors == []


def test_real_qt_minimize_restore_delivers_state_without_size_change(monkeypatch):
    calls, errors = [], []
    native = SimpleNamespace(
        update_surface_scale=lambda *args: None,
        configure_canvas=lambda *args: calls.append(args))
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    application = QT.QApplication.instance() or QT.QApplication(
        ['vispy-state-test', '-platform', 'offscreen'])

    class Widget(QT.CanvasBackendDesktop):
        """Real Qt event dispatch, production event/resizeGL, no GPU canvas."""

        def __init__(self):
            self._initialized = False
            self._vispy_canvas = None
            QT.QWidget.__init__(self)
            self._dawn_closed = self._dawn_callback_failed = False
            self._dawn_canvas_id = 7
            self._dawn_ratio_override = 1.5
            self._vispy_canvas = SimpleNamespace(
                context=SimpleNamespace(config={'samples': 4}),
                events=SimpleNamespace(resize=lambda **kw: None))
            self.resize_count = 0
            self._initialized = True

        def _dawn_surface(self):
            pass  # This packet tests state dispatch, not native WSI.

        def showEvent(self, ev):
            self._dawn_shown = True
            QT.QWidget.showEvent(self, ev)

        def resizeEvent(self, ev):
            self.resize_count += 1
            QT.QWidget.resizeEvent(self, ev)

        def paintEvent(self, ev):
            pass

        def _record_dawn_callback_error(self, error, callback):
            errors.append((error, callback))

    widget = Widget()
    try:
        widget.resize(40, 30)
        widget.show()
        application.processEvents()
        before = widget.resize_count
        calls.clear()
        widget.showMinimized()
        application.processEvents()
        assert widget.isMinimized() and (7, 0, 0, 0) in calls
        calls.clear()
        widget.showNormal()
        application.processEvents()
        assert not widget.isMinimized() and (7, 60, 45, 4) in calls
        assert widget.resize_count == before
        assert errors == []
    finally:
        widget._dawn_closed = True
        widget._vispy_canvas = None
        widget.close()
        widget.deleteLater()
        QT.QtCore.QCoreApplication.sendPostedEvents(
            None, QT.QtCore.QEvent.Type.DeferredDelete)


def test_first_maximized_show_initializes_before_any_resize(monkeypatch):
    calls, errors = [], []
    user_sizes, actual_resizes = [], []
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(
        update_surface_scale=lambda *args: None,
        configure_canvas=lambda *args: calls.append('configure')), raising=False)
    application = QT.QApplication.instance() or QT.QApplication(
        ['vispy-first-show-test', '-platform', 'offscreen'])

    class Widget(QT.CanvasBackendDesktop):
        def __init__(self):
            self._initialized = False
            self._vispy_canvas = None
            QT.QWidget.__init__(self)
            self._dawn_closed = self._dawn_callback_failed = False
            self._dawn_canvas_id = 7
            self._dawn_ratio_override = 1.
            self._vispy_canvas = SimpleNamespace(
                context=SimpleNamespace(config={'samples': 0}),
                events=SimpleNamespace(initialize=lambda: calls.append('initialize'),
                                       resize=lambda **kw: (calls.append('resize'), user_sizes.append(kw['size']))))
            self._initialized = True

        def resizeEvent(self, event):
            if getattr(self, '_dawn_shown', False):
                actual_resizes.append((event.size().width(), event.size().height()))
            return QT.CanvasBackendDesktop.resizeEvent(self, event)

        def _dawn_surface(self):
            calls.append('surface')

        def paintEvent(self, ev):
            pass

        def _record_dawn_callback_error(self, error, callback):
            errors.append((error, callback))

    widget = Widget()
    try:
        widget.resize(40, 30)
        widget.showMaximized()
        application.processEvents()
        # WinIdChange can notify the surface more than once before show.
        # User initialization must still precede every configure/resize.
        assert calls.count('initialize') == 1
        assert calls.index('initialize') < calls.index('configure')
        assert calls.index('initialize') < calls.index('resize')
        assert errors == []
        calls.clear()
        user_sizes.clear()
        actual_resizes.clear()
        widget.showNormal()
        application.processEvents()
        widget.showMaximized()
        application.processEvents()
        assert user_sizes == actual_resizes
    finally:
        widget._dawn_closed = True
        widget._vispy_canvas = None
        widget.close()
        widget.deleteLater()
        application.sendPostedEvents(None, QT.QtCore.QEvent.Type.DeferredDelete)
