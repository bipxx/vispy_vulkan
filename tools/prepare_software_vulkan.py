# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare retained software Vulkan inputs in registered scratch, without installation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

try:
    from .build_hygiene import no_alias, RUN_ID
except ImportError:
    from build_hygiene import no_alias, RUN_ID

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / 'compat/software-vulkan-driver.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def select_members(stream, wanted):
    """Read regular, explicitly named members; never extract archive paths or links."""
    found = {}
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            if member.name not in wanted:
                continue
            if member.name in found or not member.isfile() or member.size > 128 * 1024 * 1024:
                raise ValueError('duplicate, nonregular or oversized selected member: ' + member.name)
            found[member.name] = archive.extractfile(member).read()
    if set(found) != set(wanted):
        raise ValueError('missing selected package members: ' + str(set(wanted) - set(found)))
    return found


def retained_inputs(pin, artifacts):
    result = {}
    for item in pin['inputs']:
        name = item['name']
        if Path(name).name != name or name in result:
            raise ValueError('invalid or duplicate input name')
        path = no_alias((artifacts / item['sha256'] / name).absolute())
        if path.stat().st_size != item['size'] or digest(path) != item['sha256']:
            raise ValueError('retained package/source identity changed: ' + name)
        result[name] = path
    return result


def prepare(run_id, owner, output, artifacts=ROOT / 'build/artifacts'):
    if sys.platform != 'linux':
        raise ValueError('run preparation with Linux Python; no host package installation is performed')
    if not RUN_ID.fullmatch(run_id):
        raise ValueError('invalid run ID')
    scratch = no_alias(ROOT / 'build/work' / run_id)
    marker = json.loads(no_alias(scratch / '.build-hygiene-owner.json').read_bytes())
    if marker != {'schema': 1, 'run_id': run_id, 'owner': owner}:
        raise ValueError('scratch ownership does not match the registered run')
    output = no_alias(Path(output).absolute())
    if output.resolve().is_relative_to((ROOT / 'build/work').resolve()) or output.exists():
        raise ValueError('preparation record must be new and outside all scratch')
    pin = json.loads(PIN.read_bytes())
    inputs = retained_inputs(pin, Path(artifacts))
    destination = scratch / 'software-vulkan'
    destination.mkdir()  # Exclusive: never adopt another run's prepared directory.
    record = {'scope': 'isolated driver preparation; not qualification', 'qualified': False,
              'pin_sha256': digest(PIN), 'run_id': run_id, 'owner': owner,
              'inputs': [{'path': str(inputs[x['name']]), 'sha256': x['sha256'], 'roles': x['roles']}
                         for x in pin['inputs']], 'libraries': [], 'commands': [], 'notices': []}
    for item in pin['libraries']:
        command = ['dpkg-deb', '--fsys-tarfile', str(inputs[item['package']])]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
            try:
                members = select_members(child.stdout, {item['member'], item['notice']})
            finally:
                # Drain on parser failure, then actually reap this exact child.
                child.stdout.read()
                errors = child.stderr.read().decode(errors='replace')
                code = child.wait()
                record['commands'].append({'argv': command, 'actual_exit': code,
                                           'child_waited': True, 'child_pid': child.pid, 'stderr': errors})
        if code:
            raise RuntimeError('dpkg-deb failed: ' + errors)
        data = members[item['member']]
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('selected library differs from tested input: ' + item['filename'])
        library = destination / item['filename']
        with library.open('xb') as stream:
            stream.write(data)
        notice = output.with_name(output.stem + '-' + item['filename'] + '-copyright')
        with notice.open('xb') as stream:
            stream.write(members[item['notice']])
        record['libraries'].append({'path': str(library), 'sha256': digest(library)})
        record['notices'].append({'path': str(notice), 'sha256': digest(notice)})
    icd = destination / 'lvp_icd.json'
    icd.write_text(json.dumps({'file_format_version': '1.0.0', 'ICD': {
        'api_version': '1.3.0', 'library_path': str(destination / 'libvulkan_lvp.so')}}, indent=2) + '\n')
    record['icd'] = {'path': str(icd), 'sha256': digest(icd)}
    record['environment'] = {'VK_DRIVER_FILES': str(icd), 'LD_LIBRARY_PATH': str(destination)}
    record['dependency_scope'] = 'Only these two libraries are supplied; actual loaded system dependencies must be observed by the workflow.'
    with output.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    record = prepare(args.run_id, args.owner, args.output)
    print(json.dumps({'status': 'PREPARED_NOT_QUALIFIED', 'environment': record['environment']}))


if __name__ == '__main__':
    main()
