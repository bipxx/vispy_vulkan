# SPDX-License-Identifier: AGPL-3.0-only
"""Finite capture scenario; execution alone does not admit an installed artifact.

The input colors and top-left image oracle follow the already executed capture
fixtures. This separate contract does not extend the old Tk/resource composite.
"""
import hashlib
import json
import sys
import time
import traceback


CONTRACT = 'tk-capture-1'
SCOPE = 'Single-sample RGBA8 Tk crops: byte/normalized-float32 alpha, resize, argument rejection/retry'
COUNTERS = ('pending_draws', 'dawn_queue_submits', 'finish_calls',
            'completion_waits', 'application_presents')


def expected_frame(width, height):
    import numpy as np
    image = np.empty((height, width, 4), dtype=np.uint8)
    left, bottom = width // 2, height // 2
    image[:height-bottom, :left] = [0, 0, 255, 192]
    image[:height-bottom, left:] = [255, 255, 0, 255]
    image[height-bottom:, :left] = [255, 0, 0, 64]
    image[height-bottom:, left:] = [0, 255, 0, 128]
    return image


def _capture(canvas, viewport, expected):
    import numpy as np
    from vispy import gloo
    canvas.set_current()
    byte = gloo.read_pixels(viewport, alpha=True, out_type='unsigned_byte')
    assert byte.dtype == np.uint8 and byte.shape == expected.shape
    np.testing.assert_array_equal(byte, expected)
    floating = gloo.read_pixels(viewport, alpha=True, out_type='float')
    assert floating.dtype == np.float32 and floating.shape == expected.shape
    reference = expected.astype(np.float32) / 255
    assert np.isfinite(floating).all()
    np.testing.assert_allclose(floating, reference, atol=1e-6, rtol=0)
    # Keep the closed result compact while retaining a full-image positional
    # digest and the separately asserted normalized-float tolerance.
    quantized = np.rint(floating * 255).astype(np.uint8)
    np.testing.assert_array_equal(quantized, expected)
    flat = floating.reshape(-1, 4)
    starts = np.r_[0, np.flatnonzero(np.any(flat[1:] != flat[:-1], axis=1))+1]
    ends = np.r_[starts[1:], len(flat)]
    # Lossless runs let the independent decoder check every actual float pixel,
    # including its position, finiteness and error against byte/255.
    runs = [[int(end-start), flat[start].tolist()] for start, end in zip(starts, ends)]
    return dict(viewport=list(viewport), shape=list(byte.shape),
                byte_dtype=str(byte.dtype), float_dtype=str(floating.dtype),
                rgba_sha256=hashlib.sha256(byte.tobytes()).hexdigest(),
                float_rgba_sha256=hashlib.sha256(quantized.tobytes()).hexdigest(),
                float_runs=runs,
                float_max_abs_error=float(np.max(np.abs(
                    floating.astype(np.float64)-expected.astype(np.float64)/255))))


