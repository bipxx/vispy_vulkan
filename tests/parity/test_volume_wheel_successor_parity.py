# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of test_volume_wheel_parity.py: every required scalar and categorical volume workflow from a
clean wheel, one worker per scene, with the categorical (napari) cases on the napari release that
tools/volume_wheel_reference_successor.py names (0.10.0).

VISPY_TEST_RUNTIME_REQUIREMENTS must name that release's runtime (its lock without vispy, plus numba). Evidence goes
to VISPY_NAPARI_EVIDENCE (tools/napari_host_packets.evidence_dir) and must be fresh.
"""
import os
from pathlib import Path
import pytest
from tools.volume_wheel_reference_successor import CASES,DIRECT_CASES,NAPARI
from tools.napari_host_packets import evidence_dir
from tools.volume_wheel_runner_successor import ROOT,installed_environment,run_case

pytestmark=[pytest.mark.gpu,pytest.mark.wheel]


@pytest.fixture(scope='module')
def consumer():
    wheel=os.environ.get('VISPY_TEST_WHEEL')
    assert wheel, 'Set VISPY_TEST_WHEEL to the wheel under test; missing artifacts are failures'
    runtime=os.environ.get('VISPY_TEST_RUNTIME_REQUIREMENTS')
    assert runtime and f'napari=={NAPARI}' in Path(runtime).read_text(encoding='utf-8'), 'Set VISPY_TEST_RUNTIME_REQUIREMENTS to the napari release runtime'
    evidence=evidence_dir('volume-wheel-successor',NAPARI).resolve()
    assert not evidence.exists(), 'Preserve every earlier consumer attempt'
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
    napari_case=name not in DIRECT_CASES
    assert ('host' in worker)==napari_case and (not napari_case or worker['host']['napari']==NAPARI)
