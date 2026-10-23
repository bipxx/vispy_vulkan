# SPDX-License-Identifier: AGPL-3.0-only
"""Arithmetic cancellation, independent pixel transport and geometry controls."""
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from smooth_line_mechanism import Probe
from smooth_line_directed_axial import predict_axial_staged
from smooth_line_slope_planes import (HYPOTHESES, CONSTANTS, EVALUATIONS, fma32_exact,
    intercept, residual, predict_slope_pixels, predict_slope_planes)
sys.path.pop(0)
P = Probe('oblique', (3072, 4096), (12288, 10240), 832)


def exact_fma_oracle(a, b, c):
    a, b, c = (float(np.float32(v)) for v in (a, b, c))
    value = Fraction(a) * Fraction(b) + Fraction(c)
    rounded = np.float32(a * b + c)
    candidates = [np.nextafter(rounded, np.float32(-np.inf)), rounded,
                  np.nextafter(rounded, np.float32(np.inf))]
    return min(candidates, key=lambda x: (abs(Fraction(float(x)) - value), int(x.view(np.uint32)) & 1))


@pytest.mark.parametrize('sign', (-1, 1))
def test_fma_retains_an_addend_smaller_than_a_binary64_midpoint_ulp(sign):
    a = np.float32(1 + 2 ** -12)
    c = np.float32(sign * 2 ** -60)
    expected = exact_fma_oracle(a, a, c)
    assert fma32_exact(a, a, c) == expected
    if sign > 0:
        assert np.float32(float(a) * float(a) + float(c)) != expected


@pytest.mark.parametrize('a,b,c', [(32, .5, -16), (-32, .5, 16),
    (1 + 2 ** -12, 1 - 2 ** -12, -1), (.25, -.5, 2 ** -60), (-.25, -.5, -2 ** -60)])
def test_fma_matches_exact_rational_rounding(a, b, c):
    assert fma32_exact(a, b, c) == exact_fma_oracle(a, b, c)


def test_fma_vectorization_has_the_same_rounding_as_each_scalar():
    a = np.array([1 + 2 ** -12, -.25, 32], np.float32)
    b = np.array([1 + 2 ** -12, .5, .5], np.float32)
    c = np.array([2 ** -60, -2 ** -60, -16], np.float32)
    np.testing.assert_array_equal(fma32_exact(a, b, c), [exact_fma_oracle(x, y, z) for x, y, z in zip(a, b, c)])


@pytest.mark.parametrize('path', CONSTANTS)
def test_intercept_recovers_an_exact_rational_line(path):
    assert intercept(np.float32(.5), 12, 16, path) == 10


@pytest.mark.parametrize('path', EVALUATIONS)
def test_centerline_residual_is_zero_for_exact_points(path):
    np.testing.assert_array_equal(residual(.5, 10, np.array([12, 16, 24]), np.array([16, 18, 22]), path), 0)


@pytest.mark.parametrize('hypothesis', (HYPOTHESES[0], HYPOTHESES[-1]))
def test_full_frame_and_selected_pixels_are_bit_identical(hypothesis):
    pixels = ((0, 0), (12, 16), (28, 27), (48, 40), (63, 63))
    image = predict_slope_planes(P, hypothesis)
    selected = predict_slope_pixels(P, hypothesis, pixels)
    np.testing.assert_array_equal(selected, [image[y, x] for x, y in pixels])
    assert image.shape == (64, 64, 4) and image.dtype == np.uint8
    assert np.any((image[:, :, 3] > 0) & (image[:, :, 3] < 255))


def test_axial_predictions_preserve_the_existing_staged_delegate():
    p = replace(P, end_units=(12288, 4096))
    np.testing.assert_array_equal(predict_slope_planes(p, HYPOTHESES[-1]), predict_axial_staged(p))


@pytest.mark.parametrize('probe', [replace(P, end_units=P.start_units), replace(P, width_units=0),
    replace(P, start_units=(True, 4096)), replace(P, end_units=(17000, 4096))])
def test_outside_training_domain_refuses(probe):
    with pytest.raises(ValueError):
        predict_slope_pixels(probe, HYPOTHESES[0], ((0, 0),))


def test_unknown_family_and_noninteger_pixel_refuse():
    assert len(HYPOTHESES) == len(set(HYPOTHESES)) == 5760
    with pytest.raises(ValueError, match='5760 declared'):
        predict_slope_pixels(P, ('fit',), ((0, 0),))
    with pytest.raises(ValueError, match='Integer in-frame'):
        predict_slope_pixels(P, HYPOTHESES[0], ((.5, 1),))
