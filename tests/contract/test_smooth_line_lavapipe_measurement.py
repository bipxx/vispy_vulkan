# SPDX-License-Identifier: AGPL-3.0-only
"""The lavapipe smooth-line measurement (W7 step 5) measures with the criterion's own edges and bound, adds no
tolerance, and reads captures and the retained NVIDIA packets only through their recorded hashes. CPU only."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pytest

from tools import smooth_line_lavapipe_measurement as measurement
from tools import smooth_line_parity
from tools.documented_outcomes import DIFFERENCES

ROOT = Path(__file__).resolve().parents[2]
VECTORS = 'tests/reference/napari-vector-layers-opengl'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def line_frame():
    frame = np.zeros((24, 32, 4), np.uint8)
    frame[..., 3] = 255
    frame[10:14, 4:28] = (0, 255, 0, 255)  # rows 11 and 12 have uniform 3x3 neighbourhoods: the line's interior
    return frame


def test_the_bound_edges_and_verdicts_are_the_smooth_line_criterion_s_own():
    assert measurement.EDGE_TOLERANCE is smooth_line_parity.EDGE_TOLERANCE
    assert measurement.EDGE_TOLERANCE == 32
    assert measurement.reference_edges is smooth_line_parity.reference_edges
    assert measurement.smooth_line_difference is smooth_line_parity.smooth_line_difference
    assert ('smooth_line_parity', 'EDGE_TOLERANCE', 32) in DIFFERENCES['D5'].bindings
    # No tolerance of its own: the only module-level constants are the criterion's, the comparison table, the
    # histogram bins (a report format) and paths/patterns.
    constants = {name for name in vars(measurement) if name.isupper()}
    assert constants == {'EDGE_TOLERANCE', 'MAX_DIFFERING_FRACTION', 'COMPARISONS', 'LEVEL_BINS', 'NOPERSPECTIVE',
                         'ROOT'}
    assert measurement.COMPARISONS == {'A': ('candidate', 'upstream'), 'B': ('candidate', 'nvidia'),
                                       'C': ('upstream', 'nvidia')}


def test_metrics_separate_edges_interiors_alpha_and_the_bound():
    reference = line_frame()
    edges = smooth_line_parity.reference_edges(reference)
    assert edges[10, 10] and edges[9, 10] and not edges[11, 15] and not edges[0, 0]
    image = reference.copy()
    image[10, 10, 1] = 255 - 32  # an edge pixel at the bound
    metrics = measurement.frame_metrics(image, reference)
    assert (metrics['edge_max'], metrics['exceeds_bound'], metrics['over_bound_pixels']) == (32, False, 0)
    assert metrics['differing_edge_pixels'] == 1 and metrics['differing_interior_pixels'] == 0
    assert metrics['verdict_with_cap'] is None and metrics['edge_level_histogram']['25-32'] == 1
    image[10, 12, 1] = 255 - 33  # one level beyond it
    metrics = measurement.frame_metrics(image, reference)
    assert (metrics['edge_max'], metrics['exceeds_bound'], metrics['over_bound_edge_pixels']) == (33, True, 1)
    assert metrics['edge_max_at'] == {'row': 10, 'column': 12, 'channel': 'G', 'image': [0, 222, 0, 255],
                                      'reference': [0, 255, 0, 255]}
    assert metrics['verdict_with_cap'] == smooth_line_parity.smooth_line_difference(image, reference)
    assert metrics['verdict_with_cap'] == 'edge difference 33 exceeds 32'
    assert metrics['edge_level_histogram']['33-64'] == 1 and metrics['over_bound_box']['rows'] == [10, 10]
    image[11, 15, 1] -= 1  # an interior pixel is never folded into the edge maximum
    image[9, 20, 3] = 200  # an alpha difference on an edge pixel
    metrics = measurement.frame_metrics(image, reference)
    assert (metrics['differing_interior_pixels'], metrics['interior_max']) == (1, 1)
    assert metrics['interior_max_at']['row'] == 11 and metrics['interior_max_at']['column'] == 15
    assert (metrics['alpha_differing_pixels'], metrics['alpha_max'], metrics['edge_max_alpha']) == (1, 55, 55)
    assert metrics['edge_max'] == 55 and metrics['edge_max_rgb'] == 33
    assert metrics['verdict_with_cap'] == '1 interior pixels differ'
    assert metrics['differing_pixels'] == 4 and not metrics['over_frame_cap']


def test_identical_and_incomparable_frames():
    reference = line_frame()
    metrics = measurement.frame_metrics(reference.copy(), reference)
    assert metrics['comparable'] and metrics['differing_pixels'] == 0 and metrics['edge_max'] == 0
    assert metrics['edge_pixels'] == int(smooth_line_parity.reference_edges(reference).sum()) > 0
    assert metrics['verdict_with_cap'] is None and metrics['verdict_without_cap'] is None
    assert 'edge_max_at' not in metrics and not metrics['exceeds_bound']
    assert measurement.frame_metrics(reference[:-1], reference)['comparable'] is False
    assert measurement.frame_metrics(reference.astype(np.uint16), reference)['comparable'] is False
    assert measurement.exact_metrics(reference, reference.copy()) == {'equal': True, 'comparable': True,
                                                                     'differing_pixels': 0, 'max': 0}


def captures(tmp_path, change=None):
    """Driver-layout captures for both sides made from the retained NVIDIA vector-layer frames."""
    packet = ROOT / VECTORS
    manifest = json.loads((packet / 'manifest.json').read_text(encoding='utf-8'))
    for side in ('upstream', 'candidate'):
        directory = tmp_path / side / 'napari_vector_layers'
        directory.mkdir(parents=True)
        for case in ('vectors', 'tracks', 'shapes_selected'):
            data = (packet / manifest['fixtures'][case]['rgba']['file']).read_bytes()
            if change and (side, case) == change[:2]:
                array = np.load(io.BytesIO(data), allow_pickle=False)
                change[2](array)
                stream = io.BytesIO()
                np.save(stream, array, allow_pickle=False)
                data = stream.getvalue()
            (directory / ('%s.rgba.npy' % case)).write_bytes(data)
            shaders = json.dumps({'1': 'varying vec4 v_color; void main() { gl_FragColor = v_color; }'}).encode()
            (directory / ('%s.shaders.json' % case)).write_bytes(shaders)
            report = {'status': 'PASS_CASE', 'process_exit': 0,
                      'artifacts': {'rgba': {'file': '%s.rgba.npy' % case, 'sha256': sha(data)},
                                    'expanded_shaders': {'file': '%s.shaders.json' % case, 'sha256': sha(shaders)}}}
            (directory / ('%s.result.json' % case)).write_text(json.dumps(report), encoding='utf-8')
    protocol = {'fixtures': [{'name': 'napari_vector_layers', 'cases': ['vectors', 'tracks', 'shapes_selected'],
                              'frames': {case: ['rgba'] for case in ('vectors', 'tracks', 'shapes_selected')},
                              'bound_cases': ['tracks', 'shapes_selected']}],
                'sides': {'nvidia': {'packets': {'napari_vector_layers': {
                    'path': VECTORS, 'manifest_sha256': sha((packet / 'manifest.json').read_bytes())}}}}}
    path = tmp_path / 'protocol.json'
    path.write_text(json.dumps(protocol), encoding='utf-8')
    return path, manifest


def test_measure_reads_capture_reports_and_the_hash_bound_nvidia_packet(tmp_path):
    reference = np.load(ROOT / VECTORS / 'tracks.npy', allow_pickle=False)
    rows, columns = np.nonzero(smooth_line_parity.reference_edges(reference))
    row, column = int(rows[0]), int(columns[0])
    value = int(reference[row, column, 1])
    changed = value + 40 if value <= 215 else value - 40

    def edit(array):
        array[row, column, 1] = changed

    protocol, _ = captures(tmp_path, ('candidate', 'tracks', edit))
    results = measurement.measure(protocol, {'upstream': tmp_path / 'upstream', 'candidate': tmp_path / 'candidate'},
                                  ROOT)
    fixture = results['fixtures']['napari_vector_layers']
    tracks = fixture['cases']['tracks']['frames']['rgba']['comparisons']
    assert tracks['A']['edge_max'] == tracks['B']['edge_max'] == 40 and tracks['C']['edge_max'] == 0
    assert tracks['A']['exceeds_bound'] and tracks['A']['admitted'] and tracks['A']['over_bound_edge_pixels'] == 1
    assert tracks['A']['edge_max_at']['row'] == row and tracks['A']['edge_max_at']['column'] == column
    assert tracks['A']['rule_verdict'] == 'edge difference 40 exceeds 32'
    assert tracks['C']['rule_verdict'] is None and tracks['C']['differing_pixels'] == 0
    assert [(f['comparison'], f['case']) for f in results['findings']] == [('A', 'tracks'), ('B', 'tracks')]
    assert results['interior_findings'] == [] and results['unadmitted_frames'] == []
    vectors = fixture['cases']['vectors']['frames']['rgba']['comparisons']
    assert all(vectors[key]['differing_pixels'] == 0 and vectors[key]['rule_verdict'] is None for key in 'ABC')
    assert fixture['cases']['vectors']['bound_case'] is False and fixture['cases']['tracks']['bound_case'] is True
    assert fixture['cases']['tracks']['clipping']['noperspective_in_expanded_shaders'] == {'upstream': False,
                                                                                           'candidate': False}
    summary = fixture['summary']
    assert (summary['A']['bound']['edge_max'], summary['A']['bound']['edge_max_where']) == (40, 'tracks/rgba')
    assert summary['A']['bound']['frames_over_bound'] == ['tracks/rgba: 40'] and summary['C']['bound']['edge_max'] == 0
    assert summary['A']['context']['edge_max'] == 0 and summary['A']['context']['frames_measured'] == 1
    assert results['overall']['A'] == {'bound_edge_max': 40, 'bound_frames_over_bound': 1,
                                       'context_frames_over_bound': 0}
    assert results['criterion']['EDGE_TOLERANCE'] == 32


def test_measure_refuses_changed_capture_bytes_and_an_unpinned_packet(tmp_path):
    protocol, _ = captures(tmp_path)
    roots = {'upstream': tmp_path / 'upstream', 'candidate': tmp_path / 'candidate'}
    frame = tmp_path / 'candidate/napari_vector_layers/shapes_selected.rgba.npy'
    original = frame.read_bytes()
    frame.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(ValueError, match='frame bytes differ'):
        measurement.measure(protocol, roots, ROOT)
    frame.write_bytes(original)
    data = json.loads(protocol.read_text(encoding='utf-8'))
    data['sides']['nvidia']['packets']['napari_vector_layers']['manifest_sha256'] = '0' * 64
    protocol.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='NVIDIA packet manifest differs'):
        measurement.measure(protocol, roots, ROOT)


def test_a_failed_capture_is_unadmitted_and_never_summarized(tmp_path):
    protocol, _ = captures(tmp_path)
    report_path = tmp_path / 'upstream/napari_vector_layers/shapes_selected.result.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report.update(status='FAILED_PRESERVED', process_exit=1, error='AssertionError: landmark')
    report_path.write_text(json.dumps(report), encoding='utf-8')
    results = measurement.measure(protocol, {'upstream': tmp_path / 'upstream', 'candidate': tmp_path / 'candidate'},
                                  ROOT)
    summary = results['fixtures']['napari_vector_layers']['summary']
    assert summary['A']['bound']['frames_measured'] == 1 and summary['A']['bound']['unadmitted'] == ['shapes_selected/rgba']
    assert summary['C']['bound']['unadmitted'] == ['shapes_selected/rgba'] and summary['B']['bound']['unadmitted'] == []
    assert {(row['comparison'], row['case']) for row in results['unadmitted_frames']} == {('A', 'shapes_selected'),
                                                                                         ('C', 'shapes_selected')}


__all__ = [name for name in dir() if name.startswith('test_')]
