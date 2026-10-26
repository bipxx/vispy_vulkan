# SPDX-License-Identifier: AGPL-3.0-only
"""Capture in-worker JSON results and check the closed Tk branch contract.

This functional join does not run or replace an absence gate or admit an artifact.
"""
from __future__ import annotations

import hashlib
import json
import os

RESULT_NAME = 'VISPY_FUNCTIONAL_RESULT'
CONTRACT = 'tk-state-resource-1'
WORKFLOW = 'tk-state-resource-failures'
COUNTERS = ('dawn_queue_submits', 'finish_calls', 'completion_waits', 'application_presents')
GAUGES = ('pending_tickets', 'queued_frames', 'live_buffer_bytes', 'live_cpu_buffer_bytes',
          'live_texture_bytes', 'canvas_texture_bytes', 'transient_buffer_bytes',
          'line_resource_pool_busy_slots', 'line_resource_pool_bytes')
RETIREMENT_GAUGES = ('live_cpu_buffer_bytes', 'live_buffer_bytes', 'pending_tickets',
                     'queued_frames', 'pending_draws', 'vertex_input_current_entries',
                     'vertex_input_current_bytes', 'vertex_input_cache_entries',
                     'vertex_input_cache_bytes', 'resource_texture_bytes')
TK_FEATURES = {
    'tk.backend.raster', 'tk.application.manual', 'tk.canvas.basic', 'tk.context.current',
    'tk.context.shared', 'tk.canvas.recovery', 'tk.timer.once', 'tk.gl.flush',
    'tk.wrappers.submission', 'tk.wrappers.raster', 'tk.readback.rgba', 'tk.object.delete',
    'tk.buffer.triangle', 'tk.texture.rgba8', 'tk.program.texture',
}


def require(condition, message):
    if not condition:
        raise ValueError('functional result: ' + message)


def canonical(value):
    def json_value(item):
        if type(item) is dict:
            require(all(type(key) is str for key in item), 'JSON object keys must be strings')
            for child in item.values():
                json_value(child)
        elif type(item) is list:
            for child in item:
                json_value(child)
        else:
            require(type(item) in (str, int, float, bool, type(None)), 'non-JSON value in export')
    json_value(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys.split()), 'closed ' + label + ' fields differ')


def text(value):
    return type(value) is str and bool(value.strip())


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def color(value, expected):
    return type(value) is list and all(type(v) is int for v in value) and value == expected


def counters(value, extra=()):
    closed(value, ' '.join((*COUNTERS, *extra)), 'counter snapshot')
    require(all(integer(v) for v in value.values()), 'counter must be a nonnegative integer')


def expected_error(value, kind, message):
    closed(value, 'type message traceback', 'expected error')
    require(value['type'] == kind and text(value['message']) and message in value['message'], 'wrong expected exception')
    require(text(value['traceback']) and value['traceback'].startswith('Traceback (most recent call last):\n')
            and kind + ': ' + value['message'] in value['traceback'], 'missing original exception traceback')


def capture(namespace, workflow, source_mode):
    """Freeze the actual returned namespace; never read stdout or a result file."""
    if namespace is None or RESULT_NAME not in namespace:
        require(workflow.get('id') != WORKFLOW, 'required scenario export is missing')
        return None
    payload = namespace[RESULT_NAME]
    require(type(payload) is dict and bool(payload), 'export must be a nonempty JSON object')
    # Round-trip rejects unsupported values/NaN and detaches subsequent mutation.
    encoded = canonical(payload)
    payload = json.loads(encoded)
    if workflow.get('id') == WORKFLOW or payload.get('contract') == CONTRACT:
        validate_tk_result(payload)
    return {'schema': 1, 'producer_pid': os.getpid(), 'workflow': json.loads(canonical(workflow)),
            'source_mode': source_mode, 'payload': payload, 'payload_sha256': hashlib.sha256(encoded).hexdigest()}


