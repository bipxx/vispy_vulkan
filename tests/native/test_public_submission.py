# SPDX-License-Identifier: AGPL-3.0-only
"""Public synchronization must submit real work without implicit presentation."""
import numpy as np
import pytest
import time

from vispy import _dawn, app, gloo
from vispy.gloo import gl

pytestmark = pytest.mark.gpu
FULL = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)


def flush(route):
    (gloo.flush if route == 'gloo' else gl.glFlush)()


@pytest.fixture
def canvas():
    value = app.Canvas(app='dawn_headless', size=(8, 8))
    value.set_current()
    gloo.set_viewport(0, 0, 8, 8)
    gloo.clear(color='blue')
    gloo.finish()
    yield value
    controls = getattr(_dawn, 'diagnostic_submission_controls', None)
    if controls is not None:
        controls(False, '')
    if not value._closed:
        value.set_current()
        value.context.flush_commands()
    _dawn.finish(value._backend._dawn_canvas_id)
    value.close()
    _dawn.configure_frame_slots(3)


def assert_no_wait_or_present(before, after):
    for name in ('finish_calls', 'completion_waits', 'application_presents'):
        assert after[name] == before[name], name


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_nonempty_flush_submits_before_read_finish_or_present(canvas, route):
    before = _dawn.probe()
    gloo.clear(color='red')
    flush(route)
    submitted = _dawn.probe()  # Polls retirement; never submits queued work.
    assert submitted['dawn_queue_submits'] > before['dawn_queue_submits']
    assert_no_wait_or_present(before, submitted)
    np.testing.assert_array_equal(gloo.read_pixels((0, 0, 8, 8), alpha=True),
                                  np.broadcast_to([255, 0, 0, 255], (8, 8, 4)))


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_finish_waits_without_presentation_gui_draw_or_state_change(canvas, route):
    draws = []
    canvas.events.draw.connect(lambda event: draws.append(event))
    canvas.context.set_viewport(1, 2, 5, 4)
    gloo.set_scissor(2, 1, 3, 2)
    gloo.set_state(scissor_test=True)
    gloo.clear(color='red')
    before = _dawn.probe()
    (gloo.finish if route == 'gloo' else gl.glFinish)()
    after = _dawn.probe()
    assert after['finish_calls'] == before['finish_calls'] + 1
    assert after['completion_waits'] > before['completion_waits']
    assert after['application_presents'] == before['application_presents']
    assert not draws and gloo.get_current_canvas() is canvas
    assert canvas.context.get_viewport() == (1, 2, 5, 4)
    assert tuple(_dawn.viewport(canvas._backend._dawn_canvas_id)) == (1, 2, 5, 4)
    # A following clear must still honor the selected scissor after finish.
    gloo.clear(color='green')
    (gloo.finish if route == 'gloo' else gl.glFinish)()
    assert _dawn.probe()['application_presents'] == before['application_presents']
    # Presentation stays explicit and must expose the completed target.
    _dawn.present(canvas._backend._dawn_canvas_id)
    _dawn.finish(canvas._backend._dawn_canvas_id)
    presented = _dawn.read_presented(canvas._backend._dawn_canvas_id, 0, 0, 8, 8)
    expected = np.empty((8, 8, 4), np.uint8)
    expected[:] = [0, 0, 255, 255]
    expected[5:7, 2:5] = [0, 128, 0, 255]
    # Native read_presented exposes raw BGRA8Unorm storage in top-down rows;
    # decode channels before comparing with independently authored RGBA colors.
    image = np.asarray(presented)[..., [2, 1, 0, 3]]
    np.testing.assert_array_equal(image, expected)


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_empty_repeated_flush_is_a_noop(canvas, route):
    before = _dawn.probe()
    flush(route)
    flush(route)
    after = _dawn.probe()
    assert after['dawn_queue_submits'] == before['dawn_queue_submits']
    assert_no_wait_or_present(before, after)


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_saturated_flush_reports_backpressure_and_retains_unsubmitted_work(canvas, route):
    _dawn.configure_frame_slots(1)
    _dawn.diagnostic_submission_controls(True, '')
    gloo.clear(color='red')
    flush(route)
    before = _dawn.probe()
    assert before['pending_tickets'] == 1  # Completion delivery is held, not a timing guess.
    gloo.clear(color='green')
    with pytest.raises(RuntimeError, match='glFlush.*capacity'):
        flush(route)
    blocked = _dawn.probe()
    assert blocked['pending_tickets'] == 1 and blocked['pending_draws'] > 0
    assert blocked['dawn_queue_submits'] == before['dawn_queue_submits']
    assert_no_wait_or_present(before, blocked)
    _dawn.diagnostic_submission_controls(False, '')
    _dawn.process_events()
    flush(route)
    resumed = _dawn.probe()
    assert resumed['dawn_queue_submits'] == before['dawn_queue_submits'] + 1
    assert_no_wait_or_present(before, resumed)
    image = gloo.read_pixels((0, 0, 8, 8), alpha=True)
    assert np.all(image == [0, 128, 0, 255])


