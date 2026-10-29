# SPDX-License-Identifier: AGPL-3.0-only
"""Measure the smooth-line edge bound on another renderer pair (W7 step 5: Mesa lavapipe against llvmpipe).

The smooth-line criterion (tools/smooth_line_parity.py, decision D5) lets a pixel differ by at most EDGE_TOLERANCE
(32 levels) where the reference's 3x3 neighbourhood is not uniform. The bound was set on NVIDIA only: Dawn on RTX 4090
Vulkan against NVIDIA OpenGL measured 26-29 (docs/smooth-lines.md). This tool measures frames captured under a
protocol written before capture (build/runs/w7-lavapipe-smooth-254/protocol.json and its amendment), per frame:

- A: the candidate (Dawn on lavapipe) against upstream vispy on llvmpipe OpenGL, the analogue of the measurement
  behind the bound;
- B: the candidate against the admitted NVIDIA OpenGL reference packets;
- C: upstream on llvmpipe against the same NVIDIA packets.

Every metric uses the criterion's own reference_edges() and EDGE_TOLERANCE, and the verdicts are
smooth_line_difference() and the comparison module of each case's decision. This tool defines no tolerance and
changes no criterion: a frame whose edge maximum exceeds EDGE_TOLERANCE is reported as a finding, never admitted.

Captures use capture_case.py's layout (<root>/<fixture>/<case>.result.json); the optional tool control uses the
capture tools' manifest layouts and is compared exactly with the candidate captures. NVIDIA frames are read from the
packets named by the protocol, each checked against its packet manifest, whose own hash the protocol pins.

Usage (any environment with numpy):
    python tools/smooth_line_lavapipe_measurement.py --protocol <protocol.json> --upstream <dir> --candidate <dir>
        [--repeat-upstream <dir>] [--repeat-candidate <dir>] [--tool-candidate <dir>] --output <results.json>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
from pathlib import Path
import re

import numpy as np

try:
    from .smooth_line_parity import EDGE_TOLERANCE, MAX_DIFFERING_FRACTION, reference_edges, smooth_line_difference
except ImportError:
    from smooth_line_parity import EDGE_TOLERANCE, MAX_DIFFERING_FRACTION, reference_edges, smooth_line_difference

ROOT = Path(__file__).resolve().parents[1]
COMPARISONS = {'A': ('candidate', 'upstream'), 'B': ('candidate', 'nvidia'), 'C': ('upstream', 'nvidia')}
LEVEL_BINS = ((1, 8), (9, 16), (17, 24), (25, 32), (33, 64), (65, 128), (129, 255))
NOPERSPECTIVE = re.compile(r'\bnoperspective\b')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _module(name):
    return importlib.import_module('.' + name, __package__) if __package__ else importlib.import_module(name)


def _location(difference, image, reference, mask):
    per_pixel = difference.max(axis=2)
    rows, columns = np.nonzero(mask)
    index = int(np.argmax(per_pixel[rows, columns]))
    row, column = int(rows[index]), int(columns[index])
    channel = int(np.argmax(difference[row, column]))
    return {'row': row, 'column': column, 'channel': 'RGBA'[channel], 'image': image[row, column].tolist(),
            'reference': reference[row, column].tolist()}


def frame_metrics(image, reference):
    """Per-frame measurements; edges and interiors are those of reference_edges(reference)."""
    if image.shape != reference.shape or image.dtype != reference.dtype or image.ndim != 3 or image.shape[2] != 4:
        return {'comparable': False, 'image_shape': list(image.shape), 'reference_shape': list(reference.shape),
                'image_dtype': image.dtype.str, 'reference_dtype': reference.dtype.str}
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    per_pixel = difference.max(axis=2)
    differing = per_pixel > 0
    edges = reference_edges(reference)
    interior = ~edges

    def largest(mask, channels):
        values = difference[mask][:, channels]
        return int(values.max()) if values.size else 0

    over = per_pixel > EDGE_TOLERANCE
    levels = per_pixel[differing & edges]
    metrics = {
        'comparable': True, 'pixels': int(differing.size), 'edge_pixels': int(edges.sum()),
        'differing_pixels': int(differing.sum()), 'differing_fraction': float(differing.sum() / differing.size),
        'differing_edge_pixels': int((differing & edges).sum()),
        'differing_interior_pixels': int((differing & interior).sum()),
        'edge_max': largest(edges, slice(0, 4)), 'edge_max_rgb': largest(edges, slice(0, 3)),
        'edge_max_alpha': largest(edges, slice(3, 4)), 'interior_max': largest(interior, slice(0, 4)),
        'alpha_differing_pixels': int((difference[..., 3] > 0).sum()), 'alpha_max': int(difference[..., 3].max()),
        'over_bound_pixels': int(over.sum()), 'over_bound_edge_pixels': int((over & edges).sum()),
        'over_bound_interior_pixels': int((over & interior).sum()),
        'edge_level_histogram': {'%d-%d' % (low, high): int(((levels >= low) & (levels <= high)).sum())
                                 for low, high in LEVEL_BINS},
        'verdict_with_cap': smooth_line_difference(image, reference),
        'verdict_without_cap': smooth_line_difference(image, reference, max_differing_fraction=None)}
    metrics['exceeds_bound'] = metrics['edge_max'] > EDGE_TOLERANCE
    metrics['over_frame_cap'] = metrics['differing_pixels'] > MAX_DIFFERING_FRACTION * metrics['pixels']
    if metrics['edge_max']:
        metrics['edge_max_at'] = _location(difference, image, reference, differing & edges)
    if metrics['interior_max']:
        metrics['interior_max_at'] = _location(difference, image, reference, differing & interior)
    if metrics['over_bound_pixels']:
        rows, columns = np.nonzero(over)
        height, width = per_pixel.shape
        metrics['over_bound_box'] = {'rows': [int(rows.min()), int(rows.max())],
                                     'columns': [int(columns.min()), int(columns.max())],
                                     'touches_frame_border': bool(rows.min() <= 1 or columns.min() <= 1 or
                                                                  rows.max() >= height - 2 or
                                                                  columns.max() >= width - 2)}
    return metrics


def exact_metrics(image, reference):
    """Exact equality, for the reproducibility and tool controls."""
    if image.shape != reference.shape or image.dtype != reference.dtype:
        return {'equal': False, 'comparable': False}
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    return {'equal': bool(not difference.any()), 'comparable': True,
            'differing_pixels': int(np.any(difference, axis=2).sum()), 'max': int(difference.max())}


def rule_verdict(fixture, case, image, reference):
    """The repository comparison that the case's decision applies (information only); None if it passes."""
    if fixture == 'napari_threedee_overlay':
        return smooth_line_difference(image, reference)
    if fixture in ('wide_lines', 'wide_lines_depth'):
        return _module('wide_lines_comparison').wide_line_difference(not case.endswith('aliased'), image, reference)
    if fixture == 'napari_vector_layers':
        if _module('fixture_napari_vector_layers').CRITERIA[case] == 'smooth_line':
            return _module('napari_vector_layers_comparison').smooth_line_case_difference(case, image, reference)
        metrics = exact_metrics(image, reference)
        return None if metrics['equal'] else 'not exact: %s' % metrics
    if fixture == 'napari_layer_families':
        return _module('napari_layer_families_comparison').layer_family_difference(case, image, reference)
    if fixture == 'mesh_layout_extensions':
        try:
            _module('mesh_layout_smooth_line').compare(case, image, reference)
        except AssertionError as error:
            return 'assertion: %s' % (error,)
        return None
    raise ValueError(fixture)


