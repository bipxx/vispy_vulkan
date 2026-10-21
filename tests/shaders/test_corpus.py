from pathlib import Path

import numpy as np
import pytest

from vispy import _dawn
from vispy.visuals.image import ImageVisual
from vispy.visuals.shaders import Function, ModularProgram
from vispy.visuals.volume import VolumeVisual

pytestmark = pytest.mark.gpu

ROOT = Path(__file__).resolve().parent / "corpus"
REQUIRED = (
    "image-scalar",
    "image-rgba",
    "volume-mip",
    "volume-iso",
    "volume-translucent",
    "function-blue",
)

VERT = """
attribute vec2 a_position;
void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
}
"""


def _compose_image(data, **kwargs):
    visual = ImageVisual(data, **kwargs)
    visual._prepare_transforms(visual)
    visual._prepare_draw(visual)
    program = visual.view_program
    program.build_if_needed()
    return program.shaders[0].code, program.shaders[1].code


def _compose_volume(method):
    visual = VolumeVisual(np.zeros((4, 4, 4), np.float32), method=method)
    visual._prepare_transforms(visual)
    visual._prepare_draw(visual)
    program = visual.view_program
    program.build_if_needed()
    return program.shaders[0].code, program.shaders[1].code


class Blue(Function):
    def __init__(self):
        Function.__init__(self, "void blue() { gl_FragColor = vec4(0.1, 0.2, 0.9, 1.0); }")


def _live_sources():
    sources = {
        "image-scalar": _compose_image(np.zeros((4, 4), np.float32), cmap="grays"),
        "image-rgba": _compose_image(np.zeros((4, 4, 4), np.uint8)),
        "volume-mip": _compose_volume("mip"),
        "volume-iso": _compose_volume("iso"),
        "volume-translucent": _compose_volume("translucent"),
    }
    program = ModularProgram(
        "attribute vec2 a_position; void main() { gl_Position = vec4(a_position, 0.0, 1.0); }",
        "void main() { $blue(); }",
    )
    program.frag["blue"] = Blue()
    program.build_if_needed()
    sources["function-blue"] = (program.shaders[0].code, program.shaders[1].code)
    return sources


def test_required_variants_create_pipelines_on_vulkan():
    live = _live_sources()
    keys = []
    for name in REQUIRED:
        vert = (ROOT / f"{name}.vert").read_text(encoding="utf-8")
        frag = (ROOT / f"{name}.frag").read_text(encoding="utf-8")
        assert (vert, frag) == live[name]
        has_depth = "gl_FragDepth" in frag
        info = _dawn.compile_variant(vert, frag, has_depth=has_depth)
        print("variant", name, "pipeline", info["pipeline"], "key", info["cache_key"], "entry", info["compiler_entry"])
        if not info["ok"]:
            print(info["error"])
        assert info["compiler_entry"] == "TShader::parse+TProgram::link+GlslangToSpv"
        assert "preprocess" not in info["compiler_entry"]
        assert info["spirv_magic"] == 0x07230203
        assert info["pipeline"] is True
        assert info["cache_hit"] is False
        keys.append(info["cache_key"])
        again = _dawn.compile_variant(vert, frag, has_depth=has_depth)
        assert again["cache_key"] == info["cache_key"]
        assert again["cache_hit"] is True
        assert again["pipeline"] is True
    assert len(set(keys)) == len(keys)


def test_bad_snippet_maps_to_composer_line():
    frag = "\n".join([
        "void main() {",
        "    gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);",
        "    this_is_not_valid_glsl;",
        "}",
    ])
    info = _dawn.compile_variant(VERT, frag)
    print("bad mapped_line", info["mapped_line"])
    print(info["error"])
    assert info["ok"] is False
    assert info["mapped_line"] == 3
