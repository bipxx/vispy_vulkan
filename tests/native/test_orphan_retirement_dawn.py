# SPDX-License-Identifier: AGPL-3.0-only
"""Installed matching-native lifetime controls, each in a fresh process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
import vispy


CHILD = r'''
from pathlib import Path
import gc, hashlib, importlib.util, json, threading, time, weakref
import numpy as np
import vispy
assert Path(vispy.__file__).resolve() == Path(EXPECTED_VISPY)
from vispy import _dawn, app, gloo
assert _dawn.object_retirement_contract_version == 1
NAMES = ('pending_tickets', 'queued_frames', 'live_buffer_bytes',
         'live_cpu_buffer_bytes', 'live_texture_bytes', 'canvas_texture_bytes',
         'transient_buffer_bytes', 'line_resource_pool_busy_slots',
         'line_resource_pool_bytes', 'host_import_pinned_bytes')
def gauges():
    probe = _dawn.probe()
    return {n: probe[n] for n in NAMES}
def collect(worker=False):
    if worker:
        errors = []
        def run():
            try: gc.collect()
            except BaseException as error: errors.append(repr(error))
        thread = threading.Thread(target=run)
        thread.start(); thread.join(timeout=15)
        assert not thread.is_alive(), 'helper-thread collection did not finish'
        assert not errors, errors
        assert any(c['thread'] == thread.ident and c['retired'] > 0
                   for c in retirement_calls), retirement_calls
    else:
        gc.collect()
    application.process_events()
    deadline = time.monotonic() + 15
    while True:
        more = _dawn.process_events()
        if not more and _dawn.probe()['pending_tickets'] == 0:
            break
        assert time.monotonic() < deadline, 'resource retirement did not quiesce'
        time.sleep(.001)
def image(canvas):
    canvas.set_current()
    return gloo.read_pixels((0, 0, 16, 16), alpha=True)
def assert_color(canvas, rgba):
    np.testing.assert_array_equal(image(canvas), np.broadcast_to(rgba, (16, 16, 4)))
VERTEX = ''' + '"""' + r'''
attribute vec2 a_position;
varying vec2 v_uv;
void main() { gl_Position = vec4(a_position, 0., 1.); v_uv = (a_position + 1.) * .5; }
''' + '"""' + r'''
FRAGMENT = ''' + '"""' + r'''
uniform sampler2D u_texture;
varying vec2 v_uv;
void main() { gl_FragColor = texture2D(u_texture, v_uv); }
''' + '"""' + r'''
def make(rgba):
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), show=False,
                        config={'samples': 0})
    canvas.set_current()
    program = gloo.Program(VERTEX, FRAGMENT)
    buffer = gloo.VertexBuffer(np.array([[-1., -1.], [1., -1.], [-1., 1.], [1., 1.]], np.float32))
    texture = gloo.Texture2D(np.array([[rgba]], np.uint8), interpolation='nearest')
    program['a_position'] = buffer
    program['u_texture'] = texture
    program.draw('triangle_strip')
    assert_color(canvas, rgba)
    # Force cyclic collection, rather than reference-count teardown on the main
    # thread, when the caller requests the helper-thread control.
    canvas._retirement_program = program
    program._retirement_canvas = canvas
    return canvas, program, buffer, texture
unraisable = []
previous_unraisable = __import__('sys').unraisablehook
__import__('sys').unraisablehook = lambda event: unraisable.append(repr(event.exc_value))
application = app.use_app('pyqt6' if CASE == 'panzoom' else 'dawn_headless')
observations = []
retirement_calls = []
original_retire = _dawn.retire_objects
gc_was_enabled = gc.isenabled()
if CASE == 'worker':
    # Instrument only this API boundary; delegate every call to the real native
    # function. Suppress automatic main-thread cycle collection for this case.
    def observed_retire(ids):
        retired = original_retire(ids)
        retirement_calls.append(dict(thread=threading.get_ident(), retired=retired))
        return retired
    _dawn.retire_objects = observed_retire
    gc.disable()
