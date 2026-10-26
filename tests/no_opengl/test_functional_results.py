# SPDX-License-Identifier: AGPL-3.0-only
"""CPU-only functional transport and semantic controls; not graphics evidence."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools.no_opengl.functional import (CONTRACT, RESULT_NAME, WORKFLOW, bound_payload,
                                        TK_FEATURES, capture, criterion_binding, digest,
                                        validate_bound_result, validate_for_criterion, validate_tk_result)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tests/no_opengl/data/tk-functional-result.json'


def example_result():
    return json.loads(FIXTURE.read_bytes())


def workflow():
    return {'id': WORKFLOW, 'scenario': 'script', 'binding': None,
            'script_sha256': 'a' * 64, 'arguments': [], 'features': ['tk.gl.flush']}


def worker():
    identity = workflow()
    return {'pid': os.getpid(), 'workflow': identity, 'source_mode': False,
            'status': 'PASS_SCENARIO', 'functional_result': capture({RESULT_NAME: example_result()}, identity, False)}


def test_closed_result_has_all_exact_variants_without_claiming_qualification():
    result = validate_tk_result(example_result())
    assert len(result['branch_ids']) == 8 and not result['qualified']
    assert validate_bound_result(worker(), installed=True) == result


ORACLE_FAULTS = [
    ('missing-finish', 'closed ordinary submission'),
    ('finish-chain', 'finish snapshot does not follow flush'),
    ('finish-no-call', 'finish did not complete'),
    ('finish-no-wait', 'finish did not complete'),
    ('finish-present', 'finish presented'),
    ('finish-submit-regressed', 'counters regressed'),
    ('finish-retirement-regressed', 'counters regressed'),
    ('second-corrupted', 'untouched second target'),
    ('second-bool', 'untouched second target'),
    ('missing-retirement', 'closed resource recovery'),
    ('closed-survivor', 'live survivor or Python references'),
    ('lost-references', 'live survivor or Python references'),
    ('bool-references', 'live survivor or Python references'),
    ('no-canvas', 'live survivor or Python references'),
    ('missing-gauge', 'closed retirement gauges'),
    ('negative-gauge', 'invalid retirement gauge'),
    ('bool-gauge', 'invalid retirement gauge'),
] + [('finish-pending-' + key, 'finish retained work') for key in
     ('pending_tickets', 'queued_frames', 'pending_draws')]
ORACLE_FAULTS += [('vacuous-' + key, 'resource retirement is vacuous') for key in
                 ('live_cpu_buffer_bytes', 'live_buffer_bytes', 'resource_texture_bytes')]
ORACLE_FAULTS += [('leaked-' + key, 'baseline before close') for key in
                 ('live_cpu_buffer_bytes', 'live_buffer_bytes', 'pending_tickets',
                  'queued_frames', 'pending_draws', 'vertex_input_current_entries',
                  'vertex_input_current_bytes', 'vertex_input_cache_entries',
                  'vertex_input_cache_bytes', 'resource_texture_bytes')]


def assert_oracle_rejected(original, fault, reason):
    """Exercise capture and the actual bound decoder, including resealed negatives."""
    identity = workflow()
    current = dict(pid=os.getpid(), workflow=identity, source_mode=True, status='PASS_SCENARIO',
                   functional_result=capture({RESULT_NAME: original}, identity, True))
    assert validate_bound_result(current)['status'] == 'PASS_FUNCTIONAL_RESULT'
    payload = current['functional_result']['payload']
    item = payload['ordinary_state']['submissions'][0]
    retirement = payload['resource_failure_recovery']['recovery']['retirement']
    if fault == 'missing-finish': del item['finish_before']
    elif fault == 'finish-chain': item['finish_before']['completion_waits'] += 1
    elif fault == 'finish-no-call': item['finish_after']['finish_calls'] = item['finish_before']['finish_calls']
    elif fault == 'finish-no-wait': item['finish_after']['completion_waits'] = item['finish_before']['completion_waits']
    elif fault == 'finish-present': item['finish_after']['application_presents'] += 1
    elif fault == 'finish-submit-regressed': item['finish_after']['dawn_queue_submits'] = 0
    elif fault == 'finish-retirement-regressed':
        item['finish_before']['retired_tickets'] = item['finish_after']['retired_tickets'] + 1
    elif fault.startswith('finish-pending-'): item['finish_after'][fault.removeprefix('finish-pending-')] = 1
    elif fault == 'second-corrupted': item['untouched_second_rgba'] = [255, 255, 0, 255]
    elif fault == 'second-bool': item['untouched_second_rgba'][0] = False
    elif fault == 'missing-retirement': del payload['resource_failure_recovery']['recovery']['retirement']
    elif fault == 'closed-survivor': retirement['survivor_alive'] = False
    elif fault == 'lost-references': retirement['python_references_alive'] = 0
    elif fault == 'bool-references': retirement['python_references_alive'] = True
    elif fault == 'no-canvas': retirement['canvas_bytes'] = 0
    elif fault == 'missing-gauge': del retirement['after_delete']['resource_texture_bytes']
    elif fault == 'negative-gauge': retirement['after_delete']['resource_texture_bytes'] = -1
    elif fault == 'bool-gauge': retirement['after_delete']['resource_texture_bytes'] = False
    elif fault.startswith('vacuous-'):
        key = fault.removeprefix('vacuous-'); retirement['before_delete'][key] = retirement['baseline'][key]
    elif fault.startswith('leaked-'): retirement['after_delete'][fault.removeprefix('leaked-')] += 1
    else: raise AssertionError(fault)
    current['functional_result']['payload_sha256'] = digest(payload)
    with pytest.raises(ValueError, match=reason):
        validate_bound_result(current)


@pytest.mark.parametrize('fault,reason', ORACLE_FAULTS)
def test_distinguishing_observations_are_validated_after_transport(fault, reason):
    assert_oracle_rejected(example_result(), fault, reason)


@pytest.mark.parametrize('fault,reason', [
    ('missing-branch', 'missing submission branch'),
    ('duplicate-branch', 'duplicated or omitted'),
    ('wrong-branch-id', 'wrong submission branch ID'),
    ('early-not-executed', 'early progress variant'),
    ('early-submission', 'unexpected submission'),
    ('blocked-submission', 'unexpected submission'),
    ('blocked-wait', 'waited or presented'),
    ('blocked-present', 'waited or presented'),
    ('lost-work', 'lost pending work'),
    ('not-retired', 'retirement was not observed'),
    ('missing-retry', 'missing/duplicate explicit retry'),
    ('duplicate-retry', 'missing/duplicate explicit retry'),
    ('retry-retained-work', 'retry retained pending work'),
    ('wrong-pixel', 'readback/display color'),
    ('bool-pixel', 'readback/display color'),
    ('slot-not-restored', 'frame slots'),
    ('wrong-error', 'wrong expected exception'),
    ('missing-traceback', 'original exception traceback'),
    ('duplicate-progress', 'duplicated or omitted'),
    ('repeat-error', 'delivery/cleanup differs'),
    ('polling-not-stopped', 'recovery/polling/host'),
    ('cleanup-failed', 'submission cleanup failed'),
    ('resource-leak', 'return to baseline'),
    ('resource-cleanup', 'resource cleanup failed'),
    ('resource-no-recovery', 'resource recovery differs'),
    ('ordinary-no-submit', 'ordinary flush did not submit'),
    ('ordinary-wait', 'ordinary flush waited'),
    ('ordinary-duplicate', 'ordinary routes duplicated'),
    ('unknown-field', 'closed Tk composite'),
    ('bool-counter', 'nonnegative integer'),
    ('wrong-version', 'unknown Tk contract/version'),
])
def test_tk_branch_results_reject_missing_or_changed_behavior(fault, reason):
    payload = example_result()
    branches = payload['submission_failure_recovery']
    item = branches[0]
    progress = payload['native_progress_failure_recovery']
    resource = payload['resource_failure_recovery']
    if fault == 'missing-branch': branches.pop()
    elif fault == 'duplicate-branch': branches[1] = deepcopy(branches[0])
    elif fault == 'wrong-branch-id': item['branch_id'] = 'submission.raw.immediate'
    elif fault == 'early-not-executed': branches[1]['early_progress'] = None
    elif fault == 'early-submission': branches[1]['early_progress']['dawn_queue_submits'] += 1
    elif fault == 'blocked-submission': item['blocked']['dawn_queue_submits'] += 1
    elif fault == 'blocked-wait': item['blocked']['completion_waits'] += 1
    elif fault == 'blocked-present': item['blocked']['application_presents'] += 1
    elif fault == 'lost-work': item['blocked']['pending_draws'] = 0
    elif fault == 'not-retired': item['retired']['pending_tickets'] = 1
    elif fault == 'missing-retry': item['resumed']['dawn_queue_submits'] -= 1
    elif fault == 'duplicate-retry': item['resumed']['dawn_queue_submits'] += 1
    elif fault == 'retry-retained-work': item['resumed']['pending_draws'] = 1
    elif fault == 'wrong-pixel': item['presented_rgb'] = [0, 128, 0]
    elif fault == 'bool-pixel': item['readback'][0] = False
    elif fault == 'slot-not-restored': item['restored_frame_slots'] += 1
    elif fault == 'wrong-error': item['expected_error']['message'] = 'unrelated error'
    elif fault == 'missing-traceback': item['expected_error']['traceback'] = 'RuntimeError: capacity'
    elif fault == 'duplicate-progress': progress[1] = deepcopy(progress[0])
    elif fault == 'repeat-error': progress[0]['deliveries'] = 2
    elif fault == 'polling-not-stopped': progress[0]['polling_stopped'] = False
    elif fault == 'cleanup-failed': item['cleanup_errors'] = 1
    elif fault == 'resource-leak': resource['after_failure']['live_cpu_buffer_bytes'] += 1
    elif fault == 'resource-cleanup': resource['cleanup']['secondary_errors'] = 1
    elif fault == 'resource-no-recovery': resource['recovery']['device_recovered'] = False
    elif fault == 'ordinary-no-submit': payload['ordinary_state']['submissions'][0]['after']['dawn_queue_submits'] -= 1
    elif fault == 'ordinary-wait': payload['ordinary_state']['submissions'][0]['after']['finish_calls'] += 1
    elif fault == 'ordinary-duplicate': payload['ordinary_state']['submissions'][1] = deepcopy(payload['ordinary_state']['submissions'][0])
    elif fault == 'unknown-field': payload['waive_missing_branch'] = True
    elif fault == 'bool-counter': item['before']['finish_calls'] = True
    elif fault == 'wrong-version': payload['schema'] = True
    else: raise AssertionError(fault)
    # A freshly recomputed hash must not turn a semantic failure into a pass.
    current = worker()
    current['functional_result']['payload'] = payload
    current['functional_result']['payload_sha256'] = digest(payload)
    with pytest.raises(ValueError, match=reason):
        validate_bound_result(current, installed=True)


@pytest.mark.parametrize('fault,reason', [
    ('pid', 'another child'), ('workflow', 'another workflow'),
    ('source', 'source result cannot qualify'), ('failed', 'scenario or cleanup failed'),
    ('cleanup', 'scenario or cleanup failed'), ('payload-hash', 'identity changed'),
    ('unknown', 'envelope fields differ'), ('missing', 'envelope fields differ'),
])
def test_worker_envelope_rejects_substitution(fault, reason):
    current = worker()
    if fault == 'pid': current['functional_result']['producer_pid'] += 1
    elif fault == 'workflow': current['functional_result']['workflow']['arguments'] = ['other-branch']
    elif fault == 'source':
        current['source_mode'] = current['functional_result']['source_mode'] = True
    elif fault == 'failed': current['status'] = 'FAILED_SCENARIO'
    elif fault == 'cleanup': current['cleanup_error'] = 'failed cleanup'
    elif fault == 'payload-hash': current['functional_result']['payload']['status'] = 'FAIL'
    elif fault == 'unknown': current['functional_result']['external_result_file'] = 'other.json'
    elif fault == 'missing': del current['functional_result']
    with pytest.raises(ValueError, match=reason):
        validate_bound_result(current, installed=True)


def test_capture_freezes_the_returned_object_and_never_parses_stdout():
    original = {'status': 'PASS', 'values': [1]}
    captured = capture({RESULT_NAME: original}, dict(workflow(), id='generic'), False)
    original['values'].append(2)
    assert captured['payload']['values'] == [1]
    assert captured['producer_pid'] == os.getpid()
    assert captured['payload_sha256'] == digest(captured['payload'])


def test_every_declared_tk_criterion_joins_its_required_executed_branches():
    current = worker()
    for feature in TK_FEATURES:
        for kind in ('ordinary', 'mutation', 'failure', 'recovery'):
            binding = criterion_binding(feature, kind)
            result = validate_for_criterion(current, binding)
            assert result['branch_ids'] == binding['branch_ids'] and not result['qualified']
    assert criterion_binding('tk.gl.flush', 'failure')['branch_ids'] == [
        'submission.raw.immediate', 'submission.raw.delayed']
    assert criterion_binding('tk.wrappers.submission', 'recovery')['branch_ids'] == [
        'submission.gloo.immediate', 'submission.gloo.delayed']


@pytest.mark.parametrize('fault,reason', [
    ('unexecuted', 'was not executed'), ('duplicate', 'missing or duplicated'),
    ('contract', 'contract/version differs'), ('version', 'contract/version differs'),
    ('field', 'criterion binding fields differ'), ('missing-global-branch', 'missing progress callback order'),
])
def test_criterion_join_cannot_filter_out_failed_or_unknown_work(fault, reason):
    current = worker()
    binding = criterion_binding('tk.gl.flush', 'failure')
    if fault == 'unexecuted': binding['branch_ids'] = ['ordinary.unexecuted']
    elif fault == 'duplicate': binding['branch_ids'] *= 2
    elif fault == 'contract': binding['contract'] = 'another-workflow'
    elif fault == 'version': binding['schema'] = True
    elif fault == 'field': binding['waive_other_branches'] = True
    elif fault == 'missing-global-branch':
        payload = current['functional_result']['payload']
        payload['native_progress_failure_recovery'].pop()
        current['functional_result']['payload_sha256'] = digest(payload)
    with pytest.raises(ValueError, match=reason):
        validate_for_criterion(current, binding)


@pytest.mark.parametrize('value', [None, [], {'bad': float('nan')}, {'bad': object()}, {1: 'non-string key'}])
def test_capture_refuses_non_json_exports(value):
    with pytest.raises((ValueError, TypeError)):
        capture({RESULT_NAME: value}, workflow(), False)


def probe(tmp_path, source, *, required=False):
    script, report = tmp_path / 'scenario.py', tmp_path / 'worker.json'
    script.write_text(source, encoding='utf-8')
    command = [sys.executable, '-I', '-B', str(ROOT / 'tools/no_opengl/probe.py'),
               '--scenario', 'script', '--script', str(script), '--workflow-id',
               WORKFLOW if required else 'functional-cpu-control', '--output', str(report)]
    result = subprocess.run(command, capture_output=True, text=True)
    return result, json.loads(report.read_bytes())


def test_actual_probe_binds_script_namespace_to_its_own_pid(tmp_path):
    result, report = probe(tmp_path, 'import os\nVISPY_FUNCTIONAL_RESULT={"value":42,"actual_pid":os.getpid()}\n'
                           'print(\'{"value":999,"producer_pid":0}\')\n')
    assert result.returncode == 0, report
    payload = bound_payload(report)
    assert payload == {'value': 42, 'actual_pid': report['pid']}
    assert report['functional_result']['producer_pid'] == report['pid']


@pytest.mark.parametrize('source,reason', [
    ('print(\'{"status":"PASS"}\')\n', 'required scenario export is missing'),
    ('VISPY_FUNCTIONAL_RESULT={"status":"PASS"}\nraise SystemExit(0)\n', 'required scenario export is missing'),
    ('VISPY_FUNCTIONAL_RESULT=None\n', 'nonempty JSON object'),
    ('VISPY_FUNCTIONAL_RESULT={"schema":1,"contract":"tk-state-resource-1","status":"PASS"}\n', 'closed Tk composite'),
])
def test_actual_probe_cannot_pass_required_missing_or_malformed_results(tmp_path, source, reason):
    result, report = probe(tmp_path, source, required=True)
    assert result.returncode == 1 and report['status'] == 'FAILED_SCENARIO'
    assert reason in report['error']


def test_good_structured_result_cannot_hide_later_installed_audit_failure(tmp_path):
    script, report, wheel = tmp_path / 'scenario.py', tmp_path / 'worker.json', tmp_path / 'invalid.whl'
    script.write_text('VISPY_FUNCTIONAL_RESULT={"value":42}\n', encoding='utf-8')
    wheel.write_bytes(b'not a wheel archive')
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools/no_opengl/probe.py'),
                             '--scenario', 'script', '--script', str(script), '--wheel', str(wheel),
                             '--output', str(report)], capture_output=True, text=True)
    child = json.loads(report.read_bytes())
    assert result.returncode == 1 and child['status'] == 'FAILED_SCENARIO' and 'BadZipFile' in child['error']
    assert child['functional_result']['payload'] == {'value': 42}
    with pytest.raises(ValueError, match='scenario or cleanup failed'):
        bound_payload(child)


def test_actual_controller_binds_the_complete_worker_result(tmp_path):
    script, report = tmp_path / 'scenario.py', tmp_path / 'report.json'
    script.write_text('VISPY_FUNCTIONAL_RESULT={"value":42}\n', encoding='utf-8')
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/audit_no_opengl.py'), 'run',
                             '--python', sys.executable, '--scenario', 'script', '--script', str(script),
                             '--workflow-id', 'functional-cpu-control', '--gates', 'imports',
                             '--output', str(report)], capture_output=True, text=True)
    controller = json.loads(report.read_bytes())
    path = Path(controller['worker_report'])
    child = json.loads(path.read_bytes())
    assert bound_payload(child) == {'value': 42}
    assert controller['functional_result_sha256'] == digest(child['functional_result'])
    assert controller['worker_report_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    violations = controller['gates']['violations']
    if violations:
        assert all(item['kind'] == 'native_load' for item in violations)
        assert controller['gates']['no_gl_loads'] == 'FAIL' and controller['status'] == 'FAIL' and result.returncode == 1
    else:
        assert controller['status'] == 'PASS_IMPORT_GATE_ONLY' and result.returncode == 0
    # Baseline native-load failure remains a failure; this is transport proof.