def _array(path, expected):
    data = Path(path).read_bytes()
    if sha_bytes(data) != expected:
        raise ValueError('frame bytes differ from their record: %s' % path)
    return np.load(io.BytesIO(data), allow_pickle=False), {'file': str(path), 'sha256': expected}


def load_driver_frame(root, fixture, case, frame):
    """A frame captured by capture_case.py: (array or None, information)."""
    report_path = Path(root) / fixture / ('%s.result.json' % case)
    if not report_path.is_file():
        return None, {'status': 'missing', 'reason': 'no result.json'}
    report = json.loads(report_path.read_text(encoding='utf-8'))
    artifact = report.get('artifacts', {}).get(frame)
    if artifact is None:
        return None, {'status': 'missing', 'reason': report.get('status'),
                      'error_tail': (report.get('error') or '')[-600:]}
    array, info = _array(report_path.parent / artifact['file'], artifact['sha256'])
    admitted = report.get('status') == 'PASS_CASE' and report.get('process_exit') == 0
    info.update(status='admitted' if admitted else 'unadmitted', report_sha256=sha_bytes(report_path.read_bytes()))
    if not admitted:
        info['error_tail'] = (report.get('error') or '')[-600:]
    return array, info


def driver_shaders(root, fixture, case):
    report_path = Path(root) / fixture / ('%s.result.json' % case)
    if not report_path.is_file():
        return None
    artifact = json.loads(report_path.read_text(encoding='utf-8')).get('artifacts', {}).get('expanded_shaders')
    return None if artifact is None else (report_path.parent / artifact['file']).read_text(encoding='utf-8')


