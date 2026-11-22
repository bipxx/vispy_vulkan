"""Measure first draws of new programs with cold and primed compiler inputs."""

import argparse
import json
import statistics
import time

import numpy as np

from vispy import _dawn, app, gloo


VERTEX = "attribute vec2 a_position; void main() { gl_Position = vec4(a_position, 0., 1.); }"
COUNTERS = (
    "portable_shader_misses", "shader_parse_calls", "shader_link_calls",
    "shader_spirv_stages", "shader_parse_ns", "shader_link_ns", "shader_spirv_ns",
)


def first_draw(fragment, positions, canvas):
    program = gloo.Program(VERTEX, fragment)
    program["a_position"] = positions
    gloo.clear(color=(0, 0, 0, 1))
    before = _dawn.probe()
    start = time.perf_counter_ns()
    program.draw("triangles")
    canvas.context.flush_commands()
    milliseconds = (time.perf_counter_ns() - start) / 1e6
    pixel = gloo.read_pixels((0, 0, 4, 4))[2, 2]
    np.testing.assert_array_equal(pixel, [0, 255, 0, 255])
    after = _dawn.probe()
    return {"draw_ms": milliseconds, **{k: after[k] - before[k] for k in COUNTERS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=15)
    args = parser.parse_args()
    if args.pairs < 1:
        parser.error("--pairs must be positive")
    canvas = app.Canvas(app="dawn_headless", size=(4, 4), show=False)
    try:
        canvas.set_current()
        gloo.set_viewport(0, 0, 4, 4)
        positions = gloo.VertexBuffer(np.array([[-1, -1], [3, -1], [-1, 3]], np.float32))
        samples = {"new_compiler_input": [], "primed_compiler_input": []}
        for index in range(args.pairs):
            fragment = (
                f"void main() {{ gl_FragColor = vec4(0., 1., {index}. / 1.e9, 1.); }}"
            )
            for condition in samples:
                # Remove portable artifact and pipeline owners to isolate compiler reuse.
                _dawn.configure_shader_cache(128, 64 * 1024 * 1024)
                sample = first_draw(fragment, positions, canvas)
                assert sample["portable_shader_misses"] == 1, sample
                samples[condition].append(sample)
        print(json.dumps({
            "first_sample": {k: values[0] for k, values in samples.items()},
            "medians": {
                k: {field: statistics.median(s[field] for s in values) for field in values[0]}
                for k, values in samples.items()
            },
            "samples": samples,
        }, indent=2))
    finally:
        canvas.close()


if __name__ == "__main__":
    main()
