# SPDX-License-Identifier: AGPL-3.0-only
"""Analytic quality, pan boundaries, and fail-closed residency admission."""
import numpy as np
import pytest

from tools.fixture_large_image import (
    SIDE, CASES, STAGES, RESIDENT_ZERO, input_data, expected_rows,
    quality_result, residency_result, case_contract,
    record_commands,
    rect_bounds,
    assert_framebuffer_draws,
)


def test_source_covers_full_resolution_and_independent_color_alpha_channels():
    scalar = input_data('scalar_nearest')
    assert scalar.shape == (4096, 4096) and scalar.dtype == np.float32
    assert [scalar[y, x] for x, y in ((0, 0), (4, 0), (17, 23))] == [0, .25, 1]
    np.testing.assert_array_equal(np.unique(scalar), [0, .25, .5, 1])
    rgba = input_data('rgba_nearest')
    assert rgba.shape == (4096, 4096, 4) and rgba.dtype == np.uint8
    assert [rgba[y, x].tolist() for x, y in ((0, 0), (4, 0), (17, 23))] == [
        [17, 43, 0, 0], [29, 71, 0, 0], [183, 159, 1, 0]]
    assert np.any(rgba[..., 0] != rgba[..., 1])
    assert set(np.unique(rgba[..., 3])) == {0, 85, 170, 255}
    # Transparent texels carry real RGB: alpha and blending errors cannot hide.
    assert np.any(rgba[rgba[..., 3] == 0, :3])


@pytest.mark.parametrize('name', CASES)
def test_integer_camera_pan_moves_content_and_exposes_opaque_black(name):
    row = expected_rows(name, 'pan', 0, 1)[0]
    np.testing.assert_array_equal(row[:13], np.tile([0, 0, 0, 255], (13, 1)))
    assert row[13].tolist() == expected_rows(name, 'baseline', 17, 18)[0, 0].tolist()
    bottom = expected_rows(name, 'pan', SIDE-17, SIDE)
    assert np.all(bottom[..., :3] == 0) and np.all(bottom[..., 3] == 255)
    assert not np.array_equal(row, expected_rows(name, 'baseline', 0, 1)[0])
    np.testing.assert_array_equal(expected_rows(name, 'return', 51, 53),
                                  expected_rows(name, 'baseline', 51, 53))


@pytest.mark.parametrize('name', ('scalar_nearest', 'rgba_nearest'))
def test_full_frame_quality_checks_far_interior_and_last_pixel_without_crops(name):
    image = np.empty((SIDE, SIDE, 4), np.uint8)
    for start in range(0, SIDE, 64):
        image[start:start+64] = expected_rows(name, 'baseline', start, start+64)
    result = quality_result(name, 'baseline', image)
    assert result['passed'] and result['checked_pixels'] == 16777216 and result['excluded_pixels'] == 0
    image[3001, 2917, 0] ^= 128
    image[-1, -1, 3] ^= 1
    result = quality_result(name, 'baseline', image)
    assert not result['passed'] and result['bad_pixels'] == 2


def test_scalar_rounding_tolerance_never_relaxes_alpha():
    image = np.empty((SIDE, SIDE, 4), np.uint8)
    for start in range(0, SIDE, 64):
        image[start:start+64] = expected_rows('scalar_linear', 'baseline', start, start+64)
    image[0, 4, :3] -= 1
    assert quality_result('scalar_linear', 'baseline', image)['passed']
    image[0, 4, 3] -= 1
    result = quality_result('scalar_linear', 'baseline', image)
    assert not result['passed'] and result['bad_pixels'] == 1


def test_residency_allows_quality_readback_waits_but_requires_actual_draw_submission():
    delta = dict.fromkeys(RESIDENT_ZERO, 0)
    delta.update(draw_calls=1, vk_queue_submits=1, completion_waits=1, finish_calls=1)
    assert residency_result(delta)['passed']
    for key in ('draw_calls', 'vk_queue_submits'):
        assert not residency_result(dict(delta, **{key: 0}))['passed']


@pytest.mark.parametrize('key', RESIDENT_ZERO)
def test_upload_conversion_and_compilation_evidence_is_required_and_must_be_zero(key):
    delta = dict.fromkeys(RESIDENT_ZERO, 0)
    delta.update(draw_calls=1, vk_queue_submits=1)
    for bad in (1, -1, True, 0.0, None):
        assert not residency_result(dict(delta, **{key: bad}))['passed']
    del delta[key]
    assert not residency_result(delta)['passed']


def test_contract_keeps_four_full_stages_and_exact_original_comparison():
    assert len(CASES) == len(set(CASES)) == 4
    assert STAGES == ('baseline', 'repeat', 'pan', 'return')
    for name in CASES:
        spec = case_contract(name)
        assert spec['framebuffer_shape'] == [4096, 4096, 4]
        assert spec['viewbox'] == dict(border_width=0, margin=0, padding=0)
        assert spec['comparison']['full_frame_exact_original']
        assert not spec['performance_qualified']
    with pytest.raises(ValueError):
        expected_rows('scalar_nearest', 'baseline', 0, SIDE+1)
    with pytest.raises(ValueError):
        case_contract('scalar_small')
    with pytest.raises(ValueError):
        quality_result('rgba_nearest', 'baseline', np.zeros((32, 32, 4), np.uint8))


def test_glir_hook_captures_shader_text_and_digests_full_sized_texture_payload():
    import json
    commands, shaders = [], {}
    image = input_data('rgba_nearest')
    record_commands([('DATA', 7, 0, 'void main() {}'), ('DATA', 8, (0, 0), image)], commands, shaders)
    assert shaders == {'7': 'void main() {}'}
    assert commands[1][3]['array']['bytes'] == 67108864
    assert commands[1][3]['array']['shape'] == [4096, 4096, 4]
    assert len(commands[1][3]['array']['sha256']) == 64
    assert len(json.dumps(commands)) < 512
    assert any(row[0] == 'DATA' for row in commands)


def test_camera_metadata_is_json_serializable_with_numpy_rect_coordinates():
    import json
    from types import SimpleNamespace
    rect = SimpleNamespace(left=np.int64(-13), bottom=np.int64(17),
                           width=np.float64(4096), height=np.float32(4096))
    assert json.loads(json.dumps(dict(camera_rect=rect_bounds(rect)))) == dict(camera_rect=[-13, 17, 4096, 4096])


def test_draws_require_rebinding_the_same_framebuffer_after_every_current():
    commands = [['CURRENT', 0, 0], ['FRAMEBUFFER', 3, True], ['DRAW', 4]]
    assert assert_framebuffer_draws(commands, 3) == 1
    for bad in (commands + [['CURRENT', 0, 0], ['DRAW', 4]],
                [['CURRENT', 0, 0], ['FRAMEBUFFER', 2, True], ['DRAW', 4]],
                [['CURRENT', 0, 0], ['FRAMEBUFFER', 3, True]]):
        with pytest.raises(AssertionError):
            assert_framebuffer_draws(bad, 3)
