"""Active readback canvas ownership survives real Qt layout and window changes."""

import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def test_active_canvas_moves_layouts_survives_old_parent_deletion_and_winid_change():
    from PyQt6 import QtCore, QtWidgets, sip
    from vispy import _dawn, app, gloo

    application = app.use_app('pyqt6')
    qt_application = application.native
    assert QtWidgets.QApplication.instance() is qt_application
    hosts = [QtWidgets.QWidget() for _ in range(3)]
    layouts = [QtWidgets.QVBoxLayout(host) for host in hosts]
    destroyed = []
    for index, (host, layout) in enumerate(zip(hosts, layouts)):
        host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        host.destroyed.connect(lambda obj=None, index=index: destroyed.append(index))
        host.resize(80 + index * 12, 60 + index * 10)
        layout.setContentsMargins(0, 0, 0, 0)
    canvas = app.Canvas(app='pyqt6', parent=hosts[0], size=(40, 30), show=False, vsync=False)
    widget = canvas.native
    identifier = int(widget._dawn_canvas_id)
    assert widget._dawn_presentation == 'readback', 'select readback explicitly for this bounded case'
    layouts[0].addWidget(widget)
    program = gloo.Program(
        'attribute vec2 a_position; void main() { gl_Position=vec4(a_position,0.,1.); }',
        'uniform vec4 u_color; void main() { gl_FragColor=u_color; }')
    vertices = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    program['a_position'] = vertices
    color = [1., 0., 0., 1.]
    draws, closes, events = [], [], []

    class Observe(QtCore.QObject):
        def eventFilter(self, receiver, event):
            if event.type() in (QtCore.QEvent.Type.WinIdChange, QtCore.QEvent.Type.ParentChange):
                events.append(event.type())
            return False

    observer = Observe(widget)
    widget.installEventFilter(observer)

    def draw(event):
        draws.append(tuple(color))
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.set_state(depth_test=False, stencil_test=False, blend=False, cull_face=False)
        gloo.clear(color=(0., 0., 0., 1.))
        program['u_color'] = tuple(color)
        program.draw('triangles')

    canvas.events.draw.ignore_callback_errors = False
    canvas.events.draw.connect(draw)
    canvas.events.close.connect(lambda event: closes.append(True))

    def pump_until(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            _dawn.process_events()
            assert time.monotonic() < deadline, 'reparented canvas did not redraw'
            time.sleep(.001)

    def expect_color():
        canvas.set_current()
        _dawn.finish(identifier)
        np.testing.assert_array_equal(
            _dawn.read_pixels(identifier, 0, 0, 2, 2, True),
            np.full((2, 2, 4), [round(v * 255) for v in color], dtype=np.uint8))
        assert not _dawn.benchmark_surface_info(identifier)['attached']
        assert int(widget._dawn_canvas_id) == identifier
        assert not canvas._closed and not widget._dawn_closed and not closes

    try:
        hosts[0].show()
        canvas.show()
        pump_until(lambda: bool(draws))
        expect_color()
        # Qt may use alien child widgets in readback mode. Request a real Qt
        # window here so that later native-window destruction has an observable
        # WinIdChange; this does not attach a Vulkan WSI surface.
        assert int(widget.winId()) != 0
        for index, rgb in enumerate(((0., 1., 0.), (0., 0., 1.)), start=1):
            before = len(draws)
            widget.setParent(hosts[index])
            layouts[index].addWidget(widget)
            assert widget.parentWidget() is hosts[index]
            color[:] = [*rgb, 1.]
            hosts[index].show()
            widget.show()
            canvas.update()
            pump_until(lambda: len(draws) > before)
            expect_color()
            hosts[index - 1].close()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            application.process_events()
            assert index - 1 in destroyed
            before = len(draws)
            canvas.update()
            pump_until(lambda: len(draws) > before)
            expect_color()
        before_winid = events.count(QtCore.QEvent.Type.WinIdChange)
        widget.destroy()
        assert int(widget.winId()) != 0
        widget.show()
        before = len(draws)
        canvas.update()
        pump_until(lambda: len(draws) > before)
        expect_color()
        assert events.count(QtCore.QEvent.Type.WinIdChange) > before_winid
        assert events.count(QtCore.QEvent.Type.ParentChange) >= 2
        program.delete()
        vertices.delete()
        canvas.context.flush_commands()
    finally:
        canvas.close()
        for host in hosts:
            if not sip.isdeleted(host):
                host.close()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        _dawn.process_events()
    gauges = {name: _dawn.probe()[name] for name in (
        'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
        'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
        'line_resource_pool_busy_slots', 'line_resource_pool_bytes')}
    assert len(closes) == 1 and not any(gauges.values()), gauges
    print('two active layout moves, old parents deleted, real WinIdChange, exact pixels; nine shutdown gauges', gauges)
