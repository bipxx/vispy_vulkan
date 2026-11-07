# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise upload ownership across the actual native renderer's shutdown."""
import gc
import json

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu

_GAUGES = (
    'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
    'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
    'line_resource_pool_busy_slots', 'line_resource_pool_bytes', 'host_import_pinned_bytes',
)


def _shutdown_gauges():
    probe = _dawn.probe()
    result = {name: probe[name] for name in _GAUGES}
    assert not any(result.values()), result
    return result


def test_shutdown_retires_uploads_and_preserves_external_snapshot():
    # Rows are identical so both native/read_pixels row conventions give the
    # same exact image. The snapshot must outlive mutation of its exporter.
    size = 512
    expected = np.empty((size, size, 4), np.uint8)
    expected[..., 0] = np.arange(size, dtype=np.uint16).astype(np.uint8)
    expected[..., 1:] = (83, 151, 255)
    exporter = expected.copy()
    external = _dawn._capture_upload(exporter)
    exporter.fill(0)
    del exporter
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), show=False)
    try:
        # Explicit native shutdown replaces Canvas.__exit__'s glFinish. A
        # context-manager exit after shutdown would address a deleted canvas.
        canvas.set_current()
        texture = gloo.Texture2D(expected, interpolation='nearest')
        fbo = gloo.FrameBuffer(color=gloo.Texture2D(shape=(size, size, 4)))
        program = gloo.Program(
            'attribute vec2 position; varying vec2 uv; void main() {'
            'uv = (position + 1.0) / 2.0; gl_Position = vec4(position, 0.0, 1.0);}',
            'uniform sampler2D u_texture; varying vec2 uv;'
            'void main() {gl_FragColor = texture2D(u_texture, uv);}')
        program['position'] = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], np.float32)
        program['u_texture'] = texture
        for _ in range(3):
            texture.set_data(expected)
            with fbo:
                gloo.set_viewport(0, 0, size, size)
                program.draw('triangle_strip')
                pixels = gloo.read_pixels(viewport=(0, 0, size, size), alpha=True)
            assert np.array_equal(pixels, expected)
        device = _dawn.device_info()
        _dawn.diagnostic_submission_controls(True, '')
        texture.set_data(expected)
        with fbo:
            program.draw('triangle_strip')
        gloo.flush()
        before = _dawn.probe()
        assert before['pending_tickets'] >= 1, before
        assert before['host_block_captures'] >= 4, before
        if device['host_mapped_pointer']:
            assert before['host_import_copies'] > 0 and before['host_import_pinned_bytes'] > 0, before
        else:
            assert before['host_import_fallbacks'] > 0, before
        # Keep the Python resources and the independent snapshot alive.
        # shutdown itself must retire held submissions and dispose imports.
        _dawn.shutdown()
        first = _shutdown_gauges()
        _dawn.shutdown()
        repeated = _shutdown_gauges()
    finally:
        _dawn.diagnostic_submission_controls(False, '')
        canvas.close()

    # Consume the independent native snapshot only after both shutdowns. An
    # exact framebuffer read verifies that clearing the cache did not free it.
    native_canvas = _dawn.register_canvas(size, size, 1)
    payload = {'__owned_blob__': external, 'dtype': '|u1', 'shape': [size, size, 4]}
    commands = [
        ('CREATE', 910001, 'Texture2D'), ('SIZE', 910001, [size, size, 4], 'rgba'),
        ('DATA', 910001, [0, 0], payload), ('CREATE', 910002, 'FrameBuffer'),
        ('ATTACH', 910002, 'color', 910001), ('FRAMEBUFFER', 910002, True),
    ]
    try:
        _dawn._execute_owned(native_canvas, commands, [],
                             dict(captures=1, bytes=expected.nbytes, fallback_dtypes=0, fallback_exports=0))
        pixels = _dawn.read_pixels(native_canvas, 0, 0, size, size, True)
        assert np.array_equal(pixels, expected)
    finally:
        _dawn.shutdown()
    final = _shutdown_gauges()
    del external, payload, commands
    gc.collect()
    # An independent owner released after shutdown can repopulate a warm pool;
    # the next explicit shutdown must remain safe and idempotent.
    _dawn.shutdown()
    _shutdown_gauges()
    print('SHUTDOWN_UPLOAD_RESULT=' + json.dumps(dict(
        scope='Actual renderer teardown and external snapshot survival; warm CPU cache bytes are covered by the CPU regression',
        host_import_supported=bool(device['host_mapped_pointer']),
        pending_before=before['pending_tickets'], pinned_before=before['host_import_pinned_bytes'],
        first_shutdown=first, repeated_shutdown=repeated, final_shutdown=final,
        external_snapshot_readback_verified=True)))
