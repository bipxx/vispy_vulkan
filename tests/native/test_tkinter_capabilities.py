# SPDX-License-Identifier: AGPL-3.0-only
"""Tk standalone/embedded configuration, sharing and owner-thread contracts."""
import threading
import time

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu


@pytest.fixture
def application():
    import tkinter as tk
    original = getattr(tk, '_default_root', None)
    value = app.Application('tkinter')
    value.native
    value.process_events()
    yield value
    root = value._backend._root
    value.quit()
    if root is not None and root is not original:
        try:
            alive = root.winfo_exists()
        except tk.TclError:
            alive = False
        if alive:
            root.destroy()


def wait(application, condition):
    deadline = time.monotonic() + 5
    while not condition():
        application.process_events()
        assert time.monotonic() < deadline, 'Tk capability acknowledgement timed out'
        time.sleep(.005)


@pytest.mark.parametrize('config,key', [
    ({'red_size': 16}, 'red_size'), ({'green_size': -1}, 'green_size'),
    ({'blue_size': 9}, 'blue_size'), ({'alpha_size': 16}, 'alpha_size'),
    ({'depth_size': 32}, 'depth_size'), ({'stencil_size': 16}, 'stencil_size'),
    ({'stereo': True}, 'stereo'), ({'double_buffer': True}, 'double_buffer'),
    ({'samples': 2}, 'samples'), ({'samples': -1}, 'samples'),
    ({'samples': True}, 'samples'),
])
def test_unsupported_configuration_fails_before_widget_or_native_owner(application, monkeypatch, config, key):
    root = application.native
    children = root.winfo_children()
    owners = []
    original = _dawn.register_canvas
    def register(*args, **kwargs):
        owners.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(_dawn, 'register_canvas', register)
    canvas = app.Canvas(app=application, config=config, create_native=False)
    try:
        with pytest.raises(RuntimeError, match=key):
            canvas.create_native()
        assert canvas._backend is None
        assert root.winfo_children() == children
        assert owners == []
    finally:
        canvas.close()


@pytest.mark.parametrize('kwargs,key', [
    ({'fullscreen': True}, 'fullscreen'), ({'position': (3, 4)}, 'position'),
    ({'resizable': False}, 'resizable'), ({'decorate': False}, 'decorate'),
    ({'always_on_top': True}, 'always_on_top'),
])
def test_embedded_window_manager_requests_fail_without_changing_parent(application, kwargs, key):
    root = application.native
    before = root.winfo_children()
    canvas = app.Canvas(app=application, parent=root, create_native=False, **kwargs)
    try:
        with pytest.raises(RuntimeError, match=key):
            canvas.create_native()
        assert canvas._backend is None
        assert root.winfo_children() == before
    finally:
        canvas.close()


@pytest.mark.parametrize('manager', ['pack', 'grid', 'place'])
def test_embedded_hide_show_restores_host_layout_and_binding(application, manager):
    import tkinter as tk
    root = application.native
    root.deiconify()
    parent = tk.Frame(root)
    parent.pack()
    canvas = app.Canvas(app=application, parent=parent, size=(30, 24))
    widget = canvas.native
    options = {'pack': {'padx': 3, 'pady': 5}, 'grid': {'row': 2, 'column': 3, 'padx': 7},
               'place': {'x': 9, 'y': 11, 'width': 30, 'height': 24}}[manager]
    getattr(widget, manager)(**options)
    seen = []
    binding = parent.bind('<<HostCapability>>', lambda event: seen.append(event), add='+')
    try:
        wait(application, lambda: widget.winfo_viewable())
        saved = getattr(widget, manager + '_info')()
        canvas.show(False)
        assert widget.winfo_manager() == ''
        assert parent.winfo_exists()
        canvas.show(True)
        wait(application, lambda: widget.winfo_viewable())
        assert getattr(widget, manager + '_info')() == saved
        assert parent.bind('<<HostCapability>>')
        parent.event_generate('<<HostCapability>>')
        application.process_events()
        assert len(seen) == 1
        canvas.close()
        assert parent.winfo_exists() and parent.bind('<<HostCapability>>')
    finally:
        canvas.close()
        parent.unbind('<<HostCapability>>', binding)
        parent.destroy()


