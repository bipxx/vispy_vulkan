# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise the Dawn/Vulkan startup path in fresh Windows processes (BUG-01).

Run with the worktree on PYTHONPATH and Python -B -S. Each run starts one
headless canvas, checks a known readback, closes it and shuts down the renderer.
The external pool watcher samples the worker throughout. The first anomalous
attempt stops the campaign and keeps its original progress and watcher logs.
"""

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[1]


def render_once(progress):
    began = time.perf_counter()

    def mark(stage, **details):
        with progress.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(dict(stage=stage, pid=os.getpid(),
                                         seconds=round(time.perf_counter() - began, 4),
                                         **details)) + '\n')

    mark('importing')
    import numpy as np
    import vispy
    from vispy import _dawn, app, gloo

    package = Path(vispy.__file__).resolve()
    native = Path(_dawn.__file__).resolve()
    if package != WORKTREE / 'src/vispy/__init__.py' or native.parent != package.parent:
        raise RuntimeError(f'expected worktree modules, got {package} and {native}')
    mark('starting_canvas', package=str(package), native=str(native))
    canvas = app.Canvas(app='dawn_headless', size=(16, 16), show=False)
    try:
        mark('reading_pixels')
        canvas.set_current()
        gloo.set_clear_color((0, 0, 1, 1))
        gloo.clear()
        pixels = gloo.read_pixels((0, 0, 16, 16), alpha=True)
        expected = np.broadcast_to(np.array([0, 0, 255, 255], dtype=np.uint8), (16, 16, 4))
        np.testing.assert_array_equal(pixels, expected)
        device = _dawn.device_info()
        if not device['ok'] or device['backend'] != 'Vulkan':
            raise RuntimeError(f'expected Vulkan device, got {device}')
        mark('pixel_check_passed', rgba=pixels[8, 8].tolist(), device=device)
    finally:
        mark('closing_canvas')
        canvas.close()
    mark('shutting_down')
    _dawn.shutdown()
    mark('finished')


def read_events(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def summarize(returncode, progress, events):
    worker = progress[0]['pid'] if progress else None
    watched = any(event['event'] == 'watching' and event['pid'] == worker for event in events)
    losses = [event for event in events if event['event'] == 'default_pool_lost']
    terminal = events[-1] if events and events[-1]['event'] == 'target_exit' else {}
    waited = terminal.get('child_waited', False)
    timed_out = any(event['event'] == 'timeout' for event in events)
    stage = progress[-1]['stage'] if progress else None
    if losses:
        outcome = 'pool_loss'
    elif timed_out:
        outcome = 'timeout'
    elif returncode or terminal.get('returncode') != 0 or not waited or stage != 'finished':
        outcome = 'failed'
    elif not watched:
        outcome = 'unobserved'
    else:
        outcome = 'passed'
    return dict(outcome=outcome, worker_pid=worker, worker_watched=watched, last_stage=stage,
                watcher_exit=returncode, child_exit=terminal.get('returncode'), child_waited=waited,
                seconds=terminal.get('seconds'), timed_out=timed_out, losses=losses)


def run_attempt(directory, timeout, interval):
    directory.mkdir()
    progress = directory / 'progress.jsonl'
    events = directory / 'watcher.jsonl'
    python = [sys.executable, '-B', '-S']
    command = [*python, str(HERE.with_name('pool_watch_external.py')), '--output', str(events),
               '--timeout', str(timeout), '--interval', str(interval), '--',
               *python, str(HERE), '--worker', str(progress)]
    (directory / 'command.json').write_text(json.dumps(command, indent=2) + '\n', encoding='utf-8')
    with (directory / 'worker.log').open('wb') as stream:
        child = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=False)
    return summarize(child.returncode, read_events(progress), read_events(events))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new directory for attempt logs and summary')
    parser.add_argument('--attempts', type=int, default=64)
    parser.add_argument('--timeout', type=float, default=15.0, help='deadline per attempt in seconds')
    parser.add_argument('--interval', type=float, default=0.005, help='watcher sample delay in seconds')
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('this campaign requires the Windows external watcher')
    if args.worker is not None:
        render_once(args.worker)
        return 0
    if args.output is None or args.attempts < 1:
        parser.error('give --output and a positive number of --attempts')
    if any(not math.isfinite(value) or value <= 0 for value in (args.timeout, args.interval)):
        parser.error('--timeout and --interval must be finite and positive')

    args.output.mkdir()
    results = []
    for attempt in range(1, args.attempts + 1):
        result = run_attempt(args.output / f'{attempt:03d}', args.timeout, args.interval)
        results.append(dict(attempt=attempt, **result))
        if result['outcome'] != 'passed':
            break
    counts = Counter(result['outcome'] for result in results)
    summary = dict(requested=args.attempts, attempts=len(results), counts=dict(counts),
                   timeout=args.timeout, interval=args.interval, results=results)
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if key != 'results'}))
    return 0 if counts['passed'] == args.attempts else 1


if __name__ == '__main__':
    sys.exit(main())
