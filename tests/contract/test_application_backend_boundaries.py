# SPDX-License-Identifier: AGPL-3.0-only
"""Public application refusals and event values; no toolkit/device construction."""
import sys

import numpy as np
import pytest
import vispy
from vispy.app import Application, KeyEvent, MouseEvent
from vispy.util import keys


REMOVED = ('egl', 'glfw', 'osmesa', 'pyglet', 'pyqt4', 'pyside', 'pyside2', 'sdl2', 'wx')
TOOLKITS = ('OpenGL', 'glfw', 'pyglet', 'PyQt4', 'PySide', 'PySide2', 'sdl2', 'wx')


def toolkit_modules():
    return {name for name in sys.modules if any(name == p or name.startswith(p + '.') for p in TOOLKITS)}


@pytest.mark.parametrize('backend', REMOVED)
def test_removed_application_selector_refuses_before_toolkit_import(backend):
    before = toolkit_modules()
    with pytest.raises(RuntimeError, match='unported.*OpenGL context path'):
        Application(backend.upper())
    assert toolkit_modules() == before


@pytest.mark.parametrize('backend', REMOVED)
def test_removed_configured_backend_refuses_before_toolkit_import(backend, monkeypatch):
    monkeypatch.delenv('_VISPY_TESTING_APP', raising=False)
    monkeypatch.setattr(Application, 'is_notebook', lambda self: False)
    previous = vispy.config['default_backend']
    before = toolkit_modules()
    try:
        vispy.config['default_backend'] = backend
        with pytest.raises(RuntimeError, match='Configured application backend.*unavailable'):
            Application()
    finally:
        vispy.config['default_backend'] = previous
    assert toolkit_modules() == before


def test_unknown_application_selector_is_a_value_error():
    with pytest.raises(ValueError, match='backend_name must be one of'):
        Application('not-a-vispy-backend')


def test_public_key_event_preserves_values_without_a_toolkit():
    native = object()
    event = KeyEvent('key_press', key=keys.ENTER, text='\r', modifiers=[keys.SHIFT], native=native)
    assert event.key == keys.ENTER and event.text == '\r'
    assert event.modifiers == (keys.SHIFT,) and event.native is native
    release = KeyEvent('key_release', key=keys.ENTER)
    assert release.text == '' and release.modifiers == ()


def test_public_mouse_event_drag_chain_keeps_order_and_native_values():
    native = object()
    press = MouseEvent('mouse_press', pos=(2, 3), button=1, buttons=[1], native=native)
    first = MouseEvent('mouse_move', pos=(4, 5), buttons=[1], press_event=press, last_event=press)
    second = MouseEvent('mouse_move', pos=(6, 7), buttons=[1], press_event=press, last_event=first)
    assert press.button == 1 and press.native is native
    assert second.is_dragging and second.press_event is press and second.last_event is first
    assert second.drag_events() == [first, second]
    np.testing.assert_array_equal(second.trail(), [[4, 5], [6, 7]])
    idle = MouseEvent('mouse_move')
    assert not idle.is_dragging and idle.trail() is None
    np.testing.assert_array_equal(idle.pos, [0, 0])
    np.testing.assert_array_equal(idle.delta, [0, 0])


__all__ = [name for name in globals() if name.startswith('test_')]
