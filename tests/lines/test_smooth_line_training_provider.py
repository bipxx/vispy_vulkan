"""Capture protocol controls with no OpenGL context, device or capture inputs."""
import copy
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
from smooth_line_mechanism import training_probes  # noqa: E402
from smooth_line_training_provider import (  # noqa: E402
    DISABLED, capture_one, expected_vertex_upload, freeze, selected_probes, repeat_indices, validate_state,
    validate_frame, format_spec,
)
sys.path.pop(0)

PROBE = training_probes()[0]


def state():
    return dict(error=0, context_handle=10, framebuffer=20, read_framebuffer=20, framebuffer_complete=True,
                owned_framebuffer=20, owned_texture=30, attachment_name=30,
                attachment_type=0x1702, attachment_bits=[8] * 4, profile_mask=2, context_flags=0,
                attachment_component_type=0x8C17,
                read_buffer=0x8CE0, pack_state=[4, 0, 0, 0, 0, 0, 0],
                samples=0, sample_buffers=0, channel_bits=[8] * 4, color_encoding=0x2601,
                viewport=[0, 0, 64, 64], color_mask=[True] * 4, hint=0x1100, line_smooth=True,
                line_width=1., width_range=[1., 64.], width_granularity=.0625, subpixel_bits=8,
                renderer='fixed renderer', version='fixed version', vendor='fixed vendor',
                **{name: False for name in DISABLED})


def commands():
    return [['DATA', 5, 0, expected_vertex_upload(PROBE)], ['FUNC', 'glLineWidth', 1.],
            ['FUNC', 'glClearColor', 0., 0., 0., 0.], ['FUNC', 'glClear', 0x4000],
            ['DRAW', 7, 'lines', [0, 2], 1], ['FUNC', 'glFinish']]


class Backend:
    program_id, vertex_buffer_id = 7, 5
    target_format = 'rgba8'

    def __init__(self):
        self.calls = []
        self.baseline = state()
        self.before, self.after = state(), state()
        self.observations = 0
        self.frame = np.zeros((64, 64, 4), np.uint8)
        self.frame[20, 12:52] = [255, 255, 255, 128]
        self.commands = commands()

    def prepare(self, probe):
        self.calls.append('prepare')

    def flush_commands(self):
        self.calls.append('dispatch')

    def observe(self):
        self.calls.append('observe')
        self.observations += 1
        return self.before if self.observations == 1 else self.after

    def read_pixels(self):
        self.calls.append('read')
        return self.frame

    def take_commands(self):
        return self.commands

    def peek_commands(self):
        return list(self.commands)


class Sink:
    def __init__(self):
        self.raw, self.accepted = [], []

    def record(self, *args):
        self.raw.append(args)

    def accept(self, index):
        self.accepted.append(index)


def test_one_read_with_observed_state_on_both_sides_and_raw_before_admission():
    backend, sink = Backend(), Sink()
    capture_one(backend, sink, PROBE, 0)
    assert backend.calls == ['prepare', 'dispatch', 'observe', 'read', 'observe']
    assert len(sink.raw) == 1 and sink.accepted == [0]


@pytest.mark.parametrize('field', ('identity', 'width_units', 'start_units', 'end_units'))
def test_forged_or_nontraining_descriptor_never_reaches_backend_or_sink(field):
    values = dict(identity='new-holdout-role-0', width_units=384,
                  start_units=(0, 0), end_units=(1, 1))
    backend, sink = Backend(), Sink()
    with pytest.raises(ValueError, match='exact frozen training'):
        capture_one(backend, sink, replace(PROBE, **{field: values[field]}), 0)
    assert not backend.calls and not sink.raw and not sink.accepted


