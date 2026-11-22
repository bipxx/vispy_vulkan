# -*- coding: utf-8 -*-
"""CPU contract tests for API-05: Application, use_app, Canvas, Timer, GLContext, and GLShared."""

from contextlib import contextmanager
import gc
import os
import types
import warnings

import numpy as np
import pytest

from vispy import config
from vispy.app import Application, Canvas, KeyEvent, MouseEvent, Timer, use_app
import vispy.app._default_app as default_app_mod
import vispy.app.application as application_mod
from vispy.app.base import BaseApplicationBackend, BaseCanvasBackend, BaseTimerBackend
from vispy.app.canvas import DrawEvent, ResizeEvent
from vispy.gloo import context as context_mod
from vispy.gloo.context import (
    FakeCanvas,
    GLContext,
    GLShared,
    forget_canvas,
    get_current_canvas,
    get_default_config,
    set_current_canvas,
)
from vispy.gloo.glir import BaseGlirParser
from vispy.util import keys as key_constants


class _RecordingParser(BaseGlirParser):
    """Pure-CPU GLIR parser recording command batches without touching Dawn."""

    def __init__(self):
        super().__init__()
        self.canvas_id = 0
        self.batches = []
        self.capabilities = dict(gl_version='CPU Contract Stub', max_texture_size=4096)

    @property
    def shader_compatibility(self):
        return 'desktop'

    def is_remote(self):
        return False

    def parse(self, commands):
        self.batches.append(list(commands))


def _make_stub_backend_module(backend_label='StubBackend', dawn_canvas_seed=100):
    """Build an in-memory pure-CPU backend module implementing vispy.app.base contracts."""
    state = {
        'next_canvas_id': dawn_canvas_seed,
        'reuse_calls': 0,
        'process_calls': 0,
        'run_calls': 0,
        'quit_calls': 0,
        'sleep_durations': [],
        'prepared_parents': [],
        'validated_kwargs': [],
        'timers': [],
    }

    class ApplicationBackend(BaseApplicationBackend):
        def _vispy_get_backend_name(self):
            return backend_label

        def _vispy_process_events(self):
            state['process_calls'] += 1

        def _vispy_run(self):
            state['run_calls'] += 1
            return 'ran'

        def _vispy_reuse(self):
            state['reuse_calls'] += 1

        def _vispy_quit(self):
            state['quit_calls'] += 1

        def _vispy_sleep(self, duration_sec):
            state['sleep_durations'].append(float(duration_sec))

        def _vispy_validate_canvas(self, kwargs):
            state['validated_kwargs'].append(dict(kwargs))

        def _vispy_prepare_canvas(self, parent):
            state['prepared_parents'].append(parent)

    class CanvasBackend(BaseCanvasBackend):
        def __init__(self, vispy_canvas, **kwargs):
            BaseCanvasBackend.__init__(self, vispy_canvas)
            p = self._process_backend_kwargs(kwargs)
            self._title = p.title
            self._size = tuple(int(v) for v in p.size)
            self._pos = (0, 0) if p.position is None else tuple(int(v) for v in p.position)
            self._visible = bool(p.show)
            self._fullscreen = p.fullscreen
            self._scale = 1.0
            self._closed = False
            self._swap_count = 0
            self._update_count = 0
            self._current_count = 0
            state['next_canvas_id'] += 1
            self._dawn_canvas_id = state['next_canvas_id']
            p.context.shared.add_ref(backend_label, vispy_canvas)
            if not isinstance(p.context.shared.parser, _RecordingParser):
                p.context.shared._parser = _RecordingParser()

        def _vispy_set_current(self):
            self._current_count += 1

        def _vispy_swap_buffers(self):
            self._swap_count += 1

        def _vispy_set_title(self, title):
            self._title = str(title)

        def _vispy_set_size(self, w, h):
            self._size = (int(w), int(h))

        def _vispy_set_position(self, x, y):
            self._pos = (int(x), int(y))

        def _vispy_set_visible(self, visible):
            self._visible = bool(visible)

        def _vispy_set_fullscreen(self, fullscreen):
            self._fullscreen = fullscreen

        def _vispy_update(self):
            self._update_count += 1

        def _vispy_close(self):
            self._closed = True
            self._vispy_canvas._backend_destroyed()

        def _vispy_get_size(self):
            return self._size

        def _vispy_get_physical_size(self):
            return (int(round(self._size[0] * self._scale)),
                    int(round(self._size[1] * self._scale)))

        def _vispy_get_position(self):
            return self._pos

        def _vispy_get_fullscreen(self):
            return bool(self._fullscreen)

        def _vispy_warmup(self):
            pass

    class TimerBackend(BaseTimerBackend):
        def __init__(self, vispy_timer):
            BaseTimerBackend.__init__(self, vispy_timer)
            self.started = False
            self.last_interval = None
            self.start_calls = 0
            self.stop_calls = 0
            state['timers'].append(self)

        def _vispy_start(self, interval):
            self.started = True
            self.last_interval = float(interval)
            self.start_calls += 1

        def _vispy_stop(self):
            self.started = False
            self.stop_calls += 1

    mod = types.ModuleType('_vispy_cpu_stub_backend')
    mod.capability = dict(
        title=True,
        size=True,
        position=True,
        show=True,
        vsync=True,
        resizable=True,
        decorate=True,
        fullscreen=True,
        context=True,
        multi_window=True,
        scroll=True,
        parent=True,
        always_on_top=True,
    )
    mod.ApplicationBackend = ApplicationBackend
    mod.CanvasBackend = CanvasBackend
    mod.TimerBackend = TimerBackend
    return mod, state


