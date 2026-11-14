"""Parent-owned destruction preserves pending work and a shared renderer peer."""

import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('close_before_delete', [False, True])
def test_parent_deletion_retires_owner_and_shared_peer_keeps_rendering(close_before_delete):
    from PyQt6 import QtCore, QtWidgets, sip
    from vispy import _dawn, app
    from vispy import gloo

    application = app.use_app('pyqt6')
    qt_application = application.native
    parent = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(parent)
    first = app.Canvas(app='pyqt6', parent=parent, size=(24, 18), show=False)
    widget = first.native
    assert widget._dawn_presentation == 'readback'
    layout.addWidget(widget)
    peer = app.Canvas(app='pyqt6', shared=first, size=(24, 18), show=False)
    peer_id = int(peer.native._dawn_canvas_id)
    program = gloo.Program(
        'attribute vec2 a_position; void main() { gl_Position=vec4(a_position,0.,1.); }',
        'uniform vec4 u_color; void main() { gl_FragColor=u_color; }')
    vertices = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    program['a_position'] = vertices
    closed, destroyed = [], []
    first.events.close.connect(lambda event: closed.append(True))
    widget.destroyed.connect(lambda obj=None: destroyed.append(True))

    def paint(canvas, color):
        canvas.set_current()
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.set_state(depth_test=False, stencil_test=False, blend=False, cull_face=False)
        gloo.clear(color=(0., 0., 0., 1.))
        program['u_color'] = color
        program.draw('triangles')

    def expect(color):
        peer.set_current()
        _dawn.finish(peer_id)
        np.testing.assert_array_equal(
            _dawn.read_pixels(peer_id, 0, 0, 4, 4, True),
            np.full((4, 4, 4), color, dtype=np.uint8))

    try:
        paint(first, (1., 0., 0., 1.))
        _dawn.finish(int(widget._dawn_canvas_id))
        paint(peer, (0., 1., 0., 1.))
        assert _dawn.probe()['pending_draws'] > 0
        if close_before_delete:
            first.close()
            assert closed == [True]
        parent.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        assert sip.isdeleted(widget) and destroyed == [True]
        assert first._closed and first._backend is None and closed == [True]
        first.close()
        expect([0, 255, 0, 255])
        paint(peer, (0., 0., 1., 1.))
        expect([0, 0, 255, 255])
        assert not peer._closed and closed == [True]
        program.delete()
        vertices.delete()
        peer.context.flush_commands()
    finally:
        first.close()
        peer.close()
        if not sip.isdeleted(parent):
            parent.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        application.process_events()
        _dawn.process_events()
    gauges = {key: _dawn.probe()[key] for key in (
        'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
        'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
        'line_resource_pool_busy_slots', 'line_resource_pool_bytes', 'host_import_pinned_bytes')}
    assert not any(gauges.values()), gauges
    print('parent deleted; owner closed once; pending peer green and subsequent blue exact; gauges', gauges)