@pytest.mark.parametrize('route', ['gloo', 'raw'])
@pytest.mark.parametrize('stage', ['after-submit', 'callback-registration', 'query-map'])
def test_post_submit_failure_retains_ticket_and_never_replays_work(canvas, route, stage):
    _dawn.diagnostic_submission_controls(True, stage)
    before = _dawn.probe()
    gloo.clear(color='red')
    with pytest.raises(RuntimeError, match='diagnostic submission failure'):
        flush(route)
    failed = _dawn.probe()
    assert failed['dawn_queue_submits'] == before['dawn_queue_submits'] + 1
    assert failed['pending_tickets'] == 1
    assert failed['pending_draws'] == failed['queued_frames'] == 0
    assert_no_wait_or_present(before, failed)
    flush(route)  # Empty retry must not repeat the irreversible submission.
    assert _dawn.probe()['dawn_queue_submits'] == failed['dawn_queue_submits']
    _dawn.diagnostic_submission_controls(False, '')
    _dawn.process_events()
    gloo.finish()
    assert _dawn.probe()['pending_tickets'] == 0
    assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [255, 0, 0, 255])


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_flush_preserves_nested_fbo_and_canvas_selection(canvas, route):
    second = app.Canvas(app='dawn_headless', size=(8, 8))
    canvas.set_current()
    colors = [gloo.Texture2D(np.zeros((8, 8, 4), np.uint8)) for _ in range(2)]
    targets = [gloo.FrameBuffer(color=color) for color in colors]
    try:
        with targets[0]:
            gloo.clear(color='red')
            flush(route)
            outer = _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)['framebuffer_id']
            with targets[1]:
                gloo.clear(color='green')
                flush(route)
                assert _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)['framebuffer_id'] != outer
                assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 128, 0, 255])
            canvas.context.flush_commands()
            assert _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)['framebuffer_id'] == outer
            assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [255, 0, 0, 255])
        second.set_current()
        gloo.clear(color='red')
        flush(route)
        assert gloo.get_current_canvas() is second
        canvas.set_current()
        assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 0, 255, 255])
    finally:
        canvas.set_current()
        for target in targets:
            target.delete()
        for color in colors:
            color.delete()
        canvas.context.flush_commands()
        second.close()


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_flush_retains_mutated_and_deleted_draw_inputs_until_completion(canvas, route):
    program = gloo.Program('attribute vec2 a_position; void main(){gl_Position=vec4(a_position,0.,1.);}',
                           'uniform vec4 u_color; void main(){gl_FragColor=u_color;}')
    vertices = gloo.VertexBuffer(FULL)
    program['a_position'] = vertices
    program['u_color'] = (1, 0, 0, 1)
    program.draw('triangles')
    gloo.finish()  # Warm native pipeline and start with no outstanding work.
    _dawn.diagnostic_submission_controls(True, '')
    program.draw('triangles')
    flush(route)
    vertices.set_data(FULL.copy())
    program['u_color'] = (0, 1, 0, 1)
    program.draw('triangles')
    flush(route)
    program.delete()
    vertices.delete()
    canvas.context.flush_commands()
    held = _dawn.probe()
    assert held['pending_tickets'] == 2 and held['live_buffer_bytes'] > 0
    _dawn.diagnostic_submission_controls(False, '')
    _dawn.process_events()
    gloo.finish()
    assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 255, 0, 255])


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_older_native_flush_contract_is_rejected_before_execution(canvas, route, monkeypatch):
    before = _dawn.probe()
    monkeypatch.setattr(_dawn, 'submission_contract_version', 0)
    gloo.clear(color='red')
    with pytest.raises(RuntimeError, match='matching native submission-contract build'):
        flush(route)
    after = _dawn.probe()
    assert after['dawn_queue_submits'] == before['dawn_queue_submits']
    assert_no_wait_or_present(before, after)


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_pre_submit_failure_has_no_irreversible_submission(canvas, route):
    _dawn.diagnostic_submission_controls(True, 'before-submit')
    before = _dawn.probe()
    gloo.clear(color='red')
    with pytest.raises(RuntimeError, match='diagnostic submission failure: before-submit'):
        flush(route)
    after = _dawn.probe()
    assert after['dawn_queue_submits'] == before['dawn_queue_submits']
    assert after['pending_tickets'] == 0
    assert_no_wait_or_present(before, after)
    _dawn.diagnostic_submission_controls(False, '')
    gloo.clear(color='green')  # Explicit redraw after the failed encoding batch.
    flush(route)
    assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 128, 0, 255])


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_flush_submitted_owners_survive_device_loss_and_recovery(canvas, route):
    _dawn.diagnostic_submission_controls(True, '')
    gloo.clear(color='red')
    flush(route)
    assert _dawn.probe()['pending_tickets'] == 1
    _dawn.lose_device()
    _dawn.diagnostic_submission_controls(False, '')
    before = _dawn.probe()
    gloo.clear(color='green')
    flush(route)
    after = _dawn.probe()
    assert after['device_generation'] > before['device_generation']
    assert_no_wait_or_present(before, after)
    assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 128, 0, 255])


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_close_after_flush_retires_submitted_owners_without_presentation(canvas, route):
    _dawn.diagnostic_submission_controls(True, '')
    gloo.clear(color='red')
    flush(route)
    before = _dawn.probe()
    assert before['pending_tickets'] == 1
    canvas.close()
    _dawn.diagnostic_submission_controls(False, '')
    _dawn.process_events()
    after = _dawn.probe()
    assert after['pending_tickets'] == 0
    assert after['application_presents'] == before['application_presents']