def _make_stub_app(backend_label='StubBackend'):
    mod, state = _make_stub_backend_module(backend_label=backend_label)
    app = Application.__new__(Application)
    app._backend_module = mod
    app._backend = mod.ApplicationBackend()
    return app, mod, state


@contextmanager
def _isolated_global_app_and_context():
    orig_default_app = default_app_mod.default_app
    orig_default_backend = config['default_backend']
    orig_canvasses = list(context_mod.canvasses)
    orig_gallery = os.environ.get('_VISPY_RUNNING_GALLERY_EXAMPLES')
    try:
        yield
    finally:
        default_app_mod.default_app = orig_default_app
        config['default_backend'] = orig_default_backend
        context_mod.canvasses[:] = orig_canvasses
        if orig_gallery is None:
            os.environ.pop('_VISPY_RUNNING_GALLERY_EXAMPLES', None)
        else:
            os.environ['_VISPY_RUNNING_GALLERY_EXAMPLES'] = orig_gallery


def test_api05_app_selection_use_app_reuse_and_gallery_shortcircuit():
    with _isolated_global_app_and_context():
        with pytest.raises(ValueError, match='backend_name must be one of'):
            Application('totally_nonexistent_backend')

        for legacy in ('pyqt4', 'pyside', 'pyside2', 'glfw', 'pyglet', 'sdl2', 'wx', 'egl', 'osmesa'):
            with pytest.raises(RuntimeError, match='OpenGL'):
                Application(legacy)

        config['default_backend'] = 'pyglet'
        with pytest.raises(RuntimeError, match='OpenGL'):
            Application('default')
        config['default_backend'] = 'auto'

        stub_app, _, state = _make_stub_app('PyQt6')
        default_app_mod.default_app = stub_app

        returned = use_app()
        assert returned is stub_app
        assert state['reuse_calls'] == 1

        returned_no_reuse = use_app('pyqt6', call_reuse=False)
        assert returned_no_reuse is stub_app
        assert state['reuse_calls'] == 1

        returned_matching = use_app('PyQt6', call_reuse=True)
        assert returned_matching is stub_app
        assert state['reuse_calls'] == 2

        with pytest.raises(RuntimeError, match='Can only select a backend once'):
            use_app('tkinter')

        assert stub_app.backend_name == 'PyQt6'
        assert stub_app.native is stub_app._backend
        assert 'PyQt6' in repr(stub_app)

        stub_app.process_events()
        stub_app.sleep(0.0125)
        stub_app.quit()
        assert state['process_calls'] == 1
        assert state['sleep_durations'] == [0.0125]
        assert state['quit_calls'] == 1

        os.environ.pop('_VISPY_RUNNING_GALLERY_EXAMPLES', None)
        assert stub_app.run(allow_interactive=False) == 'ran'
        assert state['run_calls'] == 1

        os.environ['_VISPY_RUNNING_GALLERY_EXAMPLES'] = '1'
        assert stub_app.run() == 0
        assert state['run_calls'] == 1

        assert isinstance(stub_app.is_interactive(), bool)
        assert isinstance(stub_app.is_notebook(), bool)


