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


SCENARIO_INPUTS = {'tkinter_state_scenario': '31932928dae83902fa88d10e1e5afd9920e7d0496c6f0b5c7d9478d48d448310', 'tkinter_resource_scenario': 'e7a9f4be5322c72cb83e382547ab23db831142141f10dbf01643d82aecf715be'}
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
    return {'branch_id': 'resource.upload-recovery', 'status': 'PASS', 'injections': injected, 'expected_error': error_record,
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
    result = None

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
        polling_stopped = not state.progress_enabled and state.progress_job is None
        assert host_job in root.tk.call('after', 'info')
        assert host_binding in root.bind('<<HostFailurePing>>')
        canvas.update()  # Explicit retry after injection is removed.
        wait(lambda: canvas._backend._photo is not previous)
        assert state.progress_enabled
        assert tuple(canvas._backend._photo.get(1, 1)) == (0, 0, 255)
        result = {'branch_id': 'progress.' + first, 'status': 'PASS', 'callback_order': first, 'loop': 'external',
                'injections': len(calls), 'deliveries': len(received),
                'expected_error': ''.join(traceback.format_exception(kind, error, trace)),
                'recovered_color': list(canvas._backend._photo.get(1, 1)), 'host_preserved': True,
                'polling_stopped': polling_stopped, 'recovered_progress_enabled': state.progress_enabled}
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
    result['cleanup_errors'] = len(errors)
    return result


def _submission_failure(route, delayed_progress):
    """Exercise real public backpressure/retry in a Tk target, without GUI pumping."""
    import tkinter as tk
    import numpy as np
    from vispy import app, gloo, _dawn
    from vispy.gloo import gl

    assert route in ('gloo', 'raw') and type(delayed_progress) is bool
    assert _dawn.submission_contract_version == 1
    application = app.Application('tkinter')
    root = tk.Tk()
    root.geometry('96x64')
    canvas = None
    host_job = host_binding = None
    host, errors = [], []
    saved_slots = None
    result = None
    fields = ('dawn_queue_submits', 'finish_calls', 'completion_waits',
              'application_presents', 'pending_tickets', 'pending_draws')

    def snapshot():
        state = _dawn.probe()
        return {key: state[key] for key in fields}

    def unchanged_completion(before, after):
        assert all(after[key] == before[key] for key in
                   ('finish_calls', 'completion_waits', 'application_presents')), (before, after)

    def flush():
        (gloo.flush if route == 'gloo' else gl.glFlush)()

    try:
        host_job = root.after(60000, lambda: host.append('unexpected-timer'))
        host_binding = root.bind('<<HostSubmissionPing>>', lambda event: host.append('host'), add='+')
        canvas = app.Canvas(app=application, parent=root, size=(96, 64), show=True)
        canvas.native.pack(fill='both', expand=True)

        def paint(event):
            gloo.set_viewport(0, 0, *canvas.physical_size)
            gloo.set_state(scissor_test=False, depth_test=False, blend=False)
            gloo.clear(color='blue')

        canvas.events.draw.ignore_callback_errors = False
        canvas.events.draw.connect(paint)
        canvas.update()
        deadline = time.monotonic() + 5
        while (canvas._backend._photo is None
               or (canvas._backend._photo.width(), canvas._backend._photo.height())
               != tuple(canvas.physical_size)
               or tuple(canvas._backend._photo.get(1, 1)) != (0, 0, 255)):
            application.process_events()
            assert time.monotonic() < deadline, 'submission setup did not present'
            time.sleep(.005)
        canvas.set_current()
        gloo.finish()  # Setup only; no completion operation is allowed inside measured flush/retry.
        saved_slots = int(_dawn.probe()['frame_slots'])
        _dawn.configure_frame_slots(1)
        configured_slots = int(_dawn.probe()['frame_slots'])
        assert configured_slots == 1
        _dawn.diagnostic_submission_controls(True, '')
        gloo.clear(color='red')
        flush()
        before = snapshot()
        assert before['pending_tickets'] == 1
        gloo.clear(color='green')
        try:
            flush()
        except RuntimeError as error:
            assert 'glFlush' in str(error) and 'capacity' in str(error), str(error)
            expected_error = {'type': type(error).__name__, 'message': str(error),
                              'traceback': traceback.format_exc()}
        else:
            raise AssertionError('required flush capacity failure did not occur')
        blocked = snapshot()
        assert blocked['pending_tickets'] == 1 and blocked['pending_draws'] > 0
        assert blocked['dawn_queue_submits'] == before['dawn_queue_submits']
        unchanged_completion(before, blocked)
        early = None
        if delayed_progress:
            _dawn.process_events()  # Real early pump while completion delivery remains held.
            early = snapshot()
            assert early['pending_tickets'] == 1 and early['pending_draws'] > 0
            assert early['dawn_queue_submits'] == before['dawn_queue_submits']
            unchanged_completion(before, early)
        _dawn.diagnostic_submission_controls(False, '')
        deadline = time.monotonic() + 5
        while _dawn.probe()['pending_tickets']:
            _dawn.process_events()
            assert time.monotonic() < deadline, 'released submission did not retire'
            time.sleep(.001)
        retired = snapshot()
        assert retired['pending_tickets'] == 0 and retired['pending_draws'] > 0
        assert retired['dawn_queue_submits'] == before['dawn_queue_submits']
        unchanged_completion(before, retired)
        flush()  # Explicit retry must submit retained green work exactly once.
        resumed = snapshot()
        assert resumed['dawn_queue_submits'] == before['dawn_queue_submits'] + 1
        assert resumed['pending_draws'] == 0 and resumed['pending_tickets'] <= 1
        unchanged_completion(before, resumed)
        width, height = canvas.physical_size
        pixels = gloo.read_pixels((0, 0, width, height), alpha=True)
        assert np.all(pixels == [0, 128, 0, 255])
        assert tuple(canvas._backend._photo.get(1, 1)) == (0, 0, 255)
        result = {'branch_id': 'submission.' + route + ('.delayed' if delayed_progress else '.immediate'),
                  'route': route, 'delayed_progress': delayed_progress,
                  'expected_error': expected_error, 'before': before, 'blocked': blocked,
                  'early_progress': early, 'retired': retired, 'resumed': resumed,
                  'readback': pixels[0, 0].tolist(), 'presented_rgb': list(canvas._backend._photo.get(1, 1)),
                  'saved_frame_slots': saved_slots, 'configured_frame_slots': configured_slots}
    finally:
        primary = sys.exc_info()

        def cleanup(callback, *args):
            try:
                callback(*args)
            except BaseException:
                errors.append(sys.exc_info())

        def verify_host():
            assert root.winfo_exists() and not root.winfo_children()
            assert host_job in root.tk.call('after', 'info')
            assert host_binding in root.bind('<<HostSubmissionPing>>')
            assert not host
            root.event_generate('<<HostSubmissionPing>>')
            assert host == ['host']

        cleanup(_dawn.diagnostic_submission_controls, False, '')
        if canvas is not None:
            cleanup(canvas.set_current)
            cleanup(canvas.context.flush_commands)
            cleanup(gloo.finish)
            cleanup(canvas.close)
        cleanup(application.quit)
        if saved_slots is not None:
            cleanup(_dawn.configure_frame_slots, saved_slots)
        if host_job is not None and host_binding is not None:
            cleanup(verify_host)
        if host_job is not None:
            cleanup(root.after_cancel, host_job)
        if host_binding is not None:
            cleanup(root.unbind, '<<HostSubmissionPing>>', host_binding)
        cleanup(root.update_idletasks)
        cleanup(root.destroy)
        for error in errors:
            traceback.print_exception(*error)
        if errors and primary[0] is None:
            raise errors[0][1].with_traceback(errors[0][2])
    assert _dawn.probe()['frame_slots'] == saved_slots
    result.update(status='PASS', host_preserved=True, restored_frame_slots=saved_slots, cleanup_errors=len(errors))
    return result


def run():
    ordinary = _scenario('tkinter_state_scenario')()
    assert ordinary['status'] == 'PASS'
    resource = _resource_failure()
    progress = [_progress_failure(order) for order in ('poll', 'draw')]
    submissions = [_submission_failure(route, delayed)
                   for route in ('gloo', 'raw') for delayed in (False, True)]
    return {'schema': 1, 'contract': 'tk-state-resource-1',
            'status': 'PASS', 'scope': 'source workflow until exact installed gates pass',
            'ordinary_state': ordinary, 'resource_failure_recovery': resource,
            'native_progress_failure_recovery': progress, 'submission_failure_recovery': submissions}


if __name__ == '__main__':
    VISPY_FUNCTIONAL_RESULT = run()
    print(json.dumps(VISPY_FUNCTIONAL_RESULT, indent=2))
