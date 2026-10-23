"""Controls for the new mechanism investigation, without GL/Vulkan or holdouts."""
from pathlib import Path
import sys

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
from smooth_line_mechanism import (  # noqa: E402
    FUTURE_HOLDOUT_ROLES, PIXEL_UNITS, SIZE, coverage_diagnostics, quantized_levels,
    read_training_artifact, read_training_row, training_artifact_name, training_contract, training_probes,
)
sys.path.pop(0)


def test_training_selection_unique_exact_and_inside_target():
    probes = training_probes()
    assert len(probes) == 7040
    assert len({probe.identity for probe in probes}) == len(probes)
    assert len({(probe.start_units, probe.end_units, probe.width_units) for probe in probes}) == len(probes)
    for probe in probes:
        clip = probe.clip_positions()
        assert clip.dtype == np.float32 and clip.shape == (2, 2)
        reconstructed = np.column_stack(((clip[:, 0] + 1) * (PIXEL_UNITS * SIZE[0] / 2),
                                         (1 - clip[:, 1]) * (PIXEL_UNITS * SIZE[1] / 2)))
        np.testing.assert_array_equal(reconstructed, [probe.start_units, probe.end_units])
        assert np.all(np.abs(clip) < 1)
        assert min(*probe.start_units, *probe.end_units) / PIXEL_UNITS - probe.width_units / PIXEL_UNITS / 2 > 0
        assert max(*probe.start_units, *probe.end_units) / PIXEL_UNITS + probe.width_units / PIXEL_UNITS / 2 < SIZE[0]
    assert training_contract() == training_contract()
    assert training_contract()['blending'] is False and training_contract()['model_selected'] is False


@pytest.mark.parametrize('identity', (*FUTURE_HOLDOUT_ROLES, '../held.npy', '/held.npy', 'unknown', None))
def test_nontraining_role_refused_before_any_artifact_access(identity, monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError('Artifact access preceded scientific-role admission')
    with monkeypatch.context() as context:
        context.setattr(Path, 'read_bytes', forbidden)
        context.setattr(Path, 'stat', forbidden)
        context.setattr(Path, 'lstat', forbidden)
        context.setattr(np, 'load', forbidden)
        with pytest.raises(ValueError, match='not in the frozen training selection'):
            read_training_artifact('unused-root', identity)
        with pytest.raises(ValueError, match='not in the frozen training selection'):
            read_training_row('unused-root', identity)
    assert calls == []


def test_bulk_reader_returns_exact_selected_row_from_real_produced_format():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='vispy-training-reader-control-') as temporary:
        folder = Path(temporary)
        data = np.lib.format.open_memmap(folder / 'training.rgba.npy', mode='w+', dtype=np.uint8,
                                        shape=(7040, 64, 64, 4))
        data[0] = 17
        data[-1] = 93
        data.flush()
        del data
        probes = training_probes()
        assert np.all(read_training_row(folder, probes[0].identity) == 17)
        assert np.all(read_training_row(folder, probes[-1].identity) == 93)
    assert not folder.exists()


@pytest.mark.parametrize('shape,dtype', [((2, 64, 64, 4), np.uint8), ((7040, 1, 1, 4), np.float32)])
def test_bulk_reader_refuses_incomplete_or_wrong_format(shape, dtype):
    import tempfile
    with tempfile.TemporaryDirectory(prefix='vispy-training-reader-refusal-') as temporary:
        np.save(Path(temporary) / 'training.rgba.npy', np.zeros(shape, dtype))
        with pytest.raises(ValueError, match='Complete frozen training array required'):
            read_training_row(temporary, training_probes()[0].identity)


def test_generated_zero_alpha_is_distinct_from_no_fragment():
    frames = np.zeros((1, *SIZE[::-1], 4), np.uint8)
    frames[0, 10, 10, :3] = 255
    result = coverage_diagnostics(frames)
    assert result['generated_fragments'] == 1 and result['zero_alpha_generated_fragments'] == 1
    assert result['alpha_histogram'][0] == 1
    assert result['mechanism_identified'] is False and result['full_frame_parity_proven'] is False


def test_discrete_histogram_is_necessary_but_does_not_identify_a_mechanism():
    frames = np.zeros((1, *SIZE[::-1], 4), np.uint8)
    # A continuous linear phase ramp sampled at these positions has exactly
    # the same RGBA8 levels as a finite population; histogram is not a proof.
    values = np.floor(np.linspace(0, 255, 33) + .5).astype(np.uint8)
    frames[0, 8, :33, :3] = 255
    frames[0, 8, :33, 3] = values
    np.testing.assert_array_equal(values, quantized_levels(32, 'nearest'))
    result = coverage_diagnostics(frames)
    assert {'sample_count': 32, 'rounding': 'nearest'} in result['necessary_lattice_compatibility']
    assert {'sample_count': 64, 'rounding': 'nearest'} in result['necessary_lattice_compatibility']
    assert result['mechanism_identified'] is False and result['coverage_model_selected'] is False


def test_dense_alpha_levels_refute_all_predeclared_small_populations():
    frames = np.zeros((1, *SIZE[::-1], 4), np.uint8)
    frames[0, :4, :, :3] = 255
    frames[0, :4, :, 3] = np.arange(256, dtype=np.uint8).reshape(4, 64)
    result = coverage_diagnostics(frames)
    assert len(result['observed_alpha_levels']) == 256
    assert result['necessary_lattice_compatibility'] == []


@pytest.mark.parametrize('kind', ('wrong_dtype', 'wrong_size', 'empty', 'nonwhite', 'alpha_without_fragment'))
def test_wrong_observation_protocol_refused(kind):
    frames = np.zeros((1, *SIZE[::-1], 4), np.uint8)
    if kind == 'wrong_dtype':
        frames = frames.astype(np.float32)
    elif kind == 'wrong_size':
        frames = frames[:, :32]
    elif kind == 'empty':
        frames = frames[:0]
    elif kind == 'nonwhite':
        frames[0, 8, 8, :3] = (255, 128, 255)
    else:
        frames[0, 8, 8, 3] = 1
    with pytest.raises(ValueError):
        coverage_diagnostics(frames)