def test_api05_app_use_app_fresh_initialization_and_subsequent_reuse():
    with _isolated_global_app_and_context():
        default_app_mod.default_app = None
        mod, state = _make_stub_backend_module('Dawn_Headless')
        orig_use = Application._use

        def _fake_use(self, backend_nam=None):
            self._backend_module = mod
            self._backend = mod.ApplicationBackend()

        Application._use = _fake_use
        try:
            created = use_app('dawn_headless', call_reuse=True)
            assert default_app_mod.default_app is created
            assert created.backend_name == 'Dawn_Headless'
            # Initial creation constructs Application without reuse(); reuse() runs on subsequent use_app().
            assert state['reuse_calls'] == 0
            reused = use_app('dawn_headless', call_reuse=True)
            assert reused is created
            assert state['reuse_calls'] == 1
        finally:
            Application._use = orig_use


def test_api05_app_canvas_validation_deferred_native_and_close_idempotence():
    with _isolated_global_app_and_context():
        stub_app, _, state = _make_stub_app('StubCanvasHost')

        with pytest.raises(ValueError, match='Invalid value for app'):
            Canvas(app=object(), create_native=False)
        with pytest.raises(TypeError, match='config must be a dict'):
            Canvas(app=stub_app, config=['not', 'a', 'dict'], create_native=False)
        with pytest.raises(TypeError, match='shared must be a Canvas'):
            Canvas(app=stub_app, shared='invalid_shared', create_native=False)
        with pytest.raises(TypeError, match='fullscreen must be bool or int'):
            Canvas(app=stub_app, fullscreen='yes', create_native=False)
        with pytest.raises(ValueError, match='must be "interactive"'):
            Canvas(app=stub_app, keys='bogus', create_native=False)
        with pytest.raises(TypeError, match='keys must be a dict, str, or None'):
            Canvas(app=stub_app, keys=42, create_native=False)
        with pytest.raises(ValueError, match='is not an attribute of Canvas'):
            Canvas(app=stub_app, keys={'escape': 'nonexistent_canvas_method'}, create_native=False)
        with pytest.raises(TypeError, match='is not callable'):
            Canvas(app=stub_app, keys={'escape': 99}, create_native=False)

        parent_sentinel = object()
        canvas = Canvas(
            app=stub_app,
            title='Deferred Canvas',
            size=(320, 200),
            position=(15, 25),
            px_scale=2,
            keys='interactive',
            parent=parent_sentinel,
            create_native=False,
        )
        assert canvas._backend is None
        with pytest.raises(AttributeError):
            _ = canvas.native

        canvas.create_native()
        assert state['prepared_parents'] == [parent_sentinel]
        assert len(state['validated_kwargs']) == 1
        assert canvas._backend is not None
        assert canvas.native is canvas._backend
        assert canvas.title == 'Deferred Canvas'
        canvas.title = 'Renamed Canvas'
        assert canvas.title == 'Renamed Canvas'
        assert canvas.size == (320, 200)
        assert canvas._backend._vispy_get_size() == (640, 400)
        assert canvas.physical_size == (640, 400)
        assert canvas.pixel_scale == pytest.approx(2.0)
        assert canvas.position == (15, 25)
        assert canvas.fullscreen is False
        canvas.fullscreen = True
        assert canvas.fullscreen is True

        canvas._backend._scale = 1.5
        assert canvas.physical_size == (960, 600)
        assert canvas.pixel_scale == pytest.approx(3.0)

        canvas.dpi = 144.0
        assert canvas.dpi == pytest.approx(144.0)
        assert 'StubCanvasHost' in repr(canvas)

        canvas.set_current()
        assert get_current_canvas() is canvas
        assert canvas.context.shared.parser.canvas_id == canvas._backend._dawn_canvas_id

        close_events = []
        canvas.events.close.connect(lambda ev: close_events.append(ev.type))
        canvas.close()
        assert canvas._closed is True
        assert canvas._backend is None
        assert len(close_events) == 1
        assert get_current_canvas() is not canvas

        # Closing again or receiving _backend_destroyed after close must be idempotent.
        canvas.close()
        canvas._backend_destroyed()
        canvas.create_native()
        assert len(close_events) == 1
        assert canvas._backend is None


