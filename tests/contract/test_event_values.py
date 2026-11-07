# SPDX-License-Identifier: AGPL-3.0-only
"""Finite installed event-model semantics; no GUI object or input delivery."""
import numpy as np
import pytest

from vispy import app
from vispy.app import KeyEvent, MouseEvent
from vispy.app.canvas import DrawEvent, ResizeEvent
from vispy.scene.events import SceneMouseEvent
from vispy.util import keys
from vispy.util.event import EmitterGroup, Event, EventEmitter
from vispy.visuals.transforms import STTransform


@pytest.fixture(autouse=True)
def no_gui_instances(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('CPU event acceptance must not construct a GUI object')
    for cls in (app.Application, app.Canvas, app.Timer):
        monkeypatch.setattr(cls, '__init__', forbidden)


@pytest.mark.parametrize('button', [None, 1, 2, 3])
def test_mouse_defaults_and_button_values(button):
    event = MouseEvent('mouse_press', button=button)
    assert event.type == 'mouse_press' and event.button == button
    np.testing.assert_array_equal(event.pos, [0, 0])
    np.testing.assert_array_equal(event.delta, [0., 0.])
    assert event.buttons == [] and event.modifiers == ()
    assert event.press_event is event.last_event is None
    assert not event.is_dragging and event.drag_events() is event.trail() is None
    assert isinstance(event.time, float)


@pytest.mark.parametrize('invalid', ['not-a-button', object()])
def test_invalid_button_rejects_then_valid_construction_recovers(invalid):
    with pytest.raises((TypeError, ValueError)):
        MouseEvent('mouse_press', button=invalid)
    assert MouseEvent('mouse_press', button=1).button == 1


def test_mouse_storage_native_identity_and_mutation_boundaries():
    position = np.array([3.5, -4.25]); delta = np.array([.5, -1.])
    buttons = [1, 2]; modifiers = [keys.SHIFT, keys.CONTROL]; native = object()
    event = MouseEvent('mouse_wheel', pos=position, delta=delta, buttons=buttons,
                       modifiers=modifiers, native=native, extra='payload')
    position[:] = 99; delta[:] = 99; modifiers.clear()
    np.testing.assert_array_equal(event.pos, [3.5, -4.25])
    np.testing.assert_array_equal(event.delta, [.5, -1.])
    assert event.modifiers == (keys.SHIFT, keys.CONTROL)
    assert event.native is native and event.extra == 'payload'
    assert event.buttons is buttons  # Explicit source alias; no immutable snapshot claim.
    buttons.append(3); assert event.buttons == [1, 2, 3]


def test_finite_drag_history_excludes_press_and_projects_integer_trail():
    press = MouseEvent('mouse_press', pos=[1, 2], button=1)
    first = MouseEvent('mouse_move', pos=[3.75, 4.5], press_event=press, last_event=press)
    last = MouseEvent('mouse_move', pos=[-2.25, 9.75], press_event=press, last_event=first)
    assert last.is_dragging and last.press_event is press and last.last_event is first
    assert last.drag_events() == [first, last]
    np.testing.assert_array_equal(last.trail(), [[3, 4], [-2, 9]])
    assert np.issubdtype(last.trail().dtype, np.integer)
    # No cyclic history or physical pointer delivery is constructed here.


@pytest.mark.parametrize('key,text', [(keys.ENTER, ''), (keys.Key('A'), 'A'),
    (keys.Key('A'), 'a'), (None, 'λ漢')])
def test_key_event_preserves_key_text_and_modifier_values(key, text):
    native = object(); modifiers = [keys.SHIFT]
    event = KeyEvent('key_press', key=key, text=text, modifiers=modifiers, native=native)
    modifiers.clear()
    assert event.key is key and event.text == text
    assert event.modifiers == (keys.SHIFT,) and event.native is native
    assert event.type == 'key_press'


def test_key_string_aliases_codes_and_invalid_comparison_recovery():
    assert keys.ENTER == 'Return' and keys.ENTER == 'enter'
    assert keys.Key('a') == 'A' and keys.Key('a') == 65
    assert not (keys.Key('a') == 97) and not (keys.ENTER == None)  # noqa: E711
    with pytest.raises(ValueError):
        keys.ENTER == {}
    assert keys.ENTER == 'Return'


@pytest.mark.parametrize('physical', [None, (60, 40)])
def test_resize_logical_and_physical_values_are_distinct(physical):
    event = ResizeEvent('resize', size=[30, 20], physical_size=physical)
    assert event.size == (30, 20)
    assert event.physical_size == ((30, 20) if physical is None else (60, 40))


@pytest.mark.parametrize('invalid', [None, 10])
def test_resize_requires_iterable_size_and_recovers(invalid):
    with pytest.raises(TypeError):
        ResizeEvent('resize', size=invalid)
    assert ResizeEvent('resize', size=(1, 2)).size == (1, 2)


@pytest.mark.parametrize('region', [None, (1, 2, 3, 4)])
def test_draw_region_and_native_payload_are_preserved(region):
    native = object(); event = DrawEvent('draw', region=region, native=native)
    assert event.region is region and event.native is native and event.type == 'draw'


@pytest.mark.parametrize('kind', ['event', 'mouse', 'key', 'resize', 'draw', 'scene'])
def test_shared_event_properties_preserve_source_stack_and_mutable_flags(kind):
    class Source: pass
    source = Source()
    event = {'event': lambda: Event('event'), 'mouse': lambda: MouseEvent('mouse_move'),
             'key': lambda: KeyEvent('key_press'), 'resize': lambda: ResizeEvent('resize', size=(1, 2)),
             'draw': lambda: DrawEvent('draw'),
             'scene': lambda: SceneMouseEvent(MouseEvent('mouse_move'), None)}[kind]()
    emitter = EventEmitter(source=source, type=event.type)
    seen = []
    def handle(value):
        assert value is event and value.source is source and value.sources == [source]
        value.handled = 1; value.blocked = 1; seen.append(value.type)
    emitter.connect(handle)
    emitter(event)
    assert event.handled is event.blocked is True
    assert event.source is None and event.sources == []
    event.handled = 0; event.blocked = 0; emitter(event)
    assert seen == [event.type, event.type]


def test_event_handling_blocking_and_callback_error_source_recovery():
    class Source: pass
    source = Source(); emitter = EventEmitter(source=source, type='event')
    emitter.ignore_callback_errors = False
    seen = []
    def first(event):
        assert event.source is source and event.sources == [source]
        seen.append('first'); event.handled = True
    def second(event): seen.append('second')
    emitter.connect(first, position='last'); emitter.connect(second, position='last')
    event = emitter(extra='value')
    assert seen == ['first', 'second'] and event.handled and not event.blocked
    assert event.extra == 'value' and event.source is None and event.sources == []
    def blocked(event): seen.append('blocked'); event.blocked = True
    emitter.connect(blocked, position='first'); seen.clear()
    event = emitter(); assert seen == ['blocked'] and event.blocked
    emitter.disconnect(blocked)
    def failure(event): raise ValueError('intentional event callback')
    emitter.connect(failure, position='first')
    event = Event('event')
    with pytest.raises(ValueError, match='intentional event callback'): emitter(event)
    assert event.source is None and event.sources == []
    emitter.disconnect(failure); seen.clear(); emitter()
    assert seen == ['first', 'second']


def test_emitter_group_addition_name_failure_blocking_and_recovery():
    class Source: pass
    source = Source(); group = EmitterGroup(source=source, auto_connect=False, change=Event)
    seen = []
    def receive(event):
        assert event.source is source; seen.append(event.type)
    group.connect(receive)
    assert group['change'] is group.change and list(group) == ['change']
    group.change(); assert seen == ['change']
    with pytest.raises(ValueError): group.add(later=Event, change=Event)
    assert list(group) == ['change']  # Name checks precede all additions.
    group.add(later=Event); group.later(); assert seen == ['change', 'later']
    group.block_all(); group.change(); group.later(); assert seen == ['change', 'later']
    group.unblock_all(); group.change(); assert seen == ['change', 'later', 'change']
    group.disconnect(receive); group.change(); assert seen == ['change', 'later', 'change']


class CoordinateVisual:
    def __init__(self, scale, translate):
        self.transform = STTransform(scale=scale, translate=translate); self.calls = 0
    def get_transform(self, source, target):
        assert (source, target) == ('canvas', 'visual')
        self.calls += 1; return self.transform


def test_scene_event_coordinates_cache_and_visual_reassignment():
    visual = CoordinateVisual((2, 3, 1), (1, -1, 0))
    raw = MouseEvent('mouse_move', pos=[3, 4])
    event = SceneMouseEvent(raw, visual)
    np.testing.assert_array_equal(event.pos, [7, 11, 0, 1])
    np.testing.assert_array_equal(event.pos, [7, 11, 0, 1]); assert visual.calls == 1
    replacement = CoordinateVisual((1, 1, 1), (-2, 5, 0))
    event.visual = replacement
    np.testing.assert_array_equal(event.pos, [1, 9, 0, 1]); assert replacement.calls == 1


def test_scene_event_history_payload_copy_and_independent_flags():
    visual = CoordinateVisual((1, 1, 1), (0, 0, 0)); native = object()
    press = MouseEvent('mouse_press', pos=[1, 2], native=native)
    raw = MouseEvent('mouse_move', pos=[3, 4], button=1, buttons=[1], modifiers=[keys.SHIFT],
                     delta=[.5, 1.5], last_event=press, press_event=press, native=native)
    event = SceneMouseEvent(raw, visual)
    assert event.button == 1 and event.buttons is raw.buttons and event.modifiers == (keys.SHIFT,)
    np.testing.assert_array_equal(event.delta, [.5, 1.5])
    assert event.last_event.mouse_event is press and event.press_event.mouse_event is press
    assert event.native is None and event.mouse_event.native is native
    event.handled = True; event.blocked = True; copied = event.copy()
    assert copied.mouse_event is raw and copied.visual is visual
    assert not copied.handled and not copied.blocked and copied.sources == []
    plain = SceneMouseEvent(MouseEvent('mouse_move'), visual)
    assert plain.last_event is plain.press_event is None


def test_scene_zoom_scale_refusal_then_valid_payload_recovers():
    visual = CoordinateVisual((1, 1, 1), (0, 0, 0))
    with pytest.raises(TypeError, match='has no scale'):
        SceneMouseEvent(MouseEvent('mouse_move'), visual).scale
    assert SceneMouseEvent(MouseEvent('gesture_zoom', scale=1.25), visual).scale == 1.25
