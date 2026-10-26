# SPDX-License-Identifier: AGPL-3.0-only
"""Displayed shared Program/Texture2D updates driven by a public VisPy Timer.

For audit_no_opengl.py --scenario script. Exact installed-member/profile and
observer/control proof belongs to the outer auditor, not this functional flow.
"""
import json
import sys
import time
import traceback


def run(*, cleanup_report=None):
    import tkinter as tk
    import numpy as np
    from vispy import app, gloo, _dawn

    application = app.Application('tkinter')
    root = tk.Tk()
    root.geometry('96x64')
    canvases, resources, ticks, host_events = [], [], [], []
    timer = host_job = host_binding = None
    retirement_baseline = None
    result = {'scope': 'Bounded Tk resource/timer flow; outer installed/observer gates required'}

    def resource_gauges():
        probe = _dawn.probe()
        values = {key: probe[key] for key in (
            'live_cpu_buffer_bytes', 'live_buffer_bytes', 'pending_tickets',
            'queued_frames', 'pending_draws', 'vertex_input_current_entries',
            'vertex_input_current_bytes', 'vertex_input_cache_entries', 'vertex_input_cache_bytes')}
        values['resource_texture_bytes'] = probe['live_texture_bytes'] - probe['canvas_texture_bytes']
        return values, probe['canvas_texture_bytes']

    def wait(condition):
        deadline = time.monotonic() + 5
        while not condition():
            application.process_events()
            assert time.monotonic() < deadline, 'Tk resource/timer workflow timed out'
            time.sleep(.005)

    def presented(canvas, rgb):
        photo = canvas._backend._photo
        return (photo is not None and canvas.native.winfo_viewable()
                and (photo.width(), photo.height()) == tuple(canvas.physical_size)
                and tuple(photo.get(1, 1)) == tuple(rgb))

    def expect(canvas, color):
        canvas.set_current()
        width, height = canvas.physical_size
        assert width > 2 and height > 2
        pixels = gloo.read_pixels((0, 0, width, height), alpha=True)
        photo = canvas._backend._photo
        unique, counts = np.unique(pixels.reshape(-1, 4), axis=0, return_counts=True)
        assert np.all(pixels == color), {'expected': color, 'colors': unique.tolist(),
                                        'counts': counts.tolist(), 'physical': [width, height],
                                        'photo': [photo.width(), photo.height()]}
        assert photo.width() == width and photo.height() == height
        for point in ((1, 1), (width - 2, height - 2)):
            assert tuple(photo.get(*point)) == tuple(color[:3])

    try:
        host_job = root.after(60000, lambda: host_events.append('unexpected-timer'))
        host_binding = root.bind('<<HostResourcePing>>', lambda event: host_events.append('host'), add='+')
        first = app.Canvas(app=application, parent=root, size=(96, 64), show=True)
        canvases.append(first)
        first.native.pack(fill='both', expand=True)
        second = app.Canvas(app=application, size=(96, 64), shared=first, show=True)
        canvases.append(second)
        assert first.context.shared is second.context.shared
        first.set_current()
        retirement_baseline, _ = resource_gauges()
        source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        resources.append(source)
        texture = gloo.Texture2D(np.array([[[255, 0, 0, 255]]], np.uint8))
        resources.append(texture)
        program = gloo.Program(
            'attribute vec2 position; attribute vec4 tint; varying vec4 color; '
            'void main(){color=tint;gl_Position=vec4(position,0,1);}',
            'uniform sampler2D image; varying vec4 color; '
            'void main(){gl_FragColor=color*texture2D(image,vec2(.5));}',
        )
        resources.append(program)
        program['position'], program['image'] = source, texture
        # A neutral constant attribute gives Program its own retained GPU buffer.
        program['tint'] = (1., 1., 1., 1.)

        def paint(event):
            canvas = event.source
            gloo.set_viewport(0, 0, *canvas.physical_size)
            gloo.set_state(scissor_test=False, depth_test=False, blend=False)
            program.draw('triangles')

        for canvas in canvases:
            canvas.events.draw.ignore_callback_errors = False
            canvas.events.draw.connect(paint)
            canvas.update()
        wait(lambda: all(presented(c, (255, 0, 0)) for c in canvases))
        for canvas in canvases:
            expect(canvas, [255, 0, 0, 255])

        def tick(event):
            ticks.append(event.source is timer)
            texture.set_data(np.array([[[0, 255, 0, 255]]], np.uint8))
            for canvas in canvases:
                canvas.update()
            timer.stop()

        timer = app.Timer(app=application, interval=.005, connect=tick)
        timer.events.timeout.ignore_callback_errors = False
        timer.start()
        wait(lambda: ticks and all(presented(c, (0, 255, 0)) for c in canvases))
        assert ticks == [True] and not timer.running and timer._backend._job is None
        for canvas in canvases:
            expect(canvas, [0, 255, 0, 255])
        first.close()
        assert first._closed and not second._closed
        second.set_current()
        texture.set_data(np.array([[[0, 0, 255, 255]]], np.uint8))
        second.update()
        wait(lambda: presented(second, (0, 0, 255)))
        expect(second, [0, 0, 255, 255])
        previous = second._backend._photo
        generation = _dawn.probe()['device_generation']
        _dawn.lose_device()
        second.update()
        wait(lambda: second._backend._photo is not previous
             and _dawn.probe()['device_generation'] > generation
             and presented(second, (0, 0, 255)))
        expect(second, [0, 0, 255, 255])
        result.update(device_recovered=True)
        result.update(timer_ticks=len(ticks), shared=True, survivor_color=[0, 0, 255, 255],
                      physical_sizes=[list(c.physical_size) for c in canvases])
    finally:
        primary = sys.exc_info()
        errors = []

        def cleanup(callback, *args):
            try:
                callback(*args)
                return True
            except BaseException:
                errors.append(sys.exc_info())
                return False

        if timer is not None:
            cleanup(timer.stop)
        survivor = next((c for c in reversed(canvases) if not c._closed), None)
        if survivor is not None:
            cleanup(survivor.set_current)
            before_delete, canvas_bytes = resource_gauges()
            for resource in reversed(resources):
                cleanup(resource.delete)
            cleanup(survivor.context.flush_commands)
            cleanup(gloo.finish)

            def verify_retirement():
                after_delete, after_canvas_bytes = resource_gauges()
                assert not survivor._closed and survivor.native.winfo_exists(), 'retirement requires live survivor'
                assert canvas_bytes > 0 and after_canvas_bytes == canvas_bytes, 'retirement must preserve canvas allocation'
                assert retirement_baseline is not None and len(resources) == 3
                for key in ('live_cpu_buffer_bytes', 'live_buffer_bytes', 'resource_texture_bytes'):
                    assert before_delete[key] > retirement_baseline[key], ('non-vacuous resource retirement', key)
                assert after_delete == retirement_baseline, {
                    'oracle': 'resource retirement before survivor close', 'baseline': retirement_baseline,
                    'before_delete': before_delete, 'after_delete': after_delete}
                result['retirement'] = dict(baseline=retirement_baseline, before_delete=before_delete,
                    after_delete=after_delete, canvas_bytes=canvas_bytes, survivor_alive=True,
                    python_references_alive=len(resources))

            if len(resources) == 3 and retirement_baseline is not None:
                cleanup(verify_retirement)
        for canvas in canvases:
            cleanup(canvas.close)
        cleanup(application.quit)

        def verify_host():
            assert root.winfo_exists() and not root.winfo_children()
            assert host_job in root.tk.call('after', 'info')
            assert host_binding in root.bind('<<HostResourcePing>>')
            assert not host_events
            root.event_generate('<<HostResourcePing>>')
            assert host_events == ['host']

        host_verified = not errors and cleanup(verify_host)
        if host_job is not None:
            cleanup(root.after_cancel, host_job)
        if host_binding is not None:
            cleanup(root.unbind, '<<HostResourcePing>>', host_binding)
        # Explicit host teardown; never move this idle drain into VisPy quit.
        cleanup(root.update_idletasks)
        cleanup(root.destroy)
        if cleanup_report is not None:
            cleanup_report.update(host_survived=bool(host_verified), secondary_errors=len(errors),
                                  timer_stopped=timer is not None and not timer.running
                                  and timer._backend._job is None)
        if errors:
            for error in errors:
                traceback.print_exception(*error)
            if primary[0] is None:
                raise errors[0][1].with_traceback(errors[0][2])
    result.update(status='PASS', host_survived=True)
    return result


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
