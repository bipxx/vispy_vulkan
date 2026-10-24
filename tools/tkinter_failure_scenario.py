# SPDX-License-Identifier: AGPL-3.0-only
"""Composite real Tk flow with controlled expected failures for script observation.

The harness must assert each expected error, cleanup and recovery before exiting
successfully. Running from source is not installed/absence-gate qualification.
"""
import gc
import hashlib
from pathlib import Path
import runpy
import sys
import json
import time
import traceback
from unittest.mock import patch


SCENARIO_INPUTS = {'tkinter_state_scenario': '4758319932bfd87bc11cdd0a3597efb65d914d3e3b676cc37464d71ab27957af', 'tkinter_resource_scenario': '2e7cdcae06f62a58ec57a8de94ef2b72a532c124b41792d2d2cd194a8c3f155a'}
LIVE_GAUGES = (
    'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
    'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
    'line_resource_pool_busy_slots', 'line_resource_pool_bytes',
)


def _scenario(name):
    path = Path(__file__).with_name(name + '.py')
    expected = SCENARIO_INPUTS[name]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'changed scenario input'
    function = runpy.run_path(str(path))['run']

    def execute(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        finally:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'changed scenario input'
    return execute


def _resource_failure():
    import numpy as np
    from vispy import _dawn, gloo
    run = _scenario('tkinter_resource_scenario')

    gc.collect()
    _dawn.process_events()
    baseline = {key: _dawn.probe()[key] for key in LIVE_GAUGES}
    original = gloo.Texture2D.set_data
    injected = []
    cleanup_report = {}

    def upload(texture, *args, **kwargs):
        if args and np.array_equal(args[0], np.array([[[0, 255, 0, 255]]], np.uint8)):
            injected.append('green-upload')
            raise ValueError('observed resource timer upload failure')
        return original(texture, *args, **kwargs)

    with patch.object(gloo.Texture2D, 'set_data', upload):
        try:
            run(cleanup_report=cleanup_report)
        except ValueError as error:
            assert str(error) == 'observed resource timer upload failure'
            frames = traceback.extract_tb(error.__traceback__)
            assert any(frame.name == 'tick' for frame in frames)
            assert frames[-1].name == 'upload'
            trace = error.__traceback__
            while trace.tb_frame.f_code.co_name != 'tick':
                trace = trace.tb_next
            failed_timer = trace.tb_frame.f_locals['timer']
            assert not failed_timer.running and failed_timer._backend._job is None
            del trace, failed_timer
            error_record = {'type': type(error).__name__, 'message': str(error),
                            'traceback': traceback.format_exc()}
        else:
            raise AssertionError('required resource upload failure did not occur')
    assert injected == ['green-upload'], injected
    assert cleanup_report == {'host_survived': True, 'secondary_errors': 0, 'timer_stopped': True}, cleanup_report
    assert gloo.Texture2D.set_data is original
    gc.collect()
    _dawn.process_events()
    after = {key: _dawn.probe()[key] for key in LIVE_GAUGES}
    assert after == baseline, {'before': baseline, 'after': after}
    # An explicit fresh public workflow must work after failed callback teardown.
    recovery = run()
    assert recovery['status'] == 'PASS' and recovery['device_recovered']
    assert recovery['host_survived'] and recovery['timer_ticks'] == 1
    return {'status': 'PASS', 'injections': injected, 'expected_error': error_record,
            'baseline': baseline, 'after_failure': after, 'cleanup': cleanup_report, 'timer_stopped': True, 'recovery': recovery}


def _progress_failure(first):
    import tkinter as tk
    from vispy import app, gloo, _dawn

    assert first in ('poll', 'draw')
    application = app.Application('tkinter')
    root = tk.Tk()
    root.geometry('96x64')
    canvas = None
    host_job = host_binding = watchdog = callback_job = None
    received, calls, host = [], [], []
    timed_out = []

    def wait(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            assert time.monotonic() < deadline, 'progress scenario timed out'
            time.sleep(.005)

    def report(kind, error, trace):
        received.append((kind, error, trace))

    def fail():
        calls.append('native-progress')
        raise ValueError('observed native progress failure')

    try:
        host_job = root.after(60000, lambda: host.append('unexpected-timer'))
        host_binding = root.bind('<<HostFailurePing>>', lambda event: host.append('host'), add='+')
        canvas = app.Canvas(app=application, parent=root, size=(96, 64), show=True)
        canvas.native.pack(fill='both', expand=True)

        def paint(event):
            gloo.set_viewport(0, 0, *canvas.physical_size)
            gloo.clear(color='blue')

        canvas.events.draw.ignore_callback_errors = False
        canvas.events.draw.connect(paint)
        canvas.update()
        wait(lambda: canvas._backend._photo is not None)
        state = application._backend._root_state
        draw = application._backend._callback(canvas._backend._draw)
        previous = canvas._backend._photo

        def callbacks():
            nonlocal watchdog
            try:
                routes = (state.poll, draw, state.poll) if first == 'poll' else (draw, state.poll, draw)
                for route in routes:
                    route()
            finally:
                root.after_cancel(watchdog)
                watchdog = None
                root.quit()

        def timeout():
            timed_out.append(True)
            root.quit()

        with patch.object(_dawn, 'process_events', fail), patch.object(root, 'report_callback_exception', report):
            callback_job = root.after(0, callbacks)
            watchdog = root.after(1000, timeout)
            root.mainloop()  # Actual borrowed-loop delivery, without pytest monkeypatch.
        assert not timed_out
        assert calls == ['native-progress'] and len(received) == 1
        kind, error, trace = received[0]
        assert kind is ValueError and str(error) == 'observed native progress failure'
        assert trace is not None and traceback.extract_tb(trace)[-1].name == 'fail'
        assert not state.progress_enabled and state.progress_job is None
        assert host_job in root.tk.call('after', 'info')
        assert host_binding in root.bind('<<HostFailurePing>>')
        canvas.update()  # Explicit retry after injection is removed.
        wait(lambda: canvas._backend._photo is not previous)
        assert state.progress_enabled
        assert tuple(canvas._backend._photo.get(1, 1)) == (0, 0, 255)
        return {'status': 'PASS', 'callback_order': first, 'loop': 'external',
                'injections': len(calls), 'deliveries': len(received),
                'expected_error': ''.join(traceback.format_exception(kind, error, trace)),
                'recovered_color': [0, 0, 255], 'host_preserved': True}
    finally:
        primary = sys.exc_info()
        errors = []

        def cleanup(callback, *args):
            try:
                callback(*args)
            except BaseException:
                errors.append(sys.exc_info())

        def verify_host():
            assert root.winfo_exists() and not root.winfo_children()
            assert host_job in root.tk.call('after', 'info')
            assert host_binding in root.bind('<<HostFailurePing>>')
            root.event_generate('<<HostFailurePing>>')
            assert host == ['host']

        if watchdog is not None:
            cleanup(root.after_cancel, watchdog)
        if callback_job is not None:
            cleanup(root.after_cancel, callback_job)
        if canvas is not None:
            cleanup(canvas.close)
        cleanup(application.quit)
        if host_job is not None and host_binding is not None:
            cleanup(verify_host)
        if host_job is not None:
            cleanup(root.after_cancel, host_job)
        if host_binding is not None:
            cleanup(root.unbind, '<<HostFailurePing>>', host_binding)
        cleanup(root.update_idletasks)
        cleanup(root.destroy)
        for error in errors:
            traceback.print_exception(*error)
        if errors and primary[0] is None:
            raise errors[0][1].with_traceback(errors[0][2])


def run():
    ordinary = _scenario('tkinter_state_scenario')()
    assert ordinary['status'] == 'PASS'
    resource = _resource_failure()
    progress = [_progress_failure(order) for order in ('poll', 'draw')]
    return {'status': 'PASS', 'scope': 'source workflow until exact installed gates pass',
            'ordinary_state': ordinary, 'resource_failure_recovery': resource,
            'native_progress_failure_recovery': progress}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
