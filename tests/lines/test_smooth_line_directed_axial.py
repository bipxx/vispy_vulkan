"""Arithmetic-domain and directed equality controls; no saved frames are read."""
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from smooth_line_mechanism import Probe, training_probes
from smooth_line_directed_axial import predict_axial, predict_axial_staged, snap_ramp_intercept
sys.path.pop(0)


def test_grid_center_and_directed_boundary_are_distinct_and_translate_exactly():
    assert snap_ramp_intercept(0, -1) == -32
    assert snap_ramp_intercept(0, 1) == 32
    assert snap_ramp_intercept(256, -1) == snap_ramp_intercept(256, 1) == 256
    for intercept in range(-1024, 1025):
        for direction in (-1, 1):
            result = snap_ramp_intercept(intercept, direction)
            assert result % 32 == 0
            assert snap_ramp_intercept(intercept + 512, direction) == result + 512


@pytest.mark.parametrize('probe', [Probe('oblique', (100, 100), (200, 200), 256),
                                 Probe('point', (100, 100), (100, 100), 256),
                                 Probe('thin', (100, 100), (200, 100), 128)])
def test_unrepresented_domains_refuse(probe):
    with pytest.raises(ValueError):
        predict_axial(probe)


def test_directed_transform_is_consistent_under_transpose_and_endpoint_reversal():
    probe = training_probes()[0]
    transformed = replace(probe, start_units=probe.end_units[::-1], end_units=probe.start_units[::-1])
    np.testing.assert_array_equal(predict_axial(probe).transpose(1, 0, 2), predict_axial(transformed))


def test_alphabet_is_computed_without_an_observed_alpha_lookup():
    image = predict_axial(training_probes()[0])
    assert image.dtype == np.uint8 and image.shape == (64, 64, 4)
    assert np.all(image[image[:, :, 0] == 0] == 0)
    assert np.any(image[:, :, 3]) and set(np.unique(image[:, :, :3])) == {0, 255}


def test_staged_arithmetic_preserves_transpose_and_reversed_direction_relation():
    probe = training_probes()[0]
    transformed = replace(probe, start_units=probe.end_units[::-1], end_units=probe.start_units[::-1])
    np.testing.assert_array_equal(predict_axial_staged(probe).transpose(1, 0, 2), predict_axial_staged(transformed))


def test_stage_order_is_observable_at_joint_edges_without_changing_input_geometry():
    probe = training_probes()[65]
    first, staged = predict_axial(probe), predict_axial_staged(probe)
    assert first.shape == staged.shape == (64, 64, 4)
    assert np.array_equal(first[:, 16:48], staged[:, 16:48])
    assert not np.array_equal(first, staged)