def test_api05_app_canvas_events_connect_keys_mouse_drag_and_fps():
    with _isolated_global_app_and_context():
        stub_app, _, _ = _make_stub_app('StubEventsHost')
        triggered_custom = []

        with Canvas(
            app=stub_app,
            size=(200, 150),
            keys={'r': lambda: triggered_custom.append('reset'), 'u': 'update', 'escape': 'close'},
        ) as canvas:
            draw_Log = []

            @canvas.connect
            def on_draw(event):
                draw_Log.append((event.type, event.region))

            with pytest.raises(ValueError, match='should start with "on_"'):
                canvas.connect(lambda ev: None)

            def on_unknown_event(event):
                pass

            with pytest.raises(ValueError, match='not available on this canvas'):
                canvas.connect(on_unknown_event)

            paint_events = []
            paint_cb = lambda ev: paint_events.append(ev.type)
            canvas.events.paint.connect(paint_cb)
            assert canvas.events.paint._warned is True

            canvas.events.draw(region=(0, 0, 200, 150))
            assert draw_Log == [('draw', (0, 0, 200, 150))]
            assert paint_events == ['draw']
            assert canvas._backend._swap_count == 1

            fps_samples = []
            canvas.measure_fps(window=0.0, callback=lambda fps: fps_samples.append(fps))
            canvas.events.draw()
            assert len(fps_samples) >= 1
            canvas.measure_fps(callback=False)
            count_after_disable = len(fps_samples)
            canvas.events.draw()
            assert len(fps_samples) == count_after_disable

            # Mouse press -> drag move -> release & double-click contracts.
            backend = canvas._backend
            double_clicks = []
            canvas.events.mouse_double_click.connect(
                lambda ev: double_clicks.append((ev.type, tuple(ev.last_event.pos)))
            )

            p1 = backend._vispy_mouse_press(
                pos=(20, 30), button=1, buttons=[1], modifiers=(key_constants.SHIFT,)
            )
            assert isinstance(p1, MouseEvent)
            assert tuple(p1.pos) == (20, 30)
            assert p1.button == 1
            assert p1.buttons == [1]
            assert p1.modifiers == (key_constants.SHIFT,)
            assert p1.is_dragging is False

            backend._last_time = 0.0
            m1 = backend._vispy_mouse_move(pos=(45, 55), buttons=[1], modifiers=(key_constants.SHIFT,))
            assert m1 is not None
            assert m1.is_dragging is True
            assert m1.press_event is p1
            assert m1.last_event is p1
            assert m1.drag_events() == [m1]

            backend._last_time = 0.0
            m2 = backend._vispy_mouse_move(pos=(50, 65), buttons=[1], modifiers=(key_constants.SHIFT,))
            assert m2 is not None
            assert m2.drag_events() == [m1, m2]
            assert m2.trail().shape == (2, 2)

            r1 = backend._vispy_mouse_release(pos=(45, 55), button=1, buttons=[], modifiers=())
            assert r1.is_dragging is True
            assert backend._vispy_mouse_data['press_event'] is None

            # Two consecutive presses at identical coordinates trigger synthetic double-click.
            backend._vispy_mouse_press(pos=(60, 70), button=1, buttons=[1], modifiers=())
            backend._vispy_mouse_release(pos=(60, 70), button=1, buttons=[], modifiers=())
            backend._vispy_mouse_press(pos=(60, 70), button=1, buttons=[1], modifiers=())
            backend._vispy_mouse_release(pos=(60, 70), button=1, buttons=[], modifiers=())
            assert double_clicks == [('mouse_double_click', (60, 70))]

            w_ev = canvas.events.mouse_wheel(pos=(10, 12), delta=(0.0, 1.5), modifiers=(key_constants.CONTROL,))
            assert tuple(w_ev.delta) == pytest.approx((0.0, 1.5))

            r_ev = canvas.events.resize(size=(240, 180), physical_size=(480, 360))
            assert isinstance(r_ev, ResizeEvent)
            assert r_ev.size == (240, 180)
            assert r_ev.physical_size == (480, 360)

            k_r = KeyEvent('key_press', key=key_constants.Key('R'), text='r', modifiers=())
            canvas.events.key_press(k_r)
            assert triggered_custom == ['reset']

            updates_before = canvas._backend._update_count
            canvas.events.key_press(KeyEvent('key_press', key=key_constants.Key('U'), text='u', modifiers=()))
            assert canvas._backend._update_count == updates_before + 1

            canvas.events.key_press(KeyEvent('key_press', key=key_constants.ESCAPE, text='', modifiers=()))
            assert canvas._closed is True

        assert canvas._closed is True


