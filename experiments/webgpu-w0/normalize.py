"""Compose the unlit MeshVisual shader and normalize it with the worktree binding."""
import sys
from pathlib import Path

import numpy as np

from vispy import _dawn, use
from vispy.visuals.mesh import MeshVisual
from vispy.visuals.transforms import NullTransform


def main(output):
    use(app="dawn_headless")
    mesh = MeshVisual(
        vertices=np.array([[-1, -1], [3, -1], [-1, 3]], np.float32),
        faces=np.array([[0, 1, 2]], np.uint32),
        vertex_colors=np.tile([0.25, 0.4, 0.75, 1], (3, 1)).astype(np.float32),
    )
    mesh._prepare_draw(mesh)
    program = mesh.view_program
    program.vert["transform"] = NullTransform()
    program.build_if_needed()
    info = _dawn.compile_variant(*(stage.code for stage in program.shaders))
    assert info["ok"], info["error"]
    vertex = info["normalized_vertex"]
    assert "layout(location = 0) in vec3 a_position;" in vertex
    assert "layout(location = 1) in vec4 a_base_color;" in vertex
    for stage, name in (("vert", "vertex"), ("frag", "fragment")):
        dest = output / f"mesh.{stage}.glsl"
        dest.write_text(info[f"normalized_{name}"], encoding="utf-8", newline="\n")
        print(dest.name, info[f"spirv_{name}_words"], "native SPIR-V words")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
