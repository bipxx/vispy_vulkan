# SPDX-License-Identifier: AGPL-3.0-only
"""The strict napari rows on napari 0.10.0 (D31 Phase 5b).

compat/no-opengl-napari-0.10.0.json succeeds the matrix's four napari rows. The matrix keeps its napari 0.9.2 rows,
because candidates pin its bytes; R2's matrix renewal takes these rows.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / 'compat/no-opengl-napari-0.10.0.json'
MATRIX = ROOT / 'compat/no-opengl-matrix.json'
APPLICATIONS = ('napari', 'napari-threedee')
ROW_FIELDS = ('platform', 'application', 'binding', 'mandatory', 'features')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def matrix_rows():
    return {row['id']: row for row in load(MATRIX)['rows'] if row.get('application') in APPLICATIONS}


def test_the_record_names_the_matrix_bytes_it_succeeds():
    assert load(RECORD)['supersedes'] == {'matrix': {'path': 'compat/no-opengl-matrix.json', 'sha256': sha(MATRIX)},
                                          'rows': sorted(matrix_rows())}


def test_the_record_holds_exactly_the_matrix_napari_rows():
    rows = {row['id']: row for row in load(RECORD)['rows']}
    old = matrix_rows()
    assert sorted(rows) == sorted(old) and len(rows) == 4
    for name, row in rows.items():
        assert {field: row[field] for field in ROW_FIELDS} == {field: old[name][field] for field in ROW_FIELDS}


def test_each_row_keeps_its_platforms_admitted_artifact():
    admitted = {row['platform']: row['artifact_sha256'] for row in load(MATRIX)['rows']
                if row.get('application') == 'napari' and row['status'] == 'QUALIFIED'}
    assert len(admitted) == 2
    for row in load(RECORD)['rows']:
        artifact = row['artifact_sha256'] if row['status'] == 'QUALIFIED' else row['latest_attempt']['artifact_sha256']
        assert artifact == admitted[row['platform']], row['id']


def test_rows_bind_their_evidence_like_the_matrix_rows():
    for row in load(RECORD)['rows']:
        evidence = row['evidence'] if row['status'] == 'QUALIFIED' else row['latest_attempt']['evidence']
        assert evidence and all(set(item) == {'workspace', 'path', 'sha256'} and item['workspace'] == 'vispy_vulkan'
                                and item['path'].startswith('build/runs/napari-010-strict-305/')
                                and len(item['sha256']) == 64 for item in evidence), row['id']
        if row['status'] == 'QUALIFIED':
            assert len(row['environment_id']) == 64 and row['qualification_scope']
            assert set(row['gates'].values()) == {'PASS'} and len(row['gates']) == 3
        else:
            assert row['status'] == 'PENDING'
            assert row['artifact_sha256'] is None and row['environment_id'] is None and not row['evidence']
            assert set(row['gates'].values()) == {'UNVERIFIED'} and len(row['gates']) == 3


def test_the_windows_threedee_row_leaves_r1_open():
    # R1 needs the startup stall's cause and a regression test; a passing run never closes it (consolidated plan).
    row = next(row for row in load(RECORD)['rows'] if row['id'] == 'windows-vulkan-napari-threedee-pyqt6')
    assert row['r1'] == 'open'


def test_the_host_pin_is_the_registered_napari_0_10_0_patch():
    host = load(RECORD)['host']['napari']
    patch = ROOT / host['patch']
    provenance = load(ROOT / 'compat/host-patches/napari-0.10.0-provenance.json')
    registered = [entry for entry in load(ROOT / 'compat/host-changes.json')['patches']
                  if entry['host'] == 'napari' and entry['version'] == '0.10.0']
    assert host['version'] == '0.10.0' and len(registered) == 1
    assert host['patch'] == registered[0]['patch'] and host['patch_sha256'] == registered[0]['sha256'] == sha(patch)
    assert host['patch_sha256'] == provenance['patch_sha256'] and host['sdist_sha256'] == provenance['source_sha256']
    assert len(host['commit']) == len(host['tag_object']) == 40 and len(host['wheel_sha256']) == 64


__all__ = [name for name in dir() if name.startswith('test_')]
