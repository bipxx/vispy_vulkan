# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic store/record controls; none supplies real approvals or admission."""
from copy import deepcopy
import json
import os
from pathlib import Path
import uuid

import pytest

from tools import retained_evidence as stores
from tools import qualification_artifact as qa, qualification_native as win
from tools import qualification_linux_native as linux


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
    return {'path': name, 'sha256': qa.sha(path.read_bytes())}


@pytest.mark.parametrize('mutation', ['missing', 'changed'])
def test_candidate_requires_the_imported_store_verifier_identity(mutation):
    from tools import compatibility_candidate as candidate_tools
    candidate = deepcopy(candidate_tools.read_json(qa.ROOT / 'compat/candidates/tk-state-resource-1/candidate.json'))
    candidate['preparation_tools'] = [dict(path=name, sha256=qa.sha((qa.ROOT/name).read_bytes()))
                                     for name in candidate_tools.PREPARATION_TOOLS]
    name = 'tools/retained_evidence.py'
    if mutation == 'missing':
        candidate['preparation_tools'] = [ref for ref in candidate['preparation_tools'] if ref['path'] != name]
        match = 'incomplete preparation verifier/tool identities'
    else:
        next(ref for ref in candidate['preparation_tools'] if ref['path'] == name)['sha256'] = '0'*64
        match = 'retained_evidence.py'
    candidate_tools.seal(candidate)
    with pytest.raises(qa.InventoryError, match=match): candidate_tools.validate_candidate(candidate)


@pytest.fixture
def pair(tmp_path_factory, monkeypatch):
    base = tmp_path_factory.getbasetemp() / ('stores-' + uuid.uuid4().hex)
    source, evidence = base / 'source', base / 'evidence'
    source.mkdir(parents=True); evidence.mkdir()
    profile = json.loads((qa.ROOT / stores.PROFILE).read_bytes())
    host = 'windows' if os.name == 'nt' else 'posix'
    view = {'source_workspace': 'C:/synthetic-source' if host == 'windows' else '/synthetic-source',
            'storage_workspace': 'D:/synthetic-evidence' if host == 'windows' else '/synthetic-evidence'}
    profile['hosts'][host] = view
    # Project virtual external roots onto ordinary owned test directories only at
    # the filesystem seam. Production path validation, hashes and record readers
    # remain real; a profile must never designate actual managed scratch.
    mounts = {view['source_workspace']: source, view['storage_workspace']: evidence}
    monkeypatch.setattr(stores, 'Path', lambda value: mounts.get(str(value), Path(value)))
    reference = put(source, stores.PROFILE, profile)
    return source, evidence, profile, reference


def test_explicit_store_and_legacy_resolution(pair):
    source, evidence, _, reference = pair
    assert stores.evidence_root(source) == source
    assert stores.evidence_root(source, reference) == evidence
    item = put(evidence, 'build/runs/synthetic/result.json', b'original evidence')
    assert qa.retained_file(stores.evidence_root(source, reference), item).read_bytes() == b'original evidence'
    with pytest.raises(qa.InventoryError):
        qa.retained_file(source, item)


@pytest.mark.parametrize('mutation', ['hash', 'name', 'unknown', 'bool-schema', 'host', 'relative',
    'parent', 'nested', 'same', 'scratch', 'unc', 'missing', 'source'])
def test_resealed_store_controls(pair, mutation):
    source, evidence, profile, reference = pair
    host = 'windows' if os.name == 'nt' else 'posix'
    if mutation == 'hash':
        (source / stores.PROFILE).write_bytes((source / stores.PROFILE).read_bytes() + b' ')
    elif mutation == 'name':
        reference['path'] = 'compat/another-store.json'
    else:
        if mutation == 'unknown': profile['other'] = 'unreviewed'
        elif mutation == 'bool-schema': profile['schema'] = True
        elif mutation == 'host': profile['hosts']['other'] = profile['hosts'][host]
        elif mutation == 'relative': profile['hosts'][host]['storage_workspace'] = 'relative'
        elif mutation == 'parent': profile['hosts'][host]['storage_workspace'] += '/../other'
        elif mutation == 'nested': profile['hosts'][host]['storage_workspace'] = profile['hosts'][host]['source_workspace'] + '/nested'
        elif mutation == 'same': profile['hosts'][host]['storage_workspace'] = profile['hosts'][host]['source_workspace']
        elif mutation == 'scratch': profile['hosts'][host]['storage_workspace'] += '/build/work/unit'
        elif mutation == 'unc': profile['hosts']['windows']['storage_workspace'] = '//server/share/store'
        elif mutation == 'missing': profile['hosts'][host]['storage_workspace'] = (evidence.parent / 'missing').as_posix()
        else: profile['hosts'][host]['source_workspace'] = (source.parent / 'other-source').as_posix()
        reference = put(source, stores.PROFILE, profile)
    with pytest.raises(qa.InventoryError): stores.evidence_root(source, reference)


