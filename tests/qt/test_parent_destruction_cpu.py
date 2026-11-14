"""A real Qt parent deletion must also settle the Python Canvas ownership."""

from types import SimpleNamespace
import gc
import importlib
import os
import weakref

import pytest

import vispy
from vispy.app import Canvas

binding = os.environ.get('VISPY_PARENT_TEST_BINDING', 'pyqt6')
backend = importlib.import_module('vispy.app.backends._' + binding)
QT = backend._qt

if binding == 'pyside6':
    import shiboken6
    sip = SimpleNamespace(delete=shiboken6.delete,
                          isdeleted=lambda widget: not shiboken6.isValid(widget))
else:
    sip = importlib.import_module('PyQt5.sip' if binding == 'pyqt5' else 'PyQt6.sip')


@pytest.mark.parametrize('callback_error', [False, True])
@pytest.mark.parametrize('pending_error', [False, True])
def test_parent_deletion_closes_owned_canvas_without_calling_deleted_widget(
        monkeypatch, callback_error, pending_error):
    application = QT.QApplication.instance() or QT.QApplication(
        ['vispy-parent-destruction-test', '-platform', 'offscreen'])
    calls = []
    original = RuntimeError('close callback failure')
    pending = ValueError('earlier callback failure')
    application._vispy_dawn_callback_error = pending if pending_error else None
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(
        destroy_canvas=lambda canvas_id: calls.append(('destroy', canvas_id))), raising=False)

    class Widget(QT.CanvasBackendDesktop):
        def __init__(self, parent):
            self._initialized = False
            self._vispy_canvas = None
            QT.QWidget.__init__(self, parent)
            self._dawn_closed = False
            self._dawn_canvas_id = 7001

    parent = QT.QWidget()
    widget = Widget(parent)
    canvas = Canvas.__new__(Canvas)
    canvas._backend, canvas._closed = widget, False
    canvas._app = SimpleNamespace(process_events=lambda: None, backend_name=binding + ' CPU double')
    def on_close():
        calls.append(('close-event',))
        if callback_error:
            raise original

    canvas.events = SimpleNamespace(close=on_close)
    widget._vispy_canvas = canvas
    QT._connect_dawn_canvas_release(widget, 7001, vispy._dawn.destroy_canvas)
    deleted = []
    widget.destroyed.connect(lambda obj=None: deleted.append(True))

    parent.deleteLater()
    application.sendPostedEvents(None, QT.QtCore.QEvent.Type.DeferredDelete)
    assert deleted == [True], 'the child must actually be destroyed by its parent'
    assert 7001 not in QT._dawn_canvas_releases
    assert canvas._closed, 'native release must not leave the Python Canvas open'
    assert canvas._backend is None
    assert calls.count(('close-event',)) == 1
    assert calls.count(('destroy', 7001)) == 1
    canvas.close()  # Must remain safe after the C++ QWidget has gone away.
    assert calls.count(('close-event',)) == 1
    expected = pending if pending_error else original if callback_error else None
    if expected is not None:
        with pytest.raises(type(expected)) as raised:
            QT._raise_dawn_callback_error(application)
        assert raised.value is expected
    assert application._vispy_dawn_callback_error is None


def test_module_rooted_release_does_not_keep_python_owner_alive():
    slots, calls = [], []

    class Owner:
        destroyed = SimpleNamespace(connect=slots.append)

    owner = Owner()
    reference = weakref.ref(owner)
    QT._connect_dawn_canvas_release(owner, 7002, calls.append)
    del owner
    gc.collect()
    assert reference() is None
    assert 7002 in QT._dawn_canvas_releases
    slots.pop()()
    assert calls == [7002] and 7002 not in QT._dawn_canvas_releases


