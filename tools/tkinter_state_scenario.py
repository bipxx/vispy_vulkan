# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded real Tk/state flow for audit_no_opengl.py --scenario script.

The outer auditor supplies installed-wheel/member, environment and native
observation proof. Running this script alone establishes functional behavior
only; it is not the complete Tk/state acceptance matrix.
"""
import json
import time


def run():
    import tkinter as tk
    import numpy as np
    from vispy import app, gloo, _dawn
    from vispy.gloo import gl

    assert _dawn.submission_contract_version == 1
    application = app.Application('tkinter')
    root = tk.Tk()
    root.geometry('192x128')
    canvases = []
    result = {'scope': 'Bounded Tk/state functional flow; outer installed/observer gates required',
              'submissions': []}

    def wait(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            assert time.monotonic() < deadline, 'Tk/state scenario timed out'
            time.sleep(.005)

    try:
        first = app.Canvas(app=application, parent=root, size=(192, 128), show=True)
        first.native.pack(fill='both', expand=True)
        second = app.Canvas(app=application, size=(192, 128), show=True)
        canvases.extend((first, second))
        for canvas, color in zip(canvases, ('red', 'blue')):
            def paint(event, canvas=canvas, color=color):
                gloo.set_viewport(0, 0, *canvas.physical_size)
                gloo.set_state(scissor_test=False)
                gloo.clear(color=color)
            canvas.events.draw.connect(paint)
            canvas.update()
        wait(lambda: all(canvas._backend._photo is not None and canvas.native.winfo_viewable() for canvas in canvases))
        assert first._backend._photo.get(16, 16) == (255, 0, 0)
        assert second._backend._photo.get(16, 16) == (0, 0, 255)
        received, host = [], []
        first.events.mouse_press.connect(lambda event: received.append(event))
        root.bind('<ButtonPress-1>', lambda event: host.append(event.widget), add='+')
        first.native.event_generate('<ButtonPress-1>', x=17, y=23)
        first.native.event_generate('<ButtonRelease-1>', x=17, y=23)
        assert len(received) == len(host) == 1
        assert tuple(received[0].pos) == (17, 23) and received[0].native.widget is first.native
        first.set_current()
        fields = ('dawn_queue_submits', 'finish_calls', 'completion_waits', 'application_presents')
        for name, flush, color, expected in (('gloo.flush', gloo.flush, 'green', [0, 128, 0, 255]),
                                             ('glFlush', gl.glFlush, 'blue', [0, 0, 255, 255])):
            before = _dawn.probe()
            gloo.clear(color=color)
            flush()
            after = _dawn.probe()
            assert after[fields[0]] > before[fields[0]]
            assert all(after[key] == before[key] for key in fields[1:])
            submission = {'route': name, 'before': {key: before[key] for key in fields},
                          'after': {key: after[key] for key in fields}}
            result['submissions'].append(submission)
            finish_fields = fields + ('pending_tickets', 'queued_frames', 'pending_draws', 'retired_tickets')
            finish_before = _dawn.probe()
            gloo.finish()
            finished = _dawn.probe()  # Snapshot before readback or an event pump can wait.
            assert finished['finish_calls'] == finish_before['finish_calls'] + 1, 'finish before readback'
            assert finished['completion_waits'] > finish_before['completion_waits'], 'finish completion before readback'
            assert finished['application_presents'] == after['application_presents']
            assert all(finished[key] == 0 for key in ('pending_tickets', 'queued_frames', 'pending_draws'))
            submission['finish_before'] = {key: finish_before[key] for key in finish_fields}
            submission['finish_after'] = {key: finished[key] for key in finish_fields}
            pixels = gloo.read_pixels((0, 0, *first.physical_size), alpha=True)
            assert np.all(pixels == expected)
            submission['readback'] = pixels[0, 0].tolist()
            # Inspect the actual untouched target before update can repaint it.
            second.set_current()
            untouched = gloo.read_pixels((0, 0, *second.physical_size), alpha=True)
            assert np.all(untouched == [0, 0, 255, 255]), 'untouched second target before repaint'
            submission['untouched_second_rgba'] = untouched[0, 0].tolist()
            first.set_current()
        first.close()
        previous = second._backend._photo
        second.update()
        wait(lambda: second._backend._photo is not previous)
        assert second._backend._photo.get(16, 16) == (0, 0, 255)
        application.quit()
        assert root.winfo_exists() and not root.winfo_children()
        root.event_generate('<ButtonPress-1>', x=3, y=5)
        assert len(host) == 2 and host[-1] is root
        result.update(status='PASS', tcl_patchlevel=root.tk.call('info', 'patchlevel'),
                      tk_patchlevel=root.tk.call('package', 'require', 'Tk'))
    finally:
        try:
            application.quit()
        finally:
            root.destroy()
    return result


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