@pytest.mark.parametrize('route', ['gloo', 'raw'])
def test_texture_revisions_and_deletion_remain_owned_after_flush(canvas, route):
    texture = gloo.Texture2D(np.full((2, 2, 4), [255, 0, 0, 255], np.uint8))
    program = gloo.Program('attribute vec2 a_position; void main(){gl_Position=vec4(a_position,0.,1.);}',
                           'uniform sampler2D u_texture; void main(){gl_FragColor=texture2D(u_texture,vec2(.5));}')
    vertices = gloo.VertexBuffer(FULL)
    program['a_position'] = vertices
    program['u_texture'] = texture
    program.draw('triangles')
    gloo.finish()
    _dawn.diagnostic_submission_controls(True, '')
    program.draw('triangles')
    flush(route)
    texture.set_data(np.full((2, 2, 4), [0, 255, 0, 255], np.uint8))
    program.draw('triangles')
    flush(route)
    program.delete()
    texture.delete()
    vertices.delete()
    canvas.context.flush_commands()
    held = _dawn.probe()
    assert held['pending_tickets'] == 2 and held['live_texture_bytes'] >= 2 * 2 * 4
    _dawn.diagnostic_submission_controls(False, '')
    _dawn.process_events()
    gloo.finish()
    assert np.all(gloo.read_pixels((0, 0, 8, 8), alpha=True) == [0, 255, 0, 255])


@pytest.mark.parametrize('stage', ['after-submit', 'callback-registration', 'query-map'])
def test_post_submit_query_failure_reports_actual_submission_and_retires_frame(canvas, stage):
    canvas_id = canvas._backend._dawn_canvas_id
    _dawn.benchmark_configure_gpu_timing(canvas_id, True)
    _dawn.benchmark_begin_frame(canvas_id, 901)
    token = _dawn.begin_canvas_paint(canvas_id)
    _dawn.diagnostic_submission_controls(True, stage)
    gloo.clear(color='red')
    with pytest.raises(RuntimeError, match='diagnostic submission failure'):
        gloo.flush()
    assert _dawn.probe()['pending_tickets'] == 1
    _dawn.abort_canvas_paint(canvas_id, token, 'expected post-submit failure control')
    _dawn.diagnostic_submission_controls(False, '')
    completions, timings = [], []
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        _dawn.process_events()
        completions.extend(_dawn.benchmark_completions(canvas_id))
        timings.extend(_dawn.benchmark_gpu_timings(canvas_id))
        state = _dawn.probe()
        if len(completions) == len(timings) == 1 and state['pending_tickets'] == state['pending_timestamp_frames'] == 0:
            break
    assert len(completions) == len(timings) == 1
    receipt, timing = completions[0], timings[0]
    assert receipt['frame_id'] == timing['frame_id'] == 901
    assert receipt['submission_count'] == timing['submission_count'] == 1
    assert receipt['ownership_closed'] and receipt['ownership_retired']
    assert receipt['status'] == 'failed' and not receipt['presented'] and receipt['present_count'] == 0
    assert timing['status'] in ('submission_error', 'map_error')
    assert state['pending_tickets'] == state['pending_timestamp_frames'] == 0
    _dawn.benchmark_configure_gpu_timing(canvas_id, False)
