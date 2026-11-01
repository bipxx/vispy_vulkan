# SPDX-License-Identifier: AGPL-3.0-only
"""Current Qt single-present regression scenarios, beside frozen two-present tests.

Author criteria and CPU negative controls before capturing a new artifact.
Historical captures never become admission evidence under these assertions.
"""
import copy
import os
from pathlib import Path
import time

import numpy as np
import pytest

from tools import single_present_contract as current
from tools.fixture_native_paint_frames import (
    Evidence, FRAME_IDS, PHASES, PaintHarness, QUERY_COUNTERS, RESIDENT, SIZE,
    expected_pixels, presented_bgra_to_rgba,
)

pytestmark = pytest.mark.gpu


class CurrentEvidence(Evidence):
    def __init__(self, name):
        base = os.environ.get('VISPY_NATIVE_PAINT_EVIDENCE')
        assert base, 'provide a fresh managed evidence path'
        self.output = Path(base)/name
        self.output.mkdir(parents=True, exist_ok=False)
        self.value = dict(scope=dict(revision='qt-single-present-v1',
            normal=current.layout(), intermediate=current.layout(True),
            headless_capture=copy.deepcopy(current.HEADLESS_CAPTURE),
            historical_criteria_unchanged=True, admission_claimed=False),
            issued=[], events=[], raw_batches=[], snapshots={}, GPU_used=False)
        self.save()


class CurrentPaintHarness(PaintHarness):
    def after_autoswap(self, event):
        if self.action == 'detach' and self.requested is not None:
            frame_id = self.requested
            receipts, gpu = self.poll_native('inside-paint-after-autoswap')
            self.evidence.event('after-existing-autoswap', frame_id=frame_id,
                                probe=dict(self.native.probe()))
            assert all(row.get('frame_id') != frame_id for row in receipts+gpu), 'open paint published a terminal record'
            # No polling/event processing sits between either probe and the
            # actual retirement call; its costs have their own direct witness.
            self.retire_before = dict(self.native.probe())
            self.native.clear_surface(self.canvas_id)
            self.retire_after = dict(self.native.probe())
            self.evidence.value['snapshots'].update(retire_before=self.retire_before,
                                                    retire_after=self.retire_after)
            self.evidence.event('actual-surface-detached', frame_id=frame_id,
                                surface=dict(self.native.benchmark_surface_info(self.canvas_id)))
            self.evidence.save()
        else:
            super().after_autoswap(event)


def snapshot(harness, name):
    value = dict(harness.native.probe())
    harness.evidence.value['snapshots'][name] = copy.deepcopy(value)
    harness.evidence.save()
    return value


def bounded(harness, name):
    value = snapshot(harness, name)
    for field in ('pending_tickets', 'queued_frames', 'pending_timestamp_frames'):
        assert 0 <= value[field] <= value['frame_slots'], field
    return value


@pytest.fixture
def paint(request):
    assert os.environ.get('VISPY_QT_PRESENTATION') == 'native', 'select the actual native presentation profile'
    assert os.environ.get('VISPY_NATIVE_PAINT_EVIDENCE'), 'provide a fresh managed evidence path'
    opened = []

    def create(**options):
        evidence = CurrentEvidence(request.node.name)
        harness = CurrentPaintHarness.__new__(CurrentPaintHarness)
        opened.append((harness, evidence))
        harness.__init__(evidence, **options)
        evidence.value['successor_contract'] = 'qt-single-present-v1'
        # Cold native/Qt work is allowed before the resident baseline. Drain
        # actual events without suppressing exposes or subtracting counters.
        deadline = time.monotonic() + 5
        while True:
            harness.canvas.app.process_events()
            harness.native.process_events()
            value = bounded(harness, 'cold-drain')
            if (not any(value[field] for field in ('pending_tickets', 'queued_frames', 'pending_timestamp_frames'))
                    and not harness.canvas._backend._dawn_paint_deferred):
                break
            assert time.monotonic() < deadline, 'cold Qt work did not retire'
            time.sleep(.001)
        return harness

    try:
        yield create
    finally:
        for harness, evidence in reversed(opened):
            if hasattr(harness, 'evidence'):
                harness.close()
            evidence.save()


