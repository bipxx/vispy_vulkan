# SPDX-License-Identifier: AGPL-3.0-only
"""Run the CPU contract workflow's test commands locally and concurrently, as a faster pre-publication check.

The commands are those of .github/workflows/cpu-contract.yml that run `qualification_gate.py pytest` or a
`tools/compatibility_*.py` validator, one per line. `tools/qualification_ci.py --capture` is left out: it records the
GitHub job identity. Each command runs in its own process with CI's environment (PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONPATH=src, no bytecode), and pytest gets `-p no:cacheprovider`. A pytest command naming more test files than
--files-per-shard is split into shards. Each shard is its own gate invocation with its own evidence, so it keeps the
gate's checks: exit 0, a non-empty collection, nothing skipped, and every collected case passing. A shard holds fewer
modules in one process than CI does, which CI's single-process run already covers.

This checks the local tree, which has local-only files. A test that lists a directory must also hold on the published
tree (consolidated plan, Standing rules).
Usage: tools/ci_local.py --evidence <new directory> [--jobs N] [--files-per-shard N]
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/cpu-contract.yml'
TEST_FILE = re.compile(r'\.py(::\S+)?$')


def listed_files(tokens):
    """The test files of a gate pytest command: its `.py` arguments after `--` (tests/ and src/vispy/**/tests/)."""
    return [token for token in tokens[tokens.index('--') + 1:] if TEST_FILE.search(token)] if '--' in tokens else []


def commands(workflow_text, evidence):
    """The workflow's local test commands, as argument lists after the interpreter."""
    found = []
    for line in workflow_text.splitlines():
        line = line.strip()
        if not line.startswith('"$CI_PYTHON"') or 'tools/qualification_ci.py' in line:
            continue
        if 'qualification_gate.py pytest' not in line and 'tools/compatibility_' not in line:
            continue
        tokens = shlex.split(line.replace('$EVIDENCE', evidence))[1:]
        if 'pytest' in tokens and '-p' not in tokens:
            tokens[tokens.index('--') + 1:tokens.index('--') + 1] = ['-p', 'no:cacheprovider']
        found.append(tokens)
    return found


def shard(tokens, files_per_shard):
    """Split a gate pytest command into commands of at most files_per_shard test files, each with its own evidence."""
    if 'pytest' not in tokens or files_per_shard < 1:
        return [tokens]
    files = listed_files(tokens)
    if len(files) <= files_per_shard:
        return [tokens]
    output, separator = tokens[tokens.index('--output') + 1], tokens.index('--')
    shards = []
    for index in range(0, len(files), files_per_shard):
        chosen, suffix = set(files[index:index + files_per_shard]), '-shard%d' % (index // files_per_shard + 1)
        part = []
        for position, token in enumerate(tokens):
            if position > separator and token in files and token not in chosen:
                continue
            if token == output:
                token = re.sub(r'(\.json)$', suffix + r'\1', token)
            elif token.startswith('--junitxml='):
                token = re.sub(r'(\.xml)$', suffix + r'\1', token)
            part.append(token)
        shards.append(part)
    return shards


def run(tokens, environment):
    began = time.monotonic()
    child = subprocess.Popen([sys.executable, *tokens], cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    output, _ = child.communicate()
    last = next((text for text in reversed(output.splitlines()) if text.strip()), '')
    return {'argv': tokens, 'actual_exit': child.returncode, 'child_waited': True,
            'seconds': round(time.monotonic() - began, 1), 'last_line': last, 'output': output}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument('--files-per-shard', type=int, default=5)
    options = parser.parse_args()
    options.evidence.mkdir(parents=True)
    environment = {**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONPATH': str(ROOT / 'src'),
                   'PYTHONDONTWRITEBYTECODE': '1'}
    work = [part for tokens in commands(WORKFLOW.read_text(encoding='utf-8'), options.evidence.resolve().as_posix())
            for part in shard(tokens, options.files_per_shard)]
    began = time.monotonic()
    with ThreadPoolExecutor(options.jobs) as pool:
        results = list(pool.map(lambda tokens: run(tokens, environment), work))
    with (options.evidence / 'ci-local.log').open('x', encoding='utf-8') as log:
        for result in results:
            log.write('$ %s\n%s\n[exit %d]\n\n' % (shlex.join(result['argv']), result.pop('output'),
                                                   result['actual_exit']))
    passed = all(result['actual_exit'] == 0 for result in results)
    summary = {'all_passed': passed, 'commands': len(work), 'jobs': options.jobs,
               'files_per_shard': options.files_per_shard, 'wall_seconds': round(time.monotonic() - began, 1),
               'results': results}
    with (options.evidence / 'ci-local.json').open('x', encoding='utf-8') as output:
        output.write(json.dumps(summary, indent=2) + '\n')
    for result in results:
        print(result['actual_exit'], '%6.1fs' % result['seconds'], result['last_line'][:100])
    print('ALL PASSED' if passed else 'FAILURES', 'in', summary['wall_seconds'], 's')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
