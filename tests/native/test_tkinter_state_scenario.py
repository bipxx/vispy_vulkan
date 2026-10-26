# SPDX-License-Identifier: AGPL-3.0-only
"""The observed workflow must exercise real Tk and both native flush routes."""
import pytest

from tools.tkinter_state_scenario import run

pytestmark = pytest.mark.gpu


def test_real_tk_state_observer_scenario():
    result = run()
    assert result['status'] == 'PASS'
    assert [item['route'] for item in result['submissions']] == ['gloo.flush', 'glFlush']


def test_real_tk_resource_timer_observer_scenario():
    import gc
    from vispy import _dawn
    from tools.no_opengl.policy import LIVE_GAUGES
    from tools.tkinter_resource_scenario import run as resource_run
    gc.collect()
    _dawn.process_events()
    before = _dawn.probe()
    baseline = {key: before[key] for key in LIVE_GAUGES}
    result = resource_run()
    assert result['status'] == 'PASS' and result['shared'] and result['host_survived']
    assert result['timer_ticks'] == 1 and result['survivor_color'] == [0, 0, 255, 255]
    assert result['device_recovered']
    gc.collect()
    _dawn.process_events()
    after = _dawn.probe()
    assert all(after[key] <= baseline[key] for key in LIVE_GAUGES), {
        'before': baseline, 'after': {key: after[key] for key in LIVE_GAUGES}}
    # Device recreation may retire old shared caches; no new resource may remain.


def test_resource_timer_failure_keeps_original_error_and_retires_resources(monkeypatch):
    import gc
    import numpy as np
    from vispy import _dawn, gloo
    from tools.no_opengl.policy import LIVE_GAUGES
    from tools.tkinter_resource_scenario import run as resource_run
    original = gloo.Texture2D.set_data
    calls = []

    def upload(self, *args, **kwargs):
        calls.append(True)
        if args and np.array_equal(args[0], np.array([[[0, 255, 0, 255]]], np.uint8)):
            raise ValueError('intentional resource timer upload failure')
        return original(self, *args, **kwargs)

    gc.collect()
    _dawn.process_events()
    before = _dawn.probe()
    baseline = {key: before[key] for key in LIVE_GAUGES}
    monkeypatch.setattr(gloo.Texture2D, 'set_data', upload)
    with pytest.raises(ValueError, match='intentional resource timer upload failure'):
        resource_run()
    gc.collect()
    _dawn.process_events()
    state = _dawn.probe()
    after = {key: state[key] for key in LIVE_GAUGES}
    assert after == baseline, {'before': baseline, 'after': after}
    print({'resource_cleanup_baseline': baseline, 'resource_cleanup_after': after})


def test_composite_observed_failure_and_recovery_scenario():
    from tools.tkinter_failure_scenario import run
    result = run()
    assert result['status'] == 'PASS'
    from tools.no_opengl.functional import validate_tk_result
    assert validate_tk_result(result)['status'] == 'PASS_FUNCTIONAL_RESULT'
    import json
    print(json.dumps(result, sort_keys=True))
    resource = result['resource_failure_recovery']
    assert resource['injections'] == ['green-upload']
    assert resource['baseline'] == resource['after_failure']
    assert resource['recovery']['host_survived']
    progress = result['native_progress_failure_recovery']
    assert [item['callback_order'] for item in progress] == ['poll', 'draw']
    assert all(item['deliveries'] == item['injections'] == 1 for item in progress)
    submissions = result['submission_failure_recovery']
    assert [(v['route'], v['delayed_progress']) for v in submissions] == [
        ('gloo', False), ('gloo', True), ('raw', False), ('raw', True)]
    assert all(v['status'] == 'PASS' and v['host_preserved'] for v in submissions)


@pytest.mark.parametrize('fault', ['missing-injection', 'wrong-exception', 'failed-recovery', 'secondary-cleanup'])
def test_observed_failure_harness_rejects_incomplete_proof(monkeypatch, fault):
    from tools import tkinter_failure_scenario as scenario
    real = scenario._scenario('tkinter_resource_scenario')
    calls = []

    def substitute(**kwargs):
        calls.append(True)
        if fault == 'missing-injection':
            return {'status': 'PASS'}
        if fault == 'wrong-exception':
            raise ValueError('unrelated callback failure')
        if len(calls) == 1:
            try:
                return real(**kwargs)
            finally:
                if fault == 'secondary-cleanup':
                    kwargs['cleanup_report']['secondary_errors'] = 1
        return {'status': 'FAIL'}

    monkeypatch.setattr(scenario, '_scenario', lambda name: substitute)
    with pytest.raises(AssertionError):
        scenario._resource_failure()


@pytest.mark.parametrize('route', ['gloo', 'raw'])
@pytest.mark.parametrize('delayed', [False, True])
def test_observed_submission_capacity_and_retry(route, delayed):
    from tools.tkinter_failure_scenario import _submission_failure
    from vispy import _dawn
    previous = _dawn.probe()['frame_slots']
    result = _submission_failure(route, delayed)
    assert result['status'] == 'PASS' and result['host_preserved']
    assert result['restored_frame_slots'] == previous
    assert bool(result['early_progress']) == delayed


@pytest.mark.parametrize('route', ['gloo', 'raw'])
@pytest.mark.parametrize('fault', ['missing-error', 'wrong-error', 'missing-retry'])
def test_observed_submission_harness_rejects_missing_failure_or_retry(monkeypatch, route, fault):
    from vispy import _dawn, gloo
    from vispy.gloo import gl
    from tools.tkinter_failure_scenario import _submission_failure
    owner, name = (gloo, 'flush') if route == 'gloo' else (gl, 'glFlush')
    original = []
    calls = []

    def substitute():
        calls.append(True)
        if len(calls) == 2 and fault == 'wrong-error':
            raise RuntimeError('unrelated submission error')
        if len(calls) == 2 and fault == 'missing-error':
            try:
                return original[0]()
            except RuntimeError:
                return
        if len(calls) == 3 and fault == 'missing-retry':
            return
        return original[0]()

    configure = _dawn.configure_frame_slots

    def after_setup(slots):
        configure(slots)
        # Canvas construction reinstalls the raw GL proxy. Inject only after
        # setup has finished, immediately before the measured submissions.
        if slots == 1 and not original:
            original.append(getattr(owner, name))
            monkeypatch.setattr(owner, name, substitute)

    before = _dawn.probe()['frame_slots']
    monkeypatch.setattr(_dawn, 'configure_frame_slots', after_setup)
    with pytest.raises(AssertionError):
        _submission_failure(route, True)
    assert _dawn.probe()['frame_slots'] == before
    assert len(calls) >= (3 if fault == 'missing-retry' else 2)