@pytest.mark.parametrize('mode', ['standalone', 'embedded'])
@pytest.mark.parametrize('first_closed', [0, 1])
def test_shared_texture_updates_reach_both_consumers_and_survive_either_close(application, mode, first_closed):
    parent = application.native if mode == 'embedded' else None
    a = app.Canvas(app=application, parent=parent, size=(8, 6))
    b = app.Canvas(app=application, parent=parent, size=(8, 6), shared=a)
    a.set_current()
    source = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
    texture = gloo.Texture2D(np.array([[[255, 0, 0, 255]]], np.uint8))
    program = gloo.Program('attribute vec2 position; void main(){gl_Position=vec4(position,0,1);}',
                           'uniform sampler2D image; void main(){gl_FragColor=texture2D(image,vec2(.5));}')
    program['position'] = source
    program['image'] = texture
    def draw(c, color):
        c.set_current()
        gloo.set_viewport(0, 0, 8, 6)
        program.draw('triangles')
        assert np.all(gloo.read_pixels((0, 0, 8, 6), alpha=True) == color)
    try:
        assert a.context.shared is b.context.shared
        for c in (a, b):
            draw(c, [255, 0, 0, 255])
        texture.set_data(np.array([[[0, 255, 0, 255]]], np.uint8))
        for c in (b, a):
            draw(c, [0, 255, 0, 255])
        (a, b)[first_closed].close()
        survivor = (b, a)[first_closed]
        survivor.set_current()
        texture.set_data(np.array([[[0, 0, 255, 255]]], np.uint8))
        draw(survivor, [0, 0, 255, 255])
    finally:
        survivor = b if not b._closed else a
        if not survivor._closed:
            survivor.set_current()
            for resource in (program, source, texture):
                resource.delete()
            survivor.context.flush_commands()
        a.close()
        b.close()


def test_non_owner_thread_cannot_select_canvas(application):
    canvas = app.Canvas(app=application, size=(8, 6))
    errors = []
    def worker():
        try:
            canvas.set_current()
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(2)
    try:
        assert not thread.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], RuntimeError)
        assert 'UI thread' in str(errors[0])
    finally:
        canvas.close()


@pytest.mark.parametrize('config', [{}, {'double_buffer': False},
                                  {'red_size': 0, 'alpha_size': 0, 'depth_size': 0},
                                  {'depth_size': 16, 'stencil_size': 8},
                                  {'samples': 1}, {'samples': 4}])
def test_configuration_records_requested_minimums_and_actual_storage(application, config):
    canvas = app.Canvas(app=application, size=(13, 9), config=config)
    try:
        canvas.set_current()
        actual = gloo.get_gl_configuration()
        assert canvas.context._requested_config == config
        assert actual['red_size'] == actual['green_size'] == actual['blue_size'] == actual['alpha_size'] == 8
        assert actual['depth_size'] is None and actual['depth_size_minimum'] == 24
        assert actual['stencil_size'] == 8 and actual['stereo'] is False
        assert actual['double_buffer'] is False
        assert actual['sample_count'] == max(1, config.get('samples', 0))
    finally:
        canvas.close()


def test_standalone_window_options_and_mutations_reach_native_widget(application):
    canvas = app.Canvas(app=application, size=(80, 60), title='initial',
                        resizable=False, decorate=False, always_on_top=True)
    try:
        top = canvas._backend._top
        assert top.title() == 'initial'
        assert not any(map(bool, top.resizable()))
        assert bool(top.overrideredirect())
        # Topmost/fullscreen depend on WM acknowledgement; do not substitute
        # requested flags for an actual compositor/display qualification.
        canvas.title = 'updated'
        assert top.title() == canvas.title == 'updated'
        canvas.show()
        wait(application, lambda: canvas.native.winfo_viewable())
        canvas.size = (90, 70)
        wait(application, lambda: canvas.size == (90, 70))
        canvas.position = (15, 19)
        wait(application, lambda: canvas.position == (15, 19))
        canvas.show(False)
        assert top.state() == 'withdrawn'
        canvas.show(True)
        wait(application, lambda: canvas.native.winfo_viewable())
    finally:
        canvas.close()


