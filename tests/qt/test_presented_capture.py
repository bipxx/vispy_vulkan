# SPDX-License-Identifier: AGPL-3.0-only
"""Real capture identity controls; no current-frame substitute for presentation."""
from pathlib import Path
from contextlib import contextmanager
import os
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
SIZE = (16, 12)
COLORS = [(1., 0., 0., .25), (0., 1., 0., .25),
          (0., 0., 1., .25), (1., 1., 0., .25)]


def expected(colors):
    # WebGPU scissor y passes through unchanged; the presentation fragment
    # samples source H-1-row. Thus source low-Y occupies high output rows.
    image = np.empty((12, 16, 4), np.uint8)
    for index, (x, y) in enumerate(((0, 0), (8, 0), (0, 6), (8, 6))):
        r, g, b, _ = colors[index]
        image[12-y-6:12-y, x:x+8] = [round(b*255), round(g*255), round(r*255), 64]
    return image


class Scene:
    def __init__(self, name, backend='pyqt6'):
        from vispy import app, gloo, _dawn
        base = os.environ.get('VISPY_PRESENTED_CAPTURE_EVIDENCE')
        assert base, 'provide a fresh managed evidence path'
        self.output = Path(base)/name
        self.output.mkdir(parents=True, exist_ok=False)
        self.gloo, self.native, self.backend = gloo, _dawn, backend
        self.colors, self.draws, self.reads = list(COLORS), 0, 0
        self.canvas = app.Canvas(app=backend, size=SIZE, show=False, vsync=False,
                                 decorate=False, config={'samples': 0})
        self.identifier = self.canvas._backend._dawn_canvas_id
        self.canvas.events.draw.ignore_callback_errors = False
        self.canvas.events.draw.connect(self.draw, position='first')
        self.canvas.set_current()
        if backend == 'pyqt6':
            assert os.environ.get('VISPY_QT_PRESENTATION') == 'native'
            self.canvas.show()
        self.display()
        assert tuple(self.canvas.physical_size) == SIZE
        config = self.native.framebuffer_config(self.identifier)
        assert (config['width'], config['height']) == SIZE

    def draw(self, event):
        self.draws += 1
        self.gloo.set_viewport(0, 0, *SIZE)
        self.gloo.set_state(blend=False, depth_test=False, stencil_test=False,
                            scissor_test=True, cull_face=False)
        self.gloo.set_color_mask(True, True, True, True)
        for index, (x, y) in enumerate(((0, 0), (8, 0), (0, 6), (8, 6))):
            self.gloo.set_scissor(x, y, 8, 6)
            self.gloo.clear(color=self.colors[index], depth=False, stencil=False)
        self.gloo.set_state(scissor_test=False)
        self.gloo.set_clear_color((0., 0., 0., .25))

    def settle(self):
        deadline = time.monotonic()+5
        while True:
            if self.backend == 'pyqt6':
                self.canvas.app.process_events()
            self.native.process_events()
            state = self.native.probe()
            if not any(state[name] for name in ('pending_tickets', 'queued_frames', 'pending_timestamp_frames')):
                return
            assert time.monotonic() < deadline, 'capture scene did not retire'
            time.sleep(.001)

    def display(self):
        if self.backend == 'pyqt6':
            before = self.draws
            self.canvas.update()
            deadline = time.monotonic()+5
            while self.draws == before:
                self.canvas.app.process_events()
                assert time.monotonic() < deadline, 'shown native Qt paint did not arrive'
                time.sleep(.001)
        else:
            self.draw(None)
            self.canvas.context.flush_commands()
            self.native.present(self.identifier)
        self.settle()

    def capture(self):
        image = np.asarray(self.native.read_presented(self.identifier, 0, 0, *SIZE)).copy()
        np.save(self.output/f'capture-{self.reads}.bgra.npy', image, allow_pickle=False)
        self.reads += 1
        return image

    def close(self):
        canvas = getattr(self, 'canvas', None)
        if canvas is not None:
            canvas.close()


@contextmanager
def opened_scene(name, backend='pyqt6'):
    value = Scene.__new__(Scene)
    try:
        value.__init__(name, backend)
        yield value
    finally:
        native = getattr(value, 'native', None)
        try:
            if native is not None:
                native.diagnostic_submission_controls(False, '')
        finally:
            value.close()


@pytest.fixture
def scene(request):
    with opened_scene(request.node.name) as value:
        yield value


def test_two_asymmetric_native_frames_and_repeat_capture_keep_identity(scene):
    before = dict(scene.native.probe())
    first = scene.capture()
    np.testing.assert_array_equal(first, expected(COLORS))
    captured = dict(scene.native.probe())
    again = scene.capture()
    repeated = dict(scene.native.probe())
    np.testing.assert_array_equal(again, first)
    assert captured['application_presents'] == repeated['application_presents'] == before['application_presents']
    assert captured['render_passes']-before['render_passes'] == 1
    assert repeated['render_passes'] == captured['render_passes']
    assert scene.native.benchmark_completions(scene.identifier) == []
    assert scene.native.benchmark_gpu_timings(scene.identifier) == []
    scene.colors = COLORS[2:]+COLORS[:2]
    scene.display()
    second = scene.capture()
    np.testing.assert_array_equal(second, expected(scene.colors))
    assert not np.array_equal(second, first)


@pytest.mark.parametrize('cached', [False, True])
def test_unpresented_color_write_never_becomes_the_last_presented_image(scene, cached):
    previous = scene.capture() if cached else None
    before = dict(scene.native.probe())
    scene.canvas.set_current()
    scene.gloo.clear(color=(1., 1., 1., 1.))
    scene.canvas.context.flush_commands()
    scene.native.finish(scene.identifier)  # Explicit presentation-free write/retirement.
    assert scene.native.probe()['application_presents'] == before['application_presents']
    if cached:
        np.testing.assert_array_equal(scene.capture(), previous)
    else:
        with pytest.raises(RuntimeError, match='read_presented unavailable'):
            scene.capture()
    scene.display()
    np.testing.assert_array_equal(scene.capture(), expected(scene.colors))


@pytest.mark.parametrize('query_replacement', [False, True])
def test_partial_invalid_configuration_and_target_replacement_reject_old_capture(scene, query_replacement):
    scene.capture()
    with pytest.raises(RuntimeError, match='sample counts'):
        scene.native.configure_canvas(scene.identifier, 24, 18, 3)
    if query_replacement:
        # The failed call changed dimensions; this read-only public query
        # materializes a replacement target and must invalidate capture data.
        scene.native.framebuffer_config(scene.identifier)
    with pytest.raises(RuntimeError, match='read_presented unavailable'):
        scene.capture()
    scene.native.configure_canvas(scene.identifier, *SIZE, 1)
    scene.display()
    np.testing.assert_array_equal(scene.capture(), expected(scene.colors))


@pytest.mark.parametrize('action', ['detach', 'device-loss'])
def test_surface_or_device_replacement_never_serves_an_old_capture(scene, action):
    scene.capture()
    if action == 'detach':
        scene.native.clear_surface(scene.identifier)
    else:
        scene.native.lose_device()
    with pytest.raises(RuntimeError):
        scene.capture()


def test_headless_converted_mirror_remains_readable_without_surface_success(request):
    with opened_scene(request.node.name, backend='dawn_headless') as value:
        assert value.native.benchmark_surface_info(value.identifier)['attached'] is False
        np.testing.assert_array_equal(value.capture(), expected(COLORS))
        np.testing.assert_array_equal(value.capture(), expected(COLORS))
