# SPDX-License-Identifier: AGPL-3.0-only
"""Selection controls are source-only; synthetic rows never admit artifacts."""
from copy import deepcopy

import pytest

from tools import compatibility_qualification as q


def current_review_applied(execution, candidate):
    """A bound approval alone does not apply scoped ledger review flags."""
    ledger = q.read_json(q.ROOT / execution['execution']['path'])
    selected = {(pair['feature'], pair['profile']) for pair in candidate['pairs']}
    return all(candidate['reviews'].values()) and all(
        pair['reviewed'] for pair in ledger['applicability']
        if (pair['feature'], pair['profile']) in selected)


def graph():
    mappings, rows, apps = [], [], []
    for feature, dependencies in [('view', ['device']), ('device', [])]:
        for profile in ('windows', 'linux'):
            rows.append({'feature': feature, 'profile': profile})
            apps.append({'feature': feature, 'profile': profile, 'status': 'required',
                         'dependencies': list(dependencies)})
            for mode in q.MODES:
                mappings.append({'destination': {'feature': feature, 'profile': profile,
                                                 'criterion': feature + '.' + mode}})
    return mappings, {'rows': rows, 'applicability': apps}


def request(feature='view', profile='windows', mode='ordinary'):
    return {'feature': feature, 'profile': profile, 'criterion': feature + '.' + mode}


def test_single_criterion_expands_whole_row_and_same_profile_dependencies():
    mappings, ledger = graph()
    closure = q.expand_selection([request()], mappings, ledger)
    assert len(closure) == 8
    assert {item['profile'] for item in closure} == {'windows'}
    assert {item['criterion'] for item in closure} == {
        feature + '.' + mode for feature in ('device', 'view') for mode in q.MODES}
    assert closure == q.ordered(closure)


def test_expansion_is_unique_even_for_shared_dependency_and_repeated_row_requests():
    mappings, ledger = graph()
    requests = q.ordered([request(), request(mode='recovery'), request(feature='device')])
    assert len(q.expand_selection(requests, mappings, ledger)) == 8


@pytest.mark.parametrize('change,message', [
    ('empty', 'empty admission'), ('duplicate', 'duplicate requested'),
    ('unsorted', 'must be sorted'), ('unknown', 'no execution mapping'),
    ('missing-recovery', 'all four'), ('optional-dependency', 'not required'),
    ('cross-profile', 'missing dependency'), ('missing-row', 'missing dependency'),
    ('cycle', 'cyclic admission'), ('duplicate-map', 'duplicate mapped'),
])
def test_semantic_selection_controls(change, message):
    mappings, ledger = graph()
    requests = [request()]
    if change == 'empty':
        requests = []
    elif change == 'duplicate':
        requests *= 2
    elif change == 'unsorted':
        requests.append(request(feature='device'))
    elif change == 'unknown':
        requests = [request(mode='invented')]
    elif change == 'missing-recovery':
        mappings = [m for m in mappings if m['destination'] != request('device', mode='recovery')]
    elif change == 'optional-dependency':
        ledger['applicability'][2]['status'] = 'optional'
    elif change == 'cross-profile':
        ledger['applicability'] = [a for a in ledger['applicability']
                                   if (a['feature'], a['profile']) != ('device', 'windows')]
    elif change == 'missing-row':
        ledger['rows'] = [r for r in ledger['rows'] if r != {'feature': 'device', 'profile': 'windows'}]
    elif change == 'cycle':
        ledger['applicability'][2]['dependencies'] = ['view']
    elif change == 'duplicate-map':
        mappings.append(deepcopy(mappings[0]))
    with pytest.raises(q.InventoryError, match=message):
        q.expand_selection(requests, mappings, ledger)


def test_current_selection_is_incomplete_and_preserves_both_profiles():
    record = q.read_json(q.DEFAULT)
    result = q.validate_selection(record)
    assert len(result['requested']) == len(result['closure']) == 120
    assert len({key['profile'] for key in result['closure']}) == 2
    execution = q.read_json(q.ROOT / record['execution_map']['path'])
    candidate, _, _ = q.load_inputs(execution, q.ROOT)
    expected_review = current_review_applied(execution, candidate)
    assert result['reviewed'] is expected_review
    assert not any(result[key] for key in ('admitted', 'qualified', 'full_inventory_complete'))
    if expected_review:
        assert q.validate_selection(record, require_reviewed=True) == result
    else:
        with pytest.raises(q.InventoryError, match='review remains pending'):
            q.validate_selection(record, require_reviewed=True)


@pytest.mark.parametrize('change', ['omit-recovery', 'wrong-profile', 'stale-map', 'unknown-field'])
def test_resealed_real_selection_rejects_scope_changes(change):
    record = deepcopy(q.read_json(q.DEFAULT))
    if change == 'omit-recovery':
        record['closure'].pop()
    elif change == 'wrong-profile':
        record['closure'][0]['profile'] = 'unassigned'
    elif change == 'stale-map':
        record['execution_map']['scope_sha256'] = '0' * 64
    else:
        record['admitted'] = True
    q.seal(record)
    with pytest.raises(q.InventoryError):
        q.validate_selection(record)


def test_default_cli_does_not_write_and_strict_review_validates_actual_approvals(capsys):
    before = q.DEFAULT.read_bytes()
    record = q.read_json(q.DEFAULT)
    execution = q.read_json(q.ROOT / record['execution_map']['path'])
    candidate, _, _ = q.load_inputs(execution, q.ROOT)
    expected_review = current_review_applied(execution, candidate)
    assert q.main([]) == 0
    assert q.main(['--require-reviewed']) == (0 if expected_review else 1)
    assert q.DEFAULT.read_bytes() == before
    assert ('"reviewed": true' if expected_review else 'review remains pending') in capsys.readouterr().out


@pytest.mark.parametrize('binding', ['exact', 'wrong', 'absent'])
def test_selection_binding_extends_existing_scope_approval(monkeypatch, binding):
    # Synthetic existing-review disposition only; never a real approval record.
    record = q.read_json(q.DEFAULT)
    execution = q.read_json(q.ROOT / record['execution_map']['path'])
    candidate, coverage, baseline = q.load_inputs(execution, q.ROOT)
    candidate = deepcopy(candidate)
    reference = {'path': 'unit-only-review.json', 'sha256': '0' * 64}
    candidate['reviews']['scope'] = reference
    review = {}
    if binding != 'absent':
        review['admission_scope_sha256'] = record['manifest_sha256'] if binding == 'exact' else '0' * 64
    original_read, original_ref = q.read_json, q.file_ref
    monkeypatch.setattr(q, 'validate_execution', lambda *a, **kw: {'reviewed': True})
    monkeypatch.setattr(q, 'load_inputs', lambda *a, **kw: (candidate, coverage, baseline))
    marker = q.ROOT / reference['path']
    monkeypatch.setattr(q, 'file_ref', lambda root, ref: marker if ref == reference else original_ref(root, ref))
    monkeypatch.setattr(q, 'read_json', lambda path: review if path == marker else original_read(path))
    if binding == 'exact':
        result = q.validate_selection(record, require_reviewed=True)
        assert result['reviewed'] and not result['admitted']
    else:
        with pytest.raises(q.InventoryError, match='pending or stale'):
            q.validate_selection(record, require_reviewed=True)
