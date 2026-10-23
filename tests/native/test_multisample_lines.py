"""Functional sample-rate line coverage, interpolation and depth on real targets.

These checks use analytic interior/background invariants, not driver-exact GL
rasterization. No missing four-sample path is accepted as an expected refusal.
"""
from contextlib import contextmanager

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu
SIZE = (32, 24)
VERTEX = "attribute vec4 a_position; void main(){gl_Position=a_position;}"
LINE = np.array([[-.75, -.5, 0, 1], [.75, .5, 0, 1]], np.float32)
FULL = np.array([[-1, -1, .5, 1], [3, -1, .5, 1], [-1, 3, .5, 1]], np.float32)


@contextmanager
def scene(samples=4):
    canvas = app.Canvas(app="dawn_headless", size=SIZE, show=False, config={"samples": samples})
    objects = []
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, *SIZE)
        gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False,
                       cull_face=False, line_smooth=False)
        gloo.set_color_mask(True, True, True, True)
        yield canvas, objects
    finally:
        canvas.set_current()
        for obj in reversed(objects):
            obj.delete()
        canvas.context.flush_commands()
        canvas.close()
        _dawn.process_events()
        after = _dawn.probe()
        assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
        assert after["line_resource_pool_busy_slots"] == 0


def program(objects, positions, fragment, vertex=VERTEX):
    source = gloo.VertexBuffer(np.asarray(positions, np.float32))
    result = gloo.Program(vertex, fragment)
    result["a_position"] = source
    objects.extend((source, result))
    return result, source


def clear():
    gloo.set_clear_color((0, 0, 0, 1))
    gloo.set_clear_depth(1)
    gloo.clear(color=True, depth=True, stencil=True)


@pytest.mark.parametrize("samples", [0, 4])
@pytest.mark.parametrize("smooth", [False, True])
def test_actual_line_target_has_covered_samples_and_untouched_background(samples, smooth):
    with scene(samples) as (canvas, objects):
        p, _ = program(objects, LINE, "void main(){gl_FragColor=vec4(1,0,0,1);}")
        gloo.set_line_width(3)
        gloo.set_state(line_smooth=smooth, blend=smooth)
        if smooth:
            gloo.set_blend_func("src_alpha", "one_minus_src_alpha")
        clear()
        p.draw("lines")
        image = gloo.read_pixels()
        assert _dawn.framebuffer_config(canvas._backend._dawn_canvas_id)["sample_count"] == max(1, samples)
        red = image[..., 0]
        assert red.max() == 255
        assert 12 < np.count_nonzero(red) < 240
        assert np.all(image[[0, -1], :, :3] == 0)
        assert np.all(image[:, [0, -1], :3] == 0)
        assert np.all(image[..., 1:3] == 0)
        if samples == 4:
            # The conservative quad extends past the line: only per-sample
            # line coverage, rather than the quad's edge, can produce these.
            assert np.any((red > 0) & (red < 255))
            if not smooth:
                # Resolve-to-UNORM rounding can choose adjacent integers at a
                # half-way value (for example 127 versus 128). Require actual
                # quarter-sample bins within one byte, not driver bit identity.
                bins = np.array([0, 64, 128, 191, 255], np.int16)
                values = np.unique(red).astype(np.int16)
                distance = np.abs(values[:, None] - bins).min(axis=1)
                assert np.all(distance <= 1), values.tolist()


@pytest.mark.parametrize("qualifier,perspective", [("sample noperspective", False), ("centroid", True)])
def test_four_sample_qualified_interpolation_uses_the_current_raster_position(qualifier, perspective):
    with scene() as (_, objects):
        w0, w1 = (.5, 2.) if perspective else (1., 1.)
        positions = np.array([[-.75*w0, 0, 0, w0], [.75*w1, 0, 0, w1]], np.float32)
        vertex = f"""attribute vec4 a_position; {qualifier} out float value;
        void main(){{gl_Position=a_position;value=float(gl_VertexID);}}"""
        expected = "q*0.5/((1.0-q)*2.0+q*0.5)" if perspective else "q"
        fragment = f"""{qualifier} in float value;
        void main(){{float q=(gl_FragCoord.x-4.0)/24.0;
        float expected={expected};gl_FragColor=vec4(abs(value-expected)*32.0,value,0,1);}}"""
        p, _ = program(objects, positions, fragment, vertex)
        gloo.set_line_width(5)
        clear()
        p.draw("lines")
        image = gloo.read_pixels()
        interior = image[10:14, 8:24]
        assert interior[..., 0].max() <= 1, "sample-coordinate and reconstructed varying disagree"
        assert interior[..., 1].max() > interior[..., 1].min() + 40
        assert np.all(interior[..., 2] == 0)


def test_four_sample_discard_and_fragment_depth_only_occlude_covered_line_samples():
    with scene() as (_, objects):
        p, _ = program(objects, [[-.75, 0, -.5, 1], [.75, 0, -.5, 1]],
            """void main(){if(gl_FragCoord.x<16.0)discard;
            gl_FragDepth=gl_FragCoord.x>22.0?0.95:0.25;gl_FragColor=vec4(1,0,0,1);}""")
        background, _ = program(objects, FULL, "void main(){gl_FragColor=vec4(0,0,1,1);}")
        gloo.set_line_width(5)
        gloo.set_state(depth_test=True)
        gloo.set_depth_func("less")
        clear()
        p.draw("lines")
        background.draw("triangles")
        image = gloo.read_pixels()
        assert np.all(image[11:13, 17:21, :3] == [255, 0, 0])
        assert np.all(image[11:13, 8:14, :3] == [0, 0, 255]), "discard wrote depth"
        assert np.all(image[11:13, 24:27, :3] == [0, 0, 255]), "fragment depth override was ignored"
        assert np.all(image[2:5, 8:27, :3] == [0, 0, 255]), "conservative quad wrote outside coverage"
        assert np.all(image[..., 1] == 0)
        total = image[..., 0].astype(np.int16) + image[..., 2]
        assert np.all((total >= 254) & (total <= 256)), "uncovered sample lost its background"


def test_four_sample_line_mutation_and_device_recovery_replay_retained_inputs():
    with scene() as (canvas, objects):
        p, source = program(objects, LINE, "uniform vec4 u_color;void main(){gl_FragColor=u_color;}")
        gloo.set_line_width(3)
        p["u_color"] = (1, 0, 0, 1)
        clear(); p.draw("lines"); initial = gloo.read_pixels()
        changed = LINE.copy(); changed[:, 1] += .25
        source.set_data(changed)
        p["u_color"] = (0, 1, 0, 1)
        clear(); p.draw("lines"); revised = gloo.read_pixels()
        assert np.count_nonzero(initial[..., 0]) > 0 and not np.any(revised[..., 0])
        assert np.count_nonzero(revised[..., 1]) > 0
        generation = _dawn.probe()["device_generation"]
        _dawn.lose_device()
        canvas.set_current()
        gloo.set_viewport(0, 0, *SIZE)
        clear(); p.draw("lines"); recovered = gloo.read_pixels()
        assert _dawn.probe()["device_generation"] > generation
        assert _dawn.device_info()["backend"] == "Vulkan"
        np.testing.assert_array_equal(recovered, revised)
