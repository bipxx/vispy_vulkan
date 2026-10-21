"""Exercise the real Qt paint method with CPU doubles; acquire no GPU."""

from types import SimpleNamespace

import pytest

from vispy.app.backends import _pyqt6
import vispy


QT = _pyqt6._qt


def paint_double(monkeypatch, *, scoped=True, failure=None, abort_failure=False, ready=True):
    events, errors = [], []
    original = RuntimeError('original paint failure')
    calls = {'present': 0}

    def frame_ready(canvas_id):
        assert canvas_id == 7
        events.append('ready')
        return ready

    def begin(canvas_id):
        assert canvas_id == 7
        events.append('begin')
        if failure == 'begin':
            raise original
        return 19

    def present(canvas_id):
        assert canvas_id == 7
        calls['present'] += 1
        events.append('present')
        if failure == 'final-present' and calls['present'] == 2:
            raise original

    def end(canvas_id, token):
        assert (canvas_id, token) == (7, 19)
        events.append('end')
        if failure == 'end':
            raise original

    def abort(canvas_id, token, reason):
        assert (canvas_id, token, reason) == (7, 19, str(original))
        events.append('abort')
        if abort_failure:
            raise RuntimeError('secondary cleanup failure')

    native = SimpleNamespace(frame_ready=frame_ready, present=present)
    if scoped:
        native.begin_canvas_paint, native.end_canvas_paint, native.abort_canvas_paint = begin, end, abort
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)

    def draw():
        events.append('draw')
        if failure == 'draw':
            raise original
        native.present(7)  # Existing autoswap, followed by the Qt paint tail.
        events.append('alpha-tail')

    backend = SimpleNamespace(
        _vispy_canvas=object(), _dawn_canvas_id=7, _dawn_closed=False, _dawn_callback_failed=False,
        isMinimized=lambda: False, width=lambda: 32, height=lambda: 24,
        _draw_dawn_scene=draw, _start_dawn_pump=lambda: events.append('pump'),
        _record_dawn_callback_error=lambda error, callback: errors.append((error, callback)),
        update=lambda: None)
    return backend, native, events, errors, original


def test_scope_surrounds_intermediate_present_alpha_tail_and_final_present(monkeypatch):
    backend, _, events, errors, _ = paint_double(monkeypatch)
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events == ['ready', 'begin', 'draw', 'present', 'alpha-tail', 'present', 'pump', 'end']
    assert errors == []


def test_earlier_native_without_scope_api_keeps_existing_paint_sequence(monkeypatch):
    backend, _, events, errors, _ = paint_double(monkeypatch, scoped=False)
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events == ['ready', 'draw', 'present', 'alpha-tail', 'present', 'pump']
    assert errors == []


@pytest.mark.parametrize('failure', ['draw', 'final-present', 'end'])
@pytest.mark.parametrize('abort_failure', [False, True])
def test_abort_retains_original_draw_present_or_end_error(monkeypatch, failure, abort_failure):
    backend, _, events, errors, original = paint_double(monkeypatch, failure=failure, abort_failure=abort_failure)
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events[-1] == 'abort'
    assert events.count('begin') == events.count('abort') == 1
    assert errors == [(original, 'paintEvent')]
    if failure != 'end':
        assert 'end' not in events


def test_failed_begin_preserves_error_without_aborting_an_unowned_token(monkeypatch):
    backend, _, events, errors, original = paint_double(monkeypatch, failure='begin')
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events == ['ready', 'begin']
    assert errors == [(original, 'paintEvent')]


def test_backpressure_defers_paint_without_acquiring_a_token(monkeypatch):
    backend, _, events, errors, _ = paint_double(monkeypatch, ready=False)
    timers = []
    monkeypatch.setattr(QT.QtCore, 'QTimer', SimpleNamespace(singleShot=lambda delay, callback: timers.append((delay, callback))))
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events == ['ready', 'pump']
    assert timers == [(1, backend.update)] and errors == []


def test_partial_native_api_reports_error_before_scene_drawing(monkeypatch):
    backend, native, events, errors, _ = paint_double(monkeypatch)
    del native.abort_canvas_paint
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events == ['ready']
    assert len(errors) == 1 and 'incomplete' in str(errors[0][0])


@pytest.mark.parametrize('token', [0, -1, True, '19', None])
def test_invalid_native_paint_token_cannot_enter_scene(monkeypatch, token):
    backend, native, events, errors, _ = paint_double(monkeypatch)
    native.begin_canvas_paint = lambda canvas_id: token
    QT.CanvasBackendDesktop.paintEvent(backend, None)
    assert events == ['ready']
    assert len(errors) == 1 and 'invalid token' in str(errors[0][0])