def drain(harness):
    deadline = time.monotonic() + 10
    while True:
        harness.canvas.app.process_events()
        harness.collect('success-drain', 'measured')
        bounded(harness, 'drain')
        if set(harness.completions.results) == set(FRAME_IDS) and (
                not harness.collector.gpu_metadata['enabled'] or
                set(harness.collector.gpu_frames.results) == set(FRAME_IDS)):
            return
        assert time.monotonic() < deadline, 'owned paints did not retire'
        time.sleep(.001)


@pytest.mark.parametrize('queries,vsync,intermediate', [
    (False, False, False), (True, False, False), (True, True, False), (True, False, True),
], ids=['queries-off', 'queries-on', 'fifo', 'actual-intermediate'])
def test_single_final_qt_present_owns_every_submission_and_alpha_tail(paint, queries, vsync, intermediate):
    harness = paint(queries=queries, vsync=vsync, intermediate=intermediate,
                    frame_slots=1 if vsync else None)
    before = snapshot(harness, 'resident-before')
    for frame_id in FRAME_IDS:
        deadline = time.monotonic() + 10
        while not harness.native.frame_ready(harness.canvas_id):
            harness.canvas.app.process_events()
            harness.collect('backpressure', PHASES[frame_id])
            bounded(harness, 'backpressure')
            assert time.monotonic() < deadline, 'nonblocking capacity did not recover'
            time.sleep(.001)
        harness.issue(frame_id, PHASES[frame_id])
        harness.dispatch(frame_id)
        harness.collect('after-real-paint', PHASES[frame_id])
        bounded(harness, f'after-{frame_id}')
    drain(harness)
    samples = harness.completions.samples('warmup') + harness.completions.samples('measured')
    assert harness.completions.issued == PHASES
    current.check_fifo(harness.raw_receipts, FRAME_IDS)
    assert harness.seen == {frame_id: 1 for frame_id in FRAME_IDS}
    if queries:
        harness.collector.gpu_frames.join(samples)
        assert [row['frame_id'] for row in harness.raw_gpu] == list(FRAME_IDS)
    else:
        assert harness.raw_gpu == []
    for row in samples:
        current.check_success(row, harness.scene_before[row['frame_id']], intermediate=intermediate)
        if queries:
            current.check_timing(row['gpu_timing'], row, intermediate=intermediate)
    assert harness.collector.verify_scope(samples) is True
    after = snapshot(harness, 'resident-after')
    for field in RESIDENT:
        assert after[field] == before[field], field
    expected = current.layout(intermediate)
    for field, delta in [('dawn_queue_submits', 12*expected['submissions']),
                         ('application_presents', 12), ('draw_calls', 12),
                         ('native_draw_calls', 12*expected['native_draws']),
                         ('uniform_upload_bytes', 12*expected['uniform_bytes'])]:
        assert after[field]-before[field] == delta, field
    for field in QUERY_COUNTERS:
        assert after[field]-before[field] == (12*expected['submissions'] if queries else 0), field
    assert after['pending_tickets'] == after['queued_frames'] == after['pending_timestamp_frames'] == 0
    if queries:
        assert after['render_passes']-before['render_passes'] == sum(len(row['passes']) for row in harness.raw_gpu)
    assert harness.native.benchmark_completions(harness.canvas_id) == []
    assert harness.native.benchmark_gpu_timings(harness.canvas_id) == []
    harness.evidence.value.update(samples=copy.deepcopy(samples), boundary=copy.deepcopy(harness.collector.boundary),
        uniform_inclusive_buffer_upload_cpu_ns=after['buffer_upload_cpu_ns']-before['buffer_upload_cpu_ns'],
        observed_deferred_frames=after['deferred_frames']-before['deferred_frames'],
        deferred_path_qualified=after['deferred_frames']>before['deferred_frames'])
    harness.evidence.save()
    # Explicit quality capture happens only after resident/no-wait assertions.
    raw = np.asarray(harness.native.read_presented(harness.canvas_id, 0, 0, *SIZE)).copy()
    np.save(harness.evidence.output/'final-bgra.npy', raw, allow_pickle=False)
    image = presented_bgra_to_rgba(raw)
    np.save(harness.evidence.output/'final-rgba.npy', image, allow_pickle=False)
    np.testing.assert_array_equal(image, expected_pixels(FRAME_IDS[-1]))


