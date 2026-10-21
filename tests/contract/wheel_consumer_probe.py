"""Execute using isolated Python from a clean installed-wheel environment."""

import hashlib
from importlib import machinery, metadata
import json
import os
from pathlib import Path
import sys

import numpy as np
import vispy
from vispy import _dawn, app, gloo, scene
from vispy.util.fonts import _load_glyph
from vispy.visuals.text import _sdf_cpu


repository = Path(sys.argv[1]).resolve()
prefix = Path(sys.prefix).resolve()
assert not prefix.is_relative_to(repository)
assert all(not Path(path).resolve().is_relative_to(repository / "src") for path in sys.path if path)
distribution = metadata.distribution("vispy")
assert distribution.metadata["Name"].lower() == "vispy"
assert distribution.version == vispy.__version__ == "0.17.0+vulkan.1"
for module in (vispy, _dawn, _sdf_cpu):
    assert Path(module.__file__).resolve().is_relative_to(prefix), module.__file__
for module in (_dawn, _sdf_cpu):
    assert any(module.__file__.endswith(suffix) for suffix in machinery.EXTENSION_SUFFIXES)
package = Path(vispy.__file__).parent
license_directory = package / "_licenses"
license_manifest = json.loads((license_directory / "manifest.json").read_text())
assert "vispy-LICENSE.txt" in license_manifest and "OpenSans-Apache-2.0.txt" in license_manifest
for name, digest in license_manifest.items():
    assert hashlib.sha256((license_directory / name).read_bytes()).hexdigest() == digest
if sys.platform != "darwin":
    layer_manifest = package / "VkLayer_vispy_submit.json"
    assert layer_manifest.is_file(), "Native submit instrumentation manifest is missing"
    layer = json.loads(layer_manifest.read_text())["layer"]
    assert layer["name"] == "VK_LAYER_VISPY_submit_count"
    layer_library = (package / layer["library_path"]).resolve()
    assert layer_library.is_relative_to(package) and layer_library.is_file(), "Native submit instrumentation library is missing"

diagnostics = os.environ.get("VISPY_WHEEL_DIAGNOSTICS")
if diagnostics:
    directory = Path(diagnostics).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    original_set_shaders = gloo.Program.set_shaders
    shader_counter = 0

    def capture_shaders(program, vert, frag, geom=None, update_variables=True):
        global shader_counter
        shader_counter += 1
        prefix = directory / f"program-{shader_counter}"
        prefix.with_suffix(".vert").write_text(vert, encoding="utf-8")
        prefix.with_suffix(".frag").write_text(frag, encoding="utf-8")
        compiled = _dawn.compile_variant(vert, frag, True, True, False)
        prefix.with_suffix(".json").write_text(json.dumps(dict(compiled), indent=2), encoding="utf-8")
        for stage in ("vertex", "fragment"):
            prefix.with_suffix(".normalized." + ("vert" if stage == "vertex" else "frag")).write_text(compiled.get("normalized_" + stage, ""), encoding="utf-8")
        return original_set_shaders(program, vert, frag, geom, update_variables)

    gloo.Program.set_shaders = capture_shaders
glyphs = {}
_load_glyph(dict(face="OpenSans", size=32, bold=False, italic=False), "R", glyphs)
glyph = glyphs["R"]["bitmap"].astype(np.float32) / 255
field = np.pad(glyph, 8)
before = field.copy()
assert _sdf_cpu._calc_distance_field(field, field.shape[1], field.shape[0], 8) is None
assert not np.array_equal(field, before)
assert np.all(np.isfinite(field))
canvas = app.Canvas(app="dawn_headless", size=(16, 16), show=False)
with canvas:
    gloo.set_clear_color((0, 0, 1, 1))
    gloo.clear()
    rgba = gloo.read_pixels((0, 0, 16, 16), alpha=True)
    np.testing.assert_array_equal(rgba[8, 8], [0, 0, 255, 255])
canvas.close()
text_canvas = scene.SceneCanvas(app="dawn_headless", size=(64, 64), bgcolor="black", show=False)
scene.visuals.Text("R", color="white", font_size=18, face="OpenSans", pos=(32, 32), parent=text_canvas.scene)
text = text_canvas.render(alpha=True)
assert np.count_nonzero(text[..., :3]) > 30, "Installed text did not render"
text_canvas.close()
device = _dawn.device_info()
assert device["ok"], device
print("wheel consumer evidence", json.dumps({
    "python": sys.version,
    "package_origin": vispy.__file__,
    "device": device,
    "dependencies": {name: metadata.version(name) for name in (
        "numpy", "freetype-py", "hsluv", "kiwisolver", "packaging",
    )},
    "native_module_sha256": {
        module.__name__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in (_dawn, _sdf_cpu)
    },
}, sort_keys=True))
print("wheel consumer verified", distribution.version, vispy.__file__, device["backend"])
