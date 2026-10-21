"""Teardown must preserve ownership and errors without requiring a GPU."""

from types import SimpleNamespace
import importlib.util
import json
from pathlib import Path

import pytest

from tools.upstream_qt_lifecycle import dispose_closed_top_level_widgets


@pytest.fixture
def lifecycle():
    gui_thread = object()
    pending = []

    def send(receiver, event):
        assert event == "DeferredDelete"
        assert pending == [receiver]
        pending.clear()
        receiver.deleted = True

    qt = SimpleNamespace(
        QThread=SimpleNamespace(currentThread=lambda: gui_thread),
        QCoreApplication=SimpleNamespace(sendPostedEvents=send),
        QEvent=SimpleNamespace(Type=SimpleNamespace(DeferredDelete="DeferredDelete")))

    class Backend:
        def __init__(self, parent=None):
            self.parent = parent
            self.deleted = False
            self.owner = gui_thread
            self.close_error = None
            self.close_calls = 0

        def thread(self):
            return self.owner

        def _vispy_close(self):
            self.close_calls += 1
            if self.close_error is not None:
                raise self.close_error
            return "original-result"

        def parentWidget(self):
            return self.parent

        def deleteLater(self):
            pending.append(self)

    return Backend, qt, pending


def test_top_level_disposes_only_its_own_posted_deletion(lifecycle):
    backend, qt, pending = lifecycle
    original = backend._vispy_close
    widget, record = backend(), {}
    with dispose_closed_top_level_widgets(backend, qt, lambda w: w.deleted, record):
        assert widget._vispy_close() == "original-result"
        assert widget.deleted and pending == []
    assert record["disposed"] == 1 and record["restored"]
    assert backend._vispy_close is original


def test_embedded_widget_remains_owned_by_parent(lifecycle):
    backend, qt, pending = lifecycle
    widget, record = backend(parent=object()), {}
    with dispose_closed_top_level_widgets(backend, qt, lambda w: w.deleted, record):
        widget._vispy_close()
    assert not widget.deleted and pending == []
    assert record["embedded_preserved"] == 1 and record["disposed"] == 0


def test_wrong_thread_rejects_before_original_close(lifecycle):
    backend, qt, pending = lifecycle
    widget, record = backend(), {}
    widget.owner = object()
    with pytest.raises(RuntimeError, match="owning thread"):
        with dispose_closed_top_level_widgets(backend, qt, lambda w: w.deleted, record):
            widget._vispy_close()
    assert widget.close_calls == 0 and not widget.deleted and pending == []
    assert record["restored"]


def test_original_failure_propagates_without_disposal(lifecycle):
    backend, qt, pending = lifecycle
    original = backend._vispy_close
    widget, record = backend(), {}
    error = widget.close_error = RuntimeError("provider close failed")
    with pytest.raises(RuntimeError) as caught:
        with dispose_closed_top_level_widgets(backend, qt, lambda w: w.deleted, record):
            widget._vispy_close()
    assert caught.value is error
    assert not widget.deleted and pending == []
    assert backend._vispy_close is original and record["restored"]


def test_failed_native_disposal_propagates_and_restores(lifecycle):
    backend, qt, _ = lifecycle
    original = backend._vispy_close
    qt.QCoreApplication.sendPostedEvents = lambda *_: None
    widget, record = backend(), {}
    with pytest.raises(RuntimeError, match="not disposed"):
        with dispose_closed_top_level_widgets(backend, qt, lambda w: w.deleted, record):
            widget._vispy_close()
    assert backend._vispy_close is original and record["restored"]


def test_inherited_method_restored_after_body_exception(lifecycle):
    backend, qt, _ = lifecycle
    class Child(backend):
        pass
    original, record = Child._vispy_close, {}
    with pytest.raises(ValueError, match="capture failed"):
        with dispose_closed_top_level_widgets(Child, qt, lambda w: w.deleted, record):
            raise ValueError("capture failed")
    assert "_vispy_close" not in vars(Child)
    assert Child._vispy_close is original and record["restored"]


@pytest.mark.parametrize("failure", ["stale_record", "nonzero_after_record"])
def test_new_capture_entrypoint_rejects_failed_worker(tmp_path, monkeypatch, failure):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "tools"))
    spec = importlib.util.spec_from_file_location("qt_oracle_failure_control", root / "tools/oracle_capture_qt.py")
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    monkeypatch.setattr(capture, "provenance", lambda kind: {})
    name = "uniform_snapshot"
    path = tmp_path / f"{name}.capture.json"
    record = {"fixtures": {name: {"untrusted": True}}, "errors": {}}
    path.write_text(json.dumps(record))

    def failed_worker(*args, **kwargs):
        assert not path.exists(), "A previous result cannot survive a new capture"
        assert str(root / "tools/oracle_capture_qt.py") in args[0]
        if failure == "nonzero_after_record":
            path.write_text(json.dumps(record))
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(capture.subprocess, "run", failed_worker)
    monkeypatch.setattr(capture.sys, "argv", ["oracle_capture_qt.py", "--kind", "candidate",
                                             "--output", str(tmp_path), "--fixtures", name])
    assert capture.main()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["fixtures"] == {} and name in manifest["errors"]
