# SPDX-License-Identifier: AGPL-3.0-only
"""Print the host GL sources of hot-swap audit reports: the top-level package behind each host GL event.

D28 adoption checks compare these before and after a host release (consolidated plan; plan
2026-10-31-upstream-host-changes.md, Tasks 9 and 10). An event with no Python stack counts as 'native', and a host
event whose stored stack holds no caller as 'host (stack truncated)'.
Usage (repository root): python -m tools.hot_swap.host_sources <audit.json> [<audit.json> ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.hot_swap.policy import host_gl_sources


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('reports', nargs='+', type=Path, help='tools/audit_hot_swap.py --output files')
    options = parser.parse_args(argv)
    for path in options.reports:
        events = json.loads(path.read_text(encoding='utf-8'))['gates']['host_gl_events']
        print(f'== {path}')
        for source, count in sorted(host_gl_sources(events).items()):
            print(f'{source}\t{count}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
