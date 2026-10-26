# SPDX-License-Identifier: AGPL-3.0-only
"""Finite capture contract controls; synthetic payloads admit no artifact."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import struct

import pytest

from tools.no_opengl import functional as f


def float32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def image(size, viewport, left, right, upper, lower, solid=None):
    # Literal intersection counts are independent of the decoder's coordinate
    # calculation:125+6 columns/9+60 rows, then145+12 columns/16+81 rows.
    blue, yellow, red, green = ([0, 0, 255, 192], [255, 255, 0, 255],
                                [255, 0, 0, 64], [0, 255, 0, 128])
    byte_runs = ([[viewport[2]*viewport[3], solid]] if solid is not None else
                 [[count, color] for rows, colors in ((upper, (blue, yellow)), (lower, (red, green)))
                  for _ in range(rows) for count, color in zip((left, right), colors)])
    pixels = b''.join(bytes(color)*count for count, color in byte_runs)
    runs = [[count, [float32(channel/255) for channel in color]] for count, color in byte_runs]
    error = max(abs(actual-channel/255)
                for (_, values), (_, color) in zip(runs, byte_runs)
                for actual, channel in zip(values, color))
    checksum = hashlib.sha256(pixels).hexdigest()
    return dict(target_size=list(size), viewport=list(viewport),
                shape=[viewport[3], viewport[2], 4], byte_dtype='uint8', float_dtype='float32',
                rgba_sha256=checksum, float_rgba_sha256=checksum,
                float_runs=runs, float_max_abs_error=error)


@pytest.fixture
def payload():
    before = dict(pending_draws=1, dawn_queue_submits=10, finish_calls=4,
                  completion_waits=3, application_presents=2)
    recovery = image((301, 177), (5, 7, 157, 97), 0, 0, 0, 0, [0, 255, 255, 96])
    recovery['after'] = dict(pending_draws=0, dawn_queue_submits=11, finish_calls=6,
                             completion_waits=4, application_presents=2)
    return dict(schema=1, contract=f.CAPTURE_CONTRACT, status='PASS', samples=0,
                scope=f.CAPTURE_SCOPE,
                setup=dict(canvas_id=1, sample_count=1, framebuffer_id=0,
                           width=257, height=129, rgba_bits=[8, 8, 8, 8]),
                cleanup_errors=0, tcl_patchlevel='8.6.14', tk_patchlevel='8.6.14',
                ordinary=image((257, 129), (3, 4, 131, 69), 125, 6, 9, 60),
                mutation=image((301, 177), (5, 7, 157, 97), 145, 12, 16, 81),
                failure=dict(type='ValueError', message='viewport should be a 1D four-element array',
                             traceback='Traceback (most recent call last):\n  synthetic capture input\nValueError: viewport should be a 1D four-element array\n',
                             attempted_viewport=[0, 0, 1],
                             before=before, after=deepcopy(before)), recovery=recovery)


def worker(payload, source=False):
    workflow = dict(id=f.CAPTURE_WORKFLOW)
    envelope = f.capture({f.RESULT_NAME: payload}, workflow, source)
    return dict(pid=os.getpid(), workflow=workflow, source_mode=source,
                status='PASS_SCENARIO', functional_result=envelope)


def test_capture_contract_binds_each_actual_branch(payload):
    child = worker(payload)
    verdict = f.validate_bound_result(child, installed=True)
    assert verdict['branch_ids'] == sorted(f.CAPTURE_BRANCHES.values())
    assert verdict['qualified'] is False
    for kind, branch in f.CAPTURE_BRANCHES.items():
        binding = f.criterion_binding(f.CAPTURE_FEATURE, kind)
        assert f.validate_for_criterion(child, binding)['branch_ids'] == [branch]


def test_capture_workflow_requires_export_and_installed_identity(payload):
    with pytest.raises(ValueError, match='export is missing'):
        f.capture({}, dict(id=f.CAPTURE_WORKFLOW), False)
    with pytest.raises(ValueError, match='source result cannot qualify'):
        f.validate_bound_result(worker(payload, source=True), installed=True)
    with pytest.raises(ValueError, match='another child'):
        child = worker(payload)
        child['pid'] += 1
        f.validate_bound_result(child, installed=True)


@pytest.mark.parametrize('target', [f.CAPTURE_WORKFLOW, f.WORKFLOW, 'unrelated-workflow'])
def test_resealed_wrong_workflow_contract_is_rejected(payload, target):
    child = worker(payload)
    wrong = json.loads((Path(__file__).parent/'data/tk-functional-result.json').read_bytes()) if target == f.CAPTURE_WORKFLOW else payload
    identity = dict(id=target)
    child['workflow'] = identity
    child['functional_result'].update(workflow=identity, payload=wrong, payload_sha256=f.digest(wrong))
    with pytest.raises(ValueError):
        f.capture({f.RESULT_NAME: wrong}, identity, False)
    with pytest.raises(ValueError):
        f.validate_bound_result(child, installed=True)


@pytest.mark.parametrize('change', [
    lambda p: p.update(samples=4),
    lambda p: p.update(cleanup_errors=1),
    lambda p: p.update(schema=True),
    lambda p: p.update(scope='all readback formats'),
    lambda p: p['setup'].update(canvas_id=0),
    lambda p: p['setup'].update(sample_count=4),
    lambda p: p['setup'].update(rgba_bits=[8, 8, 8, 0]),
    lambda p: p.update(contract=f.CONTRACT),
    lambda p: p['ordinary'].update(shape=[69, 131, 3]),
    lambda p: p['ordinary'].update(viewport=[3, 5, 131, 69]),
    lambda p: p['ordinary'].update(byte_dtype='float32'),
    lambda p: p['ordinary'].update(float_dtype='float64'),
    lambda p: p['ordinary'].update(rgba_sha256='0'*64),
    lambda p: p['ordinary'].update(float_rgba_sha256='0'*64),
    lambda p: p['ordinary'].update(float_runs=[]),
    lambda p: p['ordinary']['float_runs'][0].__setitem__(0, True),
    lambda p: p['ordinary']['float_runs'][0].__setitem__(0, 10**9),
    lambda p: p['ordinary']['float_runs'].pop(),
    lambda p: p['ordinary']['float_runs'].reverse(),
    lambda p: p['ordinary']['float_runs'][0][1].__setitem__(3, 1.0),
    lambda p: p['ordinary']['float_runs'][0][1].__setitem__(0, float('nan')),
    lambda p: p['ordinary']['float_runs'][0][1].__setitem__(0, float('inf')),
    lambda p: p['ordinary']['float_runs'][0][1].__setitem__(0, 0.1),
    lambda p: p['ordinary']['float_runs'][0][1].__setitem__(0, float32(5e-7)),
    lambda p: p['ordinary'].update(float_max_abs_error=0.0),
    lambda p: p['failure'].update(message='some other failure'),
    lambda p: p['failure'].update(traceback=''),
    lambda p: p['failure'].update(attempted_viewport=[0, 0, 1, 1]),
    lambda p: p['failure']['before'].update(pending_draws=0),
    lambda p: p['failure']['after'].update(finish_calls=5),
    lambda p: p['recovery']['after'].update(pending_draws=1),
    lambda p: p['recovery']['after'].update(dawn_queue_submits=10),
    lambda p: p['recovery']['after'].update(completion_waits=3),
    lambda p: p['recovery']['after'].update(application_presents=3),
    lambda p: p['recovery'].pop('after'),
])
def test_capture_decoder_rejects_semantic_corruption(payload, change):
    change(payload)
    with pytest.raises(ValueError):
        f.validate_capture_result(payload)


def test_prepared_capture_candidate_maps_four_modes_on_both_profiles():
    from tools import compatibility_coverage as coverage
    from tools import compatibility_execution as execution
    from tools import compatibility_qualification as selection
    root = Path(__file__).resolve().parents[2]
    base = root/'compat/candidates/tk-capture-1'
    mapped = json.loads((base/'execution.json').read_bytes())
    coverage_state = coverage.validate_coverage(json.loads((base/'coverage.json').read_bytes()))
    execution.validate_execution(mapped)
    selection.validate_selection(json.loads((base/'admission-selection.json').read_bytes()))
    assert coverage_state['original_required_pairs_retained'] == 142
    assert coverage_state['originals_discharged'] == 0
    assert len(mapped['mappings']) == 8
    for mapping in mapped['mappings']:
        kind = mapping['criterion'].rsplit('.', 1)[1]
        assert mapping['functional_result'] == dict(
            schema=1, contract=f.CAPTURE_CONTRACT, branch_ids=[f.CAPTURE_BRANCHES[kind]])


@pytest.mark.parametrize('fault', ['unknown-contract', 'old-contract', 'wrong-branch', 'missing-binding'])
def test_resealed_capture_mapping_rejects_wrong_semantics(fault):
    from tools import compatibility_execution as execution
    root = Path(__file__).resolve().parents[2]
    record = json.loads((root/'compat/candidates/tk-capture-1/execution.json').read_bytes())
    binding = record['mappings'][0]['functional_result']
    if fault == 'unknown-contract':
        binding['contract'] = 'tk-capture-2'
    elif fault == 'old-contract':
        binding['contract'] = f.CONTRACT
    elif fault == 'wrong-branch':
        binding['branch_ids'] = ['ordinary.state']
    else:
        record['mappings'][0].pop('functional_result')
    execution.seal(record)
    with pytest.raises(ValueError):
        execution.validate_execution(record)
