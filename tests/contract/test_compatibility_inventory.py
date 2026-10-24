# SPDX-License-Identifier: AGPL-3.0-only
"""CPU-only negative controls for ledger identity and promotion boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from tools import compatibility_inventory as inventory
from tools.generate_compatibility_catalog import exports, generate
from tools.migrate_compatibility_inventory import main as migrate_main, migrate_v1


ROOT = Path(__file__).resolve().parents[2]


def write_json(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def example(tmp_path):
    ledger = inventory.read_json(ROOT / 'compat/vispy-compatibility.json')
    feature = deepcopy(next(f for f in ledger['features'] if f['id'] == 'app.canvas'))
    row = deepcopy(next(r for r in ledger['rows'] if r['feature'] == feature['id']))
    ledger['features'], ledger['rows'] = [feature], [row]
    ledger['applicability'] = [deepcopy(a) for a in ledger['applicability'] if a['feature'] == feature['id']]
    ledger['applicability'][0]['reviewed'] = True  # Synthetic scope reviewed by this fixture only.
    # Tiny synthetic receipt fixtures test the auditor; they are not GPU proof.
    for name in ('compat/vispy-compatibility.schema.json', 'compat/upstream_manifest.json', inventory.SPEC):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    ledger['related_inventories'] = [write_json(tmp_path, 'compat/reference.json', {'scope': 'unit test'})]
    test_file = tmp_path / 'tests/test_workflow.py'
    test_file.parent.mkdir(parents=True)
    test_file.write_text('def test_ordinary(): pass\ndef test_mutation(): pass\n', encoding='utf-8')
    return tmp_path, ledger


def promote(root, ledger, state='source-tested'):
    profile = ledger['profiles'][0]
    profile.update(admitted=True, environment_sha256='a' * 64)
    row = ledger['rows'][0]
    row.update(state=state, outcome='passed', blocker='No open blocker in this synthetic test.')
    row['fixtures'] = [
        {'nodeid': 'tests/test_workflow.py::test_' + kind, 'kind': kind, 'expected': 'Synthetic successful ' + kind, 'cases': 1}
        for kind in ('ordinary', 'mutation')
    ]
    row['identity'] = {'source_commit': '1' * 40, 'patch_sha256': '2' * 64,
                       'profile_sha256': 'a' * 64, 'wheel_sha256': None if state == 'source-tested' else '3' * 64}
    pytest_output = {'exit_code': 0, 'collected': [f['nodeid'] for f in row['fixtures']],
                     'reports': [{'nodeid': f['nodeid'], 'when': phase, 'outcome': 'passed'}
                                 for f in row['fixtures'] for phase in ('setup', 'call', 'teardown')]}
    receipt = {'schema': 1, 'feature': row['feature'], 'profile': row['profile'],
               'identity': deepcopy(row['identity']), 'phase': state, 'child_waited': True, 'exit_code': 0,
               'requirements': ledger['features'][0]['requirements'],
               'pytest': write_json(root, 'evidence/pytest.json', pytest_output)}
    if state in ('wheel-tested', 'qualified'):
        receipt['installed_origin_verified'] = True
        receipt['distribution_audit'] = write_json(root, 'evidence/distribution.json',
                                                   {'status': 'PASS', 'identity': row['identity']})
    if state == 'qualified':
        receipt['gates'] = {gate: write_json(root, f'evidence/{gate}.json',
                                           {'status': 'PASS', 'gate': gate, 'identity': row['identity'], 'controls_passed': True})
                            for gate in inventory.GATES}
    row['receipt'] = write_json(root, 'evidence/receipt.json', receipt)
    return receipt


def test_current_seed_is_valid_but_cannot_close_full_goal():
    ledger = inventory.read_json(inventory.LEDGER)
    result = inventory.validate(ledger)
    assert result['status'] == 'VALID_INCOMPLETE'
    assert result['reviewed'] is False
    assert result['incomplete_required_rows'] > 0
    with pytest.raises(inventory.InventoryError, match='full closure unproven'):
        inventory.validate(ledger, require_complete=True)


@pytest.mark.parametrize('change, message', [
    (lambda x: x['rows'].append(deepcopy(x['rows'][0])), 'duplicate feature/profile'),
    (lambda x: x['features'].append(deepcopy(x['features'][0])), 'duplicate feature'),
    (lambda x: x['profiles'].append(deepcopy(x['profiles'][0])), 'duplicate profile'),
    (lambda x: x['features'][0]['requirements'].append('UNKNOWN-1'), 'unknown requirement'),
    (lambda x: x['features'][0]['capabilities'].append('missing'), 'unknown capability'),
    (lambda x: x['applicability'][0]['dependencies'].append('missing'), 'dangling dependency'),
    (lambda x: x['features'][0]['upstream_sources'][0].update(sha256='0' * 64), 'wrong upstream member'),
    (lambda x: x['rows'][0].update(profile='missing'), 'dangling feature/profile'),
    (lambda x: x['rows'][0].update(state='supported'), 'unknown value'),
    (lambda x: x.update(schema=True), 'wrong constant'),
    (lambda x: x.update(applicability=[]), 'too few items'),
    (lambda x: x['rows'][0].update(outcome='passed'), 'unproven state claims passed'),
])
def test_invalid_graph_and_schema_are_rejected(example, change, message):
    root, ledger = example
    change(ledger)
    with pytest.raises(inventory.InventoryError, match=message):
        inventory.validate(ledger, root)


@pytest.mark.parametrize('state', inventory.POSITIVE)
def test_matching_scoped_receipts_accept_only_their_phase(example, state):
    root, ledger = example
    promote(root, ledger, state)
    result = inventory.validate(ledger, root)
    assert result['status'] == 'VALID_INCOMPLETE'  # Review is still outstanding.
    ledger['reviewed'] = True
    if state == 'qualified':
        assert inventory.validate(ledger, root, True)['status'] == 'VALID_COMPLETE'
    else:
        with pytest.raises(inventory.InventoryError, match='full closure unproven'):
            inventory.validate(ledger, root, True)


@pytest.mark.parametrize('change, message', [
    (lambda l, r: r.update(child_waited=False), 'child wait'),
    (lambda l, r: r.update(exit_code=1), 'failed exit'),
    (lambda l, r: r.update(phase='qualified'), 'claimed phase'),
    (lambda l, r: r.update(requirements=[]), 'required contract'),
    (lambda l, r: r.update(profile='other'), 'another feature/profile'),
    (lambda l, r: r['identity'].update(source_commit='9' * 40), 'stale source/artifact'),
    (lambda l, r: l['profiles'][0].update(environment_sha256='9' * 64), 'pinned environment'),
    (lambda l, r: l['profiles'][0].update(admitted=False), 'unassigned profile'),
    (lambda l, r: l['rows'][0]['fixtures'].pop(), 'ordinary/mutation'),
    (lambda l, r: l['rows'][0].update(outcome='failed'), 'latest outcome'),
])
def test_positive_receipt_cannot_promote_stale_or_incomplete_evidence(example, change, message):
    root, ledger = example
    receipt = promote(root, ledger)
    change(ledger, receipt)
    ledger['rows'][0]['receipt'] = write_json(root, 'evidence/receipt.json', receipt)
    with pytest.raises(inventory.InventoryError, match=message):
        inventory.validate(ledger, root)


@pytest.mark.parametrize('case', ['skip', 'missing-phase', 'wrong-count', 'changed-bytes', 'false-exit'])
def test_pytest_receipt_cannot_hide_missing_or_skipped_cases(example, case):
    root, ledger = example
    receipt = promote(root, ledger)
    output = inventory.read_json(root / 'evidence/pytest.json')
    if case == 'skip':
        output['reports'][1]['outcome'] = 'skipped'
    elif case == 'missing-phase':
        output['reports'].pop()
    elif case == 'wrong-count':
        ledger['rows'][0]['fixtures'][0]['cases'] = 2
    elif case == 'false-exit':
        output['exit_code'] = False
    new_ref = write_json(root, 'evidence/pytest.json', output)
    if case != 'changed-bytes':
        receipt['pytest'] = new_ref
        ledger['rows'][0]['receipt'] = write_json(root, 'evidence/receipt.json', receipt)
    else:
        (root / 'evidence/pytest.json').write_text('{}', encoding='utf-8')
    with pytest.raises(inventory.InventoryError):
        inventory.validate(ledger, root)


@pytest.mark.parametrize('case', ['missing-gate', 'stale-gate', 'no-controls', 'source-only-audit', 'no-wheel', 'no-origin'])
def test_qualification_needs_same_artifact_audit_and_all_controlled_gates(example, case):
    root, ledger = example
    receipt = promote(root, ledger, 'qualified')
    gate = inventory.GATES[0]
    if case == 'missing-gate':
        receipt['gates'].pop(gate)
    elif case in ('stale-gate', 'no-controls'):
        output = inventory.read_json(root / receipt['gates'][gate]['path'])
        if case == 'stale-gate':
            output['identity']['wheel_sha256'] = '9' * 64
        else:
            output['controls_passed'] = False
        receipt['gates'][gate] = write_json(root, f'evidence/{gate}.json', output)
    elif case == 'source-only-audit':
        receipt['distribution_audit'] = write_json(root, 'evidence/distribution.json', {'status': 'PASS'})
    elif case == 'no-wheel':
        ledger['rows'][0]['identity']['wheel_sha256'] = None
        receipt['identity']['wheel_sha256'] = None
    elif case == 'no-origin':
        receipt['installed_origin_verified'] = False
    ledger['rows'][0]['receipt'] = write_json(root, 'evidence/receipt.json', receipt)
    with pytest.raises(inventory.InventoryError):
        inventory.validate(ledger, root)


def test_fixture_and_cyclic_dependency_cannot_dangle(example):
    root, ledger = example
    promote(root, ledger)
    ledger['rows'][0]['fixtures'][0]['nodeid'] = 'tests/test_workflow.py::test_missing'
    with pytest.raises(inventory.InventoryError, match='dangling fixture'):
        inventory.validate(ledger, root)
    ledger['rows'][0]['fixtures'] = []
    second = deepcopy(ledger['features'][0])
    second['id'] = 'second'
    ledger['features'].append(second)
    pair = deepcopy(ledger['applicability'][0])
    pair.update(feature='second', dependencies=[ledger['features'][0]['id']])
    ledger['applicability'][0]['dependencies'] = ['second']
    ledger['applicability'].append(pair)
    with pytest.raises(inventory.InventoryError, match='cyclic dependency'):
        inventory.validate(ledger, root)


def test_dependency_evidence_must_match_profile_artifact_and_phase(example):
    root, ledger = example
    promote(root, ledger)
    dependency = deepcopy(ledger['features'][0])
    dependency['id'] = 'dependency'
    ledger['features'].append(dependency)
    pair = deepcopy(ledger['applicability'][0])
    pair.update(feature='dependency')
    ledger['applicability'][0]['dependencies'] = ['dependency']
    ledger['applicability'].append(pair)
    with pytest.raises(inventory.InventoryError, match='same-profile capability'):
        inventory.validate(ledger, root)
    pending = deepcopy(ledger['rows'][0])
    pending.update(feature='dependency', state='implemented-untested', outcome='not-run', identity=None, receipt=None)
    ledger['rows'].append(pending)
    with pytest.raises(inventory.InventoryError, match='same-profile capability'):
        inventory.validate(ledger, root)


def test_duplicate_json_and_unknown_schema_constraints_fail_closed(tmp_path):
    path = tmp_path / 'duplicate.json'
    path.write_text('{"schema":1,"schema":2}')
    with pytest.raises(inventory.InventoryError, match='duplicate JSON key'):
        inventory.read_json(path)
    with pytest.raises(inventory.InventoryError, match='unsupported schema keyword'):
        inventory.shape('anything', {'unsupportedRule': True}, {})


def test_export_discovery_skips_star_and_private_and_retains_aliases():
    import ast
    tree = ast.parse('from .x import Public as Alias, _private\nfrom .y import *\ndef function(): pass\n')
    assert exports(tree) == ['Alias', 'function']


def test_catalog_uses_pinned_bytes_and_merges_duplicate_public_exports():
    source = ROOT / 'third_party/parity/vispy/vispy'
    generated = generate(source)
    assert generated == inventory.read_json(inventory.LEDGER)
    names = [feature['entry_point'] for feature in generated['features']]
    assert names.count('vispy.gloo.get_current_canvas') == 1
    assert 'vispy.visuals.VolumeVisual' in names
    assert 'vispy.app.backend.glfw' in names
    assert not any(row['state'] in inventory.POSITIVE for row in generated['rows'])
    assert generated['reviewed'] is False


def test_generator_rejects_unpinned_source_bytes(tmp_path):
    (tmp_path / 'app').mkdir()
    (tmp_path / 'app/__init__.py').write_text('from .application import Application\n')
    with pytest.raises(inventory.InventoryError, match='upstream source mismatch'):
        generate(tmp_path)


def test_completion_cli_fails_on_current_draft(capsys):
    assert inventory.main(['--require-complete']) == 1
    assert 'full closure unproven' in capsys.readouterr().out


@pytest.mark.parametrize('state,outcome', [('not-inventoried', 'not-run'),
                                         ('implemented-untested', 'failed'), ('blocked-external', 'blocked')])
def test_optional_profile_does_not_block_required_qualification(example, state, outcome):
    root, ledger = example
    promote(root, ledger, 'qualified')
    ledger['reviewed'] = True
    ledger['profiles'].append({'id': 'experimental', 'description': 'Optional experiment only',
                               'admitted': False, 'environment_sha256': None})
    pair = deepcopy(ledger['applicability'][0])
    pair.update(profile='experimental', status='optional', rationale='Reviewed optional experiment.')
    ledger['applicability'].append(pair)
    optional = deepcopy(ledger['rows'][0])
    optional.update(profile='experimental', state=state, outcome=outcome,
                    fixtures=[], identity=None, receipt=None)
    ledger['rows'].append(optional)
    assert inventory.validate(ledger, root, True)['status'] == 'VALID_COMPLETE'


def test_optional_positive_claim_still_needs_valid_evidence(example):
    root, ledger = example
    promote(root, ledger, 'qualified')
    optional = deepcopy(ledger['features'][0])
    optional['id'] = 'optional-feature'
    ledger['features'].append(optional)
    pair = deepcopy(ledger['applicability'][0])
    pair.update(feature=optional['id'], status='optional')
    ledger['applicability'].append(pair)
    row = deepcopy(ledger['rows'][0])
    row['feature'] = optional['id']
    ledger['rows'].append(row)
    ledger['reviewed'] = True
    with pytest.raises(inventory.InventoryError, match='receipt belongs to another feature/profile'):
        inventory.validate(ledger, root, True)


@pytest.mark.parametrize('state,outcome', [('not-inventoried', 'not-run'), ('unsupported', 'not-run'),
                                         ('blocked-external', 'blocked')])
def test_required_pair_stays_incomplete_including_missing_hardware(example, state, outcome):
    root, ledger = example
    ledger['reviewed'] = True
    ledger['rows'][0].update(state=state, outcome=outcome, blocker='No suitable hardware currently available.')
    result = inventory.validate(ledger, root)
    assert result['incomplete_required_rows'] == 1
    with pytest.raises(inventory.InventoryError, match='full closure unproven'):
        inventory.validate(ledger, root, True)
    # Relabeling an observed blocker as nonapplicable cannot hide its row.
    ledger['applicability'][0]['status'] = 'not-applicable'
    second = deepcopy(ledger['features'][0])
    second['id'] = 'still-required'
    ledger['features'].append(second)
    pair = deepcopy(ledger['applicability'][0])
    pair.update(feature=second['id'], status='required')
    ledger['applicability'].append(pair)
    with pytest.raises(inventory.InventoryError, match='nonapplicable pair cannot carry'):
        inventory.validate(ledger, root)


def test_absent_required_row_remains_a_completion_blocker(example):
    root, ledger = example
    ledger['rows'] = []
    ledger['reviewed'] = True
    assert inventory.validate(ledger, root)['incomplete_required_rows'] == 1
    with pytest.raises(inventory.InventoryError, match='full closure unproven'):
        inventory.validate(ledger, root, True)


@pytest.mark.parametrize('case,message', [
    ('duplicate', 'duplicate applicability key'),
    ('unknown-profile', 'dangling applicability'),
    ('unknown-feature', 'dangling applicability'),
    ('blank-rationale', 'blank applicability rationale'),
    ('unreviewed', 'unreviewed applicability'),
    ('self-dependency', 'self dependency'),
    ('no-required', 'no required feature/profile'),
    ('legacy-flag', 'unexpected fields'),
])
def test_applicability_cannot_silently_change_or_erase_scope(example, case, message):
    root, ledger = example
    pair = ledger['applicability'][0]
    if case == 'duplicate':
        ledger['applicability'].append(deepcopy(pair))
    elif case == 'unknown-profile':
        pair['profile'] = 'missing'
    elif case == 'unknown-feature':
        pair['feature'] = 'missing'
    elif case == 'blank-rationale':
        pair['rationale'] = '  '
    elif case == 'unreviewed':
        pair['reviewed'] = False
        ledger['reviewed'] = True
    elif case == 'self-dependency':
        pair['dependencies'] = [pair['feature']]
    elif case == 'no-required':
        pair['status'] = 'optional'
    elif case == 'legacy-flag':
        ledger['features'][0]['required'] = False
    with pytest.raises(inventory.InventoryError, match=message):
        inventory.validate(ledger, root)


def test_every_declared_profile_needs_explicit_applicability(example):
    root, ledger = example
    ledger['profiles'].append({'id': 'other', 'description': 'Another profile',
                               'admitted': False, 'environment_sha256': None})
    with pytest.raises(inventory.InventoryError, match='missing explicit feature/profile applicability'):
        inventory.validate(ledger, root)
    pair = deepcopy(ledger['applicability'][0])
    pair.update(profile='other', status='not-applicable',
                rationale='This fixture specifies a different backend contract.')
    ledger['applicability'].append(pair)
    promote(root, ledger, 'qualified')
    ledger['reviewed'] = True
    assert inventory.validate(ledger, root, True)['status'] == 'VALID_COMPLETE'


def test_dependencies_are_local_to_profile_and_required_closure(example):
    root, ledger = example
    second = deepcopy(ledger['features'][0])
    second['id'] = 'second'
    ledger['features'].append(second)
    pair = deepcopy(ledger['applicability'][0])
    pair.update(feature='second', dependencies=[ledger['features'][0]['id']])
    ledger['applicability'].append(pair)
    ledger['profiles'].append({'id': 'other', 'description': 'A different lowering/backend',
                               'admitted': False, 'environment_sha256': None})
    first_other = deepcopy(ledger['applicability'][0])
    first_other.update(profile='other', dependencies=['second'])
    second_other = deepcopy(pair)
    second_other.update(profile='other', dependencies=[])
    ledger['applicability'].extend([first_other, second_other])
    # Opposite dependency direction on another profile is not a cycle.
    assert inventory.validate(ledger, root)['incomplete_required_rows'] == 4
    second_other['status'] = 'optional'
    with pytest.raises(inventory.InventoryError, match='required pair depends on an optional'):
        inventory.validate(ledger, root)
    second_other['status'] = 'not-applicable'
    with pytest.raises(inventory.InventoryError, match='dependency is nonapplicable'):
        inventory.validate(ledger, root)


def legacy_v1(ledger):
    legacy = deepcopy(ledger)
    legacy.update(schema=1, required_profiles=[legacy['profiles'][0]['id']])
    pairs = legacy.pop('applicability')
    for feature in legacy['features']:
        pair = next(a for a in pairs if a['feature'] == feature['id'])
        feature.update(required=True, dependencies=list(pair['dependencies']))
    return legacy


def test_v1_migration_preserves_required_scope_evidence_and_blockers(example):
    root, ledger = example
    promote(root, ledger, 'qualified')
    ledger['reviewed'] = True
    legacy = legacy_v1(ledger)
    legacy['profiles'].append({'id': 'no-hardware', 'description': 'Optional retained experiment',
                               'admitted': False, 'environment_sha256': None})
    optional = deepcopy(legacy['rows'][0])
    optional.update(profile='no-hardware', state='blocked-external', outcome='blocked',
                    fixtures=[], identity=None, receipt=None, blocker='No hardware available.')
    legacy['rows'].append(optional)
    original = deepcopy(legacy)
    migrated = migrate_v1(legacy)
    assert legacy == original  # Caller and historical receipt bytes are not mutated.
    assert migrated['rows'] == legacy['rows']
    assert migrated['reviewed'] is False
    assert [(a['profile'], a['status']) for a in migrated['applicability']] == [
        ('unassigned', 'required'), ('no-hardware', 'optional')]
    assert not any(a['reviewed'] for a in migrated['applicability'])
    assert inventory.validate(migrated, root)['status'] == 'VALID_INCOMPLETE'
    # Missing hardware on a legacy-required profile is still required.
    legacy['required_profiles'].append('no-hardware')
    migrated = migrate_v1(legacy)
    assert all(a['status'] == 'required' for a in migrated['applicability'])
    assert inventory.validate(migrated, root)['incomplete_required_rows'] == 1


def test_v1_migration_cli_never_overwrites_and_v1_cannot_validate(example):
    root, ledger = example
    legacy = legacy_v1(ledger)
    with pytest.raises(inventory.InventoryError, match='wrong constant'):
        inventory.validate(legacy, root)
    write_json(root, 'legacy.json', legacy)
    args = ['--input', str(root / 'legacy.json'), '--output', str(root / 'converted.json'), '--root', str(root)]
    assert migrate_main(args) == 0
    first = (root / 'converted.json').read_bytes()
    with pytest.raises(FileExistsError):
        migrate_main(args)
    assert (root / 'converted.json').read_bytes() == first


@pytest.mark.parametrize('path', ['../outside.json', '/outside.json', 'C:/outside.json', 'directory\\file.json'])
def test_evidence_reference_cannot_escape_declared_workspace(tmp_path, path):
    with pytest.raises(inventory.InventoryError, match='invalid relative file'):
        inventory.local_file(tmp_path, path)