@pytest.mark.parametrize('field,value', [
    ('error', 1280), ('context_handle', 0), ('framebuffer', 0), ('framebuffer_complete', False),
    ('samples', 4), ('sample_buffers', 1), ('channel_bits', [8, 8, 8, 0]), ('color_encoding', 0x8C40),
    ('viewport', [0, 0, 32, 64]), ('color_mask', [True, True, True, False]), ('hint', 0x1102),
    ('line_smooth', False), ('line_width', 2.), ('renderer', 'different'), ('version', 'different'),
    ('width_range', [1., .5]), ('width_granularity', -1.), ('subpixel_bits', -1),
    ('read_framebuffer', 21),
    ('attachment_name', 31), ('attachment_type', 0x8D41), ('attachment_bits', [8, 8, 8, 0]),
    ('attachment_component_type', 0x1406),
    ('profile_mask', 1), ('context_flags', 1),
    ('read_buffer', 0x0405), ('pack_state', [4, 1, 0, 0, 0, 0, 0]),
    ('width_range', [1., .75]), ('width_granularity', .3), ('vendor', 'different'),
] + [(name, True) for name in DISABLED])
def test_wrong_observed_state_refuses_before_read_or_artifact(field, value):
    backend, sink = Backend(), Sink()
    backend.before[field] = value
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert 'read' not in backend.calls and not sink.raw and not sink.accepted
    assert backend.last_before == backend.before and backend.last_commands == backend.commands


def test_different_complete_nonzero_fbo_refuses_even_when_read_and_draw_agree():
    backend, sink = Backend(), Sink()
    backend.before.update(framebuffer=21, read_framebuffer=21)
    with pytest.raises(ValueError, match='owned Gloo'):
        capture_one(backend, sink, PROBE, 0)
    assert 'read' not in backend.calls and not sink.raw


def test_zero_reported_minimum_does_not_clamp_positive_width():
    baseline = state()
    baseline['width_range'] = [0., 64.]
    validate_state(baseline, PROBE, baseline)


def test_failed_before_read_does_not_retain_previous_probe_after_state():
    backend, sink = Backend(), Sink()
    backend.last_after = {'stale': True}
    backend.before['error'] = 1280
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert backend.last_after is None


def test_repeat_sink_retains_canonical_training_indices_and_separate_row_order():
    import tempfile
    from smooth_line_training_provider import TrainingSink
    indices = repeat_indices()
    assert len(indices) == 64 and indices[0] == 0 and indices[-1] == 7039
    probes = training_probes()
    with tempfile.TemporaryDirectory(prefix='vispy-repeat-control-') as temporary:
        with TrainingSink(temporary, len(indices), indices) as sink:
            for index in indices:
                sink.record(index, probes[index], Backend().frame, state(), state(), commands())
                sink.accept(index)
        assert sink.raw_frames == sink.accepted_frames == 64
        assert np.load(Path(temporary) / 'training.rgba.npy', allow_pickle=False).shape == (64, 64, 64, 4)


@pytest.mark.parametrize('indices', [(0, 0), (0, True), (-1, 0), (0, 7040), (0,)])
def test_repeat_sink_refuses_invalid_selection_before_opening_files(indices):
    from smooth_line_training_provider import TrainingSink
    with pytest.raises(ValueError, match='distinct training row'):
        TrainingSink('unused-root', 2, indices)


@pytest.mark.parametrize('field,value', [('context_handle', 99), ('framebuffer', 21), ('line_width', 2.), ('error', 1282)])
def test_state_changed_during_final_read_preserves_raw_but_refuses_admission(field, value):
    backend, sink = Backend(), Sink()
    backend.after[field] = value
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert backend.calls.count('read') == 1 and len(sink.raw) == 1 and not sink.accepted


@pytest.mark.parametrize('kind', ('shape', 'dtype', 'empty', 'colored', 'unwritten_alpha', 'zero_alpha', 'border'))
def test_wrong_pixels_are_retained_without_admission(kind):
    backend, sink = Backend(), Sink()
    if kind == 'shape':
        backend.frame = backend.frame[:32]
    elif kind == 'dtype':
        backend.frame = backend.frame.astype(np.float32)
    elif kind == 'empty':
        backend.frame[:] = 0
    elif kind == 'colored':
        backend.frame[20, 20, 1] = 128
    elif kind == 'unwritten_alpha':
        backend.frame[30, 30, 3] = 1
    elif kind == 'zero_alpha':
        backend.frame[..., 3] = 0
    else:
        backend.frame[0, 20] = 255
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert len(sink.raw) == 1 and not sink.accepted


