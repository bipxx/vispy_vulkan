# SPDX-License-Identifier: AGPL-3.0-only
"""Capture joins under existing diagnostic controls; no synthetic GPU results."""
from contextlib import contextmanager
import json
import sys
import traceback
import time

import numpy as np
import pytest

from test_presented_capture import COLORS, SIZE, Scene, expected

pytestmark = pytest.mark.gpu
PENDING = ('pending_tickets', 'queued_frames', 'pending_timestamp_frames')


@contextmanager
def opened_scene(name, backend='pyqt6'):
    # Own partial initialization and drain only this canvas's terminal rows.
    scene = Scene.__new__(Scene)
    try:
        scene.__init__(name, backend)
        yield scene
    finally:
        original = traceback.format_exc() if sys.exc_info()[0] is not None else None
        failures, receipts, maps, idle_refusals = [], [], [], []
        native = getattr(scene, 'native', None)
        identifier = getattr(scene, 'identifier', None)
        actions = []
        if native is not None:
            actions.append(('release-hold', lambda: native.diagnostic_submission_controls(False, '')))
        actions.append(('close-canvas', scene.close))
        if native is not None and identifier is not None:
            actions.append(('destroy-owned-canvas', lambda: native.destroy_canvas(identifier)))
        for phase, action in actions:
            try:
                action()
            except Exception:
                failures.append(dict(phase=phase, traceback=traceback.format_exc()))
        state = None
        if native is not None and identifier is not None:
            deadline = time.monotonic()+5
            while True:
                try:
                    native.process_events()
                    receipts.extend(native.benchmark_completions(identifier))
                    maps.extend(native.benchmark_gpu_timings(identifier))
                    state = dict(native.probe())
                    if not any(state[name] for name in PENDING):
                        # probe() polls and may publish a final row after the
                        # earlier drain. Drain again, then require the strict
                        # idle check to include segments, owners and all rows.
                        receipts.extend(native.benchmark_completions(identifier))
                        maps.extend(native.benchmark_gpu_timings(identifier))
                        try:
                            native.configure_frame_slots(state['frame_slots'])
                        except RuntimeError as error:
                            if str(error) not in (
                                    'frame slots can change only when submissions and query callbacks are idle',
                                    'frame slots can change only when frames are idle'):
                                raise
                            idle_refusals.append(str(error))
                        else:
                            break
                except Exception:
                    failures.append(dict(phase='drain-owned-terminal-work', traceback=traceback.format_exc()))
                    break
                if time.monotonic() >= deadline:
                    failures.append(dict(phase='drain-owned-terminal-work', error='five-second deadline'))
                    break
                time.sleep(.001)
        value = dict(original_exception=original, cleanup_failures=failures,
                     canvas_id=identifier, terminal_receipts=receipts, terminal_gpu=maps, probe=state,
                     bounded_idle_refusals=idle_refusals)
        output = getattr(scene, 'output', None)
        if output is not None and output.is_dir():
            (output/'owned-cleanup.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
        if failures and original is None:
            raise RuntimeError('owned scene cleanup failed; see owned-cleanup.json')


def record(scene, label, **details):
    value = dict(event=label, probe=dict(scene.native.probe()), **details)
    with (scene.output/'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True)+'\n')
    return value['probe']


def records(scene, frame_id, timing):
    receipts, maps = [], []
    deadline = time.monotonic()+5
    while True:
        scene.native.process_events()
        receipts.extend(scene.native.benchmark_completions(scene.identifier))
        maps.extend(scene.native.benchmark_gpu_timings(scene.identifier))
        state = record(scene, 'collect', receipts=receipts, gpu=maps)
        if len(receipts) == 1 and len(maps) == int(timing) and not any(state[name] for name in PENDING):
            break
        assert time.monotonic() < deadline, 'owned producer did not retire'
        time.sleep(.001)
    assert receipts[0]['frame_id'] == frame_id
    if timing:
        assert maps[0]['frame_id'] == frame_id
    return receipts[0], maps[0] if timing else None


def begin(scene, frame_id, timing):
    config = scene.native.benchmark_configure_gpu_timing(scene.identifier, timing)
    if timing:
        assert config['enabled'] and config['supported'], 'real timestamps required'
    scene.native.benchmark_begin_frame(scene.identifier, frame_id)
    return config


def submit(scene):
    scene.canvas.set_current()
    scene.draw(None)
    scene.canvas.context.flush_commands()
    scene.native.present(scene.identifier)


def assert_no_new_records(scene):
    receipts = scene.native.benchmark_completions(scene.identifier)
    maps = scene.native.benchmark_gpu_timings(scene.identifier)
    record(scene, 'after-diagnostic-records', receipts=receipts, gpu=maps)
    assert receipts == maps == []


@pytest.mark.parametrize('timing', [False, True])
def test_capture_after_consumed_producer_records_preserves_exact_image(request, timing):
    with opened_scene(request.node.name, 'dawn_headless') as scene:
        config = begin(scene, 901, timing)
        submit(scene)
        receipt, gpu = records(scene, 901, timing)
        assert receipt['status'] == 'success' and receipt['frame_scope'] == 'native_present'
        assert receipt['ownership_closed'] and receipt['ownership_retired']
        if timing:
            assert gpu['status'] == 'success' and not gpu['error'] and gpu['passes']
            assert gpu['device_generation'] == config['device_generation']
        before = record(scene, 'retired-producer')
        np.testing.assert_array_equal(scene.capture(), expected(COLORS))
        np.testing.assert_array_equal(scene.capture(), expected(COLORS))
        after = record(scene, 'repeated-capture')
        assert after['application_presents'] == before['application_presents']
        assert after['render_passes'] == before['render_passes']  # mirror was already converted
        assert_no_new_records(scene)


@pytest.mark.parametrize('timing', [False, True])
def test_held_producer_cannot_become_capture_success_before_retirement(request, timing):
    with opened_scene(request.node.name, 'dawn_headless') as scene:
        begin(scene, 901, timing)
        scene.native.diagnostic_submission_controls(True, '')
        submit(scene)
        before = record(scene, 'held-producer')
        assert before['pending_tickets'] == 1
        with pytest.raises(RuntimeError, match='read_presented unavailable'):
            scene.capture()
        after = record(scene, 'rejected-held-producer')
        assert after['pending_tickets'] == 1
        assert after['dawn_queue_submits'] == before['dawn_queue_submits']
        assert after['application_presents'] == before['application_presents']
        assert scene.native.benchmark_completions(scene.identifier) == []
        scene.native.diagnostic_submission_controls(False, '')
        receipt, gpu = records(scene, 901, timing)
        assert receipt['status'] == 'success'
        if timing:
            assert gpu['status'] == 'success'
        np.testing.assert_array_equal(scene.capture(), expected(COLORS))
        assert_no_new_records(scene)


@pytest.mark.parametrize('stage', ['before-submit', 'callback-registration', 'query-map'])
def test_failed_explicit_capture_does_not_commit_the_lazy_mirror(request, stage):
    with opened_scene(request.node.name) as scene:
        before = record(scene, 'before-failed-capture', injected_cpu_failure_stage=stage)
        scene.native.diagnostic_submission_controls(True, stage)
        with pytest.raises(RuntimeError, match=f'diagnostic submission failure: {stage}'):
            scene.capture()
        held = record(scene, 'failed-capture-held')
        submitted = int(stage != 'before-submit')
        assert held['dawn_queue_submits']-before['dawn_queue_submits'] == submitted
        assert held['pending_tickets'] == submitted
        assert held['application_presents'] == before['application_presents']
        scene.native.diagnostic_submission_controls(False, '')
        scene.settle()
        retired = record(scene, 'failed-capture-retired')
        # The failed attempt must not mark a refreshed mirror ready. A fresh,
        # successful diagnostic retries conversion from the same proven source.
        np.testing.assert_array_equal(scene.capture(), expected(COLORS))
        recovered = record(scene, 'fresh-capture-success')
        assert recovered['render_passes']-retired['render_passes'] == 1
        assert recovered['application_presents'] == before['application_presents']
        assert_no_new_records(scene)


@pytest.mark.parametrize('stage', ['after-submit', 'callback-registration', 'query-map'])
def test_failed_owned_producer_is_unavailable_after_failure_records_are_consumed(request, stage):
    with opened_scene(request.node.name, 'dawn_headless') as scene:
        begin(scene, 901, True)
        token = scene.native.begin_canvas_paint(scene.identifier)
        scene.canvas.set_current()
        scene.draw(None)
        scene.canvas.context.flush_commands()
        before = record(scene, 'before-owned-submission', injected_cpu_failure_stage=stage)
        scene.native.diagnostic_submission_controls(True, stage)
        with pytest.raises(RuntimeError, match=f'diagnostic submission failure: {stage}'):
            scene.native.present(scene.identifier)
        held = record(scene, 'failed-owned-submission-held')
        assert held['dawn_queue_submits']-before['dawn_queue_submits'] == 1
        assert held['pending_tickets'] == 1
        scene.native.abort_canvas_paint(scene.identifier, token, 'expected post-submit failure control')
        scene.native.diagnostic_submission_controls(False, '')
        receipt, gpu = records(scene, 901, True)
        assert receipt['status'] == 'failed' and not receipt['presented']
        assert receipt['paint_token'] == gpu['paint_token'] == token
        assert receipt['frame_scope'] == gpu['frame_scope'] == 'qt_paint'
        assert receipt['submission_count'] == gpu['submission_count'] == 1
        assert gpu['status'] == ('map_error' if stage == 'query-map' else 'submission_error')
        assert gpu['error']
        before_read = record(scene, 'consumed-failure-records')
        with pytest.raises(RuntimeError, match='read_presented unavailable'):
            scene.capture()
        after_read = record(scene, 'rejected-failed-producer')
        assert after_read['dawn_queue_submits'] == before_read['dawn_queue_submits']
        assert_no_new_records(scene)
        begin(scene, 902, True)
        submit(scene)
        recovered, recovered_gpu = records(scene, 902, True)
        assert recovered['status'] == recovered_gpu['status'] == 'success'
        np.testing.assert_array_equal(scene.capture(), expected(COLORS))


@contextmanager
def one_slot_scene(name):
    native, scene, previous_slots = None, None, None
    try:
        with opened_scene(name, 'dawn_headless') as scene:
            native = scene.native
            previous_slots = record(scene, 'before-slot-change')['frame_slots']
            native.configure_frame_slots(1)
            yield scene
    finally:
        # The owned scene and its terminal records retire before restoring the
        # global slot setting, including when the original assertion failed.
        original = traceback.format_exc() if sys.exc_info()[0] is not None else None
        if native is not None and previous_slots is not None:
            failures = []
            try:
                native.configure_frame_slots(previous_slots)
            except Exception:
                failures.append(dict(phase='restore-original-slots', traceback=traceback.format_exc()))
            value = dict(original_exception=original, cleanup_failures=failures,
                         original_slots=previous_slots)
            (scene.output/'slot-cleanup.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
            if failures and original is None:
                raise RuntimeError('owned slot cleanup failed; see slot-cleanup.json')


def test_deferred_native_paint_origin_cannot_be_reclassified_as_headless(request):
    # Native ownership API with no attached surface. This is a controlled
    # paint-origin case, not a claim that a real Qt paint ran here.
    with one_slot_scene(request.node.name) as scene:
        scene.native.diagnostic_submission_controls(True, '')
        scene.gloo.clear(color=(0., 0., 0., 1.))
        scene.gloo.flush()  # occupy the only slot before the owned batch
        assert record(scene, 'held-slot')['pending_tickets'] == 1
        begin(scene, 901, True)
        token = scene.native.begin_canvas_paint(scene.identifier)
        submit(scene)
        scene.native.end_canvas_paint(scene.identifier, token)
        before = record(scene, 'closed-but-queued-paint')
        assert before['queued_frames'] == 1
        with pytest.raises(RuntimeError, match='read_presented unavailable'):
            scene.capture()
        after = record(scene, 'refused-queued-paint')
        assert after['dawn_queue_submits'] == before['dawn_queue_submits']
        assert after['completion_waits'] == before['completion_waits']
        scene.native.diagnostic_submission_controls(False, '')
        receipt, gpu = records(scene, 901, True)
        assert receipt['paint_token'] == gpu['paint_token'] == token
        assert receipt['frame_scope'] == gpu['frame_scope'] == 'qt_paint'
        assert not receipt['presented'] and receipt['present_count'] == 0
        with pytest.raises(RuntimeError, match='read_presented unavailable'):
            scene.capture()


def test_measured_canvas_teardown_drains_native_ownership_each_cycle(request):
    for cycle in range(8):
        with opened_scene(f'{request.node.name}-{cycle}', 'dawn_headless') as scene:
            begin(scene, 901, True)
            submit(scene)
            receipt, gpu = records(scene, 901, True)
            assert receipt['status'] == gpu['status'] == 'success'
            np.testing.assert_array_equal(scene.capture(), expected(COLORS))
            native, identifier = scene.native, scene.identifier
            record(scene, 'before-canvas-destruction', cycle=cycle)
        state = record(scene, 'after-canvas-destruction', cycle=cycle)
        assert not any(state[name] for name in PENDING+('pending_draws',))
        # Also checks query segments, work owners and unconsumed timing rows,
        # which are not all exposed by the pending counters.
        native.configure_frame_slots(3)
        with pytest.raises(RuntimeError, match='missing presented target'):
            native.read_presented(identifier, 0, 0, *SIZE)


def test_assertion_failure_control_drains_owned_rows_before_restoring_slots(request):
    scene = None
    with pytest.raises(AssertionError, match='expected cleanup control'):
        with one_slot_scene(request.node.name) as scene:
            begin(scene, 901, True)
            scene.native.diagnostic_submission_controls(True, '')
            submit(scene)
            assert record(scene, 'cleanup-control-held-producer')['pending_tickets'] == 1
            raise AssertionError('expected cleanup control')
    assert scene is not None
    cleanup = json.loads((scene.output/'owned-cleanup.json').read_text())
    slots = json.loads((scene.output/'slot-cleanup.json').read_text())
    assert 'expected cleanup control' in cleanup['original_exception']
    assert cleanup['cleanup_failures'] == slots['cleanup_failures'] == []
    assert len(cleanup['terminal_receipts']) == len(cleanup['terminal_gpu']) == 1
    assert cleanup['terminal_receipts'][0]['frame_id'] == cleanup['terminal_gpu'][0]['frame_id'] == 901
    assert scene.native.probe()['frame_slots'] == slots['original_slots']
    scene.native.configure_frame_slots(slots['original_slots'])
