# SPDX-License-Identifier: AGPL-3.0-only
"""R1 instrumentation from outside the watched processes (tools/pool_watch_external.py, D20)."""
from collections import defaultdict
from types import SimpleNamespace
import json
import struct
import subprocess
import sys

import pytest

import tools.pool_watch_external as watcher


def snapshot(*entries):
    """A PROCESS_HANDLE_SNAPSHOT_INFORMATION buffer holding (handle value, type index) entries."""
    return struct.pack('<QQ', len(entries), 0) + b''.join(
        watcher.ENTRY.pack(handle, 1, 1, 0x1F0003, kind, 0, 0) for handle, kind in entries)


class Fake:
    """The native calls, replayed: one list of handle tables per process (None: terminating), the job's members at
    each look (the last list repeats) and each process's (parent, name)."""

    def __init__(self, tables, members=(), described=None, exit_after=None):
        self.tables = {pid: list(sequence) for pid, sequence in tables.items()}
        self.looks, self.described, self.exit_after = [list(m) for m in members], dict(described or {}), dict(exit_after or {})
        self.reads = defaultdict(int)

    def type_names(self):
        return {21: 'Event', 24: 'Semaphore', 35: 'TpWorkerFactory'}

    def members(self, *, strict=False):
        if not self.looks:
            return []
        return self.looks.pop(0) if len(self.looks) > 1 else self.looks[0]

    def open(self, pid):
        return pid if pid in self.tables else None

    def close(self, process):
        pass

    def describe(self, process):
        return self.described.get(process, (None, None))

    def snapshot(self, process):
        self.reads[process] += 1
        sequence = self.tables[process]
        return sequence.pop(0) if sequence else None

    def exited(self, process):
        limit = self.exit_after.get(process)
        return limit is not None and self.reads[process] >= limit


def run(api, root=4242, *, deadline=None):
    events = []
    watcher.watch(api, root, lambda **fields: events.append(fields), 0, 0.0, deadline)
    return events


def test_decode_reads_handle_values_and_type_indices_and_rejects_a_short_buffer():
    raw = snapshot((40, 35), (44, 21), (164, 35))
    assert watcher.decode(raw) == [(40, 35), (44, 21), (164, 35)]
    assert watcher.decode(raw + bytes(7)) == [(40, 35), (44, 21), (164, 35)]
    assert watcher.decode(snapshot()) == []
    with pytest.raises(ValueError):
        watcher.decode(raw[:-1])


def test_watch_reports_the_lowest_factory_then_each_loss_and_keeps_watching():
    events = run(Fake({4242: [[(8, 21)], [(40, 35), (164, 35)], [(40, 35), (164, 35)], [(40, 24), (164, 35)],
                              [(164, 35)], [], None]}))
    assert [event['event'] for event in events] == ['watching', 'default_pool_lost', 'watching', 'default_pool_lost']
    assert events[0]['handle'] == 40 and events[0]['factories'] == [40, 164] and events[0]['factory_type'] == 35
    assert events[1]['handle'] == 40 and events[1]['now'] == 'Semaphore' and events[1]['factories'] == [164]
    assert events[2]['handle'] == 164
    assert events[3]['handle'] == 164 and events[3]['now'] == 'closed' and events[3]['factories'] == []
    assert all(event['pid'] == 4242 for event in events)


def test_a_table_read_at_exit_is_not_a_loss_and_a_process_without_a_pool_says_so():
    # The second read happens as the process exits: its empty table must not count as a closed pool.
    assert [event['event'] for event in run(Fake({4242: [[(40, 35)], []]}, exit_after={4242: 2}))] == ['watching']
    assert [event['event'] for event in run(Fake({4242: [[(8, 21)], [(12, 24)], None]}))] == ['no_worker_factory']
    unnamed = run(Fake({4242: [[(40, 35)], [(40, 77)], None]}))
    assert unnamed[1]['now'] == 77  # an index the watcher holds no handle of is recorded as a number
    assert [event['event'] for event in run(Fake({}))] == ['not_found']  # the process was already gone


