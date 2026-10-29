# SPDX-License-Identifier: AGPL-3.0-only
"""Query validation must precede any destructive GLIR drain."""
from types import SimpleNamespace

import numpy as np
import pytest
import vispy
from vispy.gloo import context
from vispy.gloo.dawn_parser import get_gl_parameter


@pytest.fixture
def transport(monkeypatch):
    calls = []
    canvas = SimpleNamespace(_closed=False, _backend=SimpleNamespace(_dawn_canvas_id=7),
                             context=SimpleNamespace(flush_commands=lambda: calls.append('flush')))
    native = SimpleNamespace(state_query_contract_version=1,
                             state_parameter=lambda cid, code: calls.append((cid, code)) or (0, 1),
                             device_info=lambda: calls.append('device') or {})
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    monkeypatch.setattr(context, 'get_current_canvas', lambda: canvas)
    return calls, canvas, native


@pytest.mark.parametrize('version', [None, 0, 2])
def test_old_or_unknown_native_query_contract_preserves_pending_work(transport, version):
    calls, _, native = transport
    if version is None:
        del native.state_query_contract_version
    else:
        native.state_query_contract_version = version
    with pytest.raises(RuntimeError, match='matching native state-query'):
        get_gl_parameter(0x0B72)
    assert calls == []


def test_missing_query_entry_point_preserves_pending_work(transport):
    calls, _, native = transport
    del native.state_parameter
    with pytest.raises(RuntimeError, match='matching native state-query'):
        get_gl_parameter(0x0B72)
    assert calls == []


@pytest.mark.parametrize('code', [True, np.bool_(False), 1.25, '2930', object(), -1, 999999, 0x0BD0])
def test_invalid_or_unsupported_selector_has_no_observation_effects(transport, code):
    calls, _, _ = transport
    with pytest.raises((TypeError, RuntimeError)):
        get_gl_parameter(code)
    assert calls == []


def test_admitted_selector_drains_once_before_native_snapshot(transport):
    calls, _, _ = transport
    assert get_gl_parameter(np.int32(0x0B72)) == (0, 1)
    assert calls == ['flush', (7, 0x0B72)]


def test_valid_query_propagates_queued_failure_without_snapshot(transport):
    calls, canvas, _ = transport
    def fail():
        calls.append('committed-prefix')
        raise RuntimeError('queued failure')
    canvas.context.flush_commands = fail
    with pytest.raises(RuntimeError, match='queued failure'):
        get_gl_parameter(0x0B72)
    assert calls == ['committed-prefix']


@pytest.mark.parametrize('state', ['absent', 'closed', 'missing-owner'])
def test_invalid_owner_does_not_drain_or_invent_state(transport, monkeypatch, state):
    calls, canvas, _ = transport
    if state == 'absent':
        monkeypatch.setattr(context, 'get_current_canvas', lambda: None)
    elif state == 'closed':
        canvas._closed = True
    else:
        canvas._backend._dawn_canvas_id = 0
    with pytest.raises(RuntimeError, match='current Dawn canvas'):
        get_gl_parameter(0x0B72)
    assert calls == []


@pytest.mark.parametrize('filterable', [True, False])
def test_texture_float_is_advertised_only_when_float32_textures_are_filterable(transport, filterable):
    # Hosts that see texture_float upload linear-filtered float32 textures (W1).
    _, _, native = transport
    native.device_info = lambda: {'max_texture_dimension_2d': 8192, 'float32_filterable': filterable}
    extensions = get_gl_parameter(7939)  # GL_EXTENSIONS
    assert ('texture_float' in extensions) is filterable
    assert 'GL_ARB_texture_non_power_of_two' in extensions
    native.device_info = lambda: {'max_texture_dimension_2d': 8192}  # an older native answer: no claim
    assert 'texture_float' not in get_gl_parameter(7939)
