"""Rendering regressions for reflected uniforms and final vertex conversion."""

import numpy as np
import pytest

from vispy import _dawn, app, gloo

pytestmark = pytest.mark.gpu

VERTEX = """
attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
"""
POSITIONS = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)


def _render(fragment, uniforms, vertex=VERTEX):
    canvas = app.Canvas(app="dawn_headless", size=(8, 8), show=False)
    try:
        with canvas:
            gloo.set_viewport(0, 0, 8, 8)
            gloo.set_clear_color((0, 0, 0, 1))
            gloo.clear(color=True, depth=False, stencil=False)
            program = gloo.Program(vertex, fragment)
            program["a_position"] = gloo.VertexBuffer(POSITIONS)
            for name, value in uniforms.items():
                program[name] = value
            program.draw("triangles")
            return gloo.read_pixels()
    finally:
        canvas.close()


@pytest.mark.parametrize("type_,value,expression", [
    ("float", [[0.0], [1.0]], "u_values[1]"),
    ("vec2", [[0.0, 0.0], [0.0, 1.0]], "u_values[1].y"),
    ("vec3", [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]], "u_values[1].y"),
    ("vec4", [[0.0] * 4, [0.0, 0.0, 0.0, 1.0]], "u_values[1].w"),
])
def test_scalar_and_vector_arrays_use_std140_stride(type_, value, expression):
    image = _render(
        f"uniform {type_} u_values[2]; void main() {{ gl_FragColor=vec4(0.0,{expression},0.0,1.0); }}",
        {"u_values": value},
    )
    assert np.all(image == [0, 255, 0, 255])


@pytest.mark.parametrize("dimension", [2, 3, 4])
def test_matrix_columns_are_padded(dimension):
    matrix = np.zeros((dimension, dimension), np.float32)
    # OpenGL receives flattened values with transpose=False. The selected
    # column/row catches both std140 padding and accidental transposition.
    matrix.flat[dimension + dimension - 1] = 1.0
    image = _render(
        f"uniform mat{dimension} u_matrix; void main() {{ gl_FragColor=vec4(0.0,u_matrix[1][{dimension - 1}],0.0,1.0); }}",
        {"u_matrix": matrix},
    )
    assert np.all(image == [0, 255, 0, 255])


@pytest.mark.parametrize("dimension", [2, 3, 4])
def test_matrix_array_elements_use_reflected_stride(dimension):
    image = _render(
        f"uniform mat{dimension} u_matrices[2]; void main() {{ gl_FragColor=vec4(0.0,u_matrices[1][1][1],0.0,1.0); }}",
        {"u_matrices[0]": np.zeros((dimension, dimension), np.float32),
         "u_matrices[1]": np.eye(dimension, dtype=np.float32)},
    )
    assert np.all(image == [0, 255, 0, 255])


@pytest.mark.parametrize("flag,expected", [(True, [0, 255, 0, 255]), (False, [255, 0, 0, 255])])
def test_boolean_storage_preserves_boolean_expressions(flag, expected):
    image = _render(
        "uniform bool u_flag; void main() { bool local=u_flag && !false; if(local) gl_FragColor=vec4(0,1,0,1); else gl_FragColor=vec4(1,0,0,1); }",
        {"u_flag": flag},
    )
    assert np.all(image == expected)


def test_boolean_array_and_vector_expressions():
    image = _render(
        "uniform bool u_flags[2]; uniform bvec3 u_channels; void main() { if(!u_flags[0] && u_flags[1] && any(u_channels)) gl_FragColor=vec4(0,1,0,1); else gl_FragColor=vec4(1,0,0,1); }",
        {"u_flags": [[False], [True]], "u_channels": (False, True, False)},
    )
    assert np.all(image == [0, 255, 0, 255])


def test_vertex_conversion_runs_after_all_position_edits():
    image = _render(
        "void main() { gl_FragColor=vec4(0,1,0,1); }",
        {},
        """
        attribute vec2 a_position;
        void position() { gl_Position=vec4(a_position,0,1); }
        void main() { position(); gl_Position.y *= 0.5; gl_Position.y += 0.5; }
        """,
    )
    # Independently captured upstream fixture vertex_post_hook establishes
    # read_pixels' top-left origin: clip Y [0,1] fills the first four rows.
    assert np.all(image[:4] == [0, 255, 0, 255])
    assert np.all(image[4:] == [0, 0, 0, 255])


def test_pipeline_error_objects_do_not_report_success():
    result = _dawn.compile_variant(VERTEX, "void main(){ gl_FragColor=vec4(1); gl_FragDepth=0.5; }")
    # The corpus probe has no depth attachment. A shader writing depth is
    # invalid in that actual descriptor even though its SPIR-V compiles.
    assert not result["ok"]
    assert not result["pipeline"]
    assert result["error"]


def test_base_level_admission_rejects_sampling_bias():
    result = _dawn.compile_variant(
        VERTEX,
        "uniform sampler2D u_image; void main(){ gl_FragColor=texture2D(u_image,vec2(0.5),2.0); }",
        base_level_sampling=True,
    )
    assert not result["ok"]
    assert "bias" in result["error"]
