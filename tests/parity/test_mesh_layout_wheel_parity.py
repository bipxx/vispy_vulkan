# SPDX-License-Identifier: AGPL-3.0-only
"""Every required mesh/layout/text scene from a clean wheel, one worker per scene."""
import os
from pathlib import Path
import pytest
from tools.fixture_mesh_layout_extensions import CASES
from tools.mesh_layout_smooth_line import SMOOTH_LINE
from tools.mesh_layout_wheel_runner import ROOT,installed_environment,run_case

pytestmark=[pytest.mark.gpu,pytest.mark.wheel]


@pytest.fixture(scope='module')
def consumer():
    wheel=os.environ.get('VISPY_TEST_WHEEL')
    assert wheel, 'Set VISPY_TEST_WHEEL to the wheel under test; missing artifacts are failures'
    evidence=Path(os.environ.get('VISPY_MESH_LAYOUT_EVIDENCE',ROOT/'build/evidence/mesh-layout-wheel')).resolve()
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
    assert worker['status']=='PASS_INSTALLED_WHEEL_MESH_LAYOUT_CASE'
    assert worker['compared_pixels']==224*160 and worker['excluded_pixels']==0
    # Decisions D5 and D9: the axes/colorbar scene uses the smooth-line criterion without the frame cap; alpha stays exact.
    assert worker['comparison']==('smooth_line' if name in SMOOTH_LINE else 'fixture')
    assert worker['alpha_exact'] and worker['cpu_atlases_exact']