def test_native_release_failure_is_contained_at_qt_boundary():
    application = QT.QApplication.instance() or QT.QApplication(
        ['vispy-release-error-test', '-platform', 'offscreen'])
    original = RuntimeError('native release failure')

    def fail(canvas_id):
        assert canvas_id == 7003
        raise original

    QT._release_dawn_canvas({}, fail, 7003)
    with pytest.raises(RuntimeError) as raised:
        QT._raise_dawn_callback_error(application)
    assert raised.value is original


def test_destroyed_notification_after_explicit_close_keeps_close_event_once():
    calls = []
    canvas = Canvas.__new__(Canvas)
    canvas._closed = False
    canvas._backend = SimpleNamespace(_vispy_close=lambda: calls.append('backend-close'))
    canvas._app = SimpleNamespace(backend_name='CPU double')
    canvas.events = SimpleNamespace(close=lambda: calls.append('close-event'))
    canvas.close()
    canvas._backend_destroyed()
    canvas._backend_destroyed()
    canvas.close()
    assert canvas._closed and canvas._backend is None
    assert calls == ['close-event', 'backend-close']


@pytest.fixture
def owned_canvas(monkeypatch):
    application = QT.QApplication.instance() or QT.QApplication(
        ['vispy-reentrant-parent-test', '-platform', 'offscreen'])
    calls = []
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(
        destroy_canvas=lambda canvas_id: calls.append(('destroy', canvas_id))), raising=False)

    class Widget(QT.CanvasBackendDesktop):
        def __init__(self, parent):
            self._initialized, self._vispy_canvas = False, None
            QT.QWidget.__init__(self, parent)
            self._dawn_closed, self._dawn_canvas_id = False, 7005

    parent = QT.QWidget()
    widget = Widget(parent)
    canvas = Canvas.__new__(Canvas)
    canvas._backend, canvas._closed, canvas._backend_kwargs = widget, False, None
    canvas._app = SimpleNamespace(process_events=lambda: None, backend_name=binding + ' CPU double')
    canvas.events = SimpleNamespace(close=lambda: calls.append(('close-event',)))
    widget._vispy_canvas = canvas
    QT._connect_dawn_canvas_release(widget, 7005, vispy._dawn.destroy_canvas)
    try:
        yield canvas, widget, parent, calls
    finally:
        if not sip.isdeleted(parent):
            sip.delete(parent)
        application._vispy_dawn_callback_error = None


@pytest.mark.parametrize('raising_callback', [False, True])
def test_close_callback_can_delete_parent_without_secondary_cleanup_error(
        owned_canvas, raising_callback, caplog):
    canvas, widget, parent, calls = owned_canvas
    original = ValueError('original reentrant close failure')

    def on_close():
        calls.append(('close-event',))
        sip.delete(parent)
        if raising_callback:
            raise original

    canvas.events.close = on_close
    if raising_callback:
        with pytest.raises(ValueError) as raised:
            canvas.close()
        assert raised.value is original
    else:
        canvas.close()
    assert sip.isdeleted(widget) and canvas._closed and canvas._backend is None
    assert calls == [('close-event',), ('destroy', 7005)]
    assert 'Canvas cleanup after close callback failure failed' not in caplog.text
    canvas.close()


def test_create_native_and_update_after_parent_deletion_are_noops(owned_canvas):
    canvas, widget, parent, calls = owned_canvas
    sip.delete(parent)
    canvas.create_native()
    canvas.update()
    assert sip.isdeleted(widget) and canvas._backend is None and canvas._closed
    assert calls == [('close-event',), ('destroy', 7005)]


def test_explicit_close_then_real_parent_deletion_emits_close_once(owned_canvas):
    canvas, widget, parent, calls = owned_canvas
    canvas.close()
    sip.delete(parent)
    canvas.close()
    assert sip.isdeleted(widget) and canvas._backend is None and canvas._closed
    assert calls.count(('close-event',)) == 1
    # The native destroy operation must tolerate both explicit close and the
    # later QObject destruction notification. Rendered coverage checks it too.
    assert calls.count(('destroy', 7005)) == 2