def test_api05_app_timer_single_shot_repeating_and_restart_contracts():
    with _isolated_global_app_and_context():
        stub_app, _, state = _make_stub_app('StubTimerHost')

        with pytest.raises(ValueError, match='Invalid value for app'):
            Timer(app=12345)

        auto_timer = Timer(interval='auto', app=stub_app, start=False)
        assert auto_timer.interval == pytest.approx(1.0 / 60.0)
        assert auto_timer.app is stub_app
        assert auto_timer.native is auto_timer._backend
        assert auto_timer.running is False

        records = []
        starts = []
        stops = []

        def _on_tick(event):
            records.append((event.iteration, event.count, event.dt >= 0.0, event.elapsed >= 0.0))

        timer = Timer(interval=0.05, connect=_on_tick, iterations=3, start=False, app=stub_app)
        timer.events.start.connect(lambda ev: starts.append(ev.type))
        timer.events.stop.connect(lambda ev: stops.append(ev.type))
        t_backend = timer._backend

        timer.start()
        assert timer.running is True
        assert t_backend.started is True
        assert t_backend.start_calls == 1
        assert t_backend.last_interval == pytest.approx(0.05)
        assert len(starts) == 1

        # Calling start() without parameter updates while already running is a no-op.
        timer.start()
        assert t_backend.start_calls == 1

        # Updating interval while running stops and restarts the backend timer.
        timer.interval = 0.125
        assert timer.running is True
        assert t_backend.stop_calls == 1
        assert t_backend.start_calls == 2
        assert t_backend.last_interval == pytest.approx(0.125)

        timer._timeout()
        assert timer.running is True
        assert timer.iter_count == 1
        timer._timeout()
        assert timer.running is True
        assert timer.iter_count == 2
        timer._timeout()
        # Final max_iterations tick auto-stops immediately after firing the 3rd callback.
        assert timer.running is False
        assert t_backend.started is False
        assert timer.iter_count == 3
        assert len(stops) == 2
        # Calling _timeout() again after auto-stop is a no-op.
        timer._timeout()
        assert timer.running is False
        assert t_backend.started is False
        assert timer.iter_count == 3
        assert [r[:2] for r in records] == [(0, 0), (1, 1), (2, 2)]
        assert all(r[2] and r[3] for r in records)
        # 1 stop during running interval update + 1 stop when max_iterations is reached.
        assert len(stops) == 2

        # Restarting as single-shot resets iter_count and stops immediately on that 1st callback.
        timer.start(interval=0.02, iterations=1)
        assert timer.iter_count == 0
        assert timer.max_iterations == 1
        assert timer.running is True
        timer._timeout()
        assert timer.iter_count == 1
        assert timer.running is False
        timer._timeout()
        assert timer.running is False
        assert timer.iter_count == 1

        # Disconnect removes callback cleanly.
        timer.disconnect(_on_tick)
        before = len(records)
        timer.start(iterations=2)
        timer._timeout()
        timer.stop()
        assert len(records) == before


