# SPDX-License-Identifier: AGPL-3.0-only
"""R1 instrumentation (tools/pool_watch.py) records the lost default thread pool once, without touching handles."""
import json
import time

import tools.pool_watch as watch


def events(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def test_pool_watch_records_the_lost_default_pool_once_with_every_stack(tmp_path, monkeypatch):
    calls = {'default': 0}

    def handle_type(value):  # the default pool's factory becomes a reused Semaphore on the fourth query
        if value == 28:
            calls['default'] += 1
            return 'TpWorkerFactory' if calls['default'] < 4 else 'Semaphore'
        return 'TpWorkerFactory' if value == 148 else 'status 0xc0000008'

    monkeypatch.setattr(watch, '_started', None)
    monkeypatch.setattr(watch.sys, 'platform', 'win32')
    monkeypatch.setattr(watch, '_handle_type', handle_type)
    monkeypatch.setattr(watch, 'INTERVAL', 0.001)
    path = tmp_path / 'events.jsonl'
    assert watch.start(str(path)) == 28
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and 'default_pool_lost' not in path.read_text(encoding='utf-8'):
        time.sleep(0.01)
    watching, lost = events(path)
    assert watching['event'] == 'watching' and watching['factories'] == [28, 148]
    assert lost['event'] == 'default_pool_lost' and lost['handle'] == 28 and lost['now'] == 'Semaphore'
    assert lost['factories'] == [148] and lost['stacks'] and lost['seconds'] >= 0
    time.sleep(0.05)
    assert len(events(path)) == 2  # the watcher stops after one record
    assert watch.start(str(path)) is None  # once per process


def test_pool_watch_off_windows_records_that_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, '_started', None)
    monkeypatch.setattr(watch.sys, 'platform', 'linux')
    path = tmp_path / 'events.jsonl'
    assert watch.start(str(path)) is None
    assert [event['event'] for event in events(path)] == ['unsupported_platform']


# Only the tests are re-exported into CI's curated list (tests/contract/test_napari_plugin_wheel_suite.py).
__all__ = [name for name in dir() if name.startswith('test_')]