def test_a_new_job_member_is_adopted_and_watched_and_a_non_member_is_not():
    # 100 is a launcher; 200, its interpreter, joins the job at the second look and loses its pool. 300 has a
    # handle table but never joins the job.
    api = Fake({100: [[(40, 35)]] * 4, 200: [[(40, 35)], [(40, 24)], None], 300: [[(40, 35)]] * 4},
               members=[[100], [100, 200]], described={200: (100, 'python.exe')})
    events = run(api, root=100)
    assert [(event['event'], event['pid']) for event in events] == [
        ('watching', 100), ('adopted', 200), ('watching', 200), ('default_pool_lost', 200)]
    assert events[1]['parent'] == 100 and events[1]['name'] == 'python.exe'
    assert events[3]['now'] == 'Semaphore' and events[3]['handle'] == 40


def test_job_members_are_checked_again_after_the_last_observed_process_exits():
    api = Fake({100: [[(40, 35)], None], 200: [[(44, 35)], None]},
               members=[[100], [100], [200], [200], []])
    events = run(api, root=100, deadline=float('inf'))
    assert [(event['event'], event['pid']) for event in events] == [
        ('watching', 100), ('adopted', 200), ('watching', 200)]


def test_failed_membership_query_is_only_fatal_in_strict_mode():
    api = watcher.Windows.__new__(watcher.Windows)
    api.job = 1
    api.job_buffer = bytes(16)
    api.kernel32 = SimpleNamespace(QueryInformationJobObject=lambda *args: False)
    api.ctypes = SimpleNamespace(get_last_error=lambda: 5, WinError=OSError)
    assert api.members() == []
    with pytest.raises(OSError, match='5'):
        api.members(strict=True)


def test_missing_factory_type_exits_immediately_unless_a_deadline_is_set(monkeypatch):
    api = Fake({}, members=[[100], []])
    monkeypatch.setattr(api, 'type_names', lambda: {21: 'Event'})
    assert [(event['event'], event['pid']) for event in run(api, root=100)] == [
        ('no_own_worker_factory', 100)]
    assert api.looks == [[100], []]

    events = []
    monkeypatch.setattr(watcher.time, 'perf_counter', lambda: 2.0)
    with pytest.raises(subprocess.TimeoutExpired):
        watcher.watch(api, 100, lambda **fields: events.append(fields), 0, 0.0, deadline=1.0)
    assert events == [
        dict(event='no_own_worker_factory', pid=100, seconds=2.0),
        dict(event='timeout', seconds=2.0, active_pids=[100]),
    ]


def test_launch_mode_watches_a_real_child_and_returns_its_exit_code(tmp_path):
    output = tmp_path / 'events.jsonl'
    code = watcher.main(['--output', str(output), '--', sys.executable, '-B', '-S', '-c',
                         'import sys, time; time.sleep(0.3); sys.exit(3)'])
    events = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    print('events', events)
    assert code == 3
    if sys.platform == 'win32':
        assert any(event['event'] == 'watching' for event in events)
        assert not any(event['event'] == 'default_pool_lost' for event in events)
        assert events[-1]['event'] == 'target_exit' and events[-1]['returncode'] == 3 and events[-1]['child_waited']
    else:
        assert events == [{'event': 'unsupported_platform', 'platform': sys.platform, 'pid': events[0]['pid']}]


# The interpreter closes its own default pool's worker factory handle, lets a semaphore take the value, and
# terminates itself without running exit code that might need the pool.
CLOSER = r'''
import ctypes, time
from ctypes import wintypes
ntdll, kernel32 = ctypes.WinDLL('ntdll'), ctypes.WinDLL('kernel32')
ntdll.NtQueryObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG, ctypes.c_void_p]
buffer = ctypes.create_string_buffer(1024)
def kind(value):
    if ntdll.NtQueryObject(wintypes.HANDLE(value), 2, buffer, 1024, None) < 0:
        return None
    return ctypes.wstring_at(ctypes.c_void_p.from_buffer(buffer, 8).value, ctypes.c_ushort.from_buffer(buffer, 0).value // 2)
lowest = min(value for value in range(4, 8192, 4) if kind(value) == 'TpWorkerFactory')
time.sleep(0.5)
kernel32.CloseHandle(wintypes.HANDLE(lowest))
kernel32.CreateSemaphoreW.restype = wintypes.HANDLE
kernel32.CreateSemaphoreW(None, 0, 1, None)
time.sleep(0.3)
kernel32.TerminateProcess(wintypes.HANDLE(-1), 7)
'''