@pytest.mark.parametrize('path', ['../source/file', '/absolute', 'build/work/unit/result', 'a/../../file'])
def test_selected_store_keeps_existing_file_and_scratch_rules(pair, path):
    source, evidence, _, reference = pair
    put(evidence, 'build/work/unit/result', b'scratch')
    with pytest.raises(qa.InventoryError):
        qa.retained_file(stores.evidence_root(source, reference), {'path': path, 'sha256': qa.sha(b'scratch')})


def test_full_archive_record_reads_only_produced_bytes_from_store(pair, monkeypatch):
    from test_qualification_artifact import sample, wheel_bytes
    source, evidence, _, reference = pair
    entries, inputs = sample(version='0.17.0+vulkan.2')
    put(source, qa.SCHEMA, (qa.ROOT / qa.SCHEMA).read_bytes())
    put(source, qa.POLICY, (qa.ROOT / qa.POLICY).read_bytes())
    put(source, 'compat/runtime-package.json', inputs['manifest_data'])
    put(source, 'src/vispy/__init__.py', entries['vispy/__init__.py'])
    put(source, 'pyproject.toml', b'[project]\nversion = "0.17.0+vulkan.2"\nlicense-files = ["LICENSE", "LICENSE-BSD", "LICENSING.md"]\n')
    for name, data in inputs['notices'].items():
        short = name.removeprefix('vispy/_licenses/')
        put(source, short if short in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md') else 'third_party/licenses/' + short, data)
    profile = put(source, 'profile.json', dict(kind='windows-gpu', architecture='x86_64', python_abi='cp312'))
    candidate = dict(profiles=[dict(id='synthetic', observation=profile)], product_source_commit='synthetic-only')
    put(source, 'candidate.json', candidate)
    def validate(value, root):
        assert value == candidate and root == source
    monkeypatch.setattr(qa, 'validate_candidate', validate)
    record = dict(schema=1, kind='archive-prerequisite', profile='synthetic', evidence_store=reference,
        candidate=dict(path='candidate.json', scope_sha256=qa.scope_digest(candidate)),
        wheel=put(evidence, 'build/artifacts/unit/vispy-0.17.0+vulkan.2-cp312-cp312-win_amd64.whl',
                  wheel_bytes(entries, dist=qa.distribution_directory('0.17.0+vulkan.2'))),
        native_outputs=[dict(member=n, file=put(evidence, 'build/artifacts/native/' + str(i), entries[n]))
                        for i, n in enumerate(inputs['native_hashes'])])
    result = qa.validate_archive(record, source)
    assert result['artifact_admitted'] is False
    del record['evidence_store']
    with pytest.raises(qa.InventoryError, match='missing local file'):
        qa.validate_archive(record, source)


def test_full_linux_capture_keeps_source_schema_and_original_protocol(pair):
    from linux_native_fixture import Capture
    source, evidence, _, reference = pair
    definitions = json.loads((qa.ROOT / linux.SCHEMA).read_bytes())['$defs']
    put(source, linux.SCHEMA, {'$defs': definitions})
    fixture = Capture(evidence, qa.ROOT, definitions)
    capture = fixture.finish()
    result, _ = linux.validate_capture(capture, fixture.production, source,
                                     evidence_root=stores.evidence_root(source, reference))
    assert result['native_build_verified'] and result['artifact_admitted'] is False
    with pytest.raises(qa.InventoryError, match='missing local file'):
        linux.validate_capture(capture, fixture.production, source)


def test_full_linux_record_keeps_reviews_and_origins_on_source(pair, monkeypatch):
    from linux_native_fixture import Capture
    source, evidence, _, reference = pair
    definitions = json.loads((qa.ROOT / linux.SCHEMA).read_bytes())['$defs']
    put(source, linux.SCHEMA, {'$defs': definitions})
    put(source, qa.SCHEMA, (qa.ROOT / qa.SCHEMA).read_bytes())
    policy = json.loads((qa.ROOT / qa.POLICY).read_bytes())
    policy['linux_scope'] = 'reviewed-full-source-native-proof-required'
    put(source, qa.POLICY, policy)
    fixture = Capture(evidence, qa.ROOT, definitions)
    capture = fixture.finish()
    result, environment = linux.validate_capture(capture, fixture.production, source, evidence_root=evidence)
    observation = put(source, 'profile.json', dict(kind='wsl-software', architecture='x86_64', python_abi='cp312',
        python_version='3.12.13 synthetic consumer', interpreter_sha256='e'*64))
    runtime = put(source, 'runtime.json', dict(native=[dict(path=n, sha256=h) for n,h in fixture.production.items()],
                                             build=[], locks=[]))
    candidate = dict(profiles=[dict(id='synthetic', observation=observation)], runtime_inputs=runtime, reviews={})
    capture_ref = put(evidence, 'capture.json', capture)
    reuse = dict(profile='synthetic', candidate_scope_sha256=linux.scope_digest(candidate),
        capture_sha256=capture_ref['sha256'], production_sha256=result['production_sha256'],
        evidence_store=reference, impact='Synthetic record only; no actual approval or admission',
        abi=dict(tag='cp312', build_version=environment['python'].split()[0],
            build_python_sha256=environment['python_executable_sha256'],
            consumer_version='3.12.13', consumer_python_sha256='e'*64))
    for kind in ('source','scope'):
        candidate['reviews'][kind] = put(source, kind+'.json', dict(native_reuse_links=[linux.digest(reuse)]))
    def reviewed(value, root, require_reviewed):
        assert value == candidate and root == source and require_reviewed is True
    monkeypatch.setattr(linux, 'validate_candidate', reviewed)
    record = dict(schema=1, kind='original-linux-ci-native-reuse',
        candidate=put(source, 'candidate.json', candidate), capture=capture_ref, reuse=reuse)
    assert linux.validate_record(record, source) == result
    # Rebinding an evidence store changes both native review edges, even when
    # all retained capture bytes and the candidate's source scope are unchanged.
    record['reuse']['evidence_store'] = dict(reference, sha256='0'*64)
    with pytest.raises(qa.InventoryError, match='lacks exact independent review'):
        linux.validate_record(record, source)


@pytest.mark.parametrize('kind', ['source', 'scope'])
def test_native_store_selection_is_part_of_both_review_bindings(pair, monkeypatch, kind):
    from test_qualification_native import sample, record_stub
    source, evidence, _, reference = pair
    put(source, win.SCHEMA, (qa.ROOT / win.SCHEMA).read_bytes())
    recipe = sample()[0]
    recipe_ref = put(evidence, 'recipe.json', recipe)
    profile = put(source, 'profile.json', dict(kind='windows-gpu', architecture='x86_64', python_abi='cp312'))
    candidate = dict(profiles=[dict(id='synthetic', observation=profile)], reviews={})
    record = record_stub(put(source, 'candidate.json', candidate))
    record['recipe'] = recipe_ref
    record['reuse'].update(profile='synthetic', candidate_scope_sha256=win.scope_digest(candidate),
                           recipe_sha256=win.recipe_digest(recipe))
    old_edge = win.digest(record['reuse'])
    record['reuse']['evidence_store'] = reference
    for name in ('source', 'scope'):
        candidate['reviews'][name] = put(source, name + '.json',
            {'native_reuse_links': [old_edge if name == kind else win.digest(record['reuse'])]})
    record['candidate'] = put(source, 'candidate.json', candidate)
    def reviewed(value, root, require_reviewed):
        assert root == source and require_reviewed is True
    monkeypatch.setattr(win, 'validate_candidate', reviewed)
    with pytest.raises(qa.InventoryError, match='lacks bound independent review'):
        win.validate_record(record, source)
