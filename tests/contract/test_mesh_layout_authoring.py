"""Geometry and comparison controls without creating a context or device."""
from pathlib import Path
import sys

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
from fixture_mesh_layout_extensions import (  # noqa: E402
    BACKGROUND, CASES, SIZE, TEXT_PLACEMENTS, case_contract, compare, context_provenance, face_normals, inputs,
)
sys.path.pop(0)


def test_asymmetric_mesh_normals_and_deterministic_inputs():
    first, second = inputs(), inputs()
    assert first.keys() == second.keys()
    for name in first:
        np.testing.assert_array_equal(first[name], second[name])
        assert first[name] is not second[name]
    normals = face_normals(first['vertices'], first['faces'])
    np.testing.assert_array_equal(normals[0], [0, 0, 1])
    np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1)
    assert normals[1, 0] < 0 and normals[1, 1] < 0 and 0 < normals[1, 2] < .9
    assert np.unique(first['texture'].reshape(-1, 4), axis=0).shape == (4, 4)
    assert first['z'].shape == (7, 5) and first['z'].min() == 0 and first['z'].max() == 16


@pytest.mark.parametrize('name', CASES)
def test_every_case_has_fixed_inputs_and_full_frame_comparison(name):
    contract = case_contract(name)
    assert contract['case'] == name and contract['size'] == list(SIZE) and contract['reads'] == 1
    assert len(contract['inputs']) == 8 and contract['background'] == list(BACKGROUND)
    assert contract['comparison']['excluded_pixels'] == 0
    assert contract['comparison']['candidate_alignment_or_color_fit'] is False
    assert contract['comparison']['alpha_exact'] is True
    assert len(set(contract['inputs'][key]['sha256'] for key in contract['inputs'])) == 8


def test_required_fractional_dpi_multiline_anchors_and_rotations():
    assert [case_contract('text_dpi' + str(dpi))['dpi'] for dpi in (96, 120, 144)] == [96, 120, 144]
    assert {p[1] for p in TEXT_PLACEMENTS} == {'left', 'center', 'right'}
    assert {p[2] for p in TEXT_PLACEMENTS} == {'top', 'center', 'bottom'}
    assert {p[3] for p in TEXT_PLACEMENTS} == {0, 30, -90}
    assert case_contract('text_dpi120')['text'] == 'Ag\n15'


def test_text_comparison_rejects_one_changed_byte_and_alpha():
    frame = np.empty((SIZE[1], SIZE[0], 4), np.uint8)
    frame[:] = BACKGROUND
    frame[40:60, 40:60, :3] = 255
    compare('text_dpi120', frame, frame.copy())
    changed = frame.copy()
    changed[50, 50, 0] -= 1
    with pytest.raises(AssertionError):
        compare('text_dpi120', changed, frame)
    changed = frame.copy()
    changed[50, 50, 3] -= 1
    with pytest.raises(AssertionError, match='Alpha differs'):
        compare('text_dpi120', changed, frame)


def test_context_provenance_uses_the_exported_GL_parameter_API():
    class GL:
        GL_RENDERER = 0x1F01
        GL_VERSION = 0x1F02

        @staticmethod
        def glGetParameter(value):
            return {GL.GL_RENDERER: 'fixed renderer', GL.GL_VERSION: 'fixed version'}[value]

    class Gloo:
        gl = GL

    assert context_provenance(Gloo) == {'renderer': 'fixed renderer', 'version': 'fixed version'}


def test_mesh_depth_is_contained_and_clipped_background_cannot_prove_lighting():
    data = inputs()
    for name in ('mesh_flat', 'mesh_smooth', 'surface_plot'):
        projection = case_contract(name)['mesh_projection']
        assert projection == {'rect': [0, 0, *SIZE], 'depth_value': 1000, 'flip': [False, True, False]}
        assert max(float(data['vertices'][:, 2].max()), float(data['z'].max())) < projection['depth_value'] / 2
        frame = np.empty((SIZE[1], SIZE[0], 4), np.uint8)
        frame[:] = BACKGROUND
        frame[40:80, 40:184] = (255, 128, 64, 255)
        with pytest.raises(AssertionError, match='Clipped mesh interior'):
            compare(name, frame, frame.copy())
