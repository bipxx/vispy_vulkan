# SPDX-License-Identifier: AGPL-3.0-only
"""Negative controls for the current single-present Qt telemetry contract."""
from copy import deepcopy

import pytest

from tools import single_present_contract as current


def sample(intermediate=False):
    before = {name: 0 for name in current.RESIDENT_COUNTERS}
    before.update(dawn_queue_submits=10, application_presents=20, draw_calls=30,
                  native_draw_calls=40, uniform_upload_bytes=50, buffer_upload_cpu_ns=60)
    after = dict(before, dawn_queue_submits=13 if intermediate else 12,
                 application_presents=21, draw_calls=31, native_draw_calls=43,
                 uniform_upload_bytes=82, buffer_upload_cpu_ns=61)
    row = dict(frame_id=0, frame_scope='qt_paint', paint_token=7, status='success', error='',
        presented=True, ownership_closed=True, ownership_retired=True,
        counters_captured=True, counter_capture='submission', counters=after,
        submission_count=3 if intermediate else 2, present_count=1,
        last_present_submission_index=2 if intermediate else 1,
        submit_latency_ns=100, completion_latency_ns=200, completion_timestamp_ns=300)
    return row, before


def timing(row, intermediate=False):
    indices = [0, 0, 1, 2] if intermediate else [0, 0, 0, 1]
    passes = [dict(kind=kind, submission_index=index, begin_ns=position*10,
                   end_ns=position*10+2, elapsed_ns=2)
              for position, (kind, index) in enumerate(zip(
                  ['clear', 'scene', 'clear', 'surface_conversion'], indices))]
    return dict(frame_id=row['frame_id'], frame_scope='qt_paint', paint_token=row['paint_token'],
        status='success', error='', submission_count=row['submission_count'],
        last_present_submission_index=row['last_present_submission_index'], passes=passes,
        quantization_ns=0, pass_sum_ns=8, render_span_ns=32)


@pytest.mark.parametrize('intermediate', [False, True])
def test_single_present_layout_has_one_surface_conversion_and_all_owned_work(intermediate):
    layout = current.layout(intermediate)
    assert layout == dict(submissions=3 if intermediate else 2, presents=1,
        last_present=2 if intermediate else 1, native_draws=3, uniform_bytes=32,
        pass_kinds=['clear', 'scene', 'clear', 'surface_conversion'],
        pass_submission_indices=[0, 0, 1, 2] if intermediate else [0, 0, 0, 1])
    row, before = sample(intermediate)
    current.check_success(row, before, intermediate=intermediate)
    current.check_timing(timing(row, intermediate), row, intermediate=intermediate)


@pytest.mark.parametrize('field,value', [
    ('present_count', 0), ('present_count', 2), ('present_count', True),
    ('submission_count', 1), ('submission_count', 3), ('last_present_submission_index', 0),
    ('ownership_closed', False), ('ownership_retired', False), ('presented', False),
    ('counters_captured', False), ('counter_capture', 'poll'), ('paint_token', 0),
    ('paint_token', True), ('frame_scope', 'native_present'), ('status', 'failed'),
])
def test_single_present_success_rejects_missing_extra_or_premature_work(field, value):
    row, before = sample()
    row[field] = value
    with pytest.raises(AssertionError):
        current.check_success(row, before)


@pytest.mark.parametrize('field', [
    'dawn_queue_submits', 'application_presents', 'draw_calls', 'native_draw_calls',
    'uniform_upload_bytes', 'geometry_upload_bytes', 'completion_waits', 'pipeline_misses',
])
def test_single_present_requires_actual_counter_accounting_and_resident_reuse(field):
    row, before = sample()
    row['counters'][field] += 1
    with pytest.raises(AssertionError):
        current.check_success(row, before)


@pytest.mark.parametrize('damage', ['extra-present', 'missing-alpha-clear', 'wrong-submission',
                                   'other-owner', 'wrong-duration', 'bad-quantum'])
