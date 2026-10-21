"""Device loss rematerializes modules without recompiling retained programs."""

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu
VERTEX = "attribute vec2 a_position; void main(){gl_Position=vec4(a_position,0.,1.);}"
FRAGMENT = "uniform vec4 u_retained_color; void main(){gl_FragColor=u_retained_color;}"


def test_retained_program_survives_deleted_shader_objects_and_device_loss():
    canvas = app.Canvas(app="dawn_headless", size=(4, 4), show=False)
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 4, 4)
        program = gloo.Program(VERTEX, FRAGMENT)
        program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program["u_retained_color"] = (1, 0, 0, 1)
        program.draw("triangles")
        first = gloo.read_pixels((0, 0, 4, 4))
        assert np.all(first == [255, 0, 0, 255])
        before = _dawn.probe()
        assert before["portable_shader_bytes"] > 0
        _dawn.lose_device()
        recovered_info = _dawn.device_info()
        assert recovered_info["ok"] is True, recovered_info["error"]
        assert _dawn.probe()["device_generation"] > before["device_generation"]
        # Program LINK consumed and deleted its attached gloo Shader objects.
        # This DRAW has only the retained program, not a new LINK or sources.
        program["u_retained_color"] = (0, 1, 0, 1)
        program.draw("triangles")
        assert np.all(gloo.read_pixels((0, 0, 4, 4)) == [0, 255, 0, 255])
        after = _dawn.probe()
        assert after["device_generation"] > before["device_generation"]
        assert after["portable_shader_misses"] == before["portable_shader_misses"]
        assert after["artifact_cache_entries"] == before["artifact_cache_entries"]
        assert after["portable_shader_bytes"] == before["portable_shader_bytes"]
        assert after["pipeline_misses"] > before["pipeline_misses"]
    finally:
        canvas.close()


def test_sampling_policy_and_original_source_identity_are_cached_across_loss():
    # Different source provenance must not alias even when normalization drops
    # comments, and implicit sampling remains a distinct portable artifact.
    vertex = "void main(){gl_Position=vec4(0.,0.,0.,1.);}"
    fragment = "uniform sampler2D u_retained_sampler; void main(){gl_FragColor=texture2D(u_retained_sampler,vec2(.5));}"
    keys = []
    for source, base in ((fragment, False), (fragment, True), ("// composer origin\n" + fragment, False)):
        compiled = _dawn.compile_variant(vertex, source, base, False, False)
        assert compiled["ok"], compiled["error"]
        keys.append(compiled["cache_key"])
    assert len(set(keys)) == 3
    before = _dawn.probe()
    _dawn.lose_device()
    recovered_info = _dawn.device_info()
    assert recovered_info["ok"] is True, recovered_info["error"]
    assert _dawn.probe()["device_generation"] > before["device_generation"]
    for key, (source, base) in zip(keys, ((fragment, False), (fragment, True), ("// composer origin\n" + fragment, False))):
        compiled = _dawn.compile_variant(vertex, source, base, False, False)
        assert compiled["ok"] and compiled["cache_key"] == key, compiled["error"]
    after = _dawn.probe()
    assert after["portable_shader_misses"] == before["portable_shader_misses"]
    assert after["portable_shader_hits"] - before["portable_shader_hits"] == 3


@pytest.mark.parametrize("stage", ["vertex", "fragment"])
def test_failed_shader_retains_its_original_line_on_cache_hits_and_device_loss(stage):
    # Uniform/interface headers differ between stages. Mapping the combined
    # vertex log through the fragment map used to report line 4 for line 3.
    vertex = "attribute vec2 a_bad_position;\nvoid main(){gl_Position=vec4(a_bad_position,0.,1.);\nmissing_vertex_name;\n}"
    fragment = "uniform vec4 u_bad_color;\nvoid main(){gl_FragColor=u_bad_color;\nmissing_fragment_name;\n}"
    sources = (vertex, FRAGMENT) if stage == "vertex" else (VERTEX, fragment)
    first = _dawn.compile_variant(*sources)
    assert not first["ok"] and not first["pipeline"]
    assert first["mapped_line"] == 3, first["error"]
    assert f"missing_{stage}_name" in first["error"]
    assert f"missing_{stage}_name" in first[f"{stage}_log"]
    before = _dawn.probe()
    repeated = _dawn.compile_variant(*sources)
    assert repeated["error"] == first["error"]
    assert repeated["mapped_line"] == 3
    assert _dawn.probe()["portable_shader_misses"] == before["portable_shader_misses"]
    _dawn.lose_device()
    recovered_info = _dawn.device_info()
    assert recovered_info["ok"] is True, recovered_info["error"]
    assert _dawn.probe()["device_generation"] > before["device_generation"]
    recovered = _dawn.compile_variant(*sources)
    assert not recovered["ok"] and recovered["cache_key"] == first["cache_key"]
    assert recovered["error"] == first["error"] and recovered["mapped_line"] == 3
    assert recovered["vertex_log"] == first["vertex_log"]
    assert recovered["fragment_log"] == first["fragment_log"]
    after = _dawn.probe()
    assert after["device_generation"] > before["device_generation"]
    assert after["portable_shader_misses"] == before["portable_shader_misses"]
    assert after["portable_shader_hits"] - before["portable_shader_hits"] == 2


