# SPDX-License-Identifier: AGPL-3.0-only
"""Join immutable qualification inputs and detached promotion evidence.

Read-only by default and in strict mode. Existing validators remain authoritative.
No missing proof is synthesized and no scoped success closes the full inventory.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

try:
    from .compatibility_candidate import scope_digest, validate_candidate
    from .compatibility_conservation import digest
    from .compatibility_execution import validate_execution
    from .compatibility_inventory import ROOT, InventoryError, check, read_json, shape, unique_by
    from .compatibility_qualification import key, validate_selection
    from .qualification_artifact import retained_file, sha, validate_archive
    from .qualification_native import validate_record as validate_native
    from .qualification_epoch import validate_record as validate_epoch
    from .qualification_ci import validate_bundle as validate_ci, POLICY as CI_POLICY, REPOSITORY
    from .native_epoch import EpochError
except ImportError:
    from compatibility_candidate import scope_digest, validate_candidate
    from compatibility_conservation import digest
    from compatibility_execution import validate_execution
    from compatibility_inventory import ROOT, InventoryError, check, read_json, shape, unique_by
    from compatibility_qualification import key, validate_selection
    from qualification_artifact import retained_file, sha, validate_archive
    from qualification_native import validate_record as validate_native
    from qualification_epoch import validate_record as validate_epoch
    from qualification_ci import validate_bundle as validate_ci, POLICY as CI_POLICY, REPOSITORY
    from native_epoch import EpochError

SCHEMA = 'compat/qualification-index.schema.json'
DEFAULT = ROOT / 'compat/candidates/tk-state-resource-1/qualification-subject.json'


def sealed(record):
    return digest({k: v for k, v in record.items() if k != 'manifest_sha256'})


def seal(record):
    record['manifest_sha256'] = sealed(record)
    return record


def references(value):
    if type(value) is dict:
        if set(value) == {'path', 'sha256'}:
            yield value['path'], value['sha256']
        else:
            for item in value.values():
                yield from references(item)
    elif type(value) is list:
        for item in value:
            yield from references(item)


def validate_shape(record, kind, root):
    definitions = read_json(Path(root) / SCHEMA)['$defs']
    shape(record, definitions[kind], definitions)


def original_path(root, workspace, name):
    """Resolve a recorded absolute cleanup path without requiring its old drive."""
    factory = PureWindowsPath if PureWindowsPath(workspace).drive else PurePosixPath
    base, target = factory(workspace), factory(name)
    check(base.is_absolute() and '..' not in target.parts and target.is_relative_to(base),
          'retention path leaves original workspace')
    relative = target.relative_to(base)
    resolved = (Path(root) / Path(*relative.parts)).resolve()
    check(resolved.is_relative_to(Path(root).resolve()), 'retention path alias leaves workspace')
    return resolved


def validate_retention(record, root=ROOT):
    root = Path(root)
    validate_shape(record, 'retention', root)
    read = lambda ref: read_json(retained_file(root, ref))
    terminal, plan, applied = read(record['terminal']), read(record['plan']), read(record['applied'])
    check(plan['kind'] == 'build-hygiene-cleanup-plan' and plan['schema'] == terminal['schema'] == 1,
          'wrong retention protocol')
    check(plan['manifest_sha256'] == record['terminal']['sha256'], 'cleanup plan uses another terminal manifest')
    check(plan['policy_sha256'] == record['policy']['sha256']
          and plan['registry_sha256'] == record['registry']['sha256'], 'cleanup policy/registry identity differs')
    retained_file(root, record['policy'])
    retained_file(root, record['registry'])
    check(terminal['state'] in ('succeeded', 'failed', 'cancelled')
          and type(terminal['process_exit']) is int and terminal['child_waited'] is True,
          'retention child not terminal/awaited')
    check(terminal['state'] != 'succeeded' or terminal['process_exit'] == 0, 'retention success has failed exit')
    check((plan['run_id'], plan['owner']) == (terminal['run_id'], terminal['owner']), 'cleanup owner/run differs')
    check(type(terminal['run_id']) is str and re.fullmatch(r'[a-z0-9][a-z0-9._-]*', terminal['run_id'])
          and terminal['run_id'] not in ('.', '..'), 'cleanup run ID is not canonical')
    check(original_path(root, plan['workspace'], plan['manifest']) == retained_file(root, record['terminal']),
          'cleanup plan names another terminal manifest')
    scratch = root / 'build/work' / terminal['run_id']
    check(terminal['scratch_root'] == 'build/work/' + terminal['run_id']
          and original_path(root, plan['workspace'], plan['scratch_root']) == scratch.resolve(), 'cleanup scratch scope differs')
    check(not scratch.exists(), 'cleanup scratch still exists')
    check(type(applied['actual_exit']) is int and applied['actual_exit'] == 0 and applied['child_waited'] is True,
          'cleanup apply failed/unawaited')
    result = applied['result']
    check(result['status'] == 'PASS_APPLY' and type(result['deleted']) is int
          and result['deleted'] == len(plan['snapshot']['files']), 'cleanup was not completely applied')
    check(original_path(root, plan['workspace'], result['scratch_root']) == scratch.resolve(), 'cleanup result scope differs')
    command = applied['command']
    check(type(command) is list and command.count('--plan') == 1 and 'apply' in command, 'cleanup apply command absent')
    index = command.index('--plan')
    check(index + 1 < len(command)
          and original_path(root, plan['workspace'], command[index + 1]) == retained_file(root, record['plan']),
          'cleanup applied another plan')
    original = unique_by(terminal['retained'], lambda ref: ref['path'], 'terminal retained file')
    planned = unique_by(plan['retained'], lambda ref: str(original_path(root, plan['workspace'], ref['path'])), 'planned retained file')
    check(len(original) == len(planned) == result['retained_verified'], 'retained cleanup inventory differs')
    roles = set()
    covered = set()
    for name, ref in original.items():
        # Managed terminals may retain original absolute paths. Project those
        # through the recorded workspace before applying the ordinary relative
        # evidence verifier; never rewrite the original cleanup records.
        if PureWindowsPath(name).is_absolute() or PurePosixPath(name).is_absolute():
            projected = original_path(root, plan['workspace'], name)
            relative = projected.relative_to(root.resolve()).as_posix()
        else:
            relative = name
        file = retained_file(root, {'path': relative, 'sha256': ref['sha256']})
        expected = planned.get(str(file))
        check(expected and expected['sha256'] == ref['sha256'] and expected['roles'] == ref['roles'],
              'cleanup retained roles/bytes changed')
        roles.update(ref['roles'])
        covered.add((relative, ref['sha256']))
    check({'source', 'evidence', 'licenses'} | ({'repro'} if terminal['state'] != 'succeeded' else set()) <= roles,
          'retained source/evidence/license/reproducer role missing')
    return covered


def validate_attempts(attempts, selected, root, history=None, profile=None, wheel=None):
    """Keep failures and select only the newest successful terminal attempt."""
    unique_by(attempts, lambda a: a['id'], 'qualification attempt')
    sequences = [a['sequence'] for a in attempts]
    check(sequences == sorted(set(sequences)), 'qualification attempts unordered/duplicated')
    if history is not None:
        check(set(history) == {'schema', 'kind', 'profile', 'wheel_sha256', 'attempts'}
              and type(history['schema']) is int and history['schema'] == 1
              and history['kind'] == 'workflow-attempt-history' and history['profile'] == profile,
              'wrong attempt history contract/profile')
        check(wheel is None or history['wheel_sha256'] == wheel, 'attempt history belongs to another wheel')
        check(history['attempts'] == [{k: a[k] for k in ('id', 'sequence', 'outcome', 'report')} for a in attempts],
              'attempt list omitted/changed original history')
    for attempt in attempts:
        raw = read_json(retained_file(root, attempt['report']))
        check(type(raw.get('process_exit')) is int and raw.get('child_waited') is True,
              'qualification attempt has no actual terminal exit/wait')
        passed = raw.get('status') == 'PASS_ALL_NO_OPENGL_GATES'
        check(passed == (attempt['outcome'] == 'passed'), 'attempt outcome disagrees with original report')
        if attempt['resolution'] is not None:
            resolution = read_json(retained_file(root, attempt['resolution']))
            validate_shape(resolution, 'attempt-resolution', root)
            check(resolution['attempt_sha256'] == digest({k: attempt[k] for k in ('id', 'sequence', 'outcome', 'report')})
                  and resolution['profile'] == profile
                  and (wheel is None or resolution['wheel_sha256'] == wheel),
                  'failure resolution belongs to another attempt/profile/wheel')
        if attempt['retention'] is not None:
            covered = validate_retention(read_json(retained_file(root, attempt['retention'])), root)
            check((attempt['report']['path'], attempt['report']['sha256']) in covered, 'attempt report not retained by its cleanup')
    if selected is None:
        return None
    check(attempts and attempts[-1]['id'] == selected and attempts[-1]['outcome'] == 'passed',
          'selected attempt is not latest success; later failure cannot be hidden')
    return attempts[-1]


def validate_subject(subject, root=ROOT):
    root = Path(root)
    validate_shape(subject, 'subject', root)
    check(subject['manifest_sha256'] == sealed(subject), 'qualification subject seal changed')
    read = lambda ref: read_json(retained_file(root, ref))
    candidate = read(subject['candidate'])
    validate_candidate(candidate, root)
    selection = read(subject['selection'])
    state = validate_selection(selection, root)
    execution = read(subject['execution'])
    validate_execution(execution, root)
    check(selection['candidate']['scope_sha256'] == scope_digest(candidate)
          and selection['execution_map']['scope_sha256'] == execution['manifest_sha256'], 'subject scope joins differ')
    check(subject['candidate']['path'] == execution['candidate']['path']
          and subject['execution']['path'] == selection['execution_map']['path'], 'subject declaration paths differ')
    check(subject['ledger']['path'] == execution['execution']['path'], 'subject uses another execution ledger')
    ledger = read(subject['ledger'])
    check(subject['product_source_commit'] == candidate['product_source_commit'], 'subject product source changed')
    closure = selection['closure']
    profiles = unique_by(subject['profiles'], lambda p: p['profile'], 'subject profile')
    check(set(profiles) == {c['profile'] for c in closure}, 'subject omitted/added selected profile')
    rows = {(r['feature'], r['profile']): r for r in ledger['rows']}
    proved, missing, blocked = [], [], []
    for profile, entry in profiles.items():
        obligations = [item for item in closure if item['profile'] == profile]
        reasons = []
        retained = set()
        if subject['qualification_head'] is None:
            reasons.append('frozen qualification implementation head')
        if not state['reviewed']:
            reasons.append('source/scope/admission-selection review')
        archive = producer = None
        if entry['archive'] is None:
            reasons.append('exact archive')
        else:
            archive_record = read(entry['archive'])
            check(archive_record['candidate']['scope_sha256'] == scope_digest(candidate)
                  and archive_record['profile'] == profile, 'archive belongs to another subject/profile')
            archive = validate_archive(archive_record, root)
        if entry['producer'] is None:
            reasons.append('native producer')
        else:
            producer_record = read(entry['producer'])
            check(producer_record['candidate'] == subject['candidate']
                  and producer_record['reuse']['profile'] == profile, 'producer belongs to another candidate/profile')
            validator = validate_epoch if producer_record['kind'] == 'original-native-epoch-reuse' else validate_native
            producer = validator(producer_record, root)
        if archive and producer:
            hashes = producer['native_output_hashes']
            check(all(archive['package_hashes'].get(name) == value for name, value in hashes.items()),
                  'wheel native members differ from admitted producer outputs')
        if entry['attempt_history'] is None:
            reasons.append('complete workflow attempt history')
            history = None
        else:
            history = read(entry['attempt_history'])
        attempt = validate_attempts(entry['attempts'], entry['selected_attempt'], root, history,
                                    profile, archive['wheel_sha256'] if archive else None)
        if any(a['retention'] is None for a in entry['attempts']):
            reasons.append('terminal retention for every attempt')
        if any(a['outcome'] != 'passed' and a['resolution'] is None for a in entry['attempts']):
            reasons.append('reviewed failure/cancellation resolution')
        if attempt is None:
            reasons.append('installed observer attempt')
        elif attempt['retention'] is None:
            reasons.append('attempt terminal retention')
        else:
            retained.update(validate_retention(read(attempt['retention']), root))
            if entry['attempt_history'] is not None:
                check(tuple(entry['attempt_history'][k] for k in ('path', 'sha256')) in retained,
                      'attempt history not retained by cleanup')
        if entry['producer_retention'] is None:
            reasons.append('producer terminal retention')
        else:
            covered = validate_retention(read(entry['producer_retention']), root)
            retained.update(covered)
            if entry['producer'] is not None:
                check((entry['producer']['path'], entry['producer']['sha256']) in covered,
                      'producer proof not retained by cleanup')
        if archive and producer and attempt and not reasons:
            required = set(references(archive_record)) | set(references(producer_record))
            if producer_record['kind'] == 'original-linux-ci-native-reuse':
                # The wrapper points into an original, immutable CI capture.
                # Retain every raw input, not only that wrapper's JSON bytes.
                required.update(references(read(producer_record['capture'])))
            # Current frozen declarations are retained by the subject itself;
            # artifacts and raw proof must survive their contributing run.
            declarations = set(references({k: subject[k] for k in ('candidate', 'selection', 'execution', 'ledger')}))
            check(required - declarations <= retained, 'artifact/native proof has unretained inputs')
        for obligation in obligations:
            row = rows[(obligation['feature'], profile)]
            row_reasons = list(reasons)
            if row['state'] != 'qualified':
                row_reasons.append('qualified installed row')
            else:
                if archive is not None:
                    check(row['identity']['wheel_sha256'] == archive['wheel_sha256'],
                          'installed row wheel differs from archive')
                receipt = read(row['receipt'])
                # Existing inventory validation already replays all original gate
                # joins; additionally bind them to the selected terminal attempt.
                gate = read(receipt['gates']['execution-api'])
                if attempt is not None:
                    check(gate['raw_reports']['runtime'] == attempt['report'],
                          'installed gate is not the selected original attempt')
                if not row_reasons:
                    check(set(references(receipt)) | {tuple(row['receipt'][k] for k in ('path', 'sha256'))} <= retained,
                          'installed receipt/gates/tests have unretained inputs')
                    check(set(references(gate['raw_reports'])) <= retained, 'original observer reports have unretained inputs')
            if row_reasons:
                item = {'criterion': obligation, 'reasons': row_reasons}
                (blocked if row['state'] == 'blocked-external' else missing).append(item)
            else:
                proved.append(obligation)
    return {'status': 'VALID_QUALIFICATION_SUBJECT', 'subject_sha256': subject['manifest_sha256'],
            'requested': selection['requested'], 'closure': closure, 'proved': proved,
            'blocked': blocked, 'missing': missing, 'subject_proved': not missing and not blocked,
            'admitted': False, 'candidate_complete': False, 'full_inventory_complete': False, 'release_complete': False}


def validate_envelope(envelope, root=ROOT, strict=False):
    root = Path(root)
    validate_shape(envelope, 'envelope', root)
    read = lambda ref: read_json(retained_file(root, ref))
    subject = read(envelope['subject'])
    result = validate_subject(subject, root)
    basis = read(envelope['basis'])
    validate_shape(basis, 'basis', root)
    check(basis['manifest_sha256'] == sealed(basis), 'promotion basis changed')
    check(basis['subject'] == envelope['subject'] and basis['repository'] == REPOSITORY,
          'promotion basis subject/repository differs')
    check(basis['qualification_head'] == subject['qualification_head'], 'promotion head differs from frozen subject')
    check(basis['policy']['sha256'] == sha((root / CI_POLICY).read_bytes()), 'promotion CI policy changed')
    retained_file(root, basis['policy'])
    ci = validate_ci(read(basis['ci']), root)
    check(ci['qualification_head'] == basis['qualification_head'], 'promotion CI belongs to another head')
    impact = read(basis['impact'])
    review = read(envelope['review'])
    validate_shape(impact, 'impact-review', root)
    validate_shape(review, 'promotion-review', root)
    for record, kind in ((impact, 'change-impact'), (review, 'promotion')):
        check(record.get('schema') == 1 and record.get('kind') == kind and record.get('status') == 'APPROVED'
              and record.get('independent') is True and type(record.get('reviewer')) is str and record['reviewer'].strip(),
              'missing independent promotion/impact approval')
    check(impact.get('subject_sha256') == subject['manifest_sha256']
          and impact.get('qualification_head') == basis['qualification_head'], 'impact approval for another subject/head')
    check(review.get('promotion_basis_sha256') == basis['manifest_sha256'], 'final review belongs to another promotion basis')
    result['admitted'] = result['subject_proved']
    result['status'] = 'SCOPED_ADMISSION_PASS' if result['admitted'] else 'SCOPED_ADMISSION_INCOMPLETE'
    check(not strict or result['admitted'], 'strict admission has missing/blocked selected obligations')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--subject', type=Path, default=DEFAULT)
    parser.add_argument('--envelope', type=Path)
    parser.add_argument('--require-admitted', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.envelope:
            result = validate_envelope(read_json(args.envelope), args.root, args.require_admitted)
        else:
            result = validate_subject(read_json(args.subject), args.root)
            check(not args.require_admitted, 'strict admission requires detached promotion envelope and current CI')
    except (InventoryError, EpochError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