def test_single_present_queries_cannot_hide_extra_passes_or_other_owners(damage):
    row, _ = sample()
    gpu = timing(row)
    if damage == 'extra-present':
        gpu['passes'].append(deepcopy(gpu['passes'][-1]))
    elif damage == 'missing-alpha-clear':
        del gpu['passes'][2]
    elif damage == 'wrong-submission':
        gpu['passes'][2]['submission_index'] = 1
    elif damage == 'other-owner':
        gpu['paint_token'] += 1
    elif damage == 'wrong-duration':
        gpu['passes'][0]['elapsed_ns'] += 1
    else:
        gpu['quantization_ns'] = 4
    with pytest.raises(AssertionError):
        current.check_timing(gpu, row)


def test_single_present_fifo_rejects_duplicate_out_of_order_or_reused_owners():
    first, _ = sample()
    second = dict(first, frame_id=1, paint_token=8)
    current.check_fifo([first, second], [0, 1])
    for rows in ([first, first], [second, first], [first, dict(second, paint_token=7)]):
        with pytest.raises(AssertionError):
            current.check_fifo(rows, [0, 1])


@pytest.mark.parametrize('submissions', [0, 2])
def test_single_present_failures_never_claim_a_deferred_autoswap_present(submissions):
    row = dict(frame_scope='qt_paint', paint_token=7, status='failed', error='actual failure',
        presented=False, ownership_closed=True, ownership_retired=True,
        submission_count=submissions, present_count=0,
        last_present_submission_index=current.UNSUBMITTED_INDEX,
        counters_captured=bool(submissions),
        counter_capture='submission' if submissions else 'unavailable_unsubmitted')
    current.check_failed_before_present(row, 'failed')
    for changed in (dict(row, status='success'), dict(row, present_count=1, presented=True),
                    dict(row, ownership_retired=False)):
        with pytest.raises(AssertionError):
            current.check_failed_before_present(changed, 'failed')


def test_current_capture_contract_keeps_readback_presentation_free():
    assert current.HEADLESS_CAPTURE == dict(submissions=3, pass_kinds=['clear', 'present_capture'],
        pass_submission_indices=[0, 2], implicit_presents=0)


@pytest.mark.parametrize('damage', [None, 'hidden-submit', 'hidden-present', 'hidden-wait',
                                   'wrong-owned-count', 'rebased-baseline', 'stale-receipt',
                                   'coherent-extra-owned', 'hidden-finish'])
def test_win32_detach_costs_are_explicit_and_never_normalized_away(damage):
    before = dict(dawn_queue_submits=10, application_presents=20, completion_waits=30, finish_calls=40)
    retire_before = dict(before)
    retire_after = dict(dawn_queue_submits=11, application_presents=20, completion_waits=31, finish_calls=40)
    after = dict(dawn_queue_submits=13, application_presents=21, completion_waits=31, finish_calls=40)
    row = dict(frame_scope='qt_paint', paint_token=7, status='failed', error='surface detached',
        presented=False, ownership_closed=True, ownership_retired=True,
        submission_count=2, present_count=0, last_present_submission_index=current.UNSUBMITTED_INDEX,
        counters_captured=True, counter_capture='submission', counters=dict(after))
    if damage == 'hidden-submit':
        after['dawn_queue_submits'] += 1
    elif damage == 'hidden-present':
        retire_after['application_presents'] += 1
    elif damage == 'hidden-wait':
        after['completion_waits'] += 1
    elif damage == 'wrong-owned-count':
        row['submission_count'] += 1
    elif damage == 'rebased-baseline':
        retire_before['dawn_queue_submits'] += 1
    elif damage == 'stale-receipt':
        row['counters']['dawn_queue_submits'] -= 1
    elif damage == 'coherent-extra-owned':
        row['submission_count'] += 1
        after['dawn_queue_submits'] += 1
        row['counters']['dawn_queue_submits'] += 1
    elif damage == 'hidden-finish':
        after['finish_calls'] += 1
    if damage is None:
        current.check_win32_detach_accounting(before, retire_before, retire_after, after, row)
    else:
        with pytest.raises(AssertionError):
            current.check_win32_detach_accounting(before, retire_before, retire_after, after, row)


__all__ = [name for name in globals() if name.startswith('test_')]
