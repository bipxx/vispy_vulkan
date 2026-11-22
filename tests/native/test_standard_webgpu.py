"""Optional device capabilities and texture recovery on the headless backend."""

import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from vispy import _dawn, app, gloo
from tools.fixture_gloo import FULL, VERT

pytestmark = pytest.mark.gpu

CAPABILITIES = {
    "Float32Filterable": "float32_filterable",
    "Unorm16TextureFormats": "unorm16_texture_formats",
    "TimestampQuery": "timestamp_query",
}


def test_device_feature_requests():
    info = _dawn.device_info()
    assert info["ok"], info["error"]
    if os.getenv("VISPY_DAWN_STANDARD_ONLY") == "1":
        assert not info["host_mapped_pointer"]
    disabled = os.getenv("VISPY_DAWN_DISABLE_FEATURE")
    if disabled in CAPABILITIES:
        assert not info[CAPABILITIES[disabled]]


@pytest.mark.parametrize("feature,internalformat,interpolation,value,expected", [
    ("Float32Filterable", "r32f", "linear", 0.25, 64),
    ("Unorm16TextureFormats", "r16", "nearest", 0.75, 191),
])
def test_optional_texture_format_and_recovery(feature, internalformat, interpolation, value, expected):
    enabled = _dawn.device_info()[CAPABILITIES[feature]]
    with app.Canvas(app="dawn_headless", size=(2, 2), show=False):
        gloo.set_viewport(0, 0, 2, 2)
        program = gloo.Program(VERT, """
            uniform sampler2D tex;
            void main() {
                float r = texture2D(tex, vec2(0.375)).r;
                gl_FragColor = vec4(r, 0.0, 0.0, 1.0);
            }
        """)
        program["a_position"] = FULL
        data = np.full((2, 2, 1), value, np.float32)
        if feature == "Float32Filterable":
            data[:, 0] = 0
            data[:, 1] = 1
        tex = gloo.Texture2D(data, format="red",
                             internalformat=internalformat, interpolation=interpolation)
        program["tex"] = tex
        if enabled:
            program.draw("triangles")
            pixel = gloo.read_pixels((0, 0, 2, 2), alpha=True)[0, 0]
            np.testing.assert_allclose(pixel, [expected, 0, 0, 255], atol=1)
        else:
            with pytest.raises(RuntimeError, match=feature):
                program.draw("triangles")
                gloo.read_pixels((0, 0, 2, 2), alpha=True)

        if feature == "Float32Filterable":
            tex.interpolation = "nearest"
            expected = 0
        else:
            program["tex"] = gloo.Texture2D(np.full((2, 2, 1), expected, np.uint8), format="red")
        program.draw("triangles")
        pixel = gloo.read_pixels((0, 0, 2, 2), alpha=True)[0, 0]
        np.testing.assert_allclose(pixel, [expected, 0, 0, 255], atol=1)


@pytest.mark.parametrize("disabled", ["", *CAPABILITIES], ids=["all-supported", *CAPABILITIES])
def test_standard_profile_in_fresh_process(disabled):
    # Instance and device descriptors are selected before the first canvas.
    env = dict(os.environ, VISPY_DAWN_STANDARD_ONLY="1", VISPY_DAWN_HOST_IMPORT="1")
    if disabled:
        env["VISPY_DAWN_DISABLE_FEATURE"] = disabled
    else:
        env.pop("VISPY_DAWN_DISABLE_FEATURE", None)
    flags = ["-B"]
    if sys.flags.no_site:
        flags.append("-S")
    script = "import runpy, sys; runpy.run_path(sys.argv[1])['_check_standard_profile']()"
    proc = subprocess.run(
        [sys.executable, *flags, "-c", script, str(Path(__file__).resolve())],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def _check_standard_profile():
    test_device_feature_requests()
    test_optional_texture_format_and_recovery("Float32Filterable", "r32f", "linear", 0.25, 64)
    test_optional_texture_format_and_recovery("Unorm16TextureFormats", "r16", "nearest", 0.75, 191)
    info = _dawn.device_info()
    with app.Canvas(app="dawn_headless", size=(2, 2), show=False) as canvas:
        canvas_id = canvas._backend._dawn_canvas_id
        timing = _dawn.benchmark_configure_gpu_timing(canvas_id)
        assert timing["supported"] == info["timestamp_query"]
    generation = _dawn.probe()["device_generation"]
    _dawn.lose_device()
    test_device_feature_requests()
    assert _dawn.probe()["device_generation"] > generation