@pytest.mark.parametrize('action,status', [('error', 'failed'), ('loss', 'device_lost'), ('detach', 'failed')])
def test_failure_before_final_present_cannot_be_admitted_as_visible_success(paint, action, status):
    harness = paint(queries=True)
    before = snapshot(harness, 'before-failure')
    harness.issue(0, 'warmup', action=action)
    if action == 'detach':
        harness.dispatch(0)
    else:
        match = 'glLineWidth' if action == 'error' else 'intentional native-paint device loss'
        with pytest.raises(RuntimeError, match=match):
            harness.dispatch(0)
    deadline = time.monotonic()+10
    while not harness.raw_receipts or not harness.raw_gpu:
        harness.poll_native('terminal-drain')
        assert time.monotonic() < deadline, 'terminal ownership did not retire'
        time.sleep(.001)
    assert len(harness.raw_receipts) == len(harness.raw_gpu) == 1
    row, gpu = harness.raw_receipts[0], harness.raw_gpu[0]
    current.check_failed_before_present(row, status)
    assert gpu['frame_id'] == row['frame_id'] == 0
    gpu_status = 'device_lost' if status == 'device_lost' else 'submission_error'
    assert gpu['status'] == gpu_status and gpu['error'] and gpu['passes'] == []
    assert gpu['paint_token'] == row['paint_token'] and gpu['frame_scope'] == row['frame_scope']
    assert gpu['submission_count'] == row['submission_count']
    assert gpu['last_present_submission_index'] == row['last_present_submission_index']
    after = snapshot(harness, 'after-failure')
    assert after['pending_tickets'] == after['queued_frames'] == after['pending_timestamp_frames'] == 0
    # Keep global and owned deltas distinct. Win32 surface detachment may
    # deliberately retire a surface using a wait and empty queue submission.
    # Direct before/after snapshots prove that cleanup separately below.
    harness.evidence.value['terminal_global_deltas'] = {name: after[name]-before[name]
        for name in ('dawn_queue_submits', 'application_presents', 'completion_waits')}
    harness.evidence.value['terminal_owned_submissions'] = row['submission_count']
    harness.evidence.save()
    from tools.benchmark_frames import InstrumentationUnavailable
    with pytest.raises(RuntimeError, match='failed or unpresented'):
        harness.completions.collect([row], 'warmup')
    harness.collector.gpu_frames.collect([gpu])
    with pytest.raises(InstrumentationUnavailable):
        harness.collector.gpu_frames.join([copy.deepcopy(row)])
    if action == 'detach':
        current.check_win32_detach_accounting(before, harness.retire_before,
                                             harness.retire_after, after, row)
    else:
        assert row['submission_count'] == 0
        for name in ('dawn_queue_submits', 'application_presents', 'completion_waits', 'finish_calls'):
            assert after[name] == before[name], name
    assert after['finish_calls'] == before['finish_calls']


