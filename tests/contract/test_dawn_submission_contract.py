# SPDX-License-Identifier: AGPL-3.0-only
"""Native-version protocol controls without opening a device or GUI."""
from types import SimpleNamespace

import pytest
import vispy
from vispy.gloo.dawn_parser import DawnGlirParser


@pytest.mark.parametrize('commands', [[('FUNC', 'glFlush')], [['FUNC', 'glFlush']]])
@pytest.mark.parametrize('version', [None, 0])
def test_legacy_native_module_cannot_silently_accept_flush(monkeypatch, commands, version):
    executed = []
    native = SimpleNamespace(execute=lambda *args: executed.append(args), device_info=lambda: {})
    if version is not None:
        native.submission_contract_version = version
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    with pytest.raises(RuntimeError, match='matching native submission-contract build'):
        DawnGlirParser().parse(commands)
    assert not executed


def test_matching_contract_transports_flush_to_native(monkeypatch):
    executed = []
    native = SimpleNamespace(submission_contract_version=1,
                             execute=lambda *args: executed.append(args), device_info=lambda: {})
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    parser = DawnGlirParser()
    parser.canvas_id = 7
    parser.parse([('FUNC', 'glFlush')])
    assert len(executed) == 1 and executed[0][0] == 7
    assert executed[0][1] == [('FUNC', 'glFlush')]


def test_legacy_nonflush_commands_keep_their_existing_transport(monkeypatch):
    executed = []
    native = SimpleNamespace(execute=lambda *args: executed.append(args), device_info=lambda: {})
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    DawnGlirParser().parse([('FUNC', 'glViewport', 0, 0, 8, 8)])
    assert len(executed) == 1


def test_legacy_generator_keeps_streaming_array_snapshot_semantics(monkeypatch):
    import numpy as np
    executed = []
    native = SimpleNamespace(execute=lambda *args: executed.append(args), device_info=lambda: {})
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    payload = np.array([1], np.float32)
    def commands():
        yield ('DATA', 1, 0, payload)
        payload[:] = 2
        yield ('DATA', 1, 4, payload)
    DawnGlirParser().parse(commands())
    packed = executed[0][1]
    assert np.frombuffer(packed[0][3]['__bytes__'], np.float32).tolist() == [1]
    assert np.frombuffer(packed[1][3]['__bytes__'], np.float32).tolist() == [2]
