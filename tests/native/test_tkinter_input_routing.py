# SPDX-License-Identifier: AGPL-3.0-only
"""Toolkit-delivered input routing; event_generate is not physical HID input."""
import pytest

from vispy import app
from vispy.util import keys
from test_tkinter_backend import application, input_canvas, wait

pytestmark = pytest.mark.gpu


def test_native_focus_transfer_isolates_canvases_and_preserves_host_entry(application):
    import tkinter as tk
    parent = tk.Toplevel(application.native)
    canvases = []
    try:
        entry = tk.Entry(parent); entry.pack()
        for _ in range(2):
            canvas = app.Canvas(app=application, parent=parent, size=(80, 60), config={'samples': 0})
            canvases.append(canvas); canvas.native.pack(side='left')
        wait(application, lambda: all(c.native.winfo_viewable() for c in canvases))
        delivered = [[], []]; host = []; releases = []
        parent.bind('<KeyPress>', lambda event: host.append((event.widget, event.keysym)), add='+')
        for canvas, seen in zip(canvases, delivered):
            canvas.events.key_press.connect(seen.append)
            canvas.events.key_release.connect(seen.append)
        first, second = canvases
        first.events.mouse_release.connect(releases.append)
        first.native.focus_force(); application.process_events()
        assert parent.focus_get() is first.native
        first.native.event_generate('<KeyPress-Shift_L>')
        first.native.event_generate('<ButtonPress-1>', x=11, y=13, state=1)
        assert delivered[0][-1].key == keys.SHIFT
        assert delivered[0][-1].modifiers == (keys.SHIFT,)
        assert first._backend._pressed_modifiers and first._backend._pressed_keys

        # A real Tk focus transfer, rather than calling the adapter directly,
        # must cancel the first widget's held input before the second receives B.
        second.native.focus_force(); application.process_events()
        assert parent.focus_get() is second.native
        assert not first._backend._pressed_modifiers and not first._backend._pressed_keys
        assert not first._backend._pressed_buttons
        assert len(releases) == 1 and releases[0].button == 1 and releases[0].buttons == []
        assert releases[0].native.widget is first.native
        second.native.event_generate('<KeyPress-b>'); second.native.event_generate('<KeyRelease-b>')
        assert [event.type for event in delivered[1]] == ['key_press', 'key_release']
        assert all(event.key == 'B' and event.text == 'b' and event.modifiers == ()
                   and event.native.widget is second.native for event in delivered[1])
        assert len(delivered[0]) == 1  # No B leaked to the first canvas.

        # A host widget keeps its ordinary Tk binding and receives C without
        # either VisPy canvas intercepting or duplicating the event.
        entry.focus_force(); application.process_events(); assert parent.focus_get() is entry
        entry.event_generate('<KeyPress-c>'); entry.event_generate('<KeyRelease-c>')
        assert entry.get() == 'c'
        assert [event_widget for event_widget, _ in host] == [first.native, second.native, entry]
        assert [len(events) for events in delivered] == [1, 2]

        # Re-entering the first canvas starts with a clean modifier/key cache.
        first.native.focus_force(); application.process_events()
        first.native.event_generate('<KeyPress-a>'); first.native.event_generate('<KeyRelease-a>')
        assert [event.type for event in delivered[0][-2:]] == ['key_press', 'key_release']
        assert all(event.key == 'A' and event.text == 'a' and event.modifiers == ()
                   for event in delivered[0][-2:])
        assert entry.get() == 'c' and len(delivered[1]) == 2
    finally:
        for canvas in canvases: canvas.close()
        parent.destroy()


def test_delivered_key_release_failure_clears_cache_and_next_key_recovers(application):
    canvas = input_canvas(application)
    try:
        delivered = []
        canvas.events.key_press.connect(delivered.append)
        canvas.events.key_release.connect(delivered.append)
        canvas.events.key_release.ignore_callback_errors = False
        def failure(event):
            if event.key == 'A': raise ValueError('intentional delivered key release failure')
        canvas.events.key_release.connect(failure)
        canvas.native.event_generate('<KeyPress-a>')
        assert canvas._backend._pressed_keys
        canvas.native.after(0, lambda: canvas.native.event_generate('<KeyRelease-a>'))
        with pytest.raises(ValueError, match='intentional delivered key release failure'):
            application.process_events()
        assert not canvas._backend._pressed_keys and not canvas._backend._pressed_modifiers
        canvas.events.key_release.disconnect(failure)
        delivered.clear()
        canvas.native.event_generate('<KeyPress-b>'); canvas.native.event_generate('<KeyRelease-b>')
        assert [event.type for event in delivered] == ['key_press', 'key_release']
        assert all(event.key == 'B' and event.text == 'b' and event.native.widget is canvas.native
                   for event in delivered)
    finally:
        canvas.close()
