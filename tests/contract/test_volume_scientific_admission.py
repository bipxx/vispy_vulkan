# SPDX-License-Identifier: AGPL-3.0-only
"""Saved scientific evidence checks; synthetic identity rows are not timings."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tools import volume_scientific_admission as admission


PACKET = admission.ROOT / 'compat/scientific-admissions/volume-native58-cp312-numpy246-v5'


@pytest.fixture(scope='module')
def controls():
    return admission.verify_controls()


def test_all_seventeen_controls_recompute_exact_pixels_and_retain_originals(controls):
    assert set(controls['cases']) == set(admission.small.CASES)
    assert sum(row['compared_pixels'] for row in controls['cases'].values()) == 156672
    assert len(controls['package_sha256']) == 550
    paths = {path.relative_to(admission.ROOT).as_posix() for path in controls['evidence']}
    assert not any(path.startswith('build/') for path in paths)
    for name in admission.small.CASES:
        packet = admission.small.packet_for(name)
        manifest = admission.small.load_manifest(packet)
        for key in admission.small.ARTIFACTS:
            assert f"tests/reference/{packet}/{manifest['fixtures'][name][key]['file']}" in paths
    assert {'LICENSE', 'LICENSE-BSD', 'LICENSING.md'} <= paths
    assert {'tools/oracle_volume_capture.py', 'tools/oracle_napari_volume_capture.py',
            'tools/oracle_napari_requirements.txt', 'tools/fixture_gloo.py',
            'tools/fixture_volume.py', 'tools/fixture_napari_volume.py',
            'tests/reference/volume-scientific-controls-numpy246/driver.py'} <= paths


@pytest.mark.parametrize('name', admission.large.CASES)
def test_each_large_workload_has_actual_matching_controls_and_bound_admission(name, controls):
    result = admission.verify_large_case(name, controls)
    record = admission.read(PACKET / (name + '.json'))
    assert record['workload_sha256'] == result['workload_sha256']
    assert record['benchmark_data_sha256'] == result['data_sha256']
    assert record['artifacts']['candidate']['installed_package_sha256'] == controls['package_sha256']
    assert result['maximum_channel_error'] <= 2
    assert set(result['changes']) == {'probe7', 'probe73'}
    assert record['checks'] == dict.fromkeys(admission.benchmark.SCIENTIFIC_CHECKS['volume'], 'passed')
    assert record['check_cases']['primary_modes'] == [name]
    assert record['performance_qualified'] is False and record['other_cells_qualified'] is False


def test_all_admission_evidence_is_present_current_and_portable():
    plan = admission.read(PACKET / 'quality-plan.json')
    qualification = admission.read(PACKET / 'qualification.json')
    assert set(plan) == set(qualification['cases']) == set(admission.large.CASES)
    evidence = {}
    for name, entry in plan.items():
        path = PACKET / entry['scientific_admission']
        assert admission.sha(path) == qualification['cases'][name]['admission_sha256']
        record = admission.read(path)
        for item in record['evidence']:
            assert not Path(item['file']).is_absolute()
            target = (PACKET / item['file']).resolve(strict=True)
            assert target.is_relative_to(admission.ROOT)
            assert not target.is_relative_to(admission.ROOT / 'build')
            assert target not in evidence or evidence[target] == item['sha256']
            evidence[target] = item['sha256']
    for path, digest in evidence.items():
        assert admission.sha(path) == digest
    assert qualification['measured_performance_claimed'] is False
    assert qualification['measurement_identity_required'] is True
    assert qualification['full_release_qualified'] is False
    assert set(admission.benchmark.SCIENTIFIC_CHECKS['volume']) == {'primary_modes', *admission.CHECK_CASES}
    for names in admission.CHECK_CASES.values():
        assert set(names) <= set(admission.small.CASES)


@pytest.mark.parametrize('leaf', ['manifest.json', 'parent.json', 'mip/rgba.npy',
                                 'categorical_clip/parameters.json', 'mip/process.json'])
def test_control_artifact_drift_is_rejected(tmp_path, leaf):
    shutil.copytree(admission.CONTROL_ROOT, tmp_path / 'controls')
    path = tmp_path / 'controls' / leaf
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises((AssertionError, ValueError)):
        admission.verify_controls(tmp_path / 'controls')


def test_missing_control_image_is_rejected(tmp_path):
    shutil.copytree(admission.CONTROL_ROOT, tmp_path / 'controls')
    (tmp_path / 'controls/mip/rgba.npy').unlink()
    with pytest.raises(FileNotFoundError):
        admission.verify_controls(tmp_path / 'controls')


def test_different_candidate_native_payload_cannot_join_controls(controls):
    different = copy.deepcopy(controls)
    native = next(key for key in different['package_sha256'] if '_dawn.' in key)
    different['package_sha256'][native] = '0' * 64
    with pytest.raises(AssertionError, match='exact same installed artifact'):
        admission.verify_large_case(admission.large.CASES[0], different)


@pytest.mark.parametrize('role,leaf', [('candidate', 'initial.npz'), ('candidate', 'repeat.json'),
    ('candidate', 'parameters.json'), ('candidate', 'manifest.json'), ('upstream', 'probe7.npz')])
def test_large_raw_artifact_and_parent_drift_is_rejected(tmp_path, controls, role, leaf):
    name = admission.large.CASES[0]
    source = admission.LARGE_ROOT if role == 'candidate' else admission.ORIGINAL_ROOT
    shutil.copytree(source / name, tmp_path / name)
    shutil.copyfile(source / 'manifest.json', tmp_path / 'manifest.json')
    path = tmp_path / ('manifest.json' if leaf == 'manifest.json' else f'{name}/{leaf}')
    path.write_bytes(path.read_bytes() + b'changed')
    kwargs = {'candidate_root' if role == 'candidate' else 'original_root': tmp_path}
    with pytest.raises(AssertionError):
        admission.verify_large_case(name, controls, **kwargs)


def test_optimized_python_refuses_to_produce_any_admissions(tmp_path):
    output = tmp_path / 'admissions'
    process = subprocess.run([sys.executable, '-I', '-B', '-O',
        str(admission.ROOT / 'tools/volume_scientific_admission.py'), '--output', str(output)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert process.returncode != 0 and b'optimized mode is forbidden' in process.stdout
    assert not output.exists() and not output.with_name('admissions.pending').exists()


def test_later_case_failure_cannot_publish_partial_admission_set(tmp_path, controls, monkeypatch):
    first, second = admission.large.CASES[:2]
    actual = admission.verify_large_case(first, controls)
    monkeypatch.setattr(admission, 'verify_controls', lambda directory: controls)
    monkeypatch.setattr(admission.large, 'CASES', (first, second))
    verified = []
    def verify(name, *args):
        verified.append(name)
        if name == second:
            raise ValueError('injected later-case failure')
        return actual
    monkeypatch.setattr(admission, 'verify_large_case', verify)
    # Exercise publication/rollback separately from the frozen schema validator.
    # Deep pytest paths can exceed Windows' limit before resolving '..' paths.
    # Real producer executions and the saved closure tests cover schema checks.
    monkeypatch.setattr(admission.benchmark, 'validate_admission', lambda *args: {'status': 'passed'})
    # This lifecycle-only fixture need not serialize usable evidence links.
    # Windows CI checks out on D: while pytest scratch is on C:, so real
    # relpath() would fail before reaching the injected second-case failure.
    # Replace only this module's formatter, keeping global os.path untouched.
    monkeypatch.setattr(admission, 'os', SimpleNamespace(path=SimpleNamespace(
        relpath=lambda path, start: 'lifecycle-only-evidence/' + Path(path).name)))
    output = tmp_path / 'admissions'
    with pytest.raises(ValueError, match='injected later-case failure'):
        admission.produce(output)
    assert not output.exists()
    pending = output.with_name('admissions.pending')
    assert verified == [first, second]
    assert (pending / (first + '.json')).exists()
    assert not (pending / (second + '.json')).exists()
    assert pending.exists() and not (pending / 'qualification.json').exists()
    with pytest.raises(AssertionError, match='Preserve prior admission sets'):
        admission.produce(output)


@pytest.mark.parametrize('field,value', [('backend', 'OpenGL'), ('software', True),
    ('vendor_id', 0), ('device_id', 0), ('driver', 'other'), ('ok', False)])
def test_other_hardware_cell_is_rejected(field, value):
    device = dict(ok=True, backend='Vulkan', software=False, vendor_id=4318,
                  device_id=9860, device='NVIDIA GeForce RTX 4090', driver='610.88')
    device[field] = value
    with pytest.raises(AssertionError):
        admission.device_cell(device)


@pytest.mark.parametrize('role', ['upstream', 'candidate'])
@pytest.mark.parametrize('mutation', ['none', 'role', 'wheel', 'native', 'data', 'python', 'numpy', 'seven_sources'])
def test_measurement_identity_requires_complete_actual_artifact_fields(role, mutation):
    # These are deliberately synthetic contract tests, never performance proof.
    record = admission.read(PACKET / (admission.large.CASES[0] + '.json'))
    artifact = record['artifacts'][role]
    run = dict(data_sha256=record['benchmark_data_sha256'], provenance=dict(
        kind=role, wheel_sha256=artifact['wheel_sha256'],
        installed_package_sha256=copy.deepcopy(artifact['installed_package_sha256']),
        python='3.12.8', versions=dict(numpy='2.4.6')))
    provenance = run['provenance']
    if mutation == 'role': provenance.pop('kind')
    if mutation == 'wheel': provenance['wheel_sha256'] = '0' * 64
    if mutation == 'native':
        key = next(key for key in provenance['installed_package_sha256'] if key.endswith('.pyd'))
        provenance['installed_package_sha256'][key] = '0' * 64
    if mutation == 'data': run['data_sha256'] = '0' * 64
    if mutation == 'python': provenance['python'] = '3.13.0'
    if mutation == 'numpy': provenance['versions']['numpy'] = '2.5.3'
    if mutation == 'seven_sources':
        provenance['source_sha256'] = dict(list(provenance.pop('installed_package_sha256').items())[:7])
    result = admission.measurement_identity(record, run)
    assert result['status'] == ('passed' if mutation == 'none' else 'unproven')
    assert bool(result['reasons']) == (mutation != 'none')
