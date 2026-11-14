# SPDX-License-Identifier: AGPL-3.0-only
"""Qt application focus drives real canvases via one host QWindow."""
import gc
import json
import os
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
GAUGES = ('pending_tickets', 'queued_frames', 'live_buffer_bytes',
          'live_cpu_buffer_bytes', 'live_texture_bytes', 'canvas_texture_bytes',
          'transient_buffer_bytes', 'line_resource_pool_busy_slots',
          'line_resource_pool_bytes', 'host_import_pinned_bytes')


@pytest.mark.parametrize('flow', ('canvases', 'host_entry'))
def test_host_window_focus_routes_input_and_rendering_without_peer_leakage(flow):
    from PyQt6 import QtCore, QtTest, QtWidgets
    from vispy import _dawn, app, gloo, keys

    assert os.environ.get('VISPY_QT_PRESENTATION') == 'readback'
    application = app.use_app('pyqt6')
    native_application = application.native
    host = QtWidgets.QWidget()
    host.setObjectName('focus_host')
    layout = QtWidgets.QVBoxLayout(host)
    canvases, widgets = [], []
    colors = [[255, 0, 0, 255], [0, 0, 255, 255]]
    draws, presses = [0, 0], [0, 0]
    received, callback_errors, focus_trace, observations = [], [], [], []

    def pump_until(predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            application.process_events()
            _dawn.process_events()
            assert time.monotonic() < deadline, 'Qt focus/render condition timed out'
            time.sleep(.001)

    def paint(index):
        def draw(event):
            draws[index] += 1
            gloo.set_viewport(0, 0, *canvases[index].physical_size)
            gloo.clear(color=tuple(v / 255 for v in colors[index]), depth=False)
        return draw

    def receiver(index):
        def receive(event):
            # Report fixture errors after Qt returns, outside its C++ virtual.
            try:
                received.append((index, event.type, event.key, event.text,
                                 event.modifiers))
                event.handled = True
                if event.type == 'key_press':
                    presses[index] += 1
                    colors[index] = ([0, 255, 0, 255] if presses[index] == 1
                                     else [255, 255, 0, 255])
                    canvases[index].update()
            except Exception as error:
                callback_errors.append(repr(error))
        return receive

    def pixels(index):
        canvas = canvases[index]
        identifier = int(canvas.native._dawn_canvas_id)
        _dawn.finish(identifier)
        np.testing.assert_array_equal(
            _dawn.read_pixels(identifier, 0, 0, 2, 2, True),
            np.full((2, 2, 4), colors[index], np.uint8))
        assert not _dawn.benchmark_surface_info(identifier)['attached']

    try:
        for index, name in enumerate(('canvas_a', 'canvas_b')):
            canvas = app.Canvas(app='pyqt6', parent=host, size=(80, 40),
                                show=False, vsync=False)
            canvases.append(canvas)
            widget = canvas.native
            widgets.append(widget)
            widget.setObjectName(name)
            widget.setMinimumSize(80, 40)
            layout.addWidget(widget)
            assert widget._dawn_presentation == 'readback'
            canvas.events.draw.ignore_callback_errors = False
            canvas.events.draw.connect(paint(index))
            for name in ('key_press', 'key_release'):
                emitter = canvas.events[name]
                emitter.ignore_callback_errors = False
                emitter.connect(receiver(index))
        entry = QtWidgets.QLineEdit(host)
        entry.setObjectName('host_entry')
        layout.addWidget(entry)
        host.resize(220, 180)
        host.show()
        for canvas in canvases:
            canvas.show()
        host.activateWindow()
        # Exercise controlled Qt application focus, not OS-wide/HID focus.
        native_application.setActiveWindow(host)
        pump_until(lambda: host.windowHandle() is not None and all(draws))
        window = host.windowHandle()
        pixels(0)
        pixels(1)
        sequence = ([widgets[0], widgets[1], widgets[0]] if flow == 'canvases'
                    else [widgets[0], entry, widgets[0]])
        for target in sequence:
            target.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
            pump_until(lambda: native_application.focusWidget() is target)
            focus_trace.append(target.objectName())
            before = len(received)
            before_draws = draws[:]
            before_colors = [color[:] for color in colors]
            assert window is host.windowHandle()
            # The receiving window stays fixed; Qt routes to its focused child.
            QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_K,
                                 QtCore.Qt.KeyboardModifier.NoModifier)
            application.process_events()
            assert not callback_errors, callback_errors
            if target is entry:
                assert len(received) == before
                assert entry.text() == 'k'
                assert colors == before_colors
            else:
                index = widgets.index(target)
                assert len(received) == before + 2, received
                events = received[-2:]
                assert [e[0] for e in events] == [index, index]
                assert [e[1] for e in events] == ['key_press', 'key_release']
                assert all(e[2] == keys.Key('K') and e[3] == 'k' and e[4] == ()
                           for e in events), events
                assert colors[1 - index] == before_colors[1 - index]
                pump_until(lambda: draws[index] > before_draws[index])
            pixels(0)
            pixels(1)
            observations.append(dict(focus=target.objectName(),
                                     canvas_colors=[c[:] for c in colors],
                                     events=len(received), entry_text=entry.text()))
        assert presses == ([2, 1] if flow == 'canvases' else [2, 0])
        assert entry.text() == ('' if flow == 'canvases' else 'k')
        assert len(received) == (6 if flow == 'canvases' else 4)
        assert all(not c._closed and not w._dawn_callback_failed
                   for c, w in zip(canvases, widgets))
        assert getattr(native_application, '_vispy_dawn_callback_error', None) is None
    finally:
        for canvas in canvases:
            canvas.close()
        host.close()
        host.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(
            None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        gc.collect()
        _dawn.process_events()
    gauges = {name: _dawn.probe()[name] for name in GAUGES}
    assert not any(gauges.values()), gauges
    assert getattr(native_application, '_vispy_dawn_callback_error', None) is None
    print('focus rendered proof', json.dumps(dict(
        flow=flow, focus=focus_trace, observations=observations,
        presses=presses, shutdown_gauges=gauges,
        oracle='2x2 internal framebuffer readback; no Vulkan WSI surface',
        activation='controlled QApplication focus; QtTest fixed host QWindow')))