def test_public_headless_capture_keeps_finish_presentation_free_and_tracks_all_submits():
    from vispy import app, gloo, _dawn
    evidence = CurrentEvidence('headless-presentation-free-capture')
    evidence.value['GPU_used'] = True
    evidence.save()
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), show=False)
    identifier = canvas._backend._dawn_canvas_id
    try:
        canvas.set_current()
        gloo.clear(color=(0, 0, 0, 1))
        canvas.context.flush_commands()
        _dawn.present(identifier)
        _dawn.finish(identifier)
        configuration = _dawn.benchmark_configure_gpu_timing(identifier)
        surface = dict(_dawn.benchmark_surface_info(identifier))
        evidence.value.update(query_configuration=dict(configuration), surface=surface)
        evidence.save()
        assert configuration['enabled'] and configuration['supported']
        assert surface['attached'] is False
        before = dict(_dawn.probe())
        evidence.value['snapshots']['before-request'] = before
        evidence.save()
        _dawn.benchmark_begin_frame(identifier, 0)
        gloo.clear(color=(1, 0, 0, 1))
        canvas.context.flush_commands()
        image = np.asarray(gloo.read_pixels((0, 0, 8, 8))).copy()
        np.save(evidence.output/'readback-rgba.npy', image, allow_pickle=False)
        copied = dict(_dawn.probe())
        evidence.value['snapshots']['after-readback'] = copied
        evidence.save()
        np.testing.assert_array_equal(image, np.full((8, 8, 4), [255, 0, 0, 255], dtype=np.uint8))
        assert copied['application_presents'] == before['application_presents']
        assert copied['dawn_queue_submits']-before['dawn_queue_submits'] == 2
        early_rows = list(_dawn.benchmark_completions(identifier))
        early_maps = list(_dawn.benchmark_gpu_timings(identifier))
        evidence.batch('readback-while-request-open', early_rows, early_maps)
        assert early_rows == early_maps == [], 'readback closed the unpresented request early'
        _dawn.present(identifier)
        evidence.value['snapshots']['after-explicit-present'] = dict(_dawn.probe())
        evidence.save()
        receipts, maps = [], []
        deadline = time.monotonic()+5
        while not receipts or not maps:
            batch = list(_dawn.benchmark_completions(identifier))
            gpu_batch = list(_dawn.benchmark_gpu_timings(identifier))
            evidence.batch('headless-retirement', batch, gpu_batch)
            receipts.extend(batch)
            maps.extend(gpu_batch)
            assert time.monotonic() < deadline, 'headless capture did not retire'
            time.sleep(.001)
        assert len(receipts) == len(maps) == 1
        row, gpu = receipts[0], maps[0]
        expected = current.HEADLESS_CAPTURE
        assert row['frame_id'] == gpu['frame_id'] == 0
        assert row['frame_scope'] == gpu['frame_scope'] == 'native_present'
        assert row['paint_token'] == gpu['paint_token'] == 0
        assert row['status'] == gpu['status'] == 'success'
        assert not row['error'] and not gpu['error']
        assert gpu['device_generation'] == configuration['device_generation']
        assert gpu['quantization_ns'] == configuration['quantization_ns']
        assert row['ownership_closed'] is True and row['ownership_retired'] is True
        assert row['counters_captured'] is True and row['counter_capture'] == 'submission'
        assert row['submission_count'] == gpu['submission_count'] == expected['submissions']
        assert row['presented'] is False and row['present_count'] == 0
        assert row['last_present_submission_index'] == current.UNSUBMITTED_INDEX
        assert gpu['last_present_submission_index'] == row['last_present_submission_index']
        assert row['counters']['dawn_queue_submits']-before['dawn_queue_submits'] == expected['submissions']
        assert row['counters']['application_presents']-before['application_presents'] == 1
        assert [part['kind'] for part in gpu['passes']] == expected['pass_kinds']
        assert [part['submission_index'] for part in gpu['passes']] == expected['pass_submission_indices']
        assert gpu['pass_sum_ns'] == sum(part['elapsed_ns'] for part in gpu['passes'])
        assert gpu['render_span_ns'] == max(part['end_ns'] for part in gpu['passes'])-min(part['begin_ns'] for part in gpu['passes'])
        for part in gpu['passes']:
            assert 0 <= part['begin_ns'] <= part['end_ns']
            assert part['elapsed_ns'] == part['end_ns']-part['begin_ns']
            if gpu['quantization_ns']:
                assert part['begin_ns'] % gpu['quantization_ns'] == part['end_ns'] % gpu['quantization_ns'] == 0
    finally:
        evidence.save()
        canvas.close()
