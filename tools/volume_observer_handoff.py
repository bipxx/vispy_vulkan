# SPDX-License-Identifier: AGPL-3.0-only
"""Cold/warm-only geometry observation outside frozen measured parser wrappers."""
from __future__ import annotations
import inspect
import json
import sys
from types import CodeType
from . import volume_benchmark_geometry as geometry

require = geometry.require


def same_callable(left, right):
    return (getattr(left, '__func__', left) is getattr(right, '__func__', right) and
            getattr(left, '__self__', None) is getattr(right, '__self__', None))


class Handoff:
    def __init__(self, canvas, ledger):
        self.canvas, self.ledger = canvas, ledger
        self.owner = canvas.context.shared.parser
        self.pristine = self.owner.parse
        self.had_own = 'parse' in self.owner.__dict__
        self.old_own = self.owner.__dict__.get('parse')
        self.calls = 0
        self.telemetry = None
        self.observer_cpu_ns = {}
        self.telemetry_parse = None
        self.warm_wrapper = None
        self.frozen = None
        self.evidence = dict(schema=2, detached=False)
        def cold(batch):
            self.calls += 1
            self.ledger.observe(batch)
            return self.pristine(batch)
        self.cold_wrapper = cold
        self.owner.parse = cold

    def queue_identity(self):
        shared = self.canvas.context.glir._shared
        return (id(shared), id(shared._commands), tuple(map(id, shared._commands)))

    def prepare_telemetry(self, constructor, expected_code):
        require(self.owner.parse is self.cold_wrapper, 'Cold observer was replaced')
        before = self.queue_identity()
        calls = self.calls
        if self.had_own: self.owner.parse = self.old_own
        else: del self.owner.parse
        code = getattr(getattr(self.pristine, '__func__', self.pristine), '__code__', None)
        require(code is not None, 'A Python parser boundary is required')
        require(sys.getprofile() is None, 'Existing profiler prevents parser hand-off proof')
        raw_calls = []
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is code: raw_calls.append(1)
        try:
            sys.setprofile(profile)
            constructor()
        finally:
            sys.setprofile(None)
        require(not raw_calls and calls == self.calls and before == self.queue_identity(), 'Parser/queue changed during cold-to-warm hand-off')
        self.telemetry_parse = self.owner.parse
        require(getattr(self.telemetry_parse,'__code__',None) is expected_code,'Parser wrapper is not frozen telemetry code')
        captured = inspect.getclosurevars(self.telemetry_parse).nonlocals.get('original')
        require(same_callable(captured, self.pristine), 'Frozen telemetry captured an observer instead of the pristine parser')
        self.evidence['handoff_parse_calls'] = len(raw_calls)
        self.evidence['handoff_queue_unchanged'] = True
        self.evidence['frozen_parser_code_verified'] = True
        self.cold_wrapper = None

    def observe_warm(self, telemetry):
        self.telemetry = telemetry
        self.ledger.active = True
        def warm(batch):
            self.calls += 1
            frame_id = None
            if telemetry.current is not None:
                matches = [key for key, value in telemetry.frames.items() if value is telemetry.current]
                require(len(matches) == 1, 'Warm parser lacks a unique frozen frame owner')
                frame_id = matches[0]
            self.ledger.observe(batch, frame_id)
            return self.telemetry_parse(batch)
        self.warm_wrapper = warm
        self.owner.parse = warm

    def detach(self):
        require(self.owner.parse is self.warm_wrapper, 'Warm observer was replaced')
        self.owner.parse = self.telemetry_parse
        self.frozen = json.dumps(self.ledger.snapshot(), sort_keys=True, separators=(',', ':')).encode()
        self.ledger.cold.clear(); self.ledger.frames.clear(); self.ledger.unattributed.clear()
        self.ledger.types.clear(); self.ledger.errors.clear()
        self.warm_wrapper = None
        self.evidence.update(detached=True, calls_before=self.calls, measured_parser_identity=id(self.telemetry_parse),
                             pristine_parser_captured=True, no_per_frame_override=True)

    def measured_end(self):
        require(self.evidence['detached'] and self.owner.parse is self.telemetry_parse and self.warm_wrapper is None,
                'Measured parser is not the frozen telemetry wrapper')
        require(self.evidence['calls_before'] == self.calls, 'An observer ran during measurement')
        self.evidence.update(calls_after=self.calls, measured_parser_identity_after=id(self.owner.parse), observer_invocation_delta=0)

    def snapshot(self):
        require(self.frozen is not None, 'Warm proof not frozen')
        return dict(evidence=dict(self.evidence), warm=json.loads(self.frozen))

    def close(self):
        # Called after frozen telemetry.close(), including the failure path.
        if self.owner.parse is self.cold_wrapper and self.cold_wrapper is not None:
            if self.had_own: self.owner.parse = self.old_own
            else: del self.owner.parse
        require(same_callable(self.owner.parse, self.pristine), 'Frozen telemetry did not restore the pristine parser')


def telemetry_class(frozen_class, state, warm_count, measured_count, *, boundary=None):
    """Only construction and the two unsampled snapshots may execute new code."""
    expected_code=None
    for cls in frozen_class.__mro__:
        code=getattr(cls.__dict__.get('__init__'),'__code__',None)
        if code is None:continue
        wrappers=[item for item in code.co_consts if isinstance(item,CodeType) and item.co_name=='parse_wrapper']
        if wrappers:
            expected_code=next(item for item in wrappers[0].co_consts if isinstance(item,CodeType) and item.co_name=='parse')
            break
    require(expected_code is not None,'Frozen parser wrapper code not found')
    class Telemetry(frozen_class):
        def __init__(self, canvas, **kwargs):
            current = state()
            try:
                current.prepare_telemetry(lambda: frozen_class.__init__(self, canvas, **kwargs),expected_code)
            except BaseException:
                if hasattr(self, '_restores'): frozen_class.close(self)
                current.close()
                raise
            self._handoff = current
            self._handoff_snapshots = 0
            current.observe_warm(self)

        def snapshot(self):
            result = super().snapshot()
            require(self.current is None, 'Unfinished paint at the counter boundary')
            if self._handoff_snapshots == 0:
                require(set(self.frames) == set(range(warm_count)), 'Warm frame retirement incomplete')
                self._handoff.detach()
                if boundary is not None: boundary('before')
            elif self._handoff_snapshots == 1:
                require(set(self.frames) == set(range(warm_count + measured_count)), 'Measured frame retirement incomplete')
                self._handoff.measured_end()
                if boundary is not None: boundary('after')
            else:
                raise ValueError('Unexpected frozen counter snapshot')
            self._handoff_snapshots += 1
            return result
    require(Telemetry.begin is frozen_class.begin, 'Measured begin must be the frozen implementation')
    return Telemetry
