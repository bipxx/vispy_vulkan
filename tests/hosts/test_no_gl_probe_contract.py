# SPDX-License-Identifier: AGPL-3.0-only
"""Artifact and failure reporting contracts for installed host qualification."""

import importlib.util
import inspect
import json
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'no_opengl_host_probe', ROOT / 'tools/no_opengl_host_probe.py')
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def test_stale_source_overlay_cannot_pass_exact_artifact_check(tmp_path):
    package = tmp_path / 'installed/vispy'
    package.mkdir(parents=True)
    payload = {'__init__.py': b'# wheel source\n', '_dawn.test.pyd': b'native payload'}
    wheel = tmp_path / 'candidate.whl'
    with zipfile.ZipFile(wheel, 'w') as bundle:
        for name, value in payload.items():
            bundle.writestr('vispy/' + name, value)
            (package / name).write_bytes(value)
    result = PROBE.verify_installed_payload(wheel, package)
    assert result['verified_files'] == 2
    assert result['wheel_sha256'] == PROBE.file_sha256(wheel)
    (package / '__init__.py').write_bytes(b'# source from another worktree\n')
    with pytest.raises(RuntimeError, match='differs from exact wheel: vispy/__init__.py'):
        PROBE.verify_installed_payload(wheel, package)


def test_native_payload_is_required_even_when_metadata_and_python_exist(tmp_path):
    package = tmp_path / 'vispy'
    package.mkdir()
    (package / '__init__.py').write_bytes(b'')
    wheel = tmp_path / 'python-only.whl'
    with zipfile.ZipFile(wheel, 'w') as bundle:
        bundle.writestr('vispy/__init__.py', b'')
    with pytest.raises(RuntimeError, match='lacks the required VisPy Python/native payload'):
        PROBE.verify_installed_payload(wheel, package)


def test_functional_failure_is_retained_before_process_exit(tmp_path):
    evidence = PROBE.Evidence(tmp_path / 'evidence', 'napari')
    with pytest.raises(RuntimeError, match='device lost'):
        with evidence.stage('volume_capture'):
            raise RuntimeError('device lost')
    report = json.loads((evidence.output / 'functional.json').read_text())
    assert report['stages'][0]['status'] == 'failed'
    assert 'device lost' in report['stages'][0]['error']
    assert report['native_no_opengl_gates'] == 'external monitor required'


def test_existing_evidence_is_never_overwritten(tmp_path):
    output = tmp_path / 'evidence'
    PROBE.Evidence(output, 'qwidget')
    with pytest.raises(FileExistsError):
        PROBE.Evidence(output, 'napari')


class _Clock:
    def __init__(self):
        self.now = 0.

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class _ThrottledHost:
    """vispy drops moves within 10 ms; napari's leading-edge qthrottled defers a
    move until the event loop dispatches the 5 ms timer started after its handler."""

    def __init__(self, clock, lost=()):
        self.clock, self.lost = clock, set(lost)
        self.applied, self.pending, self.due, self.delivered = [], None, None, -1.

    def _apply(self, point):
        self.applied.append(point)
        self.clock.now += .015  # move-to-move delivery gap; run 202 measured 11.8-49 ms
        self.due = self.clock.now + .005

    def mouseMove(self, native, point, delay=-1):
        if point in self.lost or self.clock.now - self.delivered < .01:
            return
        self.delivered = self.clock.now
        if self.due is None:
            self._apply(point)
        else:
            self.pending = point

    def process_events(self):
        if self.due is not None and self.clock.now >= self.due:
            point, self.pending, self.due = self.pending, None, None
            if point is not None:
                self._apply(point)


@pytest.fixture
def throttled_host(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(PROBE, 'time', clock)
    return lambda lost=(): _ThrottledHost(clock, lost)


def test_single_pumps_leave_a_throttled_final_move_pending(throttled_host):
    # The original threedee drag: release followed while napari still deferred move2.
    host = throttled_host()
    for point in ('first', 'final'):
        host.mouseMove(None, point, 40)
        PROBE.pump(host)
    assert host.applied == ['first'] and host.pending == 'final'


@pytest.mark.parametrize('settle', (.05, 0))
def test_settled_moves_apply_the_final_move_before_returning(throttled_host, settle):
    host = throttled_host()
    PROBE.settled_moves(host, host, None, ('first', 'final'),
                        lambda: host.applied[-1:] == ['final'], settle=settle)
    assert host.applied == ['first', 'final'] and host.pending is None


def test_threedee_drag_goes_through_settled_moves():
    source = inspect.getsource(PROBE.threedee)
    assert 'settled_moves(' in source and 'mouseMove(' not in source


def test_settled_moves_fail_when_the_final_move_is_never_applied(throttled_host):
    host = throttled_host(lost={'final'})
    with pytest.raises(TimeoutError):
        PROBE.settled_moves(host, host, None, ('first', 'final'),
                            lambda: host.applied[-1:] == ['final'])
    assert host.applied == ['first']
