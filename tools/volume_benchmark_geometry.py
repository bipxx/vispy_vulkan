# SPDX-License-Identifier: AGPL-3.0-only
"""Observe the unmodified original volume cube, retaining all its measured cost.

No provider imports. This allowance is only for the pinned original renderer;
candidate resident work continues through the unchanged generic zero gate.
"""
from __future__ import annotations

import copy
import hashlib
from typing import NamedTuple
import numpy as np

from . import benchmark_frames as benchmark

GENERIC_WORK_GATE = benchmark.measured_work_gate


BUFFER_TYPES = ('VertexBuffer', 'IndexBuffer')
BUFFER_COUNTERS = ('gl_buffer_upload_calls', 'gl_buffer_upload_bytes')


class LivePayload(NamedTuple):
    dtype: str
    shape: tuple
    body: bytes


def capture_payload(value):
    require(isinstance(value, np.ndarray), 'Live buffer payload must be an ndarray')
    require(value.nbytes <= 96, 'Unexpected geometry payload size')
    # Size is checked before any contiguity copy. SHA/JSON construction happens
    # only when snapshot() runs after the measured interval.
    return LivePayload(value.dtype.str, value.shape, value.tobytes(order='C'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def array_record(value):
    """Only tiny geometry is hashed; never copy/hash a large source texture."""
    if isinstance(value, dict):
        # Saved captures are accepted by the pure validator, not the live hook.
        return copy.deepcopy(value)
    payload = value if isinstance(value, LivePayload) else capture_payload(value)
    return dict(array=dict(dtype=payload.dtype, shape=list(payload.shape),
                          bytes=len(payload.body), sha256=hashlib.sha256(payload.body).hexdigest()))


def reference_geometry(initial):
    """Extract the two actual typed cube buffers from a pinned original stage."""
    ids = initial['geometry_ids']
    require(len(ids) == len(set(ids)) == 2, 'Exactly two distinct geometry IDs required')
    result = {}
    for identifier, kind, size in zip(ids, BUFFER_TYPES, (96, 56)):
        rows = [row for row in initial['commands'] if len(row) > 1 and row[1] == identifier]
        creates = [row for row in rows if row[0] == 'CREATE']
        sizes = [row for row in rows if row[0] == 'SIZE']
        data = [row for row in rows if row[0] == 'DATA']
        require(creates == [['CREATE', identifier, kind]], 'Original geometry type differs')
        require(sizes == [['SIZE', identifier, size]], 'Original geometry size differs')
        require(len(data) == 1 and data[0][2] == 0, 'Original geometry upload differs')
        record = data[0][3]['array']
        require(record['bytes'] == size and len(record['sha256']) == 64, 'Original geometry descriptor differs')
        result[kind] = dict(size=size, offset=0, payload=copy.deepcopy(data[0][3]))
    return result


class GeometryObservation:
    """Lossless bounded buffer-command ledger, attached before scene allocation.

    The parser executes every command unchanged. The ledger records observation
    failures without replacing a renderer exception; validation then fails.
    """

    def __init__(self, expected, *, frame_limit):
        require(type(frame_limit) is int and frame_limit > 0, 'Positive frame bound required')
        self.expected = copy.deepcopy(expected)
        self.frame_limit = frame_limit
        self.types = {}
        self.cold = []
        self.frames = {}
        self.errors = []
        self.unattributed = []
        self.active = False
        self.ids = None
        self.command_count = 0
        self.window = None

    def begin_window(self, first_frame, frame_count):
        require(self.window is None and self.active, 'Fresh active measured window required')
        self.window = dict(first_frame=first_frame, frame_count=frame_count,
                           unattributed_before=len(self.unattributed), command_before=self.command_count)

    def end_window(self):
        require(self.window is not None and 'unattributed_after' not in self.window, 'Open measured window required')
        self.window.update(unattributed_after=len(self.unattributed), command_after=self.command_count)

    def bind(self, identifiers):
        require(self.ids is None, 'Geometry may only bind once')
        require(len(identifiers) == len(set(identifiers)) == 2, 'Two distinct live geometry IDs required')
        self.ids = dict(zip(BUFFER_TYPES, identifiers))

    def observe(self, batch, frame_id=None, *, saved=False):
        """saved=True replays an already SHA-verified raw capture for CPU checks."""
        try:
            for row in batch:
                op = row[0]
                if op == 'CREATE':
                    require(row[1] not in self.types, 'GLIR object ID reused')
                    self.types[row[1]] = row[2]
                if len(row) < 2 or self.types.get(row[1]) not in BUFFER_TYPES:
                    continue
                if op not in ('CREATE', 'SIZE', 'DATA', 'DELETE'):
                    continue
                self.command_count += 1
                require(self.command_count <= (self.frame_limit + 32) * 16, 'Buffer observation bound exceeded')
                recorded = list(row)
                if op == 'DATA':
                    require(saved or isinstance(row[3], np.ndarray), 'Live buffer payload must be an ndarray')
                    recorded[3] = array_record(row[3]) if saved else capture_payload(row[3])
                if not self.active:
                    self.cold.append(recorded)
                elif frame_id is None:
                    require(len(self.unattributed) < 32, 'Unattributed buffer command bound exceeded')
                    self.unattributed.append(recorded)
                else:
                    require(type(frame_id) is int and 0 <= frame_id < self.frame_limit, 'Unknown measured/warm frame ID')
                    self.frames.setdefault(frame_id, []).append(recorded)
                if op == 'DELETE':
                    del self.types[row[1]]
        except Exception as error:
            if len(self.errors) < 32:
                self.errors.append(str(error))

    def snapshot(self):
        result = copy.deepcopy(dict(schema=1, geometry_ids=self.ids, expected=self.expected,
            cold=self.cold, frames={str(key): value for key, value in self.frames.items()},
            errors=self.errors, unattributed=self.unattributed,
            measured_window=self.window,
            scope='Observed pass-through GLIR buffer commands; original work and instrumentation time retained'))
        for rows in (result['cold'], result['unattributed'], *result['frames'].values()):
            for row in rows:
                if row[0] == 'DATA' and isinstance(row[3], LivePayload):
                    row[3] = array_record(row[3])
        return result


def validate_geometry(record, expected, *, first_frame, frame_count, raw_counters):
    """Prove exact original geometry AND its full raw measured GL upload total."""
    try:
        require(type(first_frame) is int and first_frame >= 0, 'Invalid first frame')
        require(type(frame_count) is int and frame_count > 0, 'Invalid frame count')
        require(record['schema'] == 1 and not record['errors'], 'Incomplete buffer observation')
        window = record['measured_window']
        require(window['first_frame'] == first_frame and window['frame_count'] == frame_count, 'Measured window frame range differs')
        before, after = window['unattributed_before'], window['unattributed_after']
        require(type(before) is int and type(after) is int and 0 <= before <= after == len(record['unattributed']), 'Incomplete measured window boundary')
        require(before == after, 'Unowned buffer commands in the measured window')
        require(window['command_after'] - window['command_before'] == frame_count * 4, 'Measured window buffer command total differs')
        require(record['expected'] == expected, 'Geometry reference differs')
        ids = record['geometry_ids']
        require(set(ids) == set(BUFFER_TYPES) and len(set(ids.values())) == 2, 'Live geometry binding differs')
        for kind, identifier in ids.items():
            require(type(identifier) is int and identifier > 0, 'Invalid live geometry ID')
            rows = [row for row in record['cold'] if row[1] == identifier]
            require([row for row in rows if row[0] == 'CREATE'] == [['CREATE', identifier, kind]], 'Live geometry type differs')
            require(not any(row[0] == 'DELETE' for row in rows), 'Geometry deleted before measurement')
            for row in rows:
                if row[0] == 'SIZE': require(row == ['SIZE', identifier, expected[kind]['size']], 'Cold geometry size differs')
                if row[0] == 'DATA': require(row == ['DATA', identifier, 0, expected[kind]['payload']], 'Cold geometry payload differs')
            require(any(row[0] == 'DATA' for row in rows), 'Initial geometry upload not observed')
        expected_rows = [row for kind in BUFFER_TYPES for row in (
            ['SIZE', ids[kind], expected[kind]['size']],
            ['DATA', ids[kind], 0, expected[kind]['payload']])]
        for frame in range(first_frame, first_frame + frame_count):
            require(record['frames'].get(str(frame)) == expected_rows,
                    f'Frame {frame} differs from the exact original repeated cube uploads')
        require(type(raw_counters.get('gl_buffer_upload_calls')) is int and
                raw_counters['gl_buffer_upload_calls'] == frame_count * 2, 'Raw GL upload call total differs')
        require(type(raw_counters.get('gl_buffer_upload_bytes')) is int and
                raw_counters['gl_buffer_upload_bytes'] == frame_count * 152, 'Raw GL upload byte total differs')
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return dict(status='unproven', reasons=[str(error)])
    return dict(status='passed', reasons=[], frames=frame_count, uploads=frame_count * 2,
                bytes=frame_count * 152, scope='Only pinned original repeated cube; all raw counters and elapsed time retained')


def measured_work_gate(run, kind, *, update=False, expected=None):
    """The generic gate remains authoritative outside the exact volume allowance."""
    generic = GENERIC_WORK_GATE(run, kind, update=update)
    if kind != 'upstream' or run.get('workload', {}).get('family') != 'volume':
        return generic
    if expected is None:
        return dict(status='unproven', reasons=['Pinned original volume geometry required'])
    proof = validate_geometry(run.get('original_geometry', {}), expected,
        first_frame=run.get('warmup_frames'), frame_count=run.get('measured_frames'),
        raw_counters=run.get('counter_delta', {}))
    if proof['status'] != 'passed':
        return dict(status='unproven', reasons=proof['reasons'], original_geometry=proof)
    if update or generic['status'] == 'passed':
        return dict(generic, original_geometry=proof)
    if generic['status'] == 'failed' and set(generic.get('forbidden_nonzero', ())) == set(BUFFER_COUNTERS):
        return dict(status='passed', reasons=[], original_geometry=proof,
            required_zero=[key for key in generic['required_zero'] if key not in BUFFER_COUNTERS],
            allowed_observed_work=list(BUFFER_COUNTERS), generic_without_allowance=generic)
    return dict(generic, original_geometry=proof)