def load_tool_frame(root, fixture, case, frame):
    """A frame captured by an unchanged capture tool (the amendment's control), from its manifest layout."""
    directory = Path(root) / fixture
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    record = manifest['fixtures'].get(case)
    if record is None:
        return None, {'status': 'missing', 'reason': str(manifest['errors'].get(case, {}).get('error'))[-600:]}
    artifact = record['artifacts'][frame] if fixture == 'napari_threedee_overlay' else record[frame]
    array, info = _array(directory / artifact['file'], artifact['sha256'])
    info['status'] = 'admitted'
    return array, info


def nvidia_manifest(protocol, fixture, repository):
    packet = protocol['sides']['nvidia']['packets'][fixture]
    directory = Path(repository) / packet['path']
    body = (directory / 'manifest.json').read_bytes()
    if sha_bytes(body) != packet['manifest_sha256']:
        raise ValueError('NVIDIA packet manifest differs from the protocol: %s' % fixture)
    return directory, json.loads(body)


def load_nvidia_frame(protocol, fixture, case, frame, repository):
    directory, manifest = nvidia_manifest(protocol, fixture, repository)
    if fixture == 'mesh_layout_extensions':
        image, params, _extras = _module('mesh_layout_reference').load_case(case, directory, producer_root=repository)
        record = manifest['fixtures'][case]['artifacts']['rgba.npy']
        return np.array(image), {'status': 'admitted', 'file': str(directory / record['file']),
                                 'sha256': record['sha256'], 'loaded_by': 'tools/mesh_layout_reference.load_case'}
    record = manifest['fixtures'].get(case)
    if record is None:
        return None, {'status': 'not admitted in the packet',
                      'reason': str(manifest['errors'].get(case, {}).get('error'))}
    artifact = record['artifacts'][frame] if fixture == 'napari_threedee_overlay' else record[frame]
    array, info = _array(directory / artifact['file'], artifact['sha256'])
    info['status'] = 'admitted'
    return array, info


def _summary(cases, comparison, bound):
    rows = [(case, frame, entry['comparisons'][comparison]) for case, record in cases.items()
            if record['bound_case'] == bound for frame, entry in record['frames'].items()]
    measured = [(case, frame, m) for case, frame, m in rows if m.get('measured') and m.get('comparable')
                and m.get('admitted')]
    summary = {'frames': len(rows), 'frames_measured': len(measured),
               'not_measured': ['%s/%s: %s' % (case, frame, m.get('reason') or m.get('image_shape'))
                                for case, frame, m in rows if not (m.get('measured') and m.get('comparable'))],
               'unadmitted': ['%s/%s' % (case, frame) for case, frame, m in rows
                              if m.get('measured') and not m.get('admitted')]}
    if not measured:
        return summary
    top = max(measured, key=lambda row: row[2]['edge_max'])
    summary.update(
        edge_max=top[2]['edge_max'], edge_max_where='%s/%s' % top[:2],
        frames_over_bound=['%s/%s: %d' % (case, frame, m['edge_max']) for case, frame, m in measured
                           if m['exceeds_bound']],
        over_bound_edge_pixels=sum(m['over_bound_edge_pixels'] for _, _, m in measured),
        differing_edge_pixels=sum(m['differing_edge_pixels'] for _, _, m in measured),
        edge_pixels=sum(m['edge_pixels'] for _, _, m in measured),
        frames_with_interior_differences=['%s/%s: %d pixels, max %d' % (case, frame, m['differing_interior_pixels'],
                                                                         m['interior_max'])
                                          for case, frame, m in measured if m['differing_interior_pixels']],
        frames_with_alpha_differences=['%s/%s: %d pixels, max %d' % (case, frame, m['alpha_differing_pixels'],
                                                                      m['alpha_max'])
                                       for case, frame, m in measured if m['alpha_differing_pixels']],
        frames_over_frame_cap=['%s/%s: %.4f' % (case, frame, m['differing_fraction']) for case, frame, m in measured
                               if m['over_frame_cap']],
        max_differing_fraction=max(m['differing_fraction'] for _, _, m in measured),
        rule_failures=['%s/%s: %s' % (case, frame, m['rule_verdict']) for case, frame, m in measured
                       if m['rule_verdict'] is not None],
        edge_max_by_frame={'%s/%s' % (case, frame): m['edge_max'] for case, frame, m in measured})
    return summary


