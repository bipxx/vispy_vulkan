"""Native QWidget close must enter the actual Canvas.close ownership path."""

from types import SimpleNamespace

import pytest

import vispy
from vispy.app import Canvas
from vispy.app.backends import _pyqt6


QT = _pyqt6._qt


@pytest.mark.parametrize('legacy_opt_in', [None, 'false', 'true'])
def test_dawn_resource_sharing_does_not_require_legacy_gl_opt_in(monkeypatch, legacy_opt_in):
    if legacy_opt_in is None:
        monkeypatch.delenv('VISPY_PYQT5_SHARE_CONTEXT', raising=False)
    else:
        monkeypatch.setenv('VISPY_PYQT5_SHARE_CONTEXT', legacy_opt_in)
    assert QT.use_shared_contexts() is True
    assert QT.capability['context'] is True


@pytest.fixture
def closing_widget(monkeypatch):
    application = QT.QApplication.instance() or QT.QApplication(
        ['vispy-close-test', '-platform', 'offscreen'])
    calls, errors = [], []
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(
        destroy_canvas=lambda canvas_id: calls.append(('destroy', canvas_id))), raising=False)

    class Widget(QT.CanvasBackendDesktop):
        def __init__(self):
            self._initialized = False
            self._vispy_canvas = None
            QT.QWidget.__init__(self)
            self._dawn_closed = False
            self._dawn_canvas_id = 7

        def _record_dawn_callback_error(self, error, callback):
            errors.append((error, callback))

    widget = Widget()
    canvas = Canvas.__new__(Canvas)
    canvas._backend = widget
    canvas._closed = False
    canvas._app = SimpleNamespace(process_events=lambda: None, backend_name='PyQt6 CPU double')
    canvas.events = SimpleNamespace(close=lambda: calls.append(('close-event',)))
    widget._vispy_canvas = canvas
    try:
        yield widget, canvas, calls, errors
    finally:
        widget._dawn_closed = True
        widget._vispy_canvas = None
        widget.close()
        widget.deleteLater()
        application.sendPostedEvents(None, QT.QtCore.QEvent.Type.DeferredDelete)


def test_window_close_emits_canvas_event_and_releases_native_canvas_once(closing_widget):
    widget, canvas, calls, errors = closing_widget
    assert widget.close()
    assert canvas._closed and widget._dawn_closed
    assert calls == [('close-event',), ('destroy', 7)]
    canvas.close()
    QT.QtCore.QCoreApplication.sendEvent(widget, QT.QtGui.QCloseEvent())
    assert calls == [('close-event',), ('destroy', 7)] and errors == []


def test_programmatic_canvas_close_does_not_reenter_close_callbacks(closing_widget):
    widget, canvas, calls, errors = closing_widget
    canvas.close()
    assert canvas._closed and widget._dawn_closed
    assert calls == [('close-event',), ('destroy', 7)] and errors == []


def test_native_close_callback_failure_still_releases_and_is_contained(closing_widget):
    widget, canvas, calls, errors = closing_widget
    original = RuntimeError('application close callback failed')

    def fail():
        calls.append(('close-event',))
        raise original

    canvas.events.close = fail
    assert widget.close()
    assert canvas._closed and widget._dawn_closed
    assert calls == [('close-event',), ('destroy', 7)]
    assert errors == [(original, 'closeEvent')]


def test_detached_widget_close_has_no_canvas_to_release(closing_widget):
    widget, _, calls, errors = closing_widget
    widget._vispy_canvas = None
    assert widget.close()
    assert calls == [] and errors == []


def test_pending_callback_error_survives_nested_close_event_pump(closing_widget):
    widget, canvas, calls, errors = closing_widget
    original = ValueError('previous completion callback failure')

    def pump():
        raise original

    canvas._app.process_events = pump
    assert widget.close()
    assert canvas._closed and widget._dawn_closed
    assert calls == [('close-event',), ('destroy', 7)]
    assert errors == [(original, 'closeEvent')]
