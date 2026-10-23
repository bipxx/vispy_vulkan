# SPDX-License-Identifier: AGPL-3.0-only
"""Exact saved-frame diagnostics for the fixed white-fragment training union.

No file access, device creation, coordinate adjustment or renderer admission.
Callers remain responsible for admitting source, process and artifact identities.
"""
from itertools import zip_longest

import numpy as np

try:
    from .smooth_line_mechanism import training_probes
    from .smooth_line_corner_training import corner_probes
except ImportError:
    from smooth_line_mechanism import training_probes
    from smooth_line_corner_training import corner_probes


def canonical_rows():
    """Return original 7040 followed by the separately admitted corner 4096."""
    return tuple(dict(study=study, index=index, identity=probe.identity,
                      start_units=list(probe.start_units), end_units=list(probe.end_units),
                      width_units=probe.width_units)
                 for study, probes in (('original', training_probes()), ('corner', corner_probes()))
                 for index, probe in enumerate(probes))


def validate_rows(rows):
    """Reject role/order/geometry changes before consuming either frame stream."""
    expected = canonical_rows()
    if type(rows) not in (list, tuple) or len(rows) != len(expected):
        raise ValueError('Complete canonical training union required')
    for row, reference in zip(rows, expected):
        # Python equality alone admits bool as an integer and float as an index.
        if (type(row) is not dict or row.keys() != reference.keys() or
                type(row['index']) is not int or type(row['width_units']) is not int or
                any(type(row[name]) is not list or len(row[name]) != 2 or
                    any(type(value) is not int for value in row[name])
                    for name in ('start_units', 'end_units')) or row != reference):
            raise ValueError('Canonical training role, order and exact geometry required')
    return expected


def compare_frame(actual, reference):
    """Measure full RGBA bytes and generated masks separately, without tolerance."""
    observations = []
    for frame in (actual, reference):
        if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.shape != (64, 64, 4):
            raise ValueError('64x64 RGBA8 frame required')
        rgb = frame[:, :, :3]
        generated = np.all(rgb == 255, axis=2)
        background = np.all(rgb == 0, axis=2)
        if np.any(~(generated | background)) or np.any(frame[:, :, 3][background] != 0):
            raise ValueError('Constant-white fragments over transparent clear required')
        observations.append((generated, int(np.count_nonzero(generated)),
                             int(np.count_nonzero((frame[:, :, 3] > 0) & (frame[:, :, 3] < 255)))))
    delta = np.abs(actual.astype(np.int16) - reference.astype(np.int16))
    return dict(differing_pixels=int(np.count_nonzero(np.any(delta, axis=2))),
                generated_mask_differences=int(np.count_nonzero(observations[0][0] != observations[1][0])),
                alpha_differences=int(np.count_nonzero(delta[:, :, 3])),
                maximum_channel_error=int(delta.max()),
                actual_generated_pixels=observations[0][1], reference_generated_pixels=observations[1][1],
                actual_fractional_alpha_pixels=observations[0][2], reference_fractional_alpha_pixels=observations[1][2])


def compare_training_streams(rows, actual_frames, reference_frames):
    """Compare each canonical row once; truncated/extra streams fail closed."""
    rows = validate_rows(rows)
    result = dict(rows_checked=0, differing_rows=0, differing_pixels=0,
                  generated_mask_differences=0, alpha_differences=0, maximum_channel_error=0,
                  actual_fractional_alpha_pixels=0, reference_fractional_alpha_pixels=0,
                  invalid_rows=[], groups={}, exact_nontrivial_training_match=False,
                  renderer_qualified=False, portable_generated_fallback_implemented=False)
    missing = object()
    for position, (row, actual, reference) in enumerate(zip_longest(rows, actual_frames, reference_frames, fillvalue=missing)):
        if any(value is missing for value in (row, actual, reference)):
            raise ValueError('Exactly one frame per canonical training row required')
        metrics = compare_frame(actual, reference)
        group_name = 'corner' if row['study'] == 'corner' else ('original-axial' if position < 3072 else 'original-oblique')
        group = result['groups'].setdefault(group_name, dict(rows=0, differing_rows=0, differing_pixels=0,
                                                           generated_mask_differences=0, alpha_differences=0,
                                                           maximum_channel_error=0))
        for counts in (result, group):
            counts['differing_rows'] += int(metrics['differing_pixels'] > 0)
            for key in ('differing_pixels', 'generated_mask_differences', 'alpha_differences'):
                counts[key] += metrics[key]
            counts['maximum_channel_error'] = max(counts['maximum_channel_error'], metrics['maximum_channel_error'])
        reasons = [side + '-' + reason for side in ('actual', 'reference')
                   for reason, invalid in (('empty', metrics[side + '_generated_pixels'] < 20),
                                           ('aliased', metrics[side + '_fractional_alpha_pixels'] == 0)) if invalid]
        if reasons:
            result['invalid_rows'].append(dict(position=position, identity=row['identity'], reasons=reasons))
        for side in ('actual', 'reference'):
            result[side + '_fractional_alpha_pixels'] += metrics[side + '_fractional_alpha_pixels']
        result['rows_checked'] += 1
        group['rows'] += 1
    result['exact_nontrivial_training_match'] = result['differing_rows'] == 0 and not result['invalid_rows']
    return result