def test_embedded_mutation_refusals_preserve_state_and_pack_order(application):
    import tkinter as tk
    root = application.native
    parent = tk.Frame(root)
    parent.pack()
    before = tk.Frame(parent)
    before.pack()
    canvas = app.Canvas(app=application, parent=parent, size=(13, 9))
    canvas.native.pack(side='left', padx=4)
    after = tk.Frame(parent)
    after.pack()
    try:
        original = parent.pack_slaves()
        for setter in (lambda: setattr(canvas, 'fullscreen', True),
                       lambda: setattr(canvas, 'position', (10, 12))):
            with pytest.raises(RuntimeError, match='controlled by the host'):
                setter()
        assert canvas.fullscreen is False
        assert parent.pack_slaves() == original
        canvas.show(False)
        canvas.show(False)
        canvas.show(True)
        canvas.show(True)
        assert parent.pack_slaves() == original
        canvas.show(False)
        canvas.close()
        assert canvas._backend._hidden_layout is None
        assert before.winfo_exists() and after.winfo_exists()
    finally:
        canvas.close()
        parent.destroy()


@pytest.mark.parametrize('operation', ['close', 'title', 'timer-stop', 'timer-start',
                                       'timer-interval', 'quit', 'process-events'])
def test_non_owner_thread_rejection_preserves_public_state_and_jobs(application, operation):
    canvas = app.Canvas(app=application, size=(13, 9), title='owner')
    timer = app.Timer(interval=60, app=application, start=operation != 'timer-start')
    before = (canvas._closed, canvas.title, timer.running, timer.interval,
              timer._backend._job, application._backend._quitting)
    errors = []
    operations = {'close': canvas.close, 'title': lambda: setattr(canvas, 'title', 'worker'),
                  'timer-stop': timer.stop, 'timer-start': timer.start,
                  'timer-interval': lambda: setattr(timer, 'interval', 30),
                  'quit': application.quit, 'process-events': application.process_events}
    def worker():
        try:
            operations[operation]()
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(2)
    try:
        assert not thread.is_alive()
        assert len(errors) == 1 and 'UI thread' in str(errors[0])
        assert (canvas._closed, canvas.title, timer.running, timer.interval,
                timer._backend._job, application._backend._quitting) == before
    finally:
        timer.stop()
        canvas.close()


def test_fullscreen_property_reports_native_acknowledgement(application):
    canvas = app.Canvas(app=application, size=(80, 60), show=True)
    try:
        wait(application, lambda: canvas.native.winfo_viewable())
        top = canvas._backend._top
        for fullscreen in (True, False):
            canvas.fullscreen = fullscreen
            wait(application, lambda: top.tk.getboolean(top.attributes('-fullscreen')) == fullscreen)
            assert canvas.fullscreen is fullscreen
        with pytest.raises(RuntimeError, match='monitor-index'):
            canvas.fullscreen = 1
        assert canvas.fullscreen is False
    finally:
        canvas.close()


def test_hidden_host_relayout_replaces_saved_placement(application):
    import tkinter as tk
    parent = tk.Frame(application.native)
    parent.pack()
    canvas = app.Canvas(app=application, parent=parent, size=(13, 9))
    try:
        canvas.native.pack(padx=3)
        canvas.show(False)
        canvas.native.grid(row=4, column=2, padx=9)
        canvas.show(True)
        assert canvas.native.winfo_manager() == 'grid'
        assert canvas.native.grid_info()['padx'] == 9
        assert canvas._backend._hidden_layout is None
    finally:
        canvas.close()
        parent.destroy()


@pytest.mark.parametrize('config', [{'red_size': 16}, {'double_buffer': True},
                                  {'stereo': True}, {'samples': 2}])
def test_invalid_request_does_not_allocate_an_interpreter_and_can_be_corrected(config):
    application = app.Application('tkinter')
    canvas = app.Canvas(app=application, config=config, create_native=False)
    try:
        assert application._backend._root is None
        with pytest.raises(RuntimeError, match='configuration'):
            canvas.create_native()
        assert application._backend._root is None
        assert canvas._backend is None
        defaults = gloo.get_default_config()
        for key in config:
            canvas.context.config[key] = False if key == 'double_buffer' else defaults[key]
        canvas.create_native()
        assert canvas._backend._dawn_canvas_id > 0
    finally:
        canvas.close()
        application.quit()
