# SPDX-License-Identifier: AGPL-3.0-only
"""Actual Tk negative controls for the selected scenario's distinguishing oracles."""
import gc
from pathlib import Path
import runpy

import pytest
from vispy import app, gloo, _dawn

ROOT = Path(__file__).resolve().parents[2]
GAUGES = ('pending_tickets','queued_frames','live_buffer_bytes','live_cpu_buffer_bytes',
          'live_texture_bytes','canvas_texture_bytes','transient_buffer_bytes',
          'line_resource_pool_busy_slots','line_resource_pool_bytes')


def scenario(name):
    return runpy.run_path(str(ROOT/'tools'/('tkinter_'+name+'_scenario.py')))['run']


@pytest.fixture(autouse=True)
def cleanup_native(monkeypatch):
    yield
    monkeypatch.undo()
    gc.collect()
    _dawn.process_events()
    _dawn.shutdown()
    state = _dawn.probe()
    assert not any(state[key] for key in GAUGES), {key:state[key] for key in GAUGES}


def test_noop_finish_fails_before_readback(monkeypatch):
    reads = []
    original_read = gloo.read_pixels
    def read(*args, **kwargs):
        reads.append(True)
        return original_read(*args, **kwargs)
    monkeypatch.setattr(gloo, 'read_pixels', read)
    finish_reads = []
    def suppressed_finish(): finish_reads.append(len(reads))
    monkeypatch.setattr(gloo, 'finish', suppressed_finish)
    with pytest.raises(AssertionError, match='finish before readback'):
        scenario('state')()
    assert finish_reads and len(reads) == finish_reads[0], (
        'Readback after suppressed finish must not supply completion', finish_reads, reads)


@pytest.mark.parametrize('kind', ['Program','Texture2D','VertexBuffer'])
def test_suppressed_delete_fails_before_survivor_close(monkeypatch, kind):
    calls = []
    def suppressed(resource):calls.append(resource.id)
    monkeypatch.setattr(getattr(gloo, kind), 'delete', suppressed)
    with pytest.raises(AssertionError, match='resource retirement before survivor close'):
        scenario('resource')()
    assert calls, 'The selected class delete must actually have been suppressed'


def test_cross_target_corruption_fails_before_repaint(monkeypatch):
    canvases = []
    corrupted = []
    original_canvas, original_flush = app.Canvas, gloo.flush
    def canvas(*args, **kwargs):
        result = original_canvas(*args, **kwargs)
        canvases.append(result)
        return result
    def flush():
        original_flush()
        current = gloo.get_current_canvas()
        if len(canvases)==2 and current is canvases[0] and not corrupted:
            other = canvases[1]
            photo = other._backend._photo
            other.set_current()
            gloo.clear(color='yellow')
            original_flush()  # Corrupt the real target without a wait or repaint.
            assert other._backend._photo is photo
            current.set_current()
            corrupted.append(True)
    monkeypatch.setattr(app, 'Canvas', canvas)
    monkeypatch.setattr(gloo, 'flush', flush)
    with pytest.raises(AssertionError, match='untouched second target before repaint'):
        scenario('state')()
    assert corrupted == [True]
