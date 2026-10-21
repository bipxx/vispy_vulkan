"""Analytic public-gloo typed framebuffer captures, authored before the oracle."""

from __future__ import annotations

import hashlib

import numpy as np

if __package__:
    from .fixture_gloo import Runner
else:
    from fixture_gloo import Runner

SIZE = (8, 6)
CASES = ("r32f_float", "rg32f_float", "rgba32f_float", "rgba16f_float",
         "r8_float", "rg16_float", "rgba8_float", "rgba16_float",
         "rgba8_u8", "rgba16_u8", "float_crop_rgb", "float_owned_arrays")
FLOAT_BOTTOM = [-2, 15, .125, .25]
FLOAT_TOP = [.125, -2, 15, .75]
NORMAL_BOTTOM = [0, .25, .125, .25]
NORMAL_TOP = [.75, .125, 1, .75]


def specification(name):
    if name not in CASES:
        raise ValueError(name)
    internalformat = name.split("_")[0] if name.startswith(("r32", "rg32", "rgba", "r8", "rg16")) else "rgba32f"
    channels = 4 if internalformat.startswith("rgba") else 2 if internalformat.startswith("rg") else 1
    floating_attachment = internalformat.endswith("f")
    dtype = "<f4" if floating_attachment else "<u2" if internalformat.endswith("16") else "|u1"
    return {"internalformat": internalformat, "format": {1: "red", 2: "rg", 4: "rgba"}[channels],
            "channels": channels, "input_dtype": dtype, "attachment_size": list(SIZE),
            "out_type": "unsigned_byte" if name.endswith("_u8") else "float",
            "out_type_argument": "numpy.uint8" if name == "rgba8_u8" else "numpy.float32" if name == "float_crop_rgb" else
                                 "unsigned_byte" if name.endswith("_u8") else "float",
            "alpha": name != "float_crop_rgb", "crop": [2, 1, 4, 3] if name == "float_crop_rgb" else [0, 0, *SIZE],
            "bottom_rgba": FLOAT_BOTTOM if floating_attachment else NORMAL_BOTTOM,
            "top_rgba": FLOAT_TOP if floating_attachment else NORMAL_TOP,
            "readbacks": 2 if name == "float_owned_arrays" else 1,
            "x_pattern": "pixel-center red channel" if name == "float_crop_rgb" else "constant",
            "orientation": "top-left array, bottom-left viewport crop"}


def expected_image(name, *, second=False):
    spec = specification(name)
    output = np.empty((SIZE[1], SIZE[0], 4), np.float32)
    output[:3] = spec["top_rgba"]
    output[3:] = spec["bottom_rgba"]
    if name == "float_crop_rgb":
        output[..., 0] = np.arange(SIZE[0], dtype=np.float32) + .5
    if second:
        assert name == "float_owned_arrays"
        output[:] = [15, .125, -2, .5]
    if not spec["internalformat"].endswith("f"):
        maximum = 65535 if spec["internalformat"].endswith("16") else 255
        output = (np.floor(output.astype(np.float64) * maximum + .5) / maximum).astype(np.float32)
    if spec["channels"] < 4:
        output[..., spec["channels"]:3] = 0
        output[..., 3] = 1
    x, y, width, height = spec["crop"]
    output = output[SIZE[1] - y - height:SIZE[1] - y, x:x + width]
    if not spec["alpha"]:
        output = output[..., :3]
    if spec["out_type"] == "unsigned_byte":
        output = np.floor(np.clip(output, 0, 1).astype(np.float64) * 255 + .5).astype(np.uint8)
    return np.ascontiguousarray(output)


def assert_expected(name, image, extras):
    expected = expected_image(name, second=name == "float_owned_arrays")
    assert image.shape == expected.shape and image.dtype == expected.dtype
    assert np.array_equal(image, expected), (name, "exact analytic typed capture", image.tolist(), expected.tolist())
    if name == "float_owned_arrays":
        assert np.array_equal(extras["first"], expected_image(name)), "retained first array changed after second capture/teardown"
        assert not np.shares_memory(image, extras["first"]), "independent captures must own independent lifetimes"


def render(name, backend="dawn_headless"):
    spec = specification(name)
    runner = Runner(backend)
    gloo = runner.gloo
    runner.canvas()
    extras = {}
    try:
        texture = gloo.Texture2D(np.zeros((SIZE[1], SIZE[0], spec["channels"]), dtype=spec["input_dtype"]),
                                 format=spec["format"], internalformat=spec["internalformat"], interpolation="nearest")
        framebuffer = gloo.FrameBuffer(color=texture)
        fragment = """
            uniform vec4 u_bottom;
            uniform vec4 u_top;
            void main() { gl_FragColor = gl_FragCoord.y < 3.0 ? u_bottom : u_top;
        """ + ("gl_FragColor.r = gl_FragCoord.x;" if name == "float_crop_rgb" else "") + "}"
        program = runner.solid(frag=fragment)
        program["u_bottom"], program["u_top"] = spec["bottom_rgba"], spec["top_rgba"]
        out_type = np.uint8 if name == "rgba8_u8" else np.float32 if name == "float_crop_rgb" else spec["out_type"]
        with framebuffer:
            gloo.set_viewport(0, 0, *SIZE)
            program.draw("triangles")
            image = gloo.read_pixels(spec["crop"], alpha=spec["alpha"], out_type=out_type)
            original_layout = {"own_data": bool(image.flags.owndata), "writeable": bool(image.flags.writeable),
                               "strides": list(image.strides), "c_contiguous": bool(image.flags.c_contiguous)}
            if name == "float_owned_arrays":
                extras["first"] = image
                first_hash = hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()
                program["u_bottom"] = program["u_top"] = [15, .125, -2, .5]
                program.draw("triangles")
                image = gloo.read_pixels(spec["crop"], alpha=True, out_type="float")
                assert hashlib.sha256(np.ascontiguousarray(extras["first"]).tobytes()).hexdigest() == first_hash
                assert not np.shares_memory(image, extras["first"])
        params = dict(spec)
        params["readback_between_ownership_stages"] = spec["readbacks"] == 2
        params["explicit_gloo_finish_calls"] = 0
        # Layout differences are recorded, not required for API parity: the
        # upstream reversed view retains its backing storage's lifetime.
        return image, runner.commands, runner.shaders, params, extras, original_layout
    finally:
        runner.close()
