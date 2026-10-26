# SPDX-License-Identifier: AGPL-3.0-only
"""Capture CI checkout identity and validate the original required-job evidence.

Passing CI is one prerequisite, never artifact or hardware admission. Original
API exports and job reports must be retained; validation performs no network IO.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

try:
    from .compatibility_inventory import ROOT, InventoryError, check, file_ref, read_json, shape, unique_by
except ImportError:
    from compatibility_inventory import ROOT, InventoryError, check, file_ref, read_json, shape, unique_by

POLICY = 'compat/qualification-ci.json'
SCHEMA = 'compat/qualification-ci.schema.json'
REPOSITORY = 'bipxx/vispy_vulkan'
CPU = '.github/workflows/cpu-contract.yml'
LINUX = '.github/workflows/linux-vulkan.yml'
METAL = '.github/workflows/metal-wheel.yml'
PYTHONS = ('3.10.19', '3.11.14', '3.12.8', '3.13.8', '3.14.0')
TARGETS = ('windows-x86_64', 'linux-x86_64', 'macos-arm64', 'macos-x86_64')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(root=ROOT):
    root = Path(root)
    cpu = (root / CPU).read_text(encoding='utf-8')
    match = re.search(r'^        python: (\[.*\])$', cpu, re.M)
    check(match and tuple(ast.literal_eval(match[1])) == PYTHONS, 'CPU Python matrix changed; review CI policy')
    check(tuple(re.findall(r'^          - \{name: ([^,]+),', cpu, re.M)) == TARGETS,
          'CPU target matrix changed; review CI policy')
    check('name: CPU ${{ matrix.target.name }} CPython ${{ matrix.python }}' in cpu,
          'CPU job naming changed; review CI policy')
    metal = (root / METAL).read_text(encoding='utf-8')
    check(tuple(re.findall(r'^          - \{arch: ([^,]+),', metal, re.M)) == ('arm64', 'x86_64'),
          'Metal matrix changed; review CI policy')
    check('name: Metal wheel ${{ matrix.arch }} CPython 3.12.8' in metal,
          'Metal job naming changed; review CI policy')
    check('\n  cpu:\n' in cpu and '\n  build:\n' in metal
          and '\n  software-vulkan:\n' in (root / LINUX).read_text(encoding='utf-8'),
          'CI workflow job key changed; review CI policy')
    return {CPU: ('cpu', sorted(f'CPU {target} CPython {python}' for target in TARGETS for python in PYTHONS)),
            LINUX: ('software-vulkan', ['software-vulkan']),
            METAL: ('build', ['Metal wheel arm64 CPython 3.12.8', 'Metal wheel x86_64 CPython 3.12.8'])}


def validate_shape(record, kind, root=ROOT):
    definitions = read_json(Path(root) / SCHEMA)['$defs']
    shape(record, definitions[kind], definitions)


def validate_policy(root=ROOT):
    root = Path(root)
    policy = read_json(root / POLICY)
    validate_shape(policy, 'policy', root)
    workflows = unique_by(policy['workflows'], lambda w: w['path'], 'CI policy workflow')
    expected = contract(root)
    check(set(workflows) == set(expected), 'required CI workflow set changed')
    for path, (job_key, jobs) in expected.items():
        workflow = workflows[path]
        check(workflow['job_key'] == job_key and workflow['jobs'] == jobs, 'required CI job set changed')
        check(workflow['sha256'] == sha(root / path), 'CI workflow bytes changed')
    check(policy['collector_sha256'] == sha(root / 'tools/qualification_ci.py'), 'CI identity collector changed')
    return policy


def validate_attempts(bundle, policy, attempts, history, root=ROOT):
    """Pure semantic join; attempts carry already hash-checked original exports.

    An attempt is (entry, raw GitHub run object, paginated complete jobs object,
    job-ID-to-original-checkout-report map). Do not replace these with summaries.
    """
    validate_shape(bundle, 'bundle', root)
    check(bundle['repository'] == policy['repository'] == REPOSITORY, 'wrong CI repository')
    check(bundle['policy_sha256'] == sha(Path(root) / POLICY), 'wrong/reduced CI policy')
    check(len(attempts) == len(bundle['runs']), 'missing original CI attempt')
    workflows = {w['path']: w for w in policy['workflows']}
    check(type(history['total_count']) is int and history['total_count'] == len(history['workflow_runs']),
          'incomplete/paginated CI run history')
    history_runs = unique_by(history['workflow_runs'], lambda r: r['id'], 'CI history run')
    required_attempts = set()
    for run_id, run in history_runs.items():
        check(type(run_id) is int and run_id > 0 and type(run['run_attempt']) is int and run['run_attempt'] > 0,
              'invalid CI history run/attempt')
        check(run['head_sha'] == bundle['qualification_head'] and run['repository']['full_name'] == REPOSITORY,
              'wrong CI history head/repository')
        if run['path'] in workflows:
            required_attempts.update((run_id, attempt) for attempt in range(1, run['run_attempt'] + 1))
    groups = {path: [] for path in workflows}
    seen, job_ids = set(), set()
    for entry, run, jobs, identities in attempts:
        path = entry['workflow']
        check(path in groups, 'unexpected CI workflow')
        marker = entry['run_id'], entry['attempt']
        check(marker not in seen, 'duplicate CI attempt')
        seen.add(marker)
        check(type(run['id']) is int and type(run['run_attempt']) is int
              and run['id'] == entry['run_id'] and run['run_attempt'] == entry['attempt'], 'wrong run/attempt')
        check(entry['run_id'] in history_runs, 'CI run omitted from authoritative history')
        latest = history_runs[entry['run_id']]
        if entry['attempt'] == latest['run_attempt']:
            check(all(run[field] == latest[field] for field in ('path', 'head_sha', 'status', 'conclusion')),
                  'latest run differs from CI history')
        check(run['repository']['full_name'] == REPOSITORY and run['head_repository']['full_name'] == REPOSITORY,
              'wrong original CI repository')
        check(run['path'] == path and run['head_sha'] == bundle['qualification_head'], 'wrong CI workflow/head')
        check(run['status'] == 'completed' and isinstance(run['conclusion'], str) and run['conclusion'],
              'CI attempt has not terminated')
        check(type(jobs['total_count']) is int and jobs['total_count'] == len(jobs['jobs']), 'incomplete/paginated CI jobs')
        unique_by(jobs['jobs'], lambda j: j['id'], 'original CI job ID')
        for job in jobs['jobs']:
            check(type(job['id']) is int and job['id'] > 0
                  and type(job['run_id']) is int and job['run_id'] == entry['run_id']
                  and type(job['run_attempt']) is int and job['run_attempt'] == entry['attempt']
                  and job['head_sha'] == bundle['qualification_head'], 'wrong original CI attempt job')
            check(job['status'] == 'completed' and isinstance(job['conclusion'], str) and job['conclusion'],
                  'original CI job has not terminated')
        groups[path].append((entry, run, jobs, identities))
    check(seen == required_attempts, 'missing/newer CI attempt omitted from history join')
    selected = []
    for path, history in groups.items():
        check(history, 'missing required CI workflow: ' + path)
        # Greatest run ID, then greatest attempt. Preserve older failed attempts
        # as original inputs; a rerun must contain the complete required matrix.
        entry, run, jobs, identities = max(history, key=lambda a: (a[0]['run_id'], a[0]['attempt']))
        check(run['status'] == 'completed' and run['conclusion'] == 'success', 'latest CI attempt is not successful')
        by_name = unique_by(jobs['jobs'], lambda j: j['name'], 'CI job name')
        check(set(by_name) == set(workflows[path]['jobs']), 'missing/unexpected required CI job')
        check(set(identities) == {j['id'] for j in by_name.values()}, 'missing/substituted checkout identity')
        for name, job in by_name.items():
            check(type(job['id']) is int and job['id'] > 0 and job['id'] not in job_ids, 'duplicate/invalid CI job ID')
            job_ids.add(job['id'])
            check(type(job['run_id']) is int and type(job['run_attempt']) is int
                  and job['run_id'] == entry['run_id'] and job['run_attempt'] == entry['attempt'], 'mixed CI job attempts')
            check(job['head_sha'] == bundle['qualification_head'], 'wrong original CI job head')
            check(job['status'] == 'completed' and job['conclusion'] == 'success', 'required CI job did not succeed')
            identity = identities[job['id']]
            validate_shape(identity, 'identity', root)
            check(identity['repository'] == REPOSITORY and identity['run_id'] == entry['run_id']
                  and identity['attempt'] == entry['attempt'] and identity['job_name'] == name
                  and identity['job_key'] == workflows[path]['job_key'], 'wrong CI checkout producer')
            check(identity['source_head'] == bundle['qualification_head'], 'wrong CI source head')
            check(identity['event'] == run['event'], 'wrong CI event')
            if identity['event'] == 'pull_request':
                check(identity['checked_head'] == identity['source_head']
                      or identity['source_head'] in identity['parents'], 'PR merge checkout lacks source head')
            else:
                check(identity['checked_head'] == identity['source_head'], 'non-PR checkout differs from source head')
            check(identity['workflow'] == {'path': path, 'sha256': workflows[path]['sha256']}
                  and identity['collector_sha256'] == policy['collector_sha256'], 'stale CI workflow/collector')
            selected.append({'workflow': path, 'job': name, 'job_id': job['id'], 'run_id': entry['run_id'],
                             'attempt': entry['attempt'], 'checked_head': identity['checked_head']})
    return {'status': 'PASS_REQUIRED_CI_JOIN', 'qualification_head': bundle['qualification_head'],
            'jobs': selected, 'artifact_admitted': False, 'hardware_qualified': False}


def validate_bundle(bundle, root=ROOT):
    validate_shape(bundle, 'bundle', root)
    policy = validate_policy(root)
    attempts = []
    for entry in bundle['runs']:
        identities = unique_by(entry['identities'], lambda i: i['job_id'], 'CI identity job')
        attempts.append((entry, read_json(file_ref(root, entry['run'])), read_json(file_ref(root, entry['jobs'])),
                         {key: read_json(file_ref(root, ref['report'])) for key, ref in identities.items()}))
    return validate_attempts(bundle, policy, attempts, read_json(file_ref(root, bundle['run_history'])), root)


def capture(workflow, name, output, root=ROOT):
    root = Path(root)
    policy = validate_policy(root)
    declarations = {w['path']: w for w in policy['workflows']}
    check(workflow in declarations and name in declarations[workflow]['jobs'], 'unknown CI identity job')
    event = read_json(os.environ['GITHUB_EVENT_PATH'])
    event_name = os.environ['GITHUB_EVENT_NAME']
    checked = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    source = event['pull_request']['head']['sha'] if event_name == 'pull_request' else os.environ['GITHUB_SHA']
    commit = subprocess.check_output(['git', 'cat-file', '-p', 'HEAD'], cwd=root, text=True)
    parents = re.findall(r'^parent ([0-9a-f]{40})$', commit.split('\n\n', 1)[0], re.M)
    record = {'schema': 1, 'kind': 'ci-job-identity', 'repository': os.environ['GITHUB_REPOSITORY'],
              'run_id': int(os.environ['GITHUB_RUN_ID']), 'attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
              'job_key': os.environ['GITHUB_JOB'], 'job_name': name, 'event': event_name,
              'source_head': source, 'checked_head': checked, 'parents': parents,
              'workflow': {'path': workflow, 'sha256': sha(root / workflow)},
              'collector_sha256': sha(root / 'tools/qualification_ci.py')}
    validate_shape(record, 'identity', root)
    target = Path(output)
    check(not target.exists(), 'CI identity output already exists')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write((json.dumps(record, indent=2) + '\n').encode())
    return {'status': 'CAPTURED_CI_CHECKOUT', 'source_head': source, 'checked_head': checked}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--workflow')
    parser.add_argument('--job-name')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    try:
        if args.capture:
            check(args.workflow and args.job_name and args.output and not args.bundle, 'capture requires workflow/job/output')
            result = capture(args.workflow, args.job_name, args.output, args.root)
        else:
            check(not (args.workflow or args.job_name or args.output), 'capture options require --capture')
            result = validate_bundle(read_json(args.bundle), args.root) if args.bundle else {
                'status': 'VALID_REQUIRED_CI_POLICY', 'required_jobs': sum(len(w['jobs']) for w in validate_policy(args.root)['workflows']),
                'artifact_admitted': False, 'hardware_qualified': False}
    except (InventoryError, OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