def bound_payload(worker, *, installed=False):
    result = worker.get('functional_result')
    closed(result, 'schema producer_pid workflow source_mode payload payload_sha256', 'worker envelope')
    require(type(result['schema']) is int and result['schema'] == 1, 'unknown envelope version')
    require(integer(worker.get('pid'), 1) and type(result['producer_pid']) is int
            and result['producer_pid'] == worker['pid'], 'result belongs to another child')
    require(type(result['workflow']) is dict and bool(result['workflow'])
            and result['workflow'] == worker.get('workflow'), 'result belongs to another workflow')
    require(type(worker.get('source_mode')) is bool and type(result['source_mode']) is bool
            and result['source_mode'] == worker['source_mode'], 'source/installed mode differs')
    require(not installed or result['source_mode'] is False, 'source result cannot qualify installed behavior')
    require(worker.get('status') == 'PASS_SCENARIO' and not worker.get('error') and not worker.get('cleanup_error'),
            'worker scenario or cleanup failed')
    require(type(result['payload']) is dict and result['payload_sha256'] == digest(result['payload']), 'payload identity changed')
    return result['payload']


def validate_bound_result(worker, *, installed=False):
    payload = bound_payload(worker, installed=installed)
    workflow = worker['workflow']
    if workflow.get('id') == WORKFLOW or payload.get('contract') == CONTRACT:
        return validate_tk_result(payload)
    return {'schema': 1, 'status': 'PASS_FUNCTIONAL_TRANSPORT', 'qualified': False}


def criterion_binding(feature, kind):
    """Finite current proposal mapping, not inferred from a passing result."""
    require(feature in TK_FEATURES and kind in ('ordinary', 'mutation', 'failure', 'recovery'),
            'Tk criterion has no declared branch mapping')
    if kind in ('failure', 'recovery'):
        if feature in ('tk.gl.flush', 'tk.wrappers.submission'):
            route = 'raw' if feature == 'tk.gl.flush' else 'gloo'
            branches = ['submission.' + route + '.' + delay for delay in ('immediate', 'delayed')]
        else:
            branches = ['resource.upload-recovery']
    elif feature in ('tk.gl.flush', 'tk.wrappers.submission', 'tk.context.current') or (
            kind == 'ordinary' and feature in ('tk.backend.raster', 'tk.application.manual', 'tk.canvas.basic')):
        branches = ['ordinary.state']
    else:
        branches = ['resource.upload-recovery']
    return {'schema': 1, 'contract': CONTRACT, 'branch_ids': branches}


def validate_for_criterion(worker, binding, *, installed=True):
    """Consume an independently reviewed execution mapping, never a free file."""
    closed(binding, 'schema contract branch_ids', 'criterion binding')
    verdict = validate_bound_result(worker, installed=installed)
    require(type(binding['schema']) is int and binding['schema'] == verdict['schema']
            and binding['contract'] == verdict.get('contract'), 'criterion contract/version differs')
    branches = binding['branch_ids']
    require(type(branches) is list and branches and all(text(b) for b in branches)
            and len(set(branches)) == len(branches), 'criterion branch IDs are missing or duplicated')
    require(set(branches) <= set(verdict.get('branch_ids', [])), 'criterion branch was not executed')
    return {'status': 'PASS_CRITERION_RESULT', 'branch_ids': list(branches), 'qualified': False}