@pytest.mark.parametrize('kind', ('extra_draw', 'extra_finish', 'no_clear', 'wrong_order', 'wrong_width',
                                 'wrong_upload', 'wrong_vertices', 'no_draw', 'no_finish', 'injected_state'))
def test_wrong_command_scope_is_retained_without_admission(kind):
    backend, sink = Backend(), Sink()
    if kind == 'extra_draw':
        backend.commands.append(copy.deepcopy(backend.commands[4]))
    elif kind == 'extra_finish':
        backend.commands.append(['FUNC', 'glFinish'])
    elif kind == 'no_clear':
        del backend.commands[3]
    elif kind == 'wrong_order':
        backend.commands[3], backend.commands[4] = backend.commands[4], backend.commands[3]
    elif kind == 'wrong_width':
        backend.commands[1][2] = 2
    elif kind == 'wrong_upload':
        backend.commands[0][3] = freeze(np.zeros((2, 2), np.float32))
    elif kind == 'wrong_vertices':
        backend.commands[4][3] = [0, 3]
    elif kind == 'no_draw':
        del backend.commands[4]
    elif kind == 'no_finish':
        backend.commands.pop()
    else:
        backend.commands.insert(3, ['FUNC', 'glEnable', 0x0BE2])
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert len(sink.raw) == 1 and not sink.accepted


@pytest.mark.parametrize('optimized', (False, True))
def test_isolated_entrypoint_help_and_optimization_refusal(optimized):
    import subprocess
    flags = ['-I', '-B'] + (['-O'] if optimized else [])
    result = subprocess.run([sys.executable, *flags, str(TOOLS / 'capture_smooth_line_training.py'), '--help'],
                            capture_output=True, text=True, timeout=30)
    if optimized:
        assert result.returncode != 0
        assert 'requires -I -B with optimization disabled' in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert '--authoring-sha256' in result.stdout


def test_selected_input_and_excluded_state_tables_are_immutable():
    with pytest.raises(TypeError):
        selected_probes()['new-holdout-role-0'] = PROBE
    with pytest.raises(TypeError):
        DISABLED['blend'] = 0


@pytest.mark.parametrize('index', (-1, 1, 7040, True))
def test_wrong_row_order_refuses_before_backend(index):
    backend, sink = Backend(), Sink()
    with pytest.raises(ValueError, match='frozen descriptor order'):
        capture_one(backend, sink, PROBE, index)
    assert not backend.calls and not sink.raw


def test_sequential_sink_roundtrips_rows_and_closes_on_failure():
    import tempfile
    from smooth_line_training_provider import TrainingSink
    with tempfile.TemporaryDirectory(prefix='vispy-training-sink-control-') as temporary:
        folder = Path(temporary)
        with TrainingSink(folder, 2) as sink:
            for index, probe in enumerate(training_probes()[:2]):
                frame = Backend().frame
                sink.record(index, probe, frame, state(), state(), [])
                sink.accept(index)
        assert sink.data.closed and sink.observations.closed and sink.commands.closed
        assert sink.raw_frames == sink.accepted_frames == 2
        frames = np.load(folder / 'training.rgba.npy', allow_pickle=False)
        assert frames.shape == (2, 64, 64, 4)
        np.testing.assert_array_equal(frames[0], Backend().frame)
        np.testing.assert_array_equal(frames[1], Backend().frame)
    assert not folder.exists()


def test_sink_refuses_duplicate_and_preserves_incomplete_prefix():
    import tempfile
    from smooth_line_training_provider import TrainingSink
    with tempfile.TemporaryDirectory(prefix='vispy-training-sink-refusal-') as temporary:
        folder = Path(temporary)
        with pytest.raises(ValueError, match='Duplicate'):
            with TrainingSink(folder, 2) as sink:
                sink.record(0, PROBE, Backend().frame, state(), state(), [])
                sink.accept(0)
                sink.record(0, PROBE, Backend().frame, state(), state(), [])
        assert sink.raw_frames == sink.accepted_frames == 1
        assert sink.data.closed and sink.observations.closed and sink.commands.closed
        with pytest.raises(ValueError):
            np.load(folder / 'training.rgba.npy', allow_pickle=False)
    assert not folder.exists()