def run():
    import tkinter as tk
    import numpy as np
    from vispy import app, gloo, _dawn

    application = app.Application('tkinter')
    root = tk.Tk()
    root.geometry('257x129')
    canvas = None
    cleanup_errors = []
    result = None

    def wait(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            assert time.monotonic() < deadline, 'capture scenario timed out'
            time.sleep(.005)

    def snapshot():
        state = _dawn.probe()
        return {key: state[key] for key in COUNTERS}

    def draw(event):
        width, height = canvas.physical_size
        left, bottom = width // 2, height // 2
        gloo.set_viewport(0, 0, width, height)
        gloo.set_state(scissor_test=False)
        gloo.clear(color='black', depth=False, stencil=False)
        for rectangle, color in (
            ((0, 0, left, bottom), (1, 0, 0, 64/255)),
            ((left, 0, width-left, bottom), (0, 1, 0, 128/255)),
            ((0, bottom, left, height-bottom), (0, 0, 1, 192/255)),
            ((left, bottom, width-left, height-bottom), (1, 1, 0, 1)),
        ):
            gloo.set_scissor(*rectangle)
            gloo.set_state(scissor_test=True)
            gloo.clear(color=color, depth=False, stencil=False)
        gloo.set_viewport(3, 5, 7, 9)

    def capture_pattern(size, viewport):
        assert canvas.physical_size == size
        full = expected_frame(*size)
        photo = canvas._backend._photo
        assert (photo.width(), photo.height()) == size
        for x, y in ((2, 2), (size[0]-3, 2), (2, size[1]-3), (size[0]-3, size[1]-3)):
            assert tuple(photo.get(x, y)) == tuple(full[y, x, :3])
        x, y, width, height = viewport
        crop = full[size[1]-y-height:size[1]-y, x:x+width]
        record = _capture(canvas, viewport, crop)
        record['target_size'] = list(size)
        return record

    try:
        canvas = app.Canvas(app=application, parent=root, size=(257, 129),
                            show=True, config={'samples': 0})
        canvas.native.pack(fill='both', expand=True)
        canvas.events.draw.ignore_callback_errors = False
        canvas.events.draw.connect(draw)
        canvas.update()
        wait(lambda: canvas.native.winfo_viewable() and canvas._backend._photo is not None)
        canvas.set_current()
        samples = int(gloo.gl.glGetParameter(gloo.gl.GL_SAMPLES))
        assert samples == 0, 'capture target is not single-sample storage'
        from vispy.gloo.context import get_current_canvas
        assert get_current_canvas() is canvas
        canvas_id = int(canvas._backend._dawn_canvas_id)
        configuration = _dawn.framebuffer_config(canvas_id)
        setup = dict(canvas_id=canvas_id, sample_count=configuration['sample_count'],
                     framebuffer_id=configuration['framebuffer_id'],
                     width=configuration['width'], height=configuration['height'],
                     rgba_bits=[configuration[channel+'_size'] for channel in ('red', 'green', 'blue', 'alpha')])
        ordinary = capture_pattern((257, 129), (3, 4, 131, 69))

        root.geometry('301x177')
        canvas.update()
        wait(lambda: canvas.physical_size == (301, 177) and
             canvas._backend._photo.width() == 301 and canvas._backend._photo.height() == 177)
        mutation = capture_pattern((301, 177), (5, 7, 157, 97))

        canvas.set_current()
        gloo.set_state(scissor_test=False)
        gloo.clear(color=(0, 1, 1, 96/255), depth=False, stencil=False)
        canvas.context.flush_commands()
        before = snapshot()
        assert before['pending_draws'] > 0
        try:
            gloo.read_pixels((0, 0, 1), alpha=True)
        except ValueError as error:
            failure = dict(type=type(error).__name__, message=str(error),
                           traceback=traceback.format_exc(), attempted_viewport=[0, 0, 1])
        else:
            raise AssertionError('malformed capture viewport did not fail')
        after = snapshot()
        assert after == before, 'invalid viewport consumed queued rendering'
        failure.update(before=before, after=after)

        viewport = (5, 7, 157, 97)
        expected = np.empty((97, 157, 4), dtype=np.uint8)
        expected[:] = [0, 255, 255, 96]
        recovery = _capture(canvas, viewport, expected)
        recovery['target_size'] = [301, 177]
        recovered = snapshot()
        assert recovered['pending_draws'] == 0
        assert recovered['dawn_queue_submits'] > before['dawn_queue_submits']
        recovery['after'] = recovered
        result = dict(schema=1, contract=CONTRACT, status='PASS', scope=SCOPE, setup=setup,
                      ordinary=ordinary, mutation=mutation, failure=failure,
                      recovery=recovery, samples=samples,
                      tcl_patchlevel=str(root.tk.call('info', 'patchlevel')),
                      tk_patchlevel=str(root.tk.call('package', 'require', 'Tk')))
    finally:
        primary = sys.exc_info()
        callbacks = ([canvas.close] if canvas is not None else []) + [application.quit, root.destroy]
        for callback in callbacks:
            try:
                callback()
            except BaseException:
                cleanup_errors.append(sys.exc_info())
        for error in cleanup_errors:
            traceback.print_exception(*error)
        if cleanup_errors and primary[0] is None:
            raise cleanup_errors[0][1].with_traceback(cleanup_errors[0][2])
    result['cleanup_errors'] = len(cleanup_errors)
    return result


if __name__ == '__main__':
    VISPY_FUNCTIONAL_RESULT = run()
    print(json.dumps(VISPY_FUNCTIONAL_RESULT, indent=2))
