"""Join actual asynchronous pass timestamps to final presentation completions."""

import time

import pytest

from vispy import _dawn, app, gloo
from tools.benchmark_frames import CandidateCompletions, FrameCompletionSamples, InstrumentationUnavailable
from tools.fixture_gloo import FULL, FRAG, VERT


@pytest.mark.gpu
def test_collector_drains_bounded_gpu_maps_and_preserves_completion_samples():
    canvas = app.Canvas(app='pyqt6', size=(32, 24), show=True, vsync=False)
    canvas_id = canvas._backend._dawn_canvas_id
    try:
        canvas.app.process_events()
        canvas.set_current()
        gloo.set_viewport(0, 0, 32, 24)
        program = gloo.Program(VERT, FRAG)
        program['a_position'] = gloo.VertexBuffer(FULL)
        program['u_color'] = (1, 0, 0, 1)
        program.draw('triangles')
        _dawn.present(canvas_id)
        _dawn.finish(canvas_id)  # Cold setup, before the sampled counter baseline.
        collector = CandidateCompletions(canvas)
        before = collector.counters()
        receipts = FrameCompletionSamples()
        for phase, first, count in [('warmup', 0, 4), ('measured', 4, 8)]:
            for frame_id in range(first, first + count):
                deadline = time.monotonic() + 5
                receipts.collect(collector.poll(), phase)
                while not _dawn.frame_ready(canvas_id):
                    receipts.collect(collector.poll(), phase)
                    assert time.monotonic() < deadline, 'query backpressure failed to drain'
                collector.begin(frame_id)
                receipts.begin(frame_id, phase)
                program['u_color'] = (frame_id / 11, 0, 0, 1)
                program.draw('triangles')
                _dawn.present(canvas_id)
            deadline = time.monotonic() + 5
            while receipts.count(phase) < count:
                receipts.collect(collector.poll(), phase)
                assert time.monotonic() < deadline, 'presentation completion timed out'
            collector.drain_gpu(first, count, 5, completions=receipts, phase=phase)
            if collector.gpu_metadata['enabled']:
                collector.gpu_frames.join(receipts.samples(phase))
        samples = receipts.samples('warmup') + receipts.samples('measured')
        assert len(receipts.observed) == 12
        assert receipts.issued == {frame_id: 'warmup' if frame_id < 4 else 'measured'
                                   for frame_id in range(12)}
        assert collector.boundary['whole_qt_paint_scope_verified'] is False
        originals = [dict(sample) for sample in samples]
        assert [sample['frame_id'] for sample in samples] == list(range(12))
        assert all(sample['presented'] and sample['status'] == 'success' for sample in samples)
        if collector.gpu_metadata['supported']:
            collector.gpu_frames.join(samples)
            assert all(sample['gpu_timing']['status'] == 'success' for sample in samples)
            assert all([interval['kind'] for interval in sample['gpu_timing']['passes']] ==
                       ['scene', 'present_capture', 'surface_conversion'] for sample in samples)
        else:
            with pytest.raises(InstrumentationUnavailable, match='unsupported'):
                collector.gpu_frames.join(samples)
        assert [{key: value for key, value in sample.items() if key != 'gpu_timing'}
                for sample in samples] == originals
        after = collector.counters()
        assert after['finish_calls'] == before['finish_calls']
        assert after['completion_waits'] == before['completion_waits']
        assert after['pending_timestamp_frames'] == 0
        assert after['peak_pending_timestamp_frames'] <= after['frame_slots']
        assert all(after[key] == before[key] for key in
                   ('texture_uploads', 'buffer_uploads', 'pipeline_misses', 'portable_shader_misses'))
        print('actual collector GPU join', collector.gpu_metadata, 'frames', len(samples),
              'deliberate waits', after['completion_waits'] - before['completion_waits'])
    finally:
        canvas.close()
