# SPDX-License-Identifier: AGPL-3.0-only
"""Every required scalar/categorical volume workflow from a clean wheel, one worker per scene."""
import os
from pathlib import Path
import pytest
from tools.volume_wheel_reference import CASES
from tools.volume_wheel_runner import ROOT,installed_environment,run_case

pytestmark=[pytest.mark.gpu,pytest.mark.wheel]


@pytest.fixture(scope='module')
def consumer():
    wheel=os.environ.get('VISPY_TEST_WHEEL')
    assert wheel, 'Set VISPY_TEST_WHEEL to the wheel under test; missing artifacts are failures'
    evidence=Path(os.environ.get('VISPY_VOLUME_WHEEL_EVIDENCE',ROOT/'build/evidence/volume-wheel')).resolve()
    with installed_environment(wheel,evidence) as (python,environment):
        yield python,Path(wheel),evidence,environment


@pytest.mark.parametrize('name',CASES)
def test_installed_wheel_scene_matches_original_complete_frame(name,consumer):
    python,wheel,evidence,environment=consumer
    observed=run_case(name,python,wheel,evidence,environment)
    assert observed['child_waited'] and observed['report_present'], observed
    assert observed.get('actual_worker_terminal',{}).get('terminal'), observed
    worker=observed['worker']
    assert worker['launch_id']==observed['launch_id'] and worker['pid']==observed['actual_worker_pid']
    assert worker['case']==name and worker['reference_preserved'], worker
    assert worker['cleanup_passed'], worker
    assert worker['native_origins_verified'], worker.get('native_origin_error',worker)
    assert observed['process_exit']==worker['process_exit']==0, worker.get('error',worker)
    assert worker['status']=='PASS_INSTALLED_WHEEL_VOLUME_CASE'
    assert worker['compared_pixels']==96*96 and worker['excluded_pixels']==0
    assert worker['comparison_criteria_passed'] and worker['semantic_observations_exact']
