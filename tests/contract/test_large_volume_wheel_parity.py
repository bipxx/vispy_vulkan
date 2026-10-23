# SPDX-License-Identifier: AGPL-3.0-only
"""Mandatory installed-wheel quality/residency on all 24 large volume workloads."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from tools import large_volume_wheel_suite as suite

pytestmark=[pytest.mark.gpu,pytest.mark.wheel]
REFERENCE_SHA256='af7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac'


@pytest.fixture(scope='module')
def qualified_large_volume_suite():
    assert sys.platform=='win32' and sys.implementation.name=='cpython' and sys.version_info[:3]==(3,12,8)
    wheel=os.environ.get('VISPY_TEST_WHEEL')
    assert wheel,'The pinned installed-wheel artifact is mandatory; no missing-artifact skip'
    reference=Path(os.environ.get('VISPY_LARGE_VOLUME_REFERENCE',suite.ROOT/'tests/reference/large-volume-opengl')).resolve()
    output=Path(os.environ.get('VISPY_LARGE_VOLUME_EVIDENCE',suite.ROOT/'build/evidence/large-volume-wheel')).resolve()
    args=SimpleNamespace(kind='candidate',wheel=Path(wheel).resolve(),repository=suite.ROOT,
        output=output,reference=reference,reference_sha256=REFERENCE_SHA256)
    code=suite.run(args)
    return output,json.loads((output/'manifest.json').read_bytes()),code


@pytest.mark.parametrize('name',suite.CASES)
def test_all_large_volume_controls_match_original_and_retain_residency(name,qualified_large_volume_suite):
    output,manifest,code=qualified_large_volume_suite
    assert code==0,manifest.get('error',manifest)
    suite.assert_successful_parent(manifest,'candidate')
    row=manifest['workers'][name];worker=json.loads((output/name/'result.json').read_bytes())
    assert row['report_sha256']==suite.sha(output/name/'result.json')
    assert row['process_exit']==worker['process_exit']==0,worker.get('error',worker)
    assert worker['status']=='PASS_CANDIDATE_LARGE_VOLUME'
    viewport=suite.case_contract(name)['workload']['viewport']
    assert worker['compared_pixels']==viewport[0]*viewport[1]*4 and worker['excluded_pixels']==0
    assert worker['cleanup_passed'] and worker['native_origins_verified'] and worker['visible_windows_after_close']==0
    assert len(worker['shutdown_zeros'])==8 and set(worker['shutdown_zeros'].values())=={0}
    assert set(worker['stages'])==set(suite.STAGES)
    for stage,checks in worker['stages'].items():
        assert checks['nonblank'] and checks['comparison']['status']=='passed'
        assert checks['glir_draws_on_owned_framebuffer']>0
        if stage=='repeat' or stage!='initial' and name.endswith('-resident'):
            assert checks['residency']['passed']
        if stage in ('probe7','probe73'):
            assert checks['change_discrimination']['passed']
