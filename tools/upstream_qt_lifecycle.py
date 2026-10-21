"""Dispose closed upstream Qt widgets before a later render can trigger GC.

QOpenGLWidget's destructor makes its own context current. Delaying destruction
until Python collects a closed canvas can therefore clear another canvas's
current context. This adapter finishes the original close path, then delivers
only that top-level widget's DeferredDelete event on its owning thread.
"""

from contextlib import contextmanager


@contextmanager
def dispose_closed_top_level_widgets(backend_class, qt_core, is_deleted, record):
    """Temporarily amend teardown while retaining embedded parent ownership."""
    original = backend_class._vispy_close
    had_local = "_vispy_close" in vars(backend_class)
    record.update(entered=True, closed=0, disposed=0, embedded_preserved=0,
                  restored=False)

    def close(widget):
        if qt_core.QThread.currentThread() != widget.thread():
            raise RuntimeError("Qt widget must be closed on its owning thread")
        result = original(widget)
        record["closed"] += 1
        if is_deleted(widget):
            return result
        if widget.parentWidget() is not None:
            record["embedded_preserved"] += 1
            return result
        widget.deleteLater()
        qt_core.QCoreApplication.sendPostedEvents(
            widget, qt_core.QEvent.Type.DeferredDelete)
        if not is_deleted(widget):
            raise RuntimeError("Closed top-level Qt widget was not disposed")
        record["disposed"] += 1
        return result

    backend_class._vispy_close = close
    try:
        yield record
    finally:
        if had_local:
            backend_class._vispy_close = original
        else:
            del backend_class._vispy_close
        record["restored"] = backend_class._vispy_close is original
        if not record["restored"]:
            raise RuntimeError("Original upstream Qt close method was not restored")


@contextmanager
def upstream_qt_teardown():
    """Select pristine upstream PyQt6 and expose the explicit teardown record."""
    import vispy
    from vispy import app
    from PyQt6 import QtCore, sip

    if vispy.__version__ != "0.17.0":
        raise RuntimeError("This teardown adapter is for upstream VisPy 0.17.0 only")
    app.use_app("pyqt6")
    from vispy.app.backends import _qt

    record = {}
    with dispose_closed_top_level_widgets(
            _qt.CanvasBackendDesktop, QtCore, sip.isdeleted, record):
        yield record
