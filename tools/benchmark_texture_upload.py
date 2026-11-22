# SPDX-License-Identifier: AGPL-3.0-only
"""Measure warm full RGB8 and RGBA8 updates on a headless Dawn canvas."""

import argparse
import json
import os
from statistics import median
from time import perf_counter_ns

import numpy as np

from vispy import _dawn, app, gloo


def measure(size, channels, frames):
    rng = np.random.default_rng(602)
    data = [rng.integers(256, size=(size, size, channels), dtype=np.uint8) for _ in range(2)]
    texture = gloo.Texture2D(data[0], interpolation="nearest")
    program = gloo.Program(
        "attribute vec2 position; void main() { gl_Position = vec4(position, 0.0, 1.0); }",
        "uniform sampler2D image; void main() { gl_FragColor = texture2D(image, vec2(0.25)); }",
    )
    program["position"] = np.array([[-1, -1], [3, -1], [-1, 3]], dtype=np.float32)
    program["image"] = texture
    gloo.set_viewport(0, 0, 1, 1)

    def frame(pixels):
        texture.set_data(pixels)
        program.draw("triangles")
        gloo.finish()

    for index in range(4):
        frame(data[index % 2])
    timing = {key: [] for key in ("frame_ns", "texture_conversion_ns", "texture_upload_cpu_ns")}
    start = before = _dawn.probe()
    for index in range(frames):
        pixels = data[index % 2]
        begin = perf_counter_ns()
        frame(pixels)
        timing["frame_ns"].append(perf_counter_ns() - begin)
        after = _dawn.probe()
        for key in ("texture_conversion_ns", "texture_upload_cpu_ns"):
            timing[key].append(after[key] - before[key])
        before = after

    expected = np.full((size, size, 4), 255, dtype=np.uint8)
    expected[..., :channels] = data[(frames - 1) % 2][::-1]
    with gloo.FrameBuffer(color=texture):
        np.testing.assert_array_equal(gloo.read_pixels(viewport=(0, 0, size, size)), expected)
    assert after["texture_uploads"] - start["texture_uploads"] == frames
    return {
        "size": size, "channels": channels, "frames": frames,
        "median_ms": {key.removesuffix("_ns"): round(median(values) / 1e6, 4) for key, values in timing.items()},
        "host_import_copies": after["host_import_copies"] - start["host_import_copies"],
        "host_import_fallbacks": after["host_import_fallbacks"] - start["host_import_fallbacks"],
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Set VISPY_DAWN_CONVERTED_HOST_IMPORT=1 to measure the opt-in RGB8 path.",
    )
    parser.add_argument("--frames", type=int, default=15)
    parser.add_argument("--sizes", type=int, nargs="+", default=[512, 1536])
    args = parser.parse_args()
    if args.frames < 1 or any(size < 1 for size in args.sizes):
        parser.error("frames and sizes must be positive")
    canvas = app.Canvas(app="dawn_headless", size=(1, 1), show=False)
    with canvas:
        info = _dawn.device_info()
        metadata = {key: info[key] for key in ("device", "backend", "driver", "host_mapped_pointer")}
        metadata["converted_host_import_requested"] = os.environ.get("VISPY_DAWN_CONVERTED_HOST_IMPORT") == "1"
        print(json.dumps(metadata))
        for size in args.sizes:
            for channels in (3, 4):
                print(json.dumps(measure(size, channels, args.frames)))


if __name__ == "__main__":
    main()
