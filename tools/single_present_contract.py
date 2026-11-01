# SPDX-License-Identifier: AGPL-3.0-only
"""Current single-present telemetry criteria; frozen historical criteria stay intact.

These are regression assertions, not a release admission or a tolerance rule.
Qt's paint-token guard defers autoswap until the final alpha-complete present.
Public readback uses presentation-free finish, followed by its own copy.
"""
import math

from tools.fixture_native_paint_frames import RESIDENT as RESIDENT_COUNTERS

UNSUBMITTED_INDEX = 2**64 - 1
HEADLESS_CAPTURE = dict(submissions=3, pass_kinds=['clear', 'present_capture'],
                        pass_submission_indices=[0, 2], implicit_presents=0)


def layout(intermediate=False):
    return dict(submissions=3 if intermediate else 2, presents=1,
        last_present=2 if intermediate else 1, native_draws=3, uniform_bytes=32,
        pass_kinds=['clear', 'scene', 'clear', 'surface_conversion'],
        pass_submission_indices=[0, 0, 1, 2] if intermediate else [0, 0, 0, 1])


def _owner(row):
    assert row['frame_scope'] == 'qt_paint'
    assert type(row['paint_token']) is int and row['paint_token'] > 0
    assert row['ownership_closed'] is True and row['ownership_retired'] is True
    for name in ('submission_count', 'present_count', 'last_present_submission_index'):
        assert type(row[name]) is int and row[name] >= 0, name


def check_success(row, before, *, intermediate=False):
    """Require both owned receipt counts and actual global deltas, without rebasing."""
    expected = layout(intermediate)
    _owner(row)
    assert row['status'] == 'success' and not row['error']
    assert row['presented'] is True
    assert row['counters_captured'] is True and row['counter_capture'] == 'submission'
    assert row['submission_count'] == expected['submissions']
    assert row['present_count'] == expected['presents']
    assert row['last_present_submission_index'] == expected['last_present']
    counters = row['counters']
    for name, delta in [('dawn_queue_submits', expected['submissions']),
                        ('application_presents', 1), ('draw_calls', 1),
                        ('native_draw_calls', expected['native_draws']),
                        ('uniform_upload_bytes', expected['uniform_bytes'])]:
        assert type(counters[name]) is int and type(before[name]) is int
        assert counters[name] - before[name] == delta, name
    for name in RESIDENT_COUNTERS:
        assert counters[name] == before[name], name
    assert counters['buffer_upload_cpu_ns'] >= before['buffer_upload_cpu_ns']
    assert 0 < row['submit_latency_ns'] <= row['completion_latency_ns']
    assert row['completion_timestamp_ns'] > row['completion_latency_ns']


def check_timing(gpu, row, *, intermediate=False):
    expected = layout(intermediate)
    assert gpu['status'] == 'success' and not gpu['error']
    for name in ('frame_id', 'frame_scope', 'paint_token', 'submission_count',
                 'last_present_submission_index'):
        assert gpu[name] == row[name], name
    passes = gpu['passes']
    assert [part['kind'] for part in passes] == expected['pass_kinds']
    assert [part['submission_index'] for part in passes] == expected['pass_submission_indices']
    quantum = gpu['quantization_ns']
    assert not isinstance(quantum, bool) and math.isfinite(quantum) and quantum >= 0
    for part in passes:
        assert 0 <= part['begin_ns'] <= part['end_ns']
        assert part['elapsed_ns'] == part['end_ns'] - part['begin_ns']
        if quantum:
            assert part['begin_ns'] % quantum == part['end_ns'] % quantum == 0
    assert gpu['pass_sum_ns'] == sum(part['elapsed_ns'] for part in passes)
    assert gpu['render_span_ns'] == max(part['end_ns'] for part in passes) - min(part['begin_ns'] for part in passes)


def check_fifo(rows, frame_ids):
    assert [row['frame_id'] for row in rows] == list(frame_ids)
    assert len({row['frame_id'] for row in rows}) == len(rows)
    assert len({row['paint_token'] for row in rows}) == len(rows)
    for row in rows:
        _owner(row)


def check_failed_before_present(row, status):
    """An autoswap callback is not proof of an intermediate Surface.Present.

This validates owned terminal fields only. Callers must retain and explain
global counter deltas separately; this function never subtracts earlier work.
"""
    _owner(row)
    assert status in ('failed', 'device_lost', 'cancelled')
    assert row['status'] == status and row['error']
    assert row['presented'] is False and row['present_count'] == 0
    assert row['last_present_submission_index'] == UNSUBMITTED_INDEX
    assert row['counters_captured'] is bool(row['submission_count'])
    assert row['counter_capture'] == ('submission' if row['submission_count'] else 'unavailable_unsubmitted')


def check_win32_detach_accounting(before, retire_before, retire_after, after, row):
    """Keep Win32's explicit retirement drain separate from owned paint work.

    retire_surface performs an empty queue submit and a deliberate wait.
    The later final present request can capture offscreen pixels, incrementing
    application_presents without a successful Surface.Present. None of these
    costs is erased or relabeled as successful resident paint work.
    """
    check_failed_before_present(row, 'failed')
    assert row['submission_count'] == 2
    cleanup = dict(dawn_queue_submits=1, application_presents=0, completion_waits=1, finish_calls=0)
    for name, delta in cleanup.items():
        assert retire_before[name] == before[name], name
        assert retire_after[name]-retire_before[name] == delta, name
    expected = dict(dawn_queue_submits=row['submission_count']+1,
                    application_presents=1, completion_waits=1, finish_calls=0)
    for name, delta in expected.items():
        assert after[name]-before[name] == delta, name
        assert row['counters'][name] == after[name], name