try:
    baseline = gauges()
    assert not any(baseline.values()), baseline
    if CASE == 'unknown':
        before = _dawn.probe()
        assert _dawn.retire_objects([0, -1, 2147483647, 2147483647]) == 0
        assert _dawn.retire_objects([]) == 0
        after = _dawn.probe()
        assert gauges() == baseline
        for n in ('native_batches', 'native_commands', 'dawn_queue_submits', 'application_presents'):
            assert after[n] == before[n], (n, before[n], after[n])
    elif CASE in ('peer', 'worker'):
        peer, peer_program, peer_buffer, peer_texture = make([0, 0, 255, 255])
        peer_baseline = gauges()
        for index in range(3):
            canvas, program, buffer, texture = make([255, 0, 0, 255])
            refs = [weakref.ref(v) for v in (canvas, program, buffer, texture)]
            canvas.close()
            del canvas, program, buffer, texture
            collect(CASE == 'worker')
            assert all(ref() is None for ref in refs)
            assert gauges() == peer_baseline, (index, peer_baseline, gauges())
            assert_color(peer, [0, 0, 255, 255])
            observations.append(dict(iteration=index, gauges=gauges()))
        peer.close()
        del peer, peer_program, peer_buffer, peer_texture
        collect()
    elif CASE == 'snapshot':
        canvas, program, buffer, texture = make([255, 0, 0, 255])
        canvas.set_current()
        texture.set_data(np.array([[[0, 255, 0, 255]]], np.uint8))
        program.draw('triangle_strip')
        canvas.context.flush_commands()
        assert _dawn.probe()['pending_draws'] > 0
        ids = [program.id, buffer.id, texture.id]
        assert _dawn.retire_objects(ids + ids) == 3
        assert _dawn.retire_objects(ids) == 0
        assert_color(canvas, [0, 255, 0, 255])
        canvas.close()
        del canvas, program, buffer, texture
        collect()
    elif CASE == 'held-context':
        canvas, program, buffer, texture = make([255, 0, 0, 255])
        context = canvas.context
        canvas.close()
        del canvas, program, buffer, texture
        collect()
        assert any(c[0] == 'DELETE' for c in context.glir._shared._commands)
        try:
            context.flush_commands()
        except RuntimeError as error:
            assert 'missing canvas 0' in str(error), repr(error)
        else:
            raise AssertionError('normal flush must still reject the missing canvas')
        assert gauges() == baseline, gauges()
        del context
        collect()
    elif CASE.startswith('host-import'):
        assert _dawn.device_info()['host_mapped_pointer'], 'profile lacks host-import support'
        canvas, program, buffer, texture = make([255, 0, 0, 255])
        canvas.set_current()
        texture.set_data(np.broadcast_to(np.array([255, 0, 0, 255], np.uint8),
                                        (512, 512, 4)).copy())
        program.draw('triangle_strip')
        assert_color(canvas, [255, 0, 0, 255])
        assert _dawn.probe()['host_import_pinned_bytes'] > 0
        canvas.close()
        before_submits = _dawn.probe()['dawn_queue_submits']
        del canvas, program, buffer, texture
        failure = {'host-import-fail-before-submit': 'before-submit',
                   'host-import-fail-callback': 'callback-registration'}.get(CASE)
        if failure:
            _dawn.diagnostic_submission_controls(False, failure)
            try:
                try:
                    collect()
                except RuntimeError as error:
                    assert 'diagnostic submission failure: ' + failure in str(error)
                else:
                    raise AssertionError('cleanup submission failure was not exercised')
            finally:
                _dawn.diagnostic_submission_controls(False, '')
        collect()
        after_submits = _dawn.probe()['dawn_queue_submits']
        assert after_submits - before_submits == 1, (before_submits, after_submits)
        observations.append(dict(cleanup_submissions=after_submits - before_submits,
                                 injected_failure=failure))
    elif CASE == 'panzoom':
        source = Path(TEST_ROOT) / 'tests/qt/test_panzoom_input_gpu.py'
        spec = importlib.util.spec_from_file_location('panzoom_retirement_fixture', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def scene_once():
            with module.opened_scene() as (_, canvas, camera):
                module.assert_landmarks(application, canvas, (120, 90), (60, 60))
                return [weakref.ref(v) for v in (canvas, canvas.scene, camera, canvas.context)]
        for index in range(3):
            refs = scene_once()
            collect()
            assert all(ref() is None for ref in refs)
            assert gauges() == baseline, (index, baseline, gauges())
            observations.append(dict(iteration=index, gauges=gauges()))
    else:
        raise AssertionError(CASE)
    before_shutdown = gauges()
    assert before_shutdown == baseline, (baseline, before_shutdown)
    assert not unraisable, unraisable
finally:
    __import__('sys').unraisablehook = previous_unraisable
    _dawn.retire_objects = original_retire
    if gc_was_enabled: gc.enable()
    _dawn.shutdown()
assert not any(gauges().values()), gauges()
print('orphan retirement proof', json.dumps(dict(
    case=CASE, baseline=baseline, before_shutdown=before_shutdown,
    observations=observations, unraisable=unraisable, retirement_calls=retirement_calls,
    native_path=_dawn.__file__, native_sha256=hashlib.sha256(Path(_dawn.__file__).read_bytes()).hexdigest(),
    scope='Finite internal-framebuffer/native ownership controls; no optical or physical-memory claim.')))
'''


@pytest.mark.gpu
@pytest.mark.parametrize('case', ['unknown', 'peer', 'worker', 'snapshot', 'held-context',
                                 'host-import', 'host-import-fail-before-submit',
                                 'host-import-fail-callback', 'panzoom'])
def test_orphan_retirement_preserves_owners_and_restores_resources(case):
    setup = (f'import sys\nsys.path[:0] = {sys.path!r}\n'
             f'EXPECTED_VISPY = {str(Path(vispy.__file__).resolve())!r}\n'
             f'TEST_ROOT = {str(Path(__file__).resolve().parents[2])!r}\nCASE = {case!r}\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', VISPY_QT_PRESENTATION='readback')
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-B', '-X', 'faulthandler', '-c', setup + CHILD],
        cwd=Path(__file__).resolve().parents[2], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace', timeout=90,
    )
    assert result.returncode == 0, f'child exit {result.returncode}\n{result.stdout}'
    assert 'orphan retirement proof' in result.stdout, result.stdout
    print(result.stdout)