def validate_tk_result(payload):
    closed(payload, 'schema contract status scope ordinary_state resource_failure_recovery '
           'native_progress_failure_recovery submission_failure_recovery', 'Tk composite')
    require(type(payload['schema']) is int and payload['schema'] == 1 and payload['contract'] == CONTRACT,
            'unknown Tk contract/version')
    require(payload['status'] == 'PASS' and text(payload['scope']), 'composite failed')
    ordinary = payload['ordinary_state']
    closed(ordinary, 'scope submissions status tcl_patchlevel tk_patchlevel', 'ordinary state')
    require(ordinary['status'] == 'PASS' and all(text(ordinary[k]) for k in ('scope', 'tcl_patchlevel', 'tk_patchlevel')),
            'ordinary state failed or lacks toolkit identity')
    submits = ordinary['submissions']
    require(type(submits) is list and len(submits) == 2, 'missing ordinary submission route')
    ordinary_routes = []
    colors = {'gloo.flush': [0, 128, 0, 255], 'glFlush': [0, 0, 255, 255]}
    for item in submits:
        closed(item, 'route before after finish_before finish_after readback untouched_second_rgba', 'ordinary submission')
        require(type(item['route']) is str and item['route'] in colors, 'unknown ordinary submission route')
        ordinary_routes.append(item['route'])
        counters(item['before']); counters(item['after'])
        require(item['after']['dawn_queue_submits'] > item['before']['dawn_queue_submits'], 'ordinary flush did not submit')
        require(all(item['before'][k] == item['after'][k] for k in COUNTERS[1:]), 'ordinary flush waited or presented')
        first, last = item['finish_before'], item['finish_after']
        for snapshot in (first, last):
            counters(snapshot, ('pending_tickets', 'queued_frames', 'pending_draws', 'retired_tickets'))
        require(all(first[k] == item['after'][k] for k in COUNTERS), 'finish snapshot does not follow flush')
        require(last['finish_calls'] == first['finish_calls'] + 1
                and last['completion_waits'] > first['completion_waits'], 'finish did not complete before readback')
        require(last['application_presents'] == first['application_presents'], 'finish presented')
        require(last['dawn_queue_submits'] >= first['dawn_queue_submits']
                and last['retired_tickets'] >= first['retired_tickets']
                and all(last[k] == 0 for k in ('pending_tickets', 'queued_frames', 'pending_draws')),
                'finish retained work or counters regressed')
        require(color(item['readback'], colors[item['route']]), 'ordinary readback differs')
        require(color(item['untouched_second_rgba'], [0, 0, 255, 255]), 'untouched second target differs before repaint')
    require(set(ordinary_routes) == set(colors), 'ordinary routes duplicated or omitted')
    resource = payload['resource_failure_recovery']
    closed(resource, 'branch_id status injections expected_error baseline after_failure cleanup timer_stopped recovery', 'resource branch')
    require(resource['branch_id'] == 'resource.upload-recovery' and resource['status'] == 'PASS'
            and resource['injections'] == ['green-upload'] and resource['timer_stopped'] is True, 'resource injection/timer failed')
    expected_error(resource['expected_error'], 'ValueError', 'observed resource timer upload failure')
    require('in tick' in resource['expected_error']['traceback'] and 'in upload' in resource['expected_error']['traceback'],
            'resource traceback lost callback origin')
    for key in ('baseline', 'after_failure'):
        closed(resource[key], ' '.join(GAUGES), 'resource gauges')
        require(all(integer(v) for v in resource[key].values()), 'invalid scoped gauge')
    require(resource['baseline'] == resource['after_failure'], 'resource counters did not return to baseline')
    closed(resource['cleanup'], 'host_survived secondary_errors timer_stopped', 'resource cleanup')
    require(resource['cleanup']['host_survived'] is True and resource['cleanup']['timer_stopped'] is True
            and type(resource['cleanup']['secondary_errors']) is int and resource['cleanup']['secondary_errors'] == 0,
            'resource cleanup failed')
    recovery = resource['recovery']
    closed(recovery, 'scope device_recovered timer_ticks shared survivor_color physical_sizes status host_survived retirement', 'resource recovery')
    require(recovery['status'] == 'PASS' and text(recovery['scope']) and recovery['device_recovered'] is True
            and recovery['shared'] is True and recovery['host_survived'] is True
            and type(recovery['timer_ticks']) is int and recovery['timer_ticks'] == 1
            and color(recovery['survivor_color'], [0, 0, 255, 255]), 'resource recovery differs')
    sizes = recovery['physical_sizes']
    require(type(sizes) is list and len(sizes) == 2 and all(type(size) is list and len(size) == 2
            and all(integer(v, 3) for v in size) for size in sizes), 'resource recovery lacks actual extents')
    retirement = recovery['retirement']
    closed(retirement, 'baseline before_delete after_delete canvas_bytes survivor_alive python_references_alive', 'resource retirement')
    require(retirement['survivor_alive'] is True and integer(retirement['canvas_bytes'], 1)
            and type(retirement['python_references_alive']) is int and retirement['python_references_alive'] == 3,
            'retirement lost live survivor or Python references')
    for name in ('baseline', 'before_delete', 'after_delete'):
        closed(retirement[name], ' '.join(RETIREMENT_GAUGES), 'retirement gauges')
        require(all(integer(v) for v in retirement[name].values()), 'invalid retirement gauge')
    require(all(retirement['before_delete'][k] > retirement['baseline'][k]
                for k in ('live_cpu_buffer_bytes', 'live_buffer_bytes', 'resource_texture_bytes')),
            'resource retirement is vacuous')
    require(retirement['after_delete'] == retirement['baseline'], 'resource retirement did not return to baseline before close')
    progress = payload['native_progress_failure_recovery']
    require(type(progress) is list and len(progress) == 2, 'missing progress callback order')
    orders = []
    for item in progress:
        closed(item, 'branch_id status callback_order loop injections deliveries expected_error recovered_color '
               'host_preserved polling_stopped recovered_progress_enabled cleanup_errors', 'progress branch')
        order = item['callback_order']
        require(order in ('poll', 'draw') and item['branch_id'] == 'progress.' + order, 'wrong progress branch identity')
        orders.append(order)
        require(item['status'] == 'PASS' and item['loop'] == 'external' and item['host_preserved'] is True
                and item['polling_stopped'] is True and item['recovered_progress_enabled'] is True
                and color(item['recovered_color'], [0, 0, 255]), 'progress recovery/polling/host failed')
        require(all(type(item[k]) is int and item[k] == expected for k, expected in
                    (('injections', 1), ('deliveries', 1), ('cleanup_errors', 0))), 'progress delivery/cleanup differs')
        trace = item['expected_error']
        require(text(trace) and trace.startswith('Traceback (most recent call last):\n')
                and 'ValueError: observed native progress failure' in trace and 'in fail' in trace, 'wrong progress traceback')
    require(set(orders) == {'poll', 'draw'}, 'progress order duplicated or omitted')
    branches = payload['submission_failure_recovery']
    require(type(branches) is list and len(branches) == 4, 'missing submission branch')
    variants = []
    for item in branches:
        closed(item, 'branch_id route delayed_progress expected_error before blocked early_progress retired resumed '
               'readback presented_rgb saved_frame_slots configured_frame_slots restored_frame_slots status host_preserved cleanup_errors',
               'submission branch')
        route, delayed = item['route'], item['delayed_progress']
        require(route in ('gloo', 'raw') and type(delayed) is bool, 'unknown submission route/delay')
        variants.append((route, delayed))
        require(item['branch_id'] == 'submission.' + route + ('.delayed' if delayed else '.immediate'), 'wrong submission branch ID')
        require(item['status'] == 'PASS' and item['host_preserved'] is True and integer(item['cleanup_errors'])
                and item['cleanup_errors'] == 0, 'submission cleanup failed')
        require(integer(item['saved_frame_slots'], 1) and type(item['configured_frame_slots']) is int
                and item['configured_frame_slots'] == 1 and type(item['restored_frame_slots']) is int
                and item['restored_frame_slots'] == item['saved_frame_slots'], 'frame slots were not configured/restored')
        expected_error(item['expected_error'], 'RuntimeError', 'capacity')
        require('glFlush' in item['expected_error']['message'], 'capacity error lost public context')
        before = item['before']
        counters(before, ('pending_tickets', 'pending_draws'))
        require(before['pending_tickets'] == 1, 'completion was not held at capacity')
        require((item['early_progress'] is not None) is delayed, 'early progress variant was not executed')
        for key in ('blocked', 'retired', 'resumed') + (('early_progress',) if delayed else ()):
            snapshot = item[key]
            counters(snapshot, ('pending_tickets', 'pending_draws'))
            require(all(snapshot[k] == before[k] for k in COUNTERS[1:]), 'capacity/progress/retry waited or presented')
            require(snapshot['dawn_queue_submits'] == before['dawn_queue_submits'] + (key == 'resumed'),
                    'unexpected submission or missing/duplicate explicit retry')
            if key == 'retired':
                require(snapshot['pending_tickets'] == 0 and snapshot['pending_draws'] > 0, 'retirement was not observed before retry')
            elif key == 'resumed':
                require(snapshot['pending_draws'] == 0 and snapshot['pending_tickets'] <= 1, 'retry retained pending work or exceeded capacity')
            elif key != 'resumed':
                require(snapshot['pending_tickets'] == 1 and snapshot['pending_draws'] > 0, 'capacity lost pending work')
        require(color(item['readback'], [0, 128, 0, 255]) and color(item['presented_rgb'], [0, 0, 255]), 'readback/display color differs')
    require(set(variants) == {(route, delayed) for route in ('gloo', 'raw') for delayed in (False, True)},
            'submission variants duplicated or omitted')
    return {'contract': CONTRACT, 'schema': 1, 'status': 'PASS_FUNCTIONAL_RESULT',
            'branch_ids': sorted(['ordinary.state', 'resource.upload-recovery', 'progress.poll', 'progress.draw']
                                 + [item['branch_id'] for item in branches]),
            'qualified': False}
