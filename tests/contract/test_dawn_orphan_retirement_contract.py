# SPDX-License-Identifier: AGPL-3.0-only
"""Native protocol failure/compatibility controls without GPU execution."""
from types import SimpleNamespace

import numpy as np
import pytest
import vispy
from vispy.gloo.dawn_parser import DawnGlirParser


def native_module(monkeypatch, version=1, fail=False, owned=False):
    retired, executed = [], []

    def execute(*args):
        executed.append(args)
        if fail:
            raise RuntimeError('missing canvas 0')

    native = SimpleNamespace(execute=execute, device_info=lambda: {},
                             retire_objects=lambda ids: retired.extend(ids))
    if version is not None:
        native.object_retirement_contract_version = version
    if owned:
        native._capture_upload = lambda value: value
        native._execute_owned = execute
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    return native, retired, executed


def test_parser_without_parse_does_not_load_or_retire_native(monkeypatch):
    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError('native access before parse: ' + name)

    monkeypatch.setattr(vispy, '_dawn', Forbidden(), raising=False)
    DawnGlirParser().retire_orphaned([1])


@pytest.mark.parametrize('version', [None, 0, 2])
def test_other_native_versions_keep_legacy_behavior_without_false_retirement(monkeypatch, version):
    _, retired, executed = native_module(monkeypatch, version)
    parser = DawnGlirParser()
    parser.parse([])
    parser.retire_orphaned([2])
    assert len(executed) == 1 and retired == []


def test_matching_contract_caches_retirement_without_later_native_lookup(monkeypatch):
    _, retired, _ = native_module(monkeypatch)
    parser = DawnGlirParser()
    parser.parse([])
    monkeypatch.setattr(vispy, '_dawn', None)
    parser.retire_orphaned([np.int64(3), 4])
    assert retired == [3, 4]
    assert all(type(i) is int for i in retired)


@pytest.mark.parametrize('owned', [False, True])
def test_failed_execution_retires_consumed_deletes_and_preserves_error(monkeypatch, owned):
    _, retired, executed = native_module(monkeypatch, fail=True, owned=owned)
    parser = DawnGlirParser()
    with pytest.raises(RuntimeError, match='missing canvas 0'):
        parser.parse([('DELETE', 5), ('FUNC', 'glClear', 0x4000), ('DELETE', 6)])
    assert len(executed) == 1 and retired == [5, 6]


def test_packing_failure_preserves_already_consumed_deletion(monkeypatch):
    _, retired, executed = native_module(monkeypatch)
    parser = DawnGlirParser()

    def commands():
        yield ('DELETE', 7)
        raise ValueError('producer failed')

    with pytest.raises(ValueError, match='producer failed'):
        parser.parse(commands())
    assert executed == [] and retired == [7]


@pytest.mark.parametrize('owned', [False, True])
def test_list_packing_failure_preserves_deletes_after_failing_payload(monkeypatch, owned):
    _, retired, executed = native_module(monkeypatch, owned=owned)

    class Enum:
        def __int__(self):
            raise ValueError('invalid enum payload')

    with pytest.raises(ValueError, match='invalid enum payload'):
        DawnGlirParser().parse([('FUNC', 'glClear', Enum()), ('DELETE', 10)])
    assert executed == [] and retired == [10]


def test_successful_execution_keeps_normal_delete_ordering(monkeypatch):
    _, retired, executed = native_module(monkeypatch)
    DawnGlirParser().parse([('DELETE', 8)])
    assert executed[0][1] == [('DELETE', 8)] and retired == []


def test_retirement_failure_does_not_replace_original_execution_error(monkeypatch):
    native, _, _ = native_module(monkeypatch, fail=True)

    def fail_retirement(ids):
        raise ValueError('retirement failed')

    native.retire_objects = fail_retirement
    with pytest.raises(RuntimeError, match='missing canvas 0') as caught:
        DawnGlirParser().parse([('DELETE', 9)])
    assert isinstance(caught.value.__cause__, ValueError)
