# SPDX-License-Identifier: AGPL-3.0-only
"""A passing case cannot hide a failed or incomplete enclosing suite."""
from copy import deepcopy
import pytest
from tools.large_image_wheel_suite import CASES, assert_successful_parent


def parent(kind):
    return dict(kind=kind, cases=list(CASES), status='PASS_ALL_'+kind.upper()+'_LARGE_IMAGES',
                required_cases_without_verified_result=[],
                workers={name:dict(process_exit=0, child_waited=True,
                                   actual_worker_terminal=dict(terminal=True),
                                   worker_status='PASS_'+kind.upper()+'_LARGE_IMAGE') for name in CASES})


@pytest.mark.parametrize('kind', ('upstream', 'candidate'))
def test_complete_parent_accepts_only_all_four_terminal_passing_cases(kind):
    assert_successful_parent(parent(kind), kind)


@pytest.mark.parametrize('mutation', ('exit', 'wait', 'terminal', 'status', 'missing', 'error', 'parent_status'))
def test_case_success_does_not_override_actual_process_or_parent_failure(mutation):
    report = deepcopy(parent('candidate'))
    row = report['workers'][CASES[-1]]
    if mutation == 'exit': row['process_exit'] = 1
    if mutation == 'wait': row['child_waited'] = False
    if mutation == 'terminal': row['actual_worker_terminal']['terminal'] = False
    if mutation == 'status': row['worker_status'] = 'FAILED_PRESERVED'
    if mutation == 'missing': report['required_cases_without_verified_result'] = [CASES[-1]]
    if mutation == 'error': report['error'] = 'teardown failed'
    if mutation == 'parent_status': report['status'] = 'FAILED_REQUIRED_LARGE_IMAGES'
    with pytest.raises(AssertionError):
        assert_successful_parent(report, 'candidate')


def test_exact_reference_comparison_and_camera_gate_detect_corruption(tmp_path, monkeypatch):
    import numpy as np
    from tools import large_image_wheel_suite as suite
    # Full analytic-frame checks have separate tests. Isolate the exact parity
    # and metadata admission here so a reference mismatch cannot be hidden by
    # an analytic tolerance or a permissive quality result.
    monkeypatch.setattr(suite, 'quality_result', lambda *a: dict(passed=True))
    reference = np.array([[[0, 64, 128, 255]]], np.uint8)
    np.savez_compressed(tmp_path/'baseline.npz', rgba=reference)
    row = dict(camera_rect=[0, 0, 4096, 4096], source_texture_id=1, target_texture_id=2,
               framebuffer_id=3, commands=[['CURRENT', 0, 0], ['FRAMEBUFFER', 3, True], ['DRAW', 4]],
               counter_delta=dict(texture_uploads=1, texture_upload_bytes=4096*4096*4))
    assert suite.assert_stage('scalar_nearest', 'baseline', reference, row, 'candidate', tmp_path)['exact_original']
    bad = reference.copy(); bad[0, 0, 0] = 1
    with pytest.raises(AssertionError, match='Exact full-frame'):
        suite.assert_stage('scalar_nearest', 'baseline', bad, row, 'candidate', tmp_path)
    row['camera_rect'][0] = 1
    with pytest.raises(AssertionError):
        suite.assert_stage('scalar_nearest', 'baseline', reference, row, 'candidate', tmp_path)
    row['camera_rect'][0] = 0; row['counter_delta']['texture_uploads'] = 0
    with pytest.raises(AssertionError):
        suite.assert_stage('scalar_nearest', 'baseline', reference, row, 'candidate', tmp_path)


@pytest.mark.parametrize('kind', ('upstream', 'candidate'))
def test_resident_stage_rejects_data_commands_and_native_uploads(tmp_path, monkeypatch, kind):
    import numpy as np
    from tools import large_image_wheel_suite as suite
    from tools.fixture_large_image import RESIDENT_ZERO
    monkeypatch.setattr(suite, 'quality_result', lambda *a: dict(passed=True))
    frame = np.zeros((1, 1, 4), np.uint8)
    np.savez_compressed(tmp_path/'repeat.npz', rgba=frame)
    delta = dict.fromkeys(RESIDENT_ZERO, 0)
    delta.update(draw_calls=1, vk_queue_submits=1)
    row = dict(camera_rect=[0, 0, 4096, 4096], source_texture_id=1, target_texture_id=2,
               framebuffer_id=3, counter_delta=delta if kind == 'candidate' else None,
               commands=[['CURRENT', 0, 0], ['FRAMEBUFFER', 3, True], ['DRAW', 4]])
    suite.assert_stage('rgba_nearest', 'repeat', frame, row, kind, tmp_path)
    clean_commands = list(row['commands'])
    row['commands'].append(['DATA', 1, [0, 0], {'array': {'bytes': 67108864}}])
    with pytest.raises(AssertionError, match='GLIR data'):
        suite.assert_stage('rgba_nearest', 'repeat', frame, row, kind, tmp_path)
    if kind == 'candidate':
        row['commands'] = clean_commands; delta['texture_uploads'] = 1
        with pytest.raises(AssertionError):
            suite.assert_stage('rgba_nearest', 'repeat', frame, row, kind, tmp_path)