def measure(protocol_path, roots, repository=ROOT):
    """Measure every protocol frame; ``roots`` maps upstream, candidate and the optional controls to capture roots."""
    body = Path(protocol_path).read_bytes()
    protocol = json.loads(body)
    repository = Path(repository)
    results = {'schema': 1, 'protocol': {'file': str(protocol_path), 'sha256': sha_bytes(body)},
               'criterion': {'module': 'tools/smooth_line_parity.py',
                             'sha256': sha_bytes((repository / 'tools/smooth_line_parity.py').read_bytes()),
                             'EDGE_TOLERANCE': EDGE_TOLERANCE, 'MAX_DIFFERING_FRACTION': MAX_DIFFERING_FRACTION},
               'measurement_sha256': sha_bytes(Path(__file__).read_bytes()),
               'roots': {key: str(value) for key, value in roots.items() if value is not None},
               'comparisons': {key: {'image': image, 'reference': reference}
                               for key, (image, reference) in COMPARISONS.items()},
               'fixtures': {}, 'findings': [], 'interior_findings': [], 'unadmitted_frames': []}
    for spec in protocol['fixtures']:
        fixture, bound = spec['name'], set(spec['bound_cases'])
        unavailable, clipped = spec.get('nvidia_unavailable', {}), spec.get('clipped_geometry', {})
        cases = {}
        for case in spec['cases']:
            frames = {}
            for frame in spec['frames'][case]:
                sources = {side: load_driver_frame(roots[side], fixture, case, frame)
                           for side in ('upstream', 'candidate')}
                if case in unavailable:
                    sources['nvidia'] = (None, {'status': 'not applicable', 'reason': unavailable[case]})
                else:
                    sources['nvidia'] = load_nvidia_frame(protocol, fixture, case, frame, repository)
                entry = {'sources': {side: info for side, (_array_, info) in sources.items()}, 'comparisons': {}}
                for key, (image_side, reference_side) in COMPARISONS.items():
                    (image, image_info), (reference, reference_info) = sources[image_side], sources[reference_side]
                    if image is None or reference is None:
                        entry['comparisons'][key] = {'measured': False, 'reason': '%s %s, %s %s' % (
                            image_side, image_info['status'], reference_side, reference_info['status'])}
                        continue
                    metrics = frame_metrics(image, reference)
                    metrics['measured'] = True
                    metrics['admitted'] = image_info['status'] == reference_info['status'] == 'admitted'
                    if metrics['comparable']:
                        metrics['rule_verdict'] = rule_verdict(fixture, case, image, reference)
                    entry['comparisons'][key] = metrics
                    where = {'comparison': key, 'fixture': fixture, 'case': case, 'frame': frame,
                             'bound_case': case in bound}
                    if not metrics['admitted']:
                        results['unadmitted_frames'].append({**where, 'edge_max': metrics.get('edge_max')})
                    elif metrics['comparable'] and metrics['exceeds_bound']:
                        results['findings'].append({**where, 'edge_max': metrics['edge_max'],
                                                    'over_bound_edge_pixels': metrics['over_bound_edge_pixels'],
                                                    'edge_max_at': metrics.get('edge_max_at'),
                                                    'over_bound_box': metrics.get('over_bound_box')})
                    if metrics['admitted'] and metrics['comparable'] and metrics['differing_interior_pixels']:
                        results['interior_findings'].append({**where, 'pixels': metrics['differing_interior_pixels'],
                                                             'interior_max': metrics['interior_max'],
                                                             'interior_max_at': metrics.get('interior_max_at')})
                frames[frame] = entry
            exposure = {side: (None if driver_shaders(roots[side], fixture, case) is None else
                               bool(NOPERSPECTIVE.search(driver_shaders(roots[side], fixture, case))))
                        for side in ('upstream', 'candidate')}
            cases[case] = {'bound_case': case in bound, 'frames': frames,
                           'clipping': {'noperspective_in_expanded_shaders': exposure,
                                        'clipped_geometry': clipped.get(case)}}
        results['fixtures'][fixture] = {
            'cases': cases,
            'summary': {key: {'bound': _summary(cases, key, True), 'context': _summary(cases, key, False)}
                        for key in COMPARISONS}}
    for finding in results['findings'] + results['interior_findings']:
        finding['clipping'] = results['fixtures'][finding['fixture']]['cases'][finding['case']]['clipping']
    results['overall'] = {key: {'bound_edge_max': max((fixture['summary'][key]['bound'].get('edge_max', 0)
                                                       for fixture in results['fixtures'].values()), default=0),
                                'bound_frames_over_bound': sum(len(fixture['summary'][key]['bound'].get(
                                    'frames_over_bound', [])) for fixture in results['fixtures'].values()),
                                'context_frames_over_bound': sum(len(fixture['summary'][key]['context'].get(
                                    'frames_over_bound', [])) for fixture in results['fixtures'].values())}
                          for key in COMPARISONS}
    controls = {}
    for label, side in (('repeat_upstream', 'upstream'), ('repeat_candidate', 'candidate')):
        if roots.get(label) is None:
            continue
        rows = {}
        for spec in protocol['fixtures']:
            if not (Path(roots[label]) / spec['name']).is_dir():
                continue
            for case in spec['cases']:
                for frame in spec['frames'][case]:
                    first, first_info = load_driver_frame(roots[side], spec['name'], case, frame)
                    again, again_info = load_driver_frame(roots[label], spec['name'], case, frame)
                    rows['%s/%s/%s' % (spec['name'], case, frame)] = (
                        exact_metrics(again, first) if first is not None and again is not None
                        else {'equal': False, 'reason': '%s / %s' % (first_info['status'], again_info['status'])})
        controls[label] = {'frames': rows, 'all_equal': all(row['equal'] for row in rows.values())}
    if roots.get('tool_candidate') is not None:
        rows = {}
        for spec in protocol['fixtures']:
            if not (Path(roots['tool_candidate']) / spec['name'] / 'manifest.json').is_file():
                continue
            for case in spec['cases']:
                for frame in spec['frames'][case]:
                    tool, tool_info = load_tool_frame(roots['tool_candidate'], spec['name'], case, frame)
                    driver, driver_info = load_driver_frame(roots['candidate'], spec['name'], case, frame)
                    rows['%s/%s/%s' % (spec['name'], case, frame)] = (
                        exact_metrics(tool, driver) if tool is not None and driver is not None
                        else {'equal': False, 'reason': '%s / %s' % (tool_info['status'], driver_info['status'])})
        controls['tool_candidate'] = {'frames': rows, 'all_equal': all(row['equal'] for row in rows.values())}
    results['controls'] = controls
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--repeat-upstream', type=Path)
    parser.add_argument('--repeat-candidate', type=Path)
    parser.add_argument('--tool-candidate', type=Path)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = measure(args.protocol, {'upstream': args.upstream, 'candidate': args.candidate,
                                      'repeat_upstream': args.repeat_upstream,
                                      'repeat_candidate': args.repeat_candidate,
                                      'tool_candidate': args.tool_candidate}, args.repository)
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(results, indent=2) + '\n')
    for name, fixture in results['fixtures'].items():
        for key in COMPARISONS:
            bound = fixture['summary'][key]['bound']
            print('%-24s %s bound: frames %d/%d, edge max %s (%s), over %d: %s' % (
                name, key, bound['frames_measured'], bound['frames'], bound.get('edge_max'),
                bound.get('edge_max_where'), EDGE_TOLERANCE, bound.get('frames_over_bound')))
    print('findings over %d:' % EDGE_TOLERANCE, len(results['findings']), '; interior differences:',
          len(results['interior_findings']), '; controls:',
          {key: value['all_equal'] for key, value in results['controls'].items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