def test_api05_app_glcontext_glshared_and_fakecanvas_contracts():
    with _isolated_global_app_and_context():
        cfg = get_default_config()
        assert set(cfg) == {
            'red_size', 'green_size', 'blue_size', 'alpha_size',
            'depth_size', 'stencil_size', 'double_buffer', 'stereo', 'samples',
        }
        cfg['samples'] = 16
        assert get_default_config()['samples'] == 0

        with pytest.raises(KeyError):
            GLContext({'not_a_config_key': 1})
        with pytest.raises(TypeError):
            GLContext({'samples': '4'})

        shared = GLShared()
        assert isinstance(shared, GLShared)
        with pytest.raises(RuntimeError, match='No reference'):
            _ = shared.ref

        class _Owner:
            pass

        o1 = _Owner()
        o2 = _Owner()
        shared.add_ref('StubBackend', o1)
        assert shared.name == 'StubBackend'
        assert shared.ref is o1
        shared.add_ref('StubBackend', o2)
        with pytest.raises(RuntimeError, match='same type'):
            shared.add_ref('DifferentBackend', o2)
        assert 'StubBackend' in repr(shared)

        del o1
        gc.collect()
        assert shared.ref is o2

        stub_app, _, _ = _make_stub_app('StubShareHost')
        c1 = Canvas(app=stub_app, size=(64, 64))
        c2 = Canvas(app=stub_app, size=(64, 64), shared=c1)
        c3 = Canvas(app=stub_app, size=(64, 64), shared=c1.context)
        try:
            assert c1.context.shared is c2.context.shared
            assert c1.context.shared is c3.context.shared
            parser = c1.context.shared.parser
            assert isinstance(parser, _RecordingParser)

            set_current_canvas(c1)
            assert get_current_canvas() is c1
            assert parser.canvas_id == c1._backend._dawn_canvas_id

            c1.context.set_viewport(2, 4, 60, 56)
            assert c1.context.get_viewport() == (2, 4, 60, 56)
            c1.context.flush_commands()
            assert any(cmd[0] == 'CURRENT' for batch in parser.batches for cmd in batch)
            assert any(cmd[:2] == ('FUNC', 'glViewport') for batch in parser.batches for cmd in batch)

            set_current_canvas(c2)
            assert get_current_canvas() is c2
            assert parser.canvas_id == c2._backend._dawn_canvas_id

            forget_canvas(c2)
            assert get_current_canvas() is c1
        finally:
            c3.close()
            c2.close()
            c1.close()

        fake = FakeCanvas()
        fake_parser = _RecordingParser()
        fake.context.shared.parser = fake_parser
        assert get_current_canvas() is fake
        fake.context.set_clear_color((0.1, 0.2, 0.3, 1.0))
        fake.flush()
        assert any(cmd[0] == 'CURRENT' for batch in fake_parser.batches for cmd in batch)
        assert any(cmd[:2] == ('FUNC', 'glClearColor') for batch in fake_parser.batches for cmd in batch)
        forget_canvas(fake)


__all__ = [name for name in globals() if name.startswith('test_')]
