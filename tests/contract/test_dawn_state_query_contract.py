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


@pytest.mark.parametrize('viewport,message', [
    ((-1, 0, 3, 4), 'rectangle exceeds target bounds'),
    ((0, -1, 3, 4), 'rectangle exceeds target bounds'),
    ((0, 0, -1, 4), 'empty target'),
    ((0, 0, 3, -1), 'empty target'),
    ((0, 0, 0, 4), 'empty target'),
    ((0, 0, 3, 0), 'empty target'),
])
def test_invalid_readback_geometry_preserves_pending_commands(monkeypatch, viewport, message):
    from vispy.gloo.dawn_parser import read_pixels_dawn
    pending = [('FUNC', 'glClearColor', 1., 0., 0., 1.)]
    snapshot = list(pending)
    calls = []
    def finish():
        calls.append('finish')
        pending.clear()
    canvas = SimpleNamespace(_backend=SimpleNamespace(_dawn_canvas_id=7),
                             context=SimpleNamespace(finish=finish))
    def readback(*args):
        calls.append('readback')
        raise RuntimeError(message)
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(read_pixels=readback), raising=False)
    monkeypatch.setattr(context, 'get_current_canvas', lambda: canvas)
    with pytest.raises(RuntimeError, match=message):
        read_pixels_dawn(viewport, True, 'color')
    assert calls == []
    assert pending == snapshot


def test_valid_readback_geometry_keeps_finish_then_snapshot_order(monkeypatch):
    from vispy.gloo.dawn_parser import read_pixels_dawn
    calls = []
    canvas = SimpleNamespace(_backend=SimpleNamespace(_dawn_canvas_id=7),
                             context=SimpleNamespace(finish=lambda: calls.append('finish')))
    expected = np.zeros((4, 3, 4), np.uint8)
    def readback(*args):
        calls.append(args)
        return expected
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(read_pixels=readback), raising=False)
    monkeypatch.setattr(context, 'get_current_canvas', lambda: canvas)
    actual = read_pixels_dawn((0, 0, 3, 4), True, 'color', copy=False)
    assert actual is expected
    assert calls == ['finish', (7, 0, 0, 3, 4, True, False, 'color')]


@pytest.mark.parametrize('axis', range(4))
@pytest.mark.parametrize('value', [-(2**31) - 1, 2**31])
def test_readback_native_integer_overflow_preserves_pending_commands(monkeypatch, axis, value):
    from vispy.gloo.dawn_parser import read_pixels_dawn
    pending = [('FUNC', 'glClearColor', 1., 0., 0., 1.)]
    snapshot = list(pending)
    calls = []
    def finish():
        calls.append('finish')
        pending.clear()
    def readback(*args):
        calls.append('readback')
        raise TypeError('native integer conversion failed')
    canvas = SimpleNamespace(_backend=SimpleNamespace(_dawn_canvas_id=7),
                             context=SimpleNamespace(finish=finish))
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(read_pixels=readback), raising=False)
    monkeypatch.setattr(context, 'get_current_canvas', lambda: canvas)
    viewport = [0, 0, 3, 4]
    viewport[axis] = value
    with pytest.raises(TypeError):
        read_pixels_dawn(viewport, True, 'color')
    assert calls == []
    assert pending == snapshot


@pytest.mark.parametrize('axis', range(4))
def test_readback_representable_upper_bounds_still_reach_native(monkeypatch, axis):
    from vispy.gloo.dawn_parser import read_pixels_dawn
    calls = []
    canvas = SimpleNamespace(_backend=SimpleNamespace(_dawn_canvas_id=7),
                             context=SimpleNamespace(finish=lambda: calls.append('finish')))
    def readback(*args):
        calls.append('readback')
        raise RuntimeError('read_pixels rectangle exceeds target bounds')
    monkeypatch.setattr(vispy, '_dawn', SimpleNamespace(read_pixels=readback), raising=False)
    monkeypatch.setattr(context, 'get_current_canvas', lambda: canvas)
    viewport = [0, 0, 3, 4]
    viewport[axis] = 2**31 - 1
    with pytest.raises(RuntimeError, match='rectangle exceeds target bounds'):
        read_pixels_dawn(viewport, True, 'color')
    assert calls == ['finish', 'readback']