def float_backend():
    backend = Backend()
    backend.target_format = 'rgba32f'
    backend.frame = backend.frame.astype(np.float32) / np.float32(255)
    backend.frame[..., 3][backend.frame[..., 0] == 1] = np.float32(1 / 32768)
    for observed in (backend.baseline, backend.before, backend.after):
        observed.update(channel_bits=[32] * 4, attachment_bits=[32] * 4, attachment_component_type=0x1406)
    return backend


def test_float_capture_retains_sub_byte_alpha_without_quantization_or_extra_reads():
    backend, sink = float_backend(), Sink()
    capture_one(backend, sink, PROBE, 0)
    assert backend.calls.count('read') == 1 and sink.accepted == [0]
    measured = sink.raw[0][2]
    assert measured.dtype == np.float32 and measured[20, 20, 3] == np.float32(1 / 32768)


@pytest.mark.parametrize('field,value', [('attachment_bits', [16] * 4), ('channel_bits', [8] * 4),
                                        ('attachment_component_type', 0x8C17)])
def test_float_target_must_be_observed_as_32bit_float_before_read(field, value):
    backend, sink = float_backend(), Sink()
    backend.before[field] = value
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert 'read' not in backend.calls and not sink.raw


@pytest.mark.parametrize('value', (np.nan, np.inf, -np.inf, -0.01, 1.01))
def test_float_invalid_alpha_is_retained_and_refused(value):
    backend, sink = float_backend(), Sink()
    backend.frame[20, 20, 3] = value
    with pytest.raises(ValueError, match='Finite normalized'):
        capture_one(backend, sink, PROBE, 0)
    assert len(sink.raw) == 1 and not sink.accepted


def test_float_frame_not_accepted_by_default_rgba8_protocol():
    with pytest.raises(ValueError):
        validate_frame(float_backend().frame)


@pytest.mark.parametrize('name', ('rgba16f', 'float', None, True))
def test_undeclared_observation_format_is_refused(name):
    with pytest.raises(ValueError, match='Only declared'):
        format_spec(name)


def test_float_sink_roundtrips_raw_float_bits_and_distinct_repeat_selection():
    import tempfile
    from smooth_line_training_provider import TrainingSink
    probes = training_probes()
    frame = float_backend().frame
    with tempfile.TemporaryDirectory(prefix='vispy-float-training-sink-') as temporary:
        with TrainingSink(temporary, 2, (0, 7039), target_format='rgba32f') as sink:
            for index in (0, 7039):
                sink.record(index, probes[index], frame, {}, {}, [])
                sink.accept(index)
        loaded = np.load(Path(temporary) / 'training.rgba.npy', allow_pickle=False)
        assert loaded.dtype == np.float32 and loaded.shape == (2, 64, 64, 4)
        assert loaded[0].tobytes() == loaded[1].tobytes() == frame.tobytes()
    assert not Path(temporary).exists()


def test_normalized_16bit_attachment_is_distinct_from_float_attachment_with_float_readback():
    backend, sink = float_backend(), Sink()
    backend.target_format = 'rgba16'
    for observed in (backend.baseline, backend.before, backend.after):
        observed.update(channel_bits=[16] * 4, attachment_bits=[16] * 4, attachment_component_type=0x8C17)
    capture_one(backend, sink, PROBE, 0)
    assert format_spec('rgba16') == (np.dtype('<f4'), 16, 1, 0x8C17, 'float')
    assert backend.calls.count('read') == 1 and sink.accepted == [0]
    assert sink.raw[0][2].dtype == np.float32


def test_normalized_16bit_mode_refuses_float_attachment_before_read():
    backend, sink = float_backend(), Sink()
    backend.target_format = 'rgba16'
    with pytest.raises(ValueError):
        capture_one(backend, sink, PROBE, 0)
    assert 'read' not in backend.calls and not sink.raw