def test_oversized_shader_has_no_hidden_device_cache_ownership():
    _dawn.configure_shader_cache(4, 4096)
    try:
        vertex = "//" + "x" * 8192 + "\n" + VERTEX
        before = _dawn.probe()
        for depth in (False, True, False):
            compiled = _dawn.compile_variant(vertex, FRAGMENT, has_depth=depth)
            assert compiled["ok"], compiled["error"]
            counters = _dawn.probe()
            assert counters["artifact_cache_entries"] == counters["pipeline_cache_entries"] == 0
            assert counters["portable_shader_bytes"] == counters["shader_cache_bytes"] == 0
            assert counters["shader_cache_limit"] == 4096
        assert counters["portable_shader_misses"] - before["portable_shader_misses"] == 3
    finally:
        _dawn.configure_shader_cache(128, 64 * 1024 * 1024)


def test_uncached_live_program_is_accounted_and_recovers_without_compilation():
    _dawn.configure_shader_cache(4, 4096)
    canvas = app.Canvas(app="dawn_headless", size=(4, 4), show=False)
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 4, 4)
        program = gloo.Program("//" + "y" * 8192 + "\n" + VERTEX, FRAGMENT)
        program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        program["u_retained_color"] = (1, 0, 0, 1)
        program.draw("triangles")
        assert np.all(gloo.read_pixels((0, 0, 4, 4)) == [255, 0, 0, 255])
        before = _dawn.probe()
        assert before["shader_cache_bytes"] == 0
        assert before["uncached_live_portable_shader_bytes"] > before["shader_cache_limit"]
        assert before["live_portable_shader_bytes"] >= before["uncached_live_portable_shader_bytes"]
        _dawn.lose_device()
        recovered_info = _dawn.device_info()
        assert recovered_info["ok"] is True, recovered_info["error"]
        assert _dawn.probe()["device_generation"] > before["device_generation"]
        program["u_retained_color"] = (0, 1, 0, 1)
        program.draw("triangles")
        assert np.all(gloo.read_pixels((0, 0, 4, 4)) == [0, 255, 0, 255])
        after = _dawn.probe()
        assert after["portable_shader_misses"] == before["portable_shader_misses"]
        assert after["shader_cache_bytes"] == 0
        assert after["uncached_live_portable_shader_bytes"] == before["uncached_live_portable_shader_bytes"]
    finally:
        canvas.close()
        _dawn.configure_shader_cache(128, 64 * 1024 * 1024)


def test_evicted_live_record_cannot_change_another_record_cache_charge():
    canvas = app.Canvas(app="dawn_headless", size=(4, 4), show=False)
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 4, 4)

        def make_program():
            program = gloo.Program(VERTEX, FRAGMENT)
            program["a_position"] = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
            program["u_retained_color"] = (0, 1, 0, 1)
            return program

        old = make_program()
        gloo.set_state(blend=False, depth_test=False)
        old.draw("triangles")
        assert np.all(gloo.read_pixels((0, 0, 4, 4)) == [0, 255, 0, 255])
        # Drop only cache owners. The old Program's device record stays live.
        _dawn.configure_shader_cache(128, 64 * 1024 * 1024)
        new = make_program()
        for blend, depth in ((False, False), (True, False), (False, True)):
            gloo.set_state(blend=blend, depth_test=depth)
            new.draw("triangles")
            gloo.read_pixels((0, 0, 4, 4))
        before = _dawn.probe()
        assert before["uncached_live_portable_shader_bytes"] > 0
        assert before["pipeline_cache_entries"] >= 4
        gloo.set_state(blend=True, depth_test=True)
        old.draw("triangles")
        gloo.read_pixels((0, 0, 4, 4))
        after = _dawn.probe()
        assert after["shader_cache_bytes"] == before["shader_cache_bytes"]
        assert after["pipeline_cache_entries"] == before["pipeline_cache_entries"]
        assert after["shader_cache_bytes"] <= after["shader_cache_limit"]
    finally:
        canvas.close()
        _dawn.configure_shader_cache(128, 64 * 1024 * 1024)
