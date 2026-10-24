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
