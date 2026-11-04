# SPDX-License-Identifier: AGPL-3.0-only
"""D31: the volume scientific admission on napari 0.10.0.

tools/volume_scientific_admission_successor.py joins the unchanged 24 large-volume workloads to the 17 small controls
re-run on napari 0.10.0 (tests/reference/volume-scientific-controls-numpy246-napari-0.10.0). Its helpers,
verify_large_case, measurement_identity and main are the retained code objects; verify_controls and produce are the
retained functions with exactly the changes named here.
"""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import textwrap

from tools import volume_scientific_admission as old
from tools import volume_scientific_admission_successor as new
from tools import volume_wheel_reference_successor as successor_reference

ROOT = Path(__file__).resolve().parents[2]
SET = ROOT / 'compat/scientific-admissions/volume-native58-cp312-numpy246-napari-0.10.0'
REBOUND = ('sha', 'read', 'write', 'bounded', 'device_cell', 'verify_large_case', 'measurement_identity', 'main')
CHANGES = {
    'verify_controls': (
        ("relative=='build/volume-admission-prep-root-1/run_controls1.py'",
         "relative=='build/runs/napari-010-volume-admission-307/run_controls.py'"),
        ("""        producers={f'tools/fixture_{stem}.py':original['provenance']['volume_fixture_sha256'],
                   f'tools/oracle_{stem}_capture.py':original['provenance']['volume_capture_sha256'],
                   'tools/fixture_gloo.py':original['provenance']['fixture_source_sha256']}
        if packet=='napari-volume-opengl':
            producers['tools/oracle_napari_requirements.txt']=original['provenance']['host_requirements_sha256']
""", """        if packet=='volume-opengl':
            producers={f'tools/fixture_{stem}.py':original['provenance']['volume_fixture_sha256'],
                       f'tools/oracle_{stem}_capture.py':original['provenance']['volume_capture_sha256'],
                       'tools/fixture_gloo.py':original['provenance']['fixture_source_sha256']}
        else:
            # The D30 packet: its successor fixture and capture tool, the retained fixture they wrap, its host lock.
            producers={f'tools/fixture_{stem}_successor.py':original['provenance']['fixture_source_sha256'],
                       f'tools/fixture_{stem}.py':original['provenance']['retained_fixture_source_sha256'],
                       'tools/oracle_napari_successor_capture.py':original['provenance']['capture_source_sha256']}
            lock=original['provenance']['host_lock']
            path=bounded(base,lock['snapshot']);assert sha(path)==lock['sha256'];evidence[path]=lock['sha256']
"""),
        ("worker['host']['napari']=='0.9.2'", "worker['host']['napari']=='0.10.0'"),
    ),
    'produce': (
        ("for relative in ('tools/volume_scientific_admission.py',*large.SOURCES):",
         "for relative in ('tools/volume_scientific_admission.py','tools/volume_scientific_admission_successor.py',\n"
         "                         'tools/volume_wheel_reference.py','tools/volume_wheel_reference_successor.py',*large.SOURCES):"),
        ("status='PASS_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS',cases=reports,",
         "status='PASS_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS',cases=reports,napari='0.10.0',"),
    ),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def test_the_rebound_steps_are_the_retained_code_in_the_successors_globals():
    for name in REBOUND:
        function = getattr(new, name)
        assert function.__code__ is getattr(old, name).__code__, name
        assert function.__globals__ is vars(new) and function.__defaults__ == getattr(old, name).__defaults__, name


def test_every_global_the_rebound_and_copied_code_reads_exists_in_the_successor():
    def names(code):
        yield from code.co_names
        for constant in code.co_consts:
            if hasattr(constant, 'co_names'):
                yield from names(constant)
    for name in (*REBOUND, *CHANGES):
        code = getattr(new, name).__code__
        missing = {item for item in names(code) if item not in vars(new) and not hasattr(__builtins__, item)
                   and item not in (__builtins__ if isinstance(__builtins__, dict) else {})}
        # Attribute names (e.g. 'items', 'read_bytes') share co_names; only module-level names can be missing here.
        assert not {item for item in missing if item in vars(old)}, (name, missing)


def test_the_copied_steps_are_the_retained_ones_with_exactly_the_named_changes():
    for name, changes in CHANGES.items():
        text = textwrap.dedent(inspect.getsource(getattr(old, name)))
        for before, after in changes:
            assert text.count(before) == 1, (name, before[:60])
            text = text.replace(before, after)
        expected = ast.dump(ast.parse(text))
        assert ast.dump(ast.parse(textwrap.dedent(inspect.getsource(getattr(new, name))))) == expected, name


def test_the_successor_reads_the_napari_0_10_0_inputs_and_the_retained_large_evidence():
    assert new.small is successor_reference and successor_reference.NAPARI == '0.10.0'
    assert new.benchmark is old.benchmark and new.large is old.large and new.CHECK_CASES is old.CHECK_CASES
    assert new.CONTROL_ROOT == ROOT / 'tests/reference/volume-scientific-controls-numpy246-napari-0.10.0'
    assert new.CONTROLS_SHA == digest(new.CONTROL_ROOT / 'manifest.json') != old.CONTROLS_SHA
    assert (new.LARGE_ROOT, new.ORIGINAL_ROOT) == (old.LARGE_ROOT, old.ORIGINAL_ROOT)
    assert (new.LARGE_CANDIDATE_SHA, new.LARGE_ORIGINAL_SHA) == (old.LARGE_CANDIDATE_SHA, old.LARGE_ORIGINAL_SHA)
    manifest = load(new.CONTROL_ROOT / 'manifest.json')
    assert manifest['wheel_sha256'] == old.large.CANDIDATE_SHA and manifest['cases'] == list(successor_reference.CASES)


def test_the_seventeen_controls_verify_exactly_on_napari_0_10_0():
    controls = new.verify_controls()
    assert set(controls['cases']) == set(successor_reference.CASES) and controls['package_sha256']
    assert all(case['max_channel_error'] == 0 for case in controls['cases'].values())


def test_the_tracked_set_verifies_against_the_current_controls_and_large_evidence():
    # produce() wrote this set in the repository (its evidence paths are relative to it); writing a fresh set in a test
    # would need the repository's volume, so the test checks the tracked set the way produce() checks its own output.
    controls = new.verify_controls()
    plan, qualification = load(SET / 'quality-plan.json'), load(SET / 'qualification.json')
    assert qualification['status'] == 'PASS_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS' and qualification['napari'] == '0.10.0'
    assert qualification['controls_manifest_sha256'] == new.CONTROLS_SHA and qualification['controls'] == controls['cases']
    assert set(plan) == set(qualification['cases']) == set(old.large.CASES)
    for name in old.large.CASES:
        path = SET / plan[name]['scientific_admission']
        record, result = load(path), new.verify_large_case(name, controls)
        assert record['workload'] == name and record['workload_sha256'] == result['workload_sha256']
        assert record['benchmark_data_sha256'] == result['data_sha256']
        assert record['artifacts']['candidate']['installed_package_sha256'] == result['package_sha256'] == controls['package_sha256']
        gate = new.benchmark.validate_admission(plan[name], new.benchmark.CATALOG[name],
                                                [dict(data_sha256=result['data_sha256'])] * 2, SET)
        assert gate['status'] == 'passed', gate
        assert qualification['cases'][name] == dict(admission_sha256=digest(path), visible_change_checks=2,
                                                    maximum_channel_error=result['maximum_channel_error'])


__all__ = [name for name in dir() if name.startswith('test_')]
