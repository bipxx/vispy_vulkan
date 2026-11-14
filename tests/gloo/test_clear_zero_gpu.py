"""Numeric zero clears depth/stencil; boolean False leaves attachments alone."""

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@pytest.fixture
def seeded_canvas():
    from vispy import _dawn, app, gloo

    canvas = app.Canvas(app='dawn_headless', size=(4, 4), show=False)
    canvas.set_current()
    gloo.set_viewport(0, 0, 4, 4)
    gloo.set_state(depth_test=False, stencil_test=False, scissor_test=False, blend=False)
    gloo.set_color_mask(True, True, True, True)
    gloo.set_depth_mask(True)
    gloo.set_stencil_mask(0xff)
    gloo.set_clear_depth(.75)
    gloo.set_clear_stencil(7)
    gloo.clear(color=(1., 0., 0., 1.), depth=True, stencil=True)
    try:
        depth = gloo.read_pixels(mode='depth', out_type='float')
        stencil = gloo.read_pixels(mode='stencil')
        assert depth.shape == stencil.shape == (4, 4, 1)
        np.testing.assert_allclose(depth, .75, rtol=0, atol=1e-7)
        assert np.all(stencil == 7)
        yield canvas
    finally:
        canvas.close()
        _dawn.process_events()
    gauges = {name: _dawn.probe()[name] for name in (
        'pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
        'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
        'line_resource_pool_busy_slots', 'line_resource_pool_bytes')}
    assert not any(gauges.values()), gauges


@pytest.mark.parametrize('depth,stencil,expected_depth,expected_stencil', [
    pytest.param(False, False, .75, 7, id='false-preserves-both'),
    pytest.param(None, None, .75, 7, id='none-preserves-both'),
    pytest.param(True, True, .75, 7, id='true-uses-current-values'),
    pytest.param(np.bool_(False), np.bool_(False), .75, 7, id='numpy-false-preserves-both'),
    # Preserve the pre-existing NumPyTrue numeric-setting behavior.
    pytest.param(np.bool_(True), np.bool_(True), 1., 1, id='numpy-true-sets-one'),
    pytest.param(0, False, 0., 7, id='integer-depth-zero'),
    pytest.param(0., False, 0., 7, id='numeric-depth-zero'),
    pytest.param(False, 0, .75, 0, id='numeric-stencil-zero'),
    pytest.param(0., 0, 0., 0, id='both-numeric-zero'),
    pytest.param(np.float32(0), np.int32(0), 0., 0, id='numpy-numeric-zero'),
])
def test_numeric_zero_and_boolean_flags_are_distinct(seeded_canvas, depth, stencil, expected_depth, expected_stencil):
    from vispy import gloo

    gloo.clear(color=False, depth=depth, stencil=stencil)
    np.testing.assert_allclose(gloo.read_pixels(mode='depth', out_type='float'), expected_depth, rtol=0, atol=1e-7)
    assert np.all(gloo.read_pixels(mode='stencil') == expected_stencil)
    assert np.all(gloo.read_pixels(alpha=True) == [255, 0, 0, 255])


def test_invalid_depth_clear_preserves_seed_and_recovers_to_zero(seeded_canvas):
    from vispy import gloo

    gloo.clear(color=False, depth=float('nan'), stencil=False)
    with pytest.raises((RuntimeError, ValueError)):
        gloo.read_pixels(mode='depth', out_type='float')
    np.testing.assert_allclose(gloo.read_pixels(mode='depth', out_type='float'), .75, rtol=0, atol=1e-7)
    gloo.clear(color=False, depth=0., stencil=False)
    assert np.all(gloo.read_pixels(mode='depth', out_type='float') == 0.)
    assert np.all(gloo.read_pixels(mode='stencil') == 7)