def test_launch_mode_records_a_real_lost_default_pool(tmp_path):
    output = tmp_path / 'events.jsonl'
    command = [sys.executable, '-B', '-S', '-c', CLOSER if sys.platform == 'win32' else 'raise SystemExit(7)']
    code = watcher.main(['--output', str(output), '--', *command])
    events = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    print('events', events)
    assert code == 7
    if sys.platform == 'win32':
        lost = [event for event in events if event['event'] == 'default_pool_lost']
        assert len(lost) == 1 and lost[0]['now'] in ('Semaphore', 'closed')
        watching = [event for event in events if event['event'] == 'watching' and event['pid'] == lost[0]['pid']]
        assert watching and watching[0]['handle'] == lost[0]['handle']
        assert events[-1]['event'] == 'target_exit' and events[-1]['returncode'] == 7
    else:
        assert [event['event'] for event in events] == ['unsupported_platform']


def test_timeout_waits_for_the_owned_job_then_a_fresh_launch_passes(tmp_path, capsys):
    output = tmp_path / 'timeout.jsonl'
    if sys.platform != 'win32':
        with pytest.raises(SystemExit) as exc:
            watcher.main(['--output', str(output), '--timeout', '1', '--', sys.executable,
                          '-B', '-S', '-c', 'import time; time.sleep(60)'])
        assert exc.value.code == 2
        assert '--timeout requires a Windows launch' in capsys.readouterr().err
        assert not output.exists()
        return
    code = watcher.main(['--output', str(output), '--timeout', '1', '--', sys.executable,
                         '-B', '-S', '-c', 'import time; time.sleep(60)'])
    events = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    assert code == 124
    timeout, exit_event = events[-2:]
    assert timeout['event'] == 'timeout' and exit_event['pid'] in timeout['active_pids']
    assert exit_event['event'] == 'target_exit' and exit_event['child_waited']
    assert exit_event['returncode'] == 124
    api = watcher.Windows()
    for pid in timeout['active_pids']:
        process = api.open(pid)
        if process:
            try:
                assert api.exited(process)
            finally:
                api.close(process)

    recovery = tmp_path / 'recovery.jsonl'
    assert watcher.main(['--output', str(recovery), '--timeout', '5', '--', sys.executable,
                         '-B', '-S', '-c', 'import time; time.sleep(0.3)']) == 0
    events = [json.loads(line) for line in recovery.read_text(encoding='utf-8').splitlines()]
    assert any(event['event'] == 'watching' for event in events)
    assert all(event['event'] != 'timeout' for event in events)
    assert events[-1]['event'] == 'target_exit' and events[-1]['returncode'] == 0


def launch_model(monkeypatch, failure=None):
    """The suspended-launch API boundary, without creating or changing a real process."""
    events = []

    class Child:
        pid = 4242
        killed = waited = False

        def kill(self):
            self.killed = True
            events.append('kill')

        def wait(self):
            self.waited = True
            events.append('wait')
            return -1

    child = Child()
    monkeypatch.setattr(watcher.subprocess, 'Popen', lambda *args, **kwargs: child)
    api = object.__new__(watcher.Windows)
    api.job = None
    api.ctypes = SimpleNamespace(get_last_error=lambda: 5)

    def resume(process):
        events.append('resume')
        return -1 if failure == 'resume' else 0

    api.kernel32 = SimpleNamespace(
        OpenProcess=lambda *args: None if failure == 'open' else 10,
        CreateJobObjectW=lambda *args: None if failure == 'job' else 20,
        AssignProcessToJobObject=lambda *args: failure != 'assign',
        CloseHandle=lambda handle: events.append(('close', handle)))
    api.ntdll = SimpleNamespace(NtResumeProcess=resume)
    return api, child, events


@pytest.mark.parametrize('failure', ['open', 'job', 'assign', 'resume'])
def test_failed_tracked_launch_kills_and_waits_without_running_unobserved(monkeypatch, failure):
    api, child, events = launch_model(monkeypatch, failure)
    with pytest.raises(OSError):
        api.launch(['unused-test-command'])
    assert child.killed and child.waited
    assert events.index('kill') < events.index('wait')
    assert api.job is None
    assert ('resume' in events) == (failure == 'resume')
    if failure != 'open':
        assert events.count(('close', 10)) == 1
    if failure in ('assign', 'resume'):
        assert events.count(('close', 20)) == 1


def test_tracked_launch_transfers_the_job_only_after_successful_resume(monkeypatch):
    api, child, events = launch_model(monkeypatch)
    assert api.launch(['unused-test-command']) is child
    assert api.job == 20 and not child.killed and not child.waited
    assert events == ['resume', ('close', 10)]


__all__ = [name for name in dir() if name.startswith('test_')]
